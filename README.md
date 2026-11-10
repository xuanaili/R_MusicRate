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

### 一键启动（推荐）

```bash
# Windows 下双击 portable\start_musicrate.bat（本机小工具，git 不携带，需自行保留；或桌面「MusicRate 启动」快捷方式）即可
# 自动完成：启动后端 Flask(:5000) + 前端 npm(:8080) → 轮询等待就绪 → 自动打开浏览器
# 首次运行会在桌面自动创建带图标的快捷方式；已运行则直接打开页面
# 图标由 portable/launcher/make_icon.py 重新生成（纯 stdlib，无 PIL 依赖）
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
├── portable/                 # 本机小工具专区（gitignored，不入库）：便携 Python、ffmpeg、
│                             #   一键启动脚本 start_musicrate.bat/.ps1、防火墙修复脚本 firewall_dev.ps1、
│                             #   桌面图标生成器 launcher/（musicrate.ico + make_icon.py）等
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

# 版本演进

> 本 README 只保留每个版本一行索引；详细规划见 `ai/planning/`（2026-08-30 起，README 不再承载版本规划章节）。

| 版本 | 主题 | 状态 | 规划文档（ai/planning/） |
|---|---|---|---|---|
| v0.10 | 手机端适配：专辑详情页与子 Tab 底部 TabBar 化 + 模糊底色降级（iPhone 14 Pro / Safari 优先） | 已定稿 | `v0.10_mobile-adaptation.md` |
| v0.9.1 | 目录整理：launcher 移入 portable（仓库整理） | 已完成 | `v0.9.1_launcher-move-to-portable.md` |
| v0.9 | 曲目列表样式参数自动化 + 配置持久化 | 已完成（P0/P1） | `v0.9_track-list-style-auto-config-persist.md` |
| v0.8.5 | AI 助手整张专辑歌词上下文 | 已完成 | `v0.8.5_ai-assistant-album-lyrics-context.md` |
| v0.8.4 | 歌词页顶部当前单曲快捷评分 | 已完成 | `v0.8.4_lyric-page-quick-rating.md` |
| v0.8.3 | 歌词样式统一 + AI 助手 BPM 预触发 | 已完成 | `v0.8.3_lyric-style-unify-bpm-pretrigger.md` |
| v0.8.1 | AI 系列：歌词识别正式管线 + AI 助手 | 已完成（P0-P6） | `v0.8.1_ai-lyric-pipeline-assistant.md` |
| v0.8 | 歌词版：本地上传 LRC + AI 歌词识别可行性 | P0 已完成 / P1 验证通过 | `v0.8_lyric-local-upload-ai-feasibility.md` |
| v0.7.2 | 听后感统计修复 + 等级经验详情 | 已完成 | `v0.7.2_review-stats-fix-xp-detail.md` |
| v0.7.1 | 等级经验系统与统计展示优化 | 已完成 | `v0.7.1_level-xp-system-stats-opt.md` |
| v0.7 | 个人用户界面 | 已完成 | `v0.7_personal-user-interface.md` |
| v0.0~v0.6 | 早期版本（歌词/专题周/音乐足迹 … 静态原型） | 已完成 | `history_v0.0-v0.6.md` |

**开发待办池**：跨版本「待做 / 暂不解决」见 `ai/planning/BACKLOG.md`。

# 开发指引

- 开发新功能前，先阅读 `ai/skill/` 下的规则文件：
  - `20260810_feature_development_workflow.md` — 开发流程
  - `20260810_testing_workflow.md` — 测试流程（测试先行）
  - `20260810_big_version_planning_workflow.md` — 大版本规划
- 历史排查案例见 `ai_case_notes/`，技术笔记见 `knowledge/`
