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
            <span class="meta-label">曲目数量：</span>
            <span class="meta-value">{{ album.track_count || 0 }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">我的评分：</span>
            <span class="meta-value">{{ album.my_score || 0.0 }}</span>
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
            >
              {{ tag }}
              <span class="tag-close" @click="removeMyTag(idx)">×</span>
            </div>
          </div>
          <div class="tag-select-container">
            <input
              v-model="tagSearchInput"
              @input="filterTagOptions"
              :placeholder="selectedMyTags.length >=5 ? '最多只能选择5个标签' : '搜索标签（如Pop、Rock）'"
              class="tag-search-input"
              :disabled="selectedMyTags.length >=5"
            >
          </div>
          <button
            class="save-tags-btn"
            @click="handleSaveTags"
            :disabled="!selectedMyTags.length"
            :style="{backgroundColor: selectedMyTags.length ? mainColorDark : '#999'}"
          >
            保存
          </button>
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
            >
              {{ tag }}
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
      // 封面原始主色
      type: String,
      required: true,
      default: '#42b983'
    },
    mainColorDark: {
      // 封面主色 加深1级 (按钮/下划线/已选标签背景)
      type: String,
      required: true,
      default: '#2f9465'
    }
  },
  data() {
    return {
      tagSearchInput: '',
      allTagOptions: ['Pop', 'Rock', 'Jazz', 'Classical', 'Hip-hop', 'Electronic', 'Folk', 'R&B', 'Country', 'Metal'],
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
    // ✅ 核心新增：封面主色 加深2级 (所有文字的颜色，和编辑按钮hover同源)
    mainColorDarkDouble() {
      return this.darkenColor(this.mainColor, 0.3)
    }
  },
  watch: {
    album: {
      immediate: true,
      deep: true,
      handler(newVal) {
        if (newVal.tags && Array.isArray(newVal.tags)) {
          this.selectedMyTags = [...newVal.tags].slice(0, 5);
        }
        this.filteredTagOptions = [...this.allTagOptions];
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
  },
  methods: {
    // 颜色加深算法 (复用原有方法，无改动)
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1, 3), 16) * (1 - amount);
      const g = parseInt(hex.slice(3, 5), 16) * (1 - amount);
      const b = parseInt(hex.slice(5, 7), 16) * (1 - amount);
      return `#${Math.round(r).toString(16).padStart(2, '0')}${Math.round(g).toString(16).padStart(2, '0')}${Math.round(b).toString(16).padStart(2, '0')}`;
    },
    filterTagOptions() {
      const keyword = this.tagSearchInput.trim().toLowerCase();
      this.filteredTagOptions = keyword
          ? this.allTagOptions.filter(tag => tag.toLowerCase().includes(keyword) && !this.selectedMyTags.includes(tag))
          : this.allTagOptions.filter(tag => !this.selectedMyTags.includes(tag));
    },
    addMyTag(tag) {
      if (this.selectedMyTags.length < 5 && !this.selectedMyTags.includes(tag)) {
        this.selectedMyTags.push(tag);
        this.filterTagOptions();
        this.tagSearchInput = '';
      }
    },
    removeMyTag(index) {
      this.selectedMyTags.splice(index, 1);
      this.filterTagOptions();
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
        if (!intro) {
          this.$message?.warning('简介不能为空');
          this.$nextTick(() => this.$refs.introTextarea?.focus());
          return
        }
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
/* 全局盒模型修复 */
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
}

/* 整体卡片背景全透明，无白色边框阴影 */
.new-base-info-card {
  display: grid;
  grid-template-columns: 1fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: 20px;
  background: transparent !important;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
  min-height: 700px;
  margin-top: 0 !important;
  align-self: flex-start;
  width: calc(100vw - 270px - 50px);
  max-width: 100%;
  z-index: 2;
  border: none !important;
  box-shadow: none !important;
}

/* 所有区块无白色边框，透明背景 */
.info-section {
  padding: 15px;
  background: transparent !important;
  border-radius: 8px;
  border: none !important;
  width: 100%;
  height: 100%;
}

/* ✅ 提升优先级：标题下划线+文字颜色 强制生效 */
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

/* 封面占位图：透明磨砂无白色边框 */
.cover-placeholder {
  width: 300px;
  height: 300px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
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

/* ✅ 提升优先级：专辑名称颜色强制生效 */
.meta-album-name {
  font-size: 24px;
  color: v-bind(mainColorDarkDouble) !important;
  margin-bottom: 20px;
  font-weight: 600;
}

.meta-item {
  display: flex;
  margin-bottom: 10px;
  font-size: 16px;
}

/* ✅ 提升优先级：歌手/发行时间等文字颜色强制生效 */
.meta-label {
  width: 80px;
  color: v-bind(mainColorDarkDouble) !important;
  font-weight: 600;
}

.meta-value {
  color: v-bind(mainColorDarkDouble) !important;
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
}

.selected-tag {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  color: #fff;
  border-radius: 4px;
  font-size: 14px;
  cursor: default;
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

/* 搜索框：透明磨砂+加深再加深文字+灰色提示占位符 */
.tag-search-input {
  width: 100%;
  max-width: 200px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border: none !important;
  color: v-bind(mainColorDarkDouble) !important;
}

.tag-search-input::placeholder {
  color: #999;
  opacity: 1;
}

.tag-search-input:disabled {
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.2) !important;
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

/* ✅ 按钮hover → 封面主色加深再加深，和文字颜色一致 */
.save-tags-btn:hover:not(:disabled), .intro-edit-btn:hover:not(:disabled) {
  background-color: v-bind(mainColorDarkDouble) !important;
  opacity: 0.95;
}

.tag-options-column {
  padding: 0;
  display: flex;
  flex-direction: column;
}

/* 标签下拉列表：透明磨砂无白色边框 */
.tag-options-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-height: 200px;
  overflow-y: auto;
  border-radius: 4px;
  padding: 5px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border: none !important;
}

.tag-options-list::-webkit-scrollbar {
  width: 4px;
}

.tag-options-list::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius: 2px;
}

/* ✅ 可选标签文字 → 封面主色加深再加深 */
.tag-option {
  padding: 6px 10px;
  cursor: pointer;
  font-size: 14px;
  border-radius: 4px;
  transition: background 0.2s;
  color: v-bind(mainColorDarkDouble) !important;
}

.tag-option:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.5);
}

.tag-option.disabled {
  color: rgba(0, 0, 0, 0.3) !important;
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.2);
}

.intro-section {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 加载中文字 → 封面主色加深再加深 */
.loading-intro {
  width: 100%;
  max-width: 90%;
  padding: 10px;
  min-height: 140px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: v-bind(mainColorDarkDouble) !important;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border-radius: 4px;
  border: none !important;
}

/* ✅ 专辑简介展示文字 → 封面主色加深再加深 */
.intro-display {
  width: 100%;
  max-width: 90%;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.5;
  min-height: 140px;
  color: v-bind(mainColorDarkDouble) !important;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  white-space: pre-wrap;
  word-wrap: break-word;
  border: none !important;
}

/* ✅ 专辑简介编辑文字 → 封面主色加深再加深 */
.intro-textarea {
  width: 100%;
  max-width: 90%;
  padding: 10px;
  border-radius: 4px;
  resize: vertical;
  font-size: 14px;
  line-height: 1.5;
  rows: 6;
  height: auto;
  min-height: 140px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  color: v-bind(mainColorDarkDouble) !important;
  border: none !important;
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
}

.intro-edit-btn:disabled {
  background: #999;
  cursor: not-allowed;
  opacity: 0.7;
}

.tag-chart-section {
  display: flex;
  flex-direction: column;
  height: 350px;
  margin-top: -20px;
  width: 100%;
  background: transparent !important;
  border: none !important;
  padding-top: 0;
}
</style>