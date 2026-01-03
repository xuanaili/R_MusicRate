<template>
  <div class="search-pool-container">
    <!-- 提示文案：明确告知用户默认展示规则 -->
    <div class="tip-text">
      <i class="el-icon-info"></i> 专辑搜索池（所有用户的专辑副本）
    </div>

    <!-- 顶部操作区：新增专辑按钮 + 排序 + 每页条数 【和MusicList完全对齐】 -->
    <div class="header-actions">
      <button @click="goAddOriginalAlbum" class="add-original-btn">新增原创专辑</button>

      <!-- 排序方式：下拉框形式，和MusicList保持一致 -->
      <div class="sort-container">
        <label>排序方式：</label>
        <select v-model="sortBy" @change="getSearchResult">
          <option value="create_time">创建时间</option>
          <option value="release_year">发行年份</option>
          <option value="album_name">专辑名</option>
          <option value="singer">歌手</option>
        </select>
        <select v-model="sortOrder" @change="getSearchResult">
          <option value="asc">升序</option>
          <option value="desc">降序</option>
        </select>
      </div>

      <!-- 每页条数切换，和MusicList一致 -->
      <div class="page-size-container">
        <label>每页显示：</label>
        <select v-model="pageSize" @change="resetPageAndGetResult">
          <option value="5">5条</option>
          <option value="10">10条</option>
          <option value="20">20条</option>
          <option value="50">50条</option>
        </select>
      </div>
    </div>

    <!-- 两个独立的搜索区域，分开搜索专辑名歌手 + 标签 -->
    <div class="search-area-wrap">
      <div class="search-area">
        <input
          v-model="nameSingerKeyword"
          type="text"
          placeholder="搜索专辑名/歌手..."
          class="search-input"
          @keyup.enter="searchByNameSinger"
        >
        <button @click="searchByNameSinger" class="search-btn">专辑/歌手搜索</button>
        <button v-if="nameSingerKeyword" @click="clearNameSingerSearch" class="clear-btn">清空</button>
      </div>
      <div class="search-area">
        <input
          v-model="tagKeyword"
          type="text"
          placeholder="搜索标签（摇滚/华语/怀旧等）..."
          class="search-input"
          @keyup.enter="searchByTag"
        >
        <button @click="searchByTag" class="search-btn tag-search-btn">标签搜索</button>
        <button v-if="tagKeyword" @click="clearTagSearch" class="clear-btn">清空</button>
      </div>
    </div>

    <!-- 统一重置按钮 -->
    <div class="action-btns">
      <button @click="resetSearch" class="reset-btn">重置所有搜索条件</button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="searchResult.length === 0" class="empty-tip">
      {{ hasSearchKeyword ? '未找到匹配的专辑副本' : '暂无专辑副本数据' }}
    </div>
    <div v-else class="album-pool-list">
      <AlbumPoolItem
        v-for="album in searchResult"
        :key="album.id"
        :album="album"
        :is-admin="isAdmin"
        @copy-album="copyAlbum"
        @view-detail="viewAlbumDetail"
        @delete-album="deletePoolAlbum"
      />
    </div>

    <!-- ✅ 分页永久显示：首页/上一页/页码/下一页/尾页 + 跳转功能【完全显示】 -->
    <div class="pagination" v-show="pagination.total > 0">
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
      <!-- 跳转页码功能 -->
      <div class="jump-page">
        <input
          type="number"
          v-model="jumpPageNum"
          min="1"
          :max="pagination.total_pages"
          placeholder="页码"
          class="page-input"
        >
        <button @click="jumpToPage()" class="jump-btn">跳转</button>
      </div>
    </div>
  </div>
</template>

<script>
// 引入子组件
import AlbumPoolItem from '@/components/item/AlbumPoolItem.vue'

export default {
  name: 'SearchAlbumPool',
  components: { AlbumPoolItem },
  data() {
    return {
      nameSingerKeyword: '',  // 专辑名/歌手 搜索关键词
      tagKeyword: '',         // 标签 搜索关键词
      searchResult: [],       // 搜索结果
      loading: false,         // 加载状态
      page: 1,                // 当前页
      pageSize: 10,           // 每页条数
      pagination: {           // 分页信息 核心：字段和后端完全一致
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      },
      isAdmin: false,         // 是否为管理员
      sortBy: 'create_time',  // 排序字段
      sortOrder: 'desc',      // 排序方式
      jumpPageNum: 1          // 跳转页码输入值
    }
  },
  computed: {
    // 判断是否有输入搜索关键词，用于空数据提示
    hasSearchKeyword() {
      return this.nameSingerKeyword.trim() || this.tagKeyword.trim()
    }
  },
  created() {
    // 检查登录状态
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    // 获取用户是否为管理员
    this.isAdmin = localStorage.getItem('is_admin') === '1';
    // 初始化加载数据
    this.getSearchResult();
  },
  methods: {
    // 统一请求数据入口方法，判断走哪个搜索接口
    getSearchResult() {
      this.tagKeyword.trim() ? this.searchByTag() : this.searchByNameSinger();
    },

    // 核心方法1：按【专辑名/歌手】搜索 ✅修复全部bug
// 核心方法1：按【专辑名/歌手】搜索 ✅修复分页取值逻辑
searchByNameSinger() {
  this.loading = true;
  this.$axios({
    url: '/api/album/pool/search/name-singer',
    method: 'GET',
    headers: {
      'Authorization': localStorage.getItem('token') || '',
    },
    params: {
      keyword: this.nameSingerKeyword.trim(),
      page: this.page,
      page_size: this.pageSize,
      sort_field: this.sortBy,
      sort_order: this.sortOrder
    }
  })
  .then(res => {
    this.loading = false;
    if (res.data.code === 200) {
      this.searchResult = res.data.data.list || [];
      // ✅ 关键修复：直接取后端返回的完整分页数据，无需计算
      this.pagination = res.data.data.pagination || {
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      };
      this.jumpPageNum = this.pagination.page; // 同步跳转框页码
    } else {
      alert('专辑/歌手搜索失败：' + res.data.msg);
      this.searchResult = [];
    }
  })
  .catch(err => {
    this.loading = false;
    console.error('专辑/歌手搜索失败：', err);
    alert('搜索失败，请检查后端是否启动！');
  });
},

    // 核心方法2：按【标签】搜索 ✅修复全部bug
// 核心方法2：按【标签】搜索 ✅修复分页取值逻辑
searchByTag() {
  this.loading = true;
  this.$axios({
    url: '/api/album/pool/search/tags',
    method: 'GET',
    headers: {
      'Authorization': localStorage.getItem('token') || '',
    },
    params: {
      tag: this.tagKeyword.trim(),
      page: this.page,
      page_size: this.pageSize,
      sort_field: this.sortBy,
      sort_order: this.sortOrder
    }
  })
  .then(res => {
    this.loading = false;
    if (res.data.code === 200) {
      this.searchResult = res.data.data.list || [];
      // ✅ 关键修复：直接取后端返回的完整分页数据，无需计算
      this.pagination = res.data.data.pagination || {
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      };
      this.jumpPageNum = this.pagination.page; // 同步跳转框页码
    } else {
      alert('标签搜索失败：' + res.data.msg);
      this.searchResult = [];
    }
  })
  .catch(err => {
    this.loading = false;
    console.error('标签搜索失败：', err);
    alert('搜索失败，请检查后端是否启动！');
  });
},
    // 清空专辑名/歌手搜索
    clearNameSingerSearch() {
      this.nameSingerKeyword = '';
      this.page = 1;
      this.getSearchResult();
    },

    // 清空标签搜索
    clearTagSearch() {
      this.tagKeyword = '';
      this.page = 1;
      this.getSearchResult();
    },

    // 重置所有搜索条件
    resetSearch() {
      this.nameSingerKeyword = '';
      this.tagKeyword = '';
      this.page = 1;
      this.sortBy = 'create_time';
      this.sortOrder = 'desc';
      this.getSearchResult();
    },

    // 切换每页条数时重置页码为1
    resetPageAndGetResult() {
      this.page = 1;
      this.getSearchResult();
    },

    // 切换页码
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) return;
      this.page = newPage;
      this.getSearchResult();
    },

    // 跳转指定页码 完整功能
    jumpToPage() {
      const num = parseInt(this.jumpPageNum);
      if (isNaN(num) || num < 1 || num > this.pagination.total_pages) {
        alert(`请输入1-${this.pagination.total_pages}之间的有效页码！`);
        this.jumpPageNum = this.pagination.page;
        return;
      }
      this.changePage(num);
    },

    // 复制专辑
    copyAlbum(albumId) {
      if (!confirm('确定要复制该专辑为你的副本吗？')) return;
      this.$axios({
        url: `/api/album/pool/copy/${albumId}`,
        method: 'POST',
        headers: { 'Authorization': localStorage.getItem('token') || '' }
      })
      .then(res => {
        res.data.code === 200
          ? (alert('复制成功！已添加到你的专辑列表'), this.$router.push(`/albumDetail`))
          : alert('复制失败：' + res.data.msg);
      })
      .catch(err => {
        console.error('复制专辑失败：', err);
        alert('复制失败！' + err.message);
      });
    },

    // 查看详情
    viewAlbumDetail(poolId) {
      this.$router.push(`/album/pool/detail/${poolId}`);
    },

    // 删除专辑（仅管理员）
    deletePoolAlbum(poolId) {
      if (!this.isAdmin) return alert('无权限执行此操作！');
      if (!confirm('确定要删除该专辑吗？删除后不可恢复！')) return;
      this.$axios({
        url: `/api/album/pool/delete/${poolId}`,
        method: 'DELETE',
        headers: { 'Authorization': localStorage.getItem('token') || '' }
      })
      .then(res => {
        if (res.data.code === 200) {
          alert('删除成功！');
          this.getSearchResult();
        } else {
          alert('删除失败：' + res.data.msg);
        }
      })
      .catch(err => {
        console.error('删除专辑失败：', err);
        alert('删除失败！' + (err.response?.data?.msg || err.message));
      });
    },

    // 新增原创专辑
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

.tip-text {
  color: #666;
	font-size: 14px;
	margin-bottom: 15px;
	padding: 8px 12px;
	background-color: #f5fafe;
	border-left: 3px solid #42b983;
	border-radius: 4px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}
.sort-container, .page-size-container {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sort-container select, .page-size-container select {
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-area-wrap {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.search-area {
  display: flex;
  gap: 10px;
  align-items: center;
  flex: 1;
  min-width: 300px;
}
.search-input {
  flex: 1;
	padding: 8px 12px;
	border: 1px solid #ddd;
	border-radius: 4px;
	font-size: 14px;
}
.clear-btn {
  padding: 8px 12px;
	background: #999;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}
.search-btn {
  padding: 8px 20px;
	background: #42b983;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}
.tag-search-btn {
  background: #007acc;
}

.action-btns {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
  align-items: center;
}
.add-original-btn {
  padding: 8px 20px;
	background: #007acc;
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

.loading-tip, .empty-tip {
  text-align: center;
	color: #666;
	padding: 30px 0;
}
.album-pool-list {
  margin-top: 20px;
}

/* ✅ 分页样式【强制生效】 完全和MusicList一致，必显样式 */
.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  flex-wrap: wrap;
  width: 100%;
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
.page-btn:hover:not(:disabled) {
  background: #f0f8fb;
  border-color: #42b983;
}
.page-info {
  color: #666;
  font-size: 14px;
}
.jump-page {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-input {
  width: 60px;
	padding: 6px 8px;
	border: 1px solid #ddd;
	border-radius: 4px;
}
.jump-btn {
  padding: 6px 12px;
  background: #42b983;
  color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}
</style>