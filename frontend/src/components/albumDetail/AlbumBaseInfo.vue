<template>
  <div class="tab-content">
    <div class="new-base-info-card">
      <!-- 左上：封面 -->
      <div class="info-section cover-section">
        <img v-if="album.cover_img" :src="album.cover_img" alt="专辑封面" class="big-cover-img">
        <div v-else class="cover-placeholder">{{ album.album_name || '未知' }}</div>
      </div>

      <!-- 右上：拆分为三列（元信息 + 标签选择 + 下拉列表） -->
      <div class="info-section meta-tags-container">
        <!-- 第一列：原专辑元信息 -->
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
            <span class="meta-label">时长类型：</span>
            <span class="meta-value">{{ album.duration_type  || 'LP' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">我的评分：</span>
            <span class="meta-value">{{ albumTotalScore  }}</span>
          </div>
          <!-- ✅ 核心新增：听取时间，放在我的评分正下方，样式完全一致 -->
          <div class="meta-item">
            <span class="meta-label">听取时间：</span>
            <span class="meta-value">{{ formatListeningDuration() }}</span>
          </div>
        </div>

        <!-- 第二列：标签搜索+已选标签 -->
        <div class="my-tags-section-inline">
          <h3 class="section-title">我的分类</h3>
          <div class="selected-tags">
            <div
              class="selected-tag"
              v-for="(tag, idx) in selectedMyTags"
              :key="idx"
              :style="{backgroundColor: mainColorDark}"
              :title="getTagFullText(tag)"
            >
              {{ getTagMainText(tag) }}
              <span class="tag-close" @click="removeMyTag(idx)">×</span>
            </div>
          </div>
          <div class="tag-select-container">
            <input
              v-model="tagSearchInput"
              @input="filterTagOptions"
              :placeholder="selectedMyTags.length >=5 ? '最多只能选择5个标签' : '搜索标签（如Pop、Rock、说唱）'"
              class="tag-search-input"
              :disabled="selectedMyTags.length >=5"
            >
          </div>
        </div>

        <!-- 第三列：标签下拉列表 -->
        <div class="tag-options-column">
          <h3 class="section-title">可选标签</h3>
          <div class="tag-options-list">
            <div
              class="tag-option"
              v-for="tag in filteredTagOptions"
              :key="tag"
              @click="addMyTag(tag)"
              :class="{disabled: selectedMyTags.length >= 5}"
              :title="getTagFullText(tag)"
            >
              {{ getTagMainText(tag) }}
            </div>
          </div>
        </div>
      </div>

      <!-- 左下：可编辑专辑简介 -->
      <div class="info-section intro-section">
        <h3 class="section-title">专辑简介</h3>
        <div v-if="loadingIntro" class="loading-intro">加载中...</div>
        <div v-else-if="!isEditingIntro" class="intro-display">
          {{ albumIntro || '暂无专辑简介' }}
        </div>
        <textarea
          v-else
          v-model="albumIntro"
          class="intro-textarea"
          placeholder="请输入专辑简介（支持分段、特殊符号）..."
          rows="6"
          ref="introTextarea"
        ></textarea>
        <button
          class="intro-edit-btn"
          @click="toggleIntroEdit"
          :disabled="loadingIntro"
          :style="{backgroundColor: mainColorDark}"
        >
          {{ isEditingIntro ? '完成' : '编辑' }}
        </button>
      </div>

      <!-- 右下：分类统计气泡图【✅核心修改1：删除固定绿色，只传动态主色】 -->
      <div class="info-section tag-chart-section">
        <h3 class="section-title">专辑风格</h3>
        <TagBubbleChart
          :tag-stats="tagStatsData"
          :loading="loading"
          :main-color="mainColor"
        />
      </div>
    </div>
  </div>
</template>

<script>
import TagBubbleChart from '@/components/TagBubbleChart'
import config from '@/config/index.js'
export default {
  name: 'AlbumBaseInfo',
  components: { TagBubbleChart },
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    albumPoolId: {
      type: Number,
      required: true
    },
    mainColor: {
      type: String,
      required: true,
      default: '#42b983'
    },
    mainColorDark: {
      type: String,
      required: true,
      default: '#2f9465'
    },
    // ✅ 原有新增：专辑评分
    albumTotalScore: {
      type: Number,
      required: false,
      default: 0.0
    },
    // ✅ 核心新增：听取时间 listening_duration 接收字段
    listening_duration: {
      type: [String, Number], // 兼容字符串/数字格式的时长（如 "125分钟" 或 125）
      required: false,
      default: ''
    }
  },
  data() {
    return {
      tagSearchInput: '',
      filteredTagOptions: [],
      selectedMyTags: [],
      tagStatsData: [],
      loading: false,
      albumIntro: '',
      isEditingIntro: false,
      loadingIntro: false,
      originIntro: '',
      bgStyle: {}
    };
  },
  computed: {
    mainColorDarkDouble() {
      return this.darkenColor(this.mainColor, 0.3)
    }
  },
  watch: {
    album: {
      immediate: true,
      deep: true,
      handler(newVal, oldVal) {
        if (newVal.id !== oldVal?.id) {
          if (newVal.tags && Array.isArray(newVal.tags)) {
            this.selectedMyTags = [...newVal.tags].slice(0, 5);
          }
          this.filteredTagOptions = [...config.albumTagOptions];
          this.filterTagOptions();
          if (this.albumPoolId) {
            this.getAllUsersTagStatistics(this.albumPoolId);
          } else {
            this.tagStatsData = [];
          }
          if (newVal.id) {
            this.getUserAlbumIntro(newVal.id);
          }
        }
      }
    }
  },
  methods: {
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1, 3), 16) * (1 - amount);
      const g = parseInt(hex.slice(3, 5), 16) * (1 - amount);
      const b = parseInt(hex.slice(5, 7), 16) * (1 - amount);
      return `#${Math.round(r).toString(16).padStart(2, '0')}${Math.round(g).toString(16).padStart(2, '0')}${Math.round(b).toString(16).padStart(2, '0')}`;
    },
    // ✅ 新增：提取标签【】外的主体文字（默认展示）
    getTagMainText(tag) {
      if (!tag) return '';
      const match = tag.match(/^(.*?)【/);
      return match ? match[1].trim() : tag;
    },
    // ✅ 新增：获取标签完整文字（悬浮提示）
    getTagFullText(tag) {
      return tag || '';
    },
    filterTagOptions() {
      const keyword = this.tagSearchInput.trim().toLowerCase();
      this.filteredTagOptions = keyword
          ? config.albumTagOptions.filter(tag => tag.toLowerCase().includes(keyword) && !this.selectedMyTags.includes(tag))
          : config.albumTagOptions.filter(tag => !this.selectedMyTags.includes(tag));
    },
    addMyTag(tag) {
      if (this.selectedMyTags.length < 5 && !this.selectedMyTags.includes(tag)) {
        this.selectedMyTags.push(tag);
        this.filterTagOptions();
        this.tagSearchInput = '';
      }
      this.handleSaveTags()
    },
    // ✅✅✅ 核心新增：纯秒数 转 xxh xxmin 格式 【精准适配你的需求】
    formatListeningDuration() {
      // 拿到专辑的纯秒数，容错处理：非数字/空/0 都返回 未知
      const totalSeconds = this.album.listening_duration
      if (!totalSeconds || isNaN(Number(totalSeconds)) || Number(totalSeconds) <= 0) {
        return '未知'
      }
      const secNum = Number(totalSeconds)
      const hours = Math.floor(secNum / 3600) // 总秒数 ÷3600 = 小时数
      const minutes = Math.floor((secNum % 3600) / 60) // 剩余秒数 ÷60 = 分钟数
      // 拼接格式：有小时显示xxhxxmin，无小时只显示xxmin，无多余空格/字符
      return hours > 0 ? `${hours}h${minutes}min` : `${minutes}min`
    },
    removeMyTag(index) {
      this.selectedMyTags.splice(index, 1);
      this.filterTagOptions();
      this.handleSaveTags();
    },
    handleSaveTags() {
      this.$emit('save-tags', this.selectedMyTags);
      this.albumPoolId && this.getAllUsersTagStatistics(this.albumPoolId);
    },
    async getUserAlbumIntro(albumId) {
      try {
        this.loadingIntro = true;
        const res = await this.$axios.get(`/api/album/user/intro/get/${albumId}`);
        this.albumIntro = res.data?.code === 200 ? res.data.data || this.album.album_intro || '' : this.album.album_intro || '';
        this.originIntro = this.albumIntro;
      } catch (e) {
        this.albumIntro = this.album.album_intro || '';
        this.originIntro = this.albumIntro
      } finally {
        this.loadingIntro = false
      }
    },
    async saveUserAlbumIntro(albumId, introContent) {
      try {
        this.loadingIntro = true;
        const res = await this.$axios.post('/api/album/user/intro/save', {
          album_id: albumId,
          intro_content: introContent
        });
        if (res.data?.code === 200) {
          this.$message?.({type: 'success', message: '保存成功'});
          this.$set(this.album, 'album_intro', introContent);
          this.albumIntro = introContent;
          this.isEditingIntro = false;
          return true
        } else {
          this.$message?.({type: 'error', message: res.data?.msg || '保存失败'});
          this.albumIntro = this.originIntro;
          return false
        }
      } catch (e) {
        this.$message?.({type: 'error', message: '保存失败'});
        this.albumIntro = this.originIntro;
        return false
      } finally {
        this.loadingIntro = false
      }
    },
    async toggleIntroEdit() {
      if (this.isEditingIntro) {
        const intro = this.albumIntro.trim();
        // ✅ 移除了非空校验逻辑，允许保存空内容
        const ok = await this.saveUserAlbumIntro(this.album.id, intro);
        ok && (this.isEditingIntro = false);
      } else {
        this.originIntro = this.albumIntro;
        this.$nextTick(() => this.$refs.introTextarea?.focus());
        this.isEditingIntro = true;
      }
    },
    async getAllUsersTagStatistics(albumPoolId) {
      try {
        this.loading = true;
        const res = await this.$axios.get(`/api/album/${albumPoolId}/tag-statistics`);
        this.tagStatsData = res.data?.code === 200 && Array.isArray(res.data.data) ? res.data.data : [];
      } catch (e) {
        this.tagStatsData = []
      } finally {
        this.loading = false
      }
    }
  }
};
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.tab-content {
  padding-top: 0 !important;
  margin-top: 0 !important;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  padding-right: 50px !important;
  position: relative;
  z-index: 1;
  background: transparent !important;
	padding-bottom: 20px !important;
	margin-bottom: 0 !important;
}

.new-base-info-card {
  display: grid;
  grid-template-columns: 1fr 2fr;
  grid-template-rows: 1fr 1fr;
  grid-auto-rows: minmax(0, 1fr);
  gap: 20px;
  background: transparent !important;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 0 !important;
  max-height: 87vh;
	margin-top: 0 !important;
  align-self: flex-start;
  width: calc(100vw - 270px - 50px);
  max-width: 100%;
  z-index: 2;
  border: none !important;
  box-shadow: none !important;
}

.info-section {
  padding: 15px;
  background: transparent !important;
  border-radius: 8px;
  border: none !important;
  width: 100%;
	height: 100%;
  overflow:hidden;
}

.section-title {
  font-size: 16px;
  margin-bottom: 15px;
	padding-bottom: 8px;
  width: 100%;
  box-sizing: border-box;
  text-align: left;
  position: relative;
  border-bottom: none !important;
	color: v-bind(mainColorDarkDouble) !important;
  font-weight: 600;
  left:5px;
}

.section-title::after {
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

/* ============ 核心新增 + 修改 开始 ============ */
.meta-album-name {
  font-size: 24px;
	color: v-bind(mainColorDarkDouble) !important;
  margin-bottom: 20px;
  font-weight: 600;
  /* 新增：和其他标题一致的基础样式 */
  padding-bottom: 8px;
  box-sizing: border-box;
  text-align: left;
  position: relative;
}
/* 新增：专辑名的底部横线伪类，和section-title的横线样式完全一致 */
.meta-album-name::after {
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
/* ============ 核心新增 + 修改 结束 ============ */

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
  border: none !important;
}

.cover-placeholder {
  width: 300px;
  height: 300px;
  border-radius: 8px;
  background: transparent !important;
  display: flex;
  justify-content: center;
  align-items: center;
	color: v-bind(mainColorDarkDouble) !important;
  font-size: 14px;
	border: none !important;
}

.meta-tags-container {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: 15px;
  align-items: flex-start;
	padding: 20px;
  background: transparent !important;
	border: none !important;
}

.meta-section {
  display: flex;
  flex-direction: column;
	padding: 0;
}

.meta-item {
  display: flex;
  margin-bottom: 10px;
  font-size: 16px;
}

.meta-label {
  width: 80px;
	color: v-bind(mainColorDarkDouble) !important;
  font-weight: 600;
}

.meta-value {
	color: v-bind(mainColorDarkDouble) !important;
  max-width: 80%;
  height: 29px;
  overflow-y: auto;
}

.my-tags-section-inline {
  padding: 0;
  display: flex;
  flex-direction: column;
  max-width: calc(100% - 10px);
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  min-height: 40px;
  max-height: 195px;
  overflow-y: auto;
}

.selected-tag {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  color: #fff;
  border-radius: 4px;
  font-size: 14px;
  cursor: default;
  transition: all 0.2s ease;
}
.selected-tag:hover {
  opacity: 0.9;
  transform: scale(1.02);
}

.tag-close {
  margin-left: 8px;
  cursor: pointer;
  font-size: 16px;
	line-height: 1;
}

.tag-select-container {
  margin-bottom: 10px;
  max-width: 100%;
}

.tag-search-input {
  width: 100%;
  max-width: 200px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
  background: transparent !important;
  border: none !important;
	color: v-bind(mainColorDarkDouble) !important;
  outline: none;
}

.tag-search-input::placeholder {
  color: v-bind(mainColorDarkDouble) !important;
  opacity: 1;
}

.tag-search-input:disabled {
  cursor: not-allowed;
  background: transparent !important;
}

.save-tags-btn {
  padding: 6px 12px;
  color: #fff;
  border: none;
	border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
  font-size: 14px;
  transition: all 0.2s;
}

.save-tags-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.save-tags-btn:hover:not(:disabled), .intro-edit-btn:hover:not(:disabled) {
  background-color: v-bind(mainColorDarkDouble) !important;
  opacity: 0.95;
}

.tag-options-column {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.tag-options-list {
  display: flex;
  flex-direction: column;
  gap:5px;
  max-height:200px;
  overflow-y:auto;
  border-radius:4px;
  padding:5px;
  background: transparent !important;
  border:none !important;
}

.tag-options-list::-webkit-scrollbar {
  width:4px;
}

.tag-options-list::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius:2px;
}

.tag-option {
  padding:6px 10px;
  cursor:pointer;
  font-size:14px;
  border-radius:4px;
  transition: background 0.2s;
	color: v-bind(mainColorDarkDouble) !important;
}
.tag-option:hover:not(.disabled) {
  background: rgba(0,0,0,0.05) !important;
  color: v-bind(mainColor) !important;
}

.tag-option.disabled {
  color: rgba(0,0,0,0.3) !important;
  cursor:not-allowed;
  background: transparent !important;
}

.intro-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 0 !important;
  margin-top: -20px;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.loading-intro {
  width: 100%;
  max-width: 90%;
  padding: 10px;
  height: 200px;
  max-height: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
	color: v-bind(mainColorDarkDouble) !important;
  font-size: 14px;
  background: transparent !important;
  border-radius:4px;
	border:none !important;
  overflow: hidden;
}

.intro-display {
  width: 100%;
  max-width: 90%;
  padding: 10px;
  border-radius: 4px;
	font-size: 14px;
  line-height: 1.5;
  height: 200px;
  max-height: 200px;
  color: v-bind(mainColorDarkDouble) !important;
  background: transparent !important;
  white-space: pre-wrap;
  word-wrap: break-word;
	border:none !important;
  overflow-y: auto;
  overflow-x: hidden;
  direction: rtl; /* 核心：反向排版，让滚动条到左侧 */
  text-align: left; /* 强制文字还是左对齐，不影响阅读 */
  padding-left: 10px; /* 给左侧滚动条预留位置，防止遮挡文字 */
}

.intro-textarea {
  width: 100%;
  max-width: 90%;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
  height: 200px;
  max-height: 200px;
  background: transparent !important;
	color: v-bind(mainColorDarkDouble) !important;
	border:none !important;
  position: relative;
  z-index: 999;
  resize: none;
  overflow-y: auto;
  overflow-x: hidden;
}
.intro-textarea::placeholder {
  color: #999;
}

.intro-edit-btn {
  padding: 8px 16px;
  color: #fff;
  border: none;
	border-radius: 4px;
  cursor: pointer;
  align-self: flex-start;
	font-size: 14px;
  transition: all 0.2s;
  position: relative;
  z-index: 9999;
  margin-top: 5px;
}

.intro-edit-btn:disabled {
  background: #999;
  cursor: not-allowed;
  opacity: 0.7;
}

.tag-chart-section {
  display: flex;
  flex-direction: column;
  height: 300px;
  margin-top: -26px;
  width: 100%;
  background: transparent !important;
  border: none !important;
	padding-top: 0;
  padding-bottom: 0 !important;
  overflow: hidden;
}

::-webkit-scrollbar {
  width: 5px;
  height: 0px;
}
::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDark);
  border-radius: 3px;
  opacity: 0.8;
}
::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDarkDouble);
  opacity: 1;
}
</style>