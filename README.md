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
- **个人中心**：头像上传、修改密码、蒙版透明度调节、听取时长统计图表（近 N 天柱状图）
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

## 版本历史

详细变更记录见 [CHANGELOG.md](./CHANGELOG.md)。

| 版本 | 主题 |
|------|------|
| v0.7 | 个人用户界面（头像、改密、蒙版调节、统计图表） |
| v0.6 | 歌词、专题周、音乐足迹、提交评分即时保存 |
| v0.5 | 数据迁移、音频上传与解密（MP3/NCM/KGG/OGG） |
| v0.4 | 发现音乐主页、每日推荐、封面主色主题 |
| v0.3 | 听取时长记录、评分功能完善 |
| v0.2 | 专辑详情页优化、播放列表 |
| v0.1 | 搜索池、评论共享、权限 |
| v0.0 | 静态音乐列表原型 |

## 开发规划

> 详见 CHANGELOG 中保留的原始待办；以下为浓缩路线。

- **节奏可视化**：读取正在播放音乐的节奏，小球渐变拖尾动画（暂不解决）
- **独立播放组件**：将播放器抽离为全局组件，浏览其他页面时不中断播放（暂不解决）
- **歌手页面**：完善歌手属性，展示其专辑与收听记录
- **跨平台联动**：本地 MP3 与其他听歌平台互跳，规避版权
- **用户养成**：邮箱注册、头像、等级、账号顶号、查看他人音乐列表
- **推荐算法**：用户画像、每日推荐优化、年度总结报告
- **手机端适配**、**盈利模式**（专辑打榜）

## 开发指引

- 开发新功能前，先阅读 `ai/skill/` 下的规则文件：
  - `20260810_feature_development_workflow.md` — 开发流程
  - `20260810_testing_workflow.md` — 测试流程（测试先行）
  - `20260810_big_version_planning_workflow.md` — 大版本规划
- 历史排查案例见 `ai_case_notes/`，技术笔记见 `knowledge/`
