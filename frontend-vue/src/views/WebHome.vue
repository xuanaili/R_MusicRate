<template>
  <div class="home-container">
    <!-- 顶部一级Tab栏：发现音乐 + 我的音乐 + 搜索音乐 + 右上角用户名 -->
    <div class="main-tab-header">
      <div class="main-tab-list">
        <div
          class="main-tab-item"
          :class="{ active: activeMainTab === 'discover' }"
          @click="activeMainTab = 'discover'"
        >
          发现音乐
        </div>
        <div
          class="main-tab-item"
          :class="{ active: activeMainTab === 'mymusic' }"
          @click="activeMainTab = 'mymusic'"
        >
          我的音乐
        </div>
        <!-- ✅ 新增：搜索音乐 一级Tab项 -->
        <div
          class="main-tab-item"
          :class="{ active: activeMainTab === 'searchmusic' }"
          @click="activeMainTab = 'searchmusic'"
        >
          搜索音乐
        </div>
      </div>

      <div class="user-info">
        <span class="username">{{ username }}</span>
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>
    </div>

    <!-- 一级Tab内容区域 -->
    <div class="main-tab-content">
      <!-- 发现音乐 面板：包含二级Tab -->
      <div v-if="activeMainTab === 'discover'">
        <!-- 二级Tab栏：今日推荐/排行榜/音乐类型/歌手 -->
        <div class="sub-tab-list">
          <div
            class="sub-tab-item"
            :class="{ active: activeSubTab === 'recommend' }"
            @click="activeSubTab = 'recommend'"
          >
            今日推荐
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
            :class="{ active: activeSubTab === 'category' }"
            @click="activeSubTab = 'category'"
          >
            音乐类型
          </div>
          <div
            class="sub-tab-item"
            :class="{ active: activeSubTab === 'singer' }"
            @click="activeSubTab = 'singer'"
          >
            歌手
          </div>
        </div>

        <!-- 二级Tab内容区域-加载改名后的4个子组件 -->
        <div class="sub-tab-content">
          <DailyRecommend v-if="activeSubTab === 'recommend'" />
          <RankingList v-if="activeSubTab === 'ranking'" />
          <CategoryList v-if="activeSubTab === 'category'" />
          <SingerList v-if="activeSubTab === 'singer'" />
        </div>
      </div>

      <!-- 我的音乐 面板：直接复用你原有的MusicList组件 无任何修改 -->
      <div v-if="activeMainTab === 'mymusic'">
        <MusicList />
      </div>

      <!-- ✅ 核心新增：搜索音乐 面板，直接嵌入SearchAlbumPool组件 -->
      <div v-if="activeMainTab === 'searchmusic'">
        <SearchAlbumPool />
      </div>
    </div>
  </div>
</template>

<script>
// 引入【改名后】的4个发现音乐子组件
import DailyRecommend from '@/components/discover/DailyRecommend.vue'
import RankingList from '@/components/discover/RankingList.vue'
import CategoryList from '@/components/discover/CategoryList.vue'
import SingerList from '@/components/discover/SingerList.vue'
// 引入你的原有核心组件 MusicList
import MusicList from '@/views/MusicList.vue'
// ✅ 新增：引入搜索专辑池核心组件 SearchAlbumPool
import SearchAlbumPool from '@/views/SearchAlbumPool.vue'

export default {
  name: 'WebHome',
  components: {
    DailyRecommend,
    RankingList,
    CategoryList,
    SingerList,
    MusicList,
    SearchAlbumPool // ✅ 注册新增的组件
  },
  data() {
    return {
      activeMainTab: 'discover', // 默认显示：发现音乐
      activeSubTab: 'recommend',  // 默认显示：今日推荐
      username: ''
    }
  },
  watch: {
    $route() {
      this.$nextTick(() => this.setActiveTab())
    }
  },

  mounted() {
    this.setActiveTab()
  },
  activated() {
    this.setActiveTab()
  },

  created() {
    // 登录校验逻辑 和你的MusicList、全局守卫一致
    this.username = localStorage.getItem('username') || ''
    const token = localStorage.getItem('token')
    if (!token || !this.username) {
      this.$router.push('/login')
      return
    }
  },
  methods: {
    // 退出登录：复用你原有的逻辑，和MusicList里的logout一致
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
    setActiveTab() {
      // 读取全局变量，判断是否有值
      if (window.targetTab) {
        console.log(222)
        this.activeMainTab = window.targetTab // 赋值切换到我的音乐
        window.targetTab = null // 用完清空，避免下次进页面被影响
      }
    }
  }
}
</script>

<style scoped>
/* 主容器样式，和你的MusicList样式完全统一，无缝衔接 */
.home-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: "Microsoft YaHei", sans-serif;
}

/* 一级Tab头部：左侧tab，右侧用户名 */
.main-tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

/* 一级Tab列表样式 - 发现音乐/我的音乐/搜索音乐 */
.main-tab-list {
  display: flex;
  gap: 30px;
}

.main-tab-item {
  font-size: 18px;
  font-weight: 600;
  color: #666;
  cursor: pointer;
  padding: 8px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.main-tab-item.active {
  color: #42b983;
  border-bottom: 2px solid #42b983;
}

.main-tab-item:hover {
  color: #42b983;
}

/* 右上角用户信息+退出按钮 */
.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.username {
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

.logout-btn {
  padding: 6px 12px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.logout-btn:hover {
  background: #c0392b;
}

/* 二级Tab列表样式（发现音乐下） */
.sub-tab-list {
  display: flex;
  gap: 25px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
  margin-bottom: 25px;
}

.sub-tab-item {
  font-size: 16px;
  color: #666;
  cursor: pointer;
  padding: 6px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.sub-tab-item.active {
  color: #3498db;
  border-bottom: 2px solid #3498db;
}

.sub-tab-item:hover {
  color: #3498db;
}

/* 二级Tab内容区 */
.sub-tab-content {
  min-height: 500px;
}

/* 响应式适配-手机端正常显示 */
@media (max-width: 768px) {
  .main-tab-list, .sub-tab-list {
    gap: 15px;
  }

  .main-tab-item {
    font-size: 16px;
  }
}
</style>