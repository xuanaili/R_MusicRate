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
        <h4>音频文件处理</h4>
        <button class="unlock-parse-close-btn" @click="handleClose">×</button>
      </div>
      <div class="unlock-parse-content">
        <!-- 步骤导航 -->
        <div class="step-nav">
          <div :class="{active: currentStep === 1}">1. 选择文件</div>
          <div :class="{active: currentStep === 2}">2. 转换音频</div>
          <div :class="{active: currentStep === 3}">3. 调整顺序</div>
          <div :class="{active: currentStep === 4}">4. 解析音频</div>
        </div>

        <!-- 步骤1：选择文件 -->
        <div v-if="currentStep === 1" class="step-content">
          <!-- 切换处理模式 -->
          <div class="mode-selector">
            <button
              :class="{active: currentMode === 'normal'}"
              @click="currentMode = 'normal'">
              常规音频解析
            </button>
            <button
              :class="{active: currentMode === 'kgg'}"
              @click="currentMode = 'kgg'">
              加密音频处理
            </button>
          </div>

          <!-- 批量上传文件 -->
          <div class="upload-area"
               @drop="handleDrop"
               @dragover="handleDragOver"
               @click="chooseFiles">
    <span v-if="!fileList.length">
      {{ currentMode === 'kgg' ? '拖拽NCM/KGG文件到这里，或点击上传' : '拖拽音频文件到这里，或点击批量上传（支持MP3/OGG/FLAC/NCM/KGG等）' }}
    </span>
            <div v-else class="file-list">
              <div v-for="(file, index) in fileList" :key="index" class="file-item">
                {{ file.name }}
                <button @click="removeFile(index)" class="remove-file-btn">×</button>
              </div>
            </div>
          </div>

          <!-- 修改文件输入的accept属性 -->
          <input
            type="file"
            ref="fileInput"
            :accept="currentMode === 'kgg' ? '.kgg,.ncm' : '.mp3,.ogg,.flac,.ncm,.kgg,.kwm'"
            multiple
            style="display: none"
            @change="handleFileChange">

          <!-- 状态提示 -->
          <div class="parse-status">{{ parseStatus }}</div>

          <!-- 下一步按钮 -->
          <button
            class="unlock-parse-btn"
            @click="gotoNextStep"
            :disabled="!fileList.length || isUploading">
            {{ currentMode === 'kgg' ? '开始转换加密音频' : '直接解析音频文件' }}
          </button>
        </div>

        <!-- 步骤2：转换加密音频（KGG/NCM） -->
        <div v-if="currentStep === 2" class="step-content">
          <div class="conversion-status">
            <div v-if="isConverting" class="loading">
              <span>正在转换{{ convertFileType }}文件...</span>
              <div class="spinner"></div>
            </div>
            <div v-else-if="convertResult.code === 200" class="success">
              ✅ 成功转换 {{ convertResult.data.mp3_files.length }} 个文件
            </div>
            <div v-else-if="convertResult.code" class="error">
              ❌ {{ convertResult.msg }}
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="step-buttons">
            <button class="prev-btn" @click="gotoPrevStep">返回</button>
            <button
                class="next-btn"
                @click="gotoNextStep"
                :disabled="!convertResult.code || convertResult.code !== 200">
              进入排序环节
            </button>
          </div>
        </div>

        <!-- 步骤3：拖拽排序 -->
        <div v-if="currentStep === 3" class="step-content">
          <div class="sort-title">
            <h5>拖拽调整音频顺序（按专辑播放顺序排列）</h5>
            <p class="tip">拖动文件到指定位置，调整完成后点击解析按钮</p>
          </div>

          <!-- 拖拽排序区域 -->
          <div class="sortable-list">
            <div
                v-for="(file, index) in sortedMp3Files"
                :key="file.filename + index"
                class="sortable-item"
                :style="{opacity: isDragging && draggedIndex === index ? 0.5 : 1}"
                draggable="true"
                @dragstart="handleDragStart(index)"
                @dragover="handleDragOverSort($event)"
                @drop="handleDropSort(index)"
                @dragend="handleDragEnd">
              <div class="item-handle">☰</div>
              <div class="item-info">
                <div class="item-name">{{ file.metadata.title || file.filename }}</div>
                <div class="item-artist">{{ file.metadata.artist }}</div>
              </div>
              <div class="item-order">{{ index + 1 }}</div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="step-buttons">
            <button class="prev-btn" @click="gotoPrevStep">返回</button>
            <button
                class="next-btn"
                @click="parseSortedFiles"
                :disabled="isUploading || sortedMp3Files.length === 0">
              {{ isUploading ? '解析中...' : '解析排序后的音频' }}
            </button>
          </div>
        </div>

        <!-- 步骤4：解析完成 -->
        <div v-if="currentStep === 4" class="step-content">
          <div class="parse-result">
            <div v-if="parseResult.code === 200" class="success">
              <h5>✅ 解析成功！</h5>
              <p>共识别 {{ parseResult.data.songs.length }} 首曲目</p>
              <p>专辑：{{ parseResult.data.album_name }}</p>
              <p>歌手：{{ parseResult.data.album_singer }}</p>
            </div>
            <div v-else-if="parseResult.code" class="error">
              <h5>❌ 解析失败</h5>
              <p>{{ parseResult.msg }}</p>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="step-buttons">
            <button class="prev-btn" @click="gotoPrevStep">返回调整</button>
            <button class="finish-btn" @click="handleFinish">完成</button>
          </div>
        </div>
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
      // 基础状态
      fileList: [],        // 上传的原始文件列表
      parseStatus: '',     // 状态提示
      isUploading: false,  // 是否正在处理

      // 模式和步骤
      currentMode: 'normal', // normal:常规解析, kgg:加密音频处理(KGG/NCM)
      currentStep: 1,       // 1:选择文件 2:转换音频 3:调整顺序 4:解析完成

      // 转换结果
      isConverting: false,
      convertResult: {},    // 转换结果
      convertFileType: '',  // 当前转换的文件类型（KGG/NCM）
      sortedMp3Files: [],   // 排序后的MP3文件

      // 拖拽排序
      isDragging: false,
      draggedIndex: -1,

      // 解析结果
      parseResult: {},      // 最终解析结果

      allowedExts: {
        kgg: '.kgg',
        ncm: '.ncm',
        normal: '.mp3,.ogg,.flac,.ncm,.kgg,.kwm'
      }
    }
  },
  watch: {
    visible(newVal) {
      if (newVal) {
        this.resetState();
      }
    },
    convertResult(newVal) {
      // 转换完成后初始化排序列表
      if (newVal.code === 200 && newVal.data && newVal.data.mp3_files) {
        this.sortedMp3Files = [...newVal.data.mp3_files];
      }
    }
  },
  methods: {
    // 重置状态
    resetState() {
      this.fileList = [];
      this.parseStatus = '';
      this.isUploading = false;
      this.currentMode = 'normal';
      this.currentStep = 1;
      this.isConverting = false;
      this.convertResult = {};
      this.convertFileType = '';
      this.sortedMp3Files = [];
      this.isDragging = false;
      this.draggedIndex = -1;
      this.parseResult = {};
    },

    // 关闭侧边栏
    handleClose() {
      this.$emit('close');
    },

    // 完成处理
    handleFinish() {
      if (this.parseResult.code === 200) {
        this.$emit('parse-success', this.parseResult.data);
      }
      this.handleClose();
    },

    // 步骤导航
    gotoNextStep() {
      if (this.currentStep === 1) {
        if (this.currentMode === 'kgg') {
          // 加密音频模式：先转换（自动判断KGG/NCM）
          this.convertEncryptedFiles();
        } else {
          // 常规模式：直接解析
          this.uploadAndParseNormal();
        }
      } else if (this.currentStep === 2) {
        this.currentStep = 3;
      } else if (this.currentStep === 3) {
        // 解析完成后自动到步骤4
      } else if (this.currentStep === 4) {
        // 完成
      }
    },

    gotoPrevStep() {
      if (this.currentStep > 1) {
        this.currentStep--;
      }
    },

    // 拖拽相关处理（文件上传）
    handleDragOver(e) {
      e.preventDefault();
    },

    // 修改handleDrop方法
    handleDrop(e) {
      e.preventDefault();

      // 根据模式筛选文件
      let files = [];
      if (this.currentMode === 'kgg') {
        // 加密音频模式（KGG/NCM）
        files = Array.from(e.dataTransfer.files).filter(file =>
            file.name.endsWith('.kgg') || file.name.endsWith('.ncm')
        );
      } else {
        // 常规模式接受多种音频格式
        const audioTypes = ['audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/wav', 'audio/mp4', 'audio/x-m4a'];
        files = Array.from(e.dataTransfer.files).filter(file =>
            audioTypes.includes(file.type) ||
            ['.mp3', '.ogg', '.flac', '.ncm', '.kgg', '.kwm'].some(ext => file.name.endsWith(ext))
        );
      }

      if (files.length) {
        this.fileList = files;
        this.parseStatus = `已选择 ${files.length} 个文件`;
      } else {
        this.parseStatus = this.currentMode === 'kgg'
            ? '❌ 请选择有效的NCM/KGG文件'
            : '❌ 请选择有效的音频文件';
      }
    },

    // 选择文件
    chooseFiles() {
      this.$refs.fileInput.click();
    },

    // 修改chooseFiles相关的文件选择器
    handleFileChange(e) {
      const files = Array.from(e.target.files);
      if (files.length) {
        this.fileList = files;
        this.parseStatus = `已选择 ${files.length} 个文件`;
      } else {
        this.parseStatus = this.currentMode === 'kgg'
            ? '❌ 请选择有效的NCM/KGG文件'
            : '❌ 请选择有效的音频文件';
      }
      e.target.value = '';
    },

    // 移除单个文件
    removeFile(index) {
      this.fileList.splice(index, 1);
      if (!this.fileList.length) {
        this.parseStatus = '';
      } else {
        this.parseStatus = `已选择 ${this.fileList.length} 个文件`;
      }
    },

    // ========== 加密音频转换逻辑（支持KGG/NCM） ==========
    async convertEncryptedFiles() {
      // 判断文件类型（统一处理KGG/NCM）
      const fileExts = this.fileList.map(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        return ext === 'kgg' || ext === 'ncm' ? ext : '';
      });

      // 检查是否混合了不同类型
      const hasKgg = fileExts.includes('kgg');
      const hasNcm = fileExts.includes('ncm');

      if (hasKgg && hasNcm) {
        this.parseStatus = '❌ 暂不支持同时上传KGG和NCM文件，请分开上传';
        return;
      }

      if (!hasKgg && !hasNcm) {
        this.parseStatus = '❌ 请选择有效的KGG或NCM文件';
        return;
      }

      // 设置当前转换类型
      this.convertFileType = hasKgg ? 'KGG' : 'NCM';
      this.isConverting = true;
      this.parseStatus = `正在转换${this.convertFileType}文件...`;

      try {
        // 创建FormData对象
        const formData = new FormData();
        const formKey = hasKgg ? 'kgg_files' : 'ncm_files';
        this.fileList.forEach(file => {
          formData.append(formKey, file);
        });

        // 选择对应的转换接口
        const apiUrl = hasKgg
            ? '/api/audio/unlock/convert-kgg-only'
            : '/api/audio/unlock/convert-ncm-only';

        // 调用转换接口
        const response = await this.$axios.post(apiUrl, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
            this.parseStatus = `上传中：${percentCompleted}%`;
          },
          timeout: 600000
        });

        this.convertResult = response.data;
        this.currentStep = 2; // 进入转换结果步骤

      } catch (error) {
        console.error(`${this.convertFileType}转换失败:`, error);
        this.convertResult = {
          code: 500,
          msg: error.message || `${this.convertFileType}转换失败，请重试`
        };
      } finally {
        this.isConverting = false;
      }
    },

    // ========== 常规音频解析 ==========
    async uploadAndParseNormal() {
      this.isUploading = true;
      this.parseStatus = '正在上传文件并解析...';

      try {
        // 创建FormData对象
        const formData = new FormData();
        this.fileList.forEach(file => {
          formData.append('audio_files', file);
        });

        // 调用常规解析接口
        const response = await this.$axios.post('/api/audio/unlock/parse', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
            this.parseStatus = `上传中：${percentCompleted}%`;
          },
          timeout: 600000
        });

        this.parseResult = response.data;
        this.currentStep = 4; // 直接到解析完成步骤

      } catch (error) {
        console.error('音频解析失败:', error);
        this.parseResult = {
          code: 500,
          msg: error.message || '解析失败，请重试'
        };
      } finally {
        this.isUploading = false;
      }
    },

    // ========== 拖拽排序逻辑 ==========
    handleDragStart(index) {
      this.isDragging = true;
      this.draggedIndex = index;
      // 设置拖拽数据
      event.dataTransfer.setData('text/plain', index);
      event.dataTransfer.effectAllowed = 'move';
    },

    handleDragOverSort(e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    },

    handleDropSort(targetIndex) {
      if (this.draggedIndex !== targetIndex && this.draggedIndex !== -1) {
        // 移动数组元素
        const draggedItem = this.sortedMp3Files[this.draggedIndex];
        this.sortedMp3Files.splice(this.draggedIndex, 1);
        this.sortedMp3Files.splice(targetIndex, 0, draggedItem);
      }
    },

    handleDragEnd() {
      this.isDragging = false;
      this.draggedIndex = -1;
    },

    // ========== 解析排序后的MP3 ==========
    async parseSortedFiles() {
      this.isUploading = true;

      try {
        // 调用解析接口 - 显式设置Content-Type
        const response = await this.$axios.post(
            '/api/audio/unlock/parse-sorted-mp3',
            {
              sorted_mp3_files: this.sortedMp3Files
            },
            {
              headers: {
                'Content-Type': 'application/json'  // 关键：添加这个请求头
              },
              timeout: 600000
            }
        );

        this.parseResult = response.data;
        this.currentStep = 4; // 进入解析完成步骤

      } catch (error) {
        console.error('排序MP3解析失败:', error);
        this.parseResult = {
          code: 500,
          msg: error.message || '解析失败，请重试'
        };
      } finally {
        this.isUploading = false;
      }
    }
  }
}
</script>

<style scoped>
/* 基础样式 */
.unlock-parse-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.2);
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
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
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
  overflow-y: auto;
}

/* 步骤导航 */
.step-nav {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.step-nav > div {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.step-nav > div.active {
  background: v-bind(mainColorDark);
  color: white;
  font-weight: bold;
}

/* 步骤内容 */
.step-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 模式选择器 */
.mode-selector {
  display: flex;
  gap: 10px;
}

.mode-selector button {
  flex: 1;
  padding: 8px 0;
  border: 1px solid v-bind(mainColorDark);
  background: transparent;
  color: v-bind(mainColorDark);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-selector button.active {
  background: v-bind(mainColorDark);
  color: white;
}

.mode-selector button:hover:not(.active) {
  border-color: v-bind(mainColorDarkDouble);
  color: v-bind(mainColorDarkDouble);
}

/* 上传区域 */
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
  min-height: 200px;
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

/* 状态提示 */
.parse-status, .conversion-status {
  height: 20px;
  line-height: 20px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: v-bind(mainColorDark);
}

.conversion-status {
  height: auto;
  padding: 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid v-bind(mainColorDark);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.success {
  color: #2f9465;
}

.error {
  color: #dc2626;
}

/* 排序区域 */
.sort-title {
  text-align: center;
}

.sort-title h5 {
  margin: 0;
  color: v-bind(mainColorDarkDouble);
}

.sort-title .tip {
  font-size: 12px;
  color: #666;
  margin: 5px 0 0 0;
}

.sortable-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 300px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.sortable-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  cursor: grab;
  transition: all 0.2s;
}

.sortable-item:hover {
  background: rgba(255, 255, 255, 0.5);
}

.item-handle {
  margin-right: 10px;
  color: #999;
  cursor: grab;
}

.item-info {
  flex: 1;
}

.item-name {
  font-weight: 500;
}

.item-artist {
  font-size: 12px;
  color: #666;
}

.item-order {
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  background: v-bind(mainColorDark);
  color: white;
  border-radius: 50%;
  font-size: 12px;
}

/* 按钮样式 */
.unlock-parse-btn, .prev-btn, .next-btn, .finish-btn {
  padding: 10px 0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}

.unlock-parse-btn {
  background: v-bind(mainColorDark);
  color: #fff;
}

.step-buttons {
  display: flex;
  gap: 10px;
}

.prev-btn {
  flex: 1;
  background: #999;
  color: white;
}

.next-btn, .finish-btn {
  flex: 1;
  background: v-bind(mainColorDark);
  color: white;
}

.finish-btn {
  background: v-bind(mainColorDarkDouble);
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 解析结果 */
.parse-result {
  text-align: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.parse-result h5 {
  margin: 0 0 10px 0;
}

.parse-result p {
  margin: 5px 0;
  font-size: 14px;
}
</style>