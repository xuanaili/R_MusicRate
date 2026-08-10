<template>
  <div class="user-avatar-trigger" :title="username" @click="$emit('click')">
    <span class="avatar-circle" :style="circleStyle">
      <img v-if="avatar" :src="avatar" class="avatar-img" alt="头像" />
      <span v-else class="avatar-letter">{{ firstLetter }}</span>
    </span>
    <span v-if="showName" class="avatar-username" :style="textStyle">{{ username }}</span>
  </div>
</template>

<script>
export default {
  name: 'UserAvatar',
  props: {
    username: { type: String, default: '' },
    avatar: { type: String, default: '' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' },
    size: { type: Number, default: 32 },
    showName: { type: Boolean, default: true }
  },
  computed: {
    firstLetter() {
      return this.username ? this.username.trim().charAt(0).toUpperCase() : '?'
    },
    circleStyle() {
      return {
        width: this.size + 'px',
        height: this.size + 'px',
        backgroundColor: this.mainColorDark,
        borderColor: this.mainColorDarkDouble
      }
    },
    textStyle() {
      return { color: this.mainColorDarkDouble }
    }
  }
}
</script>

<style scoped>
.user-avatar-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 20px;
  transition: background 0.2s;
  white-space: nowrap;
}
.user-avatar-trigger:hover {
  background: rgba(255, 255, 255, 0.4);
}
.avatar-circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid;
  flex-shrink: 0;
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-letter {
  color: #fff;
  font-weight: 600;
  line-height: 1;
  font-size: 14px;
}
.avatar-username {
  font-size: 15px;
  font-weight: 500;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
