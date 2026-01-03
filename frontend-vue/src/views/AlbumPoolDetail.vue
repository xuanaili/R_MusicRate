<template>
  <div class="pool-detail-container">
    <!-- ✅ 全屏独立模糊封面背景层 - 和AlbumDetail完全一致 -->
    <div class="bg-layer" :style="bgStyle"></div>

    <!-- 管理员修改按钮 -->
    <div v-if="isAdmin" class="edit-btn-container">
      <button @click="goEditAlbum" class="edit-btn" :style="{backgroundColor: mainColorDark}">修改专辑信息</button>
    </div>

    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="!albumData" class="empty-tip">未找到该公共专辑</div>
    <!-- 核心布局：左(放大基础信息+箭头左移) | 中(收窄单曲列表) | 右(用户固定高+风格占满) -->
    <div v-else class="album-detail-wrapper">
      <!-- 左侧：放大版基础信息/简介 滑动切换面板 + 箭头左移露全 -->
      <div class="album-left-section" :class="{ 'slide-to-intro': showIntro }">
        <!-- 专辑基础信息面板（放大） -->
        <div class="album-panel info-panel">
          <div class="cover">
            <img v-if="albumData.cover_img" :src="albumData.cover_img" alt="封面" class="detail-cover">
            <div v-else class="no-cover">暂无封面</div>
          </div>
          <!-- ✅ 外层增加蒙版容器 - 和收听用户一致的白色磨砂层 -->
          <div class="info-mask">
            <div class="info">
              <h3>{{ albumData.album_name }}</h3>
              <p :style="{color: mainColorDarkDouble}">歌手：{{ albumData.singer }}</p>
              <p :style="{color: mainColorDarkDouble}">发行年份：{{ albumData.release_year }}</p>
              <p :style="{color: mainColorDarkDouble}">时长类型：{{ albumData.duration_type|| 'LP' }}</p>
              <p :style="{color: mainColorDarkDouble}">创建用户：{{ albumData.create_user_name || albumData.create_user || '未知用户' }}</p>
              <p class="create-time" :style="{color: mainColorDarkDouble}">创建时间：{{ formatCreateTime(albumData.create_time) }}</p>
            </div>
          </div>
          <div class="actions">
            <button @click="copyAlbum" class="copy-btn" :style="{backgroundColor: mainColorDarkDouble}">添加</button>
            <button @click="goBack" class="back-btn">返回</button>
          </div>
        </div>

        <!-- 专辑简介面板（放大） -->
        <div class="album-panel intro-panel">
          <h4 class="intro-title" :style="{borderBottomColor: mainColor}">专辑简介</h4>
          <!-- ✅ 外层增加蒙版容器 - 和收听用户一致的白色磨砂层 -->
          <div class="intro-mask">
            <div v-if="albumData.album_intro && albumData.album_intro.trim()" class="intro-content">
              {{ albumData.album_intro }}
            </div>
            <div v-else class="no-intro-tip">暂无专辑简介</div>
          </div>
        </div>

        <!-- 切换箭头左移露全 - 主色加深色 -->
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
        <!-- 最近收听用户：固定高度250px+内部滚动+宽度收窄 -->
        <div class="album-recent-users">
          <h4 class="users-title" :style="{borderBottomColor: mainColor}">最近收听用户</h4>
          <div class="users-scroll-wrapper">
            <div class="no-users-tip" v-if="recentUsers.length === 0">暂无用户添加该专辑</div>
            <ul class="users-list" v-else>
              <li class="user-item" v-for="(user, idx) in recentUsers" :key="idx">
                <span class="user-avatar" :style="{backgroundColor: mainColorDark}">{{ user.name.slice(0,1) }}</span>
                <span class="user-name">{{ user.name }}</span>
                <span class="user-time" :style="{color: mainColorDarkDouble}">{{ user.listenTime }}</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- 专辑风格：占满右侧剩余所有高度 -->
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
  name: 'AlbumPoolDetail',
  components: {TagBubbleChart},
  data() {
    return {
      albumData: null,
      loading: false,
      chartLoading: false,
      isAdmin: false,
      tagChartData: [],
      recentUsers: [],
      showIntro: false,
      bgStyle: {},
      mainColor: 'transparent',
      mainColorDark: 'transparent',
      mainColorDarkDouble: 'transparent'
    }
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    this.isAdmin = localStorage.getItem('is_admin') === '1';
    const poolId = this.$route.params.poolId;
    this.getPoolAlbumDetail(poolId);
    this.getAlbumTagStats(poolId);
    this.getAlbumPoolUsers(poolId);
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
        const data = ctx.getImageData(0,0,10,10).data;
        let r=0,g=0,b=0,c=0;
        for(let i=0;i<data.length;i+=4){r+=data[i];g+=data[i+1];b+=data[i+2];c++}
        r=Math.floor(r/c);g=Math.floor(g/c);b=Math.floor(b/c);
        const hex = `#${((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1)}`;
        this.mainColor = hex;
        this.mainColorDark = this.darkenColor(hex, 0.3);
        this.mainColorDarkDouble = this.darkenColor(hex, 0.5);
      };
      img.onerror = () => {
        this.mainColor = '#42b983';
        this.mainColorDark = '#2f9465';
        this.mainColorDarkDouble = '#257750';
      };
      img.src = imgUrl;
    },
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1,3),16)*(1-amount);
      const g = parseInt(hex.slice(3,5),16)*(1-amount);
      const b = parseInt(hex.slice(5,7),16)*(1-amount);
      return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`;
    },
    setFullPageBg(coverImg) {
      if (coverImg) {
        this.bgStyle = {
          backgroundImage: `url(${coverImg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }
      } else {
        this.bgStyle = { backgroundColor: '#f9f9f9' };
      }
    },
    getPoolAlbumDetail(poolId) {
      this.loading = true;
      this.$axios({
        url: `/api/album/pool/detail/${poolId}`,
        method: 'GET',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200) {
              this.albumData = res.data.data;
              if (typeof this.albumData.tracks === 'string') {
                try {
                  this.albumData.tracks = JSON.parse(this.albumData.tracks);
                } catch {
                  this.albumData.tracks = [];
                }
              } else if (!Array.isArray(this.albumData.tracks)) {
                this.albumData.tracks = [];
              }
              this.setFullPageBg(this.albumData.cover_img);
              if(this.albumData.cover_img) this.extractAlbumMainColor(this.albumData.cover_img);
            } else {
              alert('获取详情失败：' + res.data.msg);
            }
          })
          .catch(err => {
            this.loading = false;
            console.error('获取公共专辑详情失败：', err);
            alert('获取详情失败！');
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
            if (res.data.code === 200) {
              this.tagChartData = res.data.data || [];
            }
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
            if (res.data.code === 200) {
              this.recentUsers = res.data.data || [];
            }
          })
          .catch(err => {
            console.error('获取专辑用户列表失败：', err);
            this.recentUsers = [];
          });
    },
    copyAlbum() {
      if (!confirm('确定复制该公共专辑为你的私有副本吗？')) return;
      this.$axios({
        url: `/api/album/pool/copy/${this.$route.params.poolId}`,
        method: 'POST',
        headers: {'Authorization': `Bearer ${localStorage.getItem('token') || ''}`}
      })
          .then(res => {
            if (res.data.code === 200) {
              alert('复制成功！跳转到我的专辑列表');
              this.$router.push('/albumDetail');
            } else {
              alert('复制失败：' + res.data.msg);
            }
          })
          .catch(err => {
            console.error('复制失败：', err);
            alert('复制失败！');
          });
    },
    goEditAlbum() {
      this.$router.push(`/album/pool/edit/${this.$route.params.poolId}`);
    },
goBack() {
  window.targetTab = 'searchmusic'          // ① 告诉 WebHome 要去搜索音乐
  this.$router.push({ path: '/webhome' })   // ② 先跳过去
}
  }
};
</script>

<style scoped>
.pool-detail-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  position: relative;
  min-height: 100vh;
  z-index: 1;
}

.bg-layer {
  position: absolute;
  top: 0;
  left: 0;
	width: 100%;
	height: 100%;
  z-index: -1;
  filter: blur(25px) brightness(1.2);
  -webkit-filter: blur(25px) brightness(1.2);
}

.edit-btn-container {
  text-align: right;
  margin-bottom: 20px;
  z-index: 9;
  position: relative;
}

.edit-btn {
  padding: 8px 20px;
  color: white;
	border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.edit-btn:hover {
  opacity: 0.9;
  transform: scale(1.02);
}

.loading-tip, .empty-tip {
  text-align: center;
  color: #666;
  padding: 30px 0;
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

.cover {
  width: 260px;
  height: 260px;
  margin: 40px auto 20px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
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
  marginTop: 10px;
}

.actions {
  margin-top: 10px;
  display: flex;
  justify-content: center;
  gap: 25px;
}

.copy-btn, .back-btn {
  padding: 10px 25px;
  font-size: 16px;
  border-radius: 6px;
	border: none;
  cursor: pointer;
  transition: all 0.2s;
  color: #fff;
}
.back-btn {
  background: #999;
}
.copy-btn:hover, .back-btn:hover {
  opacity: 0.9;
  transform: scale(1.02);
}

.intro-title, .songs-title, .users-title, .style-title {
  font-size: 18px;
  font-weight: 600;
  color:v-bind(mainColorDarkDouble);
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
.no-intro-tip {
  color: #999;
  text-align: center;
	padding: 60px 0;
	height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin:0;
}

.no-songs-tip {
  color: #999;
  text-align: center;
	padding: 12px 20px 20px;
  marginTop: 0;
}

/** 1. 单曲列表滚动容器 - 核心样式 */
.songs-list {
  list-style: none;
	padding: 12px 20px 0;
  margin: 0;
  max-height: calc(100% - 60px);
  overflow-y: auto;
  padding-right: 5px;
  background: transparent !important;
}
.songs-list::-webkit-scrollbar { width: 6px; }
.songs-list::-webkit-scrollbar-thumb { background: v-bind(mainColorDarkDouble); border-radius: 3px; }
.songs-list::-webkit-scrollbar-thumb:hover { background: v-bind(mainColorDark); }
.songs-list::-webkit-scrollbar-track { background: transparent !important; }
.songs-list::-webkit-scrollbar-button { display: none !important; }

/** 2. 最近收听用户滚动容器 - 统一相同样式 */
.users-scroll-wrapper {
	height: calc(100% - 50px);
  overflow-y: auto;
  padding: 12px 20px 0;
  padding-right: 5px;
  background: transparent !important;
}
.users-scroll-wrapper::-webkit-scrollbar { width: 6px; }
.users-scroll-wrapper::-webkit-scrollbar-thumb { background: v-bind(mainColorDarkDouble); border-radius: 3px; }
.users-scroll-wrapper::-webkit-scrollbar-thumb:hover { background: v-bind(mainColorDark); }
.users-scroll-wrapper::-webkit-scrollbar-track { background: transparent !important; }
.users-scroll-wrapper::-webkit-scrollbar-button { display: none !important; }

/** 3. 专辑简介滚动容器 - 统一相同样式 */
.intro-content {
  font-size: 16px;
  color: #333;
  line-height: 1.8;
  white-space: pre-wrap;
  word-wrap: break-word;
	padding: 10px 15px;
	height: 100%;
  overflow-y: auto;
  margin-top: 0;
  padding-right: 5px;
  background: transparent !important;
}
.intro-content::-webkit-scrollbar { width: 6px; }
.intro-content::-webkit-scrollbar-thumb { background: v-bind(mainColorDarkDouble); border-radius: 3px; }
.intro-content::-webkit-scrollbar-thumb:hover { background: v-bind(mainColorDark); }
.intro-content::-webkit-scrollbar-track { background: transparent !important; }
.intro-content::-webkit-scrollbar-button { display: none !important; }

.song-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
	padding: 10px 15px;
  background: rgba(255,255,255,0.3);
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
.users-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.user-item {
  display:flex;
  align-items:center;
  justify-content: space-between;
	padding:8px 10px;
  margin-bottom:8px;
  background:rgba(255,255,255,0.3);
	border-radius:6px;
	font-size:14px;
}
.user-avatar {
  width:26px;
	height:26px;
	border-radius:50%;
	color:#fff;
	display:flex;
	align-items:center;
	justify-content:center;
	font-size:13px;
	margin-right:8px;
}
.user-name {
  flex:1;
	font-size:14px;
	color:#333;
}
.user-time {
	font-size:12px;
}

.album-style-chart {
  padding:0 !important;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
	border-radius:8px;
  flex:1;
  min-height:320px;
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
}
.album-style-chart >>> .tag-bubble-chart-container {
  padding:12px 20px 20px !important;
  box-sizing: border-box;
	width:100%;
	height: calc(100% - 55px) !important;
  position: relative;
}

.slide-toggle-btn {
  position:absolute;
  top:50%;
  right:0px;
  transform: translateY(-50%);
	width:24px;
	height:auto;
  min-height:48px;
	color:#fff;
	border-radius:12px 0 0 12px;
	display:flex;
	align-items:center;
	justify-content:center;
	cursor:pointer;
	box-shadow:0 2px 8px rgba(0,0,0,0.15);
	z-index:99;
	transition:all 0.3s ease;
	padding:5px 0;
}
.slide-toggle-btn:hover {
  opacity:0.95;
}
.icon-arrow {
  font-size:18px;
	font-weight:bold;
	line-height:1;
}

@media (max-width: 1200px) {
  .album-detail-wrapper {
    flex-wrap: wrap;
    align-items: flex-start;
  }
  .album-left-section {
    max-width:100%;
    flex:1 1 100%;
  }
  .album-center-section {
    flex:1 1 100%;
    min-width:100%;
    max-width:100%;
    margin-top:20px;
    height:auto;
  }
  .album-right-section {
    flex:1 1 100%;
    min-width:100%;
    max-width:100%;
    marginTop:20px;
    height:auto;
    flex-direction:row;
    gap:20px;
  }
  .album-recent-users {
    flex:1;
    height:300px;
  }
  .album-style-chart {
    flex:1;
    min-height:300px;
  }
}

@media (max-width: 768px) {
  .album-right-section {
    flex-direction: column;
  }
  .album-recent-users {
    height:280px;
  }
  .album-style-chart {
    min-height:250px;
  }
}
</style>