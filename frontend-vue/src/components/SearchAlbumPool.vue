<template>
  <div class="search-pool-container">
    <h2>专辑搜索池（所有用户的专辑副本）</h2>
    
    <!-- 搜索区域 -->
    <div class="search-area">
      <input 
        v-model="searchKeyword" 
        type="text" 
        placeholder="搜索专辑名/歌手/标签..." 
        class="search-input"
      >
      <button @click="searchAlbums" class="search-btn">搜索</button>
      <button @click="resetSearch" class="reset-btn">重置</button>
    </div>

    <!-- 操作按钮 -->
    <div class="action-btns">
      <button @click="goAddOriginalAlbum" class="add-original-btn">新增原创专辑</button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="searchResult.length === 0" class="empty-tip">
      {{ searchKeyword ? '未找到匹配的专辑副本' : '暂无专辑副本数据' }}
    </div>
    <div v-else class="album-pool-list">
      <div v-for="album in searchResult" :key="album.id" class="album-pool-item">
        <div class="album-info">
          <img v-if="album.cover_img" :src="album.cover_img" alt="封面" class="pool-cover">
          <div class="pool-info">
            <h4>{{ album.album_name }}</h4>
            <p>歌手：{{ album.singer }}</p>
            <p>发行年份：{{ album.release_year }}</p>
            <p>标签：{{ album.tags?.join('、') || '无' }}</p>
            <p>创建用户：{{ album.create_user || '未知' }}</p>
          </div>
        </div>
        <div class="pool-actions">
          <button @click="copyAlbum(album.id)" class="copy-btn">复制为我的副本</button>
          <button @click="viewAlbumDetail(album.id)" class="detail-btn">查看详情</button>
        </div>
      </div>
    </div>

    <!-- 分页控件 -->
    <div v-if="pagination.total > 0" class="pagination">
      <button 
        @click="changePage(1)" 
        :disabled="pagination.page === 1 || loading"
        class="page-btn"
      >首页</button>
      <button 
        @click="changePage(pagination.page - 1)" 
        :disabled="pagination.page === 1 || loading"
        class="page-btn"
      >上一页</button>
      <span class="page-info">
        第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页 (总 {{ pagination.total }} 条)
      </span>
      <button 
        @click="changePage(pagination.page + 1)" 
        :disabled="pagination.page === pagination.total_pages || loading"
        class="page-btn"
      >下一页</button>
      <button 
        @click="changePage(pagination.total_pages)" 
        :disabled="pagination.page === pagination.total_pages || loading"
        class="page-btn"
      >尾页</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SearchAlbumPool',
  data() {
    return {
      searchKeyword: '',      // 搜索关键词
      searchResult: [],       // 搜索结果
      loading: false,         // 加载状态
      page: 1,                // 当前页
      pageSize: 10,           // 每页条数
      pagination: {           // 分页信息
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      }
    }
  },
  created() {
    // 检查登录状态
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    // 初始化加载所有专辑副本
    this.searchAlbums();
  },
  methods: {
    // 搜索专辑副本（支持关键词+分页）
    searchAlbums() {
      this.loading = true;
      this.$axios({
        url: '/api/album/pool/search',
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        params: {
          keyword: this.searchKeyword.trim(),
          page: this.page,
          page_size: this.pageSize
        }
      })
      .then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          this.searchResult = res.data.data.list || [];
          this.pagination = res.data.data.pagination || {
            total: 0,
            page: 1,
            page_size: 10,
            total_pages: 0
          };
        } else {
          alert('搜索失败：' + res.data.msg);
          this.searchResult = [];
        }
      })
      .catch(err => {
        this.loading = false;
        console.error('搜索专辑池失败：', err);
        alert('搜索失败，请检查后端是否启动！');
      });
    },


    // 重置搜索
    resetSearch() {
      this.searchKeyword = '';
      this.page = 1;
      this.searchAlbums();
    },

    // 切换页码
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) {
        return;
      }
      this.page = newPage;
      this.searchAlbums();
    },

    // 复制专辑为我的副本
    copyAlbum(albumId) {
      if (!confirm('确定要复制该专辑为你的副本吗？')) {
        return;
      }
      this.$axios({
        url: `/api/album/pool/copy/${albumId}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        }
      })
      .then(res => {
        if (res.data.code === 200) {
          alert('复制成功！已添加到你的专辑列表');
          // 复制成功后跳回我的专辑列表
          this.$router.push('/music');
        } else {
          alert('复制失败：' + res.data.msg);
        }
      })
      .catch(err => {
        console.error('复制专辑失败：', err);
        alert('复制失败！' + err.message);
      });
    },

    // SearchAlbumPool.vue 的 methods 中
    viewAlbumDetail(poolId) {
  // 跳转到公共专辑详情页，传递poolId（album_pool表的ID）
  this.$router.push(`/album/pool/detail/${poolId}`);
},

    // 跳转到新增原创专辑页面
    goAddOriginalAlbum() {
      this.$router.push('/add-album');
    }
  }
};
</script>

<style scoped>
.search-pool-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.search-area {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-btn {
  padding: 8px 20px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.reset-btn {
  padding: 8px 20px;
  background: #999;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.action-btns {
  margin-bottom: 20px;
}

.add-original-btn {
  padding: 8px 20px;
  background: #007acc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.loading-tip, .empty-tip {
  text-align: center;
  color: #666;
  padding: 30px 0;
}

.album-pool-list {
  margin-top: 20px;
}

.album-pool-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 8px;
  margin-bottom: 15px;
  background: #f9f9f9;
}

.album-info {
  display: flex;
  gap: 15px;
  align-items: center;
  flex: 1;
}

.pool-cover {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
}

.pool-info {
  flex: 1;
}

.pool-info h4 {
  margin: 0 0 8px 0;
  color: #333;
}

.pool-info p {
  margin: 4px 0;
  color: #666;
  font-size: 14px;
}

.pool-actions {
  display: flex;
  gap: 10px;
}

.copy-btn {
  padding: 6px 12px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.detail-btn {
  padding: 6px 12px;
  background: #007acc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* 分页样式 */
.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  flex-wrap: wrap;
}

.page-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.page-btn:disabled {
  background: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.page-info {
  color: #666;
  font-size: 14px;
}
</style>