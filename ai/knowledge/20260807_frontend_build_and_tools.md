---
name: frontend-build-and-tools
description: 前端构建配置、SVG资源、公共静态文件、自动录屏工具详解
metadata:
  type: reference
---

# 前端构建配置与工具

## 构建工具链

### Vue CLI 5
- **入口**: `@vue/cli-service` ^5.0.9
- **Babel插件**: `@vue/cli-plugin-babel` ^5.0.9
- **ESLint插件**: `@vue/cli-plugin-eslint` ^5.0.9
- **模板编译器**: `vue-template-compiler` ^2.6.14（必须与vue版本严格匹配）

### vue.config.js
```javascript
const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true
})
```
- 极简配置，仅开启 `transpileDependencies`
- 无 devServer proxy（前后端通过CORS直连，后端:5000，前端:8080）
- 无自定义 webpack 配置

### babel.config.js
```javascript
module.exports = {
  presets: ['@vue/cli-plugin-babel/preset']
}
```
- 使用Vue CLI默认Babel预设

### jsconfig.json
```json
{
  "compilerOptions": {
    "target": "es5",
    "module": "esnext",
    "baseUrl": "./",
    "paths": { "@/*": ["src/*"] }
  },
  "exclude": ["node_modules", "dist"]
}
```
- `@/*` → `src/*` 路径别名（前端代码中大量使用 `@/` 引用）
- 编译目标 es5，模块系统 esnext

### package.json scripts
```json
{
  "serve": "vue-cli-service serve --host 0.0.0.0 --port 8080",
  "build": "vue-cli-service build",
  "lint": "vue-cli-service lint"
}
```
- 开发服务器监听 `0.0.0.0:8080`（局域网可访问）

## ESLint 配置

内嵌在 `package.json` 的 `eslintConfig` 字段：
```json
{
  "root": true,
  "env": { "node": true },
  "extends": ["plugin:vue/essential", "eslint:recommended"],
  "parserOptions": { "parser": "@babel/eslint-parser" },
  "rules": {}
}
```
- Vue必要规则 + ESLint推荐规则
- 无自定义规则覆盖
- 浏览器兼容：`> 1%`、`last 2 versions`、`not dead`

## 公共静态资源（frontend/public/）

### index.html
- 标准 Vue CLI HTML 模板
- `<div id="app">` 挂载点
- 无自定义 meta 标签或 CDN 引用

### SVG 图标
| 文件 | 用途 | 使用位置 |
|------|------|----------|
| `屏蔽.svg` | 屏蔽/隐藏评论图标 | 评论组件 |
| `点赞.svg` | 点赞图标 | 评论组件 |
| `重置.svg` | 重置按钮图标 | 评分/搜索组件 |

### favicon.ico
- 标准Vue CLI默认图标

## 前端 .gitignore

```
.DS_Store
node_modules/
/dist
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
```
- 标准Vue CLI忽略规则
- `node_modules/` 和 `/dist` 是最关键的忽略项

## 自动录屏工具详解

### 架构
```
Playwright (Edge浏览器) → 注入localStorage → 跳转专辑页 → 点击播放
                                                           ↓
FFmpeg (gdigrab) ← 桌面捕获 ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

### 关键技术点

1. **localStorage注入**：先打开登录页，通过 `addInitScript` 注入认证信息，再刷新使路由守卫生效
2. **页面就绪检测**：双重检测——`document.body.innerText.includes('专辑')` 或 `document.querySelector('.album_name')`
3. **播放器定位**：`waitForSelector('.album-rotate-box', { state: 'attached' })`，使用 `attached` 而非 `visible` 避免样式隐藏导致检测失败
4. **强制滚动**：`scrollIntoView({ behavior: 'smooth', block: 'center' })` 确保播放器在视口内
5. **强制点击**：`{ force: true }` 忽略元素可见性检测
6. **错误截图**：超时时自动保存 `page-error.png`

### 依赖
- `playwright` ^1.58.2（devDependencies中）
- `ffmpeg.exe`（项目内置，位于 `backend/tools/ffmpeg/`）
- Edge浏览器（`channel: 'msedge'`）

### 扩展建议
- 改为浏览器内录屏（`page.video.startRecording()`）可避免全屏桌面捕获
- 可批量录制多个专辑（循环CONFIG数组）
- 添加音频录制支持

## 相关文档

- [[deployment-and-environment]] — 部署与环境配置
- [[frontend-routes-and-config]] — 前端路由与Axios配置
