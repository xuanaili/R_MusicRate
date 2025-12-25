<template>
  <div class="music-item">
    <!-- 专辑封面：优先显示URL，无则显示“暂无封面” -->
    <div class="cover">
      <img
        v-if="music.cover_img && music.cover_img.trim() !== ''"
        :src="music.cover_img"
        alt="专辑封面"
        width="80"
        height="80"
      >
      <div v-else class="no-cover">暂无封面</div>
    </div>

    <!-- 专辑核心信息：所有字段加兜底，确保不会空 -->
    <div class="info">
      <h3 class="album-name">{{ music.album_name || music.name || '未知专辑' }}</h3>
      <p class="singer"><strong>歌手：</strong>{{ music.singer || '未知' }}</p>
      <p class="year"><strong>发行年份：</strong>{{ music.release_year || '未知' }}</p>
      <p class="type"><strong>主要类型：</strong>{{ music.main_type || '未知' }}</p>
      <p class="tags"><strong>标签：</strong>{{ (music.tags && music.tags.length > 0) ? music.tags.join('、') : '无' }}</p>
      <p class="score"><strong>评分：</strong>{{ music.score || 0 }}</p>

      <!-- 评论区 -->
      <div class="comments">
        <p><strong>评论：</strong></p>
        <ul v-if="music.comments && music.comments.length > 0">
          <li v-for="(comment, idx) in music.comments" :key="idx">{{ comment }}</li>
        </ul>
        <p v-else class="no-comment">暂无评论</p>
        <input v-model="newComment" placeholder="输入评论" class="comment-input">
        <button @click="submitComment" class="comment-btn">提交评论</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MusicItem',
  props: {
    music: {
      type: Object,
      required: true,
      default: () => ({}) // 加默认值，避免传空
    }
  },
  data() {
    return {
      newComment: ''
    }
  },
  methods: {
    submitComment() {
      const comment = this.newComment.trim()
      if (!comment) {
        alert('评论不能为空！')
        return
      }
      this.$emit('add-comment', {
        musicId: this.music.id,
        comment: comment,
        score: 0
      })
      this.newComment = ''
    }
  }
}
</script>

<style scoped>
/* 整体卡片样式 */
.music-item {
  display: flex;
  gap: 20px;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 10px;
  margin-bottom: 20px;
  background: #f9f9f9;
}

/* 封面样式 */
.cover {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
  border-radius: 6px;
  overflow: hidden;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover; /* 图片自适应，不变形 */
}

.no-cover {
  color: #999;
  font-size: 12px;
  text-align: center;
}

/* 信息区域 */
.info {
  flex: 1;
}

.album-name {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 18px;
}

.singer, .year, .type, .tags, .score {
  margin: 5px 0;
  color: #666;
  font-size: 14px;
}

.score {
  color: #e67e22; /* 评分用橙色突出 */
  font-weight: 600;
}

/* 评论区样式 */
.comments {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed #eee;
}

.no-comment {
  color: #999;
  font-size: 13px;
  margin: 5px 0;
}

.comment-input {
  padding: 8px;
  width: 250px;
  margin-right: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.comment-btn {
  padding: 8px 15px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.comment-btn:hover {
  background: #3aa876;
}

.comments ul {
  list-style: none;
  padding: 0;
  margin: 8px 0;
}

.comments li {
  background: #fff;
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 13px;
  color: #555;
}
</style>