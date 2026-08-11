# v0.7.1 P1 统计优化落地（小时显示 + 总时长口径统一 + 活跃度）

## 一、案例基本信息
- 问题场景分类：v0.7.1 P1 功能落地（StatsPanel 统计展示优化 + 统计口径统一 + 活跃度）
- 产生时间：2026-08-11
- 项目模块：
  - 后端：`backend/utils/user_stats.py`（新增 compute_current_streak / compute_active_days / _parse_log_date；aggregate_stats 改口径）、`backend/api/user.py`（/api/user/stats 总时长改读 listening_total + 取 30 天记录）
  - 前端：`frontend/src/components/user/StatsPanel.vue`（formatDuration 小时化 + 图表转小时 + 新增活跃度卡片）
  - 测试：`backend/tests/test_user_stats.py`（38 单测）、`test_user_stats_realdata.py`（2 realdata）
- 相似问题判定特征：
  1. "统计 / 听取总时长 / 小时显示" → `user_stats.py` 纯函数 + StatsPanel 前端 `formatDuration`
  2. "总时长删专辑就掉 / 口径不一致" → 改读 `users.listening_total` 持久化列（pause 随 play_seconds 累加，删专辑不掉），不再 SUM albums.listening_duration
  3. "活跃度 / 连续收听 / 打卡天数" → `compute_current_streak`（标准断签语义）+ `compute_active_days`，数据源 `user_listening_log`
  4. "图表秒单位想改小时" → series data `duration / 3600` 保留浮点精度（轴刻度自动取整），tooltip / axisLabel 用 `toFixed(1)`

## 二、原始问题描述
v0.7.1 P1：个人中心统计展示优化。三个诉求：
1. **小时显示统一**：StatsPanel 总时长卡片与近 N 天柱状图全部 `h + 1 位小数`（不足 1 小时也显示如 `0.4小时`），替代原来「2小时30分钟 / 45分钟 / 30秒」混排格式
2. **总时长口径统一**：总时长改读 `users.listening_total`（P0 已迁移持久化列，pause 随 play_seconds 累加）——删专辑不掉，不再 `SUM(albums.listening_duration)`
3. **活跃度**：连续收听天数 + 近 30 天活跃天数，由 `user_listening_log` 纯函数计算（可单测）

## 三、核心诉求
1. 总时长卡片 + 近 N 天图表 y 轴 / 轴标签 / tooltip 全部转小时（1 位小数）
2. `/api/user/stats` 的 `total_duration` 改读 `users.listening_total`（口径统一）
3. 新增 `current_streak` / `active_days_30` 字段 + 前端两张卡片
4. 断签语义采用标准 App 语义（用户拍板）：今天未听不算断签，锚点 = 最近有收听日；昨天及更早有整天无收听即断签为 0

## 四、最终解决方案/改造步骤
1. **测试先行**（test_user_stats.py）：新增 `TestCurrentStreak` / `TestActiveDays` + `TestAggregateStats` 改为新口径断言（total_duration 读传入值、返回含 streak/active_days_30）→ 红灯（ImportError：新函数不存在）
2. **user_stats.py 新增纯函数**：
   - `_parse_log_date(value)`：统一解析 listen_date（date/datetime/字符串 → date，None/非法 → None）；`accumulate_daily_logs` 重构复用
   - `compute_current_streak(rows)`：收集「时长>0」的日期集合 → 锚点 = max(listened)；`last < today-1` 直接返回 0（断签）；否则从锚点往回连续数
   - `compute_active_days(rows, days=30)`：窗口 `[today-(days-1), today]` 内时长>0 的不同日期数
   - `aggregate_stats(album_rows, daily_rows, days, total_duration=None)`：total_duration 为 None 时回退 SUM(albums.listening_duration)（兼容旧调用）；返回新增 `current_streak` / `active_days_30`
3. **api/user.py /api/user/stats 改造**：
   - 新增 `SELECT listening_total FROM users` → `total_duration` 传给 aggregate_stats
   - daily 查询从「窗口内 days 天」改为固定取近 30 天（活跃度需要完整 30 天窗口）；柱状图窗口由 aggregate_stats 内部按 days 截取，窗口外行被 accumulate 忽略
4. **前端 StatsPanel.vue**：
   - `formatDuration(seconds) = (s/3600).toFixed(1) + '小时'`
   - 近 N 天图 series data `duration / 3600`（保留浮点精度），tooltip `(value).toFixed(1) + ' 小时'`，y 轴 axisLabel formatter `.toFixed(1)`
   - `DEFAULT_STATS` 加 `current_streak: 0` / `active_days_30: 0`；新增「连续收听 / 近30天活跃」卡片（值带小号「天」单位），统计卡片 6 张改 3 列网格
5. **realdata 更新**：test_stats_matches_db_aggregation 给测试用户 SET listening_total=4200 断言 total_duration=4200（证明读持久化列）、断言 streak=2 / active_days_30=3
6. **验证**：单测 38 → 全量 145 passed；realdata 2 passed（MySQL80 运行中）；eslint 通过；README 勾选 P1 + 明确断签语义（5cd1c0b）
7. **提交**：c6df000（代码+测试+README）、5cd1c0b（README 断签语义说明）

## 五、关键代码/配置/模板（可直接复用）
```python
# backend/utils/user_stats.py —— 活跃度纯函数（标准断签语义）
def compute_current_streak(rows):
    listened = set()
    for row in rows:
        d = _parse_log_date(row.get('listen_date'))
        if d is not None and float(row.get('duration_seconds') or 0) > 0:
            listened.add(d)
    if not listened:
        return 0
    last = max(listened)
    today = datetime.date.today()
    if last < today - datetime.timedelta(days=1):  # 昨天及更早有整天无收听 → 断签
        return 0
    streak = 0
    day = last
    while day in listened:
        streak += 1
        day -= datetime.timedelta(days=1)
    return streak

def compute_active_days(rows, days=30):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    active = set()
    for row in rows:
        d = _parse_log_date(row.get('listen_date'))
        if d is None or not (start <= d <= today):
            continue
        if float(row.get('duration_seconds') or 0) > 0:
            active.add(d)
    return len(active)

# aggregate_stats 关键点：total_duration 参数 + 返回活跃度
def aggregate_stats(album_rows, daily_rows, days, total_duration=None):
    if total_duration is None:
        total_duration = round(sum(float(a.get('listening_duration') or 0) for a in album_rows), 1)
    return {
        'album_count': len(album_rows),
        'scored_count': sum(1 for a in album_rows if is_scored(a.get('my_score'))),
        'review_count': sum(1 for a in album_rows if has_review(a.get('review'))),
        'total_duration': round(float(total_duration or 0), 1),   # 读 users.listening_total
        'current_streak': compute_current_streak(daily_rows),
        'active_days_30': compute_active_days(daily_rows, 30),
        'daily_listening': accumulate_daily_logs(daily_rows, days),
        'tag_distribution': build_tag_distribution(album_rows),
        'score_distribution': build_score_distribution(album_rows),
    }
```
```js
// frontend StatsPanel.vue —— 小时显示
formatDuration(seconds) {
  const s = Number(seconds) || 0
  return `${(s / 3600).toFixed(1)}小时`
}
// 近N天图：series data 用秒转小时（保留浮点），轴/tooltip toFixed(1)
data: list.map(d => Number(d.duration || 0) / 3600)
axisLabel: { formatter: v => `${Number(v).toFixed(1)}` }
tooltip: return `${p.axisValue}：${(Number(p.value) || 0).toFixed(1)} 小时`
```

## 六、踩坑点 & 注意事项（非常重要）
- **`total_duration` 参数回退陷阱**：`aggregate_stats` 在 `total_duration=None` 时静默回退 `SUM(albums.listening_duration)`（兼容旧调用/旧测试）。**API 调用方必须显式传 `users.listening_total`**，否则口径不一致且无报错。未来新增统计聚合调用点要注意这一点
- **活跃度需要完整 30 天窗口**：daily 查询固定取近 30 天（`today - 29`），而不是所选 days 窗口（7/14/30）。若仍按窗口取，active_days_30 会漏算窗口外活跃日。窗口外行由 `accumulate_daily_logs` 的日期范围判断自动忽略，不会污染柱状图
- **`_parse_log_date` 必须兼容三种类型**：PyMySQL 对 DATE 列返回 `datetime.date`、DATETIME 返回 `datetime.datetime`、手写字符串 'YYYY-MM-DD'——统一转 date，字符串要 `[:10]` 截断防带时间
- **断签语义**：标准语义「今天未听不算断签」（锚点 = 最近有收听日）；`last < today-1` 才判断签 0。不要用「今天必须听否则 0」的严格口径，也不要出现「最近收听日早于昨天还显示 >0」的错误（会当成连续）
- **图表秒转小时别预舍入**：series data 用 `duration / 3600` 保留浮点（如 90 秒 → 0.025 小时），ECharts 自动取整刻度（0.5 / 1 / 1.5…）；若先 `toFixed(1)` 会把 0.025 → 0.0，柱状图消失
- **realdata 前确认 MySQL**：`sc query MySQL80` 状态 RUNNING 再跑，避免误判「接口挂了」；realdata 用进程内 `test_client` 不经过 5000 端口，不会踩 P0 的「多实例端口冲突」，但 curl 验证真实接口时仍要先 `netstat :5000`

## 七、同类问题快速适配规则
- 【适配点1】"统计/图表想改小时显示" → 前端 `formatDuration = (s/3600).toFixed(1)+'小时'`；图 series data `/3600`（不预舍入）+ tooltip/axisLabel `toFixed(1)`，数据源仍传秒（后端口径不变）
- 【适配点2】"总时长口径/删专辑掉时" → API 里 `SELECT listening_total FROM users`，传给 `aggregate_stats(..., total_duration)`；不要 SUM albums.listening_duration
- 【适配点3】"新增活跃度/打卡类统计" → `user_listening_log` 行直接喂 `compute_current_streak` / `compute_active_days`（纯函数零 DB 依赖）；API 记得取满 30 天窗口
- 【适配点4】断签/活跃度口径改版 → 只改 `user_stats.py` 两个纯函数 + `test_user_stats.py` 对应用例，README「已定决策」同步更新语义

## 八、优化复盘（2026-08-11 本次对话）
**流程效率**：按铁律「测试先行→实现→验证→提交」执行，本次一次通过无返工——先写活跃度单测 + aggregate_stats 新口径断言（红灯 ImportError）→ 实现纯函数 → 绿灯 38 → 更新 API → realdata 更新 → 全量 145 + realdata 2 全绿 → eslint → 提交。前端纯展示改动（小时化 + 新卡片），eslint 把关即可，风险低。

**浪费点 / 可改进**：
1. 无明显大坑。唯一潜在点：前端 StatsPanel 改动只过了 eslint，未做浏览器人工验证（项目 playwright 未配置）——纯展示层改动风险低，但严格流程下近 N 天图表「转小时后轴刻度」值得肉眼扫一眼
2. `aggregate_stats` 的 total_duration 回退设计是双刃剑：向后兼容了旧测试，但也埋了「调用方忘传 → 静默回退旧口径」的隐患。本次 API 显式传值 + 单测覆盖了 fallback 分支，后续新增调用点需留意
3. 复用 P0 教训（netstat / /tmp / 中文编码 / 响应结构）本次 realdata 用进程内 test_client，天然避开前三者，未耗时

**下次快速命中清单**：
- 活跃度统计直接复用：`compute_current_streak` / `compute_active_days` + `_parse_log_date`（`user_stats.py`）
- 总时长口径：API `SELECT listening_total FROM users` → `aggregate_stats(..., total_duration)`；注意显式传值防回退
- 小时显示：`formatDuration` + 图表 `/3600` 不预舍入 + `toFixed(1)` 三件套（StatsPanel.vue）
- 可复用测试：`test_user_stats.py::TestCurrentStreak/TestActiveDays`（断签/窗口边界用例）、`test_user_stats_realdata.py`（总时长读持久化列 + 活跃度）
- 待办：v0.7.1 P2 蒙版滑轨偏移修复（实测 rect → CSS 补偿 + 数值气泡/刻度线）、以及 README「待做」补充项（utils/duration.js 统一、等级徽章入口扩展）
