<template>
  <div class="tag-bubble-chart-container">
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
        :title="item.tag.match(/【(.*?)】/)?.[1] || item.tag"
      >
        <!-- 显示【】外的英文 -->
        <div class="bubble-label">{{ item.tag.split('【')[0].trim() || item.tag }}</div>
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
      default: () => ({min: 50, max: 150})
    }
  },
  computed: {
    chartData() {
      const {tagStats, mainColor, sizeRange} = this
      const total = tagStats.reduce((sum, item) => sum + item.count, 0)
      if (total === 0) return []

      const generatedBubbles = []
      const baseStep = Math.max(8, 20 - tagStats.length * 0.3)
      const safeXMin = 8
      const safeXMax = 92
      const safeYMin = 15
      const safeYMax = 85

      return tagStats.map((item, idx) => {
        const percent = ((item.count / total) * 100).toFixed(1)
        const size = Math.min(sizeRange.max, Math.max(sizeRange.min, sizeRange.min + percent * 1))
        let x = safeXMin + idx * baseStep
        x = x > safeXMax ? safeXMax - Math.random() * 10 : x + Math.random() * 6 - 3
        const ySection = Math.floor(idx / 5)
        let y = safeYMin + ySection * 18 + Math.random() * 25
        y = Math.min(safeYMax, Math.max(safeYMin, y))

        const color = this.getRandomColor(mainColor)
        const bubbleItem = {
          tag: item.tag,
          count: item.count,
          percent: percent,
          size: size,
          x: x,
          y: y,
          color: color
        }

        if (generatedBubbles.length > 0) {
          this.avoidOverlap(bubbleItem, generatedBubbles, safeXMin, safeXMax, safeYMin, safeYMax)
        }
        generatedBubbles.push(bubbleItem)
        return bubbleItem
      })
    }
  },
  methods: {
    getRandomColor(base) {
      base = base.replace('#', '')
      let r = parseInt(base.slice(0, 2), 16)
      let g = parseInt(base.slice(2, 4), 16)
      let b = parseInt(base.slice(4, 6), 16)
      const random = Math.random() * 0.6 - 0.3
      r = Math.round(Math.min(255, Math.max(0, r * (1 + random))))
      g = Math.round(Math.min(255, Math.max(0, g * (1 + random))))
      b = Math.round(Math.min(255, Math.max(0, b * (1 + random))))
      return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
    },
    avoidOverlap(currentBubble, existBubbles, xMin, xMax, yMin, yMax) {
      const currentRadius = currentBubble.size / 2
      existBubbles.forEach(bubble => {
        const existRadius = bubble.size / 2
        const dx = currentBubble.x - bubble.x
        const dy = currentBubble.y - bubble.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        const minSafeDistance = currentRadius * 0.01 + existRadius * 0.01 + 1
        if (distance < minSafeDistance) {
          const offsetX = (Math.random() - 0.5) * 4
          const offsetY = (Math.random() - 0.5) * 4
          currentBubble.x = Math.max(xMin, Math.min(xMax, currentBubble.x + offsetX))
          currentBubble.y = Math.max(yMin, Math.min(yMax, currentBubble.y + offsetY))
        }
      })
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
  border: none !important;
  padding-top: 0 !important;
  margin-top: 0 !important;
}

.section-title {
  display: none !important;
}

.bubble-chart {
  position: relative;
  width: 100%;
  height: 100%;
  flex: 1;
  background: transparent !important;
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
  color: v-bind(mainColor) !important;
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
  /* ✅ 可选：鼠标悬浮时显示手型指针，提升交互体验 */
  cursor: pointer;
}

.bubble:hover {
  transform: scale(1.05) !important;
}

.bubble-label {
  font-size: 14px !important;
  font-weight: 600 !important;
  margin-bottom: 4px !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
  white-space: nowrap;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
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
  background: transparent !important;
  border-radius: 6px;
  border: none !important;
}
</style>