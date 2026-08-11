# 单曲评分保存后被旧 GET 覆盖回退（打分无法立即生效）

## 一、案例基本信息
- 问题场景分类：前端交互 bug（评分回退）→ 深层 watcher 重拉竞态修复
- 产生时间：2026-08-11
- 项目模块：`frontend/src/components/albumDetail/AlbumTrackList.vue`（评分 UI + 保存唯一所在）
- 相似问题判定特征：
  1. "点击/拖动后分数不生效，点另一首才刷新" → 有异步 GET 在 PUT 后覆盖本地值
  2. Network 时序出现 `GET score/get` 紧跟在 `PUT score/save` 之后 → 保存触发重拉
  3. 子组件 `deep: true` 监听父组件传入的 `album` prop，且 watcher 内调了接口 → 父组件任何深层改动（如同步 `my_score`）都会引发重拉
  4. 保存流程走"emit → 父改 prop 深层字段 → 子 deep watcher 再取数" 的回路 → 竞态高发
  5. 先写最小脚本验证 Vue 响应式正常，再怀疑"异步覆盖"，能快速收敛

## 二、原始问题描述
- 痛点：用户点击单曲评分进度条，分数短暂显示后被**覆盖回退**（0→70→0），表现为"打分不生效"；再点另一首单曲才"刷新"出第一首的分。用户反馈"整个单曲评分功能实现有些问题"。
- 约束：评分 UI 全在 `AlbumTrackList.vue`（单曲滑块拖拽/点击/滚轮 + 整体圆环滚轮/点击/重置）；前端无 JS 测试运行器，验证依赖 Playwright 真机 + Network 观察。
- 背景：v0.6 引入了防抖即时保存（`scheduleScoreSave` 800ms → `doScoreSave` → emit `score-list-change` → 父组件 `handleScoreList` 改 `album.my_score`）。这个"保存成功即同步父组件展示"的链路，副作用是触发了子组件 `album` deep watcher 无条件调 `getAllScore()` 重拉。

## 三、核心诉求
1. 点击/拖动/滚轮打分后，显示分数持续保持，不被回退
2. 保存动作不再触发多余的评分重拉（消除竞态源）
3. 兼容挂载期未完成的 GET / 专辑切换期间的用户打分，不被过期响应覆盖
4. 不破坏 v0.6 的防抖保存、切专辑 flush、emit 展示同步

## 四、最终解决方案/改造步骤
1. **定位根因（Playwright 复现 + Network 时序）**：
   - 点击 70% → 0ms/100ms/300ms 显示 70 ✅
   - 800ms 防抖触发 → `PUT score/save` 与 `GET score/get` **同一时刻发出**
   - 重拉 GET 抢在 PUT 提交前返回 DB 旧值 0 → `getAllScore` 把 `trackList[i].score` 覆盖回 0
2. **改造一（根因切断）**：`album` watcher 只响应专辑切换（新旧 id 不同，含经 `id=0` 的重置过渡），同一专辑的深层变化不再调 `initTrackList` / `getAllScore`：
   ```js
   album: {
     handler(newVal, oldVal) {
       const oldId = oldVal && oldVal.id;
       const newId = newVal && newVal.id;
       if (oldId !== newId) { // 仅专辑切换才重置+重拉
         if (oldId) this.flushScoreSave(); // 旧 id 有效即落盘待保存快照
         this.initTrackList(false);
         this.initFavouriteTrackList(false);
         this.getAllScore();
       }
     }, deep: true
   }
   ```
   同专辑内 `tracks`/`favourite_tracks` 的更新由对应 prop watcher 处理，不依赖 album watcher。
3. **改造二（防御性双守卫）**：`getAllScore` 发起时快照 `albumId` 与 `scoreEditVersion`，响应到达时任一变化则丢弃：
   ```js
   const albumId = this.album.id;
   const reqVersion = this.scoreEditVersion;
   const res = await this.$axios.get(`/api/album/score/get/${albumId}`, {headers: ...});
   if (this.album.id !== albumId) return;            // 已切专辑
   if (this.scoreEditVersion !== reqVersion) return; // 期间用户继续打分
   ```
4. **改造三（版本号递增）**：`data()` 新增 `scoreEditVersion: 0`；在 5 个用户打分入口递增：`calcTrackScore`（滑块拖拽/点击共用）、`handleTrackScoreWheel`、`resetRating`、`handleRatingWheel`、`handleRatingClick`。`getAllScore` 自身写分不递增（是加载不是编辑）。

## 五、关键代码/配置/模板（可直接复用）
- **Vue 2 响应式最小验证脚本**（先排除"响应式失效"再查竞态）：
  ```js
  const Vue = require('vue/dist/vue.common.js');
  const state = Vue.observable({ trackList: [] });
  const vm = new Vue();
  vm.$watch(() => state.trackList.map(t => t.score).join(','), nv => changes.push(nv));
  // 注意：Vue2 watcher 异步 flush，断言前必须 await Vue.nextTick()
  state.trackList[0].score = 50;
  await Vue.nextTick();
  ```
- **Playwright 复现模板**（msedge 通道，无需下载浏览器）：
  ```js
  import { chromium } from 'playwright';
  const browser = await chromium.launch({ channel: 'msedge' });
  await page.addInitScript(() => { /* 预置 token/is_admin/user_id 到 localStorage */ });
  await page.goto('http://localhost:8080/#/album/detail/43', { waitUntil: 'networkidle' });
  await page.getByText('曲目列表', { exact: true }).first().click();
  const box = await page.locator('.track-score-slider').nth(i).boundingBox();
  await page.mouse.click(box.x + box.width * frac, box.y + box.height / 2);
  // SPA 内切专辑：page.evaluate(i => { location.hash = '#/album/detail/' + i })——不要用 page.goto
  ```
- **后端可直查验证**：`curl -X PUT /api/album/score/save/<id>` 重置评分；`curl /api/album/score/get/<id>` 核对 DB。

## 六、踩坑点 & 注意事项（非常重要）
- **"保存→emit→父改 prop→子 deep watcher→重拉接口" 是竞态源**：任何子组件 `deep:true` 监听父传对象且内部调接口，都会因父组件同步展示（改 `my_score`）而触发重拉。凡是"保存后同步展示"的链路，要么条件 emit，要么 watcher 加 id 切换守卫。
- **异步 GET 覆盖本地值前必须校验**：校验"发起时快照的版本号 + 专辑 ID"，两者之一变化就丢弃。否则挂载期未完成的 GET、切专辑途中的 GET 都会污染显示。
- **`flushScoreSave` 触发条件**：旧代码要求新旧 id 都非空才 flush，经 `id=0` 重置过渡（`resetAlbumPageData`）时会漏掉 → 改为"旧 id 有效即 flush"，切专辑更可靠。
- **专辑切换会经过 `id=0` 重置**：守卫不能写成"新旧 id 都真值且不同"，否则 43→0→47 的两次过渡都被跳过；应写成 `oldId !== newId`（含 0 与 undefined 参与比较）。
- **Playwright 用 `page.goto` 是整页重载**：组件销毁、`beforeDestroy` 里的异步保存不可靠，还会丢 SPA 状态 → SPA 内路由切换必须改 `location.hash`。
- **Playwright 复现会写真实库**：测试后必须把改动的专辑评分还原（本次还原了 43/50 号），否则污染用户数据。
- **Vue 2 响应式验证有坑**：未挂载实例的 computed 不会求值、watcher 是异步 flush → 用 `vm.$watch(getter)` + `await Vue.nextTick()`，同步断言会误判"非响应式"。

## 七、同类问题快速适配规则
下次遇到"XX 改了不生效 / 被回退 / 点别的才刷新"的同类交互，只需：
- 【适配点1】Network 看 `GET` 是否紧跟 `PUT` 之后 → 是，则找保存→emit→deep watcher 重拉链路，watcher 加 id 切换守卫
- 【适配点2】把 `getAllScore` 的双守卫换成目标取数函数（发起时快照 id + 版本号，返回后校验）
- 【适配点3】把 `scoreEditVersion` 递增点换成目标交互的事件入口
- 【适配点4】先跑 Vue 响应式最小脚本排除响应式问题，再查竞态；Playwright 复现模板原样套用
- 其余（deep watcher 改造 / flush 条件 / 守卫逻辑）原样复用

## 八、优化复盘（2026-08-11 本次对话）
**流程效率**：按铁律先加载开发 skill + 测试 skill；读 `AlbumTrackList.vue`/`AlbumDetail.vue`/`score.py`/`scoreCalc.js` 关键段定位；最终靠 **Playwright 真机复现 + Network 时序** 一次拿到根因（GET→PUT→GET 同刻），比纯读码推演高效得多。

**浪费点**：
1. **在"响应式失效"假设上反复推演了多轮**（约 6 次读码/推演），直到写 Vue 2 Reactivity 最小脚本才确认响应式正常、转向竞态假设。教训：遇到"数据改了 UI 不变"类问题，先跑最小脚本验证响应式，再怀疑异步覆盖，别在代码里空转。
2. **Reactivity 脚本本身踩了两处坑**（未挂载实例 computed 不求值、Vue2 watcher 异步 flush），第一次误判"非响应式"。教训：Vue 2 验证用 `vm.$watch(getter)` + `await nextTick()`。
3. **验证脚本场景 C 用 `page.goto` 整页重载**，组件销毁、异步 flush 不可靠，且脚本忘了切回专辑就读显示，白白多跑一轮。教训：SPA 内切换用改 `location.hash`。
4. **Playwright 复现污染了真实用户数据**（43/50 号专辑评分被改），最后手动还原。教训：跑完立刻还原测试数据。

**下次快速命中清单**：
- 评分相关文件：前端评分 UI+保存 `AlbumTrackList.vue`；父组件总分/同步 `AlbumDetail.vue`（`albumTotalScore` + `handleScoreList`）；后端接口 `backend/api/score.py`
- 可复用：Vue 2 响应式最小验证脚本、Playwright 复现模板（msedge 通道）、双守卫 + 版本号递增逻辑
- 关键时序认知：emit→父改 prop→deep watcher→重拉 = 竞态源；异步 GET 覆盖前校验版本号+专辑ID；专辑切换经 `id=0` 过渡
- 验证手段：`npm run serve` + 后端已运行（MySQL80 自动起），Playwright 用系统 Edge，无需下载浏览器
