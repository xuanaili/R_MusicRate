<template>
  <div class="appearance-panel">
    <!-- 蒙版透明度调节（localStorage 持久化，联动侧边栏 + 专辑详情页 + 主页） -->
    <div class="appearance-card common-card">
      <div class="card-title">蒙版透明度</div>
      <p class="appearance-desc">调节页面毛玻璃遮罩的不透明度，值越大遮罩越实白</p>
      <div class="slider-row">
        <span class="slider-label">更透明</span>
        <input
          type="range"
          class="mask-slider"
          min="0"
          max="60"
          :value="maskOpacity"
          :style="trackStyle"
          @input="handleMaskChange"
        />
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
import { MASK_DEFAULT, getSavedMaskOpacity, applyMaskOpacity } from '@/utils/maskOpacity'

export default {
  name: 'AppearancePanel',
  props: {
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      maskOpacity: MASK_DEFAULT
    }
  },
  computed: {
    // 滑块轨道渐变色：已选区间用主题色填充
    trackStyle() {
      const pct = this.maskOpacity
      return {
        background: `linear-gradient(to right, ${this.mainColorDark} 0%, ${this.mainColorDark} ${pct}%, rgba(255, 255, 255, 0.4) ${pct}%, rgba(255, 255, 255, 0.4) 100%)`
      }
    }
  },
  created() {
    // 读取已保存值（main.js 启动时已应用过一次，这里与当前滑块状态对齐）
    this.maskOpacity = getSavedMaskOpacity()
    this.applyMaskOpacityLocal()
  },
  methods: {
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

.appearance-desc {
  font-size: 12px;
  color: #888;
  margin-bottom: 14px;
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

.mask-slider {
  -webkit-appearance: none;
  appearance: none;
  flex: 1;
  height: 6px;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.4);
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
