<template>
  <!-- ✅ 根容器解决Vue2单节点问题 + 层级控制 -->
  <div class="sidebar-root-container">
    <!-- ✅ 左侧侧边栏蒙版 0.5透明度 毛玻璃效果 -->
    <div
      v-show="visible"
      class="sidebar-mask"
      @click="handleMaskClose"
    ></div>

    <!-- ✅ 核心：修改专辑 左侧抽屉式独立侧边栏 (全屏高度) -->
    <div
      class="edit-album-sidebar"
      :class="{show: visible}"
    >
      <div class="sidebar-header">
        <h2>修改公共专辑模板</h2>
        <button class="close-btn" @click="handleClose">×</button>
      </div>
      <div class="sidebar-content">
        <!-- 同步结果提示 -->
        <div v-if="syncResult" class="sync-result">
          <div class="sync-result-title">🔍 修改同步结果</div>
          <div class="sync-result-content">
            {{ syncResult.msg }}
            <span v-if="syncResult.data?.sync_count" class="sync-count">
              （同步更新了 {{ syncResult.data.sync_count }} 条用户数据）
            </span>
          </div>
        </div>

        <!-- 表单区域 -->
        <div class="album-form">
          <!-- 专辑名 -->
          <div class="form-item">
            <label>专辑名：</label>
            <input
                v-model="album.album_name"
                type="text"
                placeholder="请输入专辑名"
                class="form-input"
                required
            >
          </div>

          <!-- 封面图片 -->
          <div class="form-item">
            <label>封面图片：</label>
            <div
                class="upload-area"
                @drop="handleDrop"
                @dragover="handleDragOver"
                @click="chooseFile"
            >
              <span v-if="!album.cover_img">拖拽图片到这里，或点击上传</span>
              <img v-else :src="album.cover_img" class="preview-img" alt="封面预览" loading="lazy">
            </div>
            <input type="file" ref="fileInput" accept="image/*" style="display: none" @change="handleFileChange">
            <input v-model="album.cover_img" type="text" placeholder="可选：输入图片URL" style="margin-top: 10px"
                   class="form-input">
          </div>

          <!-- 歌手 -->
          <div class="form-item">
            <label>歌手：</label>
            <input
                v-model="album.singer"
                type="text"
                placeholder="请输入歌手名"
                class="form-input"
                required
            >
          </div>

          <!-- 发行年份 -->
          <div class="form-item">
            <label>发行年份：</label>
            <input
                v-model="album.release_year"
                type="number"
                placeholder="如：2024"
                class="form-input"
            >
          </div>

          <!-- 专辑类型下拉选择框 -->
          <div class="form-item">
            <label>专辑类型：</label>
            <select v-model="album.duration_type" class="form-input album-type-select">
              <option value="LP">LP - 正式专辑</option>
              <option value="EP">EP - 迷你专辑</option>
              <option value="SIN">SIN - 单曲专辑</option>
              <option value="Mix">Mix - 混音专辑</option>
              <option value="Com">Com - 合集/精选</option>
            </select>
          </div>

          <!-- 专辑简介 -->
          <div class="form-item">
            <label>专辑简介：</label>
            <textarea
                v-model="album.album_intro"
                placeholder="请输入专辑简介（支持长文本、分段、特殊符号）"
                class="album-intro-textarea form-input"
                rows="6"
                spellcheck="false"
            ></textarea>
            <p class="intro-tip">提示：支持分段（按Enter）、特殊符号，内容将完整保存</p>
          </div>

          <!-- 核心：单曲列表 + 时间戳输入框 + 文本解析按钮 -->
          <div class="form-item">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <label>单曲列表：</label>
              <button @click="showParseModal = true" class="btn-add-song" style="padding: 6px 12px; font-size: 12px;">
                📝 文本解析
              </button>
            </div>
            <!-- 循环渲染单曲+时间戳输入框 -->
            <div class="song-item" v-for="(song, index) in album.songs" :key="index">
              <div class="song-input-wrapper" style="display: flex; align-items: center; gap: 10px; flex: 1;">
                <span class="song-index">{{ index + 1 }}.</span>
                <input
                    v-model="song.song_name"
                    type="text"
                    placeholder="请输入单曲名"
                    class="song-input form-input"
                    style="flex: 3;"
                >
                <input
                    v-model="song.track_time"
                    type="text"
                    placeholder="0:00:00"
                    class="song-input form-input"
                    style="flex: 1; text-align: center;"
                    maxlength="8"
                    @input="song.track_time = filterDurationInput(song.track_time)"
                    @blur="formatDurationInput(song, index)"
                >
              </div>
              <button
                  v-if="album.songs.length > 1"
                  @click="removeSong(index)"
                  class="btn-delete-song"
              >
                ×
              </button>
            </div>
            <!-- 添加单曲按钮 -->
            <button @click="addSong" class="btn-add-song">+ 添加单曲</button>
          </div>

          <!-- 同步说明提示 -->
          <div class="sync-tips">
            📌 温馨提示：修改后会自动同步到「开启同步且未自定义修改」的用户专辑，已自定义的用户专辑不会被覆盖。
          </div>

          <!-- 错误提示 -->
          <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>

          <!-- 操作按钮 -->
          <div class="form-actions btn-group">
            <button @click="submitEdit" class="submit-btn btn-submit" :disabled="loading || isUploading">
              <span v-if="loading">保存中...</span>
              <span v-else>保存修改</span>
            </button>
            <button @click="handleClose" class="cancel-btn btn-cancel" :disabled="loading || isUploading">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ✅ 文本解析 右侧独立侧边栏 (和AddAlbum完全一致) -->
    <div v-show="showParseModal" class="parse-sidebar-mask" @click="showParseModal = false"></div>
    <div class="track-parse-sidebar" :class="{show: showParseModal}">
      <TrackParse
        :visible="showParseModal"
        :main-color-dark="mainColorDark"
        :main-color-dark-double="mainColorDarkDouble"
        @close="showParseModal = false"
        @parse-success="handleParseSuccess"
      />
    </div>
  </div>
</template>

<script>
import TrackParse from '@/components/sidebar/TrackParse.vue'

export default {
  name: 'EditPoolAlbum',
  components: { TrackParse },
  // ✅ 新增props 适配侧边栏组件化调用
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    albumId: {
      type: [String, Number],
      required: true
    },
    mainColor: {
      type: String,
      default: 'transparent'
    },
    mainColorDark: {
      type: String,
      default: '#2f9465'
    },
    mainColorDarkDouble: {
      type: String,
      default: '#257d51'
    }
  },
  data() {
    return {
      // 专辑表单
      album: {
        album_name: "",
        cover_img: "",
        singer: "",
        release_year: "",
        duration_type: "LP",
        album_intro: "",
        songs: [{song_name: "", track_time: "0:00:00"}],
        tracks_time: []
      },
      loading: false,
      isUploading: false,
      syncResult: null,
      errorMsg: "",
      showParseModal: false
    }
  },
  watch: {
    // ✅ 监听专辑ID/显隐状态变化，自动加载数据
    visible(newVal) {
      if (newVal && this.albumId) {
        this.getAlbumData()
      }
    },
    albumId(newVal) {
      if (newVal && this.visible) {
        this.getAlbumData()
      }
    }
  },
  methods: {
    // 时间戳处理工具方法
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
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const totalSeconds = Math.floor(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const sec = Math.floor(totalSeconds % 60);
      return `${hours}:${minutes.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      const colonCount = filterVal.split(':').length - 1;
      if (colonCount > 2) filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      return filterVal;
    },
    formatDurationInput(song) {
      song.track_time = this.filterDurationInput(song.track_time);
      const sec = this.timeToSeconds(song.track_time);
      song.track_time = this.secondsToTime(sec);
    },
    // 单曲列表方法
    addSong() {
      this.album.songs.push({song_name: "", track_time: "0:00:00"});
      this.errorMsg = "";
      this.$nextTick(() => {
        const inputs = document.querySelectorAll('.song-input');
        if (inputs.length > 0) {
          inputs[inputs.length - 2].focus();
        }
      });
    },
    removeSong(index) {
      if (this.album.songs.length <= 1) {
        this.errorMsg = "至少保留1首单曲！";
        return;
      }
      this.album.songs.splice(index, 1);
      this.errorMsg = "";
    },
    // 封面上传
    handleDragOver(e) { e.preventDefault(); },
    handleDrop(e) {
      e.preventDefault();
      if (this.isUploading) return;
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) { this.uploadToImgBed(file); }
      else { this.errorMsg = "请拖拽有效的图片文件！"; }
    },
    chooseFile() { this.$refs.fileInput.click(); },
    handleFileChange(e) {
      if (this.isUploading) return;
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        this.uploadToImgBed(file);
        e.target.value = "";
      } else { this.errorMsg = "请选择有效的图片文件！"; }
    },
    async uploadToImgBed(file) {
      this.isUploading = true;
      this.errorMsg = "";
      try {
        const formData = new FormData();
        formData.append('image', file);
        const res = await this.$axios.post('/api/upload_img', formData, {
          headers: {'Authorization': localStorage.getItem('token') || '', 'Content-Type': 'multipart/form-data'},
          timeout: 15000
        });
        if (res.data.code === 200) {
          this.album.cover_img = res.data.data.img_url || res.data.data.url;
        } else {
          this.errorMsg = "图片上传失败：" + res.data.msg;
        }
      } catch (err) {
        console.error("上传失败：", err);
        this.errorMsg = "图片上传失败！检查后端是否启动";
      } finally {
        this.isUploading = false;
      }
    },
    // 加载专辑数据
    getAlbumData() {
      this.loading = true;
      this.$axios({
        url: `/api/album/pool/detail/${this.albumId}`,
        method: 'GET',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200) {
              const data = res.data.data;
              const trackNames = data.tracks && Array.isArray(data.tracks) ? data.tracks : [];
              const trackSecs = data.tracks_time && Array.isArray(data.tracks_time) ? data.tracks_time : [];
              const songs = [];
              if (trackNames.length > 0) {
                trackNames.forEach((name, idx) => {
                  songs.push({
                    song_name: name.trim() || '未知曲目',
                    track_time: this.secondsToTime(trackSecs[idx] || 0)
                  })
                })
              } else {
                songs.push({song_name: "", track_time: "0:00:00"});
              }
              this.album = {
                album_name: data.album_name || "",
                cover_img: data.cover_img || "",
                singer: data.singer || "",
                release_year: data.release_year || "",
                duration_type: data.duration_type || "LP",
                album_intro: data.album_intro || "",
                songs: songs,
                tracks_time: trackSecs
              };
            } else {
              alert('加载专辑数据失败：' + res.data.msg);
              this.handleClose();
            }
          })
          .catch(err => {
            this.loading = false;
            console.error('加载专辑数据失败：', err);
            alert('加载数据失败！');
            this.handleClose();
          });
    },
    // 解析成功回调
    handleParseSuccess(parseSongs) {
      this.showParseModal = false;
      this.errorMsg = '';
      const formatSongs = parseSongs.map(item => ({
        song_name: item.name ? item.name.trim() : '',
        track_time: item.duration ? item.duration : '0:00:00'
      }));
      this.album.songs = formatSongs;
      alert(`解析成功！共识别到 ${formatSongs.length} 首单曲，已自动填充 ✔️`);
    },
    // 提交修改
    submitEdit() {
      this.errorMsg = "";
      if (!this.album.album_name.trim()) {
        this.errorMsg = "专辑名不能为空！";
        return;
      }
      if (!this.album.singer.trim()) {
        this.errorMsg = "歌手名不能为空！";
        return;
      }
      if (this.album.release_year && isNaN(this.album.release_year)) {
        this.errorMsg = "请输入有效的发行年份！";
        return;
      }
      const validSongs = this.album.songs.map(song => ({
        name: song.song_name.trim(),
        time: song.track_time || '0:00:00'
      })).filter(item => item.name);
      if (validSongs.length === 0) {
        this.errorMsg = "至少填写1首单曲名！";
        return;
      }
      const trackNames = validSongs.map(item => item.name);
      const trackSecs = validSongs.map(item => this.timeToSeconds(item.time));
      const submitData = {
        album_name: this.album.album_name.trim(),
        cover_img: this.album.cover_img.trim(),
        singer: this.album.singer.trim(),
        release_year: this.album.release_year ? Number(this.album.release_year) : '',
        duration_type: this.album.duration_type,
        album_intro: this.album.album_intro.trim(),
        tracks: trackNames,
        tracks_time: trackSecs
      };
      this.loading = true;
      this.syncResult = null;
      this.$axios({
        url: `/api/album/pool/update/${this.albumId}`,
        method: 'PUT',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`, 'Content-Type': 'application/json'},
        data: submitData
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200) {
              this.syncResult = res.data;
              this.handleClose(true); // 传参表示修改成功
            } else {
              this.errorMsg = '修改失败：' + res.data.msg;
            }
          })
          .catch(err => {
            this.loading = false;
            console.error('修改专辑失败：', err);
            this.errorMsg = '修改失败！' + (err.response?.data?.msg || err.message);
          });
    },
    // ✅ 点击蒙版关闭侧边栏 (只关闭当前侧边栏，不跳转路由)
    handleMaskClose(e) {
      if (e.target.className === 'sidebar-mask') {
        this.handleClose();
      }
    },
    // ✅ 关闭侧边栏统一方法
    handleClose(isSuccess = false) {
      this.$emit('close', isSuccess); // 向父组件传值，告知关闭/修改成功
      this.resetForm();
    },
    // 重置表单数据
    resetForm() {
      this.album = {
        album_name: "",
        cover_img: "",
        singer: "",
        release_year: "",
        duration_type: "LP",
        album_intro: "",
        songs: [{song_name: "", track_time: "0:00:00"}],
        tracks_time: []
      };
      this.errorMsg = "";
      this.syncResult = null;
      this.showParseModal = false;
      this.loading = false;
      this.isUploading = false;
    }
  }
};
</script>

<style scoped>
/* 根容器 */
.sidebar-root-container {
  position: relative;
  z-index: 9999;
}

/* 左侧蒙版 0.5透明度 */
.sidebar-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 9998;
  transition: all 0.3s ease;
}

/* ✅ 修改专辑 左侧侧边栏主样式 */
.edit-album-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 580px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  z-index: 9999;
  transform: translateX(-100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding-bottom: 30px;
  box-shadow: 2px 0 15px rgba(0, 0, 0, 0.2);
  box-sizing: border-box;
}

.edit-album-sidebar.show {
  transform: translateX(0);
}

/* 头部标题栏 */
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid v-bind(mainColorDark);
  margin-bottom: 10px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  color: v-bind(mainColorDark);
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
  width: 30px;
  height: 30px;
  line-height: 30px;
}

.close-btn:hover {
  color: #ff4444;
}

.sidebar-content {
  padding: 0 20px;
}

/* 全局字体颜色：非按钮全部用mainColorDark */
.form-item {
  margin: 15px 0;
  text-align: left;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: v-bind(mainColorDark);
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 9px 10px;
  box-sizing: border-box;
  border: 1px solid v-bind(mainColorDark);
  border-radius: 4px;
  font-size: 14px;
  color: v-bind(mainColorDark);
  background: rgba(255, 255, 255, 0.3);
}

.form-input::placeholder {
  color: v-bind(mainColorDark);
  opacity: 0.7;
}

.album-type-select {
  background: rgba(255, 255, 255, 0.3);
  cursor: pointer;
}

.album-intro-textarea {
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.intro-tip {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: v-bind(mainColorDark);
  opacity: 0.8;
  line-height: 1.4;
}

/* 封面上传区 */
.upload-area {
  width: 100%;
  height: 110px;
  border: 2px dashed v-bind(mainColorDark);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: v-bind(mainColorDark);
  cursor: pointer;
  margin-bottom: 10px;
  transition: border-color 0.3s;
  background: rgba(255, 255, 255, 0.2);
}

.upload-area:hover {
  border-color: v-bind(mainColorDarkDouble);
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* 单曲列表样式 */
.song-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid v-bind(mainColorDark);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
}

.song-index {
  color: v-bind(mainColorDark);
  font-weight: 600;
  width: 20px;
  text-align: center;
}

.song-input {
  padding: 8px !important;
  border: 1px solid v-bind(mainColorDark) !important;
  color: v-bind(mainColorDark) !important;
  background: rgba(255, 255, 255, 0.3) !important;
}

.song-input::placeholder {
  color: v-bind(mainColorDark) !important;
  opacity: 0.7 !important;
}

.btn-delete-song {
  width: 28px;
  height: 28px;
  line-height: 28px;
  padding: 0 !important;
  background: #ff4444 !important;
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 按钮样式 保留不变 */
.btn-add-song {
  padding: 9px 16px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
  margin-top: 8px;
}

.btn-add-song:hover {
  background: v-bind(mainColorDarkDouble);
}

.btn-group {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-submit {
  flex: 1;
  padding: 11px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: v-bind(mainColorDark);
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.btn-cancel {
  flex: 1;
  padding: 11px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: #999;
  color: white;
  font-size: 14px;
}

.btn-submit:disabled, .btn-cancel:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 提示样式 */
.error-tip {
  color: v-bind(mainColorDark);
  margin-top: 10px;
  text-align: center;
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  background: rgba(255, 245, 245, 0.5);
}

.sync-result {
  margin-bottom: 20px;
  padding: 12px 16px;
  border-radius: 6px;
  background-color: rgba(240, 248, 251, 0.5);
  border: 1px solid v-bind(mainColorDark);
}

.sync-result-title {
  font-weight: 600;
  color: v-bind(mainColorDark);
  margin-bottom: 4px;
  font-size: 14px;
}

.sync-result-content {
  color: v-bind(mainColorDark);
  font-size: 13px;
}

.sync-count {
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
  margin-left: 8px;
}

.sync-tips {
  margin-bottom: 20px;
  padding: 10px;
  border-radius: 4px;
  background-color: rgba(248, 249, 250, 0.5);
  color: v-bind(mainColorDark);
  font-size: 12px;
  line-height: 1.5;
}

/* 滚动条美化 */
.edit-album-sidebar::-webkit-scrollbar {
  width: 6px;
}

.edit-album-sidebar::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDark);
  opacity: 0.5;
  border-radius: 3px;
}

.edit-album-sidebar::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDarkDouble);
}

/* ✅ 文本解析 右侧侧边栏样式 (和AddAlbum完全一致) */
.parse-sidebar-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 99997;
  transition: all 0.3s ease;
}

.track-parse-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 560px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  z-index: 99998;
  transform: translateX(100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding: 10px 0;
  box-shadow: -2px 0 15px rgba(0, 0, 0, 0.2);
}

.track-parse-sidebar.show {
  transform: translateX(0);
}
</style>