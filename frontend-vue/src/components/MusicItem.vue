<template>
  <div class="music-item">
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

    <div class="info">
      <h3
        class="album-name"
        @click="goToAlbumDetail"
        style="cursor: pointer; color: #42b983;"
      >
        {{ music.album_name || '未知专辑' }}
      </h3>
      <p class="singer"><strong>歌手：</strong>{{ music.singer || '未知' }}</p>
      <p class="year"><strong>发行年份：</strong>{{ music.release_year || '未知' }}</p>
      <p class="type"><strong>主要类型：</strong>{{ (music.main_type && music.main_type.length > 0) ? music.main_type[0] : '未知' }}</p>
      <p class="tags"><strong>标签：</strong>{{ (music.tags && music.tags.length > 0) ? music.tags.join('、') : '无' }}</p>
      <p class="score"><strong>评分：</strong>{{ music.my_score || 0 }}</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    music: {
      type: Object,
      required: true,
      default: () => ({})
    }
  },
  data() {
    return {
      newComment: ''
    }
  },
  methods: {
    goToAlbumDetail() {
      if (!this.music.id) { // 改回后端实际的id
        alert('专辑ID不存在，无法查看详情！');
        return;
      }
      this.$router.push({
        path: `/album/detail/${this.music.id}`, // 改回id
        query: {id: this.music.id}
      });
    },
    submitComment() {
      const comment = this.newComment.trim()
      if (!comment) {
        alert('评论不能为空！')
        return
      }
      this.$emit('add-comment', {
        musicId: this.music.id, // 改回id
        comment: comment,
        score: 0
      })
      this.newComment = ''
    }
  }
}
</script>

<style scoped>
/* 样式不变，保留原有 */
.music-item {
  display: flex;
  gap: 20px;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 10px;
  margin-bottom: 20px;
  background: #f9f9f9;
}

.cover {
  width: 160px;
  height: 160px;
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
  object-fit: cover;
}

.no-cover {
  color: #999;
  font-size: 12px;
  text-align: center;
}

.info {
  flex: 1;
}

.album-name {
  margin: 0 0 10px 0;
  font-size: 18px;
  transition: all 0.2s;
}

.album-name:hover {
  color: #3aa876;
  text-decoration: underline;
}

.singer, .year, .type, .tags, .score {
  margin: 5px 0;
  color: #666;
  font-size: 14px;
}

.score {
  color: #e67e22;
  font-weight: 600;
}

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