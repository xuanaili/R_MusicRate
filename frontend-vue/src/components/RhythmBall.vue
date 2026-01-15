<template>
  <div class="rhythm-container">
    <div class="ball-config-panel">
      <div class="ball-switch-wrap">
        <h3>样式参数</h3>
      </div>
      <!-- 配置项和开关横向排列 -->
      <div class="config-with-toggle">
        <div class="ball-config-list">
          <div class="config-item" v-for="item in configItems" :key="item.key">
            <span class="config-label" style="display: none;">{{ item.label }}</span>
            <div
              class="config-progress-vertical"
              @mousedown="(e) => startBallConfigDrag(e, item.key)"
              @click="(e) => setBallConfigByClick(e, item.key)"
            >
              <div class="progress-inner" :style="{height: `${getPercent(item.key)}%`}"></div>
            </div>
            <span class="config-value" style="display: none;">{{ currentBallConfig[item.key] }}</span>
          </div>
        </div>
        <!-- 两个开关垂直排列 -->
        <div class="toggle-btn-group">
          <!-- 开关1：关闭状态 -->
          <div
            class="toggle-btn"
            :class="{active: toggleStatus === 'close'}"
            @click="switchToggle('close')"
          ></div>
          <!-- 开关2：小球开启状态 -->
          <div
            class="toggle-btn"
            :class="{active: toggleStatus === 'play'}"
            @click="switchToggle('play')"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import globalConfig from '@/config/index.js';

export default {
  name: 'RhythmBall',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    isMusicPlaying: {
      type: Boolean,
      required: true,
      default: true
    },
    mainColorDark: {
      type: String,
      required: true,
      default: '#2f9465'
    },
    mainColorDarkDouble: {
      type: String,
      required: true,
      default: '#257d51'
    },
    initialBallConfig: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      toggleStatus: 'close', // 切换状态：close-关闭 play-小球开启
      currentBallConfig: {},
      isBallConfigDragging: false,
      currentConfigKey: '',
      autoBallTimer: null,
      configItems: [
        { key: 'minSize', label: '最小尺寸' },
        { key: 'maxSize', label: '最大尺寸' },
        { key: 'minRate', label: '最小速率' },
        { key: 'maxRate', label: '最大速率' },
        { key: 'numWeight', label: '数量权重' }
      ]
    };
  },
  computed: {
    // 计算是否开启小球
    isBallPlay() {
      return this.toggleStatus === 'play';
    }
  },
  watch: {
    album: {
      handler(newVal) {
        this.currentBallConfig = this.getBallConfigByTag(newVal.tags);
      },
      deep: true,
      immediate: true
    },
    isMusicPlaying(newVal) {
      newVal && this.isBallPlay ? this.startAutoBallGenerate() : this.stopAutoBallGenerate();
    },
    isBallPlay(newVal) {
      this.$emit('toggle-ball-play', newVal);
      newVal && this.isMusicPlaying ? this.startAutoBallGenerate() : this.stopAutoBallGenerate();
    }
  },
  mounted() {
    this.currentBallConfig = {
      ...globalConfig.ballConfig.default,
      ...this.initialBallConfig,
      ...this.getBallConfigByTag(this.album.tags)
    };

    this.$nextTick(() => {
      this.isMusicPlaying && this.isBallPlay && this.startAutoBallGenerate();
    });
  },
  deactivated() {
    this.stopAutoBallGenerate();
  },
  beforeDestroy() {
    clearInterval(this.autoBallTimer);
    this.isBallConfigDragging = false;
    this.currentConfigKey = '';
    document.removeEventListener('mousemove', this.handleBallConfigMouseMove);
    document.removeEventListener('mouseup', this.stopBallConfigDrag);
    this.stopAutoBallGenerate();
  },
  methods: {
    getBallConfigByTag(tags) {
      if (!tags || !Array.isArray(tags) || tags.length === 0) {
        return globalConfig.ballConfig.default;
      }
      const firstTag = tags[0];
      return globalConfig.ballConfig[firstTag] || globalConfig.ballConfig.default;
    },
    // 切换开关状态（互斥逻辑）
    switchToggle(status) {
      this.toggleStatus = status;
    },
    getPercent(key) {
      const config = this.currentBallConfig;
      let val = config[key];
      let max, min;
      switch (key) {
        case 'minSize':
        case 'maxSize':
          min = 0;
          max = 1000;
          break;
        case 'minRate':
        case 'maxRate':
          min = 10;
          max = 4000;
          break;
        case 'numWeight':
          min = 0;
          max = 10;
          break;
        default:
          return 0;
      }
      const percent = ((val - min) / (max - min)) * 100;
      return Math.max(0, Math.min(100, percent));
    },
    startBallConfigDrag(e, key) {
      this.isBallConfigDragging = true;
      this.currentConfigKey = key;
      this.calcBallConfigValueByMouse(e, key);
      document.addEventListener('mousemove', this.handleBallConfigMouseMove);
      document.addEventListener('mouseup', this.stopBallConfigDrag);
      e.stopPropagation();
      e.preventDefault();
    },
    handleBallConfigMouseMove(e) {
      if (this.isBallConfigDragging && this.currentConfigKey) {
        this.calcBallConfigValueByMouse(e, );
      }
    },
    stopBallConfigDrag() {
      this.isBallConfigDragging = false;
      this.currentConfigKey = '';
      document.removeEventListener('mousemove', this.handleBallConfigMouseMove);
      document.removeEventListener('mouseup', this.stopBallConfigDrag);
    },
    calcBallConfigValueByMouse(e, key) {
      const progressDom = e.currentTarget.querySelector('.progress-inner').parentNode;
      const rect = progressDom.getBoundingClientRect();
      let percent = ((rect.bottom - e.clientY) / rect.height) * 100;
      percent = Math.max(0, Math.min(100, percent));
      this.setBallConfigValueByPercent(key, percent);
    },
    setBallConfigValueByPercent(key, percent) {
      let min, max, step = 1;
      switch (key) {
        case 'minSize':
        case 'maxSize':
          min = 0;
          max = 1000;
          step = 1;
          break;
        case 'minRate':
        case 'maxRate':
          min = 10;
          max = 4000;
          step = 10;
          break;
        case 'numWeight':
          min = 0;
          max = 10;
          step = 1;
          break;
        default:
          return;
      }
      let realValue = ((max - min) * (percent / 100)) + min;
      realValue = Math.round(realValue / step) * step;
      realValue = Math.max(min, Math.min(max, realValue));
      this.currentConfigKey = key;
      this.currentBallConfig[key] = realValue;
      this.$emit('update-ball-config', {...this.currentBallConfig});
    },
    setBallConfigByClick(e, key) {
      this.currentConfigKey = key;
      this.calcBallConfigValueByMouse(e, key);
    },
    startAutoBallGenerate() {
      if (!this.isBallPlay) return;
      const {minRate, maxRate, numWeight} = this.currentBallConfig;
      this.autoBallTimer = setInterval(() => {
        if (!this.isBallPlay || !this.isMusicPlaying) return;
        for (let i = 0; i < numWeight; i++) {
          const size = Math.floor(Math.random() * (this.currentBallConfig.maxSize - this.currentBallConfig.minSize)) + this.currentBallConfig.minSize;
          this.$emit('generate-rhythm-ball', {size});
        }
      }, Math.floor(Math.random() * (maxRate - minRate)) + minRate);
    },
    stopAutoBallGenerate() {
      this.autoBallTimer && (clearInterval(this.autoBallTimer), this.autoBallTimer = null);
    }
  }
};
</script>

<style scoped>
.rhythm-container {
  width: 100%;
  background: transparent !important;
  border-radius: 8px;
  padding: 20px;
  box-shadow: none;
  box-sizing: border-box;
  flex: 1;
  min-height: 350px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.ball-config-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.ball-switch-wrap {
  width: 100%;
}

.ball-switch-wrap h3 {
  margin: 0;
  font-size: 16px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 4px solid v-bind(mainColorDark);
}

/* 配置项和开关横向排列容器 */
.config-with-toggle {
  display: flex;
  align-items: stretch;
  gap: 12px;
  height: calc(100% - 40px);
}

.ball-config-list {
  display: flex;
  justify-content: space-around;
  align-items: stretch;
  flex: 1;
  gap: 8px;
}

.config-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
}

.config-progress-vertical {
  width: 8px;
  height: 100%;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  flex-direction: column-reverse;
  cursor: pointer;
}

.progress-inner {
  width: 100%;
  background: v-bind(mainColorDark);
  border-radius: 4px;
  transition: height 0.3s ease;
}

/* 开关按钮组：垂直排列 */
.toggle-btn-group {
  display: flex;
  flex-direction: column;
  gap: 15px; /* 开关间距 */
  align-self: flex-start;
  margin-top: 20px; /* 整体向上位置 */
}

/* 通用开关样式 */
.toggle-btn {
  width: 16px;
  height: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  position: relative;
}

/* 未激活状态 - 粗横线 */
.toggle-btn::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  width: 100%;
  height: 4px;
  background-color: v-bind(mainColorDark);
  border-radius: 2px;
  transform: translateY(-50%);
}

/* 激活状态 - 实心圆点 */
.toggle-btn.active {
  border-radius: 50%;
  background-color: v-bind(mainColorDark);
}

/* 激活状态隐藏横线 */
.toggle-btn.active::before {
  display: none;
}
</style>