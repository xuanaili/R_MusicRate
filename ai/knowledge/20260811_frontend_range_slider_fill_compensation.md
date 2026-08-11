# MusicRate 原生 range 滑块填充补偿 + 布局实测（AppearancePanel 蒙版滑轨）

> 2026-08-11 实测结论。来源：v0.7.1 P2「蒙版滑轨偏移修复 + 拖动数值气泡 / 刻度线」，用 headless Edge + CDP/像素实测得出，非目测。

## 1. 核心公式：渐变边界对齐 thumb 中心

原生 `<input type="range">`（`-webkit-appearance:none` 自定义样式）里，**value→thumb 位移**按 thumb 的 **content-box 宽度**（本项目 16px，不含 2px border）线性映射：

```
thumbCenter(px) = trackLeft + pct*(trackWidth - THUMB_W) + THUMB_W/2     （pct = value/max）
```

若渐变只写 `pct%`，边界在 `pct*trackWidth`，与 thumb 中心差 `THUMB_W*(0.5 - pct)` px：**value<50% 时边界偏左、>50% 偏右**（实测最大偏差 ±8px，value=0 时差 8px）。补偿公式：

```css
/* THUMB_W = 16（content-box 宽度，实测 Edge/Chrome 以此计算位移） */
background: linear-gradient(to right,
  ${color} 0%,
  ${color} calc(${pct*100}% + ${THUMB_W*(0.5 - pct)}px),
  rgba(255,255,255,.4) calc(${pct*100}% + ${THUMB_W*(0.5 - pct)}px),
  rgba(255,255,255,.4) 100%);
```

- value=0 → `calc(0% + 8px)`；value=60(max) → `calc(100% - 8px)`；value=25 → `calc(41.67% + 1.33px)`
- 实测验证（track 宽 183）：渐变边界 vs thumb 中心 diff = 0 / 0.41 / 0（修复前 -8 / -1.25 / +8）
- 同一公式复用于数值气泡 `left` 与刻度线 `left`，气泡/刻度加 `transform: translateX(-50%)` 居中

## 2. 两个实测坑

### 2.1 `input` 默认 margin 2px（inline-block）
`<input>` 在 UA 样式表里有 `margin-left/right: 2px`（实测 computed `margin-left:2px`），会让轨道相对包裹层右偏 2px。渐变画在 input 上、气泡/刻度定位在包裹层上，**两者错位 2px**。修复：`.mask-slider { margin: 0 }`。

### 2.2 thumb 垂直居中（无需 margin-top）
README 曾疑有「thumb 垂直偏移」，但实测 `thumbCenterY - trackCenterY = 0`（Chrome/Edge 默认把 `-webkit-slider-thumb` 垂直居中于轨道）。**加 margin-top 补偿反而会引入偏移**——以实测为准，勿凭教程加。

## 3. Vue 2 模板无法访问模块常量

`const MASK_MAX = 60` 是模块级常量，模板 `:max="MASK_MAX"` 会取到 `this.MASK_MAX` = undefined → 属性不落 → input 退化为默认 max=100（value/60 被当 /100，thumb 只走 40%）。必须暴露到实例：

```js
data() { return { MASK_MAX } }
```

## 4. headless 实测工具

`portable/tools/layout_probe/`（puppeteer-core + 本机 Edge，不下载浏览器）：
- `probe_mask_slider.js` — 独立 HTML 复现滑块，截图像素识别 thumb 中心，输出 rect/偏差
- `probe_real_app.js` / `probe_fix_verify.js` — 登录真实前端（注入 token+username 到 localStorage，路由守卫 + WebHome created 都要）、打开 UserCenter「外观」tab、实测 + 解析 computed background 渐变 stop
- 关键 CDP 技巧：`DOM.getDocument({depth:-1})` 对 range input 拿不到 thumb 伪元素，改用「截图像素识别 thumb 洋红核心」；`el.value=v; dispatchEvent(new Event('input'))` 可模拟滑动
- 运行：`node portable/tools/layout_probe/probe_*.js <token>`（token 由 `curl -s localhost:5000/api/login -X POST -d '{"username":"admin","password":"123456"}'` 获取）

## 5. 排查命令

```bash
node portable/tools/layout_probe/probe_fix_verify.js <token>   # 修复后收敛验证
grep -rn "mask-slider" frontend/src --include="*.vue"           # 滑块使用点
```
