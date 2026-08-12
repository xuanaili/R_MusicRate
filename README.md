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

---

---

## v0.8.3 — 歌词样式统一 + AI 助手 BPM 预触发（规划已定稿）

> 承接 v0.8.1 AI 系列的两个体验收尾 + 把 v0.8 歌词遗留待办并入：① 解决 AI 助手「首次提问才开始分析 BPM」的滞后——打开专辑详情页 / AI 助手 tab 即预触发节奏分析（幂等），提问不再首问必「节奏分析中」；② 歌词展示页样式一致性美化——修复单曲歌名标题选择器失配（模板 `<h2>`、CSS 却是 `.fixed-track-title h3`，歌名一直无样式）与全页硬编码颜色主题化，顺带修 v0.8 遗留三件（当前句抖动 / 长歌词省略号 / `parseTimeStr` 小数精度）。规划于 2026-08-12 定稿（**注：v0.8.2 未在 README 留档，直接规划 v0.8.3**），实现按 `feature_development_workflow`（20260810）+ `testing_workflow`（20260810）成对拆 P0→P2 落地。

### 功能概述

1. **BPM 预触发（消除滞后）**：新增任意登录用户可用的 get-or-trigger 接口 `POST /api/ai/tempo/ensure/<album_pool_id>`；前端在**专辑详情页打开**（`getAlbumDetail` 成功）与 **AI 助手 tab 打开**（`created()`）两个时机各调一次，幂等防重复（`album_tempo` 缓存短路 + `tasks.find_active`）。AI 助手页显示「节奏分析中…」提示条并轮询就绪。`chat` 接口在 tempo 缺失/分析中时**照常回答**（暂缺【单曲节奏 BPM】段，不再返回「节奏分析中」占位），BPM 就绪后自动带上。
2. **歌词展示页样式统一**：修复歌名标题 `<h2>` 与 CSS `.fixed-track-title h3` 选择器失配 bug（歌名一直无样式）；歌词页硬编码 `#333/#666/#888/#999` 统一收敛到主题色三档（`mainColorDarkDouble` 高亮/时间/歌名、`mainColorDark` 下划线/按钮/激活项、`mainColor`/`White` 按钮/进度条）。
3. **v0.8 遗留三件并入**：当前句抖动（字号动画与滚动目标 offsetTop 反馈循环）、长歌词省略号（`.lyric-text` nowrap 撑破居中布局）、`parseTimeStr` 小数 `/1000` 不自洽（`00:05.5` 被解析成 5.005s）。
4. **其他优化并入**：听取时长显示格式统一（抽公共 `utils/duration.js`，v0.7.1 遗留）；`album_pool.tracks_time` DDL 漂移统一（v0.8 遗留）。

### 已定决策（2026-08-12 拍板）

| 决策点 | 结论 |
|--------|------|
| BPM 预触发时机 | **专辑详情页打开 + AI 助手 tab 打开都触发**；幂等不重复（缓存短路 + find_active） |
| BPM 触发权限 | **任意登录用户**（新增 ensure 接口）；BPM 为 album_pool 级共享缓存非私有数据；serial_lock 串行 + find_active 防重复控滥用 |
| 分析中提问行为 | **照常回答**（暂缺 BPM 段），不再返回「节奏分析中」占位；BPM 就绪后自动带上 |
| 歌词美化范围 | **全量样式统一**（歌名 h2 修复 + 全页主题化 + v0.8 遗留三件一起修） |

### 数据来源

| 数据 | 存哪 | 现成 or 需新建 | 查询接口 / 字段 |
|------|------|--------------|----------------|
| 每曲 BPM / 节奏结构 | `album_tempo`（album_pool_id 唯一） | 现成 | ensure 短路判断 + chat 上下文 |
| 整轨 mp3 是否可分析 | `album_pool.mp3_url` + 磁盘存在性 | 现成 | `_resolve_audio_path` |
| 活跃 tempo 任务 | `tasks`（内存任务表） | 现成 | `find_active(kind='tempo')` |
| 歌词展示样式 | `AlbumLyricViewer.vue`（前端纯样式） | 现成 | — |
| 听取时长格式 | 前端 4 组件各写一遍 | 需抽公共 | `utils/duration.js` |

### 架构设计

- **ensure get-or-trigger**：`backend/api/tempo_ai.py` 新增 `ensure_tempo(app, album_pool_id, user_id)` 帮助函数——① `album_tempo` 已有 → `{ready:true}`；② 有活跃 tempo 任务 → `{ready:false, analyzing:true, task_id}`；③ 否则 `start_tempo_task` → `{ready:false, analyzing:true, task_id}`；池不存在 404 / 无 mp3 → `{ready:false, has_mp3:false}`（前端忽略）。路由 `POST /api/ai/tempo/ensure/<album_pool_id>` 仅 `@login_required`（任意登录用户，不再校验 is_admin）
- **chat 语义变更**：`ai_chat()` 的懒分析分支删除「返回占位 JSON」，改为「tempo 缺失 + 有 mp3 → 触发 ensure（防重复）+ 照常走 SSE/非流式回答（`format_tempo(None)` → 无 BPM 段）」；前端 `tempo_analyzing` JSON 分支随之删除
- **前端预触发**：`AlbumDetail.vue` `getAlbumDetail` 成功后调 ensure；`AlbumAIAssistant.vue` `created()` 调 ensure + 若 `analyzing` 显示顶部提示条「⏳ 正在分析专辑节奏（BPM）…」并轮询 `GET /api/ai/tempo/status/<task_id>`（~4s）就绪后隐藏（beforeDestroy 清定时器）
- **歌词样式统一**：AlbumLyricViewer 颜色收敛三档主题色；`.fixed-track-title` 选择器改对（`h2`）；`.lyric-text` 长行改约束换行；`getLyricItemStyle` + `scrollToCurrentCombinedLyric` 改稳定滚动锚点
- **parseTimeStr 精度**：按小数位数 `/10`（1位）/`/100`（2位）/`/1000`（3位），对齐 `parseLrcToStandardFormat` 已正确实现

### 数据库

v0.8.3 **无新增表**。`album_pool.tracks_time` 建表 DDL 补默认值 `'[]'`（漂移统一，幂等 CREATE 只影响新表；线上库不强制迁移）。

### 后端接口

- `POST /api/ai/tempo/ensure/<album_pool_id>`（新增，任意登录用户）——get-or-trigger，见架构设计
- `POST /api/ai/tempo/analyze/<album_pool_id>`（保持）——管理员手动触发入口不变
- `GET /api/ai/tempo/status/<task_id>`（保持）——前端提示条就绪检测复用
- `POST /api/ai/chat`（改）——tempo 缺失分支由「返回占位」改为「触发 ensure + 照常回答（无 BPM 段）」

### 前端组件

- `views/AlbumDetail.vue`（改）——`getAlbumDetail` 成功后预触发 ensure
- `components/albumDetail/AlbumAIAssistant.vue`（改）——`created()` ensure + 节奏分析中提示条 + 轮询就绪隐藏；删 `tempo_analyzing` JSON 分支
- `components/albumDetail/AlbumLyricViewer.vue`（改）——h2 歌名样式 + 全页颜色主题化 + 修抖动/省略号/parseTimeStr
- `utils/duration.js`（新增）+ `item/AlbumItem.vue`、`albumDetail/AlbumBaseInfo.vue`、`albumDetail/AlbumReviewEditor.vue`、`albumDetail/AlbumCommentSection.vue`（改）——听取时长格式统一

### 分阶段路线

- **P0 歌词展示页样式统一**：h2 选择器修复 + 全页颜色主题化 → `parseTimeStr` 精度修复 → 长歌词省略号 → 当前句抖动 → 单测（`parseTimeStr` 纯函数可测）+ `npm run lint` + 手动回归 ✅ 2026-08-12
- **P1 BPM 预触发**：`ensure_tempo` 帮助函数 + ensure 路由 + chat 改照常回答 → 单测 + realdata（test_ai_chat_realdata 懒分析断言同步更新）→ 前端 AlbumDetail + AlbumAIAssistant 预触发 + 提示条轮询 → lint + 手动回归 ✅ 2026-08-12
- **P2 其他优化**：`duration.js` 抽取统一 4 处格式 → `album_pool.tracks_time` DDL 漂移统一 → realdata + 回归

### 难点与对策

- **多时机预触发防重**：ensure 短路（`album_tempo` 已有即 ready）+ `find_active(kind='tempo', album_pool_id)` 防重复启动；AlbumDetail 与 AI tab 两次触发不冲突
- **非管理员触发滥用**：serial_lock 全局串行（CPU 同一时间只跑一个后台任务）+ 每专辑分析一次即缓存 → 滥用收益极低，可接受
- **chat 语义变更回归**：v0.8.1 realdata 断言「tempo 缺失返回 tempo_analyzing」需同步改为「照常回答且 system 无 BPM 段 + ensure 被调用」；AI 无 BPM 上下文时基于其他段作答，信息不足会如实告知（prompt 已约束）
- **抖动修复**：根因是字号随距离动画改变每行 offsetTop，滚动目标漂移 → 用「index × 固定行高」作稳定锚点或动画结束二次定位，避免反馈循环
- **parseTimeStr 精度**：与 `parseLrcToStandardFormat` 对齐按位数除，双端行为一致；顺带校验 `formatTime`/`formatTimeForOutput` round-trip

### 待做（勾选清单）

- [x] P0 歌名 h2 选择器修复 + 歌词页颜色主题化 ✅ 2026-08-12
- [x] P0 `parseTimeStr` 小数精度修复（对齐 parseLrcToStandardFormat）✅ 2026-08-12
- [x] P0 长歌词省略号撑破布局修复 ✅ 2026-08-12
- [x] P0 当前句抖动修复 ✅ 2026-08-12
- [x] P1 `ensure` 接口 + chat 改照常回答 + 单测/realdata ✅ 2026-08-12
- [x] P1 前端双时机预触发 + 提示条轮询 ✅ 2026-08-12
- [ ] P2 `utils/duration.js` 抽取统一 4 处格式
- [ ] P2 `album_pool.tracks_time` DDL 漂移统一

## v0.8.1 — AI 系列：歌词识别正式管线 + AI 助手（P0-P6 已完成）

> 承接 v0.8 P1 spike 评估结论（草稿级可行），正式落地 AI 歌词识别管线：管理员对已有整轨 mp3 的专辑触发识别 → faster-whisper（small，VAD 关）产出草稿歌词 + 时间戳 → 幻觉过滤 + OpenCC 繁转简 → DeepSeek 校正（difflib 保时间戳）→ 整轨绝对时间存储文本落 `album_lyric`，前端按 `tracks_time` 自动切分。规划于 2026-08-12 用户拍板落地；2026-08-12 补充更新：**个人中心 AI key 配置 + 专辑详情「AI 助手」子页面 + BPM 节奏分析**，并入本版本扩成「AI 系列」。实现按 `feature_development_workflow`（20260810）+ `testing_workflow`（20260810）成对拆 P0→P6 落地；**P0 识别器升级、P1 异步任务 + 接口、P2 DeepSeek 校正 + 前端按钮、P3 AI key 配置（个人中心）、P4 BPM 节奏分析（tempo_analyzer + album_tempo 缓存 + 异步任务，与歌词识别共用同一任务表串行）已完成（2026-08-12）**。2026-08-12 增补：**AI 识别整轨进度条（实时转写进度）+ 添加专辑自动触发识别**（管理员添加带整轨 mp3 的专辑时自动启动识别，省得每次手动再识别一次）。2026-08-12 增补：**平台参考歌词辅助校正**——DeepSeek 校正环节按曲目实时拉取网易云/酷狗/QQ 官方歌词作纠错参考，专治中文同音错字（参考仅用于消歧，不改草稿行文与时间戳）。2026-08-12 增补：**P5 AI 助手后端**——`ai_conversation` / `ai_quota` 表 + 上下文组装（专辑/歌手/评分/听后感/标签/BPM/当前歌歌词/平台评论/全网听后感，纯函数放 `ai_context.py` 可单测）+ OpenAI 兼容 chat（deepseek/openai）+ SSE 流式 + 配额（提问成功才计数）+ 会话按 user+album_pool_id 持久化；BPM 懒分析（tempo 缺失 + 有整轨 mp3 → 异步触发分析返回「节奏分析中」，防重复用 `tasks.find_active(kind='tempo')`）完成（2026-08-12）。2026-08-12 增补：**P6 AI 助手前端**——`AlbumAIAssistant.vue` 专辑详情子页（消息列表用户气泡/AI markdown 气泡 + 空态引导问题 + 底部 textarea Enter 发送/Shift+Enter 换行 + SSE 流式渲染原生 fetch/ReadableStream + 思考中动画 + 单条删除 + 重置对话）+ `AlbumDetail.vue` 左侧菜单「AI 助手」入口（`/api/ai/status` has_key 显隐）+ 前端新增 `markdown-it`（`html:false` 防 XSS）完成（2026-08-12）。

### 功能概述

1. **识别触发**：管理员在歌词展示页歌名标题栏左侧点「AI 识别歌词」（按钮已移出歌词弹窗，与右上「上传/编辑歌词」按钮对称放左侧、悬停才显示，仅歌词展示页；轮询挂在常驻父组件 `AlbumDetail.vue` → 切到听后感/评论/其他子页面时识别持续，进度条在标题栏下方实时可见）→ 后台异步识别（RTF 0.18，44min 专辑 ≈ 8min，串行任务队列）→ 完成落库；**自动触发**——管理员通过「添加专辑」提交带整轨 mp3 的新专辑时，后端自动启动识别（响应 `recognize_task_id`，失败不影响添加）
2. **草稿产出**：faster-whisper small（CPU int8，VAD 关）→ 幻觉过滤（no_speech_prob 阈值 + 噪音模式 + 器乐标签滤除）→ OpenCC 繁→简 → 按 `tracks_time` 切分验证；**进度实时上报**——转写阶段按 `segment.end / 音频总时长` 逐段回调，任务 `progress` 10→90 平滑推进 + 阶段 message，前端进度条展示
3. **DeepSeek 校正**：以 whisper 逐行 `mm:ss.x 文本` 为锚，强制保行数/行序/时间戳只改文字，difflib.SequenceMatcher 处理行数变化再对齐回时间戳
4. **AI key 配置**：个人中心新增「AI 配置」tab（镜像 BookRate `AISettingsTab`）——服务商下拉（deepseek 默认 + openai）+ API 密钥，key 明文存后端 `ai_key` 表（按 user_id 唯一），前端只存「是否已配置」布尔、绝不返回明文；状态徽章 + 今日用量
5. **BPM 节奏分析**：为 AI 助手提供「歌曲节奏」数据——librosa 对整轨 mp3 做节奏分析，按 `tracks_time` 切分得每曲 BPM + 整专节奏结构，结果缓存 `album_tempo` 表（按 album_pool_id）；异步任务分析（与歌词识别共用同一内存任务表实例，serial_lock 全局唯一保证 CPU 串行）
6. **AI 助手**：专辑详情左侧菜单新增「AI 助手」子页（与听后感/平台评论同级，**非** BookRate 的侧边栏形态），仅配置 key 的用户可见——AI 依据用户对这张专辑的所有听后感、当前播放歌曲的歌词、单曲节奏（BPM）、歌手信息、专辑信息、平台评论、全网听后感精选，与用户讨论整张专辑的感受；SSE 流式输出，对话历史按 user + album_pool_id 持久化
7. **定位与覆盖**：识别产物是「草稿」，管理员可再用官方歌词上传/手动编辑覆盖（复用 v0.8 P0 的 save/upload 落库路径）
8. **平台参考歌词辅助校正**：DeepSeek 校正环节按曲目标题+歌手实时拉取网易云/酷狗/QQ 官方歌词作参考（网易云优先 → 酷狗 → QQ 逐级兜底，每曲取第一个成功平台）——参考文本仅作纠错参考注入校正 prompt（消除同音字/错字/断句歧义），**不改草稿行文与时间戳**；拉取失败/无参考时校正行为与无此功能完全一致；**不缓存，现拉现用**（无新表）

### 已定决策（2026-08-12 拍板）

| 决策点 | 结论 |
|--------|------|
| 正式管线 | **落地**（用户拍板，spike 验证通过）；含简体转换 + 幻觉过滤 + DeepSeek 校正 |
| 模型 | small（CPU int8，RTF 0.19 可接受）；如需更快降 base（RTF ~0.09，质量略低） |
| VAD | **关闭**（spike 证明音乐场景过度过滤导致曲目整首丢失）；幻觉靠 no_speech_prob + 噪音模式过滤 |
| 简体 | faster-whisper 输出繁体 → **OpenCC t2s** 转简体落库（全站存储/显示统一简体） |
| DeepSeek 校正 | 正式阶段做，需 **config.py 服务器端 `DEEPSEEK_API_KEY`**（用户拍板保留服务器端，与个人用户 AI key 分开两套）；whisper 时间戳为锚，只改文字不改时间，difflib 对齐兜底 |
| 异步 | 单机后台线程 + 内存任务表（spike 规模够用，不引 Redis）；识别/分析串行化，避免 CPU 100% 抢占 |
| 触发入口 | **歌词展示页歌名标题栏左侧「AI 识别歌词」按钮**（仅管理员，复用 is_admin 口径），已完成弹窗迁出——与右上「上传/编辑歌词」按钮对称放左侧、悬停才显示，仅歌词展示页；轮询挂在常驻父组件 `AlbumDetail.vue`，切换子页面识别持续 |
| 产物存储 | 复用 `album_lyric`（整轨绝对时间存储格式，前端按 tracks_time 切分），无新表 |
| **AI key 配置** | **并入 v0.8.1**（用户拍板扩成 AI 系列）；个人中心「AI 配置」tab 镜像 BookRate `AISettingsTab`——服务商 deepseek（默认，国内直连）+ openai，key 明文存后端 `ai_key` 表按 user_id 唯一，前端只存 has_key 布尔、绝不返回明文 |
| **DeepSeek 校正 key 来源** | **保留服务器端 config.py `DEEPSEEK_API_KEY`**（用户拍板）；歌词识别是管理员专属操作，与个人用户 AI key 分离两套 |
| **BPM 节奏** | **新增 BPM 音频分析**（用户拍板）——librosa 提取每曲 BPM + 节奏结构，`album_tempo` 表缓存；解决全库原本无节拍数据缺口（原有 tracks_time 单曲边界 + mp3_duration 仅时长结构） |
| **AI 助手形态** | 专辑详情**左侧菜单新增「AI 助手」子页**（与听后感/平台评论同级），非 BookRate 侧边栏形态；仅配置 key 的用户显示该菜单项 |
| **AI 助手上下文** | **含平台评论 + 全网听后感精选**（用户拍板镜像 BookRate）：用户本专辑听后感/评分/标签 + 专辑信息 + 歌手信息 + 当前歌歌词 + 单曲 BPM 节奏 + 平台评论 + 其他用户听后感精选 |
| **AI 对话历史** | `ai_conversation` 按 user + album_pool_id 持久化，**成功才落库**（失败/中断不留半会话，镜像 BookRate 踩坑）；`ai_quota` 按日统计提问次数/字符 |
| **流式** | SSE `text/event-stream`；前端**用原生 fetch 直连**（axios 不能流式 + 超时会杀长流，镜像 BookRate 踩坑）；后端 `threaded=True` + SSE generator 内 `with app.app_context()` |
| **参考歌词平台** | **网易云优先 → 酷狗 → QQ 逐级兜底**（用户拍板）；非官方接口易变动，每曲取第一个成功平台、失败自动降级，全失败该曲无参考不阻断校正 |
| **参考参与方式** | **仅作纠错参考**（用户拍板）；草稿行文/时间戳为准，参考歌词只用于消除同音字/错字/断句歧义，不替换草稿行 |
| **参考歌词缓存** | **不缓存现拉现用**（用户拍板）；无新表，管理员低频识别，多花几秒~十几秒可接受 |

### 数据来源

| 数据 | 存哪 | 现成 or 需新建 | 查询接口 / 字段 |
|------|------|--------------|----------------|
| 整轨 mp3 | `album_pool.mp3_url` → `backend/data/album_track/` | 现成 | `GET /tracks/<file>` |
| 单曲边界 | `albums_{user_id}.tracks_time` | 现成 | `/api/album/detail`（P1 spike 已验证读取路径） |
| 识别产物 | `album_lyric.lyric_text`（整轨绝对时间） | 现成表 | save / upload 复用 |
| faster-whisper 模型 | `portable/models/faster-whisper`（small 已下载） | 现成 | 懒加载单例 |
| OpenCC 繁转简 | pip `opencc-python-reimplemented` | 需新建依赖 | 纯函数 |
| DeepSeek API key（校正） | `config.py` 新增 `DEEPSEEK_API_KEY` | 需新建 | 校正环节（服务器端） |
| **用户 AI key** | `ai_key` 表（user_id 唯一，provider + api_key + is_enabled） | 需新建表 | `POST /api/ai/key` / `GET /api/ai/status` |
| **每曲 BPM / 节奏结构** | `album_tempo` 表（album_pool_id 唯一，JSON：track_tempos + avg/min/max + 单曲时长） | **已建（2026-08-12）** + librosa 依赖已装 | AI 上下文组装时读（懒分析 + 缓存） |
| **AI 对话历史** | `ai_conversation` 表（user_id + album_pool_id + role + content + create_time） | 需新建表 | `GET /api/ai/conversation` |
| **AI 用量** | `ai_quota` 表（user_id + quota_date + requests + chars） | 需新建表 | `GET /api/ai/status` 今日用量 |
| **专辑信息 / 你的评分** | `albums_{user_id}`（album_intro/tags/my_score/tracks） + `album_pool` | 现成 | `/api/album/detail` |
| **你的听后感** | `albums_{user_id}.review`（dict `{"feelings":[...]}`） | 现成 | `/api/album/detail` 内 review 字段 |
| **当前歌歌词** | `album_lyric.lyric_text` 按 `tracks_time` 切当前曲目切片 | 现成表 | `GET /api/album/lyric/get/<pool_id>` |
| **歌手信息** | `albums_{user_id}.singer`（字符串）+ `album_singers.detail_intro`（按 singer_name best-effort 查） | 现成（新增查询） | — |
| **平台评论** | `album_comments` 表 | 现成 | comment.py / pool detail |
| 平台参考歌词（每曲 LRC） | 外部 API 实时拉取（网易云/酷狗/QQ） | 需新建 `lyric_reference.py` | 校正环节按 `album_pool.tracks` + `singer` 逐曲拉取 |

### 架构设计

- **识别器升级**（保持）：`lyric_recognizer.py` transcribe 默认 `vad_filter=False` + 返回 segment `no_speech_prob` → 幻觉过滤（no_speech_prob 阈值丢弃 + `[Music]`/`詞曲 李宗盛`/`字幕by` 等噪音模式滤除 + 器乐标签黑名单）；新增繁→简转换（OpenCC t2s）
- **异步任务**（保持）：`lyric_ai.py`（新 api 模块）`POST /api/album/lyric/recognize/<album_pool_id>` 触发后台线程任务，内存任务表存状态（running/done/failed + 进度），`GET .../status/<task_id>` 轮询；完成后自动落 `album_lyric`；**BPM 分析复用同一内存任务表模式**
- **DeepSeek 校正**（保持）：`deepseek_correct.py`：whisper 行 `mm:ss.x 文本` 作锚 → prompt 强制「逐行只改文字，不改时间戳、不增删行」→ 若行数变化用 difflib.SequenceMatcher 对齐回锚定时间戳；key 读 `config.py.DEEPSEEK_API_KEY`
- **平台参考歌词**（新增）：`lyric_reference.py`——按「曲名+歌手」逐曲搜索并拉取官方 LRC，解析为纯文字（去时间戳）作参考；`build_correct_prompt` 增加可选 `reference_text` 参数（为空则 prompt 不变，向后兼容）；拉取按 网易云→酷狗→QQ 逐级兜底、每请求 5s 超时，失败/为空该曲无参考不阻断校正；`lyric_ai` 在 DeepSeek 校正前读 `album_pool.tracks` + `singer` 逐曲拉参考文本
- **AI key**：`ai.py`（新 api 模块）`ai_key` 表 upsert；`POST /api/ai/key` 永不返回明文 key，`GET /api/ai/status` 返回 has_key + provider + 今日用量（镜像 BookRate）
- **BPM 节奏分析**：`tempo_analyzer.py`（librosa）对整轨 mp3 做 tempo/RMS 分析，按 `tracks_time` 切分得每曲 BPM + 整专节奏结构（avg/min/max/单曲时长），结果缓存 `album_tempo`；**懒分析**——AI 首次提问该专辑若 tempo 缺失则触发异步分析（复用内存任务表），chat 返回「节奏分析中」提示，完成后重试即可，避免请求线程阻塞几十秒
- **AI 助手上下文组装**：`ai.py` `_build_system_prompt` 镜像 BookRate 分层结构——【专辑信息】/【歌手信息】/【你的评分】/【你的听后感】/【你的标签】/【单曲节奏 BPM】/【当前播放歌曲歌词】/【平台评论】/【其他用户听后感精选】；各段截断（听后感 cap、评论 15 条、全网听后感每用户最新 3 条 cap 20），结尾强约束「优先依据以上上下文，信息不足如实告知，不编造」
- **AI 对话**：OpenAI 兼容 `chat/completions`（provider 映射 base_url + model）；SSE 流式（delta/done/error 三事件）+ 非流式兜底；成功才写 `ai_conversation` + `ai_quota`
- **安全**：AI key 只存后端、前端只存布尔；全部接口 `@login_required`；SSE generator `with app.app_context()`；前端 markdown 渲染 `html:false` 防 XSS

### 数据库（新增 4 张表，均幂等 CREATE 挂 `init_base_tables()`）

1. `ai_key` —— `id`、`user_id INT`（对齐 MusicRate users 主键类型）、`provider VARCHAR(20)`（deepseek/openai）、`api_key VARCHAR(200)`、`is_enabled TINYINT`、`create_time`、`update_time`，`UNIQUE KEY(user_id)`；镜像 BookRate
2. `ai_conversation` —— `id`、`user_id INT`、`album_pool_id INT`、`role VARCHAR(10)`、`content TEXT`、`create_time DATETIME`，`INDEX(user_id, album_pool_id)`
3. `ai_quota` —— `id`、`user_id INT`、`quota_date DATE`、`requests INT`、`chars INT`，`UNIQUE KEY(user_id, quota_date)`
4. `album_tempo` —— `id`、`album_pool_id INT`（唯一）、`tempo TEXT`（JSON `{track_tempos:[bpm...], avg_bpm, min_bpm, max_bpm, track_durations:[...]}`）、`create_time`、`update_time`

### 后端接口

歌词识别（保持原规划）：
- `POST /api/album/lyric/recognize/<album_pool_id>`（新增，管理员）——触发异步识别，返回 `task_id`；校验 album 有整轨 mp3 + 管理员权限（识别逻辑抽为 `start_recognize_task` 帮助函数，与专辑添加自动触发共用）
- `GET /api/album/lyric/recognize/status/<task_id>`（新增）——轮询任务状态（running/done/failed + `progress` 0~100 + `message` 阶段提示；转写进度实时上报）
- 复用：`POST /api/album/lyric/save/<album_pool_id>`（识别完成后也可再手动覆盖）
- `POST /api/album/add`（改）——管理员 + 带整轨 `mp3_url` → 添加成功后自动启动识别，响应 `data.recognize_task_id`（非空即已自动开始；失败置空不影响添加）

AI 助手（新增 `backend/api/ai.py`，全部 `@login_required`）：
- `POST /api/ai/key`——保存/更新用户 AI key（`{provider, api_key, is_enabled}`），upsert `ai_key`，响应不含明文
- `GET /api/ai/status`——`{has_key, provider, today_requests, today_chars}`
- `GET /api/ai/conversation?album_pool_id=`——加载该专辑对话历史（最近 20 条）
- `POST /api/ai/conversation/reset`——清空该专辑历史
- `POST /api/ai/conversation/delete`——删除单条消息（按 id + 归属校验）
- `POST /api/ai/chat`——`{album_pool_id, question, current_track_index?, stream?}`；组装上下文（含 BPM/歌词/听后感/评论/全网听后感）+ 调 provider；tempo 缺失时触发 BPM 异步分析并返回友好提示
- `POST /api/ai/tempo/analyze/<album_pool_id>`（可选）——显式触发 BPM 分析（AI tab 打开时可预触发）

### 前端组件

- `AlbumLyricViewer.vue`（改，**AI 按钮已迁出弹窗**）——弹窗内原「AI 识别歌词」按钮移除；歌名标题栏左侧新增同款按钮（与右上「上传/编辑歌词」对称、悬停才显示，仅歌词展示页、仅管理员；识别中保持可见显示进度百分比），无歌词提示区也并排展示上传 + AI 识别两按钮；进度条置于标题栏下方；轮询逻辑（triggerAiRecognize/pollAiRecognize/stopAiRecognizePolling）已迁到常驻父组件 `AlbumDetail.vue`，本组件只通过 props 接收展示 + `@trigger-ai-recognize` 事件触发；保留上传/编辑歌词、整轨 LRC 上传、批量上传、保存等歌词编辑功能
- `AddAlbum.vue`（改）——提交专辑成功且响应带 `recognize_task_id` → toast 提示「AI 歌词识别已自动开始（后台生成中）」
- `components/user/AISettingsTab.vue`（新增）——镜像 BookRate：服务商下拉（deepseek/openai）+ 密码框 API key（已配置显示占位「输入新密钥可覆盖」）+ 保存 + 状态徽章 + 今日用量 + 说明文案；保存成功后清空输入框
- `components/user/UserCenter.vue`（改）——tabs 新增「AI 配置」（`activeTab='ai'`），与个人资料/外观/音乐统计同级
- `components/albumDetail/AlbumAIAssistant.vue`（新增）——专辑详情**子页形态**（非侧边栏）：消息列表（用户气泡 / AI markdown 气泡）+ 空态引导问题 + 底部 textarea（Enter 发送、Shift+Enter 换行）+ SSE 流式渲染（原生 fetch）+ 思考中动画 + 单条删除 + 重置对话
- `views/AlbumDetail.vue`（改）——左侧菜单新增「AI 助手」`menu-item`（`v-if` 仅 has_key 显示），`activeTab='ai'` 渲染 `<AlbumAIAssistant :album="album" :current-track-index="currentTrackIndex" ... />`；currentTrackIndex 由播放器 `currentTime` + `tracks_time` 推导；**v0.8.1 增补**：AI 识别轮询迁入常驻父组件（`triggerAiRecognize`/`pollAiRecognize`/`stopAiRecognizePolling` 自 AlbumLyricViewer 迁入，done 后 `getAlbumLyrics()` 刷新），通过 props 下传 `aiRecognizeLoading/Progress/StatusMsg` + `@trigger-ai-recognize` 事件给 AlbumLyricViewer → 切换听后感/评论等子页面时识别持续、进度条实时更新；`beforeDestroy`/切换专辑时停止轮询防泄漏
- 依赖：前端新增 `markdown-it`（`html:false` 防 XSS）；后端新增 `librosa`（portable Python，P4 spike 验证安装）

### 分阶段路线

- **P0 识别器升级**（保持）：VAD 关 + no_speech_prob 幻觉过滤 + 噪音模式滤除 + OpenCC 繁转简 + 单测（纯函数）✅ 2026-08-12
- **P1 异步任务 + 接口**（保持）：`lyric_ai.py`（recognize + status）+ 后台线程任务表 + realdata 测试 ✅ 2026-08-12
- **P2 DeepSeek 校正 + 前端**（保持）：`deepseek_correct.py`（difflib 保时间戳）+ config API key + 前端按钮 + realdata 验证 + README 归档 ✅ 2026-08-12
- **P3 AI key 配置**：`ai_key` 表 + `ai.py` key/status 接口 + 单测 → `AISettingsTab.vue` + UserCenter tab + realdata 验证 ✅ 2026-08-12
- **P4 BPM 节奏分析**：librosa 安装 spike（portable Python 兼容性验证，同 faster-whisper spike 流程；装不上降级 aubio）→ `tempo_analyzer.py` 纯函数（整轨 mp3 → 每曲 BPM，单测）→ `album_tempo` 表 + 异步任务（与歌词识别共用共享 TaskTable）→ realdata 验证 ✅ 2026-08-12
- **增补：识别进度条 + 自动触发**：`transcribe` 增加 `progress_callback`（segment.end/总时长 实时比例）+ `_map_transcribe_progress`（10→90 映射）+ 前端进度条；`start_recognize_task` 帮助函数抽取 + `album/add` 管理员带 mp3 自动触发识别（响应 `recognize_task_id`）→ 单测 + realdata ✅ 2026-08-12
- **增补：AI 识别按钮移出弹窗、悬停显示**：弹窗内 AI 按钮迁到歌词展示页歌名标题栏左侧（与右上「上传/编辑歌词」对称、悬停才显示，仅歌词展示页；无歌词提示区也并排展示）；轮询逻辑迁到常驻父组件 `AlbumDetail.vue`（props 下传 + 事件触发）——切换听后感/评论/其他子页面时识别持续轮询、进度条在标题栏下方实时可见；done 后 `getAlbumLyrics()` 刷新歌词联动子组件 ✅ 2026-08-12
- **增补：平台参考歌词辅助校正**：`lyric_reference.py`（网易云优先/酷狗/QQ 兜底拉取 LRC + 纯文字解析 + 优先级逐级降级 + 5s 超时）+ `build_correct_prompt` 加可选 `reference_text` 参数（为空则 prompt 不变）+ `lyric_ai` 集成（DeepSeek 校正前按 `album_pool.tracks`+`singer` 逐曲拉参考）+ 单测（解析/prompt）+ realdata 验证（真实拉取知名中文歌）
- **P5 AI 助手后端**：`ai_conversation` / `ai_quota` 表 + 上下文组装（含 BPM/歌词/听后感/评论/全网听后感）+ OpenAI 兼容 chat + SSE 流式 + 配额 → 单测 + realdata ✅ 2026-08-12（`ai.py` chat/conversation/reset/delete + `ai_context.py` 纯函数 + `task_table.find_active`/`start_tempo_task` 抽取 + 懒分析；单测 32 条 + realdata 19 条）
- **P6 AI 助手前端**：`AlbumAIAssistant.vue` 子页 + SSE 流式渲染 + markdown + AlbumDetail 菜单入口（has_key 显隐）+ `npm run lint` + 手动回归 ✅ 2026-08-12（`markdown-it` 依赖 + 组件 + 菜单入口；lint 通过 + build 通过）

### 难点与对策

- **幻觉过滤**（保持）：no_speech_prob > 0.6 丢弃 + 噪音模式（`[Music]`/`詞曲 李宗盛`/`字幕by`/器乐标签）+ 连续短句聚合 → 单测锁定
- **繁体转简体**（保持）：OpenCC `t2s`（纯 Python 实现，无外部服务）；注意歌词专名（如人名）转换后仍准确
- **DeepSeek 校正**（保持）：以 whisper 时间戳为锚，prompt 强约束「只改文字」，difflib 对齐行数变化；校正失败回退 whisper 原稿
- **非官方歌词接口易变动**（新增）：网易云/酷狗/QQ 均为非官方 API → 每曲按 网易云→酷狗→QQ 优先级逐级兜底（一个平台失败自动降级下一个，全失败该曲无参考）；每请求 5s 超时 + 异常捕获；网络失败/无参考不阻断 DeepSeek 校正（回退原行为）
- **CPU 占用**（保持）：识别数分钟 100% → 串行任务 + 前端明确提示「后台生成中」；并发请求排队
- **异步任务进程重启丢失**（保持）：内存任务表不持久化 → 后端重启任务状态丢失，识别/分析接口幂等（重复触发视为新任务）
- **librosa 安装风险**：portable Python（Windows）装 librosa 依赖 numba/llvmlite 二进制 wheel，版本不兼容会翻车 → **P4 先 spike**（同 faster-whisper 流程）；装不上则降级 aubio（轻量 tempo 检测）
- **BPM 分析耗时阻塞 chat**：44min 整轨 tempo 分析 ~几十秒，不能同步阻塞提问 → 懒分析 + 异步任务 + chat 友好提示「节奏分析中，稍后再问」，完成后缓存 `album_tempo` 自动可用
- **歌手数据薄弱**：`album_singers` 有 detail_intro 但无 API 且可能为空 → 歌手上下文先给 singer 名，detail_intro 按 singer_name best-effort 查、缺失优雅降级；AI 查询用 `album_singers`（注意 legacy `json.py` 查 `FROM singers` 的旧 bug 勿复用）
- **SSE 坑**（镜像 BookRate）：generator 须 `with app.app_context()`；前端 axios 不能流式且超时会杀长流 → 原生 fetch + ReadableStream 解析 `data:` 事件
- **key 安全**：key 明文存后端 DB（镜像 BookRate，本机 HTTP 场景可接受），**绝不返回前端**——前端只有 has_key 布尔；`/api/ai/key` 响应不含明文，输入框不保留
- **对话历史一致**（镜像 BookRate）：消息成功才落库，失败/中断不留半会话；前端 temp id 占位，done 事件回填真实 id
- **XSS**：AI markdown 渲染 `markdown-it({html:false})` 转义原始 HTML

### 待做（勾选清单）

- [x] P1 AI spike（faster-whisper 安装 + 识别器 + CLI 报告）✅ 2026-08-12（v0.8 P1）
- [x] P0 识别器升级（VAD 关 + no_speech_prob 幻觉过滤 + 噪音模式滤除 + OpenCC 繁转简 + 单测）✅ 2026-08-12
- [x] P1 异步任务 + recognize/status 接口 + realdata 测试 ✅ 2026-08-12
- [x] P2 DeepSeek 校正（difflib 保时间戳）+ config API key + 前端入口 + README 归档 ✅ 2026-08-12
- [x] P3 AI key 配置（ai_key 表 + key/status 接口 + AISettingsTab + UserCenter tab）✅ 2026-08-12
- [x] P4 BPM 节奏分析（librosa spike + tempo_analyzer + album_tempo 表 + 共享 TaskTable + analyze/status 异步接口 + realdata 测试）✅ 2026-08-12
- [x] 增补：识别进度条 + 添加专辑自动触发（transcribe progress_callback + 前端进度条 + album/add 自动识别 + 测试）✅ 2026-08-12
- [x] 增补：AI 识别按钮移出弹窗、悬停显示（歌名标题栏左侧，与上传/编辑歌词对称；轮询迁入常驻父组件 AlbumDetail，切换子页面识别持续）✅ 2026-08-12
- [x] 增补：平台参考歌词辅助校正（lyric_reference.py 网易云优先/酷狗/QQ 兜底 + build_correct_prompt reference 参数 + lyric_ai 集成 + 单测 + realdata）✅ 2026-08-12
- [x] P5 AI 助手后端（conversation/quota 表 + 上下文组装 + OpenAI 兼容 chat + SSE 流式 + 配额）✅ 2026-08-12
- [x] P6 AI 助手前端（AlbumAIAssistant 子页 + markdown-it + SSE 流式渲染 + AlbumDetail 菜单入口 has_key 显隐）✅ 2026-08-12
## v0.8 — 歌词版：本地上传 LRC 接口（干净版）+ AI 歌词识别可行性验证（P0 已完成）

> v0.8 主题为歌词，重点是 `album/detail` 下的歌词展示页面。规划已于 2026-08-11 定稿，实现按 `feature_development_workflow`（20260810）+ `testing_workflow`（20260810）成对落地；**P0（LRC 纯函数双端同构 + 后端重构删 QQ/权限修复/整轨上传接口 + 前端删 QQ 加整轨上传入口）已完成（2026-08-11）**；**P1 AI 歌词识别 spike（faster-whisper 可行性验证）已完成（2026-08-12），验证通过 → 正式管线拍板落地，见 v0.8.1 章节**。歌词样式迭代与两个已知 bug（当前句抖动、长歌词省略号）明确留给后续小版本。

### 功能概述

1. **本地上传 LRC 接口（干净版）**：移除 QQ 音乐自动获取（后端 `fetch_auto`/`fetch_qq_lyric` + 前端 QQ 拉取按钮/网易云死代码），修复 `save_album_lyric` 硬编码 `is_admin=True` 的权限漏洞（改真实管理员校验），新增真正的整轨 LRC 文件上传接口（服务端解析/校验/规范化落库），新增 `backend/utils/lrc.py` 纯函数与前端 `parseLrcToStandardFormat` 双端同构。
2. **AI 歌词识别可行性验证（spike）**：装 faster-whisper，对 1~2 张已有整轨 mp3 的专辑做语音识别（含时间戳），按 `tracks_time` 切分到各单曲，产出评估报告（文本准确度 / 时间戳对齐 / CPU 耗时 RTF），验证通过后再决定正式管线是否落地。✅ 已通过（2026-08-12），评估结论见「P1 spike 评估结论」。
3. **后续小版本待办（本大版本不做）**：歌词显示到当前句时抖动；歌词过长只显示省略号导致其他歌词不显示；歌词样式迭代。

### 已定决策（2026-08-11 拍板）

| 决策点 | 结论 |
|--------|------|
| AI 识别节奏 | **spike 已通过（2026-08-12）**：faster-whisper small CPU int8 RTF 0.18-0.19、人声清晰句 ~90% 逐字命中、按 tracks_time 切分正确；结论「草稿级可行」→ **正式管线落地（v0.8.1）** |
| DeepSeek 定位 | DeepSeek 是纯文本模型**不能直接吃音频**；音频→歌词靠 faster-whisper，DeepSeek 只在正式落地阶段做歌词校正（可选增强，需用户 API key，difflib 保时间戳对齐） |
| QQ 音乐 | **彻底移除**：`fetch_auto` 接口 + `fetch_qq_lyric` + `clean_lyric` + 前端 QQ 拉取按钮 + 网易云死代码；保留 `krc2lrc`（本地文件转换） |
| 歌词存储格式 | 保持 `mm:ss(.x)? 歌词`（无方括号，1 位小数）不变，后端新增校验/上传统一转成此格式；不引入标准 LRC 方括号格式 |
| 歌词存储位置 | 保持 `album_lyric` 表按 `album_pool_id`（公共池级，全用户共享），不迁移、不加用户维度 |
| 上传权限 | save 与 upload 均改**真实管理员校验**（复用 `users.is_admin`）；原「任何登录用户可存」为硬编码 bug，本次修复属权限收紧 |
| 上传接口形态 | 新增整轨 LRC 文件上传（绝对时间覆盖全专辑），与现有逐单曲批量上传（相对时间按文件名匹配）语义不同、两个入口并存 |

### 数据来源

| 数据 | 存哪 | 现成 or 需新建 | 查询接口 / 字段 |
|------|------|--------------|----------------|
| 整轨 LRC 歌词 | `album_lyric.lyric_text`（按 `album_pool_id`） | 现成 | `GET /api/album/lyric/get` |
| 歌词翻译 | `album_lyric.lyric_translate`（JSON `{"CN":"..."}`） | 现成 | 同上 |
| 单曲列表 + 时间戳 | `albums_{user_id}.tracks` / `tracks_time` | 现成 | `/api/album/detail` |
| 整轨 mp3 | `album_pool.mp3_url` → `backend/data/album_track/` | 现成 | `GET /tracks/<file>` |
| 上传/识别产物 | 复用 `album_lyric` 表 | 现成表 | save / upload 接口 |
| faster-whisper 模型 | portable python pip 安装 + `portable/models/faster-whisper` | 需新建 | — |
| DeepSeek API key | `config.py` 新增（正式落地阶段） | 需新建 | — |

### 架构设计

- **LRC 纯函数双端同构**：`backend/utils/lrc.py`（`str_to_seconds`/`seconds_to_str`/`parse_any_to_items`/`items_to_storage`/`normalize_to_storage`/`validate_lyric_text`）与前端 `parseLrcToStandardFormat` 输出同一存储格式，复用 scoreCalc「前后端一致」既有模式，双端可单测
- **权限收敛**：`backend/utils/decorators.py` 新增 `is_admin_user(user_id)` 共享助手（参考 audio_resource.py 的真实校验），save/upload 复用
- **上传与保存共用落库**：`upsert_album_lyric()` 抽出公共，save（编辑器 JSON 逐单曲）与 upload（整轨 LRC 文件）结果等价、幂等互斥覆盖
- **AI 识别管线**（spike 阶段 CLI 不接路由）：`lyric_recognizer.py` 懒加载模型单例 → `transcribe(word_timestamps=True, vad_filter=True)` → segment 级时间戳按 `round(start*10)/10` 去重升序 → 按 `tracks_time` 边界切分到单曲 → `items_to_storage` 产出整轨绝对时间存储文本（可直接落 `album_lyric`）
- **DeepSeek 校正（正式阶段）**：以 whisper 逐行 `mm:ss.x 文本` 为锚，DeepSeek 强制保行数/行序/时间戳只改文字，difflib.SequenceMatcher 处理行数变化再对齐回时间戳

### 数据库

v0.8 **无新增表**，全部复用 `album_lyric`（歌词）与现有表。备注：`album_pool.tracks_time` 列存在于线上库但不在 `db.py` 建表 DDL（DDL 漂移），本次不迁移，P1 spike 从用户专辑表读 `tracks_time`。

### 后端接口

- `POST /api/album/lyric/upload/<album_pool_id>`（新增）——整轨 LRC 文件上传（multipart `lrc_file`，≤1MB，utf-8 失败回退 gbk），服务端规范化落库，仅管理员；可选 `translate_file` 存 `{"CN":...}`；返回 `{album_pool_id, lyric_text, lyric_text_length, has_translate}`（lyric_text 直接回前端免二次 GET）
- `POST /api/album/lyric/save/<album_pool_id>`（改）——`is_admin` 硬编码改真实管理员校验；`lyric_text`/翻译 CN 值走 `validate_lyric_text` + `normalize_to_storage` 规范化落库；补专辑存在性校验
- `GET /api/album/lyric/get/<album_pool_id>`（不动）
- `POST /api/lyric/krc2lrc`（保留）——酷狗 KRC 本地文件转换
- `POST /api/lyric/fetch_auto`（删除）——QQ 音乐自动获取彻底移除

### 前端组件

- `AlbumLyricViewer.vue`（改）——删除「一键获取所有歌词」/「从QQ音乐获取」按钮、自动获取弹窗、`startBatchFetchLyrics`/`fetchLyrics` 等方法、`lyricSources`/`fetchNeteaseUrl` data 及 watcher；保留逐单曲批量上传/粘贴拆分/保存合并；弹窗头部新增「上传整轨LRC（绝对时间）」按钮，`FormData` 直传 upload 接口，成功后 `$emit('update:lyrics')` 触发 `initTrackLyricsMap` 按 `tracks_time` 自动切分

### 分阶段路线

- [x] **P0-A LRC 纯函数**：`lrc.py` + `test_lrc.py`（测试先行）→ 单测绿 + 与前端样例逐字符一致 ✅ 2026-08-11（cd5d9a3）
- [x] **P0-B 后端重构**：`is_admin_user` 助手 → save 修权限+校验+抽 upsert → 新增 upload 接口 → 删 QQ → `test_lyric_api_realdata.py`（realdata）绿 → grep `fetch_auto` 后端零命中 ✅ 2026-08-11（f1ce6ee）
- [x] **P0-C 前端改造**：删 QQ + 整轨上传入口 → `npm run lint` 过 + 手动回归（批量上传/粘贴/保存/滚动高亮/整轨同步）✅ 2026-08-11（f6b2530）
- [x] **P0-D README 归档**：v0.8 章节 + 待做清单（本章节即本次规划产出）✅ 2026-08-11
- [x] **P1 AI spike**：装 faster-whisper → `lyric_recognizer.py` → `lyric_spike.py`（CLI）→ 跑 2 张专辑 → 报告（文本/对齐/RTF）→ 拍板落地 ✅ 2026-08-12（ce59579）

### P0 实现要点（复盘速查）

- **双端同构验证方式**：用 node 直接跑前端真实 `parseLrcToStandardFormat` 生成 golden 基线，硬编码进 `test_lrc.py`（47 例）逐字符对比，锁定了 `.5`→0.05s→`00:10.1` 等前端怪癖与去重取首规则
- **权限漏洞修复**：原 save 硬编码 `is_admin=True`（任何登录用户可存歌词）→ `is_admin_user()` 真实查 `users.is_admin`；注意 `MYSQL_CONFIG` 全局 `cursorclass=DictCursor` 使行是 dict，取列须 `row.get('is_admin')` 而非 `row[0]`
- **DDL 漂移**：线上 `album_pool.tracks_time` 存在但无默认值，realdata 测试插入模板须显式传 `tracks_time='[]'`
- **JS round 怪癖**：JS `Math.round` 是半进位、Python `round` 是银行家舍入 → `_round_half_up = math.floor(x + 0.5)` 复刻
- **前端上传沿用全站惯例**：`FormData` + 显式 `Content-Type: multipart/form-data`（与 krc2lrc / ProfilePanel / UnlockParse 一致），成功后 `$emit('update:lyrics')` 复用父组件双保存（幂等）机制

### 难点与对策

- **DeepSeek 不吃音频**：音频→歌词必须 ASR（faster-whisper），DeepSeek 仅做歌词校正（正式阶段），定位清晰不混淆
- **中文歌词识别草稿级**：伴奏干扰 + 诗意歌词 + 同音字 → spike 产出定位「草稿+时间戳」非成品；正式管线必须接 DeepSeek 校正或人工修正环节
- **CPU 慢**（RTF 0.1-0.3，分钟级）→ spike 首跑 small + `--limit-secs 300` 拿 RTF 再决定整轨
- **模型下载失败**（国内 HuggingFace 不可达）→ `HF_ENDPOINT=https://hf-mirror.com` + `download_root` 固定 `portable/models`
- **删 QQ 回归**：grep 确认 `fetch_auto`/`lyricSources`/`fetchNeteaseUrl`/`startBatchFetchLyrics` 全部收敛在 `AlbumLyricViewer.vue`，删后全仓再 grep 一遍
- **权限收紧**：原任何登录用户可存歌词（硬编码 bug），改管理员校验后非管理员 403，前端 `isAdmin` 口径一致
- **存储格式精度 bug**（前端 `parseTimeStr` 小数位 /1000 不自洽）→ 本版本不修，后端按前端现有格式生成保证 round-trip，归小版本

### P1 spike 评估结论（2026-08-12）

| 维度 | 结果 |
|------|------|
| CPU 耗时 | small int8 RTF 0.19（VAD 开）/ 0.18（VAD 关）；2105s 专辑 ≈ 6.7min、2662s 整轨 ≈ 8min → 后台一次性生成可接受，交互不可行（base 可再快一半） |
| 文本准确度 | 人声清晰句 ~90% 逐字命中（春日光「某夜你離開/某天你走來」全对，仅同音字错）；人声密集/伴奏重 ~50-60%（冀西南「將甘苦注入湯」）；**输出繁体需转简体**；定位「草稿 + 时间戳」非成品 |
| 时间戳对齐 | 句间隔 3-7s 符合人声节奏；VAD 滤掉器乐长空档（春日光 track1 尾 47s 空白被跳）；按 `tracks_time` 边界切分到单曲完全正确 |
| VAD 双刃剑 | **音乐场景过度过滤**：开 → 冀西南 44min 仅 16 段（山雀/河北墨麒麟整首丢失，RTF 虚低到 0.01）；关 → 召回 72 段（泥河 3→55 条）但器乐段幻觉出「Zither Harp / 詞曲 李宗盛 / 字幕by索兰娅」 |
| 结论 | **技术路径可行，质量上限「草稿 + 时间戳」** → 拍板落地正式管线（v0.8.1） |

关键坑（正式管线复用）：hf-mirror 不支持新版 huggingface-hub 的 Xet 后端（cas-server 401）→ 必须 `HF_HUB_DISABLE_XET=1` 回退经典 HTTP；Windows 无符号链接 → 模型缓存降级但可用；spike 输出在 `backend/data/spike_output/`（gitignore）。

### 待做（勾选清单）

- [x] P0-A `lrc.py` 纯函数 + 单测 ✅ 2026-08-11
- [x] P0-B lyric.py 重构（删QQ + 权限修复 + 校验 + upload 接口）+ realdata 测试 ✅ 2026-08-11
- [x] P0-C 前端删 QQ + 整轨 LRC 上传入口 ✅ 2026-08-11
- [x] P1 AI spike（faster-whisper 安装 + 识别器 + CLI 报告）✅ 2026-08-12

### 后续小版本待办（本大版本不做）

- [x] **歌词当前句抖动**：`getLyricItemStyle` 字号随距离变化 + `smoothScrollTo` 的 offsetTop 不稳定形成反馈循环 → **已并入 v0.8.3（P0）**
- [x] **长歌词省略号**：`.lyric-text` 的 `white-space: nowrap; text-overflow: ellipsis` 撑破居中布局导致其他歌词不显示 → **已并入 v0.8.3（P0）**
- [x] **歌词样式迭代**：整体美化（含前端 `parseTimeStr` 小数精度 bug） → **已并入 v0.8.3（P0 全量样式统一）**
- [ ] ~~DeepSeek 歌词校正正式落地~~ → 已并入 v0.8.1 正式管线
- [x] **`album_pool.tracks_time` DDL 漂移**统一 → **已并入 v0.8.3（P2）**


---

## v0.7.2 — 听后感统计修复 + 等级经验详情（已完成）

> 承接 v0.7.1 等级经验系统，修复个人中心「听后感统计恒为 0」的 bug，并落地「等级经验详情弹窗」：点击个人资料页等级徽章，查看总经验 / 今日经验 / 最近经验 / 按来源拆分的经验明细。规划已于 2026-08-11 定稿，实现按 `feature_development_workflow`（20260810）拆 P0 → P1 逐步落地；**P0 听后感统计修复、P1 经验详情（明细落表 + 详情接口 + 弹窗）已完成（2026-08-11）**。

### 功能概述

1. **听后感统计修复**：个人中心「听后感」卡片恒为 0——统计口径 `has_review()` 误以为 `review` 列是 JSON 数组，实际存储是 dict `{"feelings":[...]}`（日历接口按 dict 解析所以正常，二者口径不一致）。改为按 `feelings` 数组长度统计**听后感总条数**（兼容旧版数组格式），与专辑详情页日历看到的条数一致。
2. **等级经验详情弹窗**：点击个人资料页等级徽章弹出 Modal，展示总经验 / 等级 / 进度、今日经验（听歌 + 加分）、近 7 天每日经验（ECharts 堆叠柱：听歌 + 加分）、按来源累计（听歌 / 评分 / 听后感 / 评论）、最近经验明细流（时间 + 来源 + 数额）。

### 已定决策（2026-08-11 拍板）

| 决策点 | 结论 |
|--------|------|
| 听后感统计口径 | 修复后按**听后感总条数**（所有专辑 `feelings` 数组长度之和），非有听感后的专辑数；`count_review_items()` 兼容 dict 与旧数组两种格式 |
| 经验明细 | 新建 `user_xp_log` 明细表，自 v0.7.2 起每次获取经验写一条（来源 + 数额 + 时间）；历史经验无法按来源拆分（此前未记录），总收听经验用 `users.listening_total` 展示完整历史 |
| 最近经验 | 近 7 天每日经验汇总（ECharts 堆叠柱：听歌 + 加分）+ 最近明细流（时间 + 来源 + 数额，取最近 30 条） |
| 弹窗入口 | 点击个人资料 tab 等级徽章 → Modal；挂 ProfilePanel 内，UserCenter 不改 |

### 数据来源

| 数据 | 存哪 | 现成 or 需新建 | 查询接口 / 字段 |
|------|------|--------------|----------------|
| 听后感总条数 | `albums_{user_id}.review`（dict 的 feelings 长度） | 现成（解析格式改对） | `/api/user/stats` `review_count` |
| 总经验 / 等级 / 进度 / 称号 | `users.xp` + level 纯函数推导 | 现成 | `/api/user/xp-detail` |
| 总收听经验（完整历史） | `users.listening_total` | 现成 | `/api/user/xp-detail` `total_listening_xp` |
| 今日收听经验 | `user_listening_log` 今日 SUM(duration_seconds)（1 秒 = 1 XP） | 现成 | `/api/user/xp-detail` `today_listening` |
| 今日加分经验 | `users.bonus_xp_today` | 现成 | `/api/user/xp-detail` `today_bonus` |
| 近 7 天每日经验 | `user_listening_log` + `user_xp_log` 按日聚合 | 需新建表 | `/api/user/xp-detail` `daily_xp` |
| 按来源累计 / 最近明细流 | `user_xp_log`（自 v0.7.2 起） | 需新建表 | `/api/user/xp-detail` `source_totals` / `recent_logs` |

### 架构设计

- **经验明细落表**：`user_xp_log` 与 `users` 累计列**同事务写入、仅 `amount > 0` 时写**——`SUM(user_xp_log 加分)` 与 `bonus_xp_today` 严格一致，明细流无 `+0` 噪音
- **来源枚举收敛**：`backend/utils/xp.py` 常量 `XP_LISTENING / XP_RATING / XP_REVIEW / XP_COMMENT` + `BONUS_SOURCES`（加分来源）+ `SOURCE_LABELS`（前端镜像）；`add_bonus_xp` 增加必填 `source` 参数并校验枚举，防漏传静默丢 log
- **聚合纯函数共享**：`backend/utils/xp_detail.py` 的 `accumulate_bonus_daily` / `build_daily_xp` 零 DB 依赖可单测，复用 `user_stats.py` 的日期补零思路；前端 ECharts 参考 `StatsPanel.vue` 既有用法

### 数据库（1 张新表）

1. 新增 `user_xp_log` 表：`id`、`user_id`、`xp_type VARCHAR(20)`（listening/rating/review/comment）、`amount FLOAT`、`created_at DATETIME DEFAULT CURRENT_TIMESTAMP`、`INDEX idx_user_created (user_id, created_at)`
- 复用 `create_user_listening_log()` 的 `CREATE TABLE IF NOT EXISTS` 幂等模式，新增 `create_user_xp_log()` 挂进 `init_base_tables()`；不回填历史（无法按来源拆分）

### 后端接口

- `GET /api/user/xp-detail`（新增）——`total_xp / level / next_level_xp / xp_progress / level_title / total_listening_xp / today_xp / today_listening / today_bonus / daily_xp[7] / source_totals / recent_logs[≤30]`
- `POST /api/album/review/add/<album_id>`（改）——听后感新增成功后 `add_bonus_xp(uid, 20, 'review')`，写 log
- `POST /api/album/comment/add/<album_id>`（改）——`add_bonus_xp(uid, 10, 'comment')`，写 log
- `POST /api/album/pool/comment/add`（改）——`add_bonus_xp(uid, 10, 'comment')`，写 log
- `PUT /api/album/score/save/<album_id>`（改）——评分实际变化时 `add_bonus_xp(uid, 5, 'rating')`，写 log
- `POST /api/album/listening/pause/<album_id>`（改）——`play_seconds > 0` 时同事务 INSERT `user_xp_log(xp_type='listening', amount=play_seconds)`

### 前端组件

- 新建 `components/user/XpDetailModal.vue`——弹窗（复用 AlbumLyricViewer mask+content 模式）：Lv 徽章 + 称号 + 总经验 + 距下一级、来源累计 4 格卡片 + 总收听经验、ECharts 近 7 天堆叠柱（听歌 + 加分）、最近明细流 HTML 列表；loading / loadError / 空态兜底；三件套主题色 props
- `ProfilePanel.vue`（改）——L25 等级徽章加 `@click.stop` 弹 XpDetailModal（`cursor:pointer` + `title` 提示）

### 分阶段路线

- **P0 听后感统计修复**：`count_review_items` + `aggregate_stats` 改总条数 + 测试同步（test_user_stats.py / test_user_stats_realdata.py 改真实 dict 格式）→ 单测 + realdata 绿 → 手工验证统计卡片
- **P1 经验详情**：`user_xp_log` 建表（挂 init_base_tables）→ `xp.py` 常量 → `add_bonus_xp` 加 source + 写 log、listening pause 写 log → `xp_detail.py` 纯函数 + 单测 → `/api/user/xp-detail` 接口 → `XpDetailModal.vue` + ProfilePanel 徽章点击 → realdata 验证 → README 归档

### 难点与对策

- **统计口径与真实格式不一致**：`has_review` 按数组判断，真实是 dict——改为按 `feelings` 长度统计，`count_review_items` 兼容 dict + 旧数组两种格式，存量数据不塌
- **经验明细落表**：新增表不回填历史（无法按来源拆分）；「总收听经验」用 `users.listening_total` 展示完整历史，弹窗文案区分「完整历史」与「自 v0.7.2 起」
- **加分与 log 一致性**：同事务、`gained > 0` 才写 log；评分防抖保存 `xp_gained=0` 不写 log（与前端 toast 守卫一致）
- **add_bonus_xp 签名变更**：source 必填 + 校验枚举，同步更新 4 处调用 + realdata 测试调用，防编译期漏改
- **时间口径**：`user_listening_log.listen_date`（本地日）与 `user_xp_log.created_at`（DB CURRENT_TIMESTAMP）均为本地时区，SQL 按 `DATE(created_at)` 与 `listen_date` 对齐

### 待做（勾选清单）

- [x] P0 听后感统计修复（count_review_items + 总条数口径 + 测试同步）✅ 2026-08-11
- [x] P1 经验详情（xp_log 表 + 加分点写明细 + xp-detail 接口 + XpDetailModal 弹窗）✅ 2026-08-11
## v0.7.1 — 等级经验系统与统计展示优化（已完成）

> 承接 v0.7 个人中心，落地「等级-经验」体系（经验与听取总时长强相关）+ 听取时长统一以「小时」展示 + 修复外观栏蒙版透明度滑轨偏移 bug。规划已于 2026-08-11 定稿，实现按 `feature_development_workflow`（20260810）拆 P0 → P1 → P2 逐步落地；**P0 等级经验 + 反馈、P1 统计优化、P2 滑轨修复 + 体验已完成（2026-08-11）**。

### 功能概述

1. **等级经验制度**：经验与听取总时长强相关——听 1 秒 = 1 XP（无上限），辅以听后感 / 评论 / 评分小额加分（**每日合计上限 100**）；等级由经验按平方根曲线推导（Lv.N 约需 N² 小时），在个人资料页展示等级徽章 + 经验进度条 + 距下一级进度 + 等级称号；**配套经验反馈**：升级瞬间弹横幅、保存听后感 / 评论 / 评分成功 toast「+N 经验」
2. **统计展示优化**：听取总时长卡片与近 N 天柱状图由「秒」统一改为「小时」，小数点后保留 1 位；**总时长口径统一**（改读持久化 `users.listening_total`，删专辑不掉）；**新增活跃度**：连续收听天数 + 近 30 天活跃天数
3. **蒙版透明度滑轨偏移修复**：外观栏滑块轨道填充渐变与滑块按钮（thumb）位置不一致 + thumb 垂直方向相对轨道偏移的 CSS bug；顺手加拖动数值气泡与刻度线

### 已定决策（2026-08-11 拍板）

| 决策点 | 结论 |
|--------|------|
| 经验来源 | 听取时长为主（1 秒 = 1 XP，无上限）；听后感新增 +20、评论新增 +10、评分保存成功 +5 小额加分，**每日合计上限 100**（不含收听），不追溯历史 |
| 升级曲线 | 平方根：`level = floor(sqrt(xp / 3600))`，Lv.N 约需 N² 小时。示例：Lv.1=3600（1h）、Lv.2=14400（4h）、Lv.3=32400（9h）、Lv.5=90000（25h）、Lv.10=360000（100h） |
| XP 存储 | 新增 `users.xp` 列；暂停时随 listening_duration 一起累加；迁移时用已有 `SUM(listening_duration)` 一次性回填初始经验 |
| 小时显示 | 听取时长统一 `h + 1 位小数`（不足 1 小时也显示如 `0.4小时`），总时长卡片与近 N 天图表一致 |
| 等级入口 | P0 先做个人资料页（徽章 + 进度条 + 称号）；头像旁 / 评论区扩展待定 |
| 加分防刷 | 加分仅计「新增 / 保存成功」一次，不做追溯；**每日加分（评分 / 听后感 / 评论合计）上限 100 XP**，超限当次不再累加（实际加分可部分/为 0）。评分经验按「实际评分变化」发放：前端在离开评分板块 / 切换子页面 / 退出专辑时都会自动保存一次，后端比较已存 `my_score`（归一化剥末尾 0），未变化不加分（返回 `xp_gained=0`） |
| 经验反馈 | 暂停 / 加分接口返回 xp、level、level_up；前端对比 localStorage 上次等级检测升级并弹横幅，加分接口返回本次 +N 供 toast |
| 总时长口径 | 新增 `users.listening_total` 持久化列（迁移回填 = `SUM(listening_duration)`，之后随 play_seconds 累加），总时长改读此列，删专辑不掉；`user_listening_log` 仅供图表 |
| 活跃度 | 连续收听天数（标准断签语义：今天未听不算断签，锚点 = 最近有收听日；昨天及更早有整天无收听即断签为 0）+ 近 30 天活跃天数，由 user_listening_log 纯函数计算 |
| 滑轨体验 | P2 修复时顺带：拖动时 thumb 上方数值气泡 + 0/25/60 刻度线 |

### 数据来源

| 数据 | 存哪 | 现成 or 需新建 | 查询接口 / 字段 |
|------|------|--------------|----------------|
| 听取总时长（秒） | `users.listening_total`（迁移回填，非实时 SUM） | 需新建列 | `/api/user/stats` `total_duration` |
| 近N天听取（秒） | `user_listening_log.duration_seconds` | 现成 | `/api/user/stats` `daily_listening` |
| 经验 XP | `users.xp` | 需新建列 | 各接口累加 + 迁移回填 |
| 等级 / 进度 / 称号 | 由 xp 推导 | 需新建纯函数 | `computeLevel(xp)` 等 |
| 听后感 / 评论 / 评分加分 | `users.xp`（每日上限 100） | 需新建列 | 各接口成功后 `add_bonus_xp()` |

### 架构设计

- **XP / 听取时长双列**：经验（xp，含加分）与持久化听取总时长（listening_total，纯收听）同源同累加——等级由 xp 实时推导、总时长展示读 listening_total，删专辑均不掉，保证「经验 vs 统计」不打架
- **纯函数共享**：`backend/utils/level.py` + `frontend/src/utils/level.js` 用同一套 `computeLevel(xp)` / `levelProgress(xp)` / `xpToNextLevel(xp)` / `levelTitle(level)`，复用 scoreCalc「前后端一致」既有模式，双端可单测
- **回填幂等**：`users.xp` / `users.listening_total` 两列迁移仅在「新加列的那一次启动」回填（循环各用户表 `SUM(listening_duration)`），重启不重复计数；之后收听在 pause 时都 `+= play_seconds`
- **每日加分上限**：评分 / 听后感 / 评论加分合计每日 ≤ 100 XP，用 `users.bonus_date` + `users.bonus_xp_today` 记录，跨天自动重置；收听经验不受限

### 数据库（3 处变更，同一次幂等迁移）

1. `users` 表新增 `xp` 列——经验货币（收听 1 秒 = 1 XP + 评分 / 听后感 / 评论加分）
2. `users` 表新增 `listening_total` 列——持久化听取总秒数（删专辑不掉）
3. `users` 表新增 `bonus_date DATE` + `bonus_xp_today FLOAT DEFAULT 0` 列——当日加分累计，用于每日上限 100（跨天自动重置，含多天未登录）
- 幂等迁移：查 `information_schema.columns` 缺列则 `ALTER TABLE ADD COLUMN` 并一次性回填 `xp = listening_total = SUM(listening_duration)`，重启不重复计数，封装挂进 `init_base_tables()`（复用 avatar 迁移已验证模式）

### 后端接口

- `POST /api/album/listening/pause/<album_id>`（改）——成功后 `users.xp += play_seconds`、`users.listening_total += play_seconds`（与 listening_duration 同请求）；返回 `xp`、`level`、`level_up`
- `POST /api/album/review/add/<album_id>`（改）——成功后走 `add_bonus_xp`（+20），返回 `xp_gained`（受每日上限约束）
- `POST /api/album/comment/add/<album_id>`（改）——成功后走 `add_bonus_xp`（+10），返回 `xp_gained`
- `PUT /api/album/score/save/<album_id>`（改）——成功后走 `add_bonus_xp`（+5），返回 `xp_gained`
- `GET /api/user/info`（改）——返回 `xp`、`level`、`next_level_xp`、`xp_progress`、`level_title`
- `GET /api/user/stats`（改）——`total_duration` 改读 `users.listening_total`（不再 SUM albums.listening_duration）；新增 `current_streak`、`active_days_30`
- 加分收敛：`backend/utils/user.py` 新增 `add_bonus_xp(user_id, amount)` 公共函数——先查 `bonus_date`，跨天则重置当日计数；`remaining = 100 - bonus_xp_today`，实际加分 = `min(amount, remaining)`（可为部分 / 0），返回本次实际 +N 供 toast，各接口成功后一行调用

### 前端组件

- `StatsPanel.vue`（改）——`formatDuration` 改 `h + 1 位小数`；近 N 天柱状图 y 轴 / 轴标签 / tooltip 秒 → 小时；新增连续收听天数 / 近 30 天活跃天数卡片
- `ProfilePanel.vue`（改）——Lv 徽章旁新增经验进度条 +「距下一级还差 X 经验」+ 等级称号；展示 `/api/user/info` 新增字段
- `AppearancePanel.vue`（改）——滑轨填充渐变按 thumb 宽度补偿 + thumb 垂直居中修正 + 拖动数值气泡 + 0/25/60 刻度线（先实测 rect 再改）
- 新建 `frontend/src/utils/level.js`——与后端一致的等级纯函数
- 升级横幅 / +N 经验 toast——复用全局 `$message`；localStorage 记上次等级，跨会话检测升级

### 分阶段路线

- **P0 等级经验 + 反馈**：users.xp / listening_total / bonus_date / bonus_xp_today 迁移 + 回填 → level.py / level.js 纯函数（先单测）→ pause 挂收听经验、评分 / 听后感 / 评论挂加分（每日上限 100）→ 升级横幅 + +N 经验 toast → `/api/user/info` 加字段 → ProfilePanel 进度条 → realdata 验证
- **P1 统计优化**：StatsPanel 总时长 + 近 N 天图表全部 `h + 1 位小数`（纯前端）→ 总时长改读 listening_total（口径统一）→ 连续收听天数 / 近 30 天活跃天数（user_stats.py 纯函数 + 单测）
- **P2 滑轨修复 + 体验**：按布局对齐工作流先 DevTools 实测 thumb / track rect → 修 CSS（填充渐变补偿 + thumb 垂直居中）→ 拖动数值气泡 + 刻度线 → 重测收敛 → 窄屏检查

### 难点与对策

- **xp / listening_total 双列同源**：两者同一时刻回填 `SUM(listening_duration)`、pause 时都 `+= play_seconds`，唯一区别是加分只进 xp——回填只跑一次（幂等），删专辑均不掉
- **加分防刷**：评分防抖保存 + 离开板块 / 切子页面 / 退出专辑自动保存都会触发 → 后端按「评分实际变化」判定（读已存 `my_score` 归一化比较），未变化 `xp_gained=0`，三重约束（仅变化 + 单次 +5 + 每日上限 100）可接受；听后感 / 评论只计「新增」不计「编辑」（均为用户主动提交，无自动保存路径）
- **加分上限重置**：`bonus_date` 与今天比对，跨天（含多天未登录）自动清零，无需定时任务
- **滑轨偏移**：不凭肉眼猜，按布局对齐工作流实测 rect 后改；注意 `-webkit-appearance:none` 下 thumb 的 margin-top 补偿与渐变起止点按 thumb 宽度偏移
- **等级与统计一致性**：等级由 xp 纯函数实时推导，总时长读 listening_total，两列同源保证「经验 vs 统计」不打架

### 待做（勾选清单）

- [x] P0 等级经验系统 + 经验反馈（升级横幅 + +N 经验 toast + 每日加分上限 100）✅ 2026-08-11
- [x] P1 统计优化（h + 1 位小数 + 总时长口径统一 + 连续收听天数 / 活跃度）✅ 2026-08-11
- [x] P2 蒙版滑轨偏移修复 + 拖动数值气泡 / 刻度线 ✅ 2026-08-11（headless 实测：填充渐变边界 vs thumb 中心收敛至 ≤0.4px；**thumb 垂直方向实测已居中，未加 margin-top**；补 0/25/60 刻度线 + 拖动数值气泡）
- [x] （补充）听取时长显示格式统一：AlbumItem / AlbumBaseInfo / AlbumReviewEditor / AlbumCommentSection 多处格式各异，抽公共 `utils/duration.js` → **已并入 v0.8.3（P2）**
- [ ] （补充）等级徽章入口扩展：UserAvatar（WebHome 右上角）+ 评论区展示等级（待定）
- [ ] （补充）等级称号文案确认（如 Lv1-3 初听者 → Lv4-7 爱乐人 → Lv8-12 资深乐迷 → …）


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
- 用户养成：邮箱注册、用户名、头像（仅封面库）；用户顶号；信息通知；可查看别人的音乐列表（等级经验已纳入 v0.7.1）
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
