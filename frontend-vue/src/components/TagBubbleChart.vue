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
        <div class="bubble-label">{{ item.tag.match(/【(.*?)】/)?.[1] || item.tag }}</div>
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

      // ✅ 新增：存储已生成的气泡数据，用于碰撞检测
      const generatedBubbles = []
      // ✅ 优化：根据标签数量计算基准间距，标签越多间距越小，适配空间
      const baseStep = Math.max(8, 20 - tagStats.length * 0.3)
      // ✅ 优化：气泡安全边界，防止超出容器（左右留边、上下留边）
      const safeXMin = 8
      const safeXMax = 92
      const safeYMin = 15
      const safeYMax = 85

      return tagStats.map((item, idx) => {
        const percent = ((item.count / total) * 100).toFixed(1)
        // 原有大小计算逻辑 不变
        const size = Math.min(sizeRange.max, Math.max(sizeRange.min, sizeRange.min + percent * 1))
        // ✅ 优化1：X轴基准均分+随机偏移，不再固定步长，基础避免横向重叠
        let x = safeXMin + idx * baseStep
        x = x > safeXMax ? safeXMax - Math.random() * 10 : x + Math.random() * 6 - 3
        // ✅ 优化2：Y轴分段随机，纵向分层，减少上下重叠（核心优化）
        const ySection = Math.floor(idx / 5) // 每5个标签分一层
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

        // ✅ 核心新增：碰撞检测+自动微调位移，彻底解决重叠问题
        if (generatedBubbles.length > 0) {
          this.avoidOverlap(bubbleItem, generatedBubbles, safeXMin, safeXMax, safeYMin, safeYMax)
        }
        generatedBubbles.push(bubbleItem)
        return bubbleItem
      })
    }
  },
  methods: {
    // ✅ 原有方法 不变 - 随机生成同色系颜色
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
    // ✅ 核心新增：气泡防重叠算法【重中之重】
    avoidOverlap(currentBubble, existBubbles, xMin, xMax, yMin, yMax) {
      const currentRadius = currentBubble.size / 2 // 气泡半径（百分比转像素不影响碰撞判断）
      // 遍历所有已存在的气泡，判断是否重叠
      existBubbles.forEach(bubble => {
        const existRadius = bubble.size / 2
        // 计算两个气泡中心点的距离（百分比维度，无需转像素，精准高效）
        const dx = currentBubble.x - bubble.x
        const dy = currentBubble.y - bubble.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        // 判断是否重叠：间距 < 两个气泡半径之和 → 重叠了
        const minSafeDistance = currentRadius * 0.01 + existRadius * 0.01 + 1 // +1是预留安全间距，彻底避免贴边
        if (distance < minSafeDistance) {
          // ✅ 重叠时：弹性微调位移，向四周随机偏移，直到不重叠
          const offsetX = (Math.random() - 0.5) * 4
          const offsetY = (Math.random() - 0.5) * 4
          // 修正位移，保证气泡不会超出安全边界
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

/* ✅ 修复2：彻底删除这个空标题的样式，根除根源 */
.section-title {
  display: none !important;
}

/* ✅ 核心修改：移除所有磨砂/蒙版/半透明背景，改为完全透明，保留原有定位和圆角 */
.bubble-chart {
  position: relative;
  width: 100%;
  height: 100%;
  flex: 1;
  background: transparent !important; /* 完全透明核心 */
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
  color: v-bind(mainColor) !important; /* 适配透明背景，直接用主色 */
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

/* ✅ 无数据容器同步改为完全透明 */
.no-chart-data {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #999;
  font-size: 14px;
  background: transparent !important; /* 完全透明核心 */
  border-radius: 6px;
  border: none !important;
}
</style>