<template>
  <div class="container">
    <!-- 所有功能一行展示容器 -->
    <div class="all-actions-wrapper">
      <!-- ✅ 专辑排序维度：下拉按钮(透明) + 下拉列表(0.25蒙版) -->
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

      <!-- ✅ 升序/降序 保留原版按钮组样式 完全不变 -->
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

      <!-- ✅ 每页条数：下拉按钮(透明) + 下拉列表(0.25蒙版) -->
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

      <!-- 综合搜索：专辑名 + 歌手 -->
      <div class="search-container">
        <input
          type="text"
          v-model="searchKeyword"
          placeholder="搜索专辑名/歌手"
          class="search-input"
          autocomplete="new-password"
          @keyup.enter="handleSearch"
        >
        <button @click="handleSearch" class="search-btn">搜索</button>
        <button v-if="searchKeyword" @click="clearSearch" class="clear-btn">清空</button>
      </div>

      <!-- 独立搜索：类型/标签
        ⚠️ autocomplete="new-password" 是故意为之：Chrome 会无视 autocomplete="off"，把已保存的用户名自动填入
        这类无 name/id 信号的纯文本输入框（启发式误判为用户名框）。new-password 是公认的阻断手段，勿删。
      -->
      <div class="search-container tag-search-container">
        <input
          type="text"
          v-model="tagKeyword"
          placeholder="搜索专辑类型/标签"
          class="search-input"
          autocomplete="new-password"
          @keyup.enter="handleTagSearch"
        >
        <button @click="handleTagSearch" class="search-btn">搜索</button>
        <button v-if="tagKeyword" @click="clearTagSearch" class="clear-btn">清空</button>
      </div>
    </div>

    <!-- 无数据提示 -->
    <div v-if="musicList.length === 0 && !loading" class="empty-tip">
      {{ searchKeyword || tagKeyword ? '没有找到匹配的专辑数据' : '暂无专辑数据，点击「添加新专辑」创建吧～' }}
    </div>

    <!-- 加载中提示 -->
    <div v-if="loading" class="loading-tip">
      加载中...
    </div>

    <!-- 循环渲染子组件 MusicItem -->
    <div v-else class="album-list">
      <div v-for="music in musicList" :key="music.id" class="album-item-wrapper">
        <MusicItem
          :music="music"
          @add-comment="handleAddComment"
          :mainColor="mainColor"
          :mainColorDark="mainColorDark"
          :mainColorDarkDouble="mainColorDarkDouble"
        />

        <!-- ✅ 核心修改1：删除按钮文字改为 × 号 -->
        <button
          @click="deleteAlbum(music.id)"
          class="delete-album-btn"
        >
          -
        </button>
      </div>
    </div>

    <!-- 分页控件 -->
    <div v-if="pagination.total > 0" class="pagination">
      <button
        @click="changePage(1)"
        :disabled="pagination.page === 1 || loading"
        class="page-btn"
      >
        首页
      </button>
      <button
        @click="changePage(pagination.page - 1)"
        :disabled="pagination.page === 1 || loading"
        class="page-btn"
      >
        上一页
      </button>

      <!-- ✅ 核心修改：给页码信息包一层容器，用于内部放横线 -->
      <div class="page-info-wrapper">
        <span class="page-info">
          第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页
          (总 {{ pagination.total }} 条)
        </span>
      </div>

      <button
        @click="changePage(pagination.page + 1)"
        :disabled="pagination.page === pagination.total_pages || loading"
        class="page-btn"
      >
        下一页
      </button>
      <button
          @click="changePage(pagination.total_pages)"
          :disabled="pagination.page === pagination.total_pages || loading"
          class="page-btn"
      >
        尾页
      </button>

      <!-- 跳转到指定页 -->
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
import MusicItem from '@/components/item/AlbumItem.vue'

export default {
  name: 'MusicList',
  components: {MusicItem},
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
      musicList: [],
      username: '',
      loading: false,
      // 分页参数
      page: 1,
      pageSize: 50,
      pageSizeOptions: [10, 20, 50,100],
      pagination: {
        total: 0,
        page: 1,
        page_size: 5,
        total_pages: 0
      },
      // 排序参数 默认最近收听+降序（最新收听的专辑排最前）
      sortBy: 'last_listened',
      sortOrder: 'desc',
      // ✅ ✅ ✅ 排序选项：最近收听作为默认排序维度
      sortByMap: {
        last_listened: '最近收听',
        album_name: '专辑名称',
        release_year: '发行年份',
        singer: '歌手',
        my_score: '我的评分',
        created_at: '添加时间',
        listening_duration: '听取时间'
      },
      // 下拉框显示状态
      dropdownShow: {
        sortBy: false,
        pageSize: false
      },
      jumpPageNum: 1,
      searchKeyword: '',
      tagKeyword: ''
    }
  },
  created() {
    this.username = localStorage.getItem('username') || ''
    const token = localStorage.getItem('token')

    if (!token || !this.username) {
      this.$router.push('/login')
      return
    }

    this.getMusicList()
  },
  methods: {
    // 请求专辑列表数据
    getMusicList() {
      this.loading = true
      this.$axios({
        url: '/api/album/list',
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        params: {
          page: this.page,
          page_size: this.pageSize,
          sort_by: this.sortBy,
          sort_order: this.sortOrder,
          search_keyword: this.searchKeyword.trim(),
          tag_keyword: this.tagKeyword.trim()
        },
        timeout: 5000
      })
          .then(res => {
            this.loading = false
            if (res.data.code === 200) {
              this.musicList = res.data.data.list || []
              this.pagination = res.data.data.pagination || {
                total: 0,
                page: 1,
                page_size: 10,
                total_pages: 0
              }
              this.jumpPageNum = this.pagination.page
            } else {
              alert('获取数据失败：' + res.data.msg)
              this.musicList = []
            }
          })
          .catch(err => {
            this.loading = false
            console.error('❌ 请求后端失败：', err)
            alert('获取专辑数据失败！请检查后端是否启动，或重新登录')
            this.$router.push('/login')
          })
    },

    // 切换下拉框显示/隐藏
    toggleDropdown(type) {
      Object.keys(this.dropdownShow).forEach(key => {
        this.dropdownShow[key] = key === type ? !this.dropdownShow[key] : false
      })
    },
    // 切换排序字段
    handleSortChange(sortBy) {
      this.sortBy = sortBy
      this.getMusicList()
    },
    // 切换排序方向
    handleOrderChange(sortOrder) {
      this.sortOrder = sortOrder
      this.getMusicList()
    },
    // 切换每页条数
    handleSizeChange(pageSize) {
      this.pageSize = pageSize
      this.resetPageAndGetList()
    },

    // 综合搜索
    handleSearch() {
      this.page = 1
      this.getMusicList()
    },
    clearSearch() {
      this.searchKeyword = ''
      this.page = 1
      this.getMusicList()
    },
    // 类型搜索
    handleTagSearch() {
      this.page = 1
      this.getMusicList()
    },
    clearTagSearch() {
      this.tagKeyword = ''
      this.page = 1
      this.getMusicList()
    },
    // 处理评论提交
    handleAddComment(data) {
      this.$axios({
        url: `/api/album/comment/add/${data.musicId}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: {
          content: data.comment
        }
      })
          .then(resp => {
            if (resp.data.code === 200) {
              this.getMusicList()
              alert('评论提交成功！')
            } else {
              alert('提交失败：' + resp.data.msg)
            }
          })
          .catch(err => {
            console.error('提交评论失败：', err)
            alert('提交失败！')
          })
    },
    // 删除专辑
    async deleteAlbum(albumId) {
      if (!albumId || isNaN(albumId) || albumId <= 0) {
        alert('无效的专辑ID！');
        return;
      }
      if (!confirm('确定删除该专辑吗？此操作仅删除你的副本，不会影响搜索池里的公共专辑')) return;

      try {
        const res = await this.$axios.delete(`/api/album/delete/${albumId}`);
        if (res.data.code === 200) {
          this.getMusicList();
        } else {
          alert(res.data.msg || '删除失败');
        }
      } catch (error) {
        console.error('删除失败：', error);
        const errMsg = error.response?.data?.msg || error.message || '网络错误，请重试';
        alert(`删除出错：${errMsg}`);
      }
    },
    // 分页相关
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) {
        return
      }
      this.page = newPage
      this.getMusicList()
    },
    resetPageAndGetList() {
      this.page = 1
      this.getMusicList()
    },
    jumpToPage() {
      const num = parseInt(this.jumpPageNum)
      if (isNaN(num) || num < 1 || num > this.pagination.total_pages) {
        alert(`请输入1-${this.pagination.total_pages}之间的有效页码！`)
        this.jumpPageNum = this.pagination.page
        return
      }
      this.changePage(num)
    },
    goAddAlbum() {
      this.$router.push('/add-album')
    },
    goToAlbumPool() {
      this.$router.push('/album-pool');
    },
    logout() {
      try {
        localStorage.clear()
        this.$router.replace('/login')
        alert('退出登录成功！')
      } catch (err) {
        console.error('退出登录失败：', err)
        window.location.href = '/#/login'
      }
    }
  }
}
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

/* 所有功能一行展示容器样式 - 0.25白色蒙版背景+毛玻璃模糊+内边距优化 */
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

/* 下拉按钮容器+按钮样式 核心修复：提升z-index到顶级 */
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

/* ✅✅✅ 核心修改 - 下拉列表样式：移除蒙版/毛玻璃、背景改为mainColorDark、字体白色 */
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
  background: rgba(255, 255, 255, 0.3);
}

/* 升序/降序 按钮组 完全保留原版 一丝未改 */
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

.empty-tip {
  text-align: center;
  color: #999;
  padding: 50px 0;
}

.loading-tip {
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

/* ✅✅✅ 核心修改2：删除专辑按钮 纯×号样式 无边框无背景 统一风格 */
.delete-album-btn {
  position: absolute;
  top: -6px;
  right: 30px;
  padding: 0;
  border: none;
  background: transparent;
  color: v-bind(mainColorDarkDouble);
  cursor: pointer;
  font-size: 60px;
  font-weight: 200;
  white-space: nowrap;
  line-height: 1;
  flex-shrink: 0;
  transform: translateY(-1px);
}

.delete-album-btn:hover {
  background: transparent;
  color: v-bind(mainColorDarkDouble);
}

/* 分页控件样式 所有样式保留 */
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
  color: #ffffff;
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

.page-input:disabled {
  cursor: not-allowed;
  background: transparent !important;
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

.search-input:disabled {
  cursor: not-allowed;
  background: transparent !important;
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
</style>