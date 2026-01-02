<template>
  <div class="search-pool-container">
    <h2>专辑搜索池（所有用户的专辑副本）</h2>

    <!-- 🔴 新增提示文案：明确告知用户默认展示规则 -->
    <div class="tip-text">
      <i class="el-icon-info"></i> 无搜索条件时，默认展示 <b>最近添加的10张专辑</b> | 输入关键词可查看全部匹配结果
    </div>

    <!-- 两个独立的搜索区域，分开搜索专辑名歌手 + 标签 -->
    <div class="search-area-wrap">
      <!-- 第一个搜索框：专辑名 / 歌手 搜索 -->
      <div class="search-area">
        <input
          v-model="nameSingerKeyword"
          type="text"
          placeholder="搜索专辑名/歌手..."
          class="search-input"
        >
        <button @click="searchByNameSinger" class="search-btn">专辑/歌手搜索</button>
      </div>

      <!-- 第二个搜索框：标签 专属搜索 -->
      <div class="search-area">
        <input
          v-model="tagKeyword"
          type="text"
          placeholder="搜索标签（摇滚/华语/怀旧等）..."
          class="search-input"
        >
        <button @click="searchByTag" class="search-btn tag-search-btn">标签搜索</button>
      </div>
    </div>

    <!-- ✅✅✅ 新增：排序按钮区域 -->
    <div class="sort-area">
      <span class="sort-title">排序方式：</span>
      <button
        v-for="item in sortOptions"
        :key="item.field"
        @click="changeSort(item.field)"
        :class="['sort-btn', currentSort.field === item.field ? 'active' : '']"
      >
        {{ item.name }}
        <span class="sort-icon">{{ currentSort.field === item.field ? (currentSort.order === 'asc' ? '↑' : '↓') : '' }}</span>
      </button>
      <span class="current-sort-text" v-if="currentSort">
        当前排序：{{ getSortName(currentSort.field) }} {{ currentSort.order === 'asc' ? '升序' : '降序' }}
      </span>
    </div>

    <!-- 操作按钮 + 统一重置按钮 -->
    <div class="action-btns">
      <button @click="goAddOriginalAlbum" class="add-original-btn">新增原创专辑</button>
      <button @click="resetSearch" class="reset-btn">重置所有搜索条件</button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="searchResult.length === 0" class="empty-tip">
      {{ hasSearchKeyword ? '未找到匹配的专辑副本' : '暂无专辑副本数据' }}
    </div>
    <div v-else class="album-pool-list">
      <!-- 核心：引入封装的子组件，循环传参 + 监听事件 -->
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

    <!-- 只有输入搜索条件时，才显示分页 -->
    <div v-if="hasSearchKeyword && pagination.total > 0" class="pagination">
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
      pagination: {           // 分页信息
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      },
      isAdmin: false,         // 是否为管理员
      // ✅✅✅ 新增：排序配置
      sortOptions: [
        { field: 'create_time', name: '创建时间' },
        { field: 'release_year', name: '发行年份' },
        { field: 'album_name', name: '专辑名' },
        { field: 'singer', name: '歌手' }
      ],
      currentSort: {
        field: 'create_time', // 默认排序字段
        order: 'desc'         // 默认排序方式：倒序 (最新优先)
      }
    }
  },
  computed: {
    // 判断是否有输入搜索关键词，用于空数据提示、分页显示、搜索逻辑判断
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
    // 初始化加载【最新10条】专辑副本
    this.searchByNameSinger();
  },
  methods: {
    // ✅✅✅ 新增：获取排序名称
    getSortName(field) {
      const item = this.sortOptions.find(item => item.field === field);
      return item ? item.name : '创建时间';
    },

    // ✅✅✅ 新增：切换排序方式（点击同一字段切换正序/倒序）
    changeSort(field) {
      if (this.currentSort.field === field) {
        // 同一字段，切换排序方向
        this.currentSort.order = this.currentSort.order === 'asc' ? 'desc' : 'asc';
      } else {
        // 不同字段，默认倒序，创建时间默认倒序，其他默认正序
        this.currentSort.field = field;
        this.currentSort.order = field === 'create_time' ? 'desc' : 'asc';
      }
      // 排序后重置页码为1
      this.page = 1;
      // 重新请求数据
      if(this.tagKeyword.trim()){
        this.searchByTag()
      }else{
        this.searchByNameSinger()
      }
    },

    // 核心方法1：按【专辑名/歌手】搜索，调用后端专属接口 + ✅新增排序参数
    searchByNameSinger() {
      this.loading = true;
      this.$axios({
        url: '/api/album/pool/search/name-singer',
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        params: {
          keyword: this.nameSingerKeyword.trim(),
          page: this.hasSearchKeyword ? this.page : 1,
          page_size: this.hasSearchKeyword ? this.pageSize : 10,
          sort_field: this.currentSort.field,
          sort_order: this.currentSort.order
        }
      })
      .then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          this.searchResult = res.data.data.list || [];
          this.pagination = {
            total: res.data.data.total || 0,
            page: res.data.data.page || 1,
            page_size: res.data.data.page_size || 10,
            total_pages: Math.ceil((res.data.data.total || 0) / (res.data.data.page_size || 10))
          };
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

    // 核心方法2：按【标签】搜索，调用后端专属接口 + ✅新增排序参数
    searchByTag() {
      this.loading = true;
      this.$axios({
        url: '/api/album/pool/search/tags',
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        params: {
          tag: this.tagKeyword.trim(),
          page: this.hasSearchKeyword ? this.page : 1,
          page_size: this.hasSearchKeyword ? this.pageSize : 10,
          sort_field: this.currentSort.field,
          sort_order: this.currentSort.order
        }
      })
      .then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          this.searchResult = res.data.data.list || [];
          this.pagination = {
            total: res.data.data.total || 0,
            page: res.data.data.page || 1,
            page_size: res.data.data.page_size || 10,
            total_pages: Math.ceil((res.data.data.total || 0) / (res.data.data.page_size || 10))
          };
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

    // 重置所有搜索条件：清空两个输入框、页码归1、恢复默认排序、加载【最新10条】
    resetSearch() {
      this.nameSingerKeyword = '';
      this.tagKeyword = '';
      this.page = 1;
      this.currentSort = { field: 'create_time', order: 'desc' };
      this.searchByNameSinger();
    },

    // 切换页码：只在【有搜索条件】时生效，保留排序条件
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page || !this.hasSearchKeyword) {
        return;
      }
      this.page = newPage;
      if(this.tagKeyword.trim()){
        this.searchByTag()
      }else{
        this.searchByNameSinger()
      }
    },

    // 复制专辑
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
          this.$router.push(`/albumDetail`);
        } else {
          alert('复制失败：' + res.data.msg);
        }
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
      if (!this.isAdmin) {
        alert('无权限执行此操作！');
        return;
      }
      if (!confirm('确定要删除该专辑吗？删除后不可恢复！')) {
        return;
      }
      this.$axios({
        url: `/api/album/pool/delete/${poolId}`,
        method: 'DELETE',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        }
      })
      .then(res => {
        if (res.data.code === 200) {
          alert('删除成功！');
          if(this.tagKeyword.trim()){
            this.searchByTag()
          }else{
            this.searchByNameSinger()
          }
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

h2 {
  margin-bottom: 10px;
}

/* 🔴 新增提示文案样式 */
.tip-text {
  color: #666;
  font-size: 14px;
  margin-bottom: 15px;
  padding: 8px 12px;
  background-color: #f5fafe;
  border-left: 3px solid #42b983;
  border-radius: 4px;
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

/* ✅✅✅ 新增：排序按钮样式 */
.sort-area {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  padding: 10px;
  background: #f9f9f9;
  border-radius: 4px;
}
.sort-title {
  color: #666;
  font-size: 14px;
  font-weight: 500;
}
.sort-btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}
.sort-btn.active {
  background: #42b983;
  color: #fff;
  border-color: #42b983;
}
.sort-icon {
  margin-left: 4px;
  font-size: 12px;
}
.current-sort-text {
  margin-left: 15px;
  color: #999;
  font-size: 13px;
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