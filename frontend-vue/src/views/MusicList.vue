<template>
  <div class="container">
    <h1>我的专辑列表（{{ username }}）</h1>
    <div class="header-actions">
      <button @click="goAddAlbum" class="add-btn">添加新专辑</button>
      <button @click="logout">退出登录</button>

      <!-- 排序功能 -->
      <div class="sort-container">
        <label>排序方式：</label>
        <select v-model="sortBy" @change="getMusicList()">
          <option value="album_name">专辑名称</option>
          <option value="release_year">发行年份</option>
          <option value="singer">歌手</option>
          <option value="my_score">我的评分</option>
        </select>
        <select v-model="sortOrder" @change="getMusicList()">
          <option value="asc">升序</option>
          <option value="desc">降序</option>
        </select>
      </div>

      <!-- 每页条数选择 -->
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

    <!-- 无数据时的提示 -->
    <div v-if="musicList.length === 0 && !loading" class="empty-tip">
      暂无专辑数据，点击「添加新专辑」创建吧～
    </div>

    <!-- 加载中提示 -->
    <div v-if="loading" class="loading-tip">
      加载中...
    </div>

    <!-- 循环渲染子组件 MusicItem -->
    <div v-else class="album-list">
      <div v-for="music in musicList" :key="music.origin_id" class="album-item-wrapper">
        <MusicItem
          :music="music"
          @add-comment="handleAddComment"
        />
        <!-- 新增：删除专辑按钮 -->
        <button
          @click="deleteAlbum(music.origin_id)"
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
import MusicItem from '../components/MusicItem.vue'

export default {
  name: 'MusicList',
  components: { MusicItem },
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
      sortBy: 'album_name',
      sortOrder: 'asc',
      // 跳转页码
      jumpPageNum: 1
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
    // 获取专辑列表（带分页和排序）
    getMusicList() {
      this.loading = true
      this.$axios({
        url: '/api/album/list',  // 修改：适配新的专辑列表接口
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        params: {
          page: this.page,
          page_size: this.pageSize,
          sort_by: this.sortBy,
          sort_order: this.sortOrder
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
          // 同步跳转页码输入框
          this.jumpPageNum = this.pagination.page
          console.log('✅ 拿到后端专辑数据：', this.musicList)
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
    // 处理评论提交
    handleAddComment(data) {
      this.$axios({
        url: '/api/album/comment/add',  // 修改：适配新的评论接口
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: {
          origin_id: data.musicId,  // 修改：用origin_id替代musicId
          content: data.comment,
          track_id: 0  // 专辑评论，track_id为0
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
    // 新增：删除专辑
    deleteAlbum(originId) {
      if (!confirm(`确定要删除ID为${originId}的专辑吗？此操作不可恢复！`)) {
        return;
      }
      this.$axios({
        url: `/api/album/delete/${originId}`,  // 修改：适配新的删除接口
        method: 'DELETE',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('专辑删除成功！');
          // 刷新列表（保持当前页）
          this.getMusicList();
        } else {
          alert(res.data.msg);
        }
      })
      .catch((err) => {
        console.error('删除专辑失败：', err);
        alert('删除专辑失败！' + err.message);
      });
    },
    // 切换页码
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) {
        return
      }
      this.page = newPage
      this.getMusicList()
    },
    // 重置页码并刷新列表（切换每页条数时）
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
    // 跳转到添加专辑页面
    goAddAlbum() {
      this.$router.push('/add-album')
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
  margin-bottom: 20px;
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
/* 新增：专辑项容器 */
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
/* 新增：删除专辑按钮样式 */
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
/* 排序样式 */
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