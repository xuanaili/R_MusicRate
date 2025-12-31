<template>
  <!-- 音频波形可视化独立组件 -->
  <div class="audio-wave-container">
    <h3>🎵 实时音频波形节奏可视化</h3>
    <canvas ref="audioCanvas" class="audio-wave-canvas"></canvas>
  </div>
</template>

<script>
export default {
  name: 'AudioWave',
  props: {
    // ✅ 核心props：传入页面的<audio>标签DOM对象，必传
    audioElement: {
      type: Object,
      required: true,
      default: null
    }
  },
  data() {
    return {
      audioContext: null,       // 音频上下文核心对象
      audioSource: null,        // 音频源
      analyser: null,           // 音频分析器，获取声音振幅/频率数据
      canvasCtx: null,          // canvas画布上下文
      canvasWidth: 0,           // canvas宽度
      canvasHeight: 0,          // canvas高度
      animationFrameId: null,   // 动画帧id，用于销毁时停止动画
      audioDataArray: null,     // 音频振幅数据数组
      isAudioInited: false,     // 音频是否初始化成功
    };
  },
  watch: {
    // 监听audioElement变化，重新初始化（防止音频标签动态赋值）
    audioElement: {
      handler(newVal) {
        if (newVal) {
          this.$nextTick(() => {
            this.initAudioVisualization();
          });
        }
      },
      immediate: true
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.initAudioVisualization();
    });
  },
  deactivated() {
    this.destroyAudioVisualization();
  },
  beforeDestroy() {
    this.destroyAudioVisualization();
  },
  methods: {
    // 初始化音频可视化核心逻辑
    async initAudioVisualization() {
      try {
        // 兼容性处理：适配不同浏览器的AudioContext前缀
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) {
          alert('你的浏览器不支持音频可视化功能，请升级Chrome/Edge/Firefox最新版后重试！');
          return;
        }
        // 校验传入的audio标签是否有效
        if (!this.audioElement || !(this.audioElement instanceof HTMLAudioElement)) {
          console.error('❌ 传入的不是有效的audio标签DOM对象');
          return;
        }
        // 初始化画布
        this.initCanvas();
        // 创建音频上下文和分析器
        this.audioContext = new AudioContext();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;          // 波形柱数量，256最佳（少而明显）
        this.analyser.smoothingTimeConstant = 0.3; // 波形平滑度
        const bufferLength = this.analyser.frequencyBinCount;
        this.audioDataArray = new Uint8Array(bufferLength);

        // 核心逻辑：将audio标签接入音频上下文
        this.audioSource = this.audioContext.createMediaElementSource(this.audioElement);
        this.audioSource.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);

        // 启动波形绘制动画
        this.drawAudioWave();
        this.isAudioInited = true;
        console.log('✅ 音频可视化初始化成功！波形将跟随音乐节奏跳动');
      } catch (err) {
        console.error('❌ 音频可视化初始化失败：', err);
        const errorTips = [
          '📌 音频可视化启动失败',
          '原因：浏览器音频策略限制',
          '',
          '✅ 解决方法：',
          '1. 点击页面任意位置后再播放音乐',
          '2. 使用 Chrome/Edge/Firefox 最新版浏览器'
        ].join('\n');
        alert(errorTips);
        this.isAudioInited = false;
      }
    },
    // 初始化画布尺寸（自适应父容器）
    initCanvas() {
      const canvas = this.$refs.audioCanvas;
      if (!canvas) return;
      this.canvasCtx = canvas.getContext('2d');
      const parentDom = canvas.parentElement;
      this.canvasWidth = parentDom.clientWidth - 40;
      this.canvasHeight = parentDom.clientHeight - 80;
      canvas.width = this.canvasWidth;
      canvas.height = this.canvasHeight;
    },
    // 绘制实时音频波形
    drawAudioWave() {
      if (!this.canvasCtx || !this.analyser || !this.isAudioInited) return;
      this.animationFrameId = requestAnimationFrame(() => this.drawAudioWave());
      // 清空画布
      this.canvasCtx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
      // 获取时域数据（波形图专用，音乐跳动更精准）
      this.analyser.getByteTimeDomainData(this.audioDataArray);

      this.canvasCtx.fillStyle = '#2ea0d6'; // 和主组件配色一致
      this.canvasCtx.lineWidth = 2;
      const barWidth = this.canvasWidth / this.audioDataArray.length * 1.8;
      let barHeight;
      let x = 0;
      for (let i = 0; i < this.audioDataArray.length; i++) {
        barHeight = (this.audioDataArray[i] - 128) / 128 * this.canvasHeight * 0.9;
        const y = (this.canvasHeight - barHeight) / 2;
        this.canvasCtx.beginPath();
        this.canvasCtx.roundRect(x, y, barWidth - 1, barHeight, 3);
        this.canvasCtx.fill();
        x += barWidth;
      }
    },
    // 销毁音频资源+画布，防止内存泄漏
    destroyAudioVisualization() {
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = null;
      }
      if (this.audioSource) {
        this.audioSource.disconnect();
        this.audioSource = null;
      }
      if (this.analyser) {
        this.analyser.disconnect();
        this.analyser = null;
      }
      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }
      this.canvasCtx = null;
      this.isAudioInited = false;
    }
  }
};
</script>

<style scoped>
.audio-wave-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.audio-wave-container h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #111827;
}

.audio-wave-canvas {
  width: 100%;
  height: 100%;
  border-radius: 6px;
	background-color: #f9fafb;
}
</style>