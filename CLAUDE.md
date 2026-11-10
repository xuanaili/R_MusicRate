# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

MusicRate 是一个音乐专辑评分与发现的 Web 应用。用户可以给专辑打分、写听后感、管理播放列表、上传音频文件，以及通过标签/气泡图探索音乐。界面以中文为主，风格标签格式为 `English【中文】`。

### 与 P_Workflow 的关系（重要）

本项目的 `ai/` 文件夹与 `CLAUDE.md`（含 `README.md`）由 **P_Workflow** 跨项目 AI 知识统一管理仓库托管：

- **真身**位于 `U:\P_Workflow\MusicRate\`
- 本项目目录 `U:\MusicRate` 下的 `ai\` 为**目录联接（Junction）**、`CLAUDE.md` 与 `README.md` 为**硬链接（Hardlink）**，均指向上述真身
- 在本项目目录读写 `ai/`、`CLAUDE.md` 或 `README.md`，实际操作的就是 P_Workflow 中的真身——**只有一个真身，杜绝两份不同步**

`ai/` 文件夹是本项目的 AI 知识库，用于沉淀对话中产生的技能、知识和案例笔记。它由三个子目录组成：

| 子目录 | 归属内容 | 文件命名 |
|---|---|---|
| `ai/ai_case_notes/` | 解决了 bug、排查了问题、修复了错误（归档型） | `YYYYMMDD_简短英文描述.md` |
| `ai/knowledge/` | 学习了技术、记录了配置方法、整理了参考信息（归档型） | `YYYYMMDD_主题.md` |
| `ai/skill/` | 总结了工作流程、制定了编码规范、提炼了操作步骤（归档型） | `YYYYMMDD_技能名.md` |
| `ai/planning/` | 版本规划：进行中/已定稿/已完成的版本设计（**工作文档，非归档**） | `v0.x_简短英文描述.md`（按版本号） |

每个子目录都有 `00_template.md` 模板，新增内容时先读模板再按格式写。

## 技术栈

- **前端**: Vue 2.6 + Vue Router 3 (hash 模式) + Vue CLI 5, Axios, ECharts 5
- **后端**: Python Flask + Flask-CORS, PyMySQL, bcrypt
- **数据库**: MySQL 8 (InnoDB, utf8mb4)
- **音频工具**: ffmpeg, NCM/KGG/OGG 解密（位于 `portable/`）

## 开发命令

```bash
# 前端（在 frontend/ 目录下）
npm run serve     # 开发服务器 http://localhost:8080
npm run build     # 生产构建
npm run lint      # ESLint 检查

# 后端（在项目根目录下）
# 注意：便携 Python 的 cwd 不在 sys.path 中，必须用脚本文件方式启动（run.py 内部自带 sys.path.insert）
# 不要用 `python -m backend.run`，会报 ModuleNotFoundError: No module named 'backend'
PYTHONIOENCODING=utf-8 portable\python\python.exe backend/run.py   # 启动 Flask http://0.0.0.0:5000（Windows 下会自动启动 MySQL80 服务）
```

### Windows 防火墙（localhost）

**禁止关闭三个防火墙配置文件**（全关 = 局域网/公网都能访问 5000/8080）。打不开的常见元凶：首次启动弹窗点“取消”生成的 python/node 阻止规则。一键修复（管理员运行，会弹 UAC；幂等，日志 `portable\firewall_dev_log.txt`，属本机小工具不入库）：

```powershell
powershell -ExecutionPolicy Bypass -File .\portable\firewall_dev.ps1
```

作用：开启三配置文件 + 仅放行本机回环 127.0.0.1/::1 的 5000/8080 + 清除误建阻止规则；局域网手机调试见脚本头注释。

### 测试（pytest）

测试统一放在 `backend/tests/`，使用 pytest 框架（已装入便携 Python）：
```bash
portable\python\python.exe -m pytest                 # 快速单测（默认跳过 realdata）
portable\python\python.exe -m pytest -m realdata     # 真实 DB/网络集成测试
portable\python\python.exe -m pytest backend/tests/test_xxx.py -k 关键词   # 单文件/定向
```
- 纯逻辑单测不依赖 MySQL / 网络，改完可直接跑；首批参考 `backend/tests/test_score.py`（评分计算）、`test_json.py`（safe_json_loads）
- `pytest.ini` 已配 `testpaths = backend/tests`（避免误收 site-packages 自带测试）+ `addopts = -m "not realdata"`
- 开发/测试流程详见 `ai/skill/20260810_feature_development_workflow.md` 与 `20260810_testing_workflow.md`
- `backend/test.py` 为空文件，`frontend/playwright` 尚未配置（未使用）

## 架构

### 前后端通信

- 前端运行在 `:8080`，后端运行在 `:5000`
- Axios 配置：`baseURL = apiOrigin()`（`frontend/src/utils/apiBase.js`），即「页面自身主机 + 5000 端口」，**不再写死 localhost**——本机打开 = localhost:5000，手机用局域网 IP 打开 = 同一主机:5000
  - 需要前端连另一台机器时：控制台 `localStorage.setItem('backend_origin', 'http://10.0.0.5:5000')` 后刷新
  - 后端写进数据库的媒体绝对地址（封面/缩略图/音频/头像）由响应拦截器 `normalizeBackendUrls()` 统一改写到当前主机，换网络后旧 IP 也能自动纠正
- 后端 `HOST` 自动跟随当前局域网 IP（`backend/config.py`：环境变量 `MUSICRATE_HOST` > `backend/data/lan_host.txt` > 自动探测 > localhost），新上传文件生成的地址永远与当前网络一致
- Token 认证：通过 `Authorization` 请求头传递，存储在 `localStorage`
- 401 响应自动清除 localStorage 并跳转到 `/login`
- CORS 由 `flask_cors` 正则 `.*` 放行任意来源（开发期换 IP 不用改配置）

### 局域网（手机）访问

1. 手机与电脑同一网络，访问 `http://<电脑局域网IP>:8080`
2. 表里存量的旧地址（localhost / 换网络前的旧 IP）用工具批量改写（本机小工具，`portable/` 不入库）：

```bash
portable\python\python.exe portable\tools\db_change.py list      # 只看现状：旧域名统计 + 影响行数
portable\python\python.exe portable\tools\db_change.py           # 交互式选地址后替换
portable\python\python.exe portable\tools\db_change.py auto      # 直接用 backend/config.py 当前生效地址
```

改写逻辑在 `backend/utils/net_domain.py`（纯逻辑有单测 `backend/tests/test_net_domain.py`）：只替换「localhost / 任意 IPv4 + 后端 5000 端口」前缀，外链不动；`album_pool`、`albums_%`、`users` 的 `cover_img / mp3_url / avatar` 字段，字段按 information_schema 取交集（老表缺列也不会报错）。

### 后端结构

- `backend/__init__.py` — Flask 应用工厂 (`create_app()`)，注册 CORS、teardown 和所有路由
- `backend/run.py` — 启动入口：自动启动 MySQL80 Windows 服务，调用 `init_base_tables()`，运行 Flask
- `backend/config.py` — 全局配置：MySQL 凭据、文件路径、管理员默认值、NCM 解密设置
- `backend/api/` — 路由模块，每个模块通过 `register_*_routes(app)` 注册路由：
  - `auth.py` — 登录/注册
  - `album.py` — 用户专辑增删改查（私有副本）
  - `album_pool.py` — 公共专辑池（共享模板）
  - `score.py` — 评分读取/保存
  - `review.py` — 听后感
  - `comment.py` — 公共评论
  - `audio_resource.py` — 音频上传/服务
  - `playlist.py` — 用户播放列表
  - `listening.py` — 听取时长记录
  - `recommend.py` — 每日推荐
  - `tags.py` — 音乐风格标签增删改查及层级关系
  - `lyric.py` — 歌词（LRC 格式）
  - `share.py` — 专题周
  - `unlock.py` — 音频文件解密（NCM/KGG/OGG）
  - `upload_utils.py` — 文件上传路由注册
- `backend/utils/` — 共享工具函数：
  - `db.py` — 核心数据库层：`get_db()`、`get_album_table_name(user_id)`、所有建表函数、`init_base_tables()`
  - `decorators.py` — `@login_required` 装饰器（验证 token，设置 `g.current_user_id`）
  - `auth.py` — `encrypt_password()` / `verify_password()`（bcrypt）
  - `score.py` — `calculate_album_total_score()` — 加权计算：专辑分 × 0.6 + 单曲均分 × 0.4
  - `json.py` — `safe_json_loads()`，从文本中自动提取歌手/专辑/标签
  - `intro.py` — 用户专辑简介同步
  - `ncm_unlock.py`、`kgg_converter.py`、`unlock.py` — 音频解密逻辑

### 前端结构

- `frontend/src/main.js` — Vue 入口：路由配置、Axios 配置、认证拦截器、全局路由守卫
- `frontend/src/views/` — 页面级组件：
  - `AlbumDetail.vue` — 专辑详情主页面（约 92KB，最大的组件）
  - `AlbumPoolDetail.vue` — 公共池专辑详情
  - `TagDetail.vue` — 风格标签详情页
  - `WebHome.vue` — 发现音乐主页
  - `LoginPage.vue` / `RegisterPage.vue`
- `frontend/src/components/` — 按功能分组的子组件：
  - `albumDetail/` — AlbumBaseInfo, AlbumCommentSection, AlbumLyricViewer, AlbumReviewEditor, AlbumTrackList
  - `discoverMusic/` — CategoryList, DailyRecommend, MusicSpecial, RankingList, SingerList
  - `sidebar/` — AddAlbum, AddTag, EditPoolAlbum, EditTag, AlbumAudioUpload, PlayerPlaylist, TrackParse, UnlockParse
  - `myMusic/` — MusicList, PlayList, YearMusic
  - `searchMusic/` — SearchAlbumPool
  - `item/` — AlbumItem, AlbumPoolItem
  - `RhythmBall.vue` — 节奏小球动画
  - `TagBubbleChart.vue` — ECharts 气泡图
- `frontend/src/config/index.js` — 标签气泡动画配置（每个风格的尺寸、速率、权重）
- `frontend/src/utils/scoreCalc.js` — 前端评分计算（与后端逻辑一致）

### 数据库关键模式

- **用户分表**：每个用户拥有独立的 `albums_{user_id}` 表，存储其私有专辑副本
- **用户表数量 = 用户数量**（线上库 1199 张 `albums_%`，其中多数是历史/测试用户建的**空表**）。任何「遍历 `albums_%`」的查询都必须走批量方案：`backend/utils/tag.py` 的 `get_album_tag_stats_map(cursor, pool_ids)` = 一次 UNION ALL 分块扫描（`UNION_CHUNK_SIZE`） + 全量快照缓存（`CACHE_TTL_SECONDS=120`，`invalidate_cache()` 可主动失效）
  - ⚠️ 反面教材（v0.9 修复）：老版 `get_album_tag_stats` 对**每张**专辑都 `SELECT ... FROM albums_N WHERE source_pool_id=%s` 扫全部 1199 张表 ≈ 1.0s/张，搜索一页 10 张 ≈ 11s，超过前端 axios 10s 超时 → 页面永远停在「搜索中」。修复后：首次 0.7s（建缓存），之后 50ms
  - 同理，`album_pool.py` 里删除/同步公共专辑时遍历用户表的逻辑（低频路径）仍未批量优化，改这些功能时注意别再引入「每专辑一次全表遍历」
- **共享表**：`album_pool`（公共模板）、`users`、`user_playlist`、`user_recommend`、`user_album_intro`、`album_tags`、`singers`、`album_singers`
- **JSON 列**：多个字段以 TEXT 类型存储 JSON 数组（tracks、my_score、tags、favourite_tracks、tracks_time、playlist）
- **评分格式**：`[专辑整体评分, 单曲1评分, 单曲2评分, ...]`，0 表示未评分
- **管理员角色**：`users` 表中 `is_admin=1`；管理员专属功能包括添加/编辑池专辑、标签、上传音频

### 认证流程

1. 登录 → 后端返回 token → 存入 `localStorage`
2. 每次请求附带 `Authorization: <token>` 请求头
3. `@login_required` 装饰器验证 token 与 MySQL `users.token` 是否匹配
4. 验证通过后设置 `g.current_user_id` 供后续使用
5. `main.js` 中的路由守卫将未认证用户重定向到 `/login`

### 评分计算逻辑

- 专辑总分 = `专辑整体评分 × 0.6 + 单曲均分 × 0.4`（评分为 0 的单曲不计入）
- 若无有效单曲评分，总分 = 专辑整体评分
- 分数范围：0–100，保留 1 位小数

## 开发约定

- 路由注册模式：每个 API 模块导出 `register_*_routes(app)`，由 `backend/api/__init__.py` 统一调用
- 前端使用 `@/` 别名指向 `src/`
- API 响应格式：`{"code": 200/401/500, "msg": "...", "data": ...}`
- 注释和 UI 文本使用中文；风格/标签名使用英文
- Vue Router 使用 hash 模式（`mode: 'hash'`）以兼容移动端
- 管理员专属功能在后端通过 `is_admin` 标志判断
- **本机小工具习惯**：主目录不堆脚本——本机私有的启动/修复/诊断类脚本（如 `portable/start_musicrate.bat/.ps1` 一键启动、`portable/firewall_dev.ps1` 防火墙修复）一律放 `portable/`（`.gitignore` 已整体忽略，不入库）；只有项目代码与文档才进 git。ps1 一律保存为 UTF-8 **带 BOM**（Windows PowerShell 5.1 按 ANSI 误读无 BOM 文件会报语法错）


## 文档导航（重要）

按需 read，不要每次全量加载：

- **版本规划** → `ai/planning/`（按版本号命名，当前 v0.9.x；跨版本待办见 `BACKLOG.md`，先读 `00_template.md`）
- **基础概念（跨版本稳定）** → `ai/knowledge/`（数据库模式 / 认证 / 评分 / 音频管线）
- **技能与流程** → `ai/skill/`
- **README.md**：只保留稳定信息 + 版本演进索引（一行一版本，2026-08-30 起规划不再写进 README）

## 铁律
- 每次修改，都要 git 提交并 **push 到 GitHub 远程 origin**（GitHub 为唯一真相源，commit 后必须 push），并说明修改内容
- 开发新功能前，必须先阅读 `ai/skill/` 目录下的规则文件，避免重复踩坑
- **版本规划**：按 `ai/skill/20260810_big_version_planning_workflow.md` 执行——规划产出 = **在 `ai/planning/` 新建 `v0.x_*.md`（先读 `00_template.md`，README 只加一行版本演进索引）+ git 提交**，不进 plan mode、不出独立方案文件；需用户拍板的决策用 AskUserQuestion
- **新需求（新对话）启动时，先同时加载「开发 skill」`ai/skill/20260810_feature_development_workflow.md` +「测试 skill」`ai/skill/20260810_testing_workflow.md`**，两者成对使用：测试先行→实现→跑测试→提交，互相验证修改；测试失败 = 改代码或按新需求改测试，不得静默跳过

## 对话结束归档

当用户说"结束对话"、"对话结束"、"归档"等关键词时，**必须**依次执行【优化复盘】+【归档】两个步骤，不能只说"好的"就结束。

### 第一步：优化复盘（先）

在回复中先总结本次对话：
1. 本次流程中哪些环节浪费了时间/轮次（如：应先建单元测试调对再批量跑、Windows 环境坑、重复验证、未测真实接口等）
2. 下次解决同类问题的快速命中清单（哪些文件/函数可直接复用、只改哪些参数/字典）
优化复盘内容须并入第二步生成的归档文档，作为独立小节。

### 第二步：归档（后）

1. 回顾本次对话，判断内容属于哪个 `ai/` 子目录：
   - `ai_case_notes/` — 解决了 bug、排查了问题、修复了错误
   - `knowledge/` — 学习了技术、记录了配置方法、整理了参考信息
   - `skill/` — 总结了工作流程、制定了编码规范、提炼了操作步骤
2. 读取对应子目录的 `00_template.md` 模板
3. 按模板格式生成总结文档，命名规则 `YYYYMMDD_简短英文描述.md`，并把第一步的优化复盘并入
4. 告知用户文件已保存的路径和简要内容

## 归档与推送流程

1. 在本项目目录 `U:\MusicRate\ai\<子目录>\` 下按模板写新 md（直接落进 P_Workflow 真身）
2. 切到 `U:\P_Workflow`，提交并推送：

```bash
cd U:\P_Workflow
git add -A
git commit -m "归档: MusicRate/<子目录> <简述>"
git push
```

3. push 前确保 VPN 已开（走 `127.0.0.1:7897` 代理）
4. **铁律：禁止触碰 `rdgitlab.wbtz.cloud`**——本项目的任何 git / 链接操作都不得涉及公司 GitLab 远程，只动本地文件系统与 P_Workflow 的 GitHub 远程
