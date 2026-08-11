<template>
  <div class="appearance-panel">
    <!-- 蒙版透明度调节（localStorage 持久化，联动侧边栏 + 专辑详情页 + 主页） -->
    <div class="appearance-card common-card">
      <div class="card-title">蒙版透明度</div>
      <p class="appearance-desc">调节页面毛玻璃遮罩的不透明度，值越大遮罩越实白</p>
      <div class="slider-row">
        <span class="slider-label">更透明</span>
        <div class="mask-slider-wrap">
          <!-- 拖动时 thumb 上方数值气泡（pointer-events:none 不挡拖动） -->
          <div
            v-show="dragging"
            class="mask-bubble"
            :style="bubbleStyle"
          >{{ maskOpacity }}%</div>
          <input
            type="range"
            class="mask-slider"
            min="0"
            :max="MASK_MAX"
            :value="maskOpacity"
            :style="trackStyle"
            @input="handleMaskChange"
            @mousedown="dragging = true"
            @touchstart="dragging = true"
            @mouseup="dragging = false"
            @mouseleave="dragging = false"
            @touchend="dragging = false"
          />
          <!-- 0/25/60 刻度线（绝对定位在轨道下方，与 thumb 值位置对齐） -->
          <div class="mask-scale">
            <span
              v-for="t in tickMarks"
              :key="t"
              class="mask-tick"
              :style="tickStyle(t)"
            >{{ t }}</span>
          </div>
        </div>
        <span class="slider-label">更实白</span>
        <span class="slider-value" :style="{ color: mainColorDark }">{{ maskOpacity }}%</span>
      </div>
    </div>

    <div class="appearance-tip">
      <p>💡 该设置保存在本机浏览器，会同步应用到播放列表侧边栏、专辑详情页与主页蒙版。</p>
      <p>点击「恢复默认」可将蒙版透明度重置为 25%。</p>
    </div>

    <button class="reset-btn" :style="{ backgroundColor: mainColorDark }" @click="resetMask">
      恢复默认（25%）
    </button>
  </div>
</template>

<script>
// 蒙版透明度取值区间、读写、全局应用统一收敛到 utils/maskOpacity.js（main.js 启动时也会调用恢复）
import { MASK_DEFAULT, MASK_MAX, getSavedMaskOpacity, applyMaskOpacity } from '@/utils/maskOpacity'

// thumb 映射宽度（实测：Edge/Chrome 按 content-box 宽度 16px 计算 value→thumb 位移，不含 2px border）
// 见 ai/knowledge：滑轨渐变补偿公式 fillStop = calc(pct% + THUMB_W*(0.5-pct)px)，使渐变边界始终落在 thumb 中心
const THUMB_W = 16

export default {
  name: 'AppearancePanel',
  props: {
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      maskOpacity: MASK_DEFAULT,
      dragging: false,
      tickMarks: [0, 25, 60],
      MASK_MAX // 模板无法直接访问模块常量，暴露到实例供 :max 绑定
    }
  },
  computed: {
    // 滑块轨道渐变色：已选区间用主题色填充，边界按 thumb 宽度补偿对齐 thumb 中心
    trackStyle() {
      const stop = this.compensatedStop(this.maskOpacity)
      return {
        background: `linear-gradient(to right, ${this.mainColorDark} 0%, ${this.mainColorDark} ${stop}, rgba(255, 255, 255, 0.4) ${stop}, rgba(255, 255, 255, 0.4) 100%)`
      }
    },
    // 数值气泡：定位在 thumb 中心正上方
    bubbleStyle() {
      return {
        left: this.compensatedStop(this.maskOpacity)
      }
    }
  },
  methods: {
    // 渐变/气泡/刻度共用的补偿位置：value 的 thumb 中心 = pct*100% + THUMB_W*(0.5-pct)px
    compensatedStop(value) {
      const pct = value / MASK_MAX
      return `calc(${(pct * 100).toFixed(2)}% + ${(THUMB_W * (0.5 - pct)).toFixed(2)}px)`
    },
    tickStyle(t) {
      return { left: this.compensatedStop(t) }
    },
    handleMaskChange(e) {
      this.maskOpacity = parseInt(e.target.value, 10)
      this.saveAndApply()
    },
    resetMask() {
      this.maskOpacity = MASK_DEFAULT
      this.saveAndApply()
      this.showMsg('success', '蒙版透明度已重置')
    },
    saveAndApply() {
      localStorage.setItem('maskOpacity', this.maskOpacity)
      this.applyMaskOpacityLocal()
    },
    // 用当前滑块值写全局 CSS 变量（联动 WebHome/PlayerPlaylist/AlbumDetail 毛玻璃容器）
    applyMaskOpacityLocal() {
      applyMaskOpacity()
    },
    showMsg(type, msg) {
      if (this.$message && this.$message[type]) {
        this.$message[type](msg)
      } else {
        alert(msg)
      }
    }
  },
  created() {
    // 读取已保存值（main.js 启动时已应用过一次，这里与当前滑块状态对齐）
    this.maskOpacity = getSavedMaskOpacity()
    this.applyMaskOpacityLocal()
  }
}
</script>

<style scoped>
.appearance-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.common-card {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  padding: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.appearance-card {
  margin-bottom: 26px; /* 给轨道下方绝对定位的刻度线预留空间，避免压住下方提示 */
}

.appearance-desc {
  font-size: 12px;
  color: #888;
  margin-bottom: 22px; /* 给拖动时上方数值气泡预留空间，避免压住说明文字 */
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.slider-label {
  font-size: 12px;
  color: #888;
  flex-shrink: 0;
}

/* 滑块包裹层：定位数值气泡（上方）与刻度线（下方），刻度与轨道左端严格对齐 */
.mask-slider-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
}

.mask-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  margin: 0; /* input 默认 margin 2px，会让轨道相对包裹层右偏，导致刻度/气泡与轨道错位 */
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.4);
}

/* 拖动数值气泡：位于 thumb 中心正上方，pointer-events 不拦截拖动 */
.mask-bubble {
  position: absolute;
  bottom: calc(100% + 7px);
  left: 0;
  transform: translateX(-50%);
  background: v-bind(mainColorDark);
  color: #fff;
  font-size: 11px;
  line-height: 1;
  padding: 3px 7px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.mask-bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: v-bind(mainColorDark);
}

/* 0/25/60 刻度线：绝对定位在轨道下方，left 与 thumb 值位置对齐 */
.mask-scale {
  position: absolute;
  top: calc(100% + 3px);
  left: 0;
  right: 0;
  height: 18px;
  pointer-events: none;
}

.mask-tick {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 10px;
  color: #999;
  line-height: 1.2;
}

.mask-tick::before {
  content: '';
  width: 1px;
  height: 4px;
  background: #bbb;
  margin-bottom: 2px;
}

.mask-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: v-bind(mainColorDark);
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.mask-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: v-bind(mainColorDark);
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.slider-value {
  font-size: 13px;
  font-weight: 600;
  width: 40px;
  text-align: right;
  flex-shrink: 0;
}

.appearance-tip {
  font-size: 12px;
  color: #888;
  line-height: 1.7;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  padding: 10px 12px;
}

.appearance-tip p {
  margin: 0;
}

.reset-btn {
  width: 100%;
  padding: 8px 0;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.reset-btn:hover {
  opacity: 0.9;
}
</style>
