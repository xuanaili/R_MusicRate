# 前端组件结构参考

## 一、组件目录树

```
frontend/src/
├── main.js                    # 入口：路由、Axios、拦截器
├── App.vue                    # 根组件（仅含router-view）
├── config/index.js            # 标签气泡动画配置（150+标签）
├── utils/scoreCalc.js         # 评分计算函数
├── assets/css/
│   ├── global.css             # 全局基础样式
│   └── star.css               # 星级评分样式
├── views/                     # 页面级组件
│   ├── LoginPage.vue          # 登录页（156行）
│   ├── RegisterPage.vue       # 注册页（143行）
│   ├── WebHome.vue            # 主页：Tab容器（529行）
│   ├── AlbumDetail.vue        # 专辑详情页（2832行，最大组件）
│   ├── AlbumPoolDetail.vue    # 公共池专辑详情（884行）
│   └── TagDetail.vue          # 标签详情页（1773行）
├── components/
│   ├── albumDetail/           # 专辑详情子组件
│   │   ├── AlbumBaseInfo.vue      # 基础信息（739行）
│   │   ├── AlbumCommentSection.vue # 评论区（577行）
│   │   ├── AlbumLyricViewer.vue   # 歌词查看器（1933行）
│   │   ├── AlbumReviewEditor.vue  # 听后感编辑（1002行）
│   │   └── AlbumTrackList.vue     # 曲目列表（1154行）
│   ├── discoverMusic/         # 发现音乐子组件
│   │   ├── CategoryList.vue       # 音乐类型分类（526行）
│   │   ├── DailyRecommend.vue     # 每日推荐（868行）
│   │   ├── MusicSpecial.vue       # 音乐专题（1174行）
│   │   ├── RankingList.vue        # 排行榜（占位43行）
│   │   └── SingerList.vue         # 歌手列表（占位44行）
│   ├── myMusic/               # 我的音乐子组件
│   │   ├── MusicList.vue          # 专辑列表（772行）
│   │   ├── PlayList.vue           # 播放列表（占位39行）
│   │   └── YearMusic.vue          # 年度音乐（占位39行）
│   ├── searchMusic/           # 搜索音乐
│   │   └── SearchAlbumPool.vue    # 公共池搜索（658行）
│   ├── sidebar/               # 侧边栏组件
│   │   ├── AddAlbum.vue           # 添加专辑（754行）
│   │   ├── AddTag.vue             # 添加标签（617行）
│   │   ├── AlbumAudioUpload.vue   # 音频上传（558行）
│   │   ├── EditPoolAlbum.vue      # 编辑池专辑（835行）
│   │   ├── EditTag.vue            # 编辑标签（628行）
│   │   ├── PlayerPlaylist.vue     # 播放器播放列表（1273行）
│   │   ├── TrackParse.vue         # 曲目解析（286行）
│   │   └── UnlockParse.vue        # 解密解析（875行）
│   ├── item/                  # 列表项组件
│   │   ├── AlbumItem.vue          # 用户专辑卡片（294行）
│   │   └── AlbumPoolItem.vue      # 公共池专辑卡片（272行）
│   ├── RhythmBall.vue         # 节奏小球动画（495行）
│   └── TagBubbleChart.vue     # ECharts气泡图（427行）
```

---

## 二、页面级组件详解

### 1. WebHome.vue — 主页容器

**功能**：一级Tab（发现音乐/我的音乐/搜索音乐）+ 二级Tab切换

**Tab结构**：
```
发现音乐 → 今日推荐 | 音乐类型 | 音乐专题 | 排行榜 | 歌手
我的音乐 → 专辑列表 | 播放列表 | 年度音乐
搜索音乐 → 专辑搜索
```

**主题色系统**：
- `mainColor` / `mainColorDark` / `mainColorDarkDouble` — 通过props传递给子组件
- 子组件通过 `@sendThemeColor` 事件向上传递主题色变更
- 主题色持久化到localStorage（persistMainColor等）

**背景图系统**：
- `coverBgUrl` — 全屏模糊背景图
- 子组件通过 `@sendCoverBg` 事件向上传递背景图URL
- 背景图持久化到localStorage（persistCoverBg）

### 2. AlbumDetail.vue — 专辑详情页（最大组件2832行）

**功能**：专辑完整信息展示+编辑+播放+评分+评论

**核心子组件**：
- `AlbumBaseInfo` — 基础信息（封面、专辑名、歌手、标签等）
- `AlbumTrackList` — 曲目列表（含单曲评分、收藏标记）
- `AlbumReviewEditor` — 听后感编辑
- `AlbumCommentSection` — 公共评论
- `AlbumLyricViewer` — 歌词查看器
- `PlayerPlaylist` — 播放器播放列表

**侧边栏组件**：
- `AddAlbum` — 添加专辑侧边栏
- `UnlockParse` — 音频解密侧边栏
- `AlbumAudioUpload` — 音频上传侧边栏
- `TrackParse` — 曲目解析侧边栏

**数据流**：
- 路由参数：`this.$route.params.id` 或 `this.$route.query.id`
- API调用：`GET /api/album/detail/{id}` → 填充所有子组件
- 子组件通过 `$emit` 事件通信

### 3. AlbumPoolDetail.vue — 公共池专辑详情

**功能**：公共池专辑展示+复制+评论

**API**：`GET /api/album/pool/detail/{poolId}`

### 4. TagDetail.vue — 标签详情页

**功能**：标签详情+关联专辑列表+年份统计+标签树

**API**：
- `GET /api/tags/detail?tagName=...`
- `GET /api/tags/album/list?tagName=...`
- `GET /api/tags/album/year-stats?tagName=...`
- `GET /api/tags/tree`

---

## 三、占位组件（开发中）

| 组件 | 位置 | 说明 |
|------|------|------|
| RankingList | discoverMusic/ | 排行榜占位 |
| SingerList | discoverMusic/ | 歌手列表占位 |
| PlayList | myMusic/ | 播放列表占位 |
| YearMusic | myMusic/ | 年度音乐占位 |

---

## 四、列表项组件

### AlbumItem.vue — 用户专辑卡片
- **Props**：`music` (Object), `mainColor`, `mainColorDark`, `mainColorDarkDouble`
- **事件**：`@add-comment`
- **功能**：封面图+专辑名+评分+歌手+年份+标签+已听时长
- **评分**：优先使用 `calculated_score`，否则用 `calculateAlbumTotalScore()` 计算
- **标签展示**：提取英文展示，中文做title悬浮提示

### AlbumPoolItem.vue — 公共池专辑卡片
- **Props**：`album` (Object), `isAdmin` (Boolean), `mainColor`, `mainColorDark`, `mainColorDarkDouble`
- **事件**：`@copy-album`, `@view-detail`, `@delete-album`
- **功能**：封面+专辑名+复制按钮+删除按钮(管理员)+标签统计

---

## 五、侧边栏组件模式

所有侧边栏组件共用相同模式：
- **Props**：`visible` (Boolean) 控制显示/隐藏
- **事件**：`@close` 关闭侧边栏
- **样式**：右侧滑入动画，半透明遮罩
- **主题色**：通过props接收 `mainColor`/`mainColorDark`/`mainColorDarkDouble`

---

## 六、动画组件

### RhythmBall.vue — 节奏小球
- **Props**：`tag` (标签名), `mainColor`, `mainColorDark`
- **配置**：从 `config/index.js` 读取 `ballConfig[tag]`
- **参数**：`minSize/maxSize/minRate/maxRate/numWeight`
- **动画**：CSS `@keyframes` 呼吸动画，随机位置/速度/大小

### TagBubbleChart.vue — ECharts气泡图
- **Props**：`tagStats` (标签统计数据), `mainColor`
- **图表**：ECharts scatter类型，气泡大小=标签占比，颜色随机
