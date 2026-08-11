# MusicRate

音乐专辑评分与发现的 Web 应用。给专辑打分、写听后感、管理播放列表、上传/解密音频，并通过标签与气泡图探索音乐。

- 界面以中文为主，风格标签格式为 `English【中文】`
- 前端 Vue 2.6，后端 Flask，数据库 MySQL 8

## 功能特性

- **专辑评分**：专辑整体评分 + 单曲逐首评分，加权计算总分（专辑 ×0.6 + 单曲均分 ×0.4）；打分即时防抖保存
- **听后感**：按时间戳记录听后感，附当时的评分与听取时长；日历组件展示历史打分足迹
- **公共专辑池**：共享专辑模板（搜索池）、跨用户评论、管理员维护模板并同步用户副本
- **播放列表**：歌单侧边栏，支持拖拽排序、三种播放模式、添加/删除/重命名歌单
- **音频资源**：上传本地音频替代在线资源；支持 MP3 / NCM / KGG / OGG 解密
- **每日推荐**：每天随机推荐一张池中专辑，并提取封面主色作为全局主题色
- **风格标签**：`English【中文】` 标签体系、层级树、气泡图展示关联风格
- **歌词**：LRC 歌词随播放进度滚动，支持上传歌词
- **专题周**：每周精选 7-10 张专辑的分享专题，配标签气泡图
- **个人中心**：头像上传、修改密码、等级经验（经验与听取时长强相关）、蒙版透明度调节、听取时长统计图表（近 N 天柱状图）
- **音乐足迹**：按天记录听取时长与听后感

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 2.6 + Vue Router 3（hash 模式）+ Vue CLI 5、Axios、ECharts 5 |
| 后端 | Python Flask + Flask-CORS、PyMySQL、bcrypt |
| 数据库 | MySQL 8（InnoDB，utf8mb4） |
| 音频工具 | ffmpeg，NCM / KGG / OGG 解密（`portable/`） |

## 快速开始

### 环境要求

- 已安装 MySQL 8（Windows 下由启动脚本自动拉起 `MySQL80` 服务）
- 项目自带便携 Python（`portable/python/python.exe`），无需单独安装 Python

### 启动后端

```bash
# 注意：便携 Python 的 cwd 不在 sys.path，必须用脚本文件方式启动（run.py 内部自带 sys.path.insert）
# 不要用 `python -m backend.run`，会报 ModuleNotFoundError: No module named 'backend'
PYTHONIOENCODING=utf-8 portable\python\python.exe backend/run.py
# 启动 Flask http://0.0.0.0:5000，Windows 下会自动启动 MySQL80 服务并初始化基础表
```

### 启动前端

```bash
cd frontend
npm install
npm run serve      # 开发服务器 http://localhost:8080
```

### 运行测试

```bash
portable\python\python.exe -m pytest                     # 快速单测（默认跳过 realdata）
portable\python\python.exe -m pytest -m realdata         # 真实 DB/网络集成测试
portable\python\python.exe -m pytest backend/tests/test_xxx.py -k 关键词   # 单文件/定向
```

## 项目结构

```
MusicRate/
├── backend/                  # Flask 后端
│   ├── run.py                # 启动入口（启动 MySQL80 → 初始化表 → 运行 Flask）
│   ├── config.py             # 全局配置（MySQL 凭据、路径、管理员默认值等）
│   ├── __init__.py           # 应用工厂 create_app()，注册 CORS / 路由
│   ├── api/                  # 路由模块，统一 register_*_routes(app) 注册
│   │   ├── auth.py           # 登录 / 注册
│   │   ├── album.py          # 用户专辑增删改查（私有副本）
│   │   ├── album_pool.py     # 公共专辑池（共享模板）
│   │   ├── score.py          # 评分读取 / 保存
│   │   ├── review.py         # 听后感
│   │   ├── comment.py        # 公共评论
│   │   ├── audio_resource.py # 音频上传 / 服务
│   │   ├── playlist.py       # 用户播放列表
│   │   ├── listening.py      # 听取时长记录
│   │   ├── recommend.py      # 每日推荐
│   │   ├── tags.py           # 风格标签及层级关系
│   │   ├── lyric.py          # 歌词（LRC）
│   │   ├── share.py          # 专题周
│   │   ├── unlock.py         # NCM / KGG / OGG 解密
│   │   ├── user.py           # 个人中心（信息 / 改密 / 头像 / 统计）
│   │   └── upload_utils.py   # 文件上传路由
│   └── utils/                # 共享工具
│       ├── db.py             # 数据库层：连接、分表、建表、init_base_tables()
│       ├── decorators.py     # @login_required 装饰器
│       ├── auth.py           # bcrypt 加解密
│       ├── score.py          # 评分加权计算
│       ├── json.py           # safe_json_loads（提取歌手/专辑/标签）
│       ├── user_stats.py     # 个人中心统计口径
│       ├── intro.py / last_listened.py / tag.py ...
│       └── unlock*.py        # ncm / kgg 解密逻辑
├── frontend/                 # Vue 2.6 前端
│   └── src/
│       ├── main.js           # 入口：路由、Axios 配置、认证拦截器、全局守卫
│       ├── config/index.js   # 标签气泡动画配置
│       ├── utils/scoreCalc.js# 前端评分计算（与后端逻辑一致）
│       ├── views/            # 页面级组件
│       │   ├── AlbumDetail.vue       # 专辑详情主页面（最大组件）
│       │   ├── AlbumPoolDetail.vue   # 公共池专辑详情
│       │   ├── TagDetail.vue         # 风格标签详情页
│       │   ├── WebHome.vue           # 发现音乐主页
│       │   └── LoginPage.vue / RegisterPage.vue
│       └── components/       # 按功能分组子组件
│           ├── albumDetail/   # 专辑信息/评论/歌词/听后感/曲目列表
│           ├── discoverMusic/ # 类型/每日推荐/专题/排行榜/歌手
│           ├── sidebar/       # 加专辑/加标签/编辑/音频上传/播放列表/解密
│           ├── myMusic/       # 音乐列表/播放列表/年度音乐
│           ├── searchMusic/   # 专辑池搜索
│           ├── item/          # 专辑卡片
│           ├── user/          # 个人中心（资料/外观/统计/头像）
│           ├── RhythmBall.vue # 节奏小球动画
│           └── TagBubbleChart.vue  # ECharts 气泡图
├── portable/                 # 便携 Python + 音频工具
├── ai/                       # 开发文档（skill 流程 / case notes / knowledge）
└── pytest.ini / requirements.txt
```

## 核心设计

### 前后端通信与认证

- 前端 `:8080`，后端 `:5000`，Axios `baseURL = 'http://localhost:5000'`，`withCredentials: true`
- Token 认证：`Authorization` 请求头传递，存于 `localStorage`；401 自动清除并跳转 `/login`
- CORS 仅允许 `localhost:8080` 来源；`@login_required` 校验 token 与 `users.token` 匹配

### 数据库模式

- **用户分表**：每个用户独立的 `albums_{user_id}` 表存私有专辑副本
- **共享表**：`album_pool`、`users`、`user_playlist`、`user_recommend`、`user_album_intro`、`album_tags`、`singers`、`album_singers`、`user_listening_log`
- **JSON 列**：`tracks`、`my_score`、`tags`、`favourite_tracks`、`tracks_time`、`playlist` 等以 TEXT 存 JSON
- **评分格式**：`[专辑整体评分, 单曲1评分, 单曲2评分, ...]`，0 表示未评分
- **管理员**：`users.is_admin=1`，拥有添加/编辑池专辑、标签、上传音频等专属功能

### 评分计算

- 总分 = `专辑整体评分 × 0.6 + 单曲均分 × 0.4`（评分为 0 的单曲不计入）
- 无有效单曲评分时，总分 = 专辑整体评分；范围 0–100，保留 1 位小数

---

# 版本历史

## v0.7.1 — 等级经验系统与统计展示优化（规划中）

> 承接 v0.7 个人中心，落地「等级-经验」体系（经验与听取总时长强相关）+ 听取时长统一以「小时」展示 + 修复外观栏蒙版透明度滑轨偏移 bug。**本版本为规划稿**：实现待确认后，按 `feature_development_workflow`（20260810）拆 P0 逐步落地。

### 功能概述

1. **等级经验制度**：经验与听取总时长强相关——听 1 秒 = 1 XP，辅以听后感 / 评论 / 评分小额加分；等级由经验按平方根曲线推导（Lv.N 约需 N² 小时），在个人资料页展示等级徽章 + 经验进度条 + 距下一级进度 + 等级称号；**配套经验反馈**：升级瞬间弹横幅、保存听后感 / 评论 / 评分成功 toast「+N 经验」
2. **统计展示优化**：听取总时长卡片与近 N 天柱状图由「秒」统一改为「小时」，小数点后保留 1 位；**总时长口径统一**（改读持久化 `users.listening_total`，删专辑不掉）；**新增活跃度**：连续收听天数 + 近 30 天活跃天数
3. **蒙版透明度滑轨偏移修复**：外观栏滑块轨道填充渐变与滑块按钮（thumb）位置不一致 + thumb 垂直方向相对轨道偏移的 CSS bug；顺手加拖动数值气泡与刻度线

### 已定决策（2026-08-11 拍板）

| 决策点 | 结论 |
|--------|------|
| 经验来源 | 听取时长为主（1 秒 = 1 XP）；听后感新增 +20、评论新增 +10、评分保存成功 +5 小额加分，不追溯历史 |
| 升级曲线 | 平方根：`level = floor(sqrt(xp / 3600))`，Lv.N 约需 N² 小时（1h→Lv1、4h→Lv2、9h→Lv3、100h→Lv10、400h→Lv20） |
| XP 存储 | 新增 `users.xp` 列；暂停时随 listening_duration 一起累加；迁移时用已有 `SUM(listening_duration)` 一次性回填初始经验 |
| 小时显示 | 听取时长统一 `h + 1 位小数`（不足 1 小时也显示如 `0.4小时`），总时长卡片与近 N 天图表一致 |
| 等级入口 | P0 先做个人资料页（徽章 + 进度条 + 称号）；头像旁 / 评论区扩展待定 |
| 加分防刷 | 仅计「新增 / 保存成功」一次，不做追溯；个人应用接受小额刷取风险 |
| 经验反馈 | 暂停 / 加分接口返回 xp、level、level_up；前端对比 localStorage 上次等级检测升级并弹横幅，加分接口返回本次 +N 供 toast |
| 总时长口径 | 新增 `users.listening_total` 持久化列（迁移回填 = `SUM(listening_duration)`，之后随 play_seconds 累加），总时长改读此列，删专辑不掉；`user_listening_log` 仅供图表 |
| 活跃度 | 连续收听天数（今天往回连续非 0）+ 近 30 天活跃天数，由 user_listening_log 纯函数计算 |
| 滑轨体验 | P2 修复时顺带：拖动时 thumb 上方数值气泡 + 0/25/60 刻度线 |

### 数据来源

| 数据 | 存哪 | 现成 or 需新建 | 查询接口 / 字段 |
|------|------|--------------|----------------|
| 听取总时长（秒） | `albums_{user_id}.listening_duration` | 现成 | SUM，`/api/user/stats` `total_duration` |
| 近N天听取（秒） | `user_listening_log.duration_seconds` | 现成 | `/api/user/stats` `daily_listening` |
| 经验 XP | `users.xp` | 需新建列 | 各接口累加 + 迁移回填 |
| 等级 / 进度 / 称号 | 由 xp 推导 | 需新建纯函数 | `computeLevel(xp)` 等 |
| 听后感 / 评论 / 评分加分 | `users.xp` | 需新建 | 各接口成功后 `add_xp()` |

### 架构设计

- **XP / 听取时长双列**：经验（xp，含加分）与持久化听取总时长（listening_total，纯收听）同源同累加——等级由 xp 实时推导、总时长展示读 listening_total，删专辑均不掉，保证「经验 vs 统计」不打架
- **纯函数共享**：`backend/utils/level.py` + `frontend/src/utils/level.js` 用同一套 `computeLevel(xp)` / `levelProgress(xp)` / `xpToNextLevel(xp)` / `levelTitle(level)`，复用 scoreCalc「前后端一致」既有模式，双端可单测
- **回填幂等**：`users.xp` / `users.listening_total` 两列迁移仅在「新加列的那一次启动」回填（循环各用户表 `SUM(listening_duration)`），重启不重复计数；之后收听在 pause 时都 `+= play_seconds`

### 数据库（2 处变更，同一次幂等迁移）

1. `users` 表新增 `xp` 列——经验货币（收听 1 秒 = 1 XP + 评分 / 听后感 / 评论加分）
2. `users` 表新增 `listening_total` 列——持久化听取总秒数（删专辑不掉）
- 幂等迁移：查 `information_schema.columns` 缺列则 `ALTER TABLE ADD COLUMN` 并一次性回填 `xp = listening_total = SUM(listening_duration)`，重启不重复计数，封装挂进 `init_base_tables()`（复用 avatar 迁移已验证模式）

### 后端接口

- `POST /api/album/listening/pause/<album_id>`（改）——成功后 `users.xp += play_seconds`、`users.listening_total += play_seconds`（与 listening_duration 同请求）；返回 `xp`、`level`、`level_up`
- `POST /api/album/review/add/<album_id>`（改）——成功后 `xp += 20`，返回 `xp_gained`
- `POST /api/album/comment/add/<album_id>`（改）——成功后 `xp += 10`，返回 `xp_gained`
- `PUT /api/album/score/save/<album_id>`（改）——成功后 `xp += 5`，返回 `xp_gained`
- `GET /api/user/info`（改）——返回 `xp`、`level`、`next_level_xp`、`xp_progress`、`level_title`
- `GET /api/user/stats`（改）——`total_duration` 改读 `users.listening_total`（不再 SUM albums.listening_duration）；新增 `current_streak`、`active_days_30`
- 加分收敛：`backend/utils/user.py` 新增 `add_xp(user_id, amount)` 公共函数（返回本次 +N），各接口成功后一行调用

### 前端组件

- `StatsPanel.vue`（改）——`formatDuration` 改 `h + 1 位小数`；近 N 天柱状图 y 轴 / 轴标签 / tooltip 秒 → 小时；新增连续收听天数 / 近 30 天活跃天数卡片
- `ProfilePanel.vue`（改）——Lv 徽章旁新增经验进度条 +「距下一级还差 X 经验」+ 等级称号；展示 `/api/user/info` 新增字段
- `AppearancePanel.vue`（改）——滑轨填充渐变按 thumb 宽度补偿 + thumb 垂直居中修正 + 拖动数值气泡 + 0/25/60 刻度线（先实测 rect 再改）
- 新建 `frontend/src/utils/level.js`——与后端一致的等级纯函数
- 升级横幅 / +N 经验 toast——复用全局 `$message`；localStorage 记上次等级，跨会话检测升级

### 分阶段路线

- **P0 等级经验 + 反馈**：users.xp / listening_total 迁移 + 回填 → level.py / level.js 纯函数（先单测）→ pause / 评分 / 听后感 / 评论挂加分 → 升级横幅 + +N 经验 toast → `/api/user/info` 加字段 → ProfilePanel 进度条 → realdata 验证
- **P1 统计优化**：StatsPanel 总时长 + 近 N 天图表全部 `h + 1 位小数`（纯前端）→ 总时长改读 listening_total（口径统一）→ 连续收听天数 / 近 30 天活跃天数（user_stats.py 纯函数 + 单测）
- **P2 滑轨修复 + 体验**：按布局对齐工作流先 DevTools 实测 thumb / track rect → 修 CSS（填充渐变补偿 + thumb 垂直居中）→ 拖动数值气泡 + 刻度线 → 重测收敛 → 窄屏检查

### 难点与对策

- **xp / listening_total 双列同源**：两者同一时刻回填 `SUM(listening_duration)`、pause 时都 `+= play_seconds`，唯一区别是加分只进 xp——回填只跑一次（幂等），删专辑均不掉
- **加分防刷**：评分防抖保存会频繁触发 → 单次加分值低（+5）可接受；听后感 / 评论只计「新增」不计「编辑」
- **滑轨偏移**：不凭肉眼猜，按布局对齐工作流实测 rect 后改；注意 `-webkit-appearance:none` 下 thumb 的 margin-top 补偿与渐变起止点按 thumb 宽度偏移
- **等级与统计一致性**：等级由 xp 纯函数实时推导，总时长读 listening_total，两列同源保证「经验 vs 统计」不打架

### 待做（勾选清单）

- [ ] P0 等级经验系统 + 经验反馈（升级横幅 + +N 经验 toast）
- [ ] P1 统计优化（h + 1 位小数 + 总时长口径统一 + 连续收听天数 / 活跃度）
- [ ] P2 蒙版滑轨偏移修复 + 拖动数值气泡 / 刻度线
- [ ] （补充）听取时长显示格式统一：AlbumItem / AlbumBaseInfo / AlbumReviewEditor / AlbumCommentSection 多处格式各异，抽公共 `utils/duration.js`
- [ ] （补充）等级徽章入口扩展：UserAvatar（WebHome 右上角）+ 评论区展示等级（待定）
- [ ] （补充）等级称号文案确认（如 Lv1-3 初听者 → Lv4-7 爱乐人 → Lv8-12 资深乐迷 → …）
- [ ] （补充，待用户继续补充）……

---

## v0.7 — 个人用户界面（已完成）

> 把 BookRate 的个人用户功能搬过来，落点为「用户播放歌曲时的播放列表侧边栏」——PlayerPlaylist.vue 与个人用户界面合并。

### 已实现

- P0 骨架：users.avatar 幂等迁移 + GET /api/user/info + POST /api/user/change-password + PlayerPlaylist「歌单/个人中心」模式切换 + UserCenter/ProfilePanel/UserAvatar + WebHome 右上角头像入口弹抽屉 ✅ 2026-08-10
- P1 设置：头像上传（复用 /api/upload_img）+ 蒙版透明度调节（AppearancePanel）+ 侧边栏样式美化（v0.6 遗留）✅ 2026-08-10
- P2 统计：user_listening_log 表 + listening.py 写按天记录 + GET /api/user/stats + StatsPanel ECharts 三图 ✅ 2026-08-10

### 已定决策（2026-08-10 拍板）

| 决策点 | 结论 |
|--------|------|
| 合并布局 | 侧边栏顶部加「歌单 / 个人中心」模式切换；歌单模式保留现有全部功能不动 |
| 主题 | 不做固定主题（MusicRate 主色来自封面动态提取），改做「蒙版透明度调节」 |
| 统计 | 做近 N 天听取时长柱状图 → 新增 `user_listening_log` 按天记录表 |
| 入口 | 抽公共 `UserCenter` 组件：嵌入 PlayerPlaylist 作 tab + WebHome 右上角「头像+用户名」弹同一抽屉 |
| AI 配置 | 不做（MusicRate 无 AI 功能，BookRate AI 是独立功能） |
| 头像 | 自定义上传（复用 `/api/upload_img`），未上传回退首字母圆形头像（同 BookRate） |

### 数据库（2 处变更）

1. `users` 表新增 `avatar` 列（VARCHAR(255) 存图片 URL）——幂等迁移：查 `information_schema.columns`，缺列则 `ALTER TABLE users ADD COLUMN avatar VARCHAR(255) DEFAULT ''`，封装函数挂进 `init_base_tables()`（复用 BookRate 已验证模式）
2. 新增 `user_listening_log` 表（近 N 天柱状图数据源）——`id`、`user_id`、`album_id`、`listen_date DATE`、`duration_seconds FLOAT`，`UNIQUE KEY(user_id, album_id, listen_date)` + `INDEX(user_id, listen_date)`；`listening.py` 的 pause 接口在更新 `listening_duration` 时同请求 upsert 按天记录

### 后端接口（backend/api/user.py，全部 @login_required）

- `GET /api/user/info` — 用户名/注册时间/等级/专辑数/头像/最近登录/会员（专辑数取 `albums_{user_id}` 实时 COUNT）
- `POST /api/user/change-password` — `{ oldPassword, newPassword }`，bcrypt 校验旧密码 + 更新
- `POST /api/user/avatar` — `{ avatarUrl }`，存 URL（图片上传复用 `/api/upload_img`）
- `GET /api/user/stats?days=7/14/30` — 统计聚合
- 蒙版调节：前端 localStorage 持久化即可，无后端接口

**统计口径**（防重复计数，参考 BookRate 经验）：

| 数据 | 来源 | 口径 |
|------|------|------|
| 专辑总数 | `albums_{user_id}` COUNT(*) | 全部 |
| 已评分 | `my_score` 数组含至少一个非 0 评分（0=未评分，全 0 数组不算） | — |
| 听取总时长 | `SUM(listening_duration)` | 以累计为准；**不与** `user_listening_log` 相加（同一秒数会写入两者，相加重复计数） |
| 听后感数 | `review` 非空且非 `[]` | — |
| 近N天听取时长 | `user_listening_log` 按 `listen_date` 分组累加 | 仅柱状图用 |
| 标签分布 | `albums_{user_id}.tags` 逐行解析前 8 个 | 气泡图 |
| 评分分布 | `my_score` 经 `calculate_album_total_score` 算总分后分桶（0 分不计入） | 柱状图；**不用** `albums.score` 列（那是评论均分，未评论的已评分专辑会漏） |

### 前端组件

- 改造 `PlayerPlaylist.vue`：顶部加「歌单 / 个人中心」模式切换；歌单模式原样保留（含拖拽/备份/防抖保存全部逻辑）
- 新建 `components/user/`：UserCenter / ProfilePanel / AppearancePanel / StatsPanel / UserAvatar
- `WebHome.vue` 右上角 `username + 退出登录` → 替换为 `UserAvatar`，点击弹出 `UserCenter` 独立抽屉

### 难点与对策

- **users 表加列无先例**：幂等 ALTER（同 BookRate v0.4），重复启动不报错
- **WebHome 无专辑播放上下文**：UserCenter 独立抽屉的主色取自 WebHome 当前主题（今日推荐封面取色）；蒙版调节全局 localStorage，两入口共享
- **关标签页丢 pause（遗留问题）**：直接关浏览器不会触发 pause，`listening_duration` 与按天记录都会漏 → v0.6 顺手在 `beforeunload` 补一次 pause 上报
- **「已评分」统计依赖 my_score 持久化**：评分若不即时保存统计会滞后 → v0.6 收尾已实现打分即时防抖保存（快照落盘），统计口径可直接依赖
- **ECharts 体积**：MusicRate 非 Electron，沿用 TagDetail.vue 全量引入即可，不必按需

### 测试

- 单测（纯逻辑，零依赖）：`test_user_stats.py`（统计口径纯函数）、`test_password.py`（改密码校验分支）、`test_user_table_migration.py`（avatar 幂等迁移）
- realdata（`-m realdata`）：`/api/user/info` 字段完整性、`/api/user/stats` 与 DB 聚合一致、listening pause 写入 `user_listening_log` 且 upsert 正确

---

## v0.6 — 歌词、专题周、音乐足迹

> 方便 B 站分享的新功能，以及日常修 bug 与收尾。

### 已完成

- 曲目列表下新增歌词页面；歌词像网易云那样随播放器进度条滚动，有按钮可上传歌词
- 音乐专题：右边日历表，左边本周专题，一般展示 7-10 个；新建专题表（专辑id、分享专题名、分享专题时间）
- 管理员显示添加按钮，弹侧边栏：下拉列表选标签 → 展示十年内未分享的专辑可选（仅管理员可编辑，每张专辑最近一年【内部调试可改无限年】只能添加一次）
- 发现音乐底下有歌曲分享栏目：左边每周主题，右边对应气泡图（该专题所有专辑的标签）
- 专辑专题封面渲染优化
- **收尾：提交评分**——打分时即时防抖保存（不再等离开页面/切歌才落盘；防抖快照避免切歌时把旧评分写进新专辑）
- **新增：我的音乐/专辑列表默认按「最近收听」排序**——albums 表新增 last_listened 字段，打开专辑详情页自动上报最近收听时间；从未收听的专辑固定排最后

---

## v0.5 — 数据迁移、音频上传与解密

> 整理数据格式，方便部署。

- 上传本地音频替代网上音频（避免不了版权问题，放弃）
- 图片保存逻辑重构（初始化时一键修改，把 url 拆开）
- 整体评分改成滚动，能打满分；单曲列表打分区域可用鼠标滚轮调整分数
- 提醒重复添加时可跳转到指定 album 详情页
- 按听取时长排序；我的分类排序
- add / edit 仅管理员可操作；AddAlbum 做成子组件改为左侧侧边栏
- 点击专辑名 / 封面都能跳转
- 一键启动，添加桌面图标
- 23 / 24 / 25 年专辑数据迁移
- 气泡图显示英文
- 管理员编辑时可同步简介和时长类型；简介为空也同步，时长类型强制同步
- 播放列表极低概率清空问题；歌单可拖动换位置；评分排序与显示问题
- 可搜索标签（两个框，不需要搜索按钮）
- 我的用户里的添加时间修改
- 上传音频脚本整合（mp3 合并）
- ncm 格式破解
- 听后感的滞后问题；喜欢时刻的保存问题

---

## v0.4 — 发现音乐主页与每日推荐

> 为后续的音乐类型、歌手、推荐算法等铺路。

- 搜索池专辑名/歌手排序问题与分页
- Tab 页面：发现音乐 / 我的音乐 / 最右上角用户名；发现音乐 Tab 含今日推荐 / 排行榜 / 音乐类型 / 歌手
- 新建 `user_recommend` 表（用户id、recommend_daily_id 查询 album_pool 取专辑详情）；登录时判断是否过一天（对比 users.last_login 时间），过了则随机从 album_pool 选一个 id 替换作为今日推荐；刚登录跳转到今日推荐页面
- 今日推荐按钮：复制到本地 + 切换按钮（随机换池中专辑写入用户表），提取主颜色 / 模糊化背景
- 返回专辑列表时模糊化封面背景加载问题
- 听后感日历非当天高亮形状改圆形
- 搜索池专辑详情单曲列表进度条样式；专辑简介下拉框样式
- 主页面/搜索池背景与页面颜色跟随今日推荐专辑及主色
- 切换当日推荐专辑按钮美化

---

## v0.3 — 听取时长与评分完善

### 已完成

- 专辑播放记录听取时长，暂停和结束都会停止并更新数据库
- 本地调试不影响正在使用的网站（copy 一份测试环境）
- 专辑类型 EP / LP / Single / Mix / Com 等
- 专辑搜索池小列表：标签显示所有人的 tags（气泡图里 tags 排行前 5）；显示时长类型
- 基础信息显示 bug（简介过长被挤下去，编辑时正常）
- 用户复制到私有查重（专辑名-歌手-发行年份）
- 用户评论加蒙版，排序方式不要蒙版要颜色加重
- 把 allTagOption 放在 config 里
- 暂停时进度条变 0 的偶发 bug
- 气泡图改成透明
- 退出登录保存当前听的歌和进度，下次登录继续
- 专辑列表排序加「按添加时间排序」；专辑列表 / 专辑搜索池类型搜索单放一个搜索框
- 专辑搜索池只显示最近添加的十个；样式再挤一些
- 正在播放专辑的着重显示、current_playlist_id 问题（应为 0,1,2 这种）
- 标签包含更多信息
- 时间戳支持超过 99:99（有的可能两个小时）
- 单曲列表栏可切换成个人喜欢时刻表；添加喜欢时刻（与编辑曲目同逻辑），点击快速跳转
- 单曲列表栏右侧上半部分个人感觉评分，下半部分节奏模块固定大小和位置
- 添加评分，用进度条显示；单曲环节内容完善，每个单曲评分存成 `[数组]my_score`
- 单曲列表时间显示单曲时间，计算放幕后
- 保存时间戳重置评分问题；评分的特殊计算
- 节奏小球颜色/空白显示问题
- 单曲列表美化；歌名过长横向自动滚动显示
- 评分进度表加粗
- 个人感觉评分圆按住变大的速率调慢，变到最大再变小循环往复
- 评论区美化；切换歌曲时读取对应评分
- 发送评论时左上角记录听取时长
- 点赞和屏蔽样式美化（SVG）
- 听后感新增时记录当前评分与听取时长，显示在听后感右上角（存 review）；格式：左上 时间-评分（点击弹出评分细则）、右下 删除、左下 听取时长
- 听后感左边日历小组件，显示写听后感情况（用户列表内所有专辑）；有评分的日期高亮；点击某天显示评分列表，记录历史总得分
- 听后感栏美化：日历框缩小、历史按时间倒序、删除 `[.mp3]` 与 `——听后感` 文案、输入框与历史模块换位置
- 搜类型不能匹配【中文】问题
- 添加时间排序问题
- 专辑搜索池搜索后的排序与分页
- 保存喜欢时间戳评分清零（要先保存评分再保存时间戳）
- 听后感详情列表按从小到大排序
- 听后感渲染半秒延迟优化
- 暂停和切歌时声音逐渐消失，不一下断开
- 听后感页面文案修改

---

## v0.2 — 专辑详情页优化

> 主要特点是评分的特殊加权计算。

### 完成

- 管理员更新时用户分类消失问题；管理员删除时全部删除
- 公共专辑详情的字删掉；简介放左边第二页，单曲列表放原简介位置，右边新增最近收听用户和专辑风格（全网用户标签统计）
- 读取专辑封面作为背景，提取主要颜色作为按钮
- 公共区评论页面优化
- 整轨欣赏放最上边：右上角获取按钮弹侧边栏，支持上传 mp3（可拖拽）；上传后显示音乐进度条（播放/暂停/音量），未上传显示暂无资源；仅管理员显示上传按键；上传后的歌曲有 URL，数据存在 `backend/data/album_track`，URL 与整轨时长存入 album_pool；其他用户自动读取 URL；管理员删除音频按钮（防侵权）；管理员删除模板时同步删除云端歌曲
- 曲目列表歌名 copy/新建时未读取问题
- 曲目列表样式美化：单曲后加时间戳（用户自定义，模板不设置）
- 曲目列表右上角编辑按钮，可编辑单曲个数/名字/时间戳并保存到自己的数据库
- 点击时间戳最上方整轨音频跳转；整轨音频放在详情页最下端
- 专辑封面剪切成圆环形旋转，放最右下方
- 播放器格式美化，颜色统一，基础信息布局同步修改

### 播放列表

- 默认列表 + 加号 + 删除，横着摆放
- 播放列表按钮弹侧边栏：上半部分播放列表（播放模式：单曲循环/随机循环/顺序播放 + 移除全部），下半部分用户所有有效音频的专辑（搜索框 + 按添加时间/名称/评分/歌手排序 + 添加全部）
- 只支持整张专辑播放；播放模式改成小图标切换，放清空歌单左边；原三栏变成添加时间/名称/评分排序
- 支持点击添加和拖拽添加，上半部分支持点击/拖拽删除；下方只显示专辑名、歌手和评分
- 播放逻辑：退出侧边栏播放当前页面歌，刚打开页面也播放当前页面歌
- 排序切换；自定义排序时可拖拽调整顺序，其他排序下拖拽转化为自定义排序（未解决，只要自定义排序）

**实现思路**：打开侧边栏 → 找 `Album_{userID}` 表所有专辑的 `source_pool_id` → 查 album_pool 里 `mp3_url` 非空的 → 再提取对应 score/album_name/created_at/source_pool_id/singer。`user_playlist` 表存 `user_id` + 二维数组 `[播放列表名][[album_id 数组]]` + `current_album_id` + `current_playlist_id`；初始化元素 `[['默认列表'],[[]],0]`。播放完成后按列表逻辑切下一张，判断是否到达播放列表边界。

---

## v0.1 — 搜索池与权限

> 评论共享（听后感不可见），初用户/次用户新建专辑逻辑，表结构重构。

- 表结构重构；后端 app.py 分离
- 新建专辑逻辑（初用户-次用户）；初用户建立专辑内容（单曲修改）
- 用户表重构，增加权限；仅管理员可删除搜索池专辑
- 评论共享；一个用户每个专辑只能评论一次；评论仅自己和管理员可删除；自己的评论默认最上层，可按时长/点赞数/时间排序
- 搜索池创建用户从用户 id 改为用户名
- 管理员查看详情后右上角出现修改按钮，可改专辑名/图片等；修改模板后同步用户数据
- 添加新专辑内容完善（专辑名/封面/歌手/发行年份/曲目数量 → 依次填写曲目列表）
- 专辑详情页优化：基础信息表格类别为所有拥有该专辑用户的气泡图（只显示比例 10% 以上的 tags），含创作者和发行时间以及 tags
- 管理员删除池子时删除本地照片
- 同步逻辑强制同步专辑名、歌手和发行时间
- 用户新建专辑 source_pool_id 未赋值问题（copy 时正常）
- 新建专辑防重复（专辑名+歌手+发行时间）
- 同步按钮出现位置奇怪，已注释
- 专辑简介作为新建的一栏

---

## v0.0 — 静态音乐列表原型

> 简单的静态音乐列表画面。

- 静态音乐列表页面（HTML/CSS）
- Vue 实现评分/评论交互（假数据）
- 新增用户登录功能；多用户登录
- Flask 接口对接，评论/评分存 JSON
- 添加专辑页面
- 替换 JSON 为 SQLite，再替换为 MySQL
- 用户 id 进行分表
- 专辑封面问题：创建新专辑时复制图片代替 URL
- 专辑列表的评论隐藏，放在平台评论里
- 听后感新增按钮，每次时间戳的听后感单独保存、单独删除
- 专辑列表排序和分页功能

---

# 开发规划

## 待做

- 后续类别直接读表，不需要自定义
- 用户自定义封面（封面文件存本地），可点击恢复原封面（把 `Album_{用户id}` 表新增的 fav_cover 改回空值）
- 用户侧边栏加调蒙版度功能（含专辑详情页那种，不要侧边栏）
- 播放列表可调整歌单、分享导出精美 PDF（用户可设置歌单是否可见，新建时可选择）
- 搜索音乐底下 tab 增加歌单搜索（搜用户名/用户 id/歌单名；默认歌单默认不可见）

## 暂不解决

**读取正在播放音乐的节奏（pass）**
- 节奏可视化组件正确显示当前音乐节奏；先用简单渐变复原波形，以后再复杂化
- 单曲列表：序号-单曲歌名-打分-（小球带渐变拖尾-贪吃蛇，跟着节奏和语速转弯前进、遇壁回弹；组件类型和权重与用户主要标签对接），仅编辑曲目时显示单曲时间戳

**独立播放组件（pass，有点难改）**
- 播放组件抽出来，干其他事时继续听
- 点击其他专辑时间戳会提醒非当前专辑、不跳转
- 退出登录时关闭；返回专辑列表/搜索专辑池不停播放
- 搜索池和用户界面背景为当前听的模糊版，按钮颜色为主色

**后续大版本**
- 歌手属性引入：歌手页面完善，显示搜索池里该歌手专辑和我听过的
- 歌词滚动另开板块「歌词本」：单曲列表可展开，上传歌词并随音乐滚动
- 本地 mp3 和其他听歌平台联动跳转，避免侵权
- 用户养成：邮箱注册、用户名、头像（仅封面库）；用户顶号；听专辑等级、账号头像、信息通知；可查看别人的音乐列表
- 推荐算法：搜索池显示符合用户画像的推荐专辑；年度总结报告（添加歌曲/喜欢，生成好看的图）；每日推荐算法
- 手机端适配
- 盈利模式：专辑打榜（细则在 obsidian）

---

# 开发指引

- 开发新功能前，先阅读 `ai/skill/` 下的规则文件：
  - `20260810_feature_development_workflow.md` — 开发流程
  - `20260810_testing_workflow.md` — 测试流程（测试先行）
  - `20260810_big_version_planning_workflow.md` — 大版本规划
- 历史排查案例见 `ai_case_notes/`，技术笔记见 `knowledge/`
