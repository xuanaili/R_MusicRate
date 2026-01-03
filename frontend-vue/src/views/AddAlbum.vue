<template>
  <div class="add-album-container">
    <h2>添加新专辑</h2>
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
        rows="8"
        spellcheck="false"
      ></textarea>
      <p class="intro-tip">提示：支持分段（按Enter）、特殊符号，内容将完整保存</p>
    </div>

    <!-- 核心：单曲列表【新增时间戳输入框】 -->
    <div class="form-item">
      <label>单曲列表：</label>
      <!-- 循环渲染单曲+时间戳输入框 -->
      <div class="song-item" v-for="(song, index) in album.songs" :key="index">
        <div class="song-input-wrapper">
          <span class="song-index">{{ index + 1 }}.</span>
          <input
            v-model="song.song_name"
            type="text"
            placeholder="请输入单曲名"
            class="song-input"
          >
          <!-- ✅✅✅ 新增：时间戳输入框 -->
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
        <!-- 至少保留1个输入框才显示删除按钮 -->
        <button
          v-if="album.songs.length > 1"
          @click="removeSong(index)"
          class="btn-delete-song"
        >
          ×
        </button>
      </div>
      <!-- 添加单曲 + 文本解析 按钮并排 -->
      <div class="song-btn-group">
        <button @click="addSong" class="btn-add-song">+ 添加单曲</button>
        <button @click="showParseModal = true" class="btn-parse-song">📝 文本解析</button>
      </div>
    </div>

    <!-- 按钮区 -->
    <div class="btn-group">
      <button @click="submitAlbum" class="btn-submit">提交专辑</button>
      <button @click="goBack" class="btn-cancel">取消</button>
    </div>
    <!-- 错误提示 -->
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>

    <!-- 文本解析组件弹窗 -->
    <TrackParse
      v-if="showParseModal"
      :visible="showParseModal"
      :main-color-dark="'#359469'"
      :main-color-dark-double="'#257d51'"
      @close="showParseModal = false"
      @parse-success="handleParseSuccess"
    />
  </div>
</template>

<script>
// 引入文本解析组件
import TrackParse from '@/components/sidebar/TrackParse.vue'

export default {
  name: 'AddAlbum',
  components: { TrackParse },
  data() {
    return {
      album: {
        album_name: "",
        cover_img: "",
        album_singer: "",
        release_year: "",
        duration_type:"LP",
        album_intro: "",
        // ✅✅✅ 修改：单曲数组新增 track_time 字段 存放时间戳文本
        songs: [{ song_name: "", track_time: "0:00:00" }]
      },
      errorMsg: "",
      isUploading: false,
      showParseModal: false
    };
  },
  created() {
    // 登录校验：未登录跳转到登录页
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
    }
  },
  methods: {
    // ========== 新增：时间戳格式化相关方法（和你参考页面逻辑完全一致） ==========
    // 过滤时间戳输入：只保留数字和冒号，最多2个冒号
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      const colonCount = filterVal.split(':').length - 1;
      if (colonCount > 2) filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      return filterVal;
    },
    // 时间戳文本 转 总秒数
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
    // 总秒数 转 标准时间戳文本 0:00:00
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const totalSeconds = Math.floor(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const sec = Math.floor(totalSeconds % 60);
      return `${hours}:${minutes.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
    // 失去焦点时自动格式化时间戳
    formatDurationInput(song) {
      song.track_time = this.secondsToTime(this.timeToSeconds(song.track_time));
    },

    // ========== 单曲列表核心方法 ==========
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

    // ========== 封面上传相关方法 ==========
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
          headers: {
            'Content-Type': 'multipart/form-data'
          },
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

    // ========== 提交专辑方法【核心修改：新增 tracks_time 数组提交】 ==========
    submitAlbum() {
      this.errorMsg = "";
      // 1. 基础字段校验
      if (!this.album.album_name.trim()) {
        this.errorMsg = "专辑名不能为空！";
        return;
      }
      if (!this.album.album_singer.trim()) {
        this.errorMsg = "歌手名不能为空！";
        return;
      }
      if (!this.album.release_year || isNaN(this.album.release_year)) {
        this.errorMsg = "请输入有效的发行年份！";
        return;
      }

      // 2. 单曲列表校验：过滤空值并检查至少1首有效单曲
      const validSongs = this.album.songs
        .filter(song => song.song_name.trim()) // 过滤单曲名为空的项
        .map(song => {
          return {
            name: song.song_name.trim(),
            time: this.timeToSeconds(song.track_time) // 转成秒数
          }
        });
      if (validSongs.length === 0) {
        this.errorMsg = "至少填写1首单曲名！";
        return;
      }

      // 3. 构造提交数据 ✅✅✅ 核心：新增 tracks_time 数组
      const submitData = {
        album_name: this.album.album_name.trim(),
        cover_img: this.album.cover_img.trim(),
        singer: this.album.album_singer.trim(),
        release_year: Number(this.album.release_year),
        album_intro: this.album.album_intro.trim(),
        duration_type: this.album.duration_type,
        tracks: validSongs.map(item => item.name), // 单曲名数组
        tracks_time: validSongs.map(item => item.time) // 时间戳秒数数组 ✅✅✅
      };

      // 4. 调用后端接口
      this.$axios({
        url: "/api/album/add",
        method: "POST",
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: submitData
      })
          .then(res => {
            if (res.data.code === 200) {
                this.$router.push({ path: '/webhome' }).then(() => {
    // 找到WebHome组件实例，修改其激活的tab值
    const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
    if (webHomeVm) {
      webHomeVm.activeMainTab = 'mymusic'
    }
  })
            } else {
              this.errorMsg = res.data.msg;
            }
          })
          .catch(err => {
            console.error("添加专辑失败：", err);
            this.errorMsg = "添加失败，请检查后端是否启动或网络连接！";
          });
    },

    // 取消按钮：返回上一页
    goBack() {
      this.$router.go(-1);
    },

// ========== 文本解析成功回调【修复核心：适配子组件传递的 对象数组，不用动子组件！】 ==========
handleParseSuccess(parseSongs) {
  this.showParseModal = false;
  this.errorMsg = '';
  // ✅ 核心修复：parseSongs是子组件传的【对象数组】，里面包含 name(单曲名) + duration(格式化时间戳)
  // 这里循环解析对象的属性，转成当前页面需要的 {song_name:xxx, track_time:xxx} 格式
  const formatSongs = parseSongs.map(item => {
    return {
      song_name: item.name ? item.name.trim() : '', // 取对象的name字段作为单曲名
      track_time: item.duration ? item.duration : '0:00:00' // 取对象的duration字段作为时间戳
    }
  });
  // ✅ 把解析好的数组赋值给页面的单曲列表，完成填充
  this.album.songs = formatSongs;
  alert(`解析成功！共识别到 ${formatSongs.length} 首单曲，已自动填充 ✔️`);
}
  }
};
</script>

<style scoped>
.add-album-container {
  width: 600px;
  margin: 50px auto;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  background: #fff;
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

.form-item input {
  width: 100%;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.album-type-select {
  width: 100%;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
  background: #fff;
}

.album-intro-textarea {
  width: 100%;
  padding: 12px;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.intro-tip {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

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
  gap: 10px;
}

.song-index {
  color: #666;
  font-weight: 600;
  width: 20px;
  text-align: center;
}

.song-input {
  flex: 3;
  padding: 8px !important;
  border: 1px solid #ddd !important;
}

/* ✅✅✅ 新增：时间戳输入框样式 */
.song-time-input {
  flex: 1;
  padding: 8px !important;
  border: 1px solid #ddd !important;
  text-align: center;
  font-size: 13px;
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

/* 按钮并排样式 */
.song-btn-group {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.btn-add-song {
  padding: 10px 16px;
  background: #42b983;
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
  background: #359469;
}

.btn-parse-song {
  padding: 10px 16px;
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

.error-tip {
  color: #ff4444;
  margin-top: 10px;
  text-align: center;
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  background: #fff5f5;
}
</style>