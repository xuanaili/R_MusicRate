<template>
  <div class="music-item">
    <div class="cover" @click="goToAlbumDetail">
      <img
        v-if="music.cover_img && music.cover_img.trim() !== ''"
        :src="coverThumb(music.cover_img)"
        alt="专辑封面"
        width="80"
        height="80"
        loading="lazy"
        @click="goToAlbumDetail"
      >
      <div v-else class="no-cover">暂无封面</div>
    </div>

    <div class="info">
      <!-- ✅ 核心修改1：专辑名+评分 外层包裹容器，用于加统一横线 -->
      <div class="album-name-score-wrapper">
        <h3 class="album-name" @click="goToAlbumDetail">
          <strong>{{ music.album_name || '未知专辑' }}</strong>
        </h3>
        <!-- 评分放到专辑名右侧 -->
        <span class="album-total-score"><strong>{{ albumTotalScore }}分</strong></span>
      </div>

      <p class="singer"><strong>歌手：</strong>{{ music.singer || '未知' }}</p>
      <p class="year"><strong>发行年份：</strong>{{ music.release_year || '未知' }}</p>
      <p class="type"><strong>时长类型：</strong>{{ music.duration_type || '未知' }}</p>
      <p class="duration"><strong>已听时长：</strong>{{ formatDuration(music.listening_duration || 0) }}</p>
      <!-- 标签：只显示英文、鼠标悬浮显示中文 -->
      <p class="tags">
        <strong>标签：</strong>
        <span
          v-for="(tagItem, index) in music.tags"
          :key="index"
          class="tag-item"
          :title="getTagChinese(tagItem)"
        >
          {{ getTagEnglish(tagItem) }}
        </span>
        <span v-if="!music.tags || music.tags.length === 0">无</span>
      </p>
    </div>
  </div>
</template>

<script>
// 引入公共的评分计算方法
import { calculateAlbumTotalScore } from '@/utils/scoreCalc.js';
// 引入封面缩略图工具（列表页小图用缩略图URL）
import { coverThumb as coverThumbUtil } from '@/utils/cover.js';

export default {
  props: {
    music: {
      type: Object,
      required: true,
      default: () => ({})
    },
    mainColor: {
      type: String,
      default: 'transparent'
    },
    mainColorDark: {
      type: String,
      default: 'transparent'
    },
    mainColorDarkDouble: {
      type: String,
      default: 'transparent'
    }
  },
  data() {
    return {
      newComment: ''
    }
  },
  // 评分数据源改为 my_score + 处理字符串数组格式转换
  computed: {
    albumTotalScore() {

      if (this.music.calculated_score !== undefined) {
        return this.music.calculated_score;
      }


      // 1. 获取原始的字符串格式评分数据




      const scoreStr = this.music.my_score || '';
      // 2. 格式化转换：字符串数组 → 真实的数字数组
      const scoreList = this.formatScoreStrToArray(scoreStr);
      // 3. 调用公共方法计算综合评分
      return calculateAlbumTotalScore(scoreList);
    }
  },
  methods: {
    // 列表页小图用缩略图URL（挂到methods便于模板解析）
    coverThumb(url) {
      return coverThumbUtil(url);
    },
    goToAlbumDetail() {
      if (!this.music.id) {
        alert('专辑ID不存在，无法查看详情！');
        return;
      }
      this.$router.push({
        path: `/album/detail/${this.music.id}`,
        query: { id: this.music.id }
      });
    },
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
    },
    // my_score 字符串格式数组 转 数字数组（容错性拉满）
    formatScoreStrToArray(scoreStr) {
      let scoreArr = []
      if (!scoreStr || typeof scoreStr !== 'string' || scoreStr.trim() === '') {
        return scoreArr
      }
      try {
        scoreArr = JSON.parse(scoreStr)
        scoreArr = scoreArr.filter(item => typeof item === 'number' && !isNaN(item) && item >= 0)
      } catch (error) {
        scoreArr = []
      }
      return scoreArr
    },
    // 已听时长：秒数 转 xxxhxxmin 格式
    formatDuration(seconds) {
      const sec = Number(seconds);
      if (isNaN(sec) || sec <= 0) return '0min';
      const hours = Math.floor(sec / 3600);
      const mins = Math.floor((sec % 3600) / 60);
      if (hours === 0) return `${mins}min`;
      if (mins === 0) return `${hours}h`;
      return `${hours}h${mins}min`;
    },
    // 标签：提取英文展示
    getTagEnglish(tagStr) {
      if (!tagStr || typeof tagStr !== 'string') return '';
      const splitIndex = tagStr.indexOf('【');
      return splitIndex > -1 ? tagStr.substring(0, splitIndex).trim() : tagStr.trim();
    },
    // 标签：提取中文做悬浮提示
    getTagChinese(tagStr) {
      if (!tagStr || typeof tagStr !== 'string') return '';
      const start = tagStr.indexOf('【');
      const end = tagStr.indexOf('】');
      return start > -1 && end > start ? tagStr.substring(start + 1, end).trim() : tagStr.trim();
    }
  }
}
</script>

<style scoped>
.music-item {
  display: flex;
  gap: 20px;
  padding: 20px;
	border-radius: 10px;
	margin-bottom: 20px;
	background: rgba(255, 255, 255, 0.25);
	backdrop-filter: blur(4px);
	border: none;
	box-sizing: border-box;
	width: 100%;
}
.cover {
	width: 160px;
	height: 160px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 6px;
	overflow: hidden;
  cursor: pointer;
}
.cover img {
	width: 100%;
	height: 100%;
	object-fit: cover;
  cursor: pointer;
}
.no-cover {
	color: #999;
	font-size: 12px;
	text-align: center;
}
.info {
	flex: 1;
}

/* ✅✅✅ 核心新增+修改 开始 - 完全匹配升序/降序的横线样式 */
/* 专辑名+评分的外层容器 - 相对定位 用于加底部横线 */
.album-name-score-wrapper {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin: 0 0 12px 0;
  padding-bottom: 4px;
}
/* 专辑名字体样式 */
.album-name {
	margin: 0;
	font-size: 18px;
	transition: all 0.2s;
	cursor: pointer;
	color: v-bind(mainColorDark);
	font-weight: normal;
}
.album-name:hover {
	color: v-bind(mainColorDarkDouble);
	text-decoration: underline;
}
/* 右侧评分的样式 */
.album-total-score {
	font-size: 16px;
	color: v-bind(mainColorDark);
	font-weight: 600;
}
/* ✅ 重中之重：和升序/降序 1:1 一致的横线样式 */
.album-name-score-wrapper::after {
	content: '';
	position: absolute;
	left: 0;
	bottom: 0;
	width: 100%;
	height: 4px;
	border-radius: 2px;
	background-color: v-bind(mainColorDark) !important;
	opacity: 1 !important;
}
/* ✅✅✅ 核心新增+修改 结束 */

/* 歌手/年份/类型/标签/时长 统一样式 */
.singer, .year, .type, .tags, .duration {
	margin: 5px 0;
	color: v-bind(mainColorDark);
	font-size: 14px;
}
.tag-item {
	margin-right: 8px;
	cursor: default;
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
	background: v-bind(mainColorDark);
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 13px;
}
.comment-btn:hover {
	background: v-bind(mainColorDarkDouble);
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