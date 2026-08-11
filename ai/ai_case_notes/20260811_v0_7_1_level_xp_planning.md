# v0.7.1 等级经验系统 + 统计单位优化 + 蒙版滑轨修复（大版本规划定稿）

## 一、案例基本信息
- 问题场景分类：新版本规划（v0.7.1）→ 按「大版本规划工作流」出方案 + 写 README，不写实现代码
- 产生时间：2026-08-11
- 项目模块：
  - 后端：`backend/utils/db.py`（users 加列幂等迁移 + 回填）、`backend/api/listening.py`（pause 累加）、`backend/api/user.py`（info/stats 加字段）、`backend/utils/user_stats.py`（口径/活跃度）、`backend/utils/user.py`（add_bonus_xp）、新增 `backend/utils/level.py`
  - 前端：`frontend/src/components/user/ProfilePanel.vue`、`StatsPanel.vue`、`AppearancePanel.vue`、新增 `frontend/src/utils/level.js`
- 相似问题判定特征：
  1. "构思/规划一个大版本功能、写进 README 版本规划" → `ai/skill/20260810_big_version_planning_workflow.md`：README 对齐 → 现状盘点（只读落点文件）→ 数据来源表 → 可行性 → AskUserQuestion 决策确认 → 写 README → git 提交，**不写实现代码**
  2. "等级 / 经验 / 成长体系" → 经验作单一货币 + 纯函数实时推导等级 + 前后端同源共享（复用 scoreCalc ↔ score.py 模式）；平方根曲线 `level = floor(sqrt(xp / 3600))`
  3. "给 users 表加列 / 历史数据回填" → `information_schema.columns` 查缺列才 ALTER + 一次性回填 `SUM(listening_duration)`，幂等（复用 avatar 迁移模式）
  4. "听取时长统计 / 单位展示" → 后端存秒、前端转小时（`h + 1 位小数`）；总时长用持久化列（listening_total）防「删专辑掉数据」
  5. "每日限额 / 防刷" → `bonus_date + bonus_xp_today` 两列跨天自动重置，无需定时任务

## 二、原始问题描述
- 背景：v0.7 个人中心已完成（资料 / 外观 / 音乐统计）。v0.7.1 规划三个优化点：①个人用户界面加「等级-经验」体系，经验与听取总时长强相关；②统计展示优化（听取总时长转 h 显示、图表以 h 为单位、保留 1 位小数）；③外观栏蒙版透明度滑轨与按钮偏移的 CSS bug。
- 约束 / 决策依赖现状：
  - `users` 表现有 `level INT DEFAULT 0`（注释"等级/经验"）但只是静态数字，无经验体系、无经验字段；等级徽章只在 ProfilePanel 一处展示
  - 听取时长多处格式各异：StatsPanel「X小时Y分钟」/ AlbumItem「xxxhxxmin」/ AlbumBaseInfo / AlbumReviewEditor / AlbumCommentSection 各不同
  - v0.7 定的总时长 = `SUM(albums.listening_duration)`，**删专辑会掉**；`user_listening_log` 按天记录天然防删
  - 蒙版滑轨 `-webkit-appearance:none` + 6px 轨道 + 16px thumb，未做 margin-top 垂直居中补偿、填充渐变未按 thumb 宽度补偿

## 三、核心诉求
1. 等级经验制度：经验与听取总时长强相关，等级在个人资料页展示徽章 + 进度条 + 称号
2. 统计展示优化：听取总时长与近 N 天图表由「秒」统一改「小时」，保留 1 位小数
3. 蒙版透明度滑轨偏移 bug 修复
4. 补充：经验反馈（升级横幅 + +N 经验 toast）、总时长口径统一、连续收听天数 / 活跃度、滑轨数值气泡 / 刻度
5. 加分每日上限：除听取时长经验外，其余（评分 / 听后感 / 评论加分）每日合计上限 100

## 四、最终解决方案/改造步骤
1. **决策确认**（2026-08-11 拍板，AskUserQuestion 一次 4 问）：
   - 经验来源：听取为主（1 秒 = 1 XP，无上限）+ 听后感 +20 / 评论 +10 / 评分 +5（每日合计上限 100，不含收听）
   - 升级曲线：平方根 `level = floor(sqrt(xp / 3600))`，Lv.N 约需 N² 小时（示例：Lv.1=3600（1h）、Lv.2=14400（4h）、Lv.3=32400（9h）、Lv.5=90000（25h）、Lv.10=360000（100h））
   - XP 存储：新增 `users.xp` 列，暂停时累加，迁移时用 `SUM(listening_duration)` 一次性回填
   - 小时显示：统一 `h + 1 位小数`（不足 1 小时也显示 `0.4小时`）
2. **数据库**（users 表 3 处变更，同一次幂等迁移）：`xp`（经验货币）、`listening_total`（持久化总秒数）、`bonus_date DATE + bonus_xp_today FLOAT`（每日加分累计）；迁移回填 `xp = listening_total = SUM(listening_duration)`，只跑一次
3. **后端**：pause 接口 `xp += play_seconds`、`listening_total += play_seconds`，返回 `xp/level/level_up`；review/comment/score 成功走 `add_bonus_xp`（每日上限）；`/api/user/info` 返回 `xp/level/next_level_xp/xp_progress/level_title`；`/api/user/stats` 的 `total_duration` 改读 `users.listening_total`，新增 `current_streak`、`active_days_30`
4. **前端**：`frontend/src/utils/level.js`（与后端一致纯函数）；ProfilePanel 加进度条 + 称号 + 距下一级；StatsPanel 统一 h + 活跃度卡片；AppearancePanel 修滑轨 + 数值气泡 / 刻度；升级横幅 + +N 经验 toast（localStorage 记上次等级跨会话检测）
5. **分阶段路线**：P0 等级经验 + 反馈 → P1 统计优化 → P2 滑轨修复 + 体验

## 五、关键代码/配置/模板（可直接复用）
```python
# 等级纯函数（backend/utils/level.py，与 frontend/src/utils/level.js 同公式）
# 1 秒收听 = 1 XP；level = floor(sqrt(xp / 3600))
def compute_level(xp):
    return int((max(0, xp) / 3600) ** 0.5)

def xp_to_next_level(xp):
    level = compute_level(xp)
    return ((level + 1) ** 2 - level ** 2) * 3600  # 距下一级还差多少 XP

def level_progress(xp):  # 0-100 当前级内进度
    level = compute_level(xp)
    base = level * level * 3600
    span = ((level + 1) ** 2 - level ** 2) * 3600
    return (xp - base) / span * 100
```
```python
# 每日加分上限（backend/utils/user.py）
def add_bonus_xp(user_id, amount, daily_cap=100):
    # 读 users.bonus_date / bonus_xp_today；bonus_date != 今天 → 重置为今天、0
    remaining = daily_cap - bonus_xp_today
    actual = min(amount, max(0, remaining))
    if actual > 0:
        bonus_xp_today += actual
        xp += actual  # 同请求 UPDATE
    return actual  # 可为部分 / 0，前端据此 toast「+N 经验」
```
```python
# users 加列幂等迁移（复用 avatar 迁移模式，泛化列判断）
def ensure_users_xp_columns():
    # SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'
    # 缺列才 ALTER ADD COLUMN xp / listening_total / bonus_date / bonus_xp_today
    # 若 xp 列本轮刚新增（迁移前不存在）→ 循环各用户表回填
    #   xp = listening_total = COALESCE(SUM(listening_duration),0) FROM `albums_{uid}`
```
- 加分挂点：`POST /api/album/review/add`（+20）、`POST /api/album/comment/add`（+10）、`PUT /api/album/score/save`（+5），成功后一行 `add_bonus_xp`
- 升级反馈：接口返回 `level_up`，或前端对比 localStorage 记录的上次等级，升级弹横幅；`$message` 全局未注册需 `if (this.$message) {...} else alert(...)` 兜底
- 滑轨修复要点（按布局对齐工作流实测 rect 后改）：`-webkit-appearance:none` 下 thumb 需 `margin-top` 垂直居中补偿；轨道填充渐变起止点按 thumb 宽度偏移（值 0% 时渐变终点应 ≈ thumb 中心 8px）

## 六、踩坑点 & 注意事项（非常重要）
- **规划与实现分离**：大版本规划工作流只出方案 + 写 README，不写实现代码；实现待用户确认后按 feature_development_workflow 拆 P0
- **Edit 大段插入 README 前先确认锚点**：第一次插 v0.7.1 章节 old_string 匹配失败（漏了 `# 版本历史` 标题行）→ 浪费一轮。教训：插入点前先 Read 目标位置，或用最短唯一锚点
- **总时长口径不能两源相加**：`SUM(listening_duration)` 与 `user_listening_log` 写的是同一批秒数，相加=重复计数（v0.7 已定）；v0.7.1 改为 `listening_total` 持久化列，历史回填只跑一次，删专辑不掉
- **xp 与 listening_total 必须同源同累加**：唯一区别是加分只进 xp——否则「经验 vs 统计」两套数字打架
- **加分防刷**：评分防抖保存会频繁触发 → 单次 +5 且每日上限 100 双重约束可接受；听后感 / 评论只计「新增」不计「编辑」
- **每日上限重置**：`bonus_date` 与今天比对，跨天（含多天未登录）自动清零，无需定时任务
- **数据来源表函数名初稿写错**：加分函数是 `add_bonus_xp` 不是 `add_xp`（含剩余额度计算），整理 README 时修正——规划文档要全文一致性自查
- **滑轨偏移不凭肉眼猜**：按布局对齐工作流先 DevTools 实测 thumb / track rect，确认偏移方向与像素量再改 CSS，改后重测收敛 + 窄屏检查

## 七、同类问题快速适配规则
下次遇到相似问题，只需改：
- 【适配点1】新版本规划：直接贴 `20260810_big_version_planning_workflow.md` → README 对齐 → 只读落点文件 → AskUserQuestion 一次问 3-4 个决策（各给推荐项）→ 写版本章节 → git 提交
- 【适配点2】等级 / 成长体系：复制 level.py / level.js 平方根纯函数，改公式或阈值；xp 单一货币 + users 加列幂等迁移 + 历史回填
- 【适配点3】每日限额 / 防刷：复制 `bonus_date + bonus_xp_today` 跨天重置 + `add_bonus_xp`（remaining = cap - today，返回实际加分）
- 【适配点4】统计单位 / 口径：后端存秒、前端转 `h + 1 位小数`；总时长读持久化列（listening_total）防删专辑掉数据

## 八、优化复盘（2026-08-11 本次对话）
**流程效率**：按铁律先加载规划相关 skill，读 README 对齐 v0.7.1 现状，只读落点文件（ProfilePanel / StatsPanel / AppearancePanel / user.py / user_stats.py / listening.py / db.py），AskUserQuestion 一次 4 问拍板全部决策，随后写 README + 多轮 git 提交。规划工作流全程顺畅，决策确认这一步价值最大——没有来回拉扯，一次定稿。

**浪费点**：
1. **Edit 插入锚点失配**：插 v0.7.1 章节时 old_string 漏了 `# 版本历史` 标题行，第一轮 Edit 失败重试。教训：大段插入前先 Read 确认锚点，或用文件内最短唯一片段做锚
2. **现状盘点略冗余**：读完整组件（200-400 行）为确认「等级徽章 / 时长格式 / 滑轨 CSS」三处展示现状。规划阶段需要理解现状，可接受；但实现阶段应回到「Grep 精准定位 + 小范围 Read」，避免全量读
3. **补充想法扩展了范围**：「总时长口径统一」引出 `listening_total` 新列（数据库 1 处 → 3 处变更），且初稿把加分函数名写成 add_xp，整理 README 时统一修正。规划阶段允许范围扩展，但实现要严格按 README 最终版，避免带旧口径

**下次快速命中清单**：
- 规划模板：`20260810_big_version_planning_workflow.md`；决策确认用 AskUserQuestion（经验来源 / 升级曲线 / 存储 / 显示格式，一次 4 问）
- 可复用模式：平方根等级纯函数、`users` 加列幂等迁移 + 一次性回填、`bonus_date + bonus_xp_today` 每日上限、前后端一致纯函数共享（scoreCalc ↔ score.py 先例，v0.7.1 用 level.js ↔ level.py）
- 已记录可依赖事实：`users` 现有 `level INT` 无经验字段；`listening_duration` 与 `user_listening_log` 同源不可相加；蒙版滑轨 thumb 需 margin-top 补偿
- 完整规划见 `README.md` 版本历史「v0.7.1（规划完成，待实现）」章节
