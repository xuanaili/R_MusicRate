<template>
  <div class="container">
    <h1>我的音乐评分</h1>
    <MusicItem
      v-for="music in musicList"
      :key="music.id"
      :music="music"
      @add-comment="handleAddComment"
    />
  </div>
</template>

<script>
import MusicItem from './components/MusicItem.vue'

export default {
  components: { MusicItem },
  data() {
    return {
      musicList: [] // 初始为空，从后端获取
    }
  },
  created() {
    // 页面加载时，调用后端接口获取音乐列表
    this.$axios.get('/api/music')
      .then(res => {
        this.musicList = res.data // 把后端数据赋值给前端
      })
      .catch(err => {
        console.error('获取音乐列表失败：', err)
        alert('加载失败，请检查后端是否启动！')
      })
  },
  methods: {
    handleAddComment(data) {
      // 提交评论到后端
      this.$axios.post('/api/music/comment', data)
        .then(resp => {
          // 核心：真正使用resp（读取后端返回的内容）
          if (resp.data.code === 200) { // 验证后端提交成功
            // 重新获取列表更新页面
            this.$axios.get('/api/music').then(newRes => {
              this.musicList = newRes.data
            })
            alert('提交成功！')
          } else {
            alert('提交失败：' + resp.data.msg)
          }
        })
          .catch(err => {
            console.error('提交评论失败：', err)
            alert('提交失败！')
          })
    }
  }
}
</script>

<style>
/* 全局样式 */
body {
  font-family: "Microsoft YaHei", sans-serif;
  margin: 20px;
}

.container {
  max-width: 800px;
  margin: 0 auto;
}
</style>