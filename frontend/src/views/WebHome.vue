<template>
  <div class="home-container">
    <!-- 全屏模糊背景层【完全复刻AlbumDetail的bg-layer，满屏无死角】 -->
    <div class="bg-layer" :style="bgStyle"></div>

    <div class="nav-mask-container">
      <div class="main-tab-header">
        <div class="sort-options main-tab-list">
          <div
            class="tab-item main-tab-item"
            :class="{ active: activeMainTab === 'discover' }"
            @click="activeMainTab = 'discover'; activeSubTab = 'recommend'"
          >
            发现音乐
          </div>
          <div
            class="tab-item main-tab-item"
            :class="{ active: activeMainTab === 'mymusic' }"
            @click="activeMainTab = 'mymusic'; activeSubTab = 'albumList'"
          >
            我的音乐
          </div>
          <div
            class="tab-item main-tab-item"
            :class="{ active: activeMainTab === 'searchmusic' }"
            @click="activeMainTab = 'searchmusic'; activeSubTab = 'albumPool'"
          >
            搜索音乐
          </div>
        </div>

        <div class="user-info">
          <span class="username">{{ username }}</span>
          <button class="logout-btn" @click="logout">退出登录</button>
        </div>
      </div>

      <!-- ✅ 发现音乐 二级tab【原封不动保留】 -->
      <div v-if="activeMainTab === 'discover'" class="sub-tab-list">
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'recommend' }"
          @click="activeSubTab = 'recommend'"
        >
          今日推荐
        </div>
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'category' }"
          @click="activeSubTab = 'category'"
        >
          音乐类型
        </div>
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'ranking' }"
          @click="activeSubTab = 'ranking'"
        >
          排行榜
        </div>

        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'singer' }"
          @click="activeSubTab = 'singer'"
        >
          歌手
        </div>
      </div>

      <!-- ✅ 我的音乐 二级tab【新增核心】 -->
      <div v-if="activeMainTab === 'mymusic'" class="sub-tab-list">
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'albumList' }"
          @click="activeSubTab = 'albumList'"
        >
          专辑列表
        </div>
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'playList' }"
          @click="activeSubTab = 'playList'"
        >
          播放列表
        </div>
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'yearMusic' }"
          @click="activeSubTab = 'yearMusic'"
        >
          年度音乐
        </div>
      </div>

      <!-- ✅ 搜索音乐 二级tab【新增核心】 -->
      <div v-if="activeMainTab === 'searchmusic'" class="sub-tab-list">
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'albumPool' }"
          @click="activeSubTab = 'albumPool'"
        >
          专辑搜索
        </div>
      </div>
    </div>

    <div class="main-tab-content">
      <div class="sub-tab-content">
        <!-- 发现音乐 子组件【原封不动】 -->
        <DailyRecommend
          v-if="activeMainTab === 'discover' && activeSubTab === 'recommend'"

          :active-sub-tab="activeSubTab"
          @sendCoverBg="getCoverBgUrl"
          @sendThemeColor="getThemeColor"
        />
        <RankingList
            v-if="activeMainTab === 'discover' && activeSubTab === 'ranking'"
            :active-sub-tab="activeSubTab"
        />
        <CategoryList
            v-if="activeMainTab === 'discover' && activeSubTab === 'category'"
            :active-sub-tab="activeSubTab"
              :mainColor="mainColor"
  :mainColorDark="mainColorDark"
  :mainColorDarkDouble="mainColorDarkDouble"

        />
        <SingerList
            v-if="activeMainTab === 'discover' && activeSubTab === 'singer'"
            :active-sub-tab="activeSubTab"
        />

        <!-- ✅ 我的音乐 子组件【核心改造】 -->
        <MusicList
          v-if="activeMainTab === 'mymusic' && activeSubTab === 'albumList'"
          @sendCoverBg="getCoverBgUrl"
          :mainColor="mainColor"
          :mainColorDark="mainColorDark"
          :mainColorDarkDouble="mainColorDarkDouble"
        />
        <PlayList v-if="activeMainTab === 'mymusic' && activeSubTab === 'playList'" />
        <YearMusic v-if="activeMainTab === 'mymusic' && activeSubTab === 'yearMusic'" />

<!-- 修改后代码【复制即用】 -->
<SearchAlbumPool
  v-if="activeMainTab === 'searchmusic' && activeSubTab === 'albumPool'"
  @sendCoverBg="getCoverBgUrl"
  :mainColor="mainColor"
  :mainColorDark="mainColorDark"
  :mainColorDarkDouble="mainColorDarkDouble"
/>
      </div>
    </div>
  </div>
</template>

<script>
import DailyRecommend from '@/components/discoverMusic/DailyRecommend.vue'
import RankingList from '@/components/discoverMusic/RankingList.vue'
import CategoryList from '@/components/discoverMusic/CategoryList.vue'
import SingerList from '@/components/discoverMusic/SingerList.vue'
import MusicList from '@/components/myMusic/MusicList.vue'
import SearchAlbumPool from '@/components/searchMusic/SearchAlbumPool.vue'
// ✅ 引入两个占位组件
import PlayList from '@/components/myMusic/PlayList.vue'
import YearMusic from '@/components/myMusic/YearMusic.vue'

export default {
  name: 'WebHome',
  components: {
    DailyRecommend,
    RankingList,
    CategoryList,
    SingerList,
    MusicList,
    SearchAlbumPool,
    PlayList,
    YearMusic
  },
  data() {
    return {
      activeMainTab: 'discover',
      activeSubTab: 'recommend',
      username: '',
      coverBgUrl: localStorage.getItem('persistCoverBg') || '',
      mainColor: localStorage.getItem('persistMainColor') || 'transparent',
      mainColorDark: localStorage.getItem('persistMainColorDark') || 'transparent',
      mainColorDarkDouble: localStorage.getItem('persistMainColorDarkDouble') || 'transparent'
    }
  },
  computed: {
    bgStyle() {
      if (this.coverBgUrl) {
        return {
          backgroundImage: `url(${this.coverBgUrl})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }
      } else {
        return { backgroundColor: 'transparent' }
      }
    }
  },
  watch: {
    $route() {
      this.$nextTick(() => {
        this.setActiveTab()
        this.$forceUpdate()
      })
    },


    coverBgUrl(newVal) {
      localStorage.setItem('persistCoverBg', newVal)
    },
    mainColor(newVal) {
      localStorage.setItem('persistMainColor', newVal)
    },
    mainColorDark(newVal) {
      localStorage.setItem('persistMainColorDark', newVal)
    },
    mainColorDarkDouble(newVal) {
      localStorage.setItem('persistMainColorDarkDouble', newVal)
    }
  },

  mounted() {
    this.setActiveTab()
  },
  activated() {
    this.setActiveTab()
    this.initThemeColor()
    this.$forceUpdate()
  },

  created() {
    this.username = localStorage.getItem('username') || ''
    const token = localStorage.getItem('token')
    if (!token || !this.username) {
      this.$router.push('/login')
      return
    }
    this.initThemeColor()
  },
  methods: {
    initThemeColor() {
      this.mainColor = localStorage.getItem('persistMainColor') || 'transparent';
      this.mainColorDark = localStorage.getItem('persistMainColorDark') || 'transparent';
      this.mainColorDarkDouble = localStorage.getItem('persistMainColorDarkDouble') || 'transparent';
    },
    logout() {
      try {
        localStorage.clear()
        this.$router.replace('/login')
        alert('退出登录成功！')
      } catch (err) {
        console.error('退出登录失败：', err)
        window.location.href = '/#/login'
      }
    },
// 1. 修改 setActiveTab 方法
setActiveTab() {
  // 优先读localStorage的状态（最稳定）
  const targetMainTab = localStorage.getItem('targetMainTab');
  const targetSubTab = localStorage.getItem('targetSubTab');

  if (targetMainTab) {
    this.activeMainTab = targetMainTab;
    // 读取子Tab状态
    this.activeSubTab = targetSubTab || 'recommend';
    // 用完就删，避免下次加载生效
    localStorage.removeItem('targetMainTab');
    localStorage.removeItem('targetSubTab');
  }
  // 兼容原有window变量逻辑
  else if (window.targetTab) {
    this.activeMainTab = window.targetTab;
    if(window.targetTab === 'mymusic') this.activeSubTab = 'albumList';
    if(window.targetTab === 'searchmusic') this.activeSubTab = 'albumPool';
    if(window.targetTab === 'discover') this.activeSubTab = window.targetSubTab || 'recommend';
    window.targetTab = null;
    window.targetSubTab = null;
  }
},
    getCoverBgUrl(url) {
      this.coverBgUrl = url
    },
    getThemeColor(colorObj) {
      this.mainColor = colorObj.mainColor
      this.mainColorDark = colorObj.mainColorDark
      this.mainColorDarkDouble = colorObj.mainColorDarkDouble
    }
  }
}
</script>

<style scoped>
/* 主容器样式 - 加相对定位，让内部元素层级生效 */
.home-container {
  max-width: 1200px;
  margin: 0 auto;
	padding: 20px;
	font-family: "Microsoft YaHei", sans-serif;
	position: relative;
	min-height: calc(100vh - 40px);
	z-index: 2;
}

/* 全屏模糊背景层【1:1复刻AlbumDetail的bg-layer，满屏无死角】 */
.bg-layer {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	z-index: -1;
	filter: blur(25px) brightness(1.2);
	-webkit-filter: blur(25px) brightness(1.2);
	background-attachment: fixed;
}

/* 磨砂玻璃蒙版 */
.nav-mask-container {
  background-color: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  -moz-backdrop-filter: blur(8px);
  border-radius: 12px;
	padding: 20px;
	position: relative;
	z-index: 2;
	width: 100%;
	box-sizing: border-box;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
	margin-bottom: 20px;
}

/* 头部布局 */
.main-tab-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: 10px;
	gap: 15px;
	position: relative;
	z-index: 3;
  border-bottom: none !important;
  flex-wrap: nowrap;
}
.main-tab-header::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 6px;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(mainColorDark);
  margin: 0;
}

/* 核心样式：一级tab外层容器 */
.sort-options {
	display: flex;
	gap: 10px;
	padding-bottom: 8px;
	background: transparent !important;
	backdrop-filter: none !important;
	-webkit-backdrop-filter: none !important;
	border-radius: 4px;
	border: none !important;
	box-sizing: border-box;
	text-align: left;
	position: relative;
}

.tab-item {
	padding: 8px 16px;
	border-radius: 6px;
	cursor: pointer;
	font-size: 15px;
	transition: all 0.2s;
	font-weight: 600;
	position: relative;
	border: none;
	background: transparent;
  color: v-bind(mainColorDarkDouble);
}
.tab-item.active {
	background: v-bind(mainColorDarkDouble);
	color: #ffffff;
}
.tab-item.active:hover {
	color: #fff;
  opacity: 1;
}
.tab-item::after {
  display: none;
}

.main-tab-list {
  gap: 10px;
}
.main-tab-item {
	font-size: 18px;
	font-weight: 600;
}

/* 用户信息 右上角紧凑布局 */
.user-info {
	display: flex;
	align-items: center;
	gap: 10px;
  white-space: nowrap;
}
.username {
	font-size: 16px;
	color: v-bind(mainColorDarkDouble);
	font-weight: 500;
}
.logout-btn {
	padding: 6px 12px;
	background: v-bind(mainColorDarkDouble);
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 14px;
}

.sub-tab-list {
	display: flex;
	gap: 8px;
	padding-bottom: 8px;
	position: relative;
	z-index: 3;
  border-bottom: none !important;
  background: transparent;
}
.sub-tab-item {
	font-size: 15px;
  color: v-bind(mainColorDark);
	cursor: pointer;
	padding: 6px 12px;
	border-radius: 5px;
	border: none;
	transition: all 0.2s;
  font-weight: 600;
  background: transparent;
}
.sub-tab-item.active {
	color: #fff;
  background: v-bind(mainColorDark);
	border-bottom: none !important;
}
.sub-tab-item.active:hover {
	opacity: 1;
}

/* 下方内容区域 核心样式 */
.main-tab-content {
  position: relative;
	z-index: 2;
	width: 100%;
	box-sizing: border-box;
}
.sub-tab-content {
	min-height: 500px;
	position: relative;
	z-index: 2;
}

/* 响应式适配 */
@media (max-width: 768px) {
	.main-tab-header {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
  .nav-mask-container {
    padding: 15px;
    border-radius: 8px;
  }
	.main-tab-list, .sub-tab-list {
		gap: 8px;
	}
	.main-tab-item {
		font-size: 16px;
	}
  .sub-tab-item {
    font-size: 14px;
    padding: 5px 10px;
  }
}
</style>