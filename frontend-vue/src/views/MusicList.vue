<template>
  <div class="container">
    <div class="header-actions">
      <!-- 排序功能 + 每页条数 这一排保持不变 -->
      <div class="sort-container">
        <label>排序方式：</label>
        <select v-model="sortBy" @change="getMusicList()">
          <option value="album_name">专辑名称</option>
          <option value="release_year">发行年份</option>
          <option value="singer">歌手</option>
          <option value="my_score">我的评分</option>
          <option value="created_at">添加时间</option>
        </select>
        <select v-model="sortOrder" @change="getMusicList()">
          <option value="asc">升序</option>
          <option value="desc">降序</option>
        </select>
      </div>

      <div class="page-size-container">
        <label>每页显示：</label>
        <select v-model="pageSize" @change="resetPageAndGetList()">
          <option value="5">5条</option>
          <option value="10">10条</option>
          <option value="20">20条</option>
          <option value="50">50条</option>
        </select>
      </div>
    </div>

    <!-- ✅ 核心修改：两个搜索框 单独放在下方的一行，并排展示 -->
    <div class="search-box-wrapper">
      <!-- 第一个搜索框：综合搜索 → 专辑名 + 歌手 -->
      <div class="search-container">
        <input
          type="text"
          v-model="searchKeyword"
          placeholder="搜索专辑名/歌手"
          class="search-input"
          @keyup.enter="handleSearch"
        >
        <button @click="handleSearch" class="search-btn">搜索</button>
        <button v-if="searchKeyword" @click="clearSearch" class="clear-btn">清空</button>
      </div>

      <!-- 第二个搜索框 → 独立搜索【类型/标签】 -->
      <div class="search-container tag-search-container">
        <input
          type="text"
          v-model="tagKeyword"
          placeholder="搜索专辑类型/标签"
          class="search-input"
          @keyup.enter="handleTagSearch"
        >
        <button @click="handleTagSearch" class="search-btn">搜类型</button>
        <button v-if="tagKeyword" @click="clearTagSearch" class="clear-btn">清空</button>
      </div>
    </div>

    <!-- 无数据时的提示（区分：无搜索结果 / 本身无数据） -->
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
        />

        <button
          @click="deleteAlbum(music.id)"
          class="delete-album-btn"
        >
          删除专辑
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

      <span class="page-info">
        第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页
        (总 {{ pagination.total }} 条)
      </span>

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
  data() {
    return {
      musicList: [],
      username: '',
      loading: false,
      // 分页参数
      page: 1,
      pageSize: 10,
      pagination: {
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      },
      // 排序参数
      sortBy: 'created_at',
      sortOrder: 'desc',
      // 跳转页码
      jumpPageNum: 1,
      // 原有：综合搜索关键词（专辑名+歌手）
      searchKeyword: '',
      // 核心新增：独立的类型/标签搜索关键词
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
    // 请求参数新增 tag_keyword 传给后端
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
          search_keyword: this.searchKeyword.trim(), // 综合搜索词
          tag_keyword: this.tagKeyword.trim()        // 独立类型搜索词
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
              console.log('✅ 拿到后端专辑数据：', this.musicList)
              this.musicList.forEach(item => {
                if (!item.id) {
                  console.warn('⚠️ 专辑数据缺少id字段：', item)
                }
              })
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

    // 综合搜索：专辑名+歌手
    handleSearch() {
      this.page = 1
      this.getMusicList()
    },
    clearSearch() {
      this.searchKeyword = ''
      this.page = 1
      this.getMusicList()
    },

    // 独立的类型搜索方法
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
          alert('删除成功！');
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
    // 切换页码
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) {
        return
      }
      this.page = newPage
      this.getMusicList()
    },
    // 重置页码并刷新列表
    resetPageAndGetList() {
      this.page = 1
      this.getMusicList()
    },
    // 跳转到指定页
    jumpToPage() {
      const num = parseInt(this.jumpPageNum)
      if (isNaN(num) || num < 1 || num > this.pagination.total_pages) {
        alert(`请输入1-${this.pagination.total_pages}之间的有效页码！`)
        this.jumpPageNum = this.pagination.page
        return
      }
      this.changePage(num)
    },
    // 废弃方法
    goAddAlbum() {
      this.$router.push('/add-album')
    },
    // 跳转到专辑搜索池页面
    goToAlbumPool() {
      this.$router.push('/album-pool');
    },
    // 退出登录
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.add-btn {
  background: #42b983;
  color: white;
  border: none;
	padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
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
}

.album-item-wrapper {
  position: relative;
  margin-bottom: 20px;
	padding: 10px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.delete-album-btn {
  position: absolute;
	top: 10px;
	right: 10px;
  padding: 6px 12px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.delete-album-btn:hover {
  background: #c0392b;
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

/* ✅ 核心新增：搜索框外层容器 单独一行，并排展示两个搜索框 */
.search-box-wrapper {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
/* 搜索框基础样式 */
.search-container {
  display: flex;
  align-items: center;
  gap: 8px;
}
.search-input {
  padding: 6px 10px;
  width: 220px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
}
.search-input:focus {
  border-color: #42b983;
}
.search-btn {
  padding: 6px 12px;
  background: #42b983;
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
/* 类型搜索框样式区分 */
.tag-search-container .search-btn {
  background: #3498db;
}
.tag-search-container .search-btn:hover {
  background: #2980b9;
}
</style>