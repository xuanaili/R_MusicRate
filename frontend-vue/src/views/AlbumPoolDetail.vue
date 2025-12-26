<template>
  <div class="pool-detail-container">
    <h2>公共专辑详情</h2>
    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="!albumData" class="empty-tip">未找到该公共专辑</div>
    <div v-else class="album-detail">
      <div class="cover">
        <img v-if="albumData.cover_img" :src="albumData.cover_img" alt="封面" class="detail-cover">
        <div v-else class="no-cover">暂无封面</div>
      </div>
      <div class="info">
        <h3>{{ albumData.album_name }}</h3>
        <p>歌手：{{ albumData.singer }}</p>
        <p>发行年份：{{ albumData.release_year }}</p>
        <p>标签：{{ albumData.tags?.join('、') || '无' }}</p>
        <p>创建用户：{{ albumData.create_user_name || '未知' }}</p>
        <p>创建时间：{{ albumData.create_time || '未知' }}</p>
      </div>
      <div class="actions">
        <button @click="copyAlbum" class="copy-btn">复制为我的副本</button>
        <button @click="goBack" class="back-btn">返回搜索池</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumPoolDetail',
  data() {
    return {
      albumData: null,
      loading: false
    }
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    // 获取URL中的poolId
    const poolId = this.$route.params.poolId;
    this.getPoolAlbumDetail(poolId);
  },
  methods: {
    // 获取公共专辑详情
    getPoolAlbumDetail(poolId) {
      this.loading = true;
      this.$axios({
        url: `/api/album/pool/detail/${poolId}`,
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || ''
        }
      })
      .then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          this.albumData = res.data.data;
        } else {
          alert('获取详情失败：' + res.data.msg);
        }
      })
      .catch(err => {
        this.loading = false;
        console.error('获取公共专辑详情失败：', err);
        alert('获取详情失败！');
      });
    },
    // 复制为我的副本
    copyAlbum() {
      if (!confirm('确定复制该公共专辑为你的私有副本吗？')) return;
      this.$axios({
        url: `/api/album/pool/copy/${this.$route.params.poolId}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || ''
        }
      })
      .then(res => {
        if (res.data.code === 200) {
          alert('复制成功！跳转到我的专辑列表');
          this.$router.push('/music');
        } else {
          alert('复制失败：' + res.data.msg);
        }
      })
      .catch(err => {
        console.error('复制失败：', err);
        alert('复制失败！');
      });
    },
    // 返回搜索池
    goBack() {
      this.$router.push('/album-pool');
    }
  }
};
</script>

<style scoped>
.pool-detail-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}
.loading-tip, .empty-tip {
  text-align: center;
  color: #666;
  padding: 30px 0;
}
.album-detail {
  margin-top: 20px;
}
.cover {
  width: 200px;
  height: 200px;
  margin: 0 auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.detail-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.no-cover {
  color: #999;
  font-size: 14px;
}
.info {
  margin-top: 20px;
  text-align: center;
}
.info h3 {
  font-size: 20px;
  color: #333;
}
.info p {
  margin: 8px 0;
  color: #666;
}
.actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 20px;
}
.copy-btn {
  padding: 8px 20px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.back-btn {
  padding: 8px 20px;
  background: #999;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>