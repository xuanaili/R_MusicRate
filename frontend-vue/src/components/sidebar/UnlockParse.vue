<template>
  <div class="unlock-parse-wrapper">
    <!-- 遮罩层 -->
    <div
      v-show="visible"
      class="unlock-parse-mask"
      @click="handleClose"
    />

    <!-- 侧边栏主体 -->
    <div v-show="visible" class="unlock-parse-sidebar">
      <div class="unlock-parse-header">
        <h4>音频文件自动解析</h4>
        <button class="unlock-parse-close-btn" @click="handleClose">×</button>
      </div>
      <div class="unlock-parse-content">
        <!-- 批量上传音频文件（支持多种格式） -->
        <div class="upload-area"
             @drop="handleDrop"
             @dragover="handleDragOver"
             @click="chooseFiles">
          <span v-if="!fileList.length">拖拽音频文件到这里，或点击批量上传（支持MP3/OGG/FLAC等）</span>
          <div v-else class="file-list">
            <div v-for="(file, index) in fileList" :key="index" class="file-item">
              {{ file.name }}
              <button @click="removeFile(index)" class="remove-file-btn">×</button>
            </div>
          </div>
        </div>

        <input
          type="file"
          ref="fileInput"
          accept=".mp3,.ogg,.flac,.ncm,.kgg,.kwm"
          multiple
          style="display: none"
          @change="handleFileChange">

        <!-- 解析进度/状态提示 -->
        <div class="parse-status">{{ parseStatus }}</div>

        <!-- 解析按钮 -->
        <button
          class="unlock-parse-btn"
          @click="uploadAndParse"
          :disabled="!fileList.length || isUploading">
          {{ isUploading ? '上传解析中...' : '✅ 上传并自动解析音频信息' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UnlockParse',
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
      fileList: [],        // 上传的音频文件列表
      parseStatus: '',     // 解析状态提示
      isUploading: false   // 是否正在上传/解析
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.resetState();
      }
    }
  },
  methods: {
    // 重置状态
    resetState() {
      this.fileList = [];
      this.parseStatus = '';
      this.isUploading = false;
    },

    // 关闭侧边栏
    handleClose() {
      this.$emit('close');
    },

    // 拖拽相关处理
    handleDragOver(e) {
      e.preventDefault();
    },

    handleDrop(e) {
      e.preventDefault();
      // 支持更多音频格式
      const audioTypes = ['audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/wav', 'audio/mp4', 'audio/x-m4a'];
      const files = Array.from(e.dataTransfer.files).filter(file =>
        audioTypes.includes(file.type) ||
        ['.mp3', '.ogg', '.flac', '.ncm', '.kgg', '.kwm'].some(ext => file.name.endsWith(ext))
      );

      if (files.length) {
        this.fileList = files;
        this.parseStatus = `已选择 ${files.length} 个音频文件`;
      } else {
        this.parseStatus = '❌ 请选择有效的音频文件（MP3/OGG/FLAC/WAV/M4A/MP4）';
      }
    },

    // 选择文件
    chooseFiles() {
      this.$refs.fileInput.click();
    },

    handleFileChange(e) {
      const files = Array.from(e.target.files);
      if (files.length) {
        this.fileList = files;
        this.parseStatus = `已选择 ${files.length} 个音频文件`;
      } else {
        this.parseStatus = '❌ 请选择有效的音频文件';
      }
      // 清空input值，以便重新选择相同文件
      e.target.value = '';
    },

    // 移除单个文件
    removeFile(index) {
      this.fileList.splice(index, 1);
      if (!this.fileList.length) {
        this.parseStatus = '';
      } else {
        this.parseStatus = `已选择 ${this.fileList.length} 个音频文件`;
      }
    },

    // 核心：上传文件到后端并解析
    async uploadAndParse() {
      if (!this.fileList.length) {
        this.parseStatus = '❌ 请先选择音频文件';
        return;
      }

      this.isUploading = true;
      this.parseStatus = '正在上传文件并解析...';

      try {
        // 创建FormData对象
        const formData = new FormData();
        // 添加所有文件
        this.fileList.forEach((file, ) => {
          formData.append('audio_files', file);
        });

        // 调用后端解析接口
        const response = await this.$axios.post('/api/audio/unlock/parse', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          // 上传进度显示
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
            this.parseStatus = `上传中：${percentCompleted}%`;
          },
          timeout: 60000 // 延长超时时间（音频文件可能较大）
        });

        if (response.data.code === 200) {
          const parseResult = response.data.data;
          this.parseStatus = `✅ 解析成功！共识别 ${parseResult.songs.length} 首曲目`;
          // 通知父组件解析结果
          this.$emit('parse-success', parseResult);
        } else {
          this.parseStatus = `❌ 解析失败：${response.data.msg}`;
        }

      } catch (error) {
        console.error('音频解析失败:', error);
        this.parseStatus = `❌ 解析失败：${error.message || '服务器错误，请稍后重试'}`;
      } finally {
        this.isUploading = false;
      }
    }
  }
}
</script>

<style scoped>
.unlock-parse-mask {
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

.unlock-parse-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 560px;
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

.unlock-parse-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 2px solid v-bind(mainColorDark);
  margin-bottom: 15px;
}

.unlock-parse-header h4 {
  margin: 0;
  font-size: 16px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
}

.unlock-parse-close-btn {
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

.unlock-parse-close-btn:hover {
  color: #dc2626;
  transform: scale(1.1);
  background: transparent;
}

.unlock-parse-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.upload-area {
  flex: 1;
  border: 2px dashed v-bind(mainColorDark);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.2);
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: v-bind(mainColorDarkDouble);
  background: rgba(255, 255, 255, 0.3);
}

.file-list {
  width: 100%;
  max-height: 300px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  margin-bottom: 5px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.remove-file-btn {
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  line-height: 20px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.parse-status {
  height: 20px;
  line-height: 20px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: v-bind(mainColorDark);
}

.unlock-parse-btn {
  background: v-bind(mainColorDark);
  color: #fff;
  border: none;
  padding: 10px 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}

.unlock-parse-btn:disabled {
  background: #999;
  cursor: not-allowed;
  opacity: 0.7;
}

.unlock-parse-btn:hover:not(:disabled) {
  background-color: v-bind(mainColorDarkDouble) !important;
  opacity: 0.95;
}
</style>