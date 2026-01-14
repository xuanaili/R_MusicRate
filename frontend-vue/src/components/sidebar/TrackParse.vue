<template>
  <div class="parse-sidebar-wrapper">
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
🖤🖤Introduction  0:00
💛💙完全感覚Dreamer  5:18
💛💛🧡🤍🤍The Golden Age 0:00
0->>>1.One Small Step   0:00
5->>>2.Life Signs   0:26
支持 emoji+歌名+时间戳 / 数字前缀+序号+歌名+时间戳 任意格式"
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
    visible: {
      type: Boolean,
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
    }
  },
  data() {
    return {
      parseText: '',
      parseTips: ''
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.parseText = ''
        this.parseTips = ''
      }
    }
  },
  methods: {
    handleClose() {
      this.$emit('close')
    },
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      const colonCount = filterVal.split(':').length - 1;
      if (colonCount > 2) filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      return filterVal;
    },
    timeToSeconds(timeStr) {
      if (!timeStr || timeStr.length === 0) return 0;
      let timeArr = timeStr.split(':').map(item => Number(item)).filter(item => !isNaN(item));
      let hours = 0, minutes = 0, seconds = 0;
      if (timeArr.length === 2) {
        minutes = timeArr[0];
        seconds = timeArr[1];
      } else if (timeArr.length === 3) {
        hours = timeArr[0];
        minutes = timeArr[1];
        seconds = timeArr[2];
      }
      minutes = Math.min(Math.max(minutes, 0), 59);
      seconds = Math.min(Math.max(seconds, 0), 59);
      hours = Math.max(hours, 0);
      return hours * 3600 + minutes * 60 + seconds;
    },
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const totalSeconds = Math.floor(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const sec = Math.floor(totalSeconds % 60);
      return `${hours}:${minutes.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
    // 新增：精准过滤所有 Emoji 字符
    removeAllEmoji(str) {
      // 覆盖所有常见 Emoji （彩色爱心、符号等），包含 Unicode 扩展区
      const emojiRegex = /[\u{1F300}-\u{1F5FF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{2B5F}\u{2300}-\u{23FF}\u{1F900}-\u{1F9FF}\u{1F1E0}-\u{1F1FF}]/gu;

      return str.replace(emojiRegex, '').trim() .replace(/[#]+/g, '').replace(/^\s*\d+\.\s*/,'');          // 井号、星号、各种横线、箭头;

    },
    handleParse() {
      if (!this.parseText.trim()) {
        this.parseTips = '❌ 请粘贴需要解析的文本内容！';
        return;
      }
      const lines = this.parseText.trim().split('\n').filter(line => line.trim());
      const newTrackList = [];

      // 核心：匹配行尾的时间戳（格式固定，零误差）
      const timeReg = /\s+(\d{1,3}:\d{1,2})\s*$/;

      lines.forEach((line, index) => {
        const timeMatch = line.match(timeReg);
        if (!timeMatch) return;

        // 步骤1：提取并处理时间戳
        const trackTime = timeMatch[1].trim();
        const filterTime = this.filterDurationInput(trackTime);
        const sec = this.timeToSeconds(filterTime);
        const formatTime = this.secondsToTime(sec);

        // 步骤2：删除时间戳，得到 Emoji + 歌名 的原始字符串
        const restStr = line.replace(timeReg, '').trim();

        // 步骤3：调用工具函数，彻底过滤所有 Emoji，只保留歌名
        const trackName = this.removeAllEmoji(restStr) || `未知曲目${index + 1}`;

        newTrackList.push({
          name: trackName,
          sec: sec,
          duration: formatTime,
          playDuration: '0:00:00',
          score: 0
        });
      });

      if (newTrackList.length === 0) {
        this.parseTips = '❌ 未解析到有效曲目数据，请检查文本格式！';
      } else {
        this.parseTips = `✅ 解析成功！共提取到 ${newTrackList.length} 首曲目，已自动填充！`;
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
  padding: 0 6px;
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