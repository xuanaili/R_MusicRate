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
          <!-- 批量上传文件（移除模式切换，统一处理所有音频） -->
          <div class="upload-area"
               @drop="handleDrop"
               @dragover="handleDragOver"
               @click="chooseFiles">
    <span v-if="!fileList.length">
      拖拽音频文件到这里，或点击上传（支持MP3/OGG/FLAC/NCM/KGG等）
    </span>
            <div v-else class="file-list">
              <div v-for="(file, index) in fileList" :key="index" class="file-item">
                {{ file.name }}
                <button @click="removeFile(index)" class="remove-file-btn">×</button>
              </div>
            </div>
          </div>

          <!-- 文件输入（统一支持所有音频格式） -->
          <input
            type="file"
            ref="fileInput"
            accept=".mp3,.ogg,.flac,.ncm,.kgg,.kwm"
            multiple
            style="display: none"
            @change="handleFileChange">

          <!-- 状态提示 -->
          <div class="parse-status">{{ parseStatus }}</div>

          <!-- 下一步按钮（统一为"开始处理音频"） -->
          <button
            class="unlock-parse-btn"
            @click="gotoNextStep"
            :disabled="!fileList.length || isUploading">
            开始处理音频
          </button>
        </div>

        <!-- 步骤2：转换音频（统一处理所有格式：MP3/OGG/FLAC/NCM/KGG） -->
        <div v-if="currentStep === 2" class="step-content">
          <div class="conversion-status">
            <div v-if="isConverting" class="loading">
              <span>正在转换{{ convertFileType }}文件... ({{ convertedFileCount }}/{{ totalFileCount }})</span>
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

      // 步骤控制
      currentStep: 1,       // 1:选择文件 2:转换音频 3:调整顺序 4:解析完成

      // 转换结果
      isConverting: false,
      convertResult: {},    // 转换结果
      convertFileType: '',  // 当前转换的文件类型（MP3/NCM/KGG等）
      sortedMp3Files: [],   // 排序后的MP3文件
      totalFileCount: 0,    // 新增：总文件数
      convertedFileCount: 0,// 新增：已转换文件数

      // 拖拽排序
      isDragging: false,
      draggedIndex: -1,

      // 解析结果
      parseResult: {}       // 最终解析结果
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
      this.currentStep = 1;
      this.isConverting = false;
      this.convertResult = {};
      this.convertFileType = '';
      this.sortedMp3Files = [];
      this.isDragging = false;
      this.draggedIndex = -1;
      this.parseResult = {};
      this.totalFileCount = 0;    // 重置
      this.convertedFileCount = 0;// 重置
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
        // 统一走转换流程（MP3/NCM/KGG都调用对应的转换接口）
        this.convertAudioFiles();
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

    // 统一处理文件拖拽上传
    handleDrop(e) {
      e.preventDefault();

      // 支持所有音频格式
      const audioExts = ['.mp3', '.ogg', '.flac', '.ncm', '.kgg', '.kwm'];
      const files = Array.from(e.dataTransfer.files).filter(file =>
        audioExts.some(ext => file.name.endsWith(ext))
      );


        // 新增：打印上传的原始文件名（看控制台）
  console.log("前端获取的原始文件列表：", files.map(f => ({
    name: f.name,
    size: f.size,
    type: f.type
  })));


      if (files.length) {
        this.fileList = files;
        this.parseStatus = `已选择 ${files.length} 个文件`;
      } else {
        this.parseStatus = '❌ 请选择有效的音频文件（MP3/OGG/FLAC/NCM/KGG等）';
      }
    },

    // 选择文件
    chooseFiles() {
      this.$refs.fileInput.click();
    },

    // 处理文件选择
    handleFileChange(e) {
      const files = Array.from(e.target.files);
      if (files.length) {
        this.fileList = files;
        this.parseStatus = `已选择 ${files.length} 个文件`;
      } else {
        this.parseStatus = '❌ 请选择有效的音频文件（MP3/OGG/FLAC/NCM/KGG等）';
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

    // ========== 统一音频转换逻辑（整合MP3/NCM/KGG） ==========
    async convertAudioFiles() {
      // 按文件类型分组
      const fileGroups = {
        kgg: [],
        ncm: [],
        mp3: []
      };

      // 分类文件
      this.fileList.forEach(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext === 'kgg') {
          fileGroups.kgg.push(file);
        } else if (ext === 'ncm') {
          fileGroups.ncm.push(file);
        } else if (['mp3', 'ogg', 'flac', 'wav', 'm4a', 'aac'].includes(ext)) {
          fileGroups.mp3.push(file);
        }
      });

      // 统计总数
      this.totalFileCount = this.fileList.length;
      this.convertedFileCount = 0;

      // 没有有效文件
      if (this.totalFileCount === 0) {
        this.parseStatus = '❌ 请选择有效的音频文件';
        return;
      }

      this.isConverting = true;
      // 存储所有转换后的MP3文件
      let allMp3Files = [];

      try {
        // 依次处理不同类型的文件
        // 1. 处理KGG文件
        if (fileGroups.kgg.length > 0) {
          this.convertFileType = 'KGG';
          this.parseStatus = `正在转换${this.convertFileType}文件...`;
          const kggResult = await this.convertFilesByType('kgg', fileGroups.kgg);
          if (kggResult.code === 200) {
            allMp3Files = [...allMp3Files, ...kggResult.data.mp3_files];
            this.convertedFileCount += fileGroups.kgg.length;
          } else {
            throw new Error(kggResult.msg || 'KGG文件转换失败');
          }
        }

        // 2. 处理NCM文件
        if (fileGroups.ncm.length > 0) {
          this.convertFileType = 'NCM';
          this.parseStatus = `正在转换${this.convertFileType}文件...`;
          const ncmResult = await this.convertFilesByType('ncm', fileGroups.ncm);
          if (ncmResult.code === 200) {
            allMp3Files = [...allMp3Files, ...ncmResult.data.mp3_files];
            this.convertedFileCount += fileGroups.ncm.length;
          } else {
            throw new Error(ncmResult.msg || 'NCM文件转换失败');
          }
        }

        // 3. 处理MP3/其他音频文件
        if (fileGroups.mp3.length > 0) {
          this.convertFileType = 'MP3';
          this.parseStatus = `正在转换${this.convertFileType}文件...`;
          const mp3Result = await this.convertFilesByType('mp3', fileGroups.mp3);
          if (mp3Result.code === 200) {
            allMp3Files = [...allMp3Files, ...mp3Result.data.mp3_files];
            this.convertedFileCount += fileGroups.mp3.length;
          } else {
            throw new Error(mp3Result.msg || 'MP3文件转换失败');
          }
        }

        // 整合所有转换结果
        this.convertResult = {
          code: 200,
          msg: '所有文件转换成功',
          data: {
            mp3_files: allMp3Files
          }
        };
        this.currentStep = 2; // 进入转换结果步骤

      } catch (error) {
        console.error('文件转换失败:', error);
        this.convertResult = {
          code: 500,
          msg: error.message || '文件转换失败，请重试'
        };
      } finally {
        this.isConverting = false;
      }
    },

    // 按类型转换文件的通用方法
    async convertFilesByType(type, files) {
      try {
        // 创建FormData对象
        const formData = new FormData();
        // 根据文件类型选择对应的formKey和接口
        let formKey, apiUrl;
        if (type === 'kgg') {
          formKey = 'kgg_files';
          apiUrl = '/api/audio/unlock/convert-kgg-only';
        } else if (type === 'ncm') {
          formKey = 'ncm_files';
          apiUrl = '/api/audio/unlock/convert-ncm-only';
        } else {
          formKey = 'audio_files';
          apiUrl = '/api/audio/unlock/convert-mp3-only'; // 新的MP3转换接口
        }

        // 添加文件到FormData
        files.forEach(file => {
          formData.append(formKey, file);
        });

        // 调用对应的转换接口
        const response = await this.$axios.post(apiUrl, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
            this.parseStatus = `上传${this.convertFileType}文件中：${percentCompleted}%`;
          },
          timeout: 600000
        });

        return response.data;
      } catch (error) {
        throw new Error(error.message || `${type.toUpperCase()}文件转换失败`);
      }
    },

    // ========== 拖拽排序逻辑 ==========
    handleDragStart(index) {
      this.isDragging = true;
      this.draggedIndex = index;
      event.dataTransfer.setData('text/plain', index);
      event.dataTransfer.effectAllowed = 'move';
    },

    handleDragOverSort(e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    },

    handleDropSort(targetIndex) {
      if (this.draggedIndex !== targetIndex && this.draggedIndex !== -1) {
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
        // 调用解析接口
        const response = await this.$axios.post(
            '/api/audio/unlock/parse-sorted-mp3',
            {
              sorted_mp3_files: this.sortedMp3Files
            },
            {
              headers: {
                'Content-Type': 'application/json'
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