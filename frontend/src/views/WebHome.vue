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
          <!-- v0.7：右上角头像+用户名触发器，点击弹个人中心抽屉 -->
          <UserAvatar
            :username="username"
            :avatar="userAvatar"
            :main-color-dark="mainColorDark"
            :main-color-dark-double="mainColorDarkDouble"
            @click="showUserCenter = true"
          />
        </div>
      </div>

      <!-- ✅ 发现音乐 二级tab【新增：音乐专题】 -->
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
        <!-- 新增：音乐专题 tab -->
        <div
          class="sub-tab-item"
          :class="{ active: activeSubTab === 'special' }"
          @click="activeSubTab = 'special'"
        >
          音乐专题
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
        <!-- 发现音乐 子组件【新增：音乐专题组件】 -->
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
        <!-- 新增：音乐专题组件渲染 -->
        <MusicSpecial
            v-if="activeMainTab === 'discover' && activeSubTab === 'special'"
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
        <PlayList v-if="activeMainTab === 'mymusic' && activeSubTab === 'playList'"/>
        <YearMusic v-if="activeMainTab === 'mymusic' && activeSubTab === 'yearMusic'"/>

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

    <!-- v0.7：个人中心独立抽屉（与播放列表侧边栏同款样式，复用公共 UserCenter） -->
    <div class="uc-mask" v-show="showUserCenter" @click="showUserCenter = false"></div>
    <div class="uc-drawer" v-show="showUserCenter">
      <UserCenter
        dismissible
        :mainColor="mainColor"
        :mainColorDark="mainColorDark"
        :mainColorDarkDouble="mainColorDarkDouble"
        @close="showUserCenter = false"
      />
    </div>
  </div>
</template>

<script>
import DailyRecommend from '@/components/discoverMusic/DailyRecommend.vue'
import RankingList from '@/components/discoverMusic/RankingList.vue'
import CategoryList from '@/components/discoverMusic/CategoryList.vue'
import SingerList from '@/components/discoverMusic/SingerList.vue'
// 新增：引入音乐专题组件
import MusicSpecial from '@/components/discoverMusic/MusicSpecial.vue'
import MusicList from '@/components/myMusic/MusicList.vue'
import SearchAlbumPool from '@/components/searchMusic/SearchAlbumPool.vue'
// ✅ 引入两个占位组件
import PlayList from '@/components/myMusic/PlayList.vue'
import YearMusic from '@/components/myMusic/YearMusic.vue'
// v0.7：个人用户中心（右上角头像入口 + 独立抽屉）
import UserAvatar from '@/components/user/UserAvatar.vue'
import UserCenter from '@/components/user/UserCenter.vue'
// 主题色合法性兜底 + 坏值修复（localStorage 可能存着 transparent，文字会变透明）
import { getSavedTheme } from '@/utils/themeColor'

export default {
  name: 'WebHome',
  components: {
    DailyRecommend,
    RankingList,
    CategoryList,
    SingerList,
    // 新增：注册音乐专题组件
    MusicSpecial,
    MusicList,
    SearchAlbumPool,
    PlayList,
    YearMusic,
    // v0.7：个人用户中心
    UserAvatar,
    UserCenter
  },
  data() {
    const theme = getSavedTheme() // 读主题色并修复坏值（transparent → 默认色）
    return {
      activeMainTab: 'discover',
      activeSubTab: 'recommend',
      username: '',
      userAvatar: '',
      showUserCenter: false,
      coverBgUrl: localStorage.getItem('persistCoverBg') || '',
      mainColor: theme.mainColor,
      mainColorDark: theme.mainColorDark,
      mainColorDarkDouble: theme.mainColorDarkDouble
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
        return {backgroundColor: 'transparent'}
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
    // v0.7：拉取用户信息（头像/资料），右上角 UserAvatar 展示
    this.fetchUserInfo()
    // v0.7 P1：头像更新后实时刷新右上角
    window.addEventListener('user-avatar-changed', this.handleAvatarChanged)
  },
  beforeDestroy() {
    window.removeEventListener('user-avatar-changed', this.handleAvatarChanged)
  },
  methods: {
    fetchUserInfo() {
      this.$axios.get('/api/user/info').then(res => {
        if (res.data.code === 200 && res.data.data) {
          this.userAvatar = res.data.data.avatar || ''
          if (res.data.data.username) {
            this.username = res.data.data.username
          }
        }
      }).catch(err => {
        console.error('获取用户信息失败：', err)
      })
    },
    handleAvatarChanged(e) {
      this.userAvatar = (e && e.detail) || ''
    },
    initThemeColor() {
      const theme = getSavedTheme() // 读主题色并修复坏值（transparent → 默认色）
      this.mainColor = theme.mainColor
      this.mainColorDark = theme.mainColorDark
      this.mainColorDarkDouble = theme.mainColorDarkDouble
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
        if (window.targetTab === 'mymusic') this.activeSubTab = 'albumList';
        if (window.targetTab === 'searchmusic') this.activeSubTab = 'albumPool';
        if (window.targetTab === 'discover') this.activeSubTab = window.targetSubTab || 'recommend';
        window.targetTab = null;
        window.targetSubTab = null;
      }
    },
    getCoverBgUrl(url) {
      // 空 URL（今日推荐加载失败/无封面）不清空已持久化的背景，避免刷新后主题背景丢失
      if (!url) return
      this.coverBgUrl = url
    },
    getThemeColor(colorObj) {
      // 提取失败时 DailyRecommend 会 emit transparent —— 此时保留已持久化的主题，不让瞬时失败覆盖掉
      if (!colorObj || !colorObj.mainColor || colorObj.mainColor === 'transparent') return
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

/* 磨砂玻璃蒙版（v0.7 P1：透明度由 --mask-opacity 全局变量控制） */
.nav-mask-container {
  background-color: rgba(255, 255, 255, var(--mask-opacity, 0.25));
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

/* v0.7：个人中心独立抽屉（与播放列表侧边栏同款固定右侧样式） */
.uc-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 9998;
}

.uc-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 380px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border-left: 1px solid rgba(255, 255, 255, 0.5);
  z-index: 9999;
  padding: 20px 15px 15px;
  box-sizing: border-box;
  color: #333;
  font-family: "Microsoft YaHei", "SimHei", sans-serif;
  display: flex;
  flex-direction: column;
  transform: translateZ(0);
  will-change: transform;
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