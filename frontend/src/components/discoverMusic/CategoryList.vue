<template>
  <div class="container"> <!-- 统一容器类名 -->
    <!-- 管理员新增标签按钮（复用你的验证逻辑） -->
    <div class="admin-add-tag-btn" v-if="isAdmin">
      <button @click="showAddTagSidebar = true" class="add-original-btn">+ 新增音乐风格</button> <!-- 统一按钮类名 -->
    </div>

    <div class="placeholder-content">
      <h3>🎼 音乐类型</h3>
      <p>该模块正在开发中，敬请期待～</p>
    </div>

    <!-- 新增标签侧边栏组件 -->
    <AddTag
      :visible="showAddTagSidebar"
      :main-color-dark="mainColorDark"
      :main-color-dark-double="mainColorDarkDouble"
      @close="showAddTagSidebar = false"
    />
  </div>
</template>

<script>
// 导入新增标签侧边栏组件
import AddTag from '@/components/sidebar/AddTag.vue'

export default {
  name: 'CategoryList',
  components: { AddTag },
  // 新增props，和SearchAlbumPool保持一致，支持外部传入样式变量
  props: {
    mainColor: {
      type: String,
      default: 'transparent'
    },
    mainColorDark: {
      type: String,
      default: '#333'
    },
    mainColorDarkDouble: {
      type: String,
      default: '#111'
    }
  },
  data() {
    return {
      showAddTagSidebar: false, // 控制新增标签侧边栏显示
      isAdmin: false // 管理员标识（和你现有代码一致）
    }
  },
  // 完全复用你现有的管理员验证逻辑
  created() {
    // 1. 先验证登录状态（和你现有代码一致）
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    // 2. 验证管理员身份（核心：复用你的is_admin判断逻辑）
    this.isAdmin = localStorage.getItem('is_admin') === '1';
  },
  // 可选：监听路由/登录状态变化（防止用户手动修改localStorage）
  watch: {
    // 监听localStorage变化（可选，增强安全性）
    '$route'() {
      this.isAdmin = localStorage.getItem('is_admin') === '1';
    }
  }
}
</script>

<style scoped>
/* 完全复用SearchAlbumPool的容器样式 */

.container {
  max-width: 1600px;
  margin: 0 auto;
  position: relative;
}
/* 管理员按钮样式完全复用SearchAlbumPool里的add-original-btn样式 */
.admin-add-tag-btn {
  display: flex;
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 99;
}




.add-original-btn {
  padding: 8px 20px;
  font-size: 15px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.placeholder-content {
  text-align: center;
  color: #666;
}
.placeholder-content h3 {
  font-size: 20px;
  margin-bottom: 10px;
  color: #333;
}
.placeholder-content p {
  font-size: 16px;
}
</style>