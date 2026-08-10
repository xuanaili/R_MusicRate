# 布局对齐工作流（强制）

> 从 BookRate 迁移（2026-08-10），适配 MusicRate。BookRate 用 `portable/tools/layout_probe.py` 实测坐标，MusicRate 暂无此工具——**建议按需自建 headless 浏览器 probe**；在工具就绪前，用浏览器 DevTools 实测 DOM rect 替代"凭肉眼猜测"。

## 触发场景
**任何涉及布局的任务**：对齐、间距、尺寸、等高、响应式、面板内留白。一律「先实测坐标 → 再动手 → 最后重测验证」，禁止凭肉眼或 CSS 猜测直接改。

## 核心原则
- 用 headless 浏览器或 DevTools 实测 DOM 元素 rect（x/y/width/height/bottom），拿到**数值**再改
- **bottom = y + height**。「底部对齐」= 两元素 bottom 相等
- 改完 CSS 重测同一组选择器，差值趋近 0 即完成
- headless 截图可能渲染不出像素（白屏），但 DOM rect 数值可靠——**以数值为准，别判断截图**

## 工作流
1. 起后端(5000) + 前端(8080)，备好能打开目标页的数据
2. 实测目标元素各坐标与 bottom 差值
3. 差值 = 需要调整的像素量，改 CSS
4. 重测验证差值收敛 → ESLint → 提交

## 常用修复手段（已验证）
- **面板内容填不满（底部留白）**：容器设 `box-sizing: border-box` + 面板负 margin 抵消 padding，如 `margin: 0 -20px -20px`
- **两侧面板不等高**：两侧 `max-height` 设一致。注意 content-box 下 max-height 只限制内容区，总高会多出 padding——用 border-box 让 vh 含 padding
- **网格项被长内容撑宽**：`.xxx-item { min-width: 0 }`（网格项默认 `min-width: auto`，长文本会把 `1fr` 轨道撑超容器）
- **长文本省略**：`white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%` + `:title` 悬停提示全名

## 坑（血泪教训）
- **改全局容器**（如 `.right-section` 的 box-sizing / max-height）会连带影响同一容器下所有组件 → 改前先列出影响面
- **测试插数据 / 改配置禁止覆盖已有真实数据**：插入临时数据等一律先 `SELECT` 确认，绝不 `ON DUPLICATE KEY UPDATE` 覆盖
- 布局改动多组件时，检查窄屏 `@media (max-width: 768px)` 是否需要同步覆盖
- 环境残留：测完必须清掉 5000/8080 端口进程 + 测试数据，避免下次污染

---

以下为固定指令，遇到布局类需求直接贴本文件执行：
凡涉及布局尺寸/对齐的修改，必须实测 DOM rect 验证后再提交，不凭视觉判断。
