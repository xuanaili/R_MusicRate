# 案例：专辑听取进度续播 + 异常退出漏报 listening_progress（keepalive 兜底）

## 一、案例基本信息

- 问题场景分类：后端存储字段扩展 + 前端播放进度续播 + 组件销毁/页面卸载上报丢请求（Vue 2 + 跨域 8080→5000）
- 产生时间：2026-08-11
- 项目模块：`backend/api/listening.py`（pause 接口）、`backend/utils/db.py`（用户专辑表 DDL）、`backend/api/album.py`（详情接口）、`frontend/src/views/AlbumDetail.vue`（播放器/退出上报）
- 相似问题判定特征（用于下次自动识别同类问题）：
  1. 需求是「暂停/退出时上传 X、下次进入恢复 X」→ 大概率走 `listening_*` 同构模式（`listening_duration` 是现成范本）
  2. 某数据只在**播放中/详情页**有意义，需要「直接点返回/关页签也能保存」→ 组件销毁 + 页面卸载两条路都要覆盖
  3. `beforeDestroy` 里放了异步请求但**实际没发出** → 检查 `fadeOutVolume` 延迟回调 + `$refs` 守卫是否被销毁置空
  4. 跨域（:8080→:5000）+ 自定义头（Authorization）在卸载时上报 → 同步 XHR 不可行，用 `fetch(keepalive:true)`
  5. realdata 测试往旧表插数据报 `1364 doesn't have a default value` → 查 `information_schema` 的 NOT NULL 无默认值遗留列

## 二、原始问题描述

两个递进需求：

1. **续播**：进入专辑详情页播放后，暂停或退出时要上报「听取进度（秒）」，下次再进该专辑页面自动从上次位置继续播，而不是重新从头放。
2. **异常退出兜底**：播放中**直接点「返回专辑列表」按钮**、或关页签/刷新等异常退出时，也要把这次的 `listening_progress` 上传——现有逻辑在这些路径**漏报**。

排查结论（针对漏报）：
- 旧 `beforeDestroy` 走 `fadeOutVolume(() => { this.pauseListeningTimer() })`：渐变定时器要 ~300ms 才回调，而组件此刻已被 Vue 销毁、`$refs.audioRef` 被置空，`pauseListeningTimer` 的 `if (!audio) return` 守卫提前 return → 请求根本没发。
- 页面卸载（关页签/刷新）连 `beforeDestroy` 都不触发，普通 async axios 会被页面销毁取消。
- 于是需要一条**不依赖 `$refs`、能跨域带 Authorization、卸载时也保活**的上报通道。

## 三、优化复盘（本次流程浪费与快速命中）

**浪费的轮次：**
1. **实现顺序反了**：续播功能先写了实现再补单测，按测试 skill 应「测试先行（红灯）→ 实现 → 绿灯」。本次 `normalize_progress` 是纯函数，本就该一步到位先写 10 条单测。
2. **realdata 插数踩旧表坑**：往 `album_pool` 插测试数据报 `1364 Field 'tracks_time' doesn't have a default value`，定位用了 1-2 轮。根因是线上表是**旧 DDL 建的**，多了当前 DDL 里没有的 `tracks_time TEXT NOT NULL`（`CREATE TABLE IF NOT EXISTS` 不会改已存在表）。下次写 realdata 前先 `SELECT ... FROM information_schema.COLUMNS WHERE IS_NULLABLE='NO' AND COLUMN_DEFAULT IS NULL` 扫一遍目标表。
3. **漏报根因判断不准**：起初猜「async axios 被中断」，读代码后才发现是 `fadeOutVolume` 延迟回调 + `$refs` 置空导致守卫提前 return。**先读守卫条件再下结论**，省得绕远。
4. **差点用同步 XHR**：`xhr.open(url, false)` 跨域 + `Authorization` 头需要预检，而同步请求无法预检 → 必然失败。keepalive fetch 才是唯一同时满足「自定义头 + 跨域 + 卸载保活」的方案，这个点值得记下来避免下次重踩。
5. **addEventListener 绑定坑**：`window.addEventListener('pagehide', this.handlePageExit)` 直接传方法引用，回调里 `this` 指向 window，`this.flushListeningReport()` 会 TypeError。需 `.bind(this)` 存引用再 add/remove。

**快速命中清单：**
1. 续播字段与 `listening_duration` **完全同构**，改 4 处即可：`db.py` DDL 加列 → `listening.py` pause 接口写列+幂等补列 → `album.py` detail 返回 → 前端 `autoPlayCurrentAlbumAudio` 读 `album.listening_progress` 续播。照抄 `listening_duration` 模式，不要自创。
2. 退出兜底上报模板：`flushListeningReport()`（keepalive fetch + 不依赖 `$refs` + `_exitReported` 防双发），挂在 `goBack`/`beforeDestroy`/`beforeUnmount`/`pagehide`/`beforeunload` 五处。
3. 后端 `normalize_progress()`（`backend/api/listening.py`）配了 10 条单测 + 3 条 realdata，改 clamp 阈值/精度直接改这一个函数。
4. realdata fixture（`client`/`test_user`）直接抄 `test_user_stats_realdata.py`，秒级上手。

## 四、最终解决方案 / 改造步骤

1. `backend/utils/db.py`：`create_user_album_table` DDL 加 `listening_progress FLOAT DEFAULT 0.0 COMMENT '专辑上次听取进度(秒) 续播用'`。
2. `backend/api/listening.py`：
   - 新增纯函数 `normalize_progress(progress, duration=None)`：非法/None/空串/负数→0；超 `duration`→clamp；保留 1 位小数。
   - pause 接口读 `request.get_json()` 的 `progress_seconds`，LEFT JOIN `album_pool` 取 `mp3_duration` 做 clamp；幂等补 `listening_progress` 列；`UPDATE ... SET listening_duration=%s, listening_progress=%s`；响应返回 `listening_progress`。
3. `backend/api/album.py`：详情接口返回 `"listening_progress": album.get("listening_progress", 0) or 0`。
4. 前端 `AlbumDetail.vue`：
   - `pauseListeningTimer()` 上报 `{progress_seconds: Math.max(0, Number(this.currentTime) || 0)}`。
   - `autoPlayCurrentAlbumAudio()` 读 `album.listening_progress`，仅在 `(1, duration-2)` 区间内续播，否则从头；上传新音频后清空进度。
   - 退出兜底 `flushListeningReport()` + `mounted` 注册 `pagehide`/`beforeunload`、`goBack` 跳转前调用、`beforeDestroy`/`beforeUnmount` 调用。
   - `$route` watcher 在切专辑（组件复用）前先 `await pauseListeningTimer()`，补上切专辑不落库的旧缺口。
5. 测试：`test_listening_progress.py`（10 条单测，红灯先行）+ `test_listening_progress_realdata.py`（3 条真实 DB）。

## 五、关键代码 / 配置（可直接复用）

```python
# backend/api/listening.py —— 进度规范化纯函数
def normalize_progress(progress, duration=None):
    """非法值/None/空串/负数→0；超整轨时长→clamp；保留1位小数"""
    try:
        val = float(progress if progress not in (None, '') else 0)
    except (TypeError, ValueError):
        return 0.0
    val = max(0.0, val)
    if duration:
        try:
            val = min(val, float(duration))
        except (TypeError, ValueError):
            pass
    return round(val, 1)
```

```js
// frontend/src/views/AlbumDetail.vue —— 退出兜底上报（挂 goBack/beforeDestroy/beforeUnmount/pagehide/beforeunload）
flushListeningReport() {
  if (this._exitReported) return;               // 防 pagehide+beforeunload 双发
  this._exitReported = true;
  const token = localStorage.getItem('token') || '';
  if (!token || !this.album.id || !this.audioSrc) return;
  const audio = this.$refs.audioRef;            // 销毁后 $refs 已置空 → 回退 currentTime
  const liveTime = audio && audio.currentTime ? audio.currentTime : this.currentTime;
  const progressSeconds = Math.max(0, Number(liveTime) || 0);
  try {
    fetch('http://localhost:5000/api/album/listening/pause/' + this.album.id, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json;charset=utf-8', 'Authorization': token },
      body: JSON.stringify({ progress_seconds: progressSeconds }),
      keepalive: true                            // 页面卸载时仍能送达
    }).catch(() => {});
  } catch (err) { /* 忽略 */ }
}
```

```js
// 前端续播：进入页面自动从上次进度播放
autoPlayCurrentAlbumAudio() {
  // ...
  const savedProgress = Number(this.album.listening_progress) || 0;
  const resumeFrom = (this.duration > 0 && savedProgress > 1 && savedProgress < this.duration - 2)
      ? savedProgress : 0;
  this.currentTime = resumeFrom;
  this.currentProgress = this.duration ? (resumeFrom / this.duration) * 100 : 0;
  if (resumeFrom > 0) { try { audio.currentTime = resumeFrom; } catch (e) { /* 忽略 */ } }
  audio.play().then(() => { /* 正常播放 */ });
}
```

```js
// mounted 里注册页面级卸载监听（必须 .bind(this)）
this._pageExitHandler = this.handlePageExit.bind(this);
window.addEventListener('pagehide', this._pageExitHandler);
window.addEventListener('beforeunload', this._pageExitHandler);
```

## 六、踩坑点 & 注意事项（非常重要）

- **组件销毁后 `$refs.audioRef` 会被 Vue 置空**：凡是 `beforeDestroy` 里延迟（setTimeout/fadeOut 回调）才执行的逻辑，再访问 `$refs` 守卫会提前 return → 漏发。兜底上报**不要依赖 `$refs`**，用缓存的 `this.currentTime`。
- **async axios 在页面卸载会被取消**；组件销毁时虽能完成，但被延迟回调 + `$refs` 守卫拦住的概率很高。卸载上报统一走 `keepalive: true` fetch。
- **同步 XHR 跨域 + 自定义头不可行**：`xhr.open(url, false)` 无法执行 CORS 预检，带 `Authorization`/JSON 会被浏览器拒绝。keepalive fetch 支持预检，是正解。
- **`window.addEventListener(name, this.method)` 传方法引用，回调 `this` 指向 window**：必须 `this.method.bind(this)` 存引用再 add，remove 用同一个引用。
- **`pagehide` 与 `beforeunload` 在卸载时都会触发**：用 `_exitReported` 标志防双发（后端 pause 无缓存时返回 400 也算兜底，但不发最好）。
- **realdata 插旧表数据先扫 NOT NULL 无默认值列**：`album_pool` 有历史遗留 `tracks_time TEXT NOT NULL`（当前 DDL 没有），插入必须显式提供，否则 1364。
- **`$route` watcher 切专辑（组件复用）不触发 `beforeDestroy`**：A→B 切换时需在 watcher 里先 `pauseListeningTimer()`，否则 A 的时长/进度全部丢失。
- **keepalive 限制**：单请求 body ≤ 64KB，本项目足够；上传音频等大文件不要走这条路。

## 七、同类问题快速适配规则

【适配点1】新增「暂停/退出上报某字段、下次进入恢复」→ 复用 `listening_progress` 全套模式：`db.py` 加列 + pause 接口幂等补列 + detail 返回 + 前端续播，把 `listening_progress` 换成新字段即可。
【适配点2】任何「关页签/刷新也要上报」（评论草稿、播放列表保存、埋点）→ 复制 `flushListeningReport()`（keepalive fetch + `_exitReported`），改 URL 和 body，挂 `pagehide`/`beforeunload`。
【适配点3】`beforeDestroy` 里现有 `fadeOutVolume(() => asyncPause())` 这类**延迟异步**上报都可能有同样的 `$refs` 置空漏报问题 → 统一替换为不依赖 `$refs` 的 keepalive 上报。
【适配点4】realdata 测试往目标表插数前 → 先查该表 NOT NULL 无默认值列，补齐再插，避免 1364。

---

相关案例：[[20260811_browser_autofill_search_field_fix]]（同日另一前端修复，验证需硬刷新）、[[20260810_v0_7_p0_user_center_feature]]（用户分表/统计字段扩展范本）、[[20260810_score_debounce_save_fix]]（前端即时落盘模式）。
