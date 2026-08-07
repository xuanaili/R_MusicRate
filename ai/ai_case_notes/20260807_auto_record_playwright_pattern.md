---
name: auto-record-playwright-pattern
description: Playwright+FFmpeg自动录屏模式，用于B站专辑分享视频录制
metadata:
  type: feedback
---

# 案例：Playwright自动录屏与认证注入

## 基本信息

- **案例编号**：20260807_auto_record_playwright
- **关键词**：Playwright、Edge浏览器、localStorage注入、FFmpeg gdigrab、路由守卫绕过
- **适用场景**：需要自动化浏览器操作并录屏，特别是SPA应用需要认证后才能访问的页面

## 问题描述

MusicRate需要自动录制专辑页面的播放视频用于B站分享。但专辑页面是受路由守卫保护的SPA页面，未登录会被重定向到登录页。需要在自动化脚本中注入认证信息，使页面能正常访问。

## 核心需求

1. 自动登录SPA应用（绕过路由守卫）
2. 等待Vue异步渲染完成
3. 定位并点击播放按钮
4. 桌面录屏输出MP4

## 解决方案

### 1. localStorage注入认证信息

```javascript
// 先打开登录页，确保localStorage生效
await page.goto(CONFIG.loginUrl, { waitUntil: 'networkidle' });

// 注入认证信息
await page.addInitScript(({ token, userId, isAdmin }) => {
  localStorage.setItem('token', token);
  localStorage.setItem('user_id', userId);
  localStorage.setItem('is_admin', isAdmin);
}, { token: CONFIG.token, userId: CONFIG.userId, isAdmin: CONFIG.isAdmin });

// 刷新让路由守卫重新验证
await page.reload({ waitUntil: 'networkidle' });
```

**Why:** 直接跳转到目标页面会被路由守卫拦截，因为localStorage中没有token。必须先打开登录页注入，再刷新让守卫验证。

### 2. 双重页面就绪检测

```javascript
// 检测1：文本内容出现
await page.waitForFunction(() => {
  return document.body.innerText.includes('专辑') || document.querySelector('.album_name') !== null;
}, { timeout: 20000 });

// 检测2：播放器元素存在
await page.waitForSelector('.album-rotate-box', {
  timeout: 20000,
  state: 'attached'  // 关键：attached而非visible
});
```

**Why:** Vue异步加载导致DOM元素可能延迟渲染。`state: 'attached'` 比 `visible` 更可靠，因为元素可能被CSS隐藏但DOM已存在。

### 3. FFmpeg桌面录屏

```javascript
const ffmpegCmd = `"${CONFIG.ffmpegPath}" -f gdigrab -framerate 20 -i desktop -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -movflags +faststart -t ${CONFIG.recordTime} ${CONFIG.outputVideo}`;
```

**Why:** 使用Windows gdigrab捕获桌面，yuv420p确保兼容性，faststart使MP4可边下边播。

## 踩坑记录

1. **路由守卫拦截**：直接跳转目标页面被重定向 → 先打开登录页注入localStorage再刷新
2. **元素检测失败**：`state: 'visible'` 对隐藏元素报错 → 改用 `state: 'attached'`
3. **MP4损坏**：FFmpeg异常退出导致文件损坏 → 使用 `-movflags +faststart` 和正确的编码参数
4. **播放器被遮挡**：元素在视口外无法点击 → `scrollIntoView` + `force: true`
5. **Vue异步渲染**：页面DOM已加载但内容未渲染 → 使用 `waitForFunction` 检测文本内容

## 适配规则

- SPA应用自动化必须先注入认证信息再刷新
- 元素检测优先使用 `attached` 状态
- 点击前确保元素在视口内
- FFmpeg录屏使用兼容性参数
- 超时时自动截图保存错误现场
