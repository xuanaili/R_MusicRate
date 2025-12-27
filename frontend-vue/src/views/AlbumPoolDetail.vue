<template>
  <div class="pool-detail-container">
    <h2>公共专辑详情</h2>
    <!-- 管理员修改按钮 -->
    <div v-if="isAdmin" class="edit-btn-container">
      <button @click="goEditAlbum" class="edit-btn">修改专辑信息</button>
    </div>

    <div v-if="loading" class="loading-tip">加载中...</div>
    <div v-else-if="!albumData" class="empty-tip">未找到该公共专辑</div>
    <!-- 核心修改：重构布局为左右分栏 -->
    <div v-else class="album-detail-wrapper">
      <!-- 左侧：基础信息 -->
      <div class="album-base-info">
        <div class="cover">
          <img v-if="albumData.cover_img" :src="albumData.cover_img" alt="封面" class="detail-cover">
          <div v-else class="no-cover">暂无封面</div>
        </div>
        <div class="info">
          <h3>{{ albumData.album_name }}</h3>
          <p>歌手：{{ albumData.singer }}</p>
          <p>发行年份：{{ albumData.release_year }}</p>
          <p>标签：{{ albumData.tags?.join('、') || '无' }}</p>
          <p>创建用户：{{ albumData.create_user_name || albumData.create_user || '未知用户' }}</p>
          <!-- 优化：只显示日期，去掉时分秒 -->
          <p class="create-time">创建时间：{{ formatCreateTime(albumData.create_time) }}</p>
        </div>
        <div class="actions">
          <button @click="copyAlbum" class="copy-btn">复制为我的副本</button>
          <button @click="goBack" class="back-btn">返回搜索池</button>
        </div>
      </div>

      <!-- 分隔线 -->
      <div class="divider"></div>

      <!-- 右侧：单曲列表 -->
      <div class="album-songs-list">
        <h4 class="songs-title">单曲列表</h4>
        <!-- 无单曲提示 -->
        <div v-if="!albumData.tracks || albumData.tracks.length === 0" class="no-songs-tip">
          暂无单曲信息
        </div>
        <!-- 单曲列表（带正方形序号） -->
        <ul class="songs-list" v-else>
          <li class="song-item" v-for="(song, index) in albumData.tracks" :key="index">
            <span class="song-index">{{ index + 1 }}</span>
            <span class="song-name">{{ song }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumPoolDetail',
  data() {
    return {
      albumData: null,
      loading: false,
      isAdmin: false // 是否为管理员
    }
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    // 判断是否为管理员
    this.isAdmin = localStorage.getItem('is_admin') === '1';
    // 获取URL中的poolId
    const poolId = this.$route.params.poolId;
    this.getPoolAlbumDetail(poolId);
  },
  methods: {
    // 终极修复：强制解析所有时间格式为YYYY-MM-DD
    formatCreateTime(timeStr) {
      if (!timeStr || timeStr === '') return '未知';

      // 第一步：强制转成Date对象（不管输入格式是什么）
      let date;
      try {
        // 处理各种时间格式：字符串/时间戳/ISO/浏览器格式
        date = new Date(timeStr);
        // 校验是否是有效日期（Invalid Date的时间戳是NaN）
        if (isNaN(date.getTime())) {
          return '未知';
        }
      } catch (e) {
        return '未知';
      }

      // 第二步：手动格式化成年月日（避免浏览器本地化差异）
      const year = date.getFullYear();
      // 月份从0开始，补0
      const month = String(date.getMonth() + 1).padStart(2, '0');
      // 日期补0
      const day = String(date.getDate()).padStart(2, '0');

      // 最终返回：YYYY-MM-DD
      return `${year}-${month}-${day}`;
    },
    // 获取公共专辑详情
    getPoolAlbumDetail(poolId) {
      this.loading = true;
      this.$axios({
        url: `/api/album/pool/detail/${poolId}`,
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}` // 修复Token格式
        }
      })
          .then(res => {
            this.loading = false;
            if (res.data.code === 200) {
              this.albumData = res.data.data;
              // 兼容：确保tracks是数组（避免后端返回字符串/空值）
              if (typeof this.albumData.tracks === 'string') {
                try {
                  this.albumData.tracks = JSON.parse(this.albumData.tracks);
                } catch {
                  this.albumData.tracks = [];
                }
              } else if (!Array.isArray(this.albumData.tracks)) {
                this.albumData.tracks = [];
              }

              // 调试：打印原始时间字符串，方便排查
              console.log('原始创建时间：', this.albumData.create_time);
              console.log('格式化后时间：', this.formatCreateTime(this.albumData.create_time));
            } else {
              alert('获取详情失败：' + res.data.msg);
            }
          })
          .catch(err => {
            this.loading = false;
            console.error('获取公共专辑详情失败：', err);
            alert('获取详情失败！');
          });
    },
    // 复制为我的副本
    copyAlbum() {
      if (!confirm('确定复制该公共专辑为你的私有副本吗？')) return;
      this.$axios({
        url: `/api/album/pool/copy/${this.$route.params.poolId}`,
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}` // 修复Token格式
        }
      })
          .then(res => {
            if (res.data.code === 200) {
              alert('复制成功！跳转到我的专辑列表');
              this.$router.push('/music');
            } else {
              alert('复制失败：' + res.data.msg);
            }
          })
          .catch(err => {
            console.error('复制失败：', err);
            alert('复制失败！');
          });
    },
    // 跳转到修改页面
    goEditAlbum() {
      this.$router.push(`/album/pool/edit/${this.$route.params.poolId}`);
    },
    // 返回搜索池
    goBack() {
      this.$router.push('/album-pool');
    }
  }
};
</script>

<style scoped>
.pool-detail-container {
  max-width: 1000px; /* 加宽容器，适配左右布局 */
  margin: 0 auto;
  padding: 20px;
}

/* 新增修改按钮样式 */
.edit-btn-container {
  text-align: right;
  margin-bottom: 20px;
}

.edit-btn {
  padding: 8px 20px;
  background: #ff9800;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.loading-tip, .empty-tip {
  text-align: center;
  color: #666;
  padding: 30px 0;
}

/* 核心：左右分栏布局 */
.album-detail-wrapper {
  margin-top: 20px;
  display: flex;
  align-items: flex-start;
  gap: 30px;
}

/* 左侧基础信息 */
.album-base-info {
  flex: 1; /* 左侧占1份 */
  min-width: 300px; /* 增大最小宽度，确保时间完整显示 */
}

.cover {
  width: 200px;
  height: 200px;
  margin: 0 auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-cover {
  color: #999;
  font-size: 14px;
}

.info {
  margin-top: 20px;
  text-align: center;
  width: 100%;
  padding: 0 15px;
  box-sizing: border-box;
}

.info h3 {
  font-size: 20px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.info p {
  margin: 10px 0; /* 增大行间距，避免拥挤 */
  color: #666;
  font-size: 15px; /* 增大字体，更清晰 */
  /* 关键：强制换行，确保时间完整显示 */
  white-space: normal;
  word-break: break-all;
}

/* 创建时间专属样式 */
.info .create-time {
  font-size: 14px;
  color: #555;
  font-weight: 500; /* 加粗，更醒目 */
  /* 确保宽度足够 */
  display: block;
  margin-top: 12px;
}

.actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.copy-btn {
  padding: 8px 20px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.back-btn {
  padding: 8px 20px;
  background: #999;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* 分隔线 */
.divider {
  width: 1px;
  background-color: #eee;
  /* 自适应高度 */
  height: auto;
  min-height: 400px;
  align-self: stretch;
}

/* 右侧单曲列表 */
.album-songs-list {
  flex: 1.5; /* 右侧占1.5份，更宽 */
  padding: 10px;
  min-width: 350px; /* 增大最小宽度 */
}

.songs-title {
  font-size: 18px;
  color: #333;
  margin-bottom: 15px;
  border-bottom: 2px solid #42b983;
  padding-bottom: 8px;
}

.no-songs-tip {
  color: #999;
  text-align: center;
  padding: 20px 0;
}

.songs-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.song-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

/* 正方形序号样式 */
.song-index {
  display: inline-block;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  background-color: #42b983;
  color: white;
  font-size: 14px;
  border-radius: 2px; /* 轻微圆角，接近正方形 */
  margin-right: 15px;
}

.song-name {
  font-size: 15px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

/* 响应式适配（小屏幕变回上下布局） */
@media (max-width: 768px) {
  .album-detail-wrapper {
    flex-direction: column;
    gap: 20px;
  }

  .divider {
    width: 100%;
    height: 1px;
    margin: 20px 0;
  }

  .album-base-info, .album-songs-list {
    min-width: 100%; /* 移动端占满宽度 */
  }
}
</style>