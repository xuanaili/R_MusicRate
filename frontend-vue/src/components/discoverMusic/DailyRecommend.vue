<template>
  <div class="discover-page-container">

    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="!albumData" class="empty-tip">今日暂无推荐专辑</div>

    <!-- 核心布局：和AlbumPoolDetail.vue完全一致的 左-中-右 三栏布局 -->
    <div v-else class="album-detail-wrapper">
      <!-- 左侧：放大版基础信息/简介 滑动切换面板 + 左侧更换箭头 + 右侧简介箭头 左右对称 -->
      <div class="album-left-section" :class="{ 'slide-to-intro': showIntro }">
        <div class="album-panel info-panel">
          <!-- ✅✅✅ 核心修改1：封面添加点击事件 @click="copyAlbum" + 鼠标悬浮指针样式 -->
          <div class="cover" @click="copyAlbum">
            <img v-if="albumData.cover_img" :src="albumData.cover_img" alt="封面" class="detail-cover">
            <div v-else class="no-cover">暂无封面</div>
          </div>
          <div class="info-mask">
            <div class="info">
              <h3 :style="{color: mainColorDarkDouble}">{{ albumData.album_name }}</h3>
              <p :style="{color: mainColorDarkDouble}">歌手：{{ albumData.singer }}</p>
              <p :style="{color: mainColorDarkDouble}">发行年份：{{ albumData.release_year }}</p>
              <p :style="{color: mainColorDarkDouble}">时长类型：{{ albumData.duration_type || 'LP' }}</p>
              <p :style="{color: mainColorDarkDouble}">
                创建用户：{{ albumData.create_user_name || albumData.create_user || '未知用户' }}</p>
              <p class="create-time" :style="{color: mainColorDarkDouble}">
                创建时间：{{ formatCreateTime(albumData.create_time) }}</p>
            </div>
          </div>
          <!-- ✅✅✅ 核心修改2：彻底删除 添加按钮的 actions 容器 -->

        </div>

        <div class="album-panel intro-panel">
          <h4 class="intro-title" :style="{borderBottomColor: mainColor}">专辑简介</h4>
          <div class="intro-mask">
            <div v-if="albumData.album_intro && albumData.album_intro.trim()" class="intro-content">
              {{ albumData.album_intro }}</div>
            <div v-else class="no-intro-tip">暂无专辑简介</div>
          </div>
        </div>

        <!-- 替换为 SVG 图标按钮 -->
        <div class="change-toggle-btn" @click="changeTodayRecommend" :style="{backgroundColor: mainColorDarkDouble}"
             :disabled="changeLoading">
          <div class="icon-arrow change-arrow">
            <img src="/重置.svg" alt="刷新推荐" class="refresh-svg-icon" />
          </div>
        </div>

        <div class="slide-toggle-btn" @click="showIntro = !showIntro" :style="{backgroundColor: mainColorDarkDouble}">
          <i class="icon-arrow" :class="showIntro ? 'arrow-left' : 'arrow-right'">
            {{ showIntro ? '←' : '→' }}
          </i>
        </div>
      </div>

      <!-- 中间：收窄版单曲列表 -->
      <div class="album-center-section">
        <div class="album-songs-list">
          <h4 class="songs-title" :style="{borderBottomColor: mainColor}">单曲列表</h4>
          <div v-if="!albumData.tracks || albumData.tracks.length === 0" class="no-songs-tip">暂无单曲信息</div>
          <ul class="songs-list" v-else>
            <li class="song-item" v-for="(song, index) in albumData.tracks" :key="index">
              <span class="song-index" :style="{backgroundColor: mainColorDark}">{{ index + 1 }}</span>
              <span class="song-name">{{ song }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- 右侧：用户固定高度+专辑风格占满剩余空间 -->
      <div class="album-right-section">
        <div class="album-recent-users">
          <h4 class="users-title" :style="{borderBottomColor: mainColor}">最近收听用户</h4>
          <div class="users-scroll-wrapper">
            <div class="no-users-tip" v-if="recentUsers.length === 0">暂无用户添加该专辑</div>
            <ul class="users-list" v-else>
              <li class="user-item" v-for="(user, idx) in recentUsers" :key="idx">
                <span class="user-avatar" :style="{backgroundColor: mainColorDark}">{{ user.name.slice(0, 1) }}</span>
                <span class="user-name">{{ user.name }}</span>
                <span class="user-time" :style="{color: mainColorDarkDouble}">{{ user.listenTime }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="album-style-chart">
          <h4 class="style-title" :style="{borderBottomColor: mainColor}">专辑风格</h4>
          <TagBubbleChart
              :tag-stats="tagChartData"
              :loading="chartLoading"
              :main-color="mainColor"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import TagBubbleChart from '@/components/TagBubbleChart.vue'

export default {
  name: "DailyRecommend",
  components: {TagBubbleChart},
  data() {
    return {
      albumData: null,
      loading: false,
      chartLoading: false,
      tagChartData: [],
      recentUsers: [],
      showIntro: false,
      mainColor: 'transparent',
      mainColorDark: 'transparent',
      mainColorDarkDouble: 'transparent',
      recommendId: null,
      changeLoading: false
    }
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    this.getTodayRecommend();
  },
  methods: {
    formatCreateTime(timeStr) {
      if (!timeStr || timeStr === '') return '未知';
      let date;
      try {
        date = new Date(timeStr);
        if (isNaN(date.getTime())) return '未知';
      } catch (e) {
        return '未知';
      }
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    },
    extractAlbumMainColor(imgUrl) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 10;
        canvas.height = 10;
        ctx.drawImage(img, 0, 0, 10, 10);
        const data = ctx.getImageData(0, 0, 10, 10).data;
        let r = 0, g = 0, b = 0, c = 0;
        for (let i = 0; i < data.length; i += 4) {
          r += data[i];
          g += data[i + 1];
          b += data[i + 2];
          c++
        }
        r = Math.floor(r / c);
        g = Math.floor(g / c);
        b = Math.floor(b / c);
        const hex = `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
        this.mainColor = hex;
        this.mainColorDark = this.darkenColor(hex, 0.3);
        this.mainColorDarkDouble = this.darkenColor(hex, 0.5);

        this.$emit('sendThemeColor', {
          mainColor: this.mainColor,
          mainColorDark: this.mainColorDark,
          mainColorDarkDouble: this.mainColorDarkDouble
        })
      };
      img.onerror = () => {
        this.mainColor = 'transparent';
        this.mainColorDark = 'transparent';
        this.mainColorDarkDouble = 'transparent';
        this.$emit('sendThemeColor', {
          mainColor: this.mainColor,
          mainColorDark: this.mainColorDark,
          mainColorDarkDouble: this.mainColorDarkDouble
        })
      };
      img.src = imgUrl;
    },
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1, 3), 16) * (1 - amount);
      const g = parseInt(hex.slice(3, 5), 16) * (1 - amount);
      const b = parseInt(hex.slice(5, 7), 16) * (1 - amount);
      return `#${Math.round(r).toString(16).padStart(2, 0)}${Math.round(g).toString(16).padStart(2, 0)}${Math.round(b).toString(16).padStart(2, 0)}`;
    },
    getTodayRecommend() {
      this.loading = true;
      this.$axios({
        url: `/api/recommend/today`,
        method: 'GET',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200 && res.data.data) {
              this.albumData = res.data.data;
              this.recommendId = this.albumData.id;
              if (typeof this.albumData.tracks === 'string') {
                try {
                  this.albumData.tracks = JSON.parse(this.albumData.tracks);
                } catch {
                  this.albumData.tracks = [];
                }
              }
              const coverUrl = this.albumData.cover_img || ''
              this.$emit('sendCoverBg', coverUrl)
              if (coverUrl) this.extractAlbumMainColor(coverUrl);

              this.getAlbumTagStats(this.recommendId);
              this.getAlbumPoolUsers(this.recommendId);
            } else {
              this.albumData = null;
              this.$emit('sendCoverBg', '')
            }
          })
          .catch(err => {
            this.loading = false;
            console.error('获取今日推荐失败：', err);
            this.$emit('sendCoverBg', '')
          });
    },
    getAlbumTagStats(poolId) {
      this.chartLoading = true;
      this.$axios({
        url: `/api/album/${poolId}/tag-statistics`,
        method: 'GET',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            this.chartLoading = false;
            this.tagChartData = res.data.data || [];
          })
          .catch(err => {
            this.chartLoading = false;
            console.error('获取专辑风格数据失败：', err);
          });
    },
    getAlbumPoolUsers(poolId) {
      this.$axios({
        url: `/api/album/pool/users/${poolId}`,
        method: 'GET',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            this.recentUsers = res.data.data || [];
          })
          .catch(err => {
            console.error('获取专辑用户列表失败：', err);
            this.recentUsers = [];
          });
    },
    // ✅ 无改动：原有添加逻辑保留，现在由封面点击触发
    copyAlbum() {
      if (!this.recommendId) return;
      this.$axios({
        url: `/api/album/pool/copy/${this.recommendId}`,
        method: 'POST',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            const { code, data } = res.data;
            if (code === 200) {
              window.targetTab = 'mymusic';
              this.$router.push('/webhome');
            } else {
              if (code === 409 && data) {
                const duplicateAlbumId = Number(data) || data;
                this.$router.push(`/album/detail/${duplicateAlbumId}?id=${duplicateAlbumId}`);
              }
            }
          })
          .catch(err => {
            console.error('复制专辑失败：', err);
          });
    },
    changeTodayRecommend() {
      if (this.changeLoading) return;
      this.changeLoading = true;
      this.$axios({
        url: `/api/recommend/change-today`,
        method: 'POST',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            this.changeLoading = false;
            if (res.data.code === 200) {
              this.getTodayRecommend();
            } else {
              alert('刷新失败：' + res.data.msg);
            }
          })
          .catch(err => {
            this.changeLoading = false;
            console.error('刷新今日推荐失败：', err);
            alert('刷新失败，请稍后重试');
          })
    }
  }
};
</script>

<style scoped>
.discover-page-container {
  color: #333;
  width: 100%;
}

.loading-tip, .empty-tip {
  text-align: center;
  color: #666;
  padding: 30px 0;
  font-size: 16px;
}

.album-detail-wrapper {
  margin-top: 20px;
  display: flex;
  align-items: flex-start;
  gap: 25px;
  width: 100%;
  align-items: stretch;
}

.album-left-section {
  flex: 1.8;
  min-width: 450px;
  max-width: 500px;
  height: 720px;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.5s ease;
}

.album-panel {
  position: absolute;
  top: 0;
	left: 0;
  width: 100%;
  height: 100%;
  padding: 0px;
  box-sizing: border-box;
  transition: all 0.5s ease;
}

.info-panel {
  opacity: 1;
  z-index: 2;
}

.intro-panel {
  opacity: 0;
  z-index: 1;
  transform: translateX(50px);
}

.slide-to-intro .info-panel {
  opacity: 0;
  transform: translateX(-50px);
  z-index: 1;
}

.slide-to-intro .intro-panel {
  opacity: 1;
  transform: translateX(0);
  z-index: 2;
}

/* ✅✅✅ 核心修改3：封面样式新增 鼠标指针 + 点击轻微缩放动画 提升交互体验 */
.cover {
  width: 260px;
  height: 260px;
  margin: 40px auto 20px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.cover:hover {
  transform: scale(1.02);
}
.cover:active {
  transform: scale(0.98);
}

.detail-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-cover {
  color: #999;
  font-size: 16px;
}

.info-mask {
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 6px;
	padding: 15px 20px;
  margin: 0 auto 25px;
  width: 380px;
  box-sizing: border-box;
}

.info {
  text-align: center;
  width: 100%;
  box-sizing: border-box;
}

.info h3 {
  font-size: 24px;
  color: #333;
  margin-bottom: 20px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  font-weight: 600;
}

.info p {
  margin: 12px 0;
  font-size: 17px;
  font-weight: 500;
}

.info .create-time {
  font-size: 15px;
  display: block;
  margin-top: 10px;
}

/* ✅✅✅ 核心修改4：彻底删除 copy-btn、actions 相关所有样式代码 */

.intro-title, .songs-title, .users-title, .style-title {
  font-size: 18px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
	padding: 15px 20px 8px;
  margin: 0 !important;
  width: 100%;
  box-sizing: border-box;
  text-align: left;
  width: calc(100% - 40px);
  margin: 0 auto !important;
  position: relative;
}

.intro-title::after,
.songs-title::after,
.users-title::after,
.style-title::after {
  content: '';
  position: absolute;
	left: 0;
	bottom: 0;
	width: 100%;
	height: 7px;
	border-radius: 2px;
  background-color: v-bind(mainColorDarkDouble);
}

.intro-mask {
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
	border-radius: 6px;
  margin: 12px 20px 0;
  padding: 10px;
  height: calc(100% - 80px);
  box-sizing: border-box;
}

.intro-content {
  font-size: 16px;
  color: #333;
  line-height: 1.8;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-y: auto;
  height: 100%;
  padding-right: 5px;
  background: transparent !important;
}

.intro-content::-webkit-scrollbar {
  width: 6px;
}
.intro-content::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius: 3px;
}
.intro-content::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDark);
}
.intro-content::-webkit-scrollbar-track {
  background: transparent !important;
}
.intro-content::-webkit-scrollbar-button {
  display: none !important;
}

.no-intro-tip {
  color: #999;
  text-align: center;
	padding: 60px 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin: 0;
}

.no-songs-tip {
  color: #999;
  text-align: center;
	padding: 12px 20px 20px;
}

.songs-list {
  list-style: none;
  padding: 12px 20px 0;
  margin: 0;
  max-height: calc(100% - 60px);
  overflow-y: auto;
  padding-right: 5px;
  background: transparent !important;
}

.songs-list::-webkit-scrollbar {
  width: 6px;
}
.songs-list::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius: 3px;
}
.songs-list::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDark);
}
.songs-list::-webkit-scrollbar-track {
  background: transparent !important;
}
.songs-list::-webkit-scrollbar-button {
  display: none !important;
}

.song-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.3);
	border-radius: 6px;
}

.song-index {
  display: inline-block;
  width: 26px;
  height: 26px;
  line-height: 26px;
  text-align: center;
  color: white;
  font-size: 14px;
  border-radius: 3px;
  margin-right: 18px;
}

.song-name {
  font-size: 16px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.album-center-section {
  flex: 1.2;
  min-width: 300px;
  max-width: 350px;
  height: 720px;
}

.album-songs-list {
  padding: 0 !important;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
	border-radius: 8px;
	height: 100%;
  box-sizing: border-box;
}

.album-right-section {
  flex: 0.8;
  min-width: 220px;
  max-width: 500px;
  height: 720px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.album-recent-users {
  padding: 0 !important;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 8px;
  height: 250px;
  box-sizing: border-box;
}

.users-scroll-wrapper {
  height: calc(100% - 50px);
  overflow-y: auto;
  padding: 12px 20px 0;
}

.users-scroll-wrapper::-webkit-scrollbar {
  width: 4px;
}

.users-scroll-wrapper::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 2px;
}

.users-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.user-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.3);
	border-radius: 6px;
  font-size: 14px;
}

.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  margin-right: 8px;
}

.user-name {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.user-time {
  font-size: 12px;
}

.album-style-chart {
  padding: 0 !important;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 8px;
  flex: 1;
  min-height: 320px;
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
}

.album-style-chart >>> .tag-bubble-chart-container {
  padding: 12px 20px 20px !important;
  box-sizing: border-box;
  width: 100%;
  height: calc(100% - 55px) !important;
  position: relative;
}

.slide-toggle-btn {
  position: absolute;
  top: 50%;
  right: 0px;
  transform: translateY(-50%);
  width: 24px;
  height: auto;
  min-height: 48px;
  color: #fff;
	border-radius: 12px 0 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 99;
  transition: all 0.3s ease;
  padding: 5px 0;
  pointer-events: auto;
}

.change-toggle-btn {
  position: absolute;
  top: 50%;
  left: 0px;
  transform: translateY(-50%);
  width: 24px;
  height: auto;
  min-height: 48px;
  color: #fff;
	border-radius: 0 12px 12px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
	box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 99;
  transition: all 0.3s ease;
  padding: 5px 0;
  pointer-events: auto;
}

.slide-toggle-btn:hover, .change-toggle-btn:hover {
  opacity: 0.95;
}

.icon-arrow {
  font-size: 18px;
  font-weight: bold;
  line-height: 1;
}

.refresh-svg-icon {
  width: 18px;
  height: 18px;
  display: block;
  fill: #ffffff !important;
  color:#ffffff;
   filter: invert(100%);
}

.change-arrow {
  animation: rotate 2s linear infinite;
  animation-play-state: paused;
  transform-origin: center center;
}

.change-toggle-btn:hover .change-arrow {
  animation-play-state: running;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.change-toggle-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.change-toggle-btn:disabled .change-arrow {
  animation-play-state: paused !important;
}

.change-toggle-btn:disabled .refresh-svg-icon {
  fill: rgba(255, 255, 255, 0.8);
}

@media (max-width: 1200px) {
  .album-detail-wrapper {
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .album-left-section {
    max-width: 100%;
    flex: 1 1 100%;
  }

  .album-center-section {
    flex: 1 1 100%;
    min-width: 100%;
    max-width: 100%;
    margin-top: 20px;
    height: auto;
  }

  .album-right-section {
    flex: 1 1 100%;
    min-width: 100%;
    max-width: 100%;
    marginTop: 20px;
    height: auto;
    flex-direction: row;
    gap: 20px;
  }

  .album-recent-users {
    flex: 1;
    height: 300px;
  }

  .album-style-chart {
    flex: 1;
    min-height: 300px;
  }
}

@media (max-width: 768px) {
  .album-right-section {
    flex-direction: column;
  }

  .album-recent-users {
    height: 280px;
  }

  .album-style-chart {
    min-height: 250px;
  }
}
</style>