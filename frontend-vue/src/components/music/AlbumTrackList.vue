<template>
  <div class="tab-content">
    <!-- 整轨欣赏卡片 - 置顶核心区域 -->
    <div class="tip-card">
      <div class="appreciation-header">
        <h3>整轨欣赏</h3>
        <!-- ✅ 核心优化：上传+更新+删除 按钮组合，删除按钮仅在有音频时显示 -->
        <div class="btn-group" v-if="isAdmin">
          <button class="get-btn upload-btn" @click="showUploadSidebar = true">
            {{ audioSrc ? '更新' : '上传' }}
          </button>
          <!-- 删除按钮：有音频时显示，样式区分，红色警示 -->
          <button v-if="audioSrc" class="get-btn delete-btn" @click="handleDeleteAudio">
            删除
          </button>
        </div>
      </div>

      <!-- 音乐播放器区域：上传了MP3显示播放器，否则显示暂无资源 -->
      <div class="music-player-container">
        <div v-if="audioSrc" class="music-player">
          <button class="play-btn" @click="togglePlayPause">
            {{ isPlaying ? '⏸' : '▶' }}
          </button>
          <input
            type="range"
            class="progress-bar"
            :value="currentProgress"
            min="0"
            max="100"
            @input="handleProgressChange"
          />
          <div class="time-text">
            {{ formatTime(currentTime) }} / {{ durationFormat }}
          </div>
          <div class="volume-wrapper" @mouseenter="showVolume = true" @mouseleave="showVolume = false">
            <span class="volume-icon">🔊</span>
            <div class="volume-dropdown" v-show="showVolume">
              <input
                type="range"
                class="volume-bar"
                v-model="volume"
                min="0"
                max="1"
                step="0.05"
              />
            </div>
          </div>
        </div>
        <div v-else class="no-resource">暂无资源</div>
      </div>
    </div>

    <h2>内容</h2>
    <h3>简介</h3>
    <div class="tracks-list">
      <div v-for="(track, idx) in (album.tracks || [])" :key="idx" class="track-item">
        <h4>{{ idx+1 }}. {{ track.track_name || '未知曲目' }}  {{ track.duration || '0:00' }}</h4>
      </div>
    </div>

    <!-- 右侧上传侧边栏 -->
    <div class="upload-sidebar" v-show="showUploadSidebar">
      <div class="sidebar-header">
        <h4>{{ audioSrc ? '更新整轨MP3文件' : '上传整轨MP3文件' }}</h4>
        <button class="close-btn" @click="showUploadSidebar = false">×</button>
      </div>
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
      <div class="upload-status" :class="statusClass">{{ statusText }}</div>
    </div>

    <div class="mask" v-show="showUploadSidebar" @click="showUploadSidebar = false"></div>
    <audio ref="audioRef" :src="audioSrc" @timeupdate="handleTimeUpdate" @ended="handleEnded" :volume="volume"></audio>
  </div>
</template>

<script>
export default {
  name: 'AlbumTrackList',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    }
  },
  data() {
    return {
      showUploadSidebar: false,
      audioSrc: '',
      fileName: '',
      volume: 0.7,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      durationFormat: '0:00',
      currentProgress: 0,
      statusText: '',
      statusClass: '',
      showVolume: false,
      isAdmin: false,
      oldMp3Url: ''
    };
  },
  async mounted() {
    this.checkAdminRole();
    if (this.album.source_pool_id) {
      await this.getAlbumAudioInfo()
    }
  },
  activated() {
    this.checkAdminRole();
    if (this.album.source_pool_id) {
      this.getAlbumAudioInfo();
    }
  },
  methods: {
    checkAdminRole() {
      try {
        const isAdminStr = localStorage.getItem('is_admin');
        this.isAdmin = Number(isAdminStr) === 1;
      } catch (err) {
        this.isAdmin = false;
        console.log('用户权限读取失败', err);
      }
    },

    async getAlbumAudioInfo() {
      try {
        const res = await this.$axios.get(`/api/album/pool/audio/info/${this.album.source_pool_id}`)
        if (res.data.code === 200 && res.data.data.mp3_url) {
          this.audioSrc = res.data.data.mp3_url
          this.fileName = res.data.data.mp3_name
          this.duration = res.data.data.mp3_duration
          this.durationFormat = res.data.data.duration_format
          this.oldMp3Url = res.data.data.mp3_url
        } else {
          this.oldMp3Url = ''
        }
      } catch (err) {
        console.log('暂无已上传的音频资源')
        this.oldMp3Url = ''
      }
    },

    handleFileChange(e) {
      const file = e.target.files[0];
      if (file) {
        this.handleFile(file);
        this.$refs.fileInput.value = ''
      }
    },
    handleDrop(e) {
      const file = e.target.files[0];
      if (file) {
        this.handleFile(file);
      }
    },

    async handleFile(file) {
      if (file.type !== 'audio/mpeg' && !file.name.toLowerCase().endsWith('.mp3')) {
        this.statusText = '❌ 仅支持上传MP3格式！';
        this.statusClass = 'error';
        return;
      }

      if (!this.album.source_pool_id) {
        this.statusText = '❌ 公共专辑ID不存在，无法上传！';
        this.statusClass = 'error';
        return;
      }

      this.statusText = this.audioSrc ? '⏳ 更新中，请稍候...' : '⏳ 上传中，请稍候...';
      this.statusClass = '';
      try {
        const formData = new FormData()
        formData.append('source_pool_id', this.album.source_pool_id)
        formData.append('mp3_file', file)
        formData.append('old_mp3_url', this.oldMp3Url || '')

        const res = await this.$axios.post('/api/album/pool/audio/upload', formData)

        if (res.data.code === 200) {
          this.audioSrc = res.data.data.mp3_url
          this.fileName = res.data.data.mp3_name
          this.duration = res.data.data.mp3_duration
          this.durationFormat = res.data.data.duration_format
          this.oldMp3Url = res.data.data.mp3_url
          this.statusText = this.audioSrc ? '✅ 更新成功，播放新音频' : '✅ 上传成功，可播放';
          this.statusClass = 'success';
          setTimeout(() => {
            this.showUploadSidebar = false
            this.statusText = ''
            this.statusClass = ''
          }, 2000)
        } else {
          this.statusText = `❌ ${res.data.msg}`;
          this.statusClass = 'error';
        }
      } catch (err) {
        console.error('音频操作失败：', err)
        if (err.response && err.response.data) {
          const {code, msg} = err.response.data;
          if(code ===403) this.statusText = '❌ 权限不足！仅管理员可操作';
          else if(code ===404) this.statusText = '❌ 公共专辑不存在！';
          else this.statusText = `❌ ${msg || '操作失败，请重试'}`;
        } else {
          this.statusText = '❌ 连接服务器失败，请检查后端状态';
        }
        this.statusClass = 'error';
      }
      this.isPlaying = false;
      this.currentTime = 0;
      this.currentProgress = 0;
    },

    // ✅ 核心新增：删除音频功能
    async handleDeleteAudio() {
      // 二次确认，防止误删
      const confirmDel = confirm("确定要删除该音频资源吗？删除后无法恢复！");
      if (!confirmDel) return;

      try {
        this.statusText = '⏳ 删除中，请稍候...';
        this.statusClass = '';
        // 调用后端删除接口
        const res = await this.$axios.post('/api/album/pool/audio/delete', {
          source_pool_id: this.album.source_pool_id,
          mp3_url: this.oldMp3Url
        })

        if (res.data.code === 200) {
          this.statusText = '✅ 音频删除成功！';
          this.statusClass = 'success';
          // ✅ 清空所有音频数据，页面恢复暂无资源
          this.clearAudioData();
          setTimeout(() => {
            this.statusText = '';
            this.statusClass = '';
          }, 2000);
        } else {
          this.statusText = `❌ ${res.data.msg}`;
          this.statusClass = 'error';
        }
      } catch (err) {
        console.error('音频删除失败：', err);
        this.statusText = '❌ 音频删除失败，请重试！';
        this.statusClass = 'error';
      }
    },

    // ✅ 新增：清空音频数据方法
    clearAudioData() {
      this.audioSrc = '';
      this.fileName = '';
      this.duration = 0;
      this.durationFormat = '0:00';
      this.oldMp3Url = '';
      this.isPlaying = false;
      this.currentTime = 0;
      this.currentProgress = 0;
    },

    togglePlayPause() {
      const audio = this.$refs.audioRef;
      this.isPlaying ? audio.pause() : audio.play();
      this.isPlaying = !this.isPlaying;
    },
    handleTimeUpdate() {
      const audio = this.$refs.audioRef;
      this.currentTime = audio.currentTime;
      this.duration = audio.duration || this.duration;
      this.currentProgress = this.duration ? (this.currentTime / this.duration) * 100 : 0;
    },
    handleProgressChange(e) {
      const audio = this.$refs.audioRef;
      const progress = e.target.value;
      this.currentProgress = progress;
      this.currentTime = (progress / 100) * this.duration;
      audio.currentTime = this.currentTime;
    },
    handleEnded() {
      this.isPlaying = false;
      this.currentProgress = 0;
      this.currentTime = 0;
    },
    formatTime(seconds) {
      if (!seconds) return '0:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      return `${min}:${sec.toString().padStart(2, '0')}`;
    }
  },
  beforeUnmount() {
    if (this.audioSrc && this.audioSrc.includes('blob:')) {
      URL.revokeObjectURL(this.audioSrc);
    }
  }
};
</script>

<style scoped>
.tab-content {
  position: relative;
  min-height: 100vh;
  box-sizing: border-box;
}

.tracks-list {
  margin: 20px 0;
	font-size: 14px;
}

.track-item {
  margin-bottom: 8px;
	padding: 4px 0;
	border-bottom: 1px dashed #eee;
}

.tip-card {
  background: #f0f8fb;
	padding: 20px;
	border-radius: 8px;
	margin-bottom: 30px;
	position: relative;
}

.appreciation-header {
  display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 20px;
}

.appreciation-header h3 {
  margin: 0;
	font-size: 18px;
	color: #1f759d;
}
/* ✅ 新增：按钮组样式，上传+删除按钮并排 */
.btn-group{
  display: flex;
  gap: 8px;
  align-items: center;
}
.get-btn {
  background: #2ea0d6;
	color: #fff;
	border: none;
	padding: 6px 12px;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
	transition: background 0.2s;
}
.get-btn:hover {
  background: #1f759d;
}
/* ✅ 新增：删除按钮红色样式，警示作用 */
.delete-btn {
  background: #dc2626;
}
.delete-btn:hover {
  background: #b91c1c;
}

.music-player-container {
  width: 100%;
}

.no-resource {
  color: #999;
	font-size: 14px;
	text-align: center;
	padding: 10px 0;
}

.music-player {
  display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: wrap;
	padding: 6px 0;
}

.play-btn {
  background: #2ea0d6;
	color: white;
	border: none;
	padding: 8px;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
	width: 40px;
	height: 32px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.play-btn:hover {
  background: #1f759d;
}

.progress-bar {
  flex: 1;
	min-width: 200px;
	height: 6px;
	cursor: pointer;
	accent-color: #2ea0d6;
}

.time-text {
  font-size: 12px;
	color: #666;
	width: 100px;
}

.volume-wrapper {
  position: relative;
	cursor: pointer;
	font-size: 14px;
}

.volume-icon {
  display: block;
	color: #666;
}

.volume-dropdown {
  position: absolute;
	top: -100px;
	right: 0;
	background: #fff;
	padding: 10px;
	border-radius: 4px;
	box-shadow: 0 2px 8px rgba(0,0,0,0.15);
	z-index: 99;
}

.volume-bar {
  width: 6px;
	height: 80px;
	writing-mode: vertical-lr;
	direction: rtl;
	accent-color: #2ea0d6;
	cursor: pointer;
}

.mask {
  position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0,0,0,0.3);
	z-index: 998;
}

.upload-sidebar {
  position: fixed;
	top: 0;
	right: 0;
	width: 360px;
	height: 100vh;
	background: white;
	z-index: 999;
	box-shadow: -2px 0 8px rgba(0,0,0,0.15);
	padding: 20px;
	box-sizing: border-box;
	overflow-y: auto;
}

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
}

.upload-area:hover {
  border-color: #2ea0d6;
	background: #f0f8fb;
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

.upload-tips p {
  margin: 4px 0;
}

.tip-text {
  font-size: 12px;
	color: #999;
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

.success {
  color: #15803d;
	background: #f0fdf4;
}

.error {
  color: #dc2626;
	background: #fef2f2;
}
</style>