<template>
  <div class="rhythm-container">
    <div class="ball-config-panel">
      <div class="ball-switch-wrap">
        <h3>样式参数</h3>
      </div>
      <div class="config-with-toggle">
        <div class="ball-config-list">
          <div class="config-item" v-for="(item ) in configItems" :key="item.key">
            <span class="config-label" style="display: none;">{{ item.label }}</span>
            <div
              class="config-progress-vertical"
              @mousedown="(e) => startBallConfigDrag(e, item.key)"
              @click="(e) => setBallConfigByClick(e, item.key)"
              :ref="el => { if (el) progressRefs[item.key] = el }"
            >
              <!-- 修复1：将0-100的数值转换为百分比高度 -->
              <div class="progress-inner" :style="{height: `${rhyConfig[item.key] || 0}%`}"></div>
            </div>
            <span class="config-value" style="display: none;">{{ rhyConfig[item.key] }}</span>
          </div>
        </div>
        <div class="toggle-btn-group">
          <div
            class="toggle-btn"
            :class="{active: toggleStatus === 'close'}"
            @click="switchToggle('close')"
            title="关闭动画"
          ></div>
          <div
            class="toggle-btn"
            :class="{active: toggleStatus === 'play'}"
            @click="switchToggle('play')"
            title="开启小球动画"
          ></div>
          <div
            class="meteor-btn"
            :class="{active: toggleStatus === 'meteor'}"
            @click="switchToggle('meteor')"
            title="开启流星动画"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
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
      default: false
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
      toggleStatus: 'close',
      // ========== 核心：rhyConfig 只保留5个参数 ==========
      rhyConfig: {
        a: 20,
        b: 40,
        c: 30,
        d: 50,
        e: 10
      },
      // ========== 仅保留必要的基础数据 ==========
      isBallConfigDragging: false,
      currentConfigKey: '',
      progressRefs: {},
      configItems: [
         {key: 'a', label: '参数A'},
        {key: 'b', label: '参数B'},

        {key: 'c', label: '参数C'},
        {key: 'd', label: '参数D'},
        {key: 'e', label: '参数E'}
      ],
      // 流星基础配置（独立存在，不混入rhyConfig）
      meteorConfig: {
        angle: 45,
        size: 10,
        tailLength: 50,
        speed: 30
      },
      // 定时器（必要的控制变量）
      autoBallTimer: null,
      autoMeteorTimer: null
    };
  },
  computed: {
    // 仅保留两个状态计算属性
    isBallPlay() {
      return this.toggleStatus === 'play';
    },
    isMeteorPlay() {
      return this.toggleStatus === 'meteor';
    }
  },
  watch: {
    // 仅监听rhyConfig的变化
    rhyConfig: {
      handler(newVal) {
        this.$emit('update-rhy-config', {...newVal});
      },
      deep: true
    },
    // 播放状态监听
    isMusicPlaying(newVal) {
      newVal && this.isBallPlay ? this.startAutoBallGenerate() : this.stopAutoBallGenerate();
      newVal && this.isMeteorPlay ? this.startAutoMeteorGenerate() : this.stopAutoMeteorGenerate();
    },
    isBallPlay(newVal) {
      this.$emit('toggle-ball-play', newVal);
      if (newVal) {
        this.toggleStatus = 'play';
        this.$emit('toggle-meteor-play', false);
        this.isMusicPlaying && this.startAutoBallGenerate();
      }
    },
    isMeteorPlay(newVal) {
      this.$emit('toggle-meteor-play', newVal);
      if (newVal) {
        this.toggleStatus = 'meteor';
        this.$emit('toggle-ball-play', false);
        this.isMusicPlaying && this.startAutoMeteorGenerate();
      }
    },
    // 流星配置独立监听
    meteorConfig: {
      handler(newVal) {
        this.$emit('update-meteor-config', newVal);
      },
      deep: true
    }
  },
  mounted() {
    this.bindDragEvents();
    // 初始化事件发射
    this.$emit('toggle-ball-play', this.isBallPlay);
    this.$emit('toggle-meteor-play', this.isMeteorPlay);
    this.$emit('update-rhy-config', this.rhyConfig);

    this.$nextTick(() => {
      this.isMusicPlaying && this.isBallPlay && this.startAutoBallGenerate();
      this.isMusicPlaying && this.isMeteorPlay && this.startAutoMeteorGenerate();
    });
  },
  deactivated() {
    this.clearAllStates();
  },
  beforeDestroy() {
    this.clearAllStates();
    this.unbindDragEvents();
  },
  methods: {
    // 切换动画状态
    switchToggle(status) {
      this.toggleStatus = status;
      if (status === 'close') {
        this.$emit('toggle-ball-play', false);
        this.$emit('toggle-meteor-play', false);
      } else if (status === 'play') {
        this.$emit('toggle-ball-play', true);
        this.$emit('toggle-meteor-play', false);
      } else if (status === 'meteor') {
        this.$emit('toggle-ball-play', false);
        this.$emit('toggle-meteor-play', true);
        this.triggerGenerateMeteor();
      }
    },
    // 拖拽相关方法
    startBallConfigDrag(e, key) {
      this.isBallConfigDragging = true;
      this.currentConfigKey = key;
      this.calcConfigValueByMouse(e, key);
      e.stopPropagation();
      e.preventDefault();
    },
    handleConfigMouseMove(e) {
      if (this.isBallConfigDragging && this.currentConfigKey) {
        this.calcConfigValueByMouse(e, this.currentConfigKey);
      }
    },
    stopConfigDrag() {
      this.isBallConfigDragging = false;
      this.currentConfigKey = '';
    },
    calcConfigValueByMouse(e, letterKey) {
      let progressDom = this.progressRefs[letterKey] ||
          (e.currentTarget?.classList.contains('config-progress-vertical') && e.currentTarget) ||
          document.querySelector(`.config-item:nth-child(${this.configItems.findIndex(i => i.key === letterKey) + 1}) .config-progress-vertical`);

      if (!progressDom || !(progressDom instanceof HTMLElement)) {
        console.warn(`无法找到进度条元素: ${letterKey}`);
        return;
      }

      try {
        const rect = progressDom.getBoundingClientRect();
        // 修复2：修正数值计算逻辑，确保0对应底部，100对应顶部，且数值范围0-100
        const value = Math.max(0, Math.min(100, ((rect.bottom - e.clientY) / rect.height) * 100));
        this.rhyConfig = {
          ...this.rhyConfig,
          [letterKey]: Math.round(value)
        };
      } catch (error) {
        console.error('计算进度条值时出错:', error);
      }
    },
    setBallConfigByClick(e, key) {
      this.calcConfigValueByMouse(e, key);
    },
    bindDragEvents() {
      document.addEventListener('mousemove', this.handleConfigMouseMove);
      document.addEventListener('mouseup', this.stopConfigDrag);
    },
    unbindDragEvents() {
      document.removeEventListener('mousemove', this.handleConfigMouseMove);
      document.removeEventListener('mouseup', this.stopConfigDrag);
    },
    // 生成流星
    triggerGenerateMeteor() {
      this.$emit('generate-meteor', {
        count: this.rhyConfig.e,
        ...this.meteorConfig
      });
    },
    // 小球自动生成（临时变量仅在方法内使用）
    startAutoBallGenerate() {
      if (!this.isBallPlay) return;
      // 所有计算变量都是局部的，不挂载到实例
      const {a, b, c, d, e} = this.rhyConfig;
      const minSize = Math.floor(a * 0.95) + 5;
      const maxSize = Math.floor(b * 0.9) + 10;
      const minRate = Math.floor(c * 29) + 100;
      const maxRate = Math.floor(d * 49) + 100;
      const numWeight = Math.floor(e * 0.09) + 1;

      this.autoBallTimer = setInterval(() => {
        if (!this.isBallPlay || !this.isMusicPlaying) return;
        for (let i = 0; i < numWeight; i++) {
          const size = Math.floor(Math.random() * (maxSize - minSize)) + minSize;
          this.$emit('generate-rhythm-ball', {size});
        }
      }, Math.floor(Math.random() * (maxRate - minRate)) + minRate);
    },
    stopAutoBallGenerate() {
      this.autoBallTimer && clearInterval(this.autoBallTimer);
      this.autoBallTimer = null;
    },
    // 流星自动生成（同理，临时变量局部化）
    startAutoMeteorGenerate() {
      if (!this.isMeteorPlay) return;
      const {c, d, e} = this.rhyConfig;
      const minRate = Math.floor(c * 29) + 100;
      const maxRate = Math.floor(d * 49) + 100;
      const numWeight = Math.floor(e * 0.09) + 1;

      this.autoMeteorTimer = setInterval(() => {
        if (!this.isMeteorPlay || !this.isMusicPlaying) return;
        this.$emit('generate-meteor', {
          ...this.meteorConfig,
          count: numWeight,
          colorStart: this.mainColorDarkDouble,
          colorEnd: this.mainColorDark,
          minRate,
          maxRate
        });
      }, Math.floor(Math.random() * (maxRate - minRate)) + minRate);
    },
    stopAutoMeteorGenerate() {
      this.autoMeteorTimer && clearInterval(this.autoMeteorTimer);
      this.autoMeteorTimer = null;
    },
    // 统一清理状态
    clearAllStates() {
      this.toggleStatus = 'close';
      this.$emit('toggle-ball-play', false);
      this.$emit('toggle-meteor-play', false);
      this.stopAutoBallGenerate();
      this.stopAutoMeteorGenerate();
    }
  }
};
</script>

<style scoped>
/* 样式部分完全不变，无需修改 */
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
  position: relative;
}

.ball-config-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  z-index: 20;
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

.config-label {
  font-size: 12px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 500;
  white-space: nowrap;
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

.config-value {
  font-size: 11px;
  color: v-bind(mainColorDarkDouble);
}

.toggle-btn-group {
  display: flex;
  flex-direction: column;
  gap: 15px;
  align-self: flex-start;
  margin-top: 20px;
}

.toggle-btn {
  width: 16px;
  height: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  position: relative;
}

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

.toggle-btn.active {
  border-radius: 50%;
  background-color: v-bind(mainColorDark);
}

.toggle-btn.active::before {
  display: none;
}

.meteor-btn {
  width: 16px;
  height: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  position: relative;
}

.meteor-btn::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  width: 100%;
  height: 4px;
  background-color: v-bind(mainColorDark);
  transform: translateY(-50%) ;
  border-radius: 2px;
}



.meteor-btn::after {

  content: '';
  position: absolute;
  top: 50%;
  left: 2px;
  width: 6px;
  height: 2px;
  background-color: v-bind(mainColorDark);
  transform: translateY(-50%) rotate(-45deg);
  border-radius: 1px;
  opacity: 0.6;
}

.meteor-btn.active {
  background-color: v-bind(mainColorDark);
    border-radius: 50%;
  transform: rotate(-45deg);
}

.meteor-btn.active::before,
.meteor-btn.active::after {
  display: none;
}

.toggle-btn:disabled, .meteor-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>