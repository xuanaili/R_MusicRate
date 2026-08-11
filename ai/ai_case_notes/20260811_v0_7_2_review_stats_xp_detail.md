# v0.7.2 听后感统计恒为0修复 + 等级经验详情（明细落表 + 接口 + 弹窗）

## 一、案例基本信息
- 问题场景分类：v0.7.2 功能落地（bug 修复 + 新功能）——「个人中心听后感统计恒为 0」修复 +「等级经验详情弹窗」
- 产生时间：2026-08-11
- 项目模块：
  - 后端：`backend/utils/user_stats.py`（count_review_items）、`backend/utils/db.py`（create_user_xp_log）、`backend/utils/xp.py`（常量，新增）、`backend/utils/xp_detail.py`（聚合纯函数，新增）、`backend/utils/user.py`（add_bonus_xp 加 source + 写 log）、`backend/api/user.py`（/api/user/xp-detail）、`backend/api/score.py` / `review.py` / `comment.py` / `listening.py`（加分点/收听点写明细）
  - 前端：`frontend/src/components/user/XpDetailModal.vue`（新增）、`ProfilePanel.vue`（徽章点击）
  - 测试：`backend/tests/test_user_stats.py`、`test_user_stats_realdata.py`、`test_xp.py`、`test_xp_detail.py`、`test_xp_detail_realdata.py`、`test_level_realdata.py`（新增/扩展）
- 相似问题判定特征：
  1. "个人中心某统计恒为 0 / 统计数字与详情页不一致" → 先核对统计函数的字段格式假设（`isinstance(parsed, list)` vs 真实 dict）与写入端格式，看日历/详情组件里怎么解析的
  2. "给某操作加经验 / 经验要按来源拆分" → `add_bonus_xp(user_id, amount, source)` + `user_xp_log` 落明细；来源枚举统一 `backend/utils/xp.py`
  3. "需要按天 / 按来源聚合经验" → `xp_detail.py` 的 `accumulate_bonus_daily` / `build_daily_xp`（零 DB 可单测）+ `user_listening_log`（1 秒 = 1 XP）
  4. "前端图表 / 组件依赖 v-if 分支 ref 却不显示" → 初始化放 `.finally` 的 `$nextTick`（loading 翻转后），不要放 `.then`
  5. "新表 / 新列" → `CREATE TABLE IF NOT EXISTS` 幂等 + 挂 `init_base_tables()`；realdata 测试的 fixture 也要建表（否则表只在后端起过时才有）

## 二、原始问题描述
- **需求 1（bug）**：个人中心「听后感」统计卡片恒为 0。用户明确有听后感数据，且老版本专辑详情页的听后感组件（含日历）能正常显示。同一份数据，详情页能看到、统计页却是 0。
- **需求 2（新功能）**：点击个人资料页等级徽章，弹出经验详情——总经验 / 今日经验 / 最近经验 / 按来源拆分（听歌 / 评分 / 听后感 / 评论）。
- 约束：历史经验无法按来源拆分（此前只存累计值、无明细）；v0.7.1 已确认口径「1 秒 = 1 XP 无上限 + 加分每日上限 100」。

## 三、核心诉求
1. 修复听后感统计恒为 0，且口径与日历一致（按 feelings 总条数统计，非有听感后的专辑数）
2. 新增经验明细表 `user_xp_log`，每次实际获得经验写一条（来源 + 数额 + 时间），只记 >0 防噪音
3. `GET /api/user/xp-detail` 接口：总经验 / 等级 / 距下一级 / 进度 / 总收听（完整历史）/ 今日（听歌 + 加分）/ 近 7 天每日 / 按来源累计 / 最近 30 条明细流
4. 前端 `XpDetailModal.vue` 弹窗展示，徽章点击触发

## 四、最终解决方案/改造步骤
1. **P0 听后感统计修复**（ff8955f）：
   - 根因：`has_review()` 判断 `isinstance(parsed, list)`，但 `review` 列真实存储是 dict `{"feelings":[...]}`（review.py / album.py / album_pool.py 写入）；日历接口 `review.get('feelings', [])` 按 dict 解析所以正常 → 统计恒 0 但日历正常
   - 改 `has_review()` → `count_review_items(review)`：dict 读 `feelings` 长度、list 兼容旧数组格式、None/空 → 0
   - `aggregate_stats` 的 `review_count = sum(count_review_items(...))`
   - 测试同步：`test_user_stats.py` 改用例（8 个 count_review_* 边界）+ `test_user_stats_realdata.py` 种数据改真实 dict 格式
2. **P1 经验明细落表**（bcc4881）：
   - `create_user_xp_log()`（`CREATE TABLE IF NOT EXISTS` 幂等，挂 `init_base_tables()`）
   - 新增 `backend/utils/xp.py` 常量：`XP_LISTENING/RATING/REVIEW/COMMENT`、`BONUS_SOURCES`（不含 listening）、`SOURCE_LABELS`
   - `add_bonus_xp(user_id, amount, source)` 加必填 source + 枚举校验；`gained > 0` 时同事务 INSERT `user_xp_log`（评分 +5 / 听后感 +20 / 评论 +10 ×2 处 / pause 收听 `amount=play_seconds`）
   - 同步更新 4 处接口调用 + 4 处 realdata 测试调用
3. **P1 经验详情接口**（95f574d）：`GET /api/user/xp-detail`（@login_required）——总经验/等级读 users 累计（完整历史），今日收听 = `user_listening_log` 今日 SUM，今日加分 = `bonus_xp_today`，近 7 天 / 按来源 / 明细流来自 `user_xp_log`；聚合纯函数 `xp_detail.py`（accumulate_bonus_daily / build_daily_xp）零 DB 可单测
4. **P1 前端弹窗**（a6d64b3 + 918227f）：`XpDetailModal.vue` 等级卡 + 今日三栏 + ECharts 近 7 天堆叠柱 + 按来源累计 + 明细流；ProfilePanel Lv 徽章 `@click.stop` 触发

## 五、关键代码/配置/模板（可直接复用）
```python
# backend/utils/user_stats.py —— 听后感条数（dict + 旧数组双兼容）
def count_review_items(review):
    parsed = safe_json_loads(review)
    if isinstance(parsed, list):
        return len(parsed)
    if isinstance(parsed, dict):
        feelings = parsed.get('feelings')
        return len(feelings) if isinstance(feelings, list) else 0
    return 0
```
```python
# backend/utils/xp.py —— 经验来源常量（新加分动作先加枚举再挂）
XP_LISTENING = 'listening'  # 听歌（1秒=1XP，无上限）
XP_RATING = 'rating'        # 评分保存成功 +5
XP_REVIEW = 'review'        # 听后感新增 +20
XP_COMMENT = 'comment'      # 评论新增 +10
BONUS_SOURCES = (XP_RATING, XP_REVIEW, XP_COMMENT)  # 加分来源（每日上限100）；不含 listening
SOURCE_LABELS = {XP_LISTENING: '听歌', XP_RATING: '评分', XP_REVIEW: '听后感', XP_COMMENT: '评论'}
```
```sql
-- backend/utils/db.py create_user_xp_log()（幂等，挂 init_base_tables）
CREATE TABLE IF NOT EXISTS user_xp_log (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id INT NOT NULL COMMENT '用户ID（关联users表）',
    xp_type VARCHAR(20) NOT NULL COMMENT '经验来源：listening/rating/review/comment',
    amount FLOAT NOT NULL DEFAULT 0 COMMENT '本次实际获得经验（仅记录>0）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '获得时间',
    INDEX idx_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户经验明细表（v0.7.2起）';
```
- 聚合纯函数 `backend/utils/xp_detail.py`：`accumulate_bonus_daily(rows, days=7)` 近 N 天加分按天累加补零；`build_daily_xp(listening_daily, bonus_daily)` 合并每日 total
- 前端弹窗：`XpDetailModal.vue`（ECharts 用法参照 StatsPanel + `sanitizeThemeColor` 兜底；mask+content 参照 AlbumLyricViewer）

## 六、踩坑点 & 注意事项（非常重要）
- **统计口径 vs 真实存储格式（本次 bug 根因）**：`has_review` 按 list 判断、真实是 dict——「日历能显示、统计是 0」是典型信号。改任何 JSON 列统计前先确认写入端格式，测试数据不要臆造格式（`test_user_stats_realdata.py` 原来用数组种数据，恰好掩盖了 bug）
- **Vue 条件渲染 + ref 初始化时序（本次最典型前端坑）**：图表初始化放 `.then` 里的 `$nextTick`，但那时 `loading` 仍为 `true`（`.finally` 才置 false）→ 页面停在「加载中」分支 → `this.$refs.dailyChart` 为 `null` → 初始化 return，图永远不渲染。**依赖 v-if/v-else-if 分支的 ref，初始化必须放到 `.finally` 的 `$nextTick`（状态翻转且 DOM 更新后）**
- **`add_bonus_xp` 签名变更**：source 设为必填 + 枚举校验，防止漏传静默丢 log；同步更新所有调用（含测试）
- **log 一致性**：log INSERT 与 users 累计同事务、`gained > 0` 才写 → `SUM(user_xp_log 加分)` 与 `bonus_xp_today` 严格一致；`play_seconds <= 0` 不写 listening log
- **历史口径区分**：`user_xp_log` 不回填历史（无法按来源拆分）；`source_totals` 仅代表 v0.7.2 起，弹窗文案区分「完整历史」（users.listening_total）与「自 v0.7.2 起」
- **realdata 测试自足建表**：新表只在 `init_base_tables()` 建、而后端未启动时跑 realdata 会报 table doesn't exist——测试 fixture 也要调 `create_user_xp_log()`
- **bash cwd 持久化**：Bash 工具调用间工作目录会保留，`cd frontend` 后再 `cd frontend` 会失败；跨目录命令用绝对路径 `cd /u/MusicRate/...`

## 七、同类问题快速适配规则
- 【适配点1】统计某 JSON 列恒 0 / 与详情页不一致 → 读写入端 + 详情解析端格式，确认 list / dict 结构；复用 `count_review_items`（dict feelings + 旧数组双兼容）
- 【适配点2】新加分动作（如收藏 +N）→ `xp.py` 加常量 → 接口成功后 `add_bonus_xp(user_id, N, XP_XX)`，返回 `xp_gained`；前端 toast 守卫 `>0`
- 【适配点3】新经验聚合 / 弹窗 → 复用 `xp_detail.py` 纯函数 + `/api/user/xp-detail` 响应结构；前端加 `SOURCE_META` 一条即可扩来源
- 【适配点4】图表/ref 依赖条件分支 → 初始化放 `.finally` 的 `$nextTick`；ECharts 用 `echarts/dist/echarts.min.js` + `sanitizeThemeColor` 兜底主题色
- 【适配点5】新表 → `create_xxx()` 幂等 + 挂 `init_base_tables()` + realdata fixture 同步建表

## 八、优化复盘（2026-08-11 本次对话）
**流程效率**：全程按铁律「测试先行→实现→跑测试→提交」执行。P0 修复：先写红灯测试（count_review_items 8 个边界 + realdata 改 dict 格式）再实现，一次通过。P1：常量→落表→聚合纯函数（先单测红→绿）→接口→弹窗，每步独立提交、可回滚。收尾全量 160 单测 + 25 realdata 全绿。

**浪费点**：
1. **前端弹窗图表时序 bug（最大浪费）**：`XpDetailModal` 提交后用户反馈「图不显示」。根因是 `renderChart` 放 `.then` 的 `$nextTick`，而 detail 分支要等 `.finally` 置 `loading=false` 才渲染 → ref 为 null。纯代码推演可定位（无需跑应用），但本应在写组件时就把「v-if 分支渲染顺序」想清楚——**初始化依赖条件分支 ref 时，`$nextTick` 只能保证「当前状态」的 DOM，状态还会在 finally 翻转一次**
2. **bash 目录持久化小坑**：`cd frontend` 一次后再 cd 报错，浪费一轮。教训：Bash 工具 cwd 会跨调用保留，命令里用绝对路径
3. **前端验证成本**：每次改 Vue 都要跑 `npm run build`（约 8s）确认编译。可以接受，但可先 `npx eslint`（秒级）过滤低级错误再 build

**下次快速命中清单**：
- 统计口径：`count_review_items` 直接复用；凡 JSON 列统计先看写入端格式（list/dict）
- 经验链路：`add_bonus_xp` + `xp.py` 常量 + `user_xp_log` + `xp_detail.py` 聚合纯函数 + `/api/user/xp-detail` 响应结构，一条链全复用
- 前端弹窗：`XpDetailModal.vue` 可作「主题色弹窗 + 图表 + 明细流」模板；图表初始化固定放 `.finally` 的 `$nextTick`
- 测试模板：`test_xp_detail.py`（纯函数补零/合并）、`test_xp_detail_realdata.py`（聚合与 DB 一致）、`test_level_realdata.py::test_bonus_xp_writes_log`（log 与 bonus_xp_today 一致性）
