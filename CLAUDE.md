# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

MusicRate 是一个音乐专辑评分与发现的 Web 应用。用户可以给专辑打分、写听后感、管理播放列表、上传音频文件，以及通过标签/气泡图探索音乐。界面以中文为主，风格标签格式为 `English【中文】`。

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
python -m backend.run   # 启动 Flask http://0.0.0.0:5000（Windows 下会自动启动 MySQL80 服务）
```

项目暂无测试框架。`backend/test.py` 为空文件，`frontend/playwright` 尚未配置。

## 架构

### 前后端通信

- 前端运行在 `:8080`，后端运行在 `:5000`
- Axios 配置：`baseURL = 'http://localhost:5000'`，`withCredentials: true`
- Token 认证：通过 `Authorization` 请求头传递，存储在 `localStorage`
- 401 响应自动清除 localStorage 并跳转到 `/login`
- CORS 仅允许 `localhost:8080` 来源

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

## 铁律
- 每次修改，都要git上传，并说明修改内容
- 开发新功能前，必须先阅读 `ai/skill/` 目录下的规则文件，避免重复踩坑

## 对话结束归档

当用户说"结束对话"、"对话结束"、"归档"等关键词时，**必须**执行归档流程，不能只说"好的"就结束：

1. 回顾本次对话，判断内容属于哪个 `ai/` 子目录：
   - `ai_case_notes/` — 解决了 bug、排查了问题、修复了错误
   - `knowledge/` — 学习了技术、记录了配置方法、整理了参考信息
   - `skill/` — 总结了工作流程、制定了编码规范、提炼了操作步骤
2. 读取对应子目录的 `00_template.md` 模板
3. 按模板格式生成总结文档，命名规则 `YYYYMMDD_简短英文描述.md`
4. 告知用户文件已保存的路径和简要内容