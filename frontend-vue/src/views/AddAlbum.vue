<template>
  <div class="add-album-container">
    <h2>添加新专辑</h2>
    <!-- 专辑名 -->
    <div class="form-item">
      <label>专辑名：</label>
      <input v-model="album.album_name" type="text" placeholder="请输入专辑名">
    </div>
    <!-- 封面图片：新增上传区域 + 保留手动URL输入 -->
    <div class="form-item">
      <label>封面图片：</label>
      <!-- 拖拽/点击上传区域 -->
      <div
        class="upload-area"
        @drop="handleDrop"
        @dragover="handleDragOver"
        @click="chooseFile"
      >
        <span v-if="!album.cover_img">拖拽图片到这里，或点击上传</span>
        <img v-else :src="album.cover_img" class="preview-img" alt="封面预览">
      </div>
      <!-- 隐藏的文件选择框 -->
      <input type="file" ref="fileInput" accept="image/*" style="display: none" @change="handleFileChange">
      <!-- 保留手动输入URL -->
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
    <!-- 主要类型 -->
    <div class="form-item">
      <label>主要类型：</label>
      <input v-model="album.main_type" type="text" placeholder="如：流行、摇滚、民谣">
    </div>
    <!-- 标签（多个用逗号分隔） -->
    <div class="form-item">
      <label>标签（多个用逗号分隔）：</label>
      <input v-model="tagInput" type="text" placeholder="如：经典,华语,治愈">
    </div>
    <!-- 评分 -->
    <div class="form-item">
      <label>评分（0-10）：</label>
      <input v-model="album.score" type="number" step="0.1" min="0" max="10" placeholder="如：8.5">
    </div>
    <!-- 按钮区 -->
    <div class="btn-group">
      <button @click="submitAlbum">提交专辑</button>
      <button @click="goBack" class="cancel-btn">取消</button>
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
      // 专辑数据（和后端字段对应）
      album: {
        album_name: "",
        cover_img: "",
        singer: "",
        release_year: "",
        main_type: "",
        tags: [],
        score: 0.0
      },
      tagInput: "",  // 标签输入框（临时存储，提交时转数组）
      errorMsg: "",
      isUploading: false  // 上传中状态，防止重复上传
    };
  },
  created() {
    // 检查登录状态，没登录跳登录页
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
    }
  },
  methods: {
    // 1. 处理拖拽上传：阻止浏览器默认行为
    handleDragOver(e) {
      e.preventDefault();
    },
    // 2. 处理拖拽放下事件
    handleDrop(e) {
      e.preventDefault();
      if (this.isUploading) return; // 上传中不重复处理
      // 获取拖拽的图片文件
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        this.uploadToImgBed(file); // 上传到图床
      } else {
        this.errorMsg = "请拖拽有效的图片文件（jpg/png/webp）！";
      }
    },
    // 3. 点击上传：触发隐藏的文件选择框
    chooseFile() {
      this.$refs.fileInput.click();
    },
    // 4. 选择文件后触发
    handleFileChange(e) {
      if (this.isUploading) return;
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        this.uploadToImgBed(file);
        // 清空文件选择框（避免重复选择同一文件无反应）
        e.target.value = "";
      } else {
        this.errorMsg = "请选择有效的图片文件！";
      }
    },
    // 5. 核心：上传图片到imgBB图床（替换原有imgchr逻辑）
async uploadToImgBed(file) {
  this.isUploading = true;
  this.errorMsg = "";
  try {
    const formData = new FormData();
    formData.append('image', file); // 传给后端的图片文件
    // 只请求你的后端接口，不再直接请求imgBB
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
    // 辅助方法：文件转Base64（新增）
    fileToBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]); // 去掉Base64前缀
        reader.onerror = (err) => reject(err);
      });
    },
    // 提交专辑（原有逻辑不变）
    submitAlbum() {
      this.errorMsg = "";
      // 1. 处理标签：把逗号分隔的字符串转数组
      if (this.tagInput) {
        this.album.tags = this.tagInput.split(',').map(tag => tag.trim());
      } else {
        this.album.tags = [];
      }
      // 2. 校验必填字段（和后端对应）
      if (!this.album.album_name || !this.album.singer || !this.album.release_year || !this.album.main_type) {
        this.errorMsg = "专辑名、歌手、发行年份、主要类型不能为空！";
        return;
      }
      // 3. 调用后端添加专辑接口
      this.$axios.post("/api/album/add", this.album)
          .then(res => {
            if (res.data.code === 200) {
              alert("专辑添加成功！");
              this.$router.push("/music");  // 跳回专辑列表页
            } else {
              this.errorMsg = res.data.msg;
            }
          })
          .catch(err => {
            console.error("添加专辑失败：", err);
            this.errorMsg = "添加失败，请检查后端是否启动！";
          });
    },
    // 返回专辑列表页（原有逻辑）
    goBack() {
      this.$router.push("/music");
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