<template>
  <div class="music-special-container">
    <!-- 遮罩层（侧边栏打开时显示） -->
    <div
      class="sidebar-mask"
      v-if="showCreateSidebar || showAddSidebar || showEditSidebar"
      @click="closeAllSidebars"
    ></div>

    <!-- 左右布局容器 -->
    <div class="special-layout">
      <!-- 左侧专题内容区 -->
      <div class="special-content">
        <!-- 标题和管理员操作按钮容器 -->
        <div class="special-title-wrapper">
          <h2 class="special-title">{{ currentWeekSpecial.title || '暂无专题数据' }}</h2>

          <!-- 管理员操作按钮区 - 移到标题右侧 -->
          <div v-if="isAdmin === 1" class="admin-actions">
            <button
              class="btn-create-share"
              @click="openCreateSidebar"
              :style="{ backgroundColor: mainColorDarkDouble, borderColor: mainColorDarkDouble }"
            >
              新建专辑专题
            </button>
            <button
              class="btn-add-album"
              @click="openAddSidebar"
              :style="{ backgroundColor: mainColorDark, borderColor: mainColorDark }"
              :disabled="!currentWeekSpecial.dateRange"
            >
              <span v-if="currentWeekSpecial.dateRange">向当前专题添加专辑</span>
              <span v-else>请先创建专题</span>
            </button>
            <button
              v-if="currentWeekSpecial.dateRange"
              class="btn-edit-title"
              @click="openEditSidebar"
              :style="{ backgroundColor: '#666', borderColor: '#666' }"
            >
              编辑专题标题
            </button>
            <!-- 删除整个专题按钮 -->
            <button
              v-if="currentWeekSpecial.dateRange"
              class="btn-delete-week"
              @click="deleteCurrentWeekShare"
              :style="{ backgroundColor: '#dc3545', borderColor: '#dc3545' }"
            >
              删除当前专题
            </button>
          </div>
        </div>

        <!-- 无数据提示 -->
        <div v-if="!currentWeekSpecial.albums || currentWeekSpecial.albums.length === 0" class="empty-tip">
          <template v-if="isAdmin === 1">
            <p>暂无专辑专题数据</p>
            <p style="margin-top: 10px; font-size: 14px;">
              👆 点击"新建专辑专题"按钮开始创建第一个专题
            </p>
          </template>
          <template v-else>
            该周暂无专辑专题数据
          </template>
        </div>

        <!-- 专辑列表 -->
        <div class="album-list" v-else>
          <div
            class="album-item"
            v-for="(album, index) in currentWeekSpecial.albums"
            :key="album.shareId || album.id || index"
            :data-share-id="album.shareId"
            @click="handleAlbumClick(album.id)"
          >
            <div class="album-cover">
              <img :src="coverThumb(album.cover) || 'https://picsum.photos/200/200?random=99'" :alt="album.name" loading="lazy" />
            </div>
            <div class="album-info">
              <h3 class="album-name">{{ album.name }}</h3>
              <p class="album-singer">{{ album.singer }}</p>
            </div>
            <!-- 管理员专辑删除按钮（仅悬停显示） -->
            <div v-if="isAdmin === 1" class="album-delete-btn">
              <button
                class="btn-delete-album"
                @click.stop="deleteAlbumFromShare(album.shareId)"
                :style="{ backgroundColor: '#dc3545', borderColor: '#dc3545' }"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧日历选择器 -->
      <div class="calendar-selector">
        <h3 class="calendar-title">专题日历</h3>
        <div v-if="weekList.length === 0" class="empty-tip">
          <template v-if="isAdmin === 1">
            <p>暂无专题数据</p>
            <p style="margin-top: 10px; font-size: 14px;">
              👆 点击顶部"新建专辑专题"按钮开始创建
            </p>
          </template>
          <template v-else>
            暂无专题数据
          </template>
        </div>
        <div class="week-list" v-else>
          <div
            class="week-item"
            v-for="(week, index) in weekList"
            :key="index"
            :class="{ active: selectedWeekIndex === index }"
            @click="selectWeek(index)"
          >
            <span class="week-theme">{{ week.title }}</span>
            <span class="week-date">{{ week.dateRange }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 1. 新建专题左侧边栏 -->
    <div class="sidebar" :class="{ 'sidebar-open': showCreateSidebar }">
      <div class="sidebar-header">
        <h3 class="sidebar-title">新建专辑专题</h3>
        <button class="sidebar-close" @click="closeCreateSidebar">×</button>
      </div>
      <div class="sidebar-body">
        <div class="form-item">
          <label>专题标题：</label>
          <input
            v-model="newShareForm.shareTitle"
            class="form-control"
            placeholder="请输入专题标题..."
          />
        </div>
        <div class="form-item">
          <label>创建时间：</label>
          <input
            v-model="newShareForm.createTime"
            type="datetime-local"
            class="form-control"
          />
        </div>

        <!-- 专辑选择区域（1列布局 + 正方形封面 + 右侧文字） -->
        <div class="album-select-section">
          <div class="search-box">
            <input
              v-model="albumSearchText"
              class="form-control"
              placeholder="搜索专辑名称/歌手..."
              autocomplete="new-password"
            />
          </div>
          <div class="album-select-title">选择专辑</div>
          <!-- 1列专辑列表 -->
          <div class="album-list-single">
            <div
              class="album-item-single"
              v-for="album in filteredAlbumList"
              :key="album.id"
              :class="{ 'album-item-selected': newShareForm.albumPoolId === album.id }"
              @click="selectAlbum(album.id, 'create')"
            >
              <div class="album-cover-square">
                <img :src="coverThumb(album.cover_img) || 'https://picsum.photos/100/100?random=' + album.id" :alt="album.album_name" loading="lazy" />
              </div>
              <div class="album-text">
                <div class="album-name-text">{{ album.album_name }}</div>
                <div class="album-singer-text">{{ album.singer }}</div>
              </div>
            </div>
            <div v-if="filteredAlbumList.length === 0" class="empty-album-tip">
              未找到匹配的专辑
            </div>
          </div>
        </div>
      </div>
      <div class="sidebar-footer">
        <button class="btn-cancel" @click="closeCreateSidebar">取消</button>
        <button class="btn-confirm" @click="createShare">确认创建</button>
      </div>
    </div>

    <!-- 2. 添加专辑左侧边栏 -->
    <div class="sidebar" :class="{ 'sidebar-open': showAddSidebar }">
      <div class="sidebar-header">
        <h3 class="sidebar-title">向专题添加专辑</h3>
        <button class="sidebar-close" @click="closeAddSidebar">×</button>
      </div>
      <div class="sidebar-body">
        <div class="form-item">
          <label>添加时间：</label>
          <input
            v-model="addAlbumForm.createTime"
            type="datetime-local"
            class="form-control"
          />
        </div>

        <!-- 专辑选择区域（和新建专题保持一致的1列布局） -->
        <div class="album-select-section">
          <div class="search-box">
            <input
              v-model="albumSearchText"
              class="form-control"
              placeholder="搜索专辑名称/歌手..."
              autocomplete="new-password"
            />
          </div>
          <div class="album-select-title">选择专辑</div>
          <!-- 1列专辑列表 -->
          <div class="album-list-single">
            <div
              class="album-item-single"
              v-for="album in filteredAlbumList"
              :key="album.id"
              :class="{ 'album-item-selected': addAlbumForm.albumPoolId === album.id }"
              @click="selectAlbum(album.id, 'add')"
            >
              <div class="album-cover-square">
                <img :src="coverThumb(album.cover_img) || 'https://picsum.photos/100/100?random=' + album.id" :alt="album.album_name" loading="lazy" />
              </div>
              <div class="album-text">
                <div class="album-name-text">{{ album.album_name }}</div>
                <div class="album-singer-text">{{ album.singer }}</div>
              </div>
            </div>
            <div v-if="filteredAlbumList.length === 0" class="empty-album-tip">
              未找到匹配的专辑
            </div>
          </div>
        </div>
      </div>
      <div class="sidebar-footer">
        <button class="btn-cancel" @click="closeAddSidebar">取消</button>
        <button class="btn-confirm" @click="addAlbumToShare">确认添加</button>
      </div>
    </div>

    <!-- 3. 编辑标题左侧边栏 -->
    <div class="sidebar" :class="{ 'sidebar-open': showEditSidebar }">
      <div class="sidebar-header">
        <h3 class="sidebar-title">编辑专题标题</h3>
        <button class="sidebar-close" @click="closeEditSidebar">×</button>
      </div>
      <div class="sidebar-body">
        <div class="form-item">
          <label>新标题：</label>
          <input
            v-model="editTitleForm.newTitle"
            class="form-control"
            placeholder="请输入新的专题标题..."
          />
        </div>
      </div>
      <div class="sidebar-footer">
        <button class="btn-cancel" @click="closeEditSidebar">取消</button>
        <button class="btn-confirm" @click="updateShareTitle">确认修改</button>
      </div>
    </div>
  </div>
</template>

<script>
// 引入封面缩略图工具（列表页小图用缩略图URL）
import { coverThumb as coverThumbUtil } from '@/utils/cover.js';

export default {
  name: 'MusicSpecial',
  props: {
    activeSubTab: {
      type: String,
      required: true
    },
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
      default: '#1a1a1a'
    }
  },
  data() {
    return {
      selectedWeekIndex: 0,
      weekList: [],
      albumList: [],
      isAdmin: 0,
      // 侧边栏显示控制（替换原弹窗变量）
      showCreateSidebar: false,
      showAddSidebar: false,
      showEditSidebar: false,
      // 搜索相关
      albumSearchText: '',
      newShareForm: {
        shareTitle: '',
        albumPoolId: '',
        createTime: ''
      },
      addAlbumForm: {
        albumPoolId: '',
        createTime: ''
      },
      editTitleForm: {
        newTitle: ''
      }
    }
  },
  computed: {
    // 当前选中的专题
    currentWeekSpecial() {
      return this.weekList[this.selectedWeekIndex] || {
        dateRange: '',
        title: '',
        albums: []
      }
    },
    // 过滤后的专辑列表（根据搜索关键词）
    filteredAlbumList() {
      if (!this.albumSearchText) {
        return this.albumList
      }
      const searchText = this.albumSearchText.toLowerCase()
      return this.albumList.filter(album => {
        const albumName = (album.album_name || '').toLowerCase()
        const singer = (album.singer || '').toLowerCase()
        return albumName.includes(searchText) || singer.includes(searchText)
      })
    }
  },
  async created() {
    await this.checkAdminRole()
    await this.fetchAvailableAlbumList()
    await this.fetchWeeklyShareList()
  },
  methods: {
    // 列表页小图用缩略图URL（挂到methods便于模板解析）
    coverThumb(url) {
      return coverThumbUtil(url)
    },
    // 检查管理员角色
    async checkAdminRole() {
      try {
        const userRoleStr = localStorage.getItem('is_admin') || '0'
        this.isAdmin = parseInt(userRoleStr, 10)
      } catch (err) {
        console.error('检查管理员角色失败：', err)
        this.isAdmin = 0
      }
    },

    // 获取可选择的专辑列表
    async fetchAvailableAlbumList() {
      try {
        const res = await this.$axios.get('/api/album/pool/available-list')
        if (res.data.code === 200) {
          this.albumList = res.data.data || []
        }
      } catch (err) {
        console.error('获取可选择专辑列表失败：', err)
        this.albumList = []
        // 本地测试数据
        if (this.isAdmin === 1 && this.albumList.length === 0) {
          this.albumList = [
            { id: 1, album_name: '测试专辑1', singer: '测试歌手1', cover_img: 'https://picsum.photos/100/100?random=1' },
            { id: 2, album_name: '测试专辑2', singer: '测试歌手2', cover_img: 'https://picsum.photos/100/100?random=2' },
            { id: 3, album_name: '流行专辑', singer: '周杰伦', cover_img: 'https://picsum.photos/100/100?random=3' },
            { id: 4, album_name: '摇滚专辑', singer: '汪峰', cover_img: 'https://picsum.photos/100/100?random=4' }
          ]
        }
      }
    },

    // 获取每周专题列表
    async fetchWeeklyShareList() {
      try {
        const res = await this.$axios.get('/api/album/share/weekly-list')
        if (res.data.code === 200) {
          this.weekList = res.data.data.weekList || []
        }
      } catch (err) {
        console.error('获取每周专题失败：', err)
        this.weekList = []
      }
    },

    // 选择周
    selectWeek(index) {
      this.selectedWeekIndex = index
    },

    // ========== 侧边栏控制方法 ==========
    // 打开新建专题侧边栏
    openCreateSidebar() {
      if (this.albumList.length === 0) {
        alert('暂无可选专辑！')
        return
      }
      // 重置表单+默认填充当前时间
      const now = new Date()
      const formattedNow = now.toISOString().slice(0, 16)
      this.newShareForm = {
        shareTitle: '',
        albumPoolId: '',
        createTime: formattedNow
      }
      this.albumSearchText = '' // 清空搜索
      this.showCreateSidebar = true
      // 关闭其他侧边栏
      this.showAddSidebar = false
      this.showEditSidebar = false
    },

    // 关闭新建专题侧边栏
    closeCreateSidebar() {
      this.showCreateSidebar = false
    },

    // 格式化日期为datetime-local格式（工具方法）
    formatDateForDatetimeLocal(date) {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${day}T${hours}:${minutes}`
    },

    // 打开添加专辑侧边栏（核心修改）
    openAddSidebar() {
      if (this.albumList.length === 0) {
        alert('暂无可选专辑！')
        return
      }
      if (!this.currentWeekSpecial.dateRange) {
        alert('请先选择一个专题！')
        return
      }

      // 1. 解析dateRange获取起始日期
      const dateRange = this.currentWeekSpecial.dateRange
      const startDateStr = dateRange.split(' - ')[0] // 提取起始日期 "2024-02-05"

      // 2. 转换为Date对象并加一天
      const startDate = new Date(startDateStr)
      startDate.setDate(startDate.getDate() + 1) // 加一天

      // 3. 设置时间为00:01
      startDate.setHours(0)
      startDate.setMinutes(1)
      startDate.setSeconds(0)
      startDate.setMilliseconds(0)

      // 4. 格式化为datetime-local所需格式（YYYY-MM-DDTHH:MM）
      const defaultAddTime = this.formatDateForDatetimeLocal(startDate)

      // 重置表单+默认填充计算出的时间（替换原来的当前时间）
      this.addAlbumForm = {
        albumPoolId: '',
        createTime: defaultAddTime // 使用计算出的时间
      }
      this.albumSearchText = '' // 清空搜索
      this.showAddSidebar = true
      // 关闭其他侧边栏
      this.showCreateSidebar = false
      this.showEditSidebar = false
    },

    // 关闭添加专辑侧边栏
    closeAddSidebar() {
      this.showAddSidebar = false
    },

    // 打开编辑标题侧边栏
    openEditSidebar() {
      this.editTitleForm.newTitle = this.currentWeekSpecial.title
      this.showEditSidebar = true
      // 关闭其他侧边栏
      this.showCreateSidebar = false
      this.showAddSidebar = false
    },

    // 关闭编辑标题侧边栏
    closeEditSidebar() {
      this.showEditSidebar = false
    },

    // 关闭所有侧边栏
    closeAllSidebars() {
      this.showCreateSidebar = false
      this.showAddSidebar = false
      this.showEditSidebar = false
    },

    // ========== 业务逻辑方法 ==========
    // 选择专辑（通用方法）
    selectAlbum(albumId, type) {
      if (type === 'create') {
        this.newShareForm.albumPoolId = albumId
      } else if (type === 'add') {
        this.addAlbumForm.albumPoolId = albumId
      }
    },

    // 创建新专题
    async createShare() {
      try {
        if (!this.newShareForm.shareTitle.trim()) {
          alert('请输入专题标题！')
          return
        }
        if (!this.newShareForm.albumPoolId) {
          alert('请选择要分享的专辑！')
          return
        }
        if (!this.newShareForm.createTime) {
          alert('请选择专题创建时间！')
          return
        }

        const shareText = this.newShareForm.shareTitle

        const res = await this.$axios.post('/api/album/share/create', {
          albumPoolId: this.newShareForm.albumPoolId,
          shareText: shareText,
          createTime: this.newShareForm.createTime
        })

        if (res.data.code === 200) {
          this.closeCreateSidebar()
          await this.fetchAvailableAlbumList()
          await this.fetchWeeklyShareList()
        } else {
          alert('创建专题失败：' + res.data.msg)
        }
      } catch (err) {
        console.error('创建专题失败：', err)
        alert('创建专题失败：' + (err.message || '网络错误'))
      }
    },

    // 向专题添加专辑
    async addAlbumToShare() {
      try {
        if (!this.addAlbumForm.albumPoolId) {
          alert('请选择要添加的专辑！')
          return
        }
        if (!this.addAlbumForm.createTime) {
          alert('请选择专辑添加时间！')
          return
        }

        const shareText = this.currentWeekSpecial.title

        const res = await this.$axios.post('/api/album/share/create', {
          albumPoolId: this.addAlbumForm.albumPoolId,
          shareText: shareText,
          createTime: this.addAlbumForm.createTime
        })

        if (res.data.code === 200) {
          this.closeAddSidebar()
          await this.fetchAvailableAlbumList()
          await this.fetchWeeklyShareList()
        } else {
          alert('添加失败：' + res.data.msg)
        }
      } catch (err) {
        console.error('添加专辑失败：', err)
        alert('添加专辑失败：' + (err.message || '网络错误'))
      }
    },

    // 更新专题标题
    async updateShareTitle() {
      try {
        if (!this.editTitleForm.newTitle.trim()) {
          alert('请输入新的专题标题！')
          return
        }

        const weekStart = this.currentWeekSpecial.dateRange.split(' - ')[0]
        const res = await this.$axios.post('/api/album/share/update-title', {
          weekStart,
          newTitle: this.editTitleForm.newTitle
        })

        if (res.data.code === 200) {
          alert('更新专题标题成功！')
          this.closeEditSidebar()
          await this.fetchWeeklyShareList()
        } else {
          alert('更新失败：' + res.data.msg)
        }
      } catch (err) {
        console.error('更新标题失败：', err)
        alert('更新标题失败：' + (err.message || '网络错误'))
      }
    },

    // 删除整个专题
    async deleteCurrentWeekShare() {
      try {
        const weekStart = this.currentWeekSpecial.dateRange.split(' - ')[0]

        const res = await this.$axios.post('/api/album/share/delete-week', {
          weekStart: weekStart
        })

        if (res.data.code === 200) {
          await this.fetchWeeklyShareList()
          this.selectedWeekIndex = 0
        } else {
          alert('删除专题失败：' + res.data.msg)
        }
      } catch (err) {
        console.error('删除专题失败：', err)
        alert('删除专题失败：' + (err.message || '网络错误'))
      }
    },

    // 删除专题中的单张专辑
    async deleteAlbumFromShare(shareId) {
      try {
        if (!shareId) {
          alert('该专辑没有分享ID，无法删除')
          return
        }
        if (!confirm('确定要删除这张专辑吗？')) return

        const res = await this.$axios.post('/api/album/share/delete-album', {
          shareId: shareId
        })

        if (res.data.code === 200) {
          alert('删除专辑成功！')
          await this.fetchWeeklyShareList()
        } else {
          alert('删除失败：' + res.data.msg)
        }
      } catch (err) {
        console.error('删除专辑失败：', err)
        alert('删除专辑异常')
      }
    },

    // 点击专辑：已有则跳详情，没有则入库（和每日推荐逻辑一致）
    async handleAlbumClick(albumId) {
      if (!albumId) return
      try {
        const res = await this.$axios({
          url: `/api/album/pool/copy/${albumId}`,
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
          }
        })

        const {code, data} = res.data
        if (code === 200) {
          window.targetTab = 'mymusic'
          this.$router.push('/webhome')
        } else if (code === 409 && data) {
          const detailId = Number(data) || data
          this.$router.push(`/album/detail/${detailId}?id=${detailId}`)
        } else {
          alert('操作失败：' + (res.data.msg || '未知错误'))
        }
      } catch (err) {
        console.error('专辑点击操作失败：', err)
        alert('操作失败，请稍后重试')
      }
    }
  }
}
</script>

<style scoped>
/* 基础容器样式 */
.music-special-container {
  padding: 20px;
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.1);
  min-height: 600px;
  position: relative;
  z-index: 1;
}

/* 标题和按钮容器 - 核心修改 */
.special-title-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  border-bottom: 4px solid v-bind(mainColorDark);
}

/* 管理员操作按钮 - 核心修改 */
.admin-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  opacity: 0; /* 默认隐藏 */
  transition: opacity 0.3s ease;
}

/* 鼠标悬停时显示按钮 */
.special-title-wrapper:hover .admin-actions {
  opacity: 1;
}

.btn-create-share, .btn-add-album, .btn-edit-title, .btn-delete-week {
  padding: 8px 16px;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-create-share:hover, .btn-add-album:hover, .btn-edit-title:hover, .btn-delete-week:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-add-album:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* 主布局 */
.special-layout {
  display: flex;
  gap: 20px;
  width: 100%;
}

.special-content {
  flex: 3;
}

.special-title {
  color: v-bind(mainColorDarkDouble);
  font-size: 24px;
  font-weight: 600;
  padding-bottom: 10px;
  margin: 0; /* 移除默认margin，避免布局错乱 */
}


.empty-tip {
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  padding: 40px 0;
  font-size: 16px;
}

/* 专辑列表 */
.album-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.album-item {
  display: flex;
  gap: 15px;
  background-color: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 15px;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.album-item:hover {
  background-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.album-item:active {
  transform: scale(0.98);
}

.album-cover img {
  width: 80px;
  height: 80px;
  border-radius: 4px;
  object-fit: cover;
}

.album-info {
  color: v-bind(mainColorDarkDouble);
  flex: 1;
}

.album-name {
  color: v-bind(mainColorDarkDouble);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 5px;
}

.album-singer {
  font-size: 14px;
  margin-bottom: 5px;
  color: v-bind(mainColorDarkDouble);
}

.album-desc {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  line-height: 1.4;
}

/* 日历选择器 */
.calendar-selector {
  flex: 1;
  background-color: rgba(255, 255, 255, 0.05);
  padding: 15px;
  height: fit-content;
  max-height: 600px;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  border-left: 4px solid v-bind(mainColorDark);
}

.calendar-title {
  color: v-bind(mainColorDarkDouble);
  font-size: 18px;
  margin-bottom: 15px;
  font-weight: 600;
  text-align: center;
}

.week-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.week-item {
  padding: 12px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 4px solid transparent;
}

.week-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.week-item.active {
  background-color: v-bind(mainColorDark);
  color: #fff;
  border-left: 4px solid v-bind(mainColorDarkDouble);
}

.week-theme {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.week-date {
  display: block;
  font-size: 12px;
  opacity: 0.9;
}

/* 专辑删除按钮 */
.album-delete-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.album-item:hover .album-delete-btn {
  opacity: 1;
}

.btn-delete-album {
  padding: 4px 8px;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
  background-color: #dc3545;
}

.btn-delete-album:hover {
  opacity: 0.9;
}

/* ========== 左侧边栏样式 ========== */
/* 遮罩层 */
.sidebar-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  transition: opacity 0.3s ease;
}

/* 侧边栏容器 */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 400px;
  height: 100vh;
  background-color: #fff;
  z-index: 1001;
  transform: translateX(-100%);
  transition: transform 0.3s ease;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

/* 侧边栏打开状态 */
.sidebar-open {
  transform: translateX(0);
}

/* 侧边栏头部 */
.sidebar-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-title {
  color: #333;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.sidebar-close {
  background: transparent;
  border: none;
  font-size: 20px;
  color: #666;
  cursor: pointer;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.sidebar-close:hover {
  background-color: #eee;
}

/* 侧边栏主体 */
.sidebar-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* 表单项 */
.form-item {
  margin-bottom: 15px;
}

.form-item label {
  display: block;
  margin-bottom: 5px;
  color: #333;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: v-bind(mainColorDark);
}

/* 专辑选择区域（放到最下方） */
.album-select-section {
  margin-top: auto; /* 固定在底部 */
  margin-bottom: 10px;
}

.search-box {
  margin-bottom: 15px;
}

.album-select-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

/* 1列专辑列表样式（核心修改） */
.album-list-single {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.album-item-single {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.album-item-single:hover {
  border-color: v-bind(mainColorDark);
  background-color: #f8f8f8;
}

.album-item-selected {
  border-color: v-bind(mainColorDarkDouble);
  background-color: rgba(26, 26, 26, 0.05);
}

/* 正方形封面（核心样式） */
.album-cover-square {
  width: 60px;
  height: 60px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
}

.album-cover-square img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 右侧文字区域 */
.album-text {
  flex: 1;
  min-width: 0;
}

.album-name-text {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 3px;
}

.album-singer-text {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-album-tip {
  text-align: center;
  padding: 20px 0;
  color: #999;
  font-size: 14px;
}

/* 侧边栏底部按钮 */
.sidebar-footer {
  padding: 15px 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 8px 16px;
  background-color: #eee;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-confirm {
  padding: 8px 16px;
  background-color: v-bind(mainColorDarkDouble);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-cancel:hover, .btn-confirm:hover {
  opacity: 0.9;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .special-layout {
    flex-direction: column;
  }

  .album-list {
    grid-template-columns: 1fr;
  }

  .calendar-selector {
    max-height: 300px;
  }

  .sidebar {
    width: 90%;
  }

  .album-cover-square {
    width: 50px;
    height: 50px;
  }

  /* 移动端适配按钮显示 */
  .admin-actions {
    opacity: 1 !important;
    margin-top: 10px;
    width: 100%;
  }

  .special-title-wrapper {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>