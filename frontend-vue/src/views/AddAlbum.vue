<template>
  <!-- 模板部分完全不变，无需修改 -->
  <div class="add-album-container">
    <h2>添加新专辑</h2>
    <!-- 专辑名 -->
    <div class="form-item">
      <label>专辑名：</label>
      <input v-model="album.album_name" type="text" placeholder="请输入专辑名">
    </div>
    <!-- 封面图片：改回cover_img -->
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
    <!-- 主类型（后端必填） -->
    <div class="form-item">
      <label>主类型：</label>
      <input v-model="album.main_type" type="text" placeholder="如：华语">
    </div>
    <!-- 标签（多个用逗号分隔） -->
    <div class="form-item">
      <label>标签（多个用逗号分隔）：</label>
      <input v-model="tagInput" type="text" placeholder="如：经典,治愈">
    </div>
    <!-- 评分 -->
    <div class="form-item">
      <label>评分（0-10）：</label>
      <input v-model="album.my_score" type="number" step="0.1" min="0" max="10" placeholder="如：8.5">
    </div>
    <!-- 按钮区 -->
    <div class="btn-group">
      <button @click="submitAlbum">提交专辑</button>
      <button @click="goBack" class="cancel-btn">取消</button>
    </div>
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
  </div>
</template>

<script>
export default {
  name: 'AddAlbum',
  data() {
    return {
      // 改回后端实际字段
      album: {
        album_name: "",
        cover_img: "",  // 改回cover_img
        singer: "",
        release_year: "",
        main_type: "",  // 后端必填字段
        tags: [],
        my_score: 0.0
      },
      tagInput: "",
      errorMsg: "",
      isUploading: false
    };
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
    }
  },
  methods: {
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
          this.album.cover_img = res.data.data.img_url; // 改回cover_img
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
    submitAlbum() {
      this.errorMsg = "";
      // 处理标签
      this.album.tags = this.tagInput ? this.tagInput.split(',').map(tag => tag.trim()) : [];
      // 校验后端必填字段
      if (!this.album.album_name || !this.album.singer || !this.album.release_year || !this.album.main_type) {
        this.errorMsg = "专辑名、歌手、发行年份、主类型不能为空！";
        return;
      }
      // 调用后端实际添加接口
      this.$axios({
        url: "/api/album/add",
        method: "POST",
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: this.album
      })
          .then(res => {
            if (res.data.code === 200) {
              alert("专辑添加成功！");
              // 【可选优化】让用户选择跳回哪里
              const goToPool = confirm("是否返回专辑搜索池？");
              if (goToPool) {
                this.$router.push("/album-pool"); // 跳回搜索池
              } else {
                this.$router.push("/music"); // 跳回我的专辑列表
              }
              // 如果不想加选择逻辑，保持原有代码即可：
              // this.$router.push("/music");
            } else {
              this.errorMsg = res.data.msg;
            }
          })
          .catch(err => {
            console.error("添加专辑失败：", err);
            this.errorMsg = "添加失败，请检查后端是否启动！";
          });
    },
    goBack() {
      // 【核心修改点1】取消按钮从跳回/music改为跳回/album-pool
      this.$router.push("/album-pool");
      // 如果想保留原有逻辑（跳回我的专辑），就用下面这行：
      // this.$router.push("/music");
    }
  }
};
</script>

<style scoped>
/* 样式部分完全不变，无需修改 */
.add-album-container {
  width: 500px;
  margin: 50px auto;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.form-item {
  margin: 15px 0;
  text-align: left;
}

.form-item label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
}

.form-item input {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
  border: 1px solid #ddd;
  border-radius: 4px;
}

/* 新增：图片上传区域样式 */
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
}

.upload-area:hover {
  border-color: #42b983;
}

/* 封面预览图样式 */
.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain; /* 保持图片比例，不拉伸 */
}

.btn-group {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-group button {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-group button:first-child {
  background: #42b983;
  color: white;
}

.cancel-btn {
  background: #999;
  color: white;
}

.error-tip {
  color: red;
  margin-top: 10px;
  text-align: center;
}
</style>