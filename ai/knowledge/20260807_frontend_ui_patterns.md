# 前端主题色与UI模式参考

## 一、主题色系统

### 三级颜色定义

| 变量 | 用途 | CSS场景 |
|------|------|---------|
| `mainColor` | 主色(浅色) | 较浅的背景、次要元素 |
| `mainColorDark` | 深色主色 | 按钮、文字、强调线、活跃Tab |
| `mainColorDarkDouble` | 双重深色 | 悬浮态、强调文字、主要按钮 |

### 传递方式

```
WebHome (data)
  ↓ props
子组件 (接收 mainColor, mainColorDark, mainColorDarkDouble)
  ↓ v-bind()
CSS样式 (使用 v-bind(mainColorDark) 绑定到CSS变量)
```

### CSS中使用v-bind

```css
.tab-item {
  color: v-bind(mainColorDark);
  background: v-bind(mainColorDark);
}
.tab-item.active {
  background: v-bind(mainColorDarkDouble);
  color: #fff;
}
.album-name-wrapper::after {
  background-color: v-bind(mainColorDark) !important;
}
```

### 主题色来源

- `DailyRecommend` — 从推荐专辑封面提取主色
- `MusicList` — 从专辑列表封面提取主色
- `SearchAlbumPool` — 从WebHome继承
- `CategoryList` — 从WebHome继承

**事件上传**：`@sendThemeColor` 事件传递 `{mainColor, mainColorDark, mainColorDarkDouble}`

---

## 二、背景图系统

### 全屏模糊背景

```css
.bg-layer {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: -1;
  filter: blur(25px) brightness(1.2);
  background-attachment: fixed;
}
```

### 毛玻璃蒙版

```css
.nav-mask-container {
  background-color: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(8px);
  border-radius: 12px;
}
```

### 背景图来源

- 子组件通过 `@sendCoverBg` 事件上传封面URL
- WebHome接收后设置 `coverBgUrl`
- 持久化到 `localStorage.persistCoverBg`

---

## 三、侧边栏组件模式

### 侧边栏结构

```html
<!-- 遮罩层 -->
<div class="sidebar-overlay" v-if="visible" @click="$emit('close')"></div>

<!-- 侧边栏主体 -->
<div class="sidebar-panel" :class="{open: visible}">
  <div class="sidebar-header">
    <h3>标题</h3>
    <button @click="$emit('close')">×</button>
  </div>
  <div class="sidebar-body">
    <!-- 内容 -->
  </div>
</div>
```

### 侧边栏样式

```css
.sidebar-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1000;
}

.sidebar-panel {
  position: fixed;
  top: 0; right: -500px;
  width: 500px; height: 100vh;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  z-index: 1001;
  transition: right 0.3s ease;
  overflow-y: auto;
}

.sidebar-panel.open {
  right: 0;
}
```

---

## 四、分页组件模式

### 分页结构

```html
<div class="pagination">
  <button @click="changePage(1)" :disabled="pagination.page === 1">首页</button>
  <button @click="changePage(pagination.page - 1)" :disabled="pagination.page === 1">上一页</button>
  <span>第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页</span>
  <button @click="changePage(pagination.page + 1)" :disabled="pagination.page === pagination.total_pages">下一页</button>
  <button @click="changePage(pagination.total_pages)" :disabled="pagination.page === pagination.total_pages">尾页</button>
  <input type="number" v-model="jumpPageNum" :max="pagination.total_pages">
  <button @click="jumpToPage()">跳转</button>
</div>
```

### 分页数据

```javascript
pagination: {
  total: 0,
  page: 1,
  page_size: 10,
  total_pages: 0
}
```

---

## 五、下拉菜单模式

```html
<div class="dropdown-btn-container">
  <button class="dropdown-btn" @click="toggleDropdown('sortBy')">
    {{ sortByMap[sortBy] }}
    <span class="arrow-icon" :class="{active: dropdownShow.sortBy}">▼</span>
  </button>
  <ul class="dropdown-options" v-show="dropdownShow.sortBy}">
    <li v-for="(label, key) in sortByMap" :key="key"
        @click="handleSortChange(key); toggleDropdown('sortBy')"
        :class="{active: sortBy === key}">
      {{ label }}
    </li>
  </ul>
</div>
```

```javascript
toggleDropdown(type) {
  Object.keys(this.dropdownShow).forEach(key => {
    this.dropdownShow[key] = key === type ? !this.dropdownShow[key] : false
  })
}
```

---

## 六、响应式适配

```css
@media (max-width: 768px) {
  .main-tab-header {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
  .main-tab-item { font-size: 16px; }
  .sub-tab-item { font-size: 14px; padding: 5px 10px; }
}
```

---

## 七、全局CSS

**位置**：`frontend/src/assets/css/global.css`

- 基础字体：Microsoft YaHei
- 容器最大宽度：800px
- 输入框统一样式：300px宽、4px圆角
- 按钮统一样式：#007bff蓝底白字、4px圆角

**星级评分**：`frontend/src/assets/css/star.css`
- 未选中：#ccc灰色
- 选中：#ffc107金色
- 大小：20px
