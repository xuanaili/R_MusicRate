<template>
  <div class="album-pool-item">
    <div class="album-info">
      <img v-if="album.cover_img" :src="album.cover_img" alt="封面" class="pool-cover">
      <div v-else class="no-cover">暂无封面</div>
      <div class="pool-info">
        <h4>{{ album.album_name || '未知专辑' }}</h4>
        <p>歌手：{{ album.singer || '未知' }}</p>
        <p>发行年份：{{ album.release_year || '未知' }}</p>
        <p>时长类型：{{ album.duration_type || '未知' }}</p>
        <p>标签：{{ album.tag_statistics?.map(item => item.tag).join('、') || '无' }}</p>
        <p>创建用户：{{ album.create_user_name || '未知' }}</p>
      </div>
    </div>
    <div class="pool-actions">
      <button @click="handleCopy" class="copy-btn">复制为我的副本</button>
      <button @click="handleViewDetail" class="detail-btn">查看详情</button>
      <!-- 仅管理员显示删除按钮 -->
      <button
        v-if="isAdmin"
        @click="handleDelete"
        class="delete-btn"
      >删除</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumPoolItem',
  // 严格的props校验，和你给的子组件写法一致
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
    }
  },
  methods: {
    // 复制专辑 - 派发事件给父组件处理
    handleCopy() {
      this.$emit('copy-album', this.album.id)
    },
    // 查看详情 - 派发事件给父组件处理
    handleViewDetail() {
      this.$emit('view-detail', this.album.id)
    },
    // 删除专辑 - 派发事件给父组件处理
    handleDelete() {
      this.$emit('delete-album', this.album.id)
    }
  }
};
</script>

<style scoped>
.album-pool-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 15px;
	border: 1px solid #eee;
	border-radius: 8px;
	margin-bottom: 15px;
	background: #f9f9f9;
}

.album-info {
	display: flex;
	gap: 15px;
	align-items: center;
	flex: 1;
}

.pool-cover {
	width: 80px;
	height: 80px;
	object-fit: cover;
	border-radius: 4px;
}

.no-cover {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
  border-radius: 4px;
  color: #999;
  font-size: 12px;
}

.pool-info {
	flex: 1;
}

.pool-info h4 {
	margin: 0 0 8px 0;
	color: #333;
}

.pool-info p {
	margin: 4px 0;
	color: #666;
	font-size: 14px;
}

.pool-actions {
	display: flex;
	gap: 10px;
}

.copy-btn {
	padding: 6px 12px;
	background: #42b983;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}

.detail-btn {
	padding: 6px 12px;
	background: #007acc;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}

.delete-btn {
	padding: 6px 12px;
	background: #e53935;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
}

.delete-btn:hover {
	background: #d32f2f;
}
</style>