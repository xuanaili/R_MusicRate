# AI 识别歌词按钮：悬停显示 + 跨子页面切换识别持续

## 一、案例基本信息

- 问题场景分类：前端 UI/交互改造 + Vue 组件生命周期问题（v-if 切换销毁子组件导致轮询中断）
- 产生时间：2026-08-12
- 项目模块：`frontend/src/views/AlbumDetail.vue`、`frontend/src/components/albumDetail/AlbumLyricViewer.vue`
- 相似问题判定特征（下次 AI 自动识别同类问题）：
  1. 涉及「切换 Tab/子页面后功能要继续运行」的诉求（轮询、计时器、websocket 等）
  2. 子页面组件用 `v-if="activeTab === 'xxx'"` 渲染（切换即销毁）
  3. 按钮要「和 X 按钮一模一样」的交互行为（悬停显示/位置/出现条件）
  4. 无歌词提示区域里的按钮「看不到」（CSS 继承 opacity）
  5. 按钮的禁用态需要保证进度信息始终可读

## 二、原始问题描述

v0.8.1 的「AI 识别整轨歌词」按钮原本放在歌词上传/编辑弹窗内部，用户点击后弹窗关闭、识别在后台跑，但切到 听后感/评论/其他子页面后无法查看进度，且轮询若放在歌词子组件里会被销毁。用户要求：**把按钮拿出来，放在上传/编辑歌词按钮的对面（左侧），切换子页面时识别继续**。随后用户澄清核心约束：**和上传/编辑按钮完全同款行为——悬停才显示、只在歌词展示界面显示**（不是常驻悬浮按钮）。

核心诉求：
1. 按钮从弹窗移出，放到歌名标题栏左侧（与右侧「上传/编辑歌词」对称）
2. 悬停才显示（opacity 0 → 1），只在歌词展示页（lyric tab）显示
3. 点击触发后，切换 听后感/评论/其他子页面，识别照常进行、进度可查
4. 无歌词提示区也要有「上传/编辑歌词」+「AI 识别」两个按钮

## 四、最终解决方案/改造步骤

核心架构决策：**轮询逻辑迁入常驻父组件 `AlbumDetail.vue`**（该组件在整个专辑页生命周期内常驻、不随 tab 切换销毁），按钮 UI 留在会销毁的子组件 `AlbumLyricViewer.vue`，通过 **props 下传 + 事件上抛** 通信。

1. **父组件 AlbumDetail.vue 持有全部 AI 状态与方法**：
   - data 增加 `aiRecognizeLoading / aiRecognizeProgress / aiRecognizeStatusMsg / aiRecognizeTimer`
   - 方法 `triggerAiRecognize()`（POST `/api/album/lyric/recognize/<pool_id>` 拿 task_id 后 setInterval 2s 轮询）、`pollAiRecognize(taskId)`（done→`getAlbumLyrics()` 刷新歌词 + 提示；failed→报错；404→提示任务丢失）、`stopAiRecognizePolling()`（clearInterval）
   - pool id 取 `this.album.source_pool_id || this.album.id`
   - `beforeDestroy()` 与 `resetAlbumPageData()`（切换专辑时）都调用 `stopAiRecognizePolling()` 并重置 AI 状态，防止定时器泄漏/跨专辑串状态
2. **父组件使用子组件处传 props + 绑事件**：
   ```html
   :ai-recognize-loading="aiRecognizeLoading"
   :ai-recognize-progress="aiRecognizeProgress"
   :ai-recognize-status-msg="aiRecognizeStatusMsg"
   @trigger-ai-recognize="triggerAiRecognize"
   ```
3. **子组件 AlbumLyricViewer.vue 只收状态 + 抛事件**：
   - 新增 3 个 props（`aiRecognizeLoading` / `aiRecognizeProgress` / `aiRecognizeStatusMsg`，均为 default）
   - AI 按钮放 `.fixed-track-title` 内、位于上传按钮之前，`v-if="isAdmin && (showUploadBtn || aiRecognizeLoading)"`，`:disabled="aiRecognizeLoading"`；识别中文案变为「识别中… X%」（disabled 时 CSS 强制 opacity 1，保证进度常可读）
   - 进度条行放 `.fixed-track-title` 之后：`v-if="aiRecognizeLoading || aiRecognizeProgress > 0"`，含进度填充条 + 「X% · 状态消息」
   - 无歌词提示区加 `.no-lyric-btn-group`，同时放「上传/编辑歌词」+「AI 识别整轨歌词」两个按钮
4. **CSS 悬停显隐模式**（与 `.upload-lyric-btn` 同款，镜像放左侧）：
   ```css
   .ai-recognize-btn { position: absolute; left: 20px; opacity: 0; transform: scale(0.95); transition: all 0.2s ease; }
   .fixed-track-title:hover .ai-recognize-btn { opacity: 1; transform: scale(1); }
   .ai-recognize-btn:hover:not(:disabled) { opacity: 0.9; transform: scale(1.05); }
   .ai-recognize-btn:disabled { cursor: not-allowed; opacity: 1; }
   ```
5. **弹窗内**移除 AI 按钮/进度/轮询相关一切，只保留 批量上传LRC / 上传整轨LRC / 保存并上传。
6. 验证：`npx eslint` 通过 + `npm run build` 通过，git 提交。

## 五、关键代码/配置/模板（可直接复用）

父组件轮询三件套（直接复用，taskId 从 trigger 响应取）：

```js
async triggerAiRecognize() {
  if (this.aiRecognizeLoading) return;
  const poolId = this.album.source_pool_id || this.album.id;
  this.aiRecognizeLoading = true; this.aiRecognizeProgress = 0;
  this.aiRecognizeStatusMsg = '任务已创建，排队等待识别';
  try {
    const res = await this.$axios.post(`/api/album/lyric/recognize/${poolId}`, {},
      { headers: { Authorization: localStorage.getItem('token') || '' } });
    if (res.data.code !== 200) { this.$message?.error(res.data.msg || '触发 AI 识别失败'); this.aiRecognizeLoading = false; return; }
    this.aiRecognizeTimer = setInterval(() => this.pollAiRecognize(res.data.data.task_id), 2000);
  } catch (err) {
    this.$message?.error('触发 AI 识别异常：' + (err.response?.data?.msg || err.message));
    this.aiRecognizeLoading = false; this.aiRecognizeStatusMsg = '触发失败';
  }
},
async pollAiRecognize(taskId) { /* status 轮询：done → stop+刷新歌词+提示；failed → 报错；404 → 任务丢失提示 */ },
stopAiRecognizePolling() { if (this.aiRecognizeTimer) { clearInterval(this.aiRecognizeTimer); this.aiRecognizeTimer = null; } }
```

props 声明（子组件）：

```js
aiRecognizeLoading: { type: Boolean, default: false },
aiRecognizeProgress: { type: Number, default: 0 },
aiRecognizeStatusMsg: { type: String, default: '' }
```

## 六、踩坑点 & 注意事项（非常重要）

- **轮询/定时器绝不能放在 v-if 销毁的子组件里**。`AlbumLyricViewer` 是 `v-if="activeTab === 'lyric'"` 渲染，切 tab 即 unmount，定时器随销毁。必须上提到常驻父组件。
- **先确认「和 X 按钮一样」的完整约束再动手**。用户原话「放在上传/编辑歌词对面」第一次被做成主内容左上角常驻悬浮按钮（所有 tab 都显示），被否。真实约束是：悬停才显示 + 仅歌词展示页 + 与上传按钮对称。动手前应确认参考按钮的 悬停/位置/出现条件 三项。
- **`.no-lyric-upload-btn` 看不见的坑**：它无独立 CSS 规则，会继承 `.upload-lyric-btn` 的 `position: absolute; right: 20px; opacity: 0`，在无歌词提示区里永远透明不可见。凡把上传按钮同款样式复用到无歌词提示区，必须覆盖：`.no-lyric-btn-group .no-lyric-upload-btn { position: static; opacity: 1; transform: none; }`。
- **识别中的按钮不能隐藏**：`v-if` 条件里加 `|| aiRecognizeLoading`，disabled 态 `opacity: 1`，否则用户切到歌词页看不到进度入口。
- **切换专辑/离开页面要清定时器**：`beforeDestroy` + `resetAlbumPageData`（专辑切换）两处都要 `stopAiRecognizePolling()` 并重置状态，否则旧专辑轮询继续、404 报错串台。
- **bash cwd 陷阱**：`npm run build` 后 shell cwd 停在 `frontend/`，再跑 `git diff frontend/...` 会报 ambiguous argument；git 命令前先 `cd /u/MusicRate`。

## 七、同类问题快速适配规则

下次遇到相似问题，只需修改：

【适配点 1：按钮/交互目标】把 AI 按钮换成任意「切子页面要继续」的功能入口——`AlbumDetail.vue` 里的 trigger/poll/stop 三方法 + 3 个 props + `@trigger-ai-recognize` 事件绑定照抄，只改请求 URL 与提示文案。

【适配点 2：放置位置/出现条件】改 `AlbumLyricViewer.vue` 的按钮 `v-if` 条件与 CSS 定位（`left: 20px` 改 right/中心、悬停目标选择器 `.fixed-track-title:hover` 改其他容器），其余不动。

【适配点 3：无歌词提示区】往 `.no-lyric-btn-group` 加按钮时，复制同款 `.no-lyric-upload-btn` 覆盖规则，不要直接用 `.upload-lyric-btn` 原样类。

---

## 本次对话优化复盘（并入）

**浪费的环节：**
1. **第一轮方案方向理解偏差**：用户最初说「放在上传/编辑歌词的对面（左侧）」，被做成主内容左上角常驻悬浮按钮（commit `21311e8` + `f4c8961` 后用户澄清），返工一轮。教训：对「和 X 按钮一样」类表述，应先确认参考按钮的 悬停/位置/出现条件 三项再动手。
2. 好处：「轮询必须在常驻父组件」这条架构判断一次到位，无返工；顺手修掉了 `.no-lyric-upload-btn` 隐藏 bug（非本次需求但低成本）。

**快速命中清单：**
- 放悬停按钮位置 = `AlbumLyricViewer.vue` 的 `.fixed-track-title`，CSS 与 `.upload-lyric-btn` 同款镜像（`left: 20px`，`opacity:0`→悬停`1`）
- 跨子页面持续的轮询/定时器 必须留 `AlbumDetail.vue`（常驻父组件），props 下传 + 事件上抛
- 坑：`.no-lyric-upload-btn` 继承 `opacity:0` + `absolute`，放按钮进无歌词提示区必须覆盖 `position:static; opacity:1`
