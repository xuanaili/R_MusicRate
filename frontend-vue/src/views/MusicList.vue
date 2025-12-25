<template>
  <div class="container">
    <h1>我的专辑列表（{{ username }}）</h1>
    <button @click="goAddAlbum" class="add-btn">添加新专辑</button>
    <button @click="logout">退出登录</button>

    <!-- 无数据时的提示 -->
    <div v-if="musicList.length === 0" class="empty-tip">
      暂无专辑数据，点击「添加新专辑」创建吧～
    </div>

    <!-- 循环渲染子组件 MusicItem -->
    <div v-else class="album-list">
      <div v-for="music in musicList" :key="music.id" class="album-item-wrapper">
        <MusicItem
          :music="music"
          @add-comment="handleAddComment"
        />
        <!-- 新增：删除专辑按钮 -->
        <button
          @click="deleteAlbum(music.id)"
          class="delete-album-btn"
        >
          删除专辑
        </button>
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
      username: ''
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
    // 获取专辑列表
    getMusicList() {
      this.$axios({
        url: 'http://127.0.0.1:5000/api/music',
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        timeout: 5000
      })
      .then(res => {
        this.musicList = res.data || []
        console.log('✅ 拿到后端专辑数据：', this.musicList)
      })
      .catch(err => {
        console.error('❌ 请求后端失败：', err)
        alert('获取专辑数据失败！请检查后端是否启动，或重新登录')
        this.$router.push('/login')
      })
    },
    // 处理评论提交
    handleAddComment(data) {
      this.$axios({
        url: 'http://127.0.0.1:5000/api/music/comment',
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: data
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
    deleteAlbum(albumId) {
      if (!confirm(`确定要删除ID为${albumId}的专辑吗？此操作不可恢复！`)) {
        return;
      }
      this.$axios({
        url: `http://127.0.0.1:5000/api/album/delete/${albumId}`,
        method: 'DELETE',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('专辑删除成功！');
          // 刷新列表
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

<style>
body {
  font-family: "Microsoft YaHei", sans-serif;
  margin: 20px;
}
.container {
  max-width: 1000px;
  margin: 0 auto;
}
.add-btn {
  background: #42b983;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 10px;
  margin-right: 10px;
}
.empty-tip {
  text-align: center;
  color: #999;
  padding: 50px 0;
}
/* 新增：专辑项容器 */
.album-list {
  margin-top: 20px;
}
.album-item-wrapper {
  position: relative;
  margin-bottom: 20px;
}
/* 新增：删除专辑按钮样式 */
.delete-album-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 8px 15px;
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
</style>