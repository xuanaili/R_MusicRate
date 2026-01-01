<template>
  <div class="parse-sidebar-wrapper">   <!-- 唯一根元素 -->
    <!-- 遮罩层 -->
    <div
      v-show="visible"
      class="parse-sidebar-mask"
      @click="handleClose"
    />

    <!-- 侧边栏主体 -->
    <div v-show="visible" class="parse-sidebar">
      <div class="parse-sidebar-header">
        <h4>文本解析提取单曲名&时间戳</h4>
        <button class="parse-close-btn" @click="handleClose">×</button>
      </div>
    <div class="parse-sidebar-content">
      <textarea
        v-model="parseText"
        placeholder="请粘贴带格式的曲目文本，例如：
0->>>1.One Small Step   0:00
5->>>2.Life Signs   0:26
4->>>3.Nights in Armor   4:58
支持任意数字前缀+序号+歌名+时间戳格式"
        class="parse-textarea"
      ></textarea>
      <div class="parse-tips">{{ parseTips }}</div>
      <button class="parse-submit-btn" @click="handleParse">✅ 一键解析并填充</button>
    </div>
  </div>
      </div>
</template>

<script>
export default {
  name: 'TrackParse',
  props: {
    // 控制侧边栏显隐（父组件传入）
    visible: {
      type: Boolean,
      default: false
    },
    // 主色系（父组件传入，用于样式统一）
    mainColorDark: {
      type: String,
      required: true,
      default: '#2f9465'
    },
    mainColorDarkDouble: {
      type: String,
      required: true,
      default: '#257d51'
    }
  },
  data() {
    return {
      parseText: '',
      parseTips: ''
    }
  },
  watch: {
    // 侧边栏打开时重置文本和提示
    visible(newVal) {
      if (newVal) {
        this.parseText = ''
        this.parseTips = ''
      }
    }
  },
  methods: {
    // ✅ 修改点：Vue2 写法 只触发close事件即可，父组件自己控制显隐
    handleClose() {
      this.$emit('close')
    },
    // 过滤时间戳输入内容 纯数字和冒号
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      const colonCount = filterVal.split(':').length - 1;
      if (colonCount > 2) filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      return filterVal;
    },
    // 时间戳转秒数
    timeToSeconds(timeStr) {
      if (!timeStr || timeStr.length === 0) return 0;
      let timeArr = timeStr.split(':').map(item => Number(item)).filter(item => !isNaN(item));
      let hours = 0, minutes = 0, seconds = 0;
      if (timeArr.length === 2) { minutes = timeArr[0]; seconds = timeArr[1]; }
      else if (timeArr.length === 3) { hours = timeArr[0]; minutes = timeArr[1]; seconds = timeArr[2]; }
      minutes = Math.min(Math.max(minutes, 0), 59);
      seconds = Math.min(Math.max(seconds, 0), 59);
      hours = Math.max(hours, 0);
      return hours * 3600 + minutes * 60 + seconds;
    },
    // 秒数转标准时间戳格式 0:00:00
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const totalSeconds = Math.floor(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const sec = Math.floor(totalSeconds % 60);
      return `${hours}:${minutes.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
    // 核心解析方法 - 解析完成向父组件传解析结果
    handleParse() {
      if (!this.parseText.trim()) {
        this.parseTips = '❌ 请粘贴需要解析的文本内容！';
        return;
      }
      const lines = this.parseText.trim().split('\n').filter(line => line.trim());
      // 兼容所有格式的正则表达式
      const reg = /(?:\d+->>>)?\d+\.?\s*([\u4e00-\u9fa5a-zA-Z\s.\-_()（）&]+)\s+(\d{1,2}:?\d{1,2}:\d{2}|\d{1,2}:\d{2})/;
      const newTrackList = [];

      lines.forEach((line) => {
        const match = line.match(reg);
        if (match && match.length >= 3) {
          const trackName = match[1].trim();
          const trackTime = match[2].trim();
          const filterTime = this.filterDurationInput(trackTime);
          const sec = this.timeToSeconds(filterTime);
          const formatTime = this.secondsToTime(sec);
          newTrackList.push({
            name: trackName || `未知曲目${newTrackList.length + 1}`,
            sec: sec,
            duration: formatTime,
            playDuration: '0:00:00',
            score: 0
          });
        }
      });

      if (newTrackList.length === 0) {
        this.parseTips = '❌ 未解析到有效曲目数据，请检查文本格式！';
      } else {
        this.parseTips = `✅ 解析成功！共提取到 ${newTrackList.length} 首曲目，已自动填充！`;
        // 核心：解析成功，向父组件传递解析后的曲目列表
        this.$emit('parse-success', newTrackList);
      }
    }
  }
}
</script>

<style scoped>
.parse-sidebar-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.2);
  backdrop-filter: blur(2px);
  z-index: 9998;
  transition: all 0.3s;
}

.parse-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 480px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border-left: 1px solid rgba(255, 255, 255, 0.5);
  z-index: 9999;
  box-sizing: border-box;
  padding: 15px;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-in-out;
  color: #333;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.parse-sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
	padding-bottom: 10px;
  border-bottom: 2px solid v-bind(mainColorDark);
  margin-bottom: 15px;
}

.parse-sidebar-header h4 {
  margin: 0;
  font-size: 16px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
}

.parse-close-btn {
  background: transparent;
	border: none;
	font-size: 18px;
	color: #999;
	cursor: pointer;
	width: auto;
	height: auto;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 0;
	transition: all 0.1s;
  padding:0 6px;
}

.parse-close-btn:hover {
  color: #dc2626;
  transform: scale(1.1);
  background: transparent;
}

.parse-sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.parse-textarea {
  flex: 1;
  width: 100%;
  padding: 10px;
	border-radius: 4px;
  border: none;
	background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  color: v-bind(mainColorDarkDouble);
  outline: none;
  resize: none;
  line-height: 1.6;
  font-size: 13px;
}

.parse-textarea:focus {
  background: rgba(255, 255, 255, 0.5);
  box-shadow: none;
  border-color: transparent;
}

.parse-tips {
  height: 20px;
  line-height: 20px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: v-bind(mainColorDark);
}

.parse-submit-btn {
  background: v-bind(mainColorDark);
  color: #fff;
  border: none;
	padding: 8px 0;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
	font-weight: 600;
	transition: all 0.2s;
}

.parse-submit-btn:hover {
  background-color: v-bind(mainColorDarkDouble) !important;
  opacity: 0.95;
}
</style>