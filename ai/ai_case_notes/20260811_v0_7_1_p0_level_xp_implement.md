# v0.7.1 P0 等级经验系统落地 + 评分经验重复发放修复

## 一、案例基本信息
- 问题场景分类：v0.7.1 P0 功能落地（等级经验 + 反馈）+ 修复「评分经验重复发放」bug
- 产生时间：2026-08-11
- 项目模块：
  - 后端：`backend/utils/level.py`（新增）、`backend/utils/score.py`（新增 normalize_score_list）、`backend/utils/db.py`（四列幂等迁移+回填）、`backend/utils/user.py`（add_bonus_xp）、`backend/api/listening.py`（pause 挂经验）、`backend/api/score.py`（加分改变化判定）、`backend/api/review.py` / `comment.py`（+20/+10）、`backend/api/user.py`（info 加字段）
  - 前端：`frontend/src/utils/level.js` / `message.js` / `levelFeedback.js`（新增）、`ProfilePanel.vue`（进度条+称号+距下一级）、`LoginPage.vue`（等级基线）、`AlbumDetail.vue` / `AlbumTrackList.vue` / `MusicList.vue`（反馈接线）
  - 测试：`backend/tests/test_level.py`（42 单测）、`test_user_table_migration.py`、`test_level_realdata.py`（21 realdata）、`test_score.py`
- 相似问题判定特征：
  1. "加经验 / 等级 / 加分" → `level.py`/`level.js` 平方根纯函数（前后端同源）+ `add_bonus_xp`（每日上限 100）
  2. "某接口每次调用都加分 / 经验被刷" → 检查前端是否在生命周期（deactivated / beforeDestroy / 防抖保存）自动发请求；后端按「实际变化」判定，比较已存值归一化
  3. "改了代码但接口行为不变" → 先查 `netstat -ano | grep :5000` 是否多实例同时监听，请求被随机打到旧代码
  4. "给 users 表加列 / 回填" → `information_schema.columns` 幂等迁移（复用 avatar 模式）

## 二、原始问题描述
- v0.7.1 P0：等级经验系统 + 经验反馈。经验与听取时长强相关（1 秒 = 1 XP 无上限）+ 听后感 +20 / 评论 +10 / 评分 +5（每日合计上限 100）；平方根曲线 `level = floor(sqrt(xp/3600))`；升级横幅 + +N 经验 toast；`/api/user/info` 加字段；ProfilePanel 进度条。
- 收尾时发现 bug：**评分经验重复发放**。老版本前端评分上传分很多次——离开评分板块自动上传、切换子页面时保存、退出专辑返回主页也保存。每发一次 PUT 后端都无条件 +5，导致不评分也白拿经验。
- 根因链：`AlbumDetail.beforeDestroy → triggerSaveScore → saveAllScore → doScoreSave → PUT`；`AlbumTrackList.deactivated/beforeDestroy → saveAllScore → PUT`；评分拖动防抖 `scheduleScoreSave → PUT`。四条路径都无条件发保存请求，后端每条都 `add_bonus_xp(+5)`。

## 三、核心诉求
1. P0 落地：迁移 + 纯函数 + 各接口挂经验 + 反馈 + 进度条 + realdata 验证
2. 修复评分经验重复发放：离开板块 / 切页 / 退出专辑的自动保存不再加分
3. 保持「评分实际变化才 +5」语义，前端已有 `xp_gained>0` 才 toast 的守卫

## 四、最终解决方案/改造步骤
1. **P0 实现**（已提交 7e06589 / c8ddbd6）：
   - `users` 加 `xp / listening_total / bonus_date / bonus_xp_today` 四列，幂等迁移 + 一次性回填 `xp = listening_total = SUM(listening_duration)`（`ensure_users_xp_columns()`，挂 `init_base_tables()`）
   - `level.py` 纯函数：compute_level / xp_to_next_level / level_progress / level_title / compute_bonus_gain；前端 `level.js` 镜像
   - `add_bonus_xp(user_id, amount)`：读 bonus_date 跨天重置，`gained = min(amount, max(0, 100-today))`，更新 xp/level/bonus_xp_today，返回 (gained, new_xp, new_level, level_up)
   - pause 挂收听经验（`xp/listening_total += play_seconds`，返回 `xp/level/level_up`）；review +20 / comment +10 / score +5 返回 `xp_gained`
   - `/api/user/info` 返回 `xp/level/next_level_xp/xp_progress/level_title`
   - 前端 `message.js` 全局 `$message` + 升级横幅；`levelFeedback.js::handleLevelFeedback` 检测升级 + `+N 经验` toast；ProfilePanel 进度条
2. **修复评分经验重复发放**（885057f）：
   - `utils/score.py` 新增 `normalize_score_list(score_list)`：剥末尾连续 0（含 `'0'/''`），首位专辑分保留；非列表返回 `[]`——末尾 0 代表未评分单曲，数组长度随曲目数变化，剥掉后比较避免误判
   - `api/score.py` 保存前先 `SELECT my_score`，`json.loads` 解析（容错非 list → `[]`），`score_changed = normalize(old) != normalize(new)`；`score_changed` 才 `add_bonus_xp(+5)`，否则 `xp_gained = 0`
   - 响应仍返回 `xp_gained`（0 表示未变化），前端 toast 守卫 `data.xp_gained > 0` 自动不弹

## 五、关键代码/配置/模板（可直接复用）
```python
# backend/utils/score.py —— 评分变化判定归一化
def normalize_score_list(score_list):
    if not isinstance(score_list, list):
        return []
    result = list(score_list)
    while result and result[-1] in (0, 0.0, '0', ''):
        result.pop()
    return result

# backend/api/score.py —— 保存接口加分门控
old_list = []
cursor.execute(f'SELECT my_score FROM `{table_name}` WHERE id = %s LIMIT 1', (album_id,))
old_row = cursor.fetchone()
if old_row and old_row.get('my_score'):
    try:
        parsed = json.loads(old_row['my_score'])
        if isinstance(parsed, list):
            old_list = parsed
    except (json.JSONDecodeError, TypeError):
        old_list = []
score_changed = normalize_score_list(old_list) != normalize_score_list(score_list)
# ...UPDATE my_score 落库...
xp_gained = 0.0
if score_changed:
    xp_gained, _, _, _ = add_bonus_xp(current_user_id, 5)
```
- 其余复用：`backend/utils/level.py` / `frontend/src/utils/level.js` 纯函数、`add_bonus_xp`、`ensure_users_xp_columns` 幂等迁移——完整见本目录 `20260811_v0_7_1_level_xp_planning.md`
- 前端反馈接线：`handleLevelFeedback(res.data.data, {toast: '评分保存'})`；升级检测 `detectLevelUp(level, title)` 对比 `localStorage.level`（无 key 视为首次静默设基线，不弹假横幅）

## 六、踩坑点 & 注意事项（非常重要）
- **多后端实例端口冲突（本次最费时）**：两个 python 进程同时 `LISTEN 0.0.0.0:5000`（SO_REUSEADDR），请求被随机分发——旧实例跑旧代码，表现为「改了代码但接口行为不变」。`netstat -ano | grep :5000` 看是否多 PID，多则杀旧进程。**开发流程固定动作：改后端代码后先查端口再测**
- **`/tmp` 路径坑**：Git Bash 的 `/tmp` 是虚拟路径，Windows 便携 python `open('/tmp/x.json')` 读不到 → FileNotFoundError。不要在 bash 落盘到 `/tmp` 再让 python 读；用管道 stdin 传 JSON 给 python 解析
- **中文 JSON body 编码坑**：git bash 里 `curl -d '{"album_name":"中文"}'` 以 GBK 发送，Flask UTF-8 解码失败（"Failed to decode JSON object"）。E2E 验证用纯 ASCII 数据，或写 UTF-8 文件 `--data-binary @file`
- **接口返回结构先确认再解**：`POST /api/album/add` 返回 `data.id`（专辑字段平铺在 data 顶层），不是 `data.album.id`——先看一次真实响应再写解析，避免 KeyError 白跑一轮
- **前端生命周期自动保存是 XP 重复发放的温床**：deactivated / beforeDestroy / 防抖保存都可能发幂等写请求；后端加分一律按「实际变化」判定，不要把「保存成功」直接当「做了这件事」
- **归一化只剥末尾 0**：首位是专辑整体分，为 0 也保留结构；不能用 `filter(x != 0)`（会把 `[0,0,0,80]` 变 `[80]`，丢失曲目位置）

## 七、同类问题快速适配规则
- 【适配点1】"某操作被生命周期/防抖触发多次，导致重复加分 / 重复写库" → 后端接口先读已存值 + 归一化比较，未变化不写不加分；前端已有 toast 守卫 `>0` 时接口可直接返回 0
- 【适配点2】"改了后端没生效" → `netstat -ano | grep :5000` 查多实例，杀旧进程，重启再测
- 【适配点3】等级 / 加分系统新动作（如评论 +N）：在接口成功后 `add_bonus_xp(user_id, N)`，返回 `xp_gained`，前端 `handleLevelFeedback(data, {toast:'XX'})`
- 【适配点4】E2E 用 curl 验证：token 用管道 stdin 给 python 解；body 用 ASCII；请求前先 `netstat` 确认唯一实例

## 八、优化复盘（2026-08-11 本次对话）
**流程效率**：P0 主体按铁律「测试先行→实现→跑测试→提交」完成，单测 131 + realdata 21 全绿；README 勾选清单收尾。修复评分经验 bug 也是先写红灯测试（normalize_score_list 单测 + 同分重存 realdata）再实现，一次通过。E2E 端到端验证把关到位。

**浪费点**：
1. **旧后端端口冲突最费时**：E2E 时 pause 不返回 xp 字段，排查发现 12:46 启动的旧实例 + 16:17 新实例同时监听 5000，请求被随机分发到旧代码。多轮验证才发现是端口问题而非代码问题。教训：**「改代码行为不变」先查 `netstat :5000` 是否多实例**，这条应固化进开发流程
2. **`/tmp` 跨环境路径**：bash 写 `/tmp/login.json`，Windows python 读不到，浪费两轮。教训：跨 bash/python 传数据一律走 stdin 管道，不落中间文件
3. **中文 body 编码**：curl 直接带中文 JSON 被 GBK 编码，Flask 解码 500。教训：E2E 用 ASCII 数据或文件方式传
4. **接口返回结构假设错误**：按「data.album.id」解析实际是「data.id」，KeyError 浪费一轮。教训：先打印一次真实响应再写解析

**下次快速命中清单**：
- 后端加分门控：`normalize_score_list` + `score_changed` 判定直接复用；新加分动作照 `add_bonus_xp` + `handleLevelFeedback(data, {toast})` 模板
- 环境自查三板斧：改后端先 `netstat :5000` 查多实例 → E2E 数据走 stdin / ASCII → 解析前先看真实响应结构
- 可复用测试：`test_score.py::TestNormalizeScoreList`（归一化边界）、`test_level_realdata.py`（加分门控 realdata）
- 待办：v0.7.1 P1 统计优化（h 显示 + 总时长口径 + 活跃度）、P2 滑轨修复，见 README「待做」清单
