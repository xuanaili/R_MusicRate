<template>
  <div class="audio-upload-sidebar" :class="{show: visible}">
    <!-- 侧边栏头部 -->
    <div class="sidebar-header">
      <h4>{{ isUpdate ? '更新整轨MP3文件' : '上传整轨MP3文件' }}</h4>
      <button class="close-btn" @click="handleClose">×</button>
    </div>

    <!-- 功能切换标签 -->
    <div class="upload-tab-group">
      <div
        class="upload-tab"
        :class="{active: activeTab === 'single'}"
        @click="activeTab = 'single'"
      >
        单一MP3上传
      </div>
      <div
        class="upload-tab"
        :class="{active: activeTab === 'auto'}"
        @click="activeTab = 'auto'"
      >
        自动解析合并
      </div>
    </div>

    <!-- 1. 单一MP3上传区域 -->
    <div class="upload-content" v-if="activeTab === 'single'">
      <div
        class="upload-area"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <input
          type="file"
          ref="fileInput"
          accept=".mp3"
          class="file-input"
          @change="handleFileChange"
        />
        <div class="upload-tips">
          <p>📂 点击上传 或 拖拽MP3文件到此处</p>
          <p class="tip-text">仅支持 .mp3 格式音频文件</p>
        </div>
      </div>
      <div v-if="fileName" class="file-name">{{ fileName }}</div>
      <div class="upload-status" :class="{success: statusClass === 'success', error: statusClass === 'error'}">
        {{ statusText }}
      </div>
    </div>

    <!-- 2. 自动解析合并区域（复用之前的音频解析逻辑） -->
    <div class="upload-content" v-if="activeTab === 'auto'">
      <div class="auto-parse-tips">
        <p>🎵 上传多个音频文件，自动解析并合并为整轨MP3</p>
        <p class="tip-text">支持批量上传，自动提取专辑信息、封面和时间戳</p>
      </div>

      <!-- 音频文件上传区域 -->
      <div class="audio-files-upload-area">
        <input
          type="file"
          ref="audioFilesInput"
          accept=".mp3,.flac,.wav,.m4a"
          multiple
          class="file-input"
          @change="handleAudioFilesChange"
        />
        <button class="btn-select-files" @click="triggerFileSelect">
          选择音频文件
        </button>

        <!-- 已选择文件列表 -->
        <div class="selected-files-list" v-if="selectedFiles.length > 0">
          <div class="file-item" v-for="(file, index) in selectedFiles" :key="index">
            {{ file.name }}
            <button class="delete-file-btn" @click="removeFile(index)">×</button>
          </div>
        </div>
      </div>

      <!-- 解析按钮 -->
      <button
        class="btn-parse-audio"
        @click="handleAutoParse"
        :disabled="selectedFiles.length === 0"
      >
        开始解析并合并
      </button>

      <!-- 解析状态提示 -->
      <div class="parse-status" :class="{success: parseStatus === 'success', error: parseStatus === 'error'}">
        {{ parseStatusText }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumAudioUpload',
  props: {
    // 是否显示侧边栏
    visible: {
      type: Boolean,
      default: false
    },
    // 是否是更新操作（已有音频）
    isUpdate: {
      type: Boolean,
      default: false
    },
    // 专辑source_pool_id（用于上传）
    sourcePoolId: {
      type: [String, Number],
      required: true
    },
    // 旧的MP3 URL（更新时使用）
    oldMp3Url: {
      type: String,
      default: ''
    },
    // 样式相关
    mainColorDark: {
      type: String,
      default: 'transparent'
    },
    mainColorDarkDouble: {
      type: String,
      default: 'transparent'
    }
  },
  data() {
    return {
      // 激活的标签：single(单一上传) / auto(自动解析)
      activeTab: 'single',
      // 单一上传相关
      fileName: '',
      statusText: '',
      statusClass: '',
      // 自动解析相关
      selectedFiles: [],
      parseStatus: '', // success/error/loading
      parseStatusText: ''
    };
  },
  methods: {
    // 关闭侧边栏
    handleClose() {
      this.resetState();
      this.$emit('close');
    },
    // 重置状态
    resetState() {
      this.fileName = '';
      this.statusText = '';
      this.statusClass = '';
      this.selectedFiles = [];
      this.parseStatus = '';
      this.parseStatusText = '';
      this.activeTab = 'single';
      // 清空文件输入
      if (this.$refs.fileInput) this.$refs.fileInput.value = '';
      if (this.$refs.audioFilesInput) this.$refs.audioFilesInput.value = '';
    },
    // ========== 单一MP3上传逻辑 ==========
    handleFileChange(e) {
      const file = e.target.files[0];
      if (file) {
        this.handleSingleFile(file);
        this.$refs.fileInput.value = '';
      }
    },
    handleDrop(e) {
      const file = e.dataTransfer.files[0];
      if (file) {
        this.handleSingleFile(file);
      }
    },
    async handleSingleFile(file) {
      // 验证文件格式
      if (file.type !== 'audio/mpeg' && !file.name.toLowerCase().endsWith('.mp3')) {
        this.statusText = '❌ 仅支持上传MP3格式！';
        this.statusClass = 'error';
        return;
      }

      // 验证sourcePoolId
      if (!this.sourcePoolId) {
        this.statusText = '❌ 公共专辑ID不存在，无法上传！';
        this.statusClass = 'error';
        return;
      }

      this.fileName = file.name;
      this.statusText = this.isUpdate ? '⏳ 更新中，请稍候...' : '⏳ 上传中，请稍候...';
      this.statusClass = '';

      try {
        const formData = new FormData();
        formData.append('source_pool_id', this.sourcePoolId);
        formData.append('mp3_file', file);
        formData.append('old_mp3_url', this.oldMp3Url || '');

        const res = await this.$axios.post('/api/album/pool/audio/upload', formData);

        if (res.data.code === 200) {
          this.statusText = this.isUpdate ? '✅ 更新成功' : '✅ 上传成功';
          this.statusClass = 'success';
          // 通知父组件上传成功
          this.$emit('upload-success', {
            mp3_url: res.data.data.mp3_url,
            mp3_name: res.data.data.mp3_name,
            mp3_duration: res.data.data.mp3_duration,
            duration_format: res.data.data.duration_format
          });
          // 2秒后关闭
          setTimeout(() => {
            this.handleClose();
          }, 2000);
        } else {
          this.statusText = `❌ ${res.data.msg}`;
          this.statusClass = 'error';
        }
      } catch (err) {
        console.error('音频操作失败：', err);
        this.statusText = '❌ 操作失败，请重试！';
        this.statusClass = 'error';
      }
    },

    // ========== 自动解析合并逻辑 ==========
    triggerFileSelect() {
      this.$refs.audioFilesInput.click();
    },
    handleAudioFilesChange(e) {
      const files = Array.from(e.target.files);
      if (files.length > 0) {
        // 过滤支持的音频格式
        const validFiles = files.filter(file => {
          const ext = file.name.split('.').pop().toLowerCase();
          return ['mp3', 'flac', 'wav', 'm4a'].includes(ext);
        });
        this.selectedFiles = [...this.selectedFiles, ...validFiles];
        this.$refs.audioFilesInput.value = '';
      }
    },
    removeFile(index) {
      this.selectedFiles.splice(index, 1);
    },
    async handleAutoParse() {
      if (this.selectedFiles.length === 0) return;

      this.parseStatus = 'loading';
      this.parseStatusText = '⏳ 正在解析音频并合并，请稍候...';

      try {
        // 构建FormData
        const formData = new FormData();
        formData.append('source_pool_id', this.sourcePoolId);
        // 添加所有音频文件
        this.selectedFiles.forEach((file,) => {
          formData.append('audio_files', file);
        });
        // 添加旧MP3 URL（更新时）
        if (this.oldMp3Url) {
          formData.append('old_mp3_url', this.oldMp3Url);
        }

        // 调用音频解析接口
        const res = await this.$axios.post('/api/audio/unlock/parse', formData);

        if (res.data.code === 200) {
          const parseResult = res.data.data;
          // 调用上传合并后音频的接口
          const uploadRes = await this.$axios.post('/api/album/pool/audio/upload/merged', {
            source_pool_id: this.sourcePoolId,
            mp3_url: parseResult.mp3_url,
            old_mp3_url: this.oldMp3Url || ''
          });

          if (uploadRes.data.code === 200) {
            this.parseStatus = 'success';
            this.parseStatusText = `✅ 解析合并成功！共识别${parseResult.songs.length}首曲目`;
            // 通知父组件上传成功
            this.$emit('upload-success', {
              mp3_url: uploadRes.data.data.mp3_url,
              mp3_name: uploadRes.data.data.mp3_name,
              mp3_duration: parseResult.mp3_duration,
              duration_format: this.formatDuration(parseResult.mp3_duration)
            });
            // 2秒后关闭
            setTimeout(() => {
              this.handleClose();
            }, 2000);
          } else {
            throw new Error(uploadRes.data.msg);
          }
        } else {
          throw new Error(res.data.msg);
        }
      } catch (err) {
        console.error('音频解析合并失败：', err);
        this.parseStatus = 'error';
        this.parseStatusText = `❌ 解析失败：${err.message || '服务器异常'}`;
      }
    },
    // 格式化时长
    formatDuration(seconds) {
      if (!seconds) return '0:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      return `${min}:${sec.toString().padStart(2, '0')}`;
    }
  }
};
</script>

<style scoped>
.audio-upload-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 360px;
  height: 100vh;
  background: white;
  z-index: 9999;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
  padding: 20px;
  box-sizing: border-box;
  overflow-y: auto;
  transform: translateX(100%);
  transition: transform 0.3s ease;
}

.audio-upload-sidebar.show {
  transform: translateX(0);
}

/* 头部样式 */
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.sidebar-header h4 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}

.close-btn:hover {
  color: #f00;
}

/* 标签切换 */
.upload-tab-group {
  display: flex;
  margin-bottom: 20px;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #eee;
}

.upload-tab {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  cursor: pointer;
  background: #f9f9f9;
  font-size: 14px;
  transition: all 0.2s;
}

.upload-tab.active {
  background: v-bind(mainColorDark);
  color: white;
}

/* 上传内容区域 */
.upload-content {
  width: 100%;
}

/* 单一上传区域 */
.upload-area {
  width: 100%;
  height: 180px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  background: #f9f9f9;
  margin-bottom: 20px;
  transition: all 0.2s ease;
}

.upload-area:hover {
  border-color: v-bind(mainColorDark);
  background: rgba(0,0,0,0.02);
}

.file-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-tips {
  text-align: center;
  color: #666;
}

.tip-text {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

.file-name {
  font-size: 14px;
  color: #333;
  margin-bottom: 10px;
  word-break: break-all;
}

.upload-status {
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  text-align: center;
}

.upload-status.success {
  color: #15803d;
  background: #f0fdf4;
}

.upload-status.error {
  color: #dc2626;
  background: #fef2f2;
}

/* 自动解析区域 */
.auto-parse-tips {
  text-align: center;
  margin-bottom: 20px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
}

.audio-files-upload-area {
  margin-bottom: 20px;
}

.btn-select-files {
  width: 100%;
  padding: 10px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 10px;
  transition: all 0.2s;
}

.btn-select-files:hover {
  background: v-bind(mainColorDarkDouble);
}

.selected-files-list {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 4px;
}

.file-item {
  padding: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  font-size: 13px;
}

.delete-file-btn {
  background: #fef2f2;
  color: #dc2626;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-parse-audio {
  width: 100%;
  padding: 12px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-parse-audio:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-parse-audio:hover:not(:disabled) {
  background: v-bind(mainColorDarkDouble);
}

.parse-status {
  margin-top: 15px;
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  text-align: center;
}

.parse-status.success {
  color: #15803d;
  background: #f0fdf4;
}

.parse-status.error {
  color: #dc2626;
  background: #fef2f2;
}
</style>