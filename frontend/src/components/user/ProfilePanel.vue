<template>
  <div class="profile-panel">
    <!-- 头像 + 用户名 -->
    <div class="profile-header">
      <span
        class="profile-avatar"
        :style="{ backgroundColor: mainColorDark }"
        :title="uploadingAvatar ? '上传中…' : '点击更换头像'"
        @click="triggerAvatarUpload"
      >
        <img v-if="userInfo.avatar" :src="userInfo.avatar" class="profile-avatar-img" alt="头像" />
        <span v-else class="profile-avatar-letter">{{ avatarLetter }}</span>
        <span class="avatar-upload-mask">{{ uploadingAvatar ? '上传中' : '更换' }}</span>
      </span>
      <input
        type="file"
        ref="avatarFileInput"
        accept="image/*"
        style="display: none"
        @change="handleAvatarFileChange"
      />
      <div class="profile-identity">
        <div class="profile-username" :style="{ color: mainColorDarkDouble }">{{ userInfo.username }}</div>
        <div class="profile-badges">
          <span class="badge level-badge" :style="{ backgroundColor: mainColorDark }">Lv.{{ userInfo.level }}</span>
          <span v-if="userInfo.is_vip" class="badge vip-badge">VIP</span>
        </div>
      </div>
    </div>

    <!-- 资料信息 -->
    <div class="profile-card common-card">
      <div class="card-title">个人资料</div>
      <div class="info-row">
        <span class="info-label">注册时间</span>
        <span class="info-value">{{ userInfo.create_time || '—' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">专辑数</span>
        <span class="info-value">{{ userInfo.album_count }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">最近登录</span>
        <span class="info-value">{{ userInfo.last_login || '—' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">会员</span>
        <span class="info-value">{{ userInfo.is_vip ? '是' : '否' }}</span>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="profile-card common-card">
      <div class="card-title">修改密码</div>
      <input
        type="password"
        v-model="pwd.oldPassword"
        placeholder="旧密码"
        class="pwd-input"
        @keyup.enter="changePassword"
      />
      <input
        type="password"
        v-model="pwd.newPassword"
        placeholder="新密码（至少6位）"
        class="pwd-input"
        @keyup.enter="changePassword"
      />
      <input
        type="password"
        v-model="pwd.confirmPassword"
        placeholder="确认新密码"
        class="pwd-input"
        @keyup.enter="changePassword"
      />
      <button class="pwd-save-btn" :style="{ backgroundColor: mainColorDark }" :disabled="changing" @click="changePassword">
        {{ changing ? '提交中…' : '保存新密码' }}
      </button>
    </div>

    <!-- 退出登录 -->
    <button class="logout-btn" :style="{ backgroundColor: mainColorDark }" @click="logout">退出登录</button>
  </div>
</template>

<script>
export default {
  name: 'ProfilePanel',
  props: {
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      userInfo: {
        username: localStorage.getItem('username') || '',
        avatar: '',
        level: 0,
        is_vip: 0,
        create_time: '',
        last_login: '',
        album_count: 0
      },
      pwd: { oldPassword: '', newPassword: '', confirmPassword: '' },
      changing: false,
      uploadingAvatar: false
    }
  },
  computed: {
    avatarLetter() {
      const name = this.userInfo.username
      return name ? name.trim().charAt(0).toUpperCase() : '?'
    }
  },
  created() {
    this.fetchUserInfo()
  },
  methods: {
    fetchUserInfo() {
      this.$axios.get('/api/user/info').then(res => {
        if (res.data.code === 200 && res.data.data) {
          this.userInfo = { ...this.userInfo, ...res.data.data }
          if (res.data.data.username) {
            localStorage.setItem('username', res.data.data.username)
          }
          if (res.data.data.avatar) {
            localStorage.setItem('avatar', res.data.data.avatar)
          }
        }
      }).catch(err => {
        console.error('获取用户信息失败：', err)
      })
    },
    // ===== 头像上传（复用 /api/upload_img 图床 → /api/user/avatar 存URL） =====
    triggerAvatarUpload() {
      if (this.uploadingAvatar) return
      this.$refs.avatarFileInput.click()
    },
    handleAvatarFileChange(e) {
      if (this.uploadingAvatar) return
      const file = e.target.files[0]
      e.target.value = '' // 允许连续选择同一文件
      if (!file) return
      if (!file.type.startsWith('image/')) {
        this.showMsg('warning', '请选择有效的图片文件！')
        return
      }
      this.uploadAvatar(file)
    },
    async uploadAvatar(file) {
      this.uploadingAvatar = true
      try {
        // 1. 上传图床拿 URL
        const formData = new FormData()
        formData.append('image', file)
        const res = await this.$axios.post('/api/upload_img', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 15000
        })
        if (res.data.code !== 200) {
          alert(res.data.msg || '图片上传失败！')
          return
        }
        const imgUrl = res.data.data.img_url
        // 2. 保存到用户表
        const saveRes = await this.$axios.post('/api/user/avatar', { avatarUrl: imgUrl })
        if (saveRes.data.code === 200) {
          this.userInfo.avatar = imgUrl
          localStorage.setItem('avatar', imgUrl)
          // 广播事件，让 WebHome 右上角 UserAvatar 实时刷新
          window.dispatchEvent(new CustomEvent('user-avatar-changed', { detail: imgUrl }))
          this.showMsg('success', '头像更新成功！')
        } else {
          alert(saveRes.data.msg || '头像保存失败！')
        }
      } catch (err) {
        console.error('头像上传失败：', err)
        alert('头像上传失败！检查后端是否启动')
      } finally {
        this.uploadingAvatar = false
      }
    },
    changePassword() {
      const { oldPassword, newPassword, confirmPassword } = this.pwd
      if (!oldPassword || !newPassword) {
        alert('请填写完整新旧密码！')
        return
      }
      if (newPassword.length < 6) {
        alert('新密码长度不能少于6位！')
        return
      }
      if (newPassword !== confirmPassword) {
        alert('两次输入的新密码不一致！')
        return
      }
      this.changing = true
      this.$axios.post('/api/user/change-password', { oldPassword, newPassword }).then(res => {
        if (res.data.code === 200) {
          this.showMsg('success', '密码修改成功！')
          this.pwd = { oldPassword: '', newPassword: '', confirmPassword: '' }
        } else {
          alert(res.data.msg || '修改密码失败！')
        }
      }).catch(err => {
        console.error('修改密码失败：', err)
        alert('修改密码失败，请稍后重试！')
      }).then(() => {
        this.changing = false
      })
    },
    logout() {
      if (!confirm('确定退出登录吗？')) return
      try {
        localStorage.clear()
        this.$router.replace('/login')
        alert('退出登录成功！')
      } catch (err) {
        console.error('退出登录失败：', err)
        window.location.href = '/#/login'
      }
    },
    showMsg(type, msg) {
      if (this.$message && this.$message[type]) {
        this.$message[type](msg)
      } else {
        alert(msg)
      }
    }
  }
}
</script>

<style scoped>
.profile-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.profile-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  color: #fff;
  position: relative;
  cursor: pointer;
}

.profile-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-avatar-letter {
  font-size: 24px;
  font-weight: 600;
}

/* 头像悬停遮罩：提示可更换 */
.avatar-upload-mask {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s;
}

.profile-avatar:hover .avatar-upload-mask {
  opacity: 1;
}

.profile-identity {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.profile-username {
  font-size: 18px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-badges {
  display: flex;
  gap: 6px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  color: #fff;
}

.vip-badge {
  background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
  color: #7a4a00;
  font-weight: 600;
}

.common-card {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  padding: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #333;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}

.info-label {
  color: #888;
}

.info-value {
  color: #333;
  font-weight: 500;
}

.pwd-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  margin-bottom: 8px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  outline: none;
}

.pwd-input:focus {
  border-color: v-bind(mainColorDark);
}

.pwd-save-btn {
  width: 100%;
  padding: 8px 0;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.pwd-save-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.logout-btn {
  width: 100%;
  padding: 9px 0;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.logout-btn:hover {
  opacity: 0.9;
}
</style>
