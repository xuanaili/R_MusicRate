<template>
  <div class="album-pool-item">
    <div class="album-info">
      <img v-if="album.cover_img" :src="album.cover_img" alt="封面" class="pool-cover">
      <div v-else class="no-cover">暂无封面</div>
      <div class="pool-info">
        <!-- 专辑名 + +号按钮 + x号按钮 同排：左专辑名，右+号+x号 -->
        <div class="album-name-wrapper">
          <!-- 点击专辑名进入详情 -->
          <h4 @click="handleViewDetail">
            <strong>{{ album.album_name || '未知专辑' }}</strong>
          </h4>
          <!-- +号添加按钮 + x号删除按钮(管理员可见) -->
          <div class="album-btn-group">
            <button @click="handleCopy" class="copy-btn">+</button>
            <button v-if="isAdmin" @click="handleDelete" class="delete-btn-top">×</button>
          </div>
        </div>

        <!-- 标准2×2网格布局 保留原效果 -->
        <div class="info-grid">
          <p class="singer"><strong>歌手：</strong>{{ album.singer || '未知' }}</p>
          <p class="year"><strong>发行年份：</strong>{{ album.release_year || '未知' }}</p>
          <p class="type"><strong>时长类型：</strong>{{ album.duration_type || '未知' }}</p>
          <p class="create-user"><strong>创建用户：</strong>{{ album.create_user_name || '未知' }}</p>
        </div>

        <!-- 标签：悬停显示【】内中文 -->
        <p class="tags">
          <strong>标签：</strong>
          <span
            v-for="(tagItem, index) in album.tag_statistics || []"
            :key="index"
            class="tag-item"
            :title="getTagChinese(tagItem.tag)"
          >
            {{ getTagEnglish(tagItem.tag) }}
          </span>
          <span v-if="!album.tag_statistics || album.tag_statistics.length === 0">无</span>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumPoolItem',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    isAdmin: {
      type: Boolean,
      required: true,
      default: false
    },
    mainColor: {
      type: String,
      default: 'transparent'
    },
    mainColorDark: {
      type: String,
      default: 'transparent'
    },
    mainColorDarkDouble: {
      type: String,
      default: 'transparent'
    }
  },
  methods: {
    handleCopy() {
      this.$emit('copy-album', this.album.id)
    },
    handleViewDetail() {
      this.$emit('view-detail', this.album.id)
    },
    handleDelete() {
      this.$emit('delete-album', this.album.id)
    },
    // 提取【】外的英文展示
    getTagEnglish(tagStr) {
      if (!tagStr || typeof tagStr !== 'string') return '';
      const splitIndex = tagStr.indexOf('【');
      return splitIndex > -1 ? tagStr.substring(0, splitIndex).trim() : tagStr.trim();
    },
    // 提取【】内的中文做悬浮提示
    getTagChinese(tagStr) {
      if (!tagStr || typeof tagStr !== 'string') return '';
      const start = tagStr.indexOf('【');
      const end = tagStr.indexOf('】');
      return start > -1 && end > start ? tagStr.substring(start + 1, end).trim() : tagStr.trim();
    }
  }
};
</script>

<style scoped>
.album-pool-item {
	display: flex;
	justify-content: flex-start;
  align-items: center;
	padding: 20px;
	border-radius: 10px;
	margin-bottom: 20px;
	background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
	border: none;
  position: relative;
  box-sizing: border-box;
  width: 100%;
}

.album-info {
	display: flex;
	gap: 20px;
  align-items: center;
  flex: 1;
  overflow: hidden;
}

/* 封面 100*100 固定尺寸 永不压缩变形 */
.pool-cover, .no-cover {
	width: 100px;
	height: 100px;
	flex-shrink: 0;
	border-radius: 6px;
  display: flex;
	align-items: center;
	justify-content: center;
	overflow: hidden;
}
.pool-cover {
	object-fit: cover;
}
.no-cover {
	border: none;
	color: #999;
	font-size: 12px;
	text-align: center;
}

.pool-info {
  flex: 1;
  overflow: hidden;
  width: 100%;
}

/* 专辑名+按钮组+横线 核心样式 */
.album-name-wrapper {
  position: relative;
  margin: 0 0 12px 0;
	padding-bottom: 4px;
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.album-name-wrapper h4 {
  margin: 0;
	font-size: 18px;
	line-height: 1.3;
	word-break: break-all;
	white-space: normal;
	color: v-bind(mainColorDark);
	font-weight: normal;
	cursor: pointer;
	transition: all 0.2s;
  flex: 1;
}
.album-name-wrapper h4:hover {
	color: v-bind(mainColorDarkDouble);
	text-decoration: underline;
}
/* 下划线从专辑名左端到最右侧按钮右端 完整拉满 */
.album-name-wrapper::after {
	content: '';
	position: absolute;
	left: 0;
	bottom: 0;
	width: 100%;
	height: 4px;
	border-radius: 2px;
	background-color: v-bind(mainColorDark) !important;
	opacity: 1 !important;
}

/* +号x号按钮组 同排右侧 */
.album-btn-group {
  display: flex;
  gap: 20px;
  flex-shrink: 0;
  align-items: center;
}
/* ✅ +号添加按钮 纯文字无样式 核心修改 */
.copy-btn {
  padding: 0;
	border: none;
  background: transparent;
	color: v-bind(mainColorDarkDouble);
	cursor: pointer;
	font-size: 20px;
  font-weight: 800;
	white-space: nowrap;
  line-height: 1;
  flex-shrink: 0;
}
/* ✅ x号删除按钮 纯文字无样式 核心修改 */
.delete-btn-top {
  padding: 0;
	border: none;
  background: transparent;
	color: v-bind(mainColorDarkDouble);
	cursor: pointer;
	font-size: 20px;
  font-weight: 800;
	white-space: nowrap;
  line-height: 1;
  flex-shrink: 0;
}
/* 彻底去掉所有悬浮高亮效果 */
.copy-btn:hover, .delete-btn-top:hover {
  background: transparent;
  color: v-bind(mainColorDarkDouble);
}

/* 2×2网格布局 不变 */
.info-grid {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px 10px;
  margin-bottom: 5px;
}

/* 歌手/年份/时长/创建用户/标签 统一样式不变 */
.singer, .year, .type, .create-user, .tags {
  margin: 0;
	color: v-bind(mainColorDark);
	font-size: 14px;
	line-height: 1.4;
	white-space: nowrap;
}
.tag-item {
	margin-right: 8px;
	cursor: default;
}
.tags {
	margin-top: 5px;
	word-break: break-all;
	white-space: normal;
}
</style>