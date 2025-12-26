<template>
  <div class="edit-album-container">
    <h2>修改公共专辑模板</h2>

    <!-- ========== 核心新增：同步结果提示 ========== -->
    <div v-if="syncResult" class="sync-result">
      <div class="sync-result-title">🔍 修改同步结果</div>
      <div class="sync-result-content">
        {{ syncResult.msg }}
        <span v-if="syncResult.data?.sync_count" class="sync-count">
          （同步更新了 {{ syncResult.data.sync_count }} 条用户数据）
        </span>
      </div>
    </div>
    <!-- ========== 同步结果提示结束 ========== -->

    <!-- 表单区域 -->
    <div class="album-form">
      <!-- 专辑名 -->
      <div class="form-item">
        <label>专辑名：</label>
        <input
          v-model="albumForm.album_name"
          type="text"
          placeholder="请输入专辑名"
          class="form-input"
          required
        >
      </div>

      <!-- 歌手 -->
      <div class="form-item">
        <label>歌手：</label>
        <input
          v-model="albumForm.singer"
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
          v-model="albumForm.release_year"
          type="number"
          placeholder="请输入发行年份"
          class="form-input"
        >
      </div>

      <!-- 封面图片 -->
      <div class="form-item">
        <label>封面图片：</label>
        <div class="upload-area">
          <input
            type="file"
            accept="image/*"
            @change="uploadCover"
            class="file-input"
          >
          <div v-if="albumForm.cover_img" class="preview-img">
            <img :src="albumForm.cover_img" alt="封面预览">
          </div>
          <div v-else class="no-preview">暂无封面</div>
        </div>
      </div>

      <!-- 标签 -->
      <div class="form-item">
        <label>标签（多个用逗号分隔）：</label>
        <input
          v-model="tagInput"
          type="text"
          placeholder="例如：流行,华语,2020"
          class="form-input"
        >
      </div>

      <!-- ========== 新增：同步说明提示 ========== -->
      <div class="sync-tips">
        📌 温馨提示：修改后会自动同步到「开启同步且未自定义修改」的用户专辑，已自定义的用户专辑不会被覆盖。
      </div>
      <!-- ========== 同步说明结束 ========== -->

      <!-- 操作按钮 -->
      <div class="form-actions">
        <button @click="submitEdit" class="submit-btn" :disabled="loading">
          <span v-if="loading">保存中...</span>
          <span v-else>保存修改</span>
        </button>
        <button @click="goBack" class="cancel-btn" :disabled="loading">取消</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EditPoolAlbum',
  data() {
    return {
      albumId: '', // 公共专辑ID
      albumForm: {
        album_name: '',
        singer: '',
        release_year: '',
        cover_img: '',
        tags: []
      },
      tagInput: '', // 标签输入框（逗号分隔）
      loading: false,
      // ========== 核心新增：同步结果数据 ==========
      syncResult: null // 存储同步结果
      // ========== 同步结果数据结束 ==========
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
    // 获取原有专辑数据
    getAlbumData() {
      this.loading = true;
      this.$axios({
        url: `/api/album/pool/detail/${this.albumId}`,
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || ''
        }
      })
      .then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          const data = res.data.data;
          this.albumForm = {
            album_name: data.album_name || '',
            singer: data.singer || '',
            release_year: data.release_year || '',
            cover_img: data.cover_img || '',
            tags: data.tags || []
          };
          // 标签数组转逗号分隔字符串
          this.tagInput = this.albumForm.tags.join(',');
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

    // 上传封面图片
    uploadCover(e) {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      this.$axios({
        url: '/api/upload_img',
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'multipart/form-data'
        },
        data: formData
      })
      .then(res => {
        if (res.data.code === 200) {
          this.albumForm.cover_img = res.data.data.url;
          alert('封面上传成功！');
        } else {
          alert('封面上传失败：' + res.data.msg);
        }
      })
      .catch(err => {
        console.error('上传封面失败：', err);
        alert('上传封面失败！');
      });
    },

    // 提交修改
    submitEdit() {
      // 验证必填项
      if (!this.albumForm.album_name || !this.albumForm.singer) {
        alert('专辑名和歌手为必填项！');
        return;
      }

      // 处理标签（字符串转数组）
      this.albumForm.tags = this.tagInput.split(',').map(tag => tag.trim()).filter(tag => tag);

      this.loading = true;
      this.syncResult = null; // 清空之前的同步结果
      this.$axios({
        url: `/api/album/pool/update/${this.albumId}`,
        method: 'PUT',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: this.albumForm
      })
      .then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          // ========== 核心新增：存储同步结果 ==========
          this.syncResult = res.data;
          // ========== 存储同步结果结束 ==========

          // 优化提示：显示同步数量
          const syncCount = res.data.data?.sync_count || 0;
          alert(`修改专辑成功！\n已同步更新 ${syncCount} 条用户数据（仅同步开启且未自定义的专辑）`);

          // 跳回专辑详情页
          this.$router.push(`/album/pool/detail/${this.albumId}`);
        } else {
          alert('修改失败：' + res.data.msg);
        }
      })
      .catch(err => {
        this.loading = false;
        console.error('修改专辑失败：', err);
        alert('修改失败！' + (err.response?.data?.msg || err.message));
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
.edit-album-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
.album-form {
  margin-top: 30px;
  border: 1px solid #eee;
  padding: 20px;
  border-radius: 8px;
  background: #f9f9f9;
}
.form-item {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.form-item label {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}
.form-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}
.upload-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.file-input {
  padding: 5px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.preview-img {
  width: 150px;
  height: 150px;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
}
.preview-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.no-preview {
  width: 150px;
  height: 150px;
  border: 1px dashed #ddd;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 12px;
}
.form-actions {
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-top: 30px;
}
.submit-btn {
  padding: 8px 30px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.cancel-btn {
  padding: 8px 30px;
  background: #999;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
/* 禁用状态样式 */
.submit-btn:disabled, .cancel-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* ========== 核心新增：同步结果样式 ========== */
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

/* ========== 同步提示样式 ========== */
.sync-tips {
  margin-bottom: 20px;
  padding: 10px;
  border-radius: 4px;
  background-color: #f8f9fa;
  color: #666;
  font-size: 12px;
  line-height: 1.5;
}
/* ========== 新增样式结束 ========== */
</style>