<template>
  <div class="user-center">
    <!-- 子 tab：个人资料 / 外观 / 音乐统计 -->
    <div class="uc-tabs" :style="{ borderBottomColor: mainColorDark }">
      <div
        class="uc-tab"
        :class="{ active: activeTab === 'profile' }"
        :style="tabStyle('profile')"
        @click="activeTab = 'profile'"
      >个人资料</div>
      <div
        class="uc-tab"
        :class="{ active: activeTab === 'appearance' }"
        :style="tabStyle('appearance')"
        @click="activeTab = 'appearance'"
      >外观</div>
      <div
        class="uc-tab"
        :class="{ active: activeTab === 'stats' }"
        :style="tabStyle('stats')"
        @click="activeTab = 'stats'"
      >音乐统计</div>
      <span v-if="dismissible" class="uc-close-btn" @click="$emit('close')">×</span>
    </div>

    <div class="uc-body">
      <ProfilePanel
        v-if="activeTab === 'profile'"
        :mainColor="mainColor"
        :mainColorDark="mainColorDark"
        :mainColorDarkDouble="mainColorDarkDouble"
      />
      <AppearancePanel
        v-else-if="activeTab === 'appearance'"
        :mainColor="mainColor"
        :mainColorDark="mainColorDark"
        :mainColorDarkDouble="mainColorDarkDouble"
      />
      <div v-else class="uc-placeholder">
        <p>音乐统计（近N天听取时长柱状图等）将在 <b>v0.7 P2</b> 上线</p>
      </div>
    </div>
  </div>
</template>

<script>
import ProfilePanel from '@/components/user/ProfilePanel.vue'
import AppearancePanel from '@/components/user/AppearancePanel.vue'

export default {
  name: 'UserCenter',
  components: { ProfilePanel, AppearancePanel },
  props: {
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' },
    dismissible: { type: Boolean, default: false }
  },
  data() {
    return {
      activeTab: 'profile'
    }
  },
  methods: {
    tabStyle(tab) {
      if (this.activeTab === tab) {
        return { backgroundColor: this.mainColorDark, color: '#fff' }
      }
      return { color: this.mainColorDark }
    }
  }
}
</script>

<style scoped>
.user-center {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  width: 100%;
  box-sizing: border-box;
}

.uc-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 10px;
  border-bottom: 2px solid;
  flex-shrink: 0;
  position: relative;
}

.uc-tab {
  padding: 5px 12px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.uc-tab:hover {
  background: rgba(255, 255, 255, 0.5);
}

.uc-close-btn {
  position: absolute;
  right: 0;
  top: -4px;
  font-size: 22px;
  color: #999;
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.2s;
}

.uc-close-btn:hover {
  color: #dc2626;
}

.uc-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 12px;
  box-sizing: border-box;
}

.uc-placeholder {
  padding: 40px 12px;
  text-align: center;
  color: #999;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 8px;
}
</style>
