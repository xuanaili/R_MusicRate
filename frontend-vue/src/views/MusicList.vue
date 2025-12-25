<!-- src/views/MusicList.vue -->
<template>
  <div class="container">
    <h1>我的音乐评分（{{ username }}）</h1>
    <button @click="logout">退出登录</button>
    <MusicItem
      v-for="music in musicList"
      :key="music.id"
      :music="music"
      @add-comment="handleAddComment"
    />
  </div>
</template>

<script>
import MusicItem from '../components/MusicItem.vue'

export default {
  name: 'MusicList',  // 新增：多单词组件名
  components: { MusicItem },
  data() {
    return {
      musicList: [],
      username: localStorage.getItem('username') || ''  // 显示登录的用户名
    }
  },
  created() {
    // 先获取用户名（优先从本地取）
    this.username = localStorage.getItem('username') || ''
    // 再判断：如果没有token/用户名，直接跳登录页
    if (!localStorage.getItem('token') || !this.username) {
      this.$router.push('/login')
      return

    }
    this.getMusicList()
  },
  methods: {
    getMusicList() {
      this.$axios.get('/api/music')
        .then(res => {
          this.musicList = res.data
        })
        .catch(err => {
          console.error('获取音乐列表失败：', err)
          // 失败也跳登录页（比如token过期）
          this.$router.push('/login')
        })
    },
    handleAddComment(data) {
      this.$axios.post('/api/music/comment', data)
        .then(resp => {
          if (resp.data.code === 200) {
            this.getMusicList()
            alert('提交成功！')
          } else {
            alert('提交失败：' + resp.data.msg)
          }
        })
        .catch(err => {
          console.error('提交评论失败：', err)
          alert('提交失败！')
        })
    },
    // 新增：退出登录
// MusicList.vue 里的logout方法优化
logout() {
  try {
    // 清空本地存储
    localStorage.clear()  // 直接清空所有，更彻底
    // 强制跳登录页
    this.$router.replace('/login')  // replace比push更适合退出跳转
    alert('退出登录成功！')
  } catch (err) {
    console.error('退出登录失败：', err)
    // 兜底：如果路由跳不了，直接刷新页面
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
  max-width: 800px;
  margin: 0 auto;
}
</style>