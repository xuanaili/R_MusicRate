# 评分即时防抖保存（v0.6 收尾：提交评分 bug）

## 一、案例基本信息
- 问题场景分类：前端交互 bug（评分未即时落盘）→ 前端组件改造
- 产生时间：2026-08-10
- 项目模块：`frontend/src/components/albumDetail/AlbumTrackList.vue`（评分 UI 唯一所在）
- 相似问题判定特征：
  1. "XX 只在离开页面/切歌时才保存" → 任何"离开时才落盘"的交互，都需要防抖即时保存
  2. 打分/滑块/滚轮改值 → 无即时请求（Network 无 `PUT /api/album/score/save`）
  3. 异步防抖 + 路由切换/切歌 → 竞态：回调里取 `this.album.id` 会写错专辑
  4. 父组件展示分数依赖 `album.my_score` → 需要在保存时同步 emit

## 二、原始问题描述
- 痛点：专辑评分只在 `deactivated` / `beforeDestroy` / 切歌 / 保存曲目列表时才写库（`saveAllScore`）。用户打分后若直接关页面，评分丢失；v0.7 统计依赖 `my_score` 持久化，会滞后。
- 约束：评分 UI 全在 `AlbumTrackList.vue`（整体圆环滚轮/点击/重置 + 单曲滑块拖拽/点击/滚轮），后端 `/api/album/score/save/<id>` 已存在且无需改动；仓库无 JS 测试运行器（`scoreCalc.js` 等前端逻辑同样无单测）。
- 背景：评分数组格式 `[专辑整体分, 单曲1分, 单曲2分, ...]`，0 表示未评分；总分计算见 `backend/utils/score.py` 与 `frontend/src/utils/scoreCalc.js`（必须一致）。

## 三、核心诉求
1. 打分时即时提交评分（防抖保存，不必等离开页面/切歌）
2. 防抖期间切歌/离开页面不写错专辑（快照 albumId）
3. 旧专辑快照落盘时不污染新专辑的显示分数（emit 条件控制）
4. 不产生重复请求（saveAllScore 去重）

## 四、最终解决方案/改造步骤
1. `data()` 新增：`saveScoreTimer: null`、`pendingScoreSave: null`（存 `{albumId, scoreList}` 快照）
2. 新增 4 个方法：
   - `buildScoreList()`：当前 `[this.score, ...trackList.map(i=>i.score||0)]`
   - `scheduleScoreSave()`：800ms 防抖；每次打分时**快照** `{albumId, scoreList}`（albumId 取快照时的 `this.album.id`，回调里不读 `this.album`）
   - `flushScoreSave()`：清定时器 + 立即落盘待执行快照（切歌/离开前调用）
   - `doScoreSave(albumId, scoreList)`：真正发 `PUT /api/album/score/save/<albumId>`；**仅当 `albumId === this.album.id` 才 emit `score-list-change`**
3. `saveAllScore()` 改造：先落盘 pending 快照，再 `buildScoreList()` 当前状态，若与刚保存快照 `JSON.stringify` 一致则跳过（去重）
4. `album` watcher 里 `saveAllScore()` → `flushScoreSave()`（原逻辑会把旧评分写到新专辑，属潜在 bug，顺手修掉）
5. 打分入口全部加 `scheduleScoreSave()`：`handleRatingWheel` / `handleRatingClick` / `resetRating` / `calcTrackScore`（拖拽 mousemove 天然被防抖合并）/ `handleTrackScoreWheel`

## 五、关键代码/配置/模板（可直接复用）
```js
// data()
saveScoreTimer: null,
pendingScoreSave: null, // { albumId, scoreList }

buildScoreList() {
  const scoreList = [this.score];
  this.trackList.forEach(item => scoreList.push(item.score || 0));
  return scoreList;
},
scheduleScoreSave() {
  const albumId = this.album.id;
  if (!albumId) return;
  this.pendingScoreSave = {albumId, scoreList: this.buildScoreList()};
  if (this.saveScoreTimer) clearTimeout(this.saveScoreTimer);
  this.saveScoreTimer = setTimeout(() => {
    this.saveScoreTimer = null;
    const pending = this.pendingScoreSave;
    this.pendingScoreSave = null;
    if (pending) this.doScoreSave(pending.albumId, pending.scoreList);
  }, 800);
},
flushScoreSave() {
  if (this.saveScoreTimer) { clearTimeout(this.saveScoreTimer); this.saveScoreTimer = null; }
  const pending = this.pendingScoreSave;
  this.pendingScoreSave = null;
  if (pending) this.doScoreSave(pending.albumId, pending.scoreList);
},
async doScoreSave(albumId, scoreList) {
  try {
    if (!albumId) return;
    if (albumId === this.album.id) this.$emit('score-list-change', scoreList);
    await this.$axios.put(`/api/album/score/save/${albumId}`, {score_list: scoreList}, {
      headers: {'Authorization': localStorage.getItem('token') || '', 'Content-Type': 'application/json'}
    });
  } catch (err) { console.error('保存评分失败：', err); }
},
async saveAllScore() {
  const albumId = this.album.id;
  if (!albumId) return;
  const pending = this.pendingScoreSave;
  if (this.saveScoreTimer) { clearTimeout(this.saveScoreTimer); this.saveScoreTimer = null; this.pendingScoreSave = null; }
  if (pending) await this.doScoreSave(pending.albumId, pending.scoreList);
  const scoreList = this.buildScoreList();
  if (pending && pending.albumId === albumId &&
      JSON.stringify(pending.scoreList) === JSON.stringify(scoreList)) return; // 去重
  await this.doScoreSave(albumId, scoreList);
},
```

## 六、踩坑点 & 注意事项（非常重要）
- **防抖回调里禁止取 `this.album.id`**：防抖期间 album prop 可能已切到新专辑，回调里取到的是新 id，会把旧评分写进新专辑 → 必须在 `scheduleScoreSave` 时快照 albumId
- **emit 的副作用链**：`score-list-change` → 父组件 `handleScoreList` 更新 `album.my_score` → 触发子组件 `album` deep watcher → `getAllScore()` 重新拉取。所以 `doScoreSave` 只在保存的是当前专辑时 emit，否则旧专辑快照会污染新专辑显示
- **`album` watcher 原 `saveAllScore()` 是潜在 bug**：专辑 id 直接变化时（新旧 id 都是真值），会把旧评分写到新专辑；实际路由切换因 `resetAlbumPageData()` 置 `id:0` 而多数被跳过。改为 `flushScoreSave()` 后快照指向旧专辑，天然正确
- **去重口径**：`saveAllScore` 的 pending 快照与 `buildScoreList()` 当前状态 `JSON.stringify` 一致时跳过，否则离开页面每次都会重复请求
- **`calcTrackScore` 在拖拽 mousemove 逐像素触发**：每次调 `scheduleScoreSave` 只是重置定时器，性能可忽略，且天然形成"松手 800ms 后保存"
- **验证手段局限**：前端 debounce 无 JS 测试运行器，验证 = 后端 `pytest` 回归（本次 15 passed）+ `vue-cli-service lint` + `npm run build`；交互正确性需真机（Network 观察 `PUT /api/album/score/save`）

## 七、同类问题快速适配规则
下次遇到"XX 离开页面/切歌才保存"的同类交互，只需：
- 【适配点1】换 `buildScoreList()` 里的字段来源（整体分 + 列表项）
- 【适配点2】把打分入口换成目标交互的事件（如 input/checkbox 的 `@change`）
- 【适配点3】`doScoreSave` 里的 URL 换成目标接口，emit 事件名换成父组件对应监听
- 其余（快照防抖 / flush / 去重 / emit 条件）原样复用

## 八、优化复盘（2026-08-10 本次对话）
**流程效率**：整体高效。按铁律先加载 开发 skill + 测试 skill，读 README 定位需求，再针对性读 `score.py`/`scoreCalc.js`/`AlbumTrackList.vue`/`AlbumDetail.vue` 关键段，一次定位到唯一评分入口组件，未走弯路。

**浪费点**：
1. 首次用 bash `ls` 列目录因 Windows 反斜杠转义失败 → 改用 Glob/Read 专用工具即解决。教训：列目录/搜文件一律用 Glob/Grep，不用 bash
2. 未做真机交互验证（dev server + backend + MySQL 未启动）。纯前端交互逻辑只能靠 lint/build + 代码审查兜底；下次若改动涉及时序/竞态，建议启动 `npm run serve` + 后端用 run skill 或让用户手测确认

**下次快速命中清单**：
- 评分相关文件：前端评分 UI+保存 `AlbumTrackList.vue`；评分计算 `frontend/src/utils/scoreCalc.js`；后端接口 `backend/api/score.py`；父组件总分 `AlbumDetail.vue` 的 `albumTotalScore` computed + `handleScoreList`
- 可复用模板：本文件第五节防抖保存四件套（schedule/flush/do/saveAll）
- 关键时序认知：切歌竞态靠快照 albumId 解决；emit 链会触发 deep watcher，需条件 emit
