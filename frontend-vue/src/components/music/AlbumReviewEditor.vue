<template>
  <div class="tab-content">
    <h2>{{ album.album_name || '未知专辑' }}——听后感</h2>
    <div class="audio-link">[{{ album.album_name || '未知' }}.mp3]</div>

    <!-- 新增听后感区域 -->
    <div class="review-edit-area">
      <textarea
        v-model="newFeelingContent"
        placeholder="输入你的听后感..."
        class="review-textarea"
        rows="3"
      ></textarea>
      <div class="review-actions">
        <button @click="handleAddReview" class="save-btn">新增听后感</button>
        <button @click="handleDeleteAll" class="delete-btn" v-if="(album.review || {}).feelings?.length">清空所有听后感</button>
      </div>
    </div>

    <!-- 所有听后感列表 -->
    <div class="feelings-list" v-if="(album.review || {}).feelings?.length">
      <h3>历史听后感</h3>
      <div
        class="feeling-item"
        v-for="(feeling, idx) in (album.review || {}).feelings"
        :key="feeling.id || idx"
      >
        <div class="feeling-content">{{ feeling.content }}</div>
        <div class="feeling-meta">
          <span class="create-time">{{ feeling.create_time }}</span>
          <button class="delete-single-btn" @click="handleDeleteSingle(feeling.id)">删除</button>
        </div>
      </div>
    </div>
    <p class="no-feeling" v-else>暂无听后感记录，快来添加吧~</p>

    <!-- 单曲评分部分 -->
    <div class="score-section">
      <h4>单曲评分</h4>
      <div v-for="(track, idx) in (album.tracks || [])" :key="idx" class="track-score-item">
        <p>{{ track.score || 0 }}->>>{{ idx+1 }}. {{ track.track_name || '未知曲目' }}  {{ track.duration || '0:00' }}</p>
      </div>
      <p class="final-score">最终评分：{{ album.my_score || 0.0 }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumReviewEditor',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    }
  },
  data() {
    return {
      newFeelingContent: ''
    };
  },
  methods: {
    // 新增听后感
    handleAddReview() {
      this.$emit('add-review', this.newFeelingContent);
      this.newFeelingContent = '';
    },
    // 删除单条听后感
    handleDeleteSingle(feelingId) {
      this.$emit('delete-single', feelingId);
    },
    // 清空所有听后感
    handleDeleteAll() {
      this.$emit('delete-all');
    }
  }
};
</script>

<style scoped>
.audio-link {
  color: #007acc;
  margin: 10px 0;
  font-size: 14px;
}

.review-edit-area {
  margin: 20px 0;
}

.review-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  margin-bottom: 10px;
}

.review-actions {
  margin-bottom: 15px;
}

.save-btn {
  padding: 8px 20px;
  background: #42b983;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
}

.delete-btn {
  padding: 8px 20px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.feelings-list {
  margin: 20px 0;
}

.feeling-item {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid #eee;
}

.feeling-content {
  color: #333;
  line-height: 1.6;
  margin-bottom: 10px;
}

.feeling-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.delete-single-btn {
  padding: 4px 8px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.delete-single-btn:hover {
  background: #c0392b;
}

.no-feeling {
  color: #999;
  text-align: center;
  margin: 20px 0;
  font-size: 14px;
}

.score-section {
  margin: 20px 0;
  font-size: 14px;
}

.track-score-item {
  margin-bottom: 4px;
}

.final-score {
  margin-top: 10px;
  font-weight: 600;
  color: #42b983;
}
</style>