<template>
  <div class="sidebar-root-container">
    <!-- 左侧添加专辑侧边栏-蒙版 -->
    <div
      v-show="visible"
      class="sidebar-mask"
      @click="handleMaskClose"
    ></div>

    <!-- ✅ 左侧抽屉：添加专辑主侧边栏 (原样式不变) -->
    <div
      class="add-album-sidebar"
      :class="{show: visible}"
    >
      <div class="sidebar-header">
        <h2>添加新专辑</h2>
        <button class="close-btn" @click="handleClose">×</button>
      </div>
      <div class="sidebar-content">
        <!-- 专辑名 -->
        <div class="form-item">
          <label>专辑名：</label>
          <input v-model="album.album_name" type="text" placeholder="请输入专辑名">
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
            <img v-else :src="album.cover_img" class="preview-img" alt="封面预览">
          </div>
          <input type="file" ref="fileInput" accept="image/*" style="display: none" @change="handleFileChange">
          <input v-model="album.cover_img" type="text" placeholder="可选：输入图片URL" style="margin-top: 10px">
        </div>
        <!-- 歌手 -->
        <div class="form-item">
          <label>歌手：</label>
          <input v-model="album.album_singer" type="text" placeholder="请输入歌手名">
        </div>
        <!-- 发行年份 -->
        <div class="form-item">
          <label>发行年份：</label>
          <input v-model="album.release_year" type="number" placeholder="如：2024">
        </div>
        <!-- 专辑类型选择框 (LP/EP/Mix/Com) -->
        <div class="form-item">
          <label>专辑类型：</label>
          <select v-model="album.duration_type" class="album-type-select">
            <option value="LP">LP - 正式专辑</option>
            <option value="EP">EP - 迷你专辑</option>
            <option value="Mix">Mix - 混音专辑</option>
            <option value="Com">Com - 合集/精选</option>
            <option value="Sin">SIN - 单曲专辑</option>
          </select>
        </div>

        <!-- 专辑简介 -->
        <div class="form-item">
          <label>专辑简介：</label>
          <textarea
            v-model="album.album_intro"
            placeholder="请输入专辑简介（支持长文本、分段、特殊符号）"
            class="album-intro-textarea"
            rows="6"
            spellcheck="false"
          ></textarea>
          <p class="intro-tip">提示：支持分段（按Enter）、特殊符号，内容将完整保存</p>
        </div>

        <!-- 核心：单曲列表【新增时间戳输入框】 -->
        <div class="form-item">
          <label>单曲列表：</label>
          <div class="song-item" v-for="(song, index) in album.songs" :key="index">
            <div class="song-input-wrapper">
              <span class="song-index">{{ index + 1 }}.</span>
              <input
                v-model="song.song_name"
                type="text"
                placeholder="请输入单曲名"
                class="song-input"
              >
              <input
                v-model="song.track_time"
                type="text"
                placeholder="0:00:00 时间戳"
                class="song-time-input"
                maxlength="8"
                @input="song.track_time = filterDurationInput(song.track_time)"
                @blur="formatDurationInput(song)"
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
          <!-- 添加单曲 + 文本解析 + 音频解析 按钮并排 -->
          <div class="song-btn-group">
            <button @click="addSong" class="btn-add-song">+ 添加单曲</button>
            <button @click="showParseModal = true" class="btn-parse-song">📝 文本解析</button>
            <button @click="showAutoParseModal = true" class="btn-unlock-song">🎵 音频解析</button>
          </div>
        </div>

        <!-- 按钮区 -->
        <div class="btn-group">
          <button @click="submitAlbum" class="btn-submit">提交专辑</button>
          <button @click="handleClose" class="btn-cancel">取消</button>
        </div>
        <!-- 错误提示 -->
        <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
      </div>
    </div>

    <!-- ✅✅✅ 核心修改：文本解析 独立右侧全屏侧边栏 (原有) -->
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

    <!-- ✅✅✅ 新增：音频解析 独立右侧全屏侧边栏 -->
    <div v-show="showAutoParseModal" class="parse-sidebar-mask" @click="showAutoParseModal = false"></div>
    <div class="unlock-parse-sidebar" :class="{show: showAutoParseModal}">
      <UnlockParse
        :visible="showAutoParseModal"
        :main-color-dark="mainColorDark"
        :main-color-dark-double="mainColorDarkDouble"
        @close="showAutoParseModal = false"
        @parse-success="handleAutoParseSuccess"
      />
    </div>
  </div>
</template>

<script>
// 导入文本解析和音频解析组件
import TrackParse from '@/components/sidebar/TrackParse.vue'
import UnlockParse from '@/components/sidebar/UnlockParse.vue'

export default {
  name: 'AddAlbum',
  components: { TrackParse, UnlockParse },
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    mainColor: {
      type: String,
      default: 'transparent'
    },
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
      album: {
        album_name: "",
        cover_img: "",
        album_singer: "",
        release_year: "",
        duration_type:"LP",
        album_intro: "",
        songs: [{ song_name: "", track_time: "0:00:00" }]
      },
      errorMsg: "",
      isUploading: false,
      showParseModal: false,
      showAutoParseModal: false // 新增：音频解析弹窗控制
    };
  },
  methods: {
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
    formatDurationInput(song) {
      song.track_time = this.secondsToTime(this.timeToSeconds(song.track_time));
    },
    addSong() {
      this.album.songs.push({ song_name: "", track_time: "0:00:00" });
      this.errorMsg = "";
      this.$nextTick(() => {
        const inputs = document.querySelectorAll('.song-input');
        if (inputs.length > 0) {
          inputs[inputs.length - 1].focus();
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
    handleDragOver(e) {
      e.preventDefault();
    },
    handleDrop(e) {
      e.preventDefault();
      if (this.isUploading) return;
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        this.uploadToImgBed(file);
      } else {
        this.errorMsg = "请拖拽有效的图片文件！";
      }
    },
    chooseFile() {
      this.$refs.fileInput.click();
    },
    handleFileChange(e) {
      if (this.isUploading) return;
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        this.uploadToImgBed(file);
        e.target.value = "";
      } else {
        this.errorMsg = "请选择有效的图片文件！";
      }
    },
    async uploadToImgBed(file) {
      this.isUploading = true;
      this.errorMsg = "";
      try {
        const formData = new FormData();
        formData.append('image', file);
        const res = await this.$axios.post('/api/upload_img', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 15000
        });
        if (res.data.code === 200) {
          this.album.cover_img = res.data.data.img_url;
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
    submitAlbum() {
      this.errorMsg = "";
      if (!this.album.album_name.trim()) { this.errorMsg = "专辑名不能为空！"; return; }
      if (!this.album.album_singer.trim()) { this.errorMsg = "歌手名不能为空！"; return; }
      if (!this.album.release_year || isNaN(this.album.release_year)) { this.errorMsg = "请输入有效的发行年份！"; return; }

      const validSongs = this.album.songs
        .filter(song => song.song_name.trim())
        .map(song => ({ name: song.song_name.trim(), time: this.timeToSeconds(song.track_time) }));
      if (validSongs.length === 0) { this.errorMsg = "至少填写1首单曲名！"; return; }
      console.log(this.album)
      const submitData = {
        album_name: this.album.album_name.trim(),
        cover_img: this.album.cover_img.trim(),
        singer: this.album.album_singer.trim(),
        mp3_duration: this.album.mp3_duration, // 关键：添加这个字段！
        mp3_url: this.album.mp3_url || '',  // 新增
        release_year: Number(this.album.release_year),
        album_intro: this.album.album_intro.trim(),
        duration_type: this.album.duration_type,
        tracks: validSongs.map(item => item.name),
        tracks_time: validSongs.map(item => item.time)
      };

      this.$axios({
        url: "/api/album/add",
        method: "POST",
        headers: { 'Authorization': localStorage.getItem('token') || '', 'Content-Type': 'application/json' },
        data: submitData
      }).then(res => {
        if (res.data.code === 200) {
          this.$router.push({ path: '/webhome' }).then(() => {
            const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
            if (webHomeVm) webHomeVm.activeMainTab = 'mymusic'
          })
          this.handleClose()
        } else {
          this.errorMsg = res.data.msg;
        }
      }).catch(err => {
        console.error("添加专辑失败：", err);
        this.errorMsg = "添加失败，请检查后端是否启动或网络连接！";
      });
    },
    handleClose() {
      this.resetForm()
      this.$emit('close')
    },
    handleMaskClose(e) {
      if(e.target.className === 'sidebar-mask'){
        this.handleClose()
      }
    },
    resetForm() {
      this.album = {
        album_name: "",
        cover_img: "",
        album_singer: "",
        release_year: "",
        duration_type:"LP",
        album_intro: "",
        songs: [{ song_name: "", track_time: "0:00:00" }]
      }
      this.errorMsg = ""
      this.showParseModal = false
      this.showAutoParseModal = false // 重置音频解析弹窗
    },
    // 文本解析成功回调
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
    // 新增：音频解析成功回调（直接使用后端返回的URL）
// 新增：音频解析成功回调（直接使用后端返回的URL）
handleAutoParseSuccess(parseResult) {
  this.showAutoParseModal = false;
  this.errorMsg = '';

  // 直接赋值后端返回的所有数据（封面已是图床URL）
  if (parseResult.album_name) this.album.album_name = parseResult.album_name;
  if (parseResult.album_singer) this.album.album_singer = parseResult.album_singer;
  if (parseResult.cover_img) this.album.cover_img = parseResult.cover_img;
  // 新增：保存MP3 URL（提交专辑时一并保存）
  this.album.mp3_url = parseResult.mp3_url || '';
  this.album.mp3_duration = parseResult.mp3_duration || 0;

  // 填充单曲列表
  const formatSongs = parseResult.songs.map(item => ({
    song_name: item.name ? item.name.trim() : '',
    track_time: item.duration ? item.duration : '0:00:00'
  }));
  this.album.songs = formatSongs;

}
  }
};
</script>

<style scoped>
/* ✅ 新增根容器样式，不影响任何布局和样式，纯占位 */
.sidebar-root-container {
  position: relative;
  z-index: 9999;
}
/* ✅ 蒙版透明度0.5 加深遮罩 */
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
/* ✅ 左侧添加专辑侧边栏 样式不变 */
.add-album-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 580px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(8px);
  z-index: 9999;
  transform: translateX(-100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding-bottom: 30px;
	box-shadow: 2px 0 15px rgba(0,0,0,0.2);
}
.add-album-sidebar.show {
  transform: translateX(0);
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid v-bind(mainColorDark);
  margin-bottom: 10px;
}
/* ✅ 所有非按钮字体统一用 mainColorDark 开始 */
.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  color: v-bind(mainColorDark);
}
.sidebar-content {
  padding: 0 20px;
}
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
.form-item input {
  width: 100%;
  padding: 9px 10px;
  box-sizing: border-box;
  border: 1px solid v-bind(mainColorDark);
  border-radius: 4px;
  font-size: 14px;
  color: v-bind(mainColorDark);
  background: rgba(255,255,255,0.3);
}
.form-item input::placeholder {
  color: v-bind(mainColorDark);
  opacity: 0.7;
}
.album-type-select {
  width: 100%;
	padding: 9px 10px;
  box-sizing: border-box;
  border: 1px solid v-bind(mainColorDark);
  border-radius: 4px;
  font-size: 14px;
  color: v-bind(mainColorDark);
  background: rgba(255,255,255,0.3);
}
.album-intro-textarea {
  width: 100%;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid v-bind(mainColorDark);
	border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: v-bind(mainColorDark);
  background: rgba(255,255,255,0.3);
}
.album-intro-textarea::placeholder {
  color: v-bind(mainColorDark);
  opacity: 0.7;
}
.intro-tip {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: v-bind(mainColorDark);
  opacity: 0.8;
  line-height: 1.4;
}
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
  background: rgba(255,255,255,0.2);
}
.upload-area:hover {
  border-color: v-bind(mainColorDarkDouble);
}
.preview-img {
  width: 100%;
	height: 100%;
  object-fit: contain;
}
.song-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid v-bind(mainColorDark);
	border-radius: 4px;
	background: rgba(255,255,255,0.2);
}
.song-input-wrapper {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 10px;
}
.song-index {
  color: v-bind(mainColorDark);
  font-weight: 600;
  width: 20px;
  text-align: center;
}
.song-input {
  flex: 3;
  padding: 8px !important;
  border: 1px solid v-bind(mainColorDark) !important;
  color: v-bind(mainColorDark) !important;
  background: rgba(255,255,255,0.3) !important;
}
.song-input::placeholder {
  color: v-bind(mainColorDark) !important;
  opacity: 0.7 !important;
}
.song-time-input {
  flex: 1;
  padding: 8px !important;
  border: 1px solid v-bind(mainColorDark) !important;
  text-align: center;
  font-size: 13px;
  color: v-bind(mainColorDark) !important;
  background: rgba(255,255,255,0.3) !important;
}
.song-time-input::placeholder {
  color: v-bind(mainColorDark) !important;
  opacity: 0.7 !important;
}
.error-tip {
  color: v-bind(mainColorDark);
  margin-top: 10px;
  text-align: center;
	font-size: 14px;
	padding: 8px;
	border-radius: 4px;
	background: rgba(255,245,245,0.5);
}
/* ✅ 所有非按钮字体统一用 mainColorDark 结束 */

/* ✅ 所有按钮样式 新增音频解析按钮样式 */
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
.song-btn-group {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}
.btn-add-song {
  padding: 9px 16px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
	font-size: 14px;
  transition: background 0.2s;
  flex: 1;
  text-align: center;
}
.btn-add-song:hover {
  background: v-bind(mainColorDarkDouble);
}
.btn-parse-song {
  padding: 9px 16px;
  background: #2196f3;
  color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
  transition: background 0.2s;
  flex: 1;
  text-align: center;
}
.btn-parse-song:hover {
  background: #1976d2;
}
.btn-unlock-song {
  padding: 9px 16px;
  background: #4caf50;
  color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
  transition: background 0.2s;
  flex: 1;
  text-align: center;
}
.btn-unlock-song:hover {
  background: #388e3c;
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

/* ✅ 滚动条美化 */
.add-album-sidebar::-webkit-scrollbar {
  width: 6px;
}
.add-album-sidebar::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDark);
  opacity: 0.5;
  border-radius: 3px;
}
.add-album-sidebar::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDarkDouble);
}

/* ✅✅✅ 重点：文本解析 右侧独立侧边栏 全套样式 */
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
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(8px);
  z-index: 99998;
  transform: translateX(100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding: 10px 0;
  box-shadow: -2px 0 15px rgba(0,0,0,0.2);
}
.track-parse-sidebar.show {
  transform: translateX(0);
}

/* ✅✅✅ 新增：音频解析 右侧独立侧边栏 样式 */
.unlock-parse-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 560px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(8px);
  z-index: 99998;
  transform: translateX(100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding: 10px 0;
  box-shadow: -2px 0 15px rgba(0,0,0,0.2);
}
.unlock-parse-sidebar.show {
  transform: translateX(0);
}
</style>