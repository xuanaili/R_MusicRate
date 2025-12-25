<!-- frontend-cdn/components/MusicItem.vue -->
<template>
  <div class="music-item">
    <h3>{{ music.name }}</h3>
    <div class="score">当前评分：{{ music.score }}</div>

    <!-- 引入评分星星组件 -->
    <StarRating
      :currentScore="localScore"
      @score-change="setScore"
    />

    <input type="text" v-model="newComment" placeholder="输入评论...">
    <button @click="addComment">提交</button>

    <div class="comments">
      <div v-for="(comment, index) in music.comments" :key="index">{{ comment }}</div>
    </div>
  </div>
</template>

<script>
// 引入评分星星组件
import StarRating from './StarRating.vue';

export default {
  props: {
    // 接收父组件传的单首音乐数据
    music: {
      type: Object,
      required: true
    }
  },
  components: {
    StarRating // 注册组件
  },
  data() {
    return {
      localScore: 0, // 当前歌曲的临时评分
      newComment: ''
    }
  },
  methods: {
    setScore(score) {
      this.localScore = score;
    },
    addComment() {
      if (this.newComment.trim() === '') return;
      // 把评论传给父组件
      this.$emit('add-comment', {
        musicId: this.music.id,
        comment: this.newComment,
        score: this.localScore
      });
      this.newComment = '';
      this.localScore = 0;
    }
  }
}
</script>

<style scoped>
/* 复用之前music-item的样式 */
.music-item {
  border: 1px solid #eee;
  padding: 15px;
  margin: 10px 0;
  border-radius: 8px;
}
.comments {
  margin-top: 10px;
  padding-left: 10px;
  color: #666;
}
input {
  padding: 8px;
  margin-right: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 300px;
}
button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>