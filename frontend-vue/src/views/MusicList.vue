<template>
  <div class="container">
    <h1>我的专辑列表（{{ username }}）</h1>
    <div class="header-actions">
      <button @click="goToAlbumPool" class="add-btn">添加新专辑</button>
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
      <!-- 关键修改1：key和传参改为music.id（分表自增ID） -->
      <div v-for="music in musicList" :key="music.id" class="album-item-wrapper">
        <MusicItem
          :music="music"
          @add-comment="handleAddComment"
        />

        <!-- ========== 核心新增：同步开关区域（已注释） ========== -->
        <!-- <div v-if="music.source_pool_id" class="sync-switch-container">
          <label class="sync-switch">
            <input
              type="checkbox"
              v-model="music.sync_pool_update"
              @change="toggleSync(music.id, music.sync_pool_update)"
              :disabled="music.is_customized"
            >
            <span class="slider round"></span>
          </label>
          <span class="sync-text">
            {{ music.sync_pool_update ? '同步开启' : '同步关闭' }}
            <span v-if="music.is_customized" class="customized-tag">（已自定义，无法同步）</span>
          </span>
        </div> -->
        <!-- ========== 同步开关结束 ========== -->

        <!-- 关键修改2：删除按钮传参改为music.id -->
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
import MusicItem from '../components/MusicItem.vue'

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
        url: '/api/album/list',  // 保持不变，适配后端接口
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
              // ========== 核心新增：处理同步开关和自定义标记的格式转换（已注释） ==========
              // this.musicList = this.musicList.map(item => ({
              //   ...item,
              //   // 数据库中是 1/0，转成布尔值方便开关使用
              //   sync_pool_update: item.sync_pool_update === 1,
              //   is_customized: item.is_customized === 1
              // }))
              // ========== 格式转换结束 ==========

              this.pagination = res.data.data.pagination || {
                total: 0,
                page: 1,
                page_size: 10,
                total_pages: 0
              }
              // 同步跳转页码输入框
              this.jumpPageNum = this.pagination.page
              console.log('✅ 拿到后端专辑数据：', this.musicList)
              // 检查每个专辑是否有id字段
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

    // ========== 核心新增：切换同步开关状态（已注释） ==========
    // toggleSync(albumId, status) {
    //   // 禁用状态下不执行
    //   if (this.musicList.find(item => item.id === albumId)?.is_customized) {
    //     alert('该专辑已自定义修改，无法切换同步状态！')
    //     return
    //   }

    //   this.loading = true
    //   this.$axios({
    //     url: '/api/album/sync/switch',
    //     method: 'POST',
    //     headers: {
    //       'Authorization': localStorage.getItem('token') || '',
    //       'Content-Type': 'application/json'
    //     },
    //     data: {
    //       album_id: albumId,
    //       sync_status: status ? 1 : 0  // 转成数据库的 1/0 格式
    //     }
    //   })
    //       .then(res => {
    //         this.loading = false
    //         if (res.data.code === 200) {
    //           alert(res.data.msg)
    //           // 局部更新，无需刷新整个列表（优化体验）
    //           const index = this.musicList.findIndex(item => item.id === albumId)
    //           if (index !== -1) {
    //             this.musicList[index].sync_pool_update = status
    //           }
    //         } else {
    //           alert('操作失败：' + res.data.msg)
    //           // 回滚开关状态
    //           const index = this.musicList.findIndex(item => item.id === albumId)
    //           if (index !== -1) {
    //             this.musicList[index].sync_pool_update = !status
    //           }
    //         }
    //       })
    //       .catch(err => {
    //         this.loading = false
    //         console.error('切换同步状态失败：', err)
    //         alert('操作失败！请重试')
    //         // 回滚开关状态
    //         const index = this.musicList.findIndex(item => item.id === albumId)
    //         if (index !== -1) {
    //           this.musicList[index].sync_pool_update = !status
    //         }
    //       })
    // },
    // ========== 同步开关方法结束 ==========

    // 处理评论提交
    handleAddComment(data) {
      // 关键修改3：评论接口传参改为music.id（分表ID）
      this.$axios({
        url: `/api/album/comment/add/${data.musicId}`,  // 改为路径传参
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
    // 关键修改4：删除方法增加ID校验
    async deleteAlbum(albumId) {
      // 第一步：校验ID有效性
      if (!albumId || isNaN(albumId) || albumId <= 0) {
        alert('无效的专辑ID！');
        return;
      }
      if (!confirm('确定删除该专辑吗？此操作仅删除你的副本，不会影响搜索池里的公共专辑')) return;

      try {
        const res = await this.$axios.delete(`/api/album/delete/${albumId}`);
        if (res.data.code === 200) {
          alert('删除成功！');
          this.getMusicList(); // 重新加载列表
        } else {
          alert(res.data.msg || '删除失败');
        }
      } catch (error) {
        console.error('删除失败：', error);
        // 更友好的错误提示
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
    // 废弃：原添加专辑方法
    goAddAlbum() {
      this.$router.push('/add-album')
    },
    // 新增：跳转到专辑搜索池页面
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

/* ========== 核心新增：同步开关样式（已注释） ========== */
/* .sync-switch-container {
  position: absolute;
  top: 10px;
  right: 100px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

/* 开关基础样式 */
/* .sync-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}

/* 隐藏原生复选框 */
/* .sync-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

/* 滑块样式 */
/* .slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 20px;
}

/* 滑块圆点 */
/* .slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

/* 选中状态 */
/* input:checked + .slider {
  background-color: #42b983;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

/* 禁用状态 */
/* input:disabled + .slider {
  background-color: #999;
  cursor: not-allowed;
}

/* 同步文本样式 */
/* .sync-text {
  color: #666;
}

/* 自定义标记样式 */
/* .customized-tag {
  color: #ff9800;
  margin-left: 4px;
} */
/* ========== 同步开关样式结束 ========== */
</style>