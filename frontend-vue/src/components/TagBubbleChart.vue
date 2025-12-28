<template>
  <div class="tag-bubble-chart-container">
    <!-- ✅ 修复1：删除空的section-title标签 或 清空其样式，彻底根除顶部白线 -->
    <!-- 加载中状态 -->
    <div v-if="loading" class="loading-chart">加载中...</div>
    <!-- 气泡图渲染核心区 -->
    <div v-else-if="chartData.length > 0" class="bubble-chart">
      <div
        class="bubble"
        v-for="(item, idx) in chartData"
        :key="idx"
        :style="{
          width: `${item.size}px`,
          height: `${item.size}px`,
          left: `${item.x}%`,
          top: `${item.y - 10}%`,
          backgroundColor: item.color
        }"
      >
        <div class="bubble-label">{{ item.tag }}</div>
        <div class="bubble-value">{{ item.percent }}%</div>
      </div>
    </div>
    <!-- 无数据提示 -->
    <div v-else class="no-chart-data">
      <slot name="empty">暂无其他用户为该专辑添加标签</slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TagBubbleChart',
  props: {
    tagStats: {
      type: Array,
      required: true,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    mainColor: {
      type: String,
      required: true,
      default: '#42b983'
    },
    sizeRange: {
      type: Object,
      default: () => ({ min: 50, max: 150 })
    }
  },
  computed: {
    chartData() {
      const { tagStats, mainColor, sizeRange } = this
      const total = tagStats.reduce((sum, item) => sum + item.count, 0)
      if (total === 0) return []

      return tagStats.map((item, idx) => {
        const percent = ((item.count / total) * 100).toFixed(1)
        const size = Math.min(sizeRange.max, Math.max(sizeRange.min, sizeRange.min + percent * 1))
        const x = 10 + (idx * 15) > 85 ? 85 : 10 + (idx * 15)
        const y = 20 + Math.random() * 60
        const color = this.getRandomColor(mainColor)

        return {
          tag: item.tag,
          count: item.count,
          percent: percent,
          size: size,
          x: x,
          y: y,
          color: color
        }
      })
    }
  },
  methods: {
    getRandomColor(base) {
      base = base.replace('#','')
      let r = parseInt(base.slice(0,2),16)
      let g = parseInt(base.slice(2,4),16)
      let b = parseInt(base.slice(4,6),16)
      const random = Math.random() * 0.6 - 0.3
      r = Math.round(Math.min(255, Math.max(0, r*(1+random))))
      g = Math.round(Math.min(255, Math.max(0, g*(1+random))))
      b = Math.round(Math.min(255, Math.max(0, b*(1+random))))
      return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`
    }
  }
}
</script>

<style scoped>
.tag-bubble-chart-container {
  display: flex;
  flex-direction: column;
  height: 280px;
  width: 100%;
  /* ✅ 双重保险：容器内无任何边框和内边距残留 */
  border: none !important;
  padding-top: 0 !important;
  margin-top: 0 !important;
}

/* ✅ 修复2：彻底删除这个空标题的样式，根除根源 */
.section-title {
  display: none !important;
}

/* 核心：磨砂蒙版样式 无任何边框 */
.bubble-chart {
  position: relative;
  width: 100%;
  height: 100%;
  flex: 1;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 6px;
  overflow: hidden;
  min-height: 200px;
  border: none !important;
}

.loading-chart {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
	color: v-bind(mainColorDarkDouble) !important;
	font-size: 14px;
}

.bubble {
  position: absolute !important;
  border-radius: 50% !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: center !important;
	color: #fff !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
  transition: transform 0.2s !important;
  z-index: 99 !important;
}

.bubble:hover {
  transform: scale(1.05) !important;
}

.bubble-label {
  font-size: 14px !important;
  font-weight: 600 !important;
  margin-bottom: 4px !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
}

.bubble-value {
	font-size: 12px !important;
	text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
}

.no-chart-data {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #999;
	font-size: 14px;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 6px;
  border: none !important;
}
</style>