<template>
  <div class="container">
    <!-- ✅ 顶部操作区：和MusicList完全一致的一行式布局+毛玻璃蒙版 -->
    <div class="all-actions-wrapper">
      <!-- ✅✅✅ 核心修改1：修改新增按钮事件 → 打开侧边栏，不是跳转路由 -->
      <button v-if="isAdmin" @click="showAddAlbumSidebar = true" class="add-original-btn"><strong>新增</strong></button>

      <!-- 排序方式：下拉按钮(透明) + 下拉列表(0.25蒙版) 完全和MusicList一致 -->
      <div class="dropdown-btn-container">
        <button
          class="dropdown-btn"
          @click="toggleDropdown('sortBy')"
        >
          {{ sortByMap[sortBy] }}
          <span class="arrow-icon" :class="{active: dropdownShow.sortBy}">▼</span>
        </button>
        <ul class="dropdown-options" v-show="dropdownShow.sortBy">
          <li
            v-for="(label, key) in sortByMap"
            :key="key"
            @click="handleSortChange(key); toggleDropdown('sortBy')"
            :class="{active: sortBy === key}"
          >
            {{ label }}
          </li>
        </ul>
      </div>

      <!-- 升序/降序 保留原版按钮组样式 完全和MusicList一致不变 -->
      <div class="sort-options">
        <button
          class="tab-item sort-btn"
          :class="{active: sortOrder === 'asc'}"
          @click="handleOrderChange('asc')"
        >
          升序
        </button>
        <button
          class="tab-item sort-btn"
          :class="{active: sortOrder === 'desc'}"
          @click="handleOrderChange('desc')"
        >
          降序
        </button>
      </div>

      <!-- 每页条数：下拉按钮(透明) + 下拉列表(0.25蒙版) 完全和MusicList一致 -->
      <div class="dropdown-btn-container">
        <button
          class="dropdown-btn"
          @click="toggleDropdown('pageSize')"
        >
          {{ pageSize }}条
          <span class="arrow-icon" :class="{active: dropdownShow.pageSize}">▼</span>
        </button>
        <ul class="dropdown-options" v-show="dropdownShow.pageSize">
          <li
            v-for="size in pageSizeOptions"
            :key="size"
            @click="handleSizeChange(size); toggleDropdown('pageSize')"
            :class="{active: pageSize === size}"
          >
            {{ size }}条
          </li>
        </ul>
      </div>

      <!-- 专辑名/歌手 搜索框 -->
      <div class="search-container">
        <input
          v-model="nameSingerKeyword"
          type="text"
          placeholder="搜索专辑名/歌手..."
          class="search-input"
          @keyup.enter="searchByNameSinger"
        >
        <button @click="searchByNameSinger" class="search-btn">搜索</button>
        <button v-if="nameSingerKeyword" @click="clearNameSingerSearch" class="clear-btn">清空</button>
      </div>

      <!-- ✅ 核心调整：标签搜索框 + 右侧追加【重置】按钮，同排展示 -->
      <div class="search-container tag-search-container">
        <input
          v-model="tagKeyword"
          type="text"
          placeholder="搜索标签（摇滚/华语/怀旧等）..."
          class="search-input"
          @keyup.enter="searchByTag"
        >
        <button @click="searchByTag" class="search-btn">搜索</button>
        <button v-if="tagKeyword" @click="clearTagSearch" class="clear-btn">清空</button>
      </div>

    </div>

    <!-- 搜索结果列表 -->
    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="searchResult.length === 0" class="empty-tip">
      {{ hasSearchKeyword ? '未找到匹配的专辑副本' : '暂无专辑副本数据' }}
    </div>
    <div v-else class="album-list">
      <div v-for="album in searchResult" :key="album.id" class="album-item-wrapper">
        <AlbumPoolItem
          :album="album"
          :is-admin="isAdmin"
          :mainColor="mainColor"
          :mainColorDark="mainColorDark"
          :mainColorDarkDouble="mainColorDarkDouble"
          @copy-album="copyAlbum"
          @view-detail="viewAlbumDetail"
          @delete-album="deletePoolAlbum"
        />
      </div>
    </div>

    <!-- 分页永久显示 -->
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
      <div class="page-info-wrapper">
        <span class="page-info">
          第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页 (总 {{ pagination.total }} 条)
        </span>
      </div>
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

    <!-- ✅✅✅ 核心修改2：引入AddAlbum左侧侧边栏子组件 -->
    <AddAlbum
      :visible="showAddAlbumSidebar"
      :mainColor="mainColor"
      :mainColorDark="mainColorDark"
      :mainColorDarkDouble="mainColorDarkDouble"
      @close="showAddAlbumSidebar = false"
    />
  </div>
</template>

<script>
// ✅✅✅ 核心修改3：引入AddAlbum组件
import AlbumPoolItem from '@/components/item/AlbumPoolItem.vue'
import AddAlbum from '@/components/sidebar/AddAlbum.vue' // 你的AddAlbum路径，按需微调

export default {
  name: 'SearchAlbumPool',
  components: { AlbumPoolItem, AddAlbum }, // ✅ 注册组件
  props: {
    mainColor: {
      type: String,
      default: 'transparent'
    },
    mainColorDark: {
      type: String,
      default: 'transparent'
    },
    mainColorDarkDouble: {
      type: String,
      default: 'transparent'
    }
  },
  data() {
    return {
      nameSingerKeyword: '',
      tagKeyword: '',
      searchResult: [],
      loading: false,
      page: 1,
      pageSize: 10,
      pageSizeOptions: [5, 10, 20, 50],
      pagination: {
        total: 0,
        page: 1,
        page_size: 5,
        total_pages: 0
      },
      isAdmin: false,
      sortBy: 'created_at',
      sortOrder: 'desc',
      jumpPageNum: 1,
      sortByMap: {
        album_name: '专辑名称',
        release_year: '发行年份',
        singer: '歌手',
        created_at: '添加时间'
      },
      dropdownShow: {
        sortBy: false,
        pageSize: false
      },
      // ✅✅✅ 核心修改4：新增侧边栏显示隐藏的状态变量
      showAddAlbumSidebar: false
    }
  },
  computed: {
    hasSearchKeyword() {
      return this.nameSingerKeyword.trim() || this.tagKeyword.trim()
    }
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    this.isAdmin = localStorage.getItem('is_admin') === '1';
    this.getSearchResult();
  },
  methods: {
    toggleDropdown(type) {
      Object.keys(this.dropdownShow).forEach(key => {
        this.dropdownShow[key] = key === type ? !this.dropdownShow[key] : false
      })
    },
    handleSortChange(sortBy) {
      this.sortBy = sortBy
      this.getSearchResult()
    },
    handleOrderChange(sortOrder) {
      this.sortOrder = sortOrder
      this.getSearchResult()
    },
    handleSizeChange(pageSize) {
      this.pageSize = pageSize
      this.resetPageAndGetResult()
    },
    getSearchResult() {
      this.tagKeyword.trim() ? this.searchByTag() : this.searchByNameSinger();
    },
    searchByNameSinger() {
      this.loading = true;
      this.$axios({
        url: '/api/album/pool/search/name-singer',
        method: 'GET',
        headers: { 'Authorization': localStorage.getItem('token') || '', },
        params: { keyword: this.nameSingerKeyword.trim(), page: this.page, page_size: this.pageSize, sort_field: this.sortBy, sort_order: this.sortOrder }
      }).then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          this.searchResult = res.data.data.list || [];
          this.pagination = res.data.data.pagination || { total: 0, page: 1, page_size: this.pageSize, total_pages: 0 };
          this.jumpPageNum = this.pagination.page;
        } else { this.searchResult = []; }
      }).catch(err => { this.loading = false; console.error('专辑/歌手搜索失败：', err); });
    },
    searchByTag() {
      this.loading = true;
      this.$axios({
        url: '/api/album/pool/search/tags',
        method: 'GET',
        headers: { 'Authorization': localStorage.getItem('token') || '', },
        params: { tag: this.tagKeyword.trim(), page: this.page, page_size: this.pageSize, sort_field: this.sortBy, sort_order: this.sortOrder }
      }).then(res => {
        this.loading = false;
        if (res.data.code === 200) {
          this.searchResult = res.data.data.list || [];
          this.pagination = res.data.data.pagination || { total: 0, page: 1, page_size: this.pageSize, total_pages: 0 };
          this.jumpPageNum = this.pagination.page;
        } else { this.searchResult = []; }
      }).catch(err => { this.loading = false; console.error('标签搜索失败：', err); });
    },
    clearNameSingerSearch() { this.nameSingerKeyword = ''; this.page = 1; this.getSearchResult(); },
    clearTagSearch() { this.tagKeyword = ''; this.page = 1; this.getSearchResult(); },
    resetSearch() { this.nameSingerKeyword = ''; this.tagKeyword = ''; this.page = 1; this.sortBy = 'created_at'; this.sortOrder = 'desc'; this.getSearchResult(); },
    resetPageAndGetResult() { this.page = 1; this.getSearchResult(); },
    changePage(newPage) { if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) return; this.page = newPage; this.getSearchResult(); },
    jumpToPage() {
      const num = parseInt(this.jumpPageNum);
      if (isNaN(num) || num < 1 || num > this.pagination.total_pages) { this.jumpPageNum = this.pagination.page; return; }
      this.changePage(num);
    },
    copyAlbum(albumId) {
      if (!albumId) return;
      this.$axios({ url: `/api/album/pool/copy/${albumId}`, method: 'POST', headers: {'Authorization': localStorage.getItem('token') || ''} })
      .then(res => {
        const {code, data} = res.data;
        if (code === 200) {
          this.$router.push(`/webhome`).then(() => {
            const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
            if (webHomeVm) webHomeVm.activeMainTab = 'mymusic'
          })
        } else if (code === 409 && data) {
          const duplicateAlbumId = Number(data) || data;
          this.$router.push(`/album/detail/${duplicateAlbumId}?id=${duplicateAlbumId}`);
        }
      }).catch(err => { console.error('复制专辑失败：', err); });
    },
    viewAlbumDetail(poolId) { this.$router.push(`/album/pool/detail/${poolId}`); },
    deletePoolAlbum(poolId) {
      if (!this.isAdmin) return;
      if (!confirm('确定要删除该专辑吗？删除后不可恢复！')) return;
      this.$axios({ url: `/api/album/pool/delete/${poolId}`, method: 'DELETE', headers: {'Authorization': localStorage.getItem('token') || ''} })
      .then(res => { if (res.data.code === 200) this.getSearchResult();
      }).catch(err => {
        console.error('删除专辑失败：', err);
      });
    },
    // ✅✅✅ 核心修改5：删除原跳转方法，不需要了
  }
};
</script>

<style scoped>
body {
  font-family: "Microsoft YaHei", sans-serif;
  margin: 20px;
}

.container {
  max-width: 1600px;
  margin: 0 auto;
  position: relative;
}

.all-actions-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  width: 100%;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
  padding: 10px 16px;
  border-radius: 8px;
  box-sizing: border-box;
  position: relative;
  z-index: 99;
}

.add-original-btn {
  padding: 8px 20px;
  font-size: 15px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.dropdown-btn-container {
  position: relative;
  z-index: 9999;
}

.dropdown-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  background: v-bind(mainColorDark);
  color: #fafafa;
  position: relative;
}

.dropdown-btn::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 4px;
	border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
}

.arrow-icon {
  font-size: 12px;
  transition: transform 0.2s;
}

.arrow-icon.active {
  transform: rotate(180deg);
}

/* ✅✅✅ 核心修改 - 下拉列表样式统一修改 去掉蒙版+毛玻璃、背景mainColorDark、字体纯白色 */
.dropdown-options {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
	padding: 8px 0;
  list-style: none;
	border-radius: 6px;
  z-index: 99999;
  background: v-bind(mainColorDark) !important;
  backdrop-filter: none !important;
  border: none;
  overflow: visible;
}
.dropdown-options li {
  padding: 8px 16px;
  font-size: 14px;
  color: #ffffff !important;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}
.dropdown-options li:hover {
  background: rgba(255, 255, 255, 0.2);
	border-radius: 4px;
}
.dropdown-options li.active {
  color: #ffffff !important;
  font-weight: 600;
  background: rgba(255,255,255,0.3);
}

.sort-options {
  display: flex;
  gap: 10px;
  background: transparent !important;
  backdrop-filter: none !important;
	border-radius: 4px;
	border: none !important;
  width: fit-content;
  box-sizing: border-box;
}

.tab-item {
  padding: 8px 16px;
	border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  color: v-bind(mainColorDark);
  transition: all 0.2s;
  font-weight: 600;
  position: relative;
	border: none;
  background: transparent;
}

.tab-item.active {
  background: v-bind(mainColorDark);
  color: #fff;
}

.tab-item::after {
  content: '';
  position: absolute;
	left: 0;
	bottom: 0;
	width: 100%;
	height: 4px;
	border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
}

.loading-tip, .empty-tip {
  text-align: center;
  color: #666;
  padding: 30px 0;
}

.album-list {
  margin-top: 20px;
  position: relative;
  z-index: 1;
}

.album-item-wrapper {
  position: relative;
  margin-bottom: 2px;
	padding: 3px 20px;
	border: none;
	border-radius: 8px;
  background: transparent;
  z-index: 2;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 30px;
  padding: 10px 16px;
  flex-wrap: wrap;
  width: 100%;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
	border-radius: 8px;
  box-sizing: border-box;
  justify-content: flex-start;
}

.page-info-wrapper {
  position: relative;
  padding: 4px 0;
  display: inline-block;
}

.page-info {
  color: v-bind(mainColorDark);
	font-size: 14px;
  line-height: 1.5;
}

.page-info-wrapper::after {
  content: '';
	position: absolute;
	left: 0;
	bottom: 0;
	width: 100%;
	height: 4px;
	border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
}

.jump-page {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.page-btn {
  padding: 6px 12px;
  border: v-bind(mainColorDark);
	border-radius: 4px;
  color:#ffffff;
  background: v-bind(mainColorDark);
  cursor: pointer;
}

.page-btn:disabled {
  background: v-bind(mainColorDark);
  color: #ffffff;
  cursor: not-allowed;
}

.page-input {
  width: 60px;
	padding: 6px 8px;
	border-radius: 4px;
  background: transparent !important;
  border: none !important;
  color: #ffffff;
  outline: none;
}

.page-input::placeholder {
  color: #ffffff;
  opacity: 1;
}

.jump-btn {
  padding: 6px 12px;
  background: v-bind(mainColorDark);
  color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}

.search-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  padding: 6px 10px;
	width: 200px;
	border-radius: 4px;
	font-size: 14px;
  background: transparent !important;
  border: none !important;
  color: v-bind(mainColorDark) !important;
  outline: none;
}

.search-input::placeholder {
  color: v-bind(mainColorDarkDouble) !important;
  opacity: 1;
}

.search-btn {
  padding: 6px 12px;
	background: v-bind(mainColorDark);
  color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
}

.clear-btn {
  padding: 6px 12px;
  background: #999;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
}

.clear-btn:hover {
  background: #666;
}

.tag-search-container .search-btn {
  background: v-bind(mainColorDark);
}

.tag-search-container .search-btn:hover {
  background: v-bind(mainColorDarkDouble);
}

.reset-btn {
  padding: 6px 12px;
  background: v-bind(mainColorDark);
  color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
}

.reset-btn:hover {
  background: v-bind(mainColorDarkDouble);
}
</style>