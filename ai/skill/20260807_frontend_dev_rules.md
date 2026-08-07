# 前端开发规范与编码约束

## 一、组件命名与文件结构

- 页面级组件放 `views/`，功能子组件放 `components/`
- 组件文件名使用 PascalCase：`AlbumDetail.vue`、`DailyRecommend.vue`
- 组件目录按功能分组：`albumDetail/`、`discoverMusic/`、`myMusic/`、`sidebar/`、`item/`
- 组件内 `name` 属性必须与文件名一致

## 二、组件通信规范

### 父→子：Props
- 主题色通过 `mainColor`/`mainColorDark`/`mainColorDarkDouble` 三个props传递
- 数据通过语义化props传递（如 `album`、`tracks`、`isAdmin`）
- Props必须声明类型和默认值

### 子→父：$emit
- 事件名使用 kebab-case：`@save-tags`、`@score-list-change`
- 侧边栏关闭：`@close`
- 主题色上传：`@sendThemeColor`、`@sendCoverBg`

### 跨层级：localStorage
- Tab状态传递：`localStorage.setItem('targetMainTab', 'mymusic')`
- 主题色持久化：`persistMainColor`/`persistMainColorDark`/`persistMainColorDarkDouble`
- 认证信息：`token`/`username`/`is_admin`/`user_id`

## 三、API调用规范

- 使用 `this.$axios` 调用（全局挂载在 `Vue.prototype`）
- 每次请求附带 `Authorization` 请求头
- 响应格式：`{code: 200, msg: "...", data: ...}`
- 成功判断：`res.data.code === 200`
- 错误处理：区分 `err.response`（有响应）和 `err.request`（无响应）

## 四、主题色系统

### 颜色层级
- `mainColor` — 浅色（背景、次要元素）
- `mainColorDark` — 深色（按钮、文字、强调线）
- `mainColorDarkDouble` — 双重深色（悬浮态、强文字）

### CSS中使用
```css
.tab-item {
  color: v-bind(mainColorDark);
  background: v-bind(mainColorDark);
}
.tab-item.active {
  background: v-bind(mainColorDarkDouble);
  color: #fff;
}
```

### 颜色提取
- 从封面图提取主色：`canvas.drawImage()` → `getImageData()` → RGB统计
- 生成5级颜色：main → mainDark → mainDarkDouble → mainWhite → mainWhiteDouble

## 五、标签格式规范

- 标签格式：`English【中文】`，如 `Pop【流行】`
- 展示英文，悬浮显示中文
- 提取英文：`tagStr.substring(0, tagStr.indexOf('【'))`
- 提取中文：`tagStr.substring(tagStr.indexOf('【') + 1, tagStr.indexOf('】'))`

## 六、侧边栏组件规范

### Props
- `visible` (Boolean) — 控制显示/隐藏
- `mainColor`/`mainColorDark`/`mainColorDarkDouble` — 主题色

### Events
- `@close` — 关闭侧边栏

### 样式
- 右侧滑入动画（translateX）
- 半透明遮罩（rgba(0,0,0,0.3)）
- 毛玻璃效果（backdrop-filter: blur(12px)）

### DOM端口模式（AddTag/EditTag特殊）
- `mounted`时将侧边栏DOM append到 `document.body`
- `beforeDestroy`时移除
- 使用uid后缀避免CSS冲突

## 七、评分计算规范

- 使用 `@/utils/scoreCalc.js` 的 `calculateAlbumTotalScore()`
- my_score可能是字符串格式JSON数组，需先 `JSON.parse()` 再计算
- 优先使用后端返回的 `calculated_score`
- 前后端逻辑必须一致

## 八、Git提交规范

- 每次修改必须git上传
- 提交信息使用中文，说明修改内容
- 遵循项目铁律：`每次修改，都要git上传，并说明修改内容`
