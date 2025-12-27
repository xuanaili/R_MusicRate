<template>
  <div class="tab-content">
    <!-- 全新基础信息卡片 -->
    <div class="new-base-info-card">
      <!-- 左上：封面 -->
      <div class="info-section cover-section">
        <img v-if="album.cover_img" :src="album.cover_img" alt="专辑封面" class="big-cover-img">
        <div v-else class="cover-placeholder">{{ album.album_name || '未知' }}</div>
      </div>

      <!-- 右上：拆分为三列（元信息 + 标签选择 + 下拉列表） -->
      <div class="info-section meta-tags-container">
        <!-- 第一列：原专辑元信息（位置不变） -->
        <div class="meta-section">
          <h2 class="meta-album-name">{{ album.album_name || '未知专辑' }}</h2>
          <div class="meta-item">
            <span class="meta-label">歌手：</span>
            <span class="meta-value">{{ album.singer || '未知' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">发行时间：</span>
            <span class="meta-value">{{ album.release_year || '未知' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">曲目数量：</span>
            <span class="meta-value">{{ album.track_count || 0 }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">我的评分：</span>
            <span class="meta-value">{{ album.my_score || 0.0 }}</span>
          </div>
        </div>

        <!-- 第二列：标签搜索+已选标签（右上角中间） -->
        <div class="my-tags-section-inline">
          <h3 class="section-title">我的分类</h3>
          <!-- 已选标签 -->
          <div class="selected-tags">
            <div
              class="selected-tag"
              v-for="(tag, idx) in selectedMyTags"
              :key="idx"
            >
              {{ tag }}
              <span class="tag-close" @click="removeMyTag(idx)">×</span>
            </div>
          </div>
          <!-- 标签搜索框（限制宽度） -->
          <div class="tag-select-container">
            <input
              v-model="tagSearchInput"
              @input="filterTagOptions"
              placeholder="搜索标签（如Pop、Rock）"
              class="tag-search-input"
            >
          </div>
          <div class="tag-tip" v-if="selectedMyTags.length >= 5">
            最多只能选择5个标签
          </div>
          <button
            class="save-tags-btn"
            @click="handleSaveTags"
            :disabled="!selectedMyTags.length"
          >
            保存
          </button>
        </div>

        <!-- 第三列：标签下拉列表（右上角最右侧） -->
        <div class="tag-options-column">
          <h3 class="section-title">可选标签</h3>
          <div class="tag-options-list">
            <div
              class="tag-option"
              v-for="tag in filteredTagOptions"
              :key="tag"
              @click="addMyTag(tag)"
              :class="{disabled: selectedMyTags.length >= 5}"
            >
              {{ tag }}
            </div>
          </div>
        </div>
      </div>

      <!-- 左下：可编辑专辑简介（缩小尺寸） -->
      <div class="info-section intro-section">
        <h3 class="section-title">专辑简介</h3>
        <textarea
          v-model="albumIntro"
          class="intro-textarea"
          placeholder="请输入专辑简介..."
          rows="6"
        ></textarea>
        <button class="save-intro-btn" @click="handleSaveIntro">保存简介</button>
      </div>

      <!-- 右下：分类统计气泡图（展示所有用户标签统计） -->
      <div class="info-section tag-chart-section">
        <h3 class="section-title">全网用户标签统计</h3>
        <!-- 气泡图容器 -->
        <div class="chart-container">
          <!-- 加载中状态 -->
          <div v-if="loading" class="loading-chart">加载中...</div>
          <!-- 气泡图渲染 -->
          <div v-else-if="chartData.length > 0" class="bubble-chart">
            <div
              class="bubble"
              v-for="(item, idx) in chartData"
              :key="idx"
              :style="{
                width: `${item.size}px`,
                height: `${item.size}px`,
                left: `${item.x}%`,
                top: `${item.y - 10}%`,
                backgroundColor: item.color
              }"
            >
              <div class="bubble-label">{{ item.tag }}</div>
              <div class="bubble-value">{{ item.percent }}%</div>
            </div>
          </div>
          <!-- 无数据提示 -->
          <div v-else class="no-chart-data">
            暂无其他用户为该专辑添加标签
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumBaseInfo',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    // 核心新增：接收公共专辑池ID（必传）
    albumPoolId: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      tagSearchInput: '',
      allTagOptions: ['Pop', 'Rock', 'Jazz', 'Classical', 'Hip-hop', 'Electronic', 'Folk', 'R&B', 'Country', 'Metal'],
      filteredTagOptions: [],
      selectedMyTags: [],
      chartData: [],
      loading: false,
      albumIntro: '',
      // 预设颜色池（用于不同标签的气泡颜色）
      colorPool: ['#42b983', '#3498db', '#9b59b6', '#e74c3c', '#f39c12', '#1abc9c', '#8e44ad', '#e67e22']
    };
  },
  watch: {
    album: {
      immediate: true,
      deep: true,
      handler(newVal) {
        // 初始化已选标签（当前用户）
        if (newVal.tags && Array.isArray(newVal.tags)) {
          this.selectedMyTags = [...newVal.tags].slice(0, 5);
        }
        // 初始化专辑简介
        this.albumIntro = newVal.introduction || '';
        // 初始化标签选项
        this.filteredTagOptions = [...this.allTagOptions];
        this.filterTagOptions();
        // 核心修复：调用接口时传入正确的公共专辑ID
        if (this.albumPoolId) {
          console.log('✅ 传入的公共专辑ID：', this.albumPoolId);
          this.getAllUsersTagStatistics(this.albumPoolId);
        } else {
          console.log('⚠️ 未传入公共专辑ID，气泡图无法渲染');
          this.chartData = [];
        }
      }
    }
  },
  methods: {
    // 过滤标签选项（当前用户的标签选择）
    filterTagOptions() {
      const keyword = this.tagSearchInput.trim().toLowerCase();
      if (!keyword) {
        this.filteredTagOptions = this.allTagOptions.filter(tag => !this.selectedMyTags.includes(tag));
      } else {
        this.filteredTagOptions = this.allTagOptions.filter(tag =>
            tag.toLowerCase().includes(keyword) && !this.selectedMyTags.includes(tag)
        );
      }
    },
    // 添加标签（当前用户）
    addMyTag(tag) {
      if (this.selectedMyTags.length < 5 && !this.selectedMyTags.includes(tag)) {
        this.selectedMyTags.push(tag);
        this.filterTagOptions();
        this.tagSearchInput = '';
      }
    },
    // 移除标签（当前用户）
    removeMyTag(index) {
      this.selectedMyTags.splice(index, 1);
      this.filterTagOptions();
    },
    // 保存标签（当前用户）
    handleSaveTags() {
      this.$emit('save-tags', this.selectedMyTags);
      // 保存后重新获取全网统计数据（传正确的公共专辑ID）
      if (this.albumPoolId) {
        this.getAllUsersTagStatistics(this.albumPoolId);
      }
    },
    // 保存专辑简介
    handleSaveIntro() {
      this.$emit('save-intro', this.albumIntro);
      alert('专辑简介保存成功！');
    },
    /**
     * 核心修改：获取所有用户对该专辑的标签统计数据
     * @param {Number} albumPoolId - 公共专辑池ID
     */
    async getAllUsersTagStatistics(albumPoolId) {
      try {
        this.loading = true;
        console.log('📡 请求全网标签统计接口，公共专辑ID：', albumPoolId);

        // 调用标签统计接口（路径与后端保持一致）
        const res = await this.$axios.get(`/api/album/${albumPoolId}/tag-statistics`);

        if (res.data?.code === 200 && Array.isArray(res.data.data)) {
          const tagStats = res.data.data;
          // 计算总标签数和各标签占比
          const total = tagStats.reduce((sum, item) => sum + item.count, 0);

          if (total === 0) {
            this.chartData = [];
            return;
          }

          // 处理数据生成气泡图所需格式
          this.chartData = tagStats.map((item, idx) => {
            const percent = ((item.count / total) * 100).toFixed(1);
            // 根据占比计算气泡大小（50-150px区间）
            const size = Math.min(150, Math.max(50, 50 + percent * 1));
            // 随机位置（避免重叠）
            const x = 10 + (idx * 15) > 85 ? 85 : 10 + (idx * 15);
            const y = 20 + Math.random() * 60;
            // 循环使用颜色池
            const color = this.colorPool[idx % this.colorPool.length];

            return {
              tag: item.tag,
              count: item.count,
              percent: percent,
              size: size,
              x: x,
              y: y,
              color: color
            };
          });
        } else {
          console.warn('⚠️ 接口返回数据格式异常', res.data);
          this.chartData = [];
        }
      } catch (error) {
        console.error('❌ 获取全网标签统计失败：', {
          url: error.config?.url,
          status: error.response?.status,
          message: error.message,
          responseData: error.response?.data
        });
        this.chartData = [];
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
/* 基础布局：保留2×2网格 + 与sidebar上端对齐 */
.new-base-info-card {
  display: grid;
  grid-template-columns: 1fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  min-height: 700px;
  margin-top: 0 !important; /* 取消顶部外边距，与sidebar上端对齐 */
  align-self: flex-start; /* 顶部对齐 */
}

.info-section {
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #eee;
}

.section-title {
  font-size: 16px;
  color: #42b983;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

/* 封面区域 */
.cover-section {
  display: flex;
  justify-content: center;
  align-items: center;
}

.big-cover-img {
  width: 300px;
  height: 300px;
  border-radius: 8px;
  object-fit: cover;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.cover-placeholder {
  width: 300px; /* 同步封面尺寸 */
  height: 300px;
  border-radius: 8px;
  background: #f5f5f5;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #999;
  font-size: 14px;
}

/* 右上容器：三列布局 */
.meta-tags-container {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr; /* 三等分 */
  gap: 15px;
  align-items: flex-start;
  padding: 20px;
}

/* 第一列：元信息 */
.meta-section {
  display: flex;
  flex-direction: column;
  padding: 0;
}

.meta-album-name {
  font-size: 24px;
  color: #222;
  margin-bottom: 20px;
}

.meta-item {
  display: flex;
  margin-bottom: 10px;
  font-size: 16px;
}

.meta-label {
  width: 80px;
  color: #666;
  font-weight: 600;
}

.meta-value {
  color: #333;
}

/* 第二列：标签选择（中间） */
.my-tags-section-inline {
  padding: 0;
  display: flex;
  flex-direction: column;
  max-width: calc(100% - 10px); /* 限制宽度，避免超出 */
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  min-height: 40px;
}

.selected-tag {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: #42b983;
  color: #fff;
  border-radius: 4px;
  font-size: 14px;
}

.tag-close {
  margin-left: 8px;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

.tag-select-container {
  margin-bottom: 10px;
  max-width: 100%; /* 限制容器宽度 */
}

/* 核心：限制搜索框宽度，右端不超过标签列表左端 */
.tag-search-input {
  width: 100%;
  max-width: 200px; /* 固定最大宽度，根据实际调整 */
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.tag-tip {
  font-size: 12px;
  color: #e53935;
  margin-bottom: 10px;
}

.save-tags-btn {
  padding: 6px 12px;
  background: #42b983;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
  font-size: 14px;
}

.save-tags-btn:disabled {
  background: #999;
  cursor: not-allowed;
}

/* 第三列：标签下拉列表（最右侧） */
.tag-options-column {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.tag-options-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 4px;
  padding: 5px;
}

.tag-option {
  padding: 6px 10px;
  cursor: pointer;
  font-size: 14px;
  border-radius: 4px;
  transition: background 0.2s;
}

.tag-option:hover {
  background: #f0f8fb;
}

.tag-option.disabled {
  color: #999;
  cursor: not-allowed;
  background: #f5f5f5;
}

/* 左下：专辑简介（缩小尺寸） */
.intro-section {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 缩小简介框：行数减少+宽度适配 */
.intro-textarea {
  width: 100%;
  max-width: 90%; /* 限制最大宽度 */
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  font-size: 14px;
  line-height: 1.5;
  rows: 6; /* 固定6行 */
  height: auto; /* 自适应高度 */
}

.save-intro-btn {
  padding: 8px 16px;
  background: #42b983;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
}

/* 右下：气泡图区域（上移调整） */
.tag-chart-section {
  display: flex;
  flex-direction: column;
  height: 280px; /* 容器高度减少，整体上移 */
  margin-top: -20px; /* 顶部负边距，整体上移 */
}

.chart-container {
  flex: 1;
  position: relative;
  background: #f8f8f8;
  border-radius: 4px;
  overflow: hidden;
  min-height: 230px; /* 容器高度上移 */
  border: 1px solid #eee;
}

.loading-chart {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #666;
  font-size: 14px;
}

.bubble-chart {
  position: relative;
  width: 100%;
  height: 100%;
}

.bubble {
  position: absolute !important;
  border-radius: 50% !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: center !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
  transition: transform 0.2s !important;
  z-index: 99 !important;
}

.bubble:hover {
  transform: scale(1.05) !important;
}

.bubble-label {
  font-size: 14px !important;
  font-weight: 600 !important;
  margin-bottom: 4px !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
}

.bubble-value {
  font-size: 12px !important;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
}

.no-chart-data {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #999;
  font-size: 14px;
}

/* 确保tab-content与sidebar对齐 */
.tab-content {
  padding-top: 0 !important;
  margin-top: 0 !important;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
</style>