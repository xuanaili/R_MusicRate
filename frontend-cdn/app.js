// frontend-cdn/app.js
// 引入Vue（如果用CDN不用这行，若后续装npm需要）
// import Vue from 'vue';
// 引入音乐卡片组件
import MusicItem from './components/AlbumItem.vue';

new Vue({
  el: '#app',
  components: {
    MusicItem // 注册全局组件
  },
  data: {
    musicList: [
      {id: 1, name: '晴天', score: 8.5, comments: ['好听', '经典']},
      {id: 2, name: '七里香', score: 9.2, comments: []}
    ]
  },
  methods: {
    handleAddComment(data) {
      // 接收子组件传的评论/评分，更新数据
      let music = this.musicList.find(item => item.id === data.musicId);
      music.comments.push(data.comment);
      // 简单计算新评分（示例）
      music.score = (music.score + data.score) / 2;
    }
  }
})