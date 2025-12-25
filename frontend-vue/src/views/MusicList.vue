<template>
  <div class="container">
    <h1>我的专辑列表（{{ username }}）</h1>
    <button @click="goAddAlbum" class="add-btn">添加新专辑</button>
    <button @click="logout">退出登录</button>

    <!-- 无数据时的提示 -->
    <div v-if="musicList.length === 0" class="empty-tip">
      暂无专辑数据，点击「添加新专辑」创建吧～
    </div>

    <!-- 循环渲染子组件 MusicItem（把每一条专辑数据传给子组件） -->
    <MusicItem
      v-else
      v-for="music in musicList"
      :key="music.id"
      :music="music"
      @add-comment="handleAddComment"
    />
  </div>
</template>

<script>
// 导入子组件 MusicItem（必须有这一步！）
import MusicItem from '../components/MusicItem.vue'

export default {
  name: 'MusicList',
  // 注册子组件（必须有！否则Vue找不到MusicItem）
  components: { MusicItem },
  data() {
    return {
      musicList: [], // 存储后端返回的所有专辑数据
      username: ''   // 登录的用户名
    }
  },
  created() {
    // 页面加载时：先检查登录状态，再拿数据
    this.username = localStorage.getItem('username') || ''
    const token = localStorage.getItem('token')

    // 没登录就跳登录页
    if (!token || !this.username) {
      this.$router.push('/login')
      return
    }

    // 已登录，调用 getMusicList 拿专辑数据
    this.getMusicList()
  },
  methods: {
    // 核心方法：向后端请求专辑数据（手动指定后端地址+token）
    getMusicList() {
      // 直接请求后端 5000 端口，手动加 token 到请求头
      this.$axios({
        url: 'http://127.0.0.1:5000/api/music', // 后端完整地址，必改！
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '', // 手动传 token
          'Content-Type': 'application/json'
        },
        timeout: 5000 // 超时时间
      })
      .then(res => {
        // 拿到后端数据，赋值给 musicList（子组件会渲染这个数组）
        this.musicList = res.data || []
        console.log('✅ 拿到后端专辑数据：', this.musicList) // 控制台能看到数据
      })
      .catch(err => {
        console.error('❌ 请求后端失败：', err)
        alert('获取专辑数据失败！请检查后端是否启动，或重新登录')
        this.$router.push('/login')
      })
    },
    // 处理子组件传来的“提交评论”事件
    handleAddComment(data) {
      this.$axios({
        url: 'http://127.0.0.1:5000/api/music/comment',
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: data // 子组件传来的评论数据
      })
      .then(resp => {
        if (resp.data.code === 200) {
          this.getMusicList() // 重新拿数据，刷新页面
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
    // 跳转到添加专辑页面
    goAddAlbum() {
      this.$router.push('/add-album')
    },
    // 退出登录
    logout() {
      try {
        localStorage.clear() // 清空本地存储
        this.$router.replace('/login') // 跳登录页
        alert('退出登录成功！')
      } catch (err) {
        console.error('退出登录失败：', err)
        window.location.href = '/#/login' // 兜底跳转
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
</style>