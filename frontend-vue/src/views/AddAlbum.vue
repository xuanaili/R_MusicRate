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
      <input v-model="album.singer" type="text" placeholder="请输入歌手名">
    </div>
    <!-- 发行年份 -->
    <div class="form-item">
      <label>发行年份：</label>
      <input v-model="album.release_year" type="number" placeholder="如：2024">
    </div>
    <!-- ✅✅✅ 新增：专辑类型选择框 (LP/EP/Mix/Com) 核心改动1 -->
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



    <!-- 新增：专辑简介（放在单曲列表上方） -->
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

    <!-- 核心：单曲列表（优化交互） -->
    <div class="form-item">
      <label>单曲列表：</label>
      <!-- 循环渲染单曲输入框 -->
      <div class="song-item" v-for="(song, index) in album.songs" :key="index">
        <div class="song-input-wrapper">
          <span class="song-index">{{ index + 1 }}.</span>
          <input
            v-model="song.song_name"
            type="text"
            placeholder="请输入单曲名"
            class="song-input"
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
      <!-- 添加单曲按钮（优化样式，更突出） -->
      <button @click="addSong" class="btn-add-song">+ 添加单曲</button>
    </div>

    <!-- 按钮区 -->
    <div class="btn-group">
      <button @click="submitAlbum" class="btn-submit">提交专辑</button>
      <button @click="goBack" class="btn-cancel">取消</button>
    </div>
    <!-- 错误提示 -->
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
  </div>
</template>

<script>
export default {
  name: 'AddAlbum',
  data() {
    return {
      // 新增 album_intro 字段
      album: {
        album_name: "",
        cover_img: "",
        singer: "",
        release_year: "",
        duration_type:"LP",
        album_intro: "", // 专辑简介
        // 单曲列表：初始1个空输入框
        songs: [{ song_name: "" }]
      },
      errorMsg: "",
      isUploading: false
    };
  },
  created() {
    // 登录校验：未登录跳转到登录页
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
    }
  },
  methods: {
    // ========== 单曲列表核心方法 ==========
    // 添加单曲输入框
    addSong() {
      this.album.songs.push({ song_name: "" });
      // 清除之前的错误提示
      this.errorMsg = "";
      // 可选：新增后自动聚焦到新输入框（提升体验）
      this.$nextTick(() => {
        const inputs = document.querySelectorAll('.song-input');
        if (inputs.length > 0) {
          inputs[inputs.length - 1].focus();
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
        e.target.value = ""; // 清空文件选择器，避免重复选择同一文件无反应
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
          alert("图片上传成功！已自动填充封面链接～");
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

    // ========== 提交专辑方法 ==========
    submitAlbum() {
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
      if (!this.album.release_year || isNaN(this.album.release_year)) {
        this.errorMsg = "请输入有效的发行年份！";
        return;
      }

      // 2. 单曲列表校验：过滤空值并检查至少1首有效单曲
      const validSongs = this.album.songs
        .map(song => song.song_name.trim())
        .filter(name => name); // 过滤空字符串
      if (validSongs.length === 0) {
        this.errorMsg = "至少填写1首单曲名！";
        return;
      }

      // 3. 构造提交数据（新增 album_intro 字段）
      const submitData = {
        album_name: this.album.album_name.trim(),
        cover_img: this.album.cover_img.trim(),
        singer: this.album.singer.trim(),
        release_year: Number(this.album.release_year),
        album_intro: this.album.album_intro.trim(), // 专辑简介（保留原始格式）
        duration_type: this.album.duration_type,
        tracks: validSongs // 仅传递有效单曲名数组
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
          alert("专辑添加成功！");
          // 提交成功后跳回专辑列表
          this.$router.push("/albumDetail");
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
      this.$router.go(-1); // 通用返回，比固定路由更灵活
    }
  }
};
</script>

<style scoped>
.add-album-container {
  width: 500px;
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

/* ✅✅✅ 新增：专辑类型下拉框样式 */
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

/* 专辑简介文本框样式 */
.album-intro-textarea {
  width: 100%;
  padding: 12px;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
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

/* 单曲列表样式优化 */
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
  flex: 1;
  padding: 8px !important;
  border: 1px solid #ddd !important;
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

/* 按钮区样式优化 */
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
</style>