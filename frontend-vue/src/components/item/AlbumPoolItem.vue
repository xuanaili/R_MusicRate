<template>
  <div class="album-pool-item">
    <div class="album-info">
      <img v-if="album.cover_img" :src="album.cover_img" alt="封面" class="pool-cover">
      <div v-else class="no-cover">暂无封面</div>
      <div class="pool-info">
        <div class="info-row">
          <!-- 第一块：专辑名 独立块 固定宽度+自动换行 -->
          <div class="info-col name-col">
            <h4>{{ album.album_name || '未知专辑' }}</h4>
          </div>
          <!-- 第二块：歌手+时长类型 固定宽度+自动换行 -->
          <div class="info-col singer-col">
            <p>歌手：{{ album.singer || '未知' }}</p>
            <p>时长类型：{{ album.duration_type || '未知' }}</p>
          </div>
          <!-- 第三块：发行年份+创建用户 固定宽度+自动换行 -->
          <div class="info-col year-col">
            <p>发行年份：{{ album.release_year || '未知' }}</p>
            <p>创建用户：{{ album.create_user_name || '未知' }}</p>
          </div>
          <!-- 第四块：标签 自适应宽度+自动换行 最后填充 -->
          <div class="info-col tag-col">
<p>标签：{{ album.tag_statistics?.map(item => item.tag.replace(/【[\s\S]*?】/g, '')).join('、') || '无' }}</p>
          </div>
        </div>
      </div>
    </div>
    <!-- 按钮区：绝对固定位置 永不被挤压 -->
    <div class="pool-actions">
      <button @click="handleCopy" class="copy-btn">复制为我的副本</button>
      <button @click="handleViewDetail" class="detail-btn">查看详情</button>
      <button v-if="isAdmin" @click="handleDelete" class="delete-btn">删除</button>
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
    }
  }
};
</script>

<style scoped>
/* 最外层容器 核心：主轴两端对齐+垂直居中，按钮区固定在右侧 */
.album-pool-item {
	display: flex;
	justify-content: space-between;
  align-items: center;
	padding: 8px 12px;
	border: 1px solid #eee;
	border-radius: 8px;
	margin-bottom: 8px;
	background: #f9f9f9;
  position: relative;
  box-sizing: border-box;
  width: 100%;
}

/* 左侧内容区：封面+所有文字信息，占满除按钮外的所有空间，永不挤压按钮 */
.album-info {
	display: flex;
	gap: 10px;
  align-items: center;
  flex: 1;
  overflow: hidden;
}

.pool-cover, .no-cover {
	width: 80px;
	height: 80px;
	flex-shrink: 0; /* 封面尺寸固定 永不压缩 */
	border-radius: 4px;
}
.no-cover {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
  color: #999;
	font-size: 12px;
}

.pool-info {
  flex: 1;
  overflow: hidden;
}

/* 四块核心内容父容器 - 永久固定布局结构 */
.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px; /* 四块间距 紧凑适中 可微调 */
  width: 100%;
  flex-wrap: nowrap;
}

/* 所有列通用样式：垂直排列+紧凑间距+左对齐 */
.info-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-start;
  flex-shrink: 0;
}

/* ✅ 第一块：专辑名 固定宽度 + 超长自动换行 + 不挤压其他块 */
.name-col {
  width: 200px;
}
.name-col h4 {
  margin: 0;
  color: #333;
  font-size: 15px;
  line-height: 1.3;
  word-break: break-all; /* 超长文字自动换行 */
  white-space: normal;   /* 取消单行限制 核心！ */
}

/* ✅ 第二块：歌手+时长类型 固定宽度 + 超长自动换行 永久对齐 */
.singer-col {
  width: 180px;
}

/* ✅ 第三块：发行年份+创建用户 固定宽度 + 超长自动换行 永久对齐 */
.year-col {
  width: 180px;
}

/* ✅ 第四块：标签 自适应宽度 + 超长自动换行 最后填充 不挤按钮 核心！ */
.tag-col {
  flex: 1;
  min-width: 150px;
  max-width: 300px;
  flex-shrink: 1;
}

/* ✅ 全局文字样式：所有小文字 超长自动换行+完整展示 取消省略号 核心修改 */
.pool-info p {
  margin: 0;
	color: #666;
	font-size: 13px;
  line-height: 1.4;
  white-space: normal;    /* 取消单行限制 自动换行 */
  word-break: break-all;  /* 中英文超长都能换行 */
}

/* ✅ 按钮区 终极固定：永久在最右侧 永不位移 永不被挤压 永不换行 核心！ */
.pool-actions {
	display: flex;
	gap: 8px;
	flex-shrink: 0;         /* 永不压缩 */
	flex-grow: 0;           /* 永不放大 */
  flex-basis: auto;       /* 固定宽度 */
  margin-left: 20px;      /* 和左侧内容区隔开 防止贴边 */
  align-items: center;
}

/* 按钮统一样式 不变 */
.copy-btn, .detail-btn, .delete-btn {
	padding: 6px 12px;
	border: none;
	border-radius: 4px;
	color: white;
	cursor: pointer;
	font-size: 13px;
  white-space: nowrap; /* 按钮文字不换行 */
}
.copy-btn { background: #42b983; }
.detail-btn { background: #007acc; }
.delete-btn { background: #e53935; }
.delete-btn:hover { background: #d32f2f; }
</style>