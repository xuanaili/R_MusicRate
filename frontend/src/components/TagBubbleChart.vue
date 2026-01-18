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
        @click="handleTagClick(item.tag)"
      >
        <!-- 显示【】外的英文 -->
        <div class="bubble-label">{{ item.tag.split('【')[0].trim() || item.tag }}</div>
        <div class="bubble-value">{{ item.percent }}%</div>
      </div>

      <!-- 过滤标签点击按钮 -->
      <div
        v-if="filteredOutTags.length > 0"
        class="filtered-tags-btn"
        @click.stop="showFilteredTags = !showFilteredTags"
      >
        其他
      </div>

      <!-- 过滤标签弹窗 - 修改class名称以复用样式 -->
      <div
        v-if="showFilteredTags && filteredOutTags.length > 0"
        class="tag-options-list filtered-tags-popup"
        @click.stop
      >
        <div
          class="tag-option"
          v-for="(tag, idx) in filteredOutTags"
          :key="idx"
          :title="tag.tag.match(/【(.*?)】/)?.[1] || tag.tag"
          @click="handleTagClick(tag.tag)"
        >
          <span class="tag-name">{{ tag.tag.split('【')[0].trim() || tag.tag }}</span>
          <span class="tag-percent">{{ tag.percent }}%</span>
        </div>
      </div>

      <!-- 点击遮罩关闭弹窗 -->
      <div
          v-if="showFilteredTags && filteredOutTags.length > 0"
          class="popup-mask"
          @click="showFilteredTags = false"
      ></div>
    </div>
    <!-- 无数据提示 -->
    <div v-else class="no-chart-data">
      <slot name="empty">暂无其他用户为该专辑添加标签</slot>
    </div>

    <!-- 新增标签侧边栏组件 -->
    <AddTag
        :visible="showAddTagSidebar"
        :mainColorDark="mainColor"
        :mainColorDarkDouble="mainColor"
        @close="showAddTagSidebar = false"
        ref="addTagRef"
        :uid="'add-tag-bubble'"
    />
  </div>
</template>

<script>
// script部分代码保持不变，这里省略以突出重点
import axios from 'axios'
import AddTag from '@/components/sidebar/AddTag.vue' // 路径和你的保持一致

export default {
  name: 'TagBubbleChart',
  components: {
    AddTag
  },
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
  data() {
    return {
      showAddTagSidebar: false, // 控制新增标签侧边栏显示
      isCheckingTag: false,     // 防止重复点击
      isAdmin: false,           // 管理员标识
      showFilteredTags: false   // 控制过滤标签弹窗显示
    }
  },
  // 完全复用你的管理员判断逻辑
  created() {
    if (!localStorage.getItem('token')) {
      this.isAdmin = false;
      return;
    }
    this.isAdmin = localStorage.getItem('is_admin') === '1';
  },
  watch: {
    '$route'() {
      this.isAdmin = localStorage.getItem('is_admin') === '1';
    }
  },
  computed: {
    // 计算过滤掉的标签列表
    filteredOutTags() {
      const total = this.tagStats.reduce((sum, item) => sum + item.count, 0)
      if (total === 0) return []
      // 筛选占比 ≤5% 的标签
      return this.tagStats.filter(item => {
        const percent = (item.count / total) * 100
        return percent <= 5
      }).map(item => {
        const percent = ((item.count / total) * 100).toFixed(1)
        return {
          tag: item.tag,
          percent: percent
        }
      })
    },
    chartData() {
      const {tagStats, mainColor, sizeRange} = this
      const total = tagStats.reduce((sum, item) => sum + item.count, 0)
      if (total === 0) return []
      // 过滤占比 > 5% 的标签
      const filteredTags = tagStats.filter(item => {
        const percent = (item.count / total) * 100;
        return percent > 5;
      });
      // 过滤后无数据则直接返回
      if (filteredTags.length === 0) return [];
      const generatedBubbles = []
      const baseStep = Math.max(8, 20 - filteredTags.length * 0.3)
      const safeXMin = 8
      const safeXMax = 92
      const safeYMin = 15
      const safeYMax = 85

      return filteredTags.map((item, idx) => {
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
    async handleTagClick(tagName) {
      if (this.isCheckingTag) return
      this.isCheckingTag = true

      try {
        const tagRes = await axios.get('/api/tags/detail', {
          params: {tagName: tagName},
          headers: {
            'Authorization': localStorage.getItem('token') || ''
          }
        })

        if (tagRes.data.code === 200) {
          this.$router.push({
            path: '/tag-detail',
            query: {tagName: encodeURIComponent(tagName)}
          })
        } else if (tagRes.data.code === 404) {
          if (this.isAdmin) {
            this.showAddTagSidebar = true
            setTimeout(() => {
              if (this.$refs.addTagRef) {
                this.$refs.addTagRef.tag.tags_name = tagName
              }
            }, 100)
          }
        }
      } catch (error) {
        console.error('处理标签点击失败：', error)
      } finally {
        this.isCheckingTag = false
      }
    },
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
  position: relative;
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

/* 过滤标签按钮样式 - 微调以匹配整体风格 */
.filtered-tags-btn {
  position: absolute;
  right: 10px;
  bottom: 10px;
  padding: 6px 10px;
  color: v-bind(mainColorDarkDouble) !important;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
  z-index: 101;
  border-radius: 4px;
}

.filtered-tags-btn:hover {
  background: rgba(0,0,0,0.05) !important;
}

/* 过滤标签弹窗样式 - 完全复用可选标签列表样式 */
.filtered-tags-popup {
  position: absolute;
  right: 10px;
  bottom: 40px;
  width: 280px;
  max-height:200px;
  z-index: 101;
  gap:5px;
  padding:5px;
}

/* 复用可选标签的item样式 */
.tag-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding:6px 10px;
  cursor:pointer;
  font-size:14px;
  border-radius:4px;
  transition: background 0.2s;
	color: v-bind(mainColorDarkDouble) !important;
}

.tag-option:hover {
  background: rgba(0,0,0,0.05) !important;
  color: v-bind(mainColor) !important;
}

.tag-name {
  max-width: 200px;
  word-wrap: break-word;
  white-space: normal;
  line-height: 1.4;
}

.tag-percent {
  color: v-bind(mainColor) !important;
  font-weight: 500;
  min-width: 40px;
  text-align: right;
  margin-left: 8px;
}

/* 弹窗遮罩层 */
.popup-mask {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: transparent;
  z-index: 100;
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
  cursor: pointer;
  box-sizing: border-box !important;
  padding: 0 8px;
  overflow: hidden;
}

.bubble:hover {
  transform: scale(1.05) !important;
}

.bubble-label {
  font-size: 14px !important;
  font-weight: 600 !important;
  margin-bottom: 4px !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
  white-space: normal;
  text-align: center;
  line-height: 1.4;
  max-width: calc(100% - 16px);
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

/* 复用滚动条样式 */
.filtered-tags-popup::-webkit-scrollbar {
  width:4px;
}

.filtered-tags-popup::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius:2px;
}
</style>