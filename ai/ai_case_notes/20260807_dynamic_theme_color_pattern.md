# 案例：动态主题色与封面提取

## 基本信息

- **案例编号**：20260807_dynamic_theme_color
- **关键词**：Canvas提取主色、v-bind CSS、主题色传递、localStorage持久化
- **适用场景**：根据专辑封面动态改变全页主题色

## 问题描述

MusicRate需要根据当前查看的专辑封面动态改变页面主题色，使整个页面（背景、按钮、文字、下划线等）与封面色调协调。这需要封面颜色提取、颜色变体生成、CSS动态绑定、跨组件传递、持久化等多个环节。

## 核心需求

1. 从专辑封面提取主色
2. 生成5级颜色变体（浅→深→极深→白→极白）
3. 主题色通过props传递给所有子组件
4. CSS中使用动态颜色（非硬编码）
5. 主题色持久化到localStorage

## 解决方案

### 1. Canvas提取主色

```javascript
extractAlbumMainColor(imgUrl) {
  return new Promise((resolve) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      canvas.width = 50
      canvas.height = 50
      ctx.drawImage(img, 0, 0, 50, 50)
      const data = ctx.getImageData(0, 0, 50, 50).data
      // 采样统计：取RGB平均值
      let r = 0, g = 0, b = 0, count = 0
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] > 128) {  // 跳过透明像素
          r += data[i]; g += data[i+1]; b += data[i+2]; count++
        }
      }
      const hex = '#' + [r, g, b].map(v =>
        Math.round(v / count).toString(16).padStart(2, '0')
      ).join('')
      resolve(hex)
    }
    img.onerror = () => resolve('#42b983')  // 默认绿色
    img.src = imgUrl
  })
}
```

### 2. 颜色变体生成

```javascript
darkenColor(hex, amount) {
  // amount: 0-1, 大于0.5变暗，小于0.5变亮
  let r = parseInt(hex.slice(1, 3), 16)
  let g = parseInt(hex.slice(3, 5), 16)
  let b = parseInt(hex.slice(5, 7), 16)
  if (amount > 0.5) {
    const factor = 1 - (amount - 0.5) * 2
    r = Math.round(r * factor); g = Math.round(g * factor); b = Math.round(b * factor)
  } else {
    const factor = amount * 2
    r = Math.round(r + (255 - r) * factor); g = Math.round(g + (255 - g) * factor); b = Math.round(b + (255 - b) * factor)
  }
  return '#' + [r, g, b].map(v => Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0')).join('')
}
```

### 3. CSS中使用v-bind绑定

```css
/* Vue 2.6+ 的 v-bind CSS 特性 */
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

### 4. 主题色传递与持久化

```javascript
// WebHome.vue
data() {
  return {
    mainColor: localStorage.getItem('persistMainColor') || 'transparent',
    mainColorDark: localStorage.getItem('persistMainColorDark') || 'transparent',
    mainColorDarkDouble: localStorage.getItem('persistMainColorDarkDouble') || 'transparent'
  }
},
watch: {
  mainColor(newVal) { localStorage.setItem('persistMainColor', newVal) },
  mainColorDark(newVal) { localStorage.setItem('persistMainColorDark', newVal) },
  mainColorDarkDouble(newVal) { localStorage.setItem('persistMainColorDarkDouble', newVal) }
},
methods: {
  getThemeColor(colorObj) {
    this.mainColor = colorObj.mainColor
    this.mainColorDark = colorObj.mainColorDark
    this.mainColorDarkDouble = colorObj.mainColorDarkDouble
  }
}
```

### 5. 子组件上传主题色

```javascript
// DailyRecommend.vue
extractAlbumMainColor(this.albumData.cover_img).then(color => {
  this.mainColor = color
  this.mainColorDark = this.darkenColor(color, 0.7)
  this.mainColorDarkDouble = this.darkenColor(color, 0.4)
  this.$emit('sendThemeColor', {
    mainColor: this.mainColor,
    mainColorDark: this.mainColorDark,
    mainColorDarkDouble: this.mainColorDarkDouble
  })
})
```

## 踩坑记录

1. **Canvas跨域**：封面图跨域时 `getImageData()` 报错 → 设置 `img.crossOrigin = 'anonymous'`
2. **v-bind CSS兼容性**：Vue 2.6的v-bind CSS需要编译器支持 → 确保vue-template-compiler版本匹配
3. **透明像素干扰**：PNG封面含透明区域导致颜色偏白 → 跳过alpha<128的像素
4. **颜色提取偏差**：简单平均法对大面积纯色区域不敏感 → 可考虑K-means聚类（但性能开销大）
5. **浅色封面文字不可见**：提取到浅色时，深色文字在浅色背景上看不清 → 需要亮度判断自动切换文字颜色

## 适配规则

- 所有需要动态主题色的组件必须接收三个颜色props
- CSS中使用v-bind()绑定，禁止硬编码颜色值
- 封面提取主色后立即emit到父组件
- 主题色变更必须持久化到localStorage
- 新增组件时检查是否需要接收主题色props
