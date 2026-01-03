<template>
  <div class="edit-album-container">
    <h2>修改公共专辑模板</h2>

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
          <img v-else :src="album.cover_img" class="preview-img" alt="封面预览">
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
            rows="8"
            spellcheck="false"
        ></textarea>
        <p class="intro-tip">提示：支持分段（按Enter）、特殊符号，内容将完整保存</p>
      </div>

      <!-- 核心：单曲列表 + 时间戳输入框 + 文本解析按钮 -->
      <div class="form-item">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <label>单曲列表：</label>
          <!-- ✅ 新增：文本解析按钮 -->
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
            <!-- ✅ 新增：时间戳输入框 -->
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
          <!-- 至少保留1个输入框才显示删除按钮 -->
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
        <button @click="goBack" class="cancel-btn btn-cancel" :disabled="loading || isUploading">取消</button>
      </div>
    </div>

    <!-- ✅ 新增：文本解析弹窗组件 (和AddAlbum一致，组件源码完全不动) -->
    <TrackParse
      :visible="showParseModal"
      :main-color-dark="mainColorDark"
      :main-color-dark-double="mainColorDarkDouble"
      @close="showParseModal = false"
      @parse-success="handleParseSuccess"
    />
  </div>
</template>

<script>
// ✅ 新增：导入文本解析组件，路径和你其他页面一致，不动组件源码
import TrackParse from '@/components/sidebar/TrackParse.vue'

export default {
  name: 'EditPoolAlbum',
  // ✅ 注册组件
  components: { TrackParse },
  data() {
    return {
      albumId: '', // 公共专辑ID
      // 专辑表单（新增tracks_time字段）
      album: {
        album_name: "",
        cover_img: "",
        singer: "",
        release_year: "",
        duration_type: "LP", // 默认选中正式专辑
        album_intro: "", // 专辑简介
        songs: [{song_name: "", track_time: "0:00:00"}], // ✅ 新增 track_time 时间戳字段
        tracks_time: [] // ✅ 新增：存储时间戳对应的秒数数组
      },
      loading: false,
      isUploading: false,
      syncResult: null, // 存储同步结果
      errorMsg: "", // 错误提示
      // ✅ 新增解析相关变量
      showParseModal: false,
      mainColorDark: '#2f9465',
      mainColorDarkDouble: '#257d51'
    }
  },
  created() {
    // 检查登录和管理员权限
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    if (localStorage.getItem('is_admin') !== '1') {
      alert('无管理员权限，禁止修改！');
      this.$router.push('/album-pool');
      return;
    }

    // 获取URL中的专辑ID
    this.albumId = this.$route.params.poolId;
    // 加载原有数据
    this.getAlbumData();
  },
  methods: {
    // ========== ✅ 新增：时间戳处理核心工具方法 (和AddAlbum/AlbumTrackList完全一致) ==========
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

    // ========== 单曲列表核心方法（改造适配时间戳） ==========
    // 添加单曲输入框
    addSong() {
      this.album.songs.push({song_name: "", track_time: "0:00:00"}); // ✅ 新增时间戳默认值
      this.errorMsg = "";
      // 新增后自动聚焦
      this.$nextTick(() => {
        const inputs = document.querySelectorAll('.song-input');
        if (inputs.length > 0) {
          inputs[inputs.length - 2].focus(); // 聚焦到歌曲名输入框
        }
      });
    },
    // 删除指定索引的单曲输入框
    removeSong(index) {
      if (this.album.songs.length <= 1) {
        this.errorMsg = "至少保留1首单曲！";
        return;
      }
      this.album.songs.splice(index, 1);
      this.errorMsg = "";
    },

    // ========== 封面上传相关方法（无改动） ==========
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
        e.target.value = ""; // 清空文件选择器
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
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'multipart/form-data'
          },
          timeout: 15000
        });
        if (res.data.code === 200) {
          this.album.cover_img = res.data.data.img_url || res.data.data.url; // 兼容两种返回格式
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

    // ========== ✅ 核心改造：加载原有专辑数据（适配 tracks + tracks_time 回显） ==========
    getAlbumData() {
      this.loading = true;
      this.$axios({
        url: `/api/album/pool/detail/${this.albumId}`,
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200) {
              const data = res.data.data;
              // 后端返回的 tracks 和 tracks_time 都是数组
              const trackNames = data.tracks && Array.isArray(data.tracks) ? data.tracks : [];
              const trackSecs = data.tracks_time && Array.isArray(data.tracks_time) ? data.tracks_time : [];
              // 组装单曲列表：歌曲名 + 格式化时间戳
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
              // 基础信息赋值
              this.album = {
                album_name: data.album_name || "",
                cover_img: data.cover_img || "",
                singer: data.singer || "",
                release_year: data.release_year || "",
                duration_type: data.duration_type || "LP",
                album_intro: data.album_intro || "",
                songs: songs, // 赋值组装好的单曲+时间戳
                tracks_time: trackSecs // 赋值原始秒数数组
              };
            } else {
              alert('加载专辑数据失败：' + res.data.msg);
              this.goBack();
            }
          })
          .catch(err => {
            this.loading = false;
            console.error('加载专辑数据失败：', err);
            alert('加载数据失败！');
            this.goBack();
          });
    },

    // ========== ✅ 新增：文本解析成功回调（和AddAlbum一致，适配组件返回的对象数组，不动组件） ==========
    handleParseSuccess(parseSongs) {
      this.showParseModal = false;
      this.errorMsg = '';
      // 适配子组件返回的对象数组：{name:xxx, duration:xxx} → 转当前页面的 {song_name:xxx, track_time:xxx}
      const formatSongs = parseSongs.map(item => {
        return {
          song_name: item.name ? item.name.trim() : '',
          track_time: item.duration ? item.duration : '0:00:00'
        }
      });
      this.album.songs = formatSongs;
      alert(`解析成功！共识别到 ${formatSongs.length} 首单曲，已自动填充 ✔️`);
    },

    // ========== ✅ 核心改造：提交修改（新增 tracks_time 秒数提交给后端） ==========
    submitEdit() {
      // 清除之前的错误提示
      this.errorMsg = "";

      // 1. 基础字段校验
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

      // 2. 单曲列表校验
      const validSongs = this.album.songs
          .map(song => ({
            name: song.song_name.trim(),
            time: song.track_time || '0:00:00'
          }))
          .filter(item => item.name);
      if (validSongs.length === 0) {
        this.errorMsg = "至少填写1首单曲名！";
        return;
      }

      // ✅ 核心：把 格式化时间戳 → 转成 秒数数组 tracks_time
      const trackNames = validSongs.map(item => item.name);
      const trackSecs = validSongs.map(item => this.timeToSeconds(item.time));

      // 3. 构造提交数据（✅ 新增 tracks_time 字段传给后端）
      const submitData = {
        album_name: this.album.album_name.trim(),
        cover_img: this.album.cover_img.trim(),
        singer: this.album.singer.trim(),
        release_year: this.album.release_year ? Number(this.album.release_year) : '',
        duration_type: this.album.duration_type,
        album_intro: this.album.album_intro.trim(),
        tracks: trackNames, // 歌曲名数组
        tracks_time: trackSecs // ✅ 新增：时间戳秒数数组，后端直接存入album_pool表
      };

      this.loading = true;
      this.syncResult = null; // 清空之前的同步结果
      this.$axios({
        url: `/api/album/pool/update/${this.albumId}`,
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          'Content-Type': 'application/json'
        },
        data: submitData
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200) {
              // 存储同步结果
              this.syncResult = res.data;

              // 优化提示：显示同步数量
              const syncCount = res.data.data?.sync_count || 0;
              alert(`修改专辑成功！\n已同步更新 ${syncCount} 条用户数据（仅同步开启且未自定义的专辑）`);

              // 跳回专辑详情页
              this.$router.push(`/album/pool/detail/${this.albumId}`);
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

    // 返回上一页
    goBack() {
      this.$router.go(-1);
    }
  }
};
</script>

<style scoped>
/* 基础布局继承添加专辑样式 */
.edit-album-container {
  width: 500px;
  margin: 50px auto;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  background: #fff;
}

.album-form {
  margin-top: 20px;
}

.form-item {
  margin: 15px 0;
  text-align: left;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-input {
  width: 100%;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

/* 专辑简介文本框样式 */
.album-intro-textarea {
  line-height: 1.6;
  resize: vertical; /* 允许垂直调整大小 */
  font-family: inherit;
  white-space: pre-wrap; /* 保留换行和空格 */
  word-wrap: break-word; /* 自动换行 */
}

.intro-tip {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

/* 封面上传区域 */
.upload-area {
  width: 100%;
	height: 120px;
  border: 2px dashed #ddd;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  cursor: pointer;
  margin-bottom: 10px;
  transition: border-color 0.3s;
  background: #f9f9f9;
}

.upload-area:hover {
  border-color: #42b983;
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
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  background: #fafafa;
}

.song-input-wrapper {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 8px;
}

.song-index {
  color: #666;
  font-weight: 600;
  width: 20px;
  text-align: center;
}

.song-input {
  padding: 8px !important;
  border: 1px solid #ddd !important;
}

/* 专辑类型下拉框样式 适配现有风格 */
.album-type-select {
  background: #fff;
  color: #333;
  cursor: pointer;
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

.btn-add-song {
  padding: 10px 16px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 8px;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-add-song:hover {
  background: #359469;
}

/* 按钮区样式 */
.btn-group {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-submit {
  flex: 1;
  padding: 12px;
  border: none;
	border-radius: 4px;
  cursor: pointer;
  background: #42b983;
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: #999;
  color: white;
  font-size: 14px;
}

/* 禁用状态样式 */
.btn-submit:disabled, .btn-cancel:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 错误提示 */
.error-tip {
  color: #ff4444;
  margin-top: 10px;
  text-align: center;
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  background: #fff5f5;
}

/* 同步结果提示样式 */
.sync-result {
  margin-bottom: 20px;
  padding: 12px 16px;
  border-radius: 6px;
  background-color: #f0f8fb;
  border: 1px solid #42b983;
}

.sync-result-title {
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 4px;
  font-size: 14px;
}

.sync-result-content {
  color: #34495e;
  font-size: 13px;
}

.sync-count {
  color: #42b983;
  font-weight: 600;
  margin-left: 8px;
}

/* 同步提示样式 */
.sync-tips {
  margin-bottom: 20px;
  padding: 10px;
  border-radius: 4px;
  background-color: #f8f9fa;
  color: #666;
  font-size: 12px;
  line-height: 1.5;
}
</style>