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
        <!-- 新增听后感按钮 - 加深色，有内容可用，无内容灰色禁用 -->
        <button
          @click="handleAddReview"
          class="save-btn"
          :disabled="!newFeelingContent.trim()"
          :style="{backgroundColor: newFeelingContent.trim() ? mainColorDark : '#999'}"
        >新增听后感</button>
        <!-- 清空按钮 - 加深色 -->
        <button
          @click="handleDeleteAll"
          class="delete-btn"
          v-if="(album.review || {}).feelings?.length"
          :style="{backgroundColor: mainColorDark}"
        >清空所有听后感</button>
      </div>
    </div>

    <!-- 所有听后感列表 -->
    <div class="feelings-list" v-if="(album.review || {}).feelings?.length">
      <h3 :style="{color: mainColor}">历史听后感</h3>
      <div
        class="feeling-item"
        v-for="(feeling, idx) in (album.review || {}).feelings"
        :key="feeling.id || idx"
      >
        <div class="feeling-content">{{ feeling.content }}</div>
        <div class="feeling-meta">
          <span class="create-time">{{ feeling.create_time }}</span>
          <!-- 删除按钮 - 加深色 -->
          <button class="delete-single-btn" @click="handleDeleteSingle(feeling.id)" :style="{backgroundColor: mainColorDark}">删除</button>
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
      <p class="final-score" :style="{color: mainColor}">最终评分：{{ album.my_score || 0.0 }}</p>
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
      newFeelingContent: '',
      mainColor: '#42b983', // 默认主色
      mainColorDark: '#2f9465' // 主色加深色（所有按钮统一用）
    };
  },
  watch: {
    album: {
      immediate: true,
      handler(newVal) {
        if(newVal.cover_img) this.extractMainColor(newVal.cover_img);
        else {
          this.mainColor = '#42b983';
          this.mainColorDark = '#2f9465';
        }
      }
    }
  },
  methods: {
    extractMainColor(imgUrl) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 10;
        canvas.height = 10;
        ctx.drawImage(img, 0, 0, 10, 10);
        const data = ctx.getImageData(0,0,10,10).data;
        let r=0,g=0,b=0,c=0;
        for(let i=0;i<data.length;i+=4){r+=data[i];g+=data[i+1];b+=data[i+2];c++}
        r=Math.floor(r/c);g=Math.floor(g/c);b=Math.floor(b/c);
        const hex = `#${((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1)}`;
        this.mainColor = hex;
        this.mainColorDark = this.darkenColor(hex, 0.3);
      };
      img.onerror = () => {
        this.mainColor = '#42b983';
        this.mainColorDark = '#2f9465';
      };
      img.src = imgUrl;
    },
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1,3),16)*(1-amount);
      const g = parseInt(hex.slice(3,5),16)*(1-amount);
      const b = parseInt(hex.slice(5,7),16)*(1-amount);
      return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`;
    },
    handleAddReview() {
      this.$emit('add-review', this.newFeelingContent);
      this.newFeelingContent = '';
    },
    handleDeleteSingle(feelingId) {
      this.$emit('delete-single', feelingId);
    },
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
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
  transition: all 0.2s;
}
.save-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.save-btn:hover:not(:disabled) {
  background-color: #257d51 !important;
  opacity: 0.95;
}

.delete-btn {
  padding: 8px 20px;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.delete-btn:hover {
  background-color: #257d51 !important;
  opacity: 0.95;
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
  color: white;
  border: none;
	border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.delete-single-btn:hover {
  background-color: #257d51 !important;
  opacity: 0.95;
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
}
</style>