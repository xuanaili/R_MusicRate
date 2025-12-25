<template>
  <div class="add-album-container">
    <h2>添加新专辑</h2>
    <!-- 专辑名 -->
    <div class="form-item">
      <label>专辑名：</label>
      <input v-model="album.album_name" type="text" placeholder="请输入专辑名">
    </div>
    <!-- 封面图片（先输入链接，后续可扩展上传） -->
    <div class="form-item">
      <label>封面图片链接：</label>
      <input v-model="album.cover_img" type="text" placeholder="可选：输入图片URL">
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
      errorMsg: ""
    };
  },
  created() {
    // 检查登录状态，没登录跳登录页
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
    }
  },
  methods: {
    // 提交专辑
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
    // 返回专辑列表页
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