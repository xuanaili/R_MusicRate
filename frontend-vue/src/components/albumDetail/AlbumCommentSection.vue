<template>
  <div class="tab-content">
    <!-- 标题颜色绑定 封面加深再加深色 + 智能文字色适配 -->
    <h2 :style="{color: isDarkMainColor ? '#ffffff' : mainColorDarkDouble}">{{ album.album_name || '未知专辑' }}——公共评论区</h2>

    <!-- ✅ 核心改版：分2种状态 - 无评论【带磨砂蒙版输入框】 | 有评论【隐藏输入框+只留提示按钮】 -->
    <div v-if="!hasComment" class="comment-input-card">
      <textarea
        v-model="commentContent"
        placeholder="分享你的听后感..."
        class="comment-textarea"
        rows="3"
        :disabled="hasComment"
        :style="{color: isDarkMainColor ? '#ffffff' : '#333'}"
      ></textarea>
      <div class="comment-submit-area">
        <button
          @click="handleSubmitComment"
          class="submit-btn"
          :disabled="!commentContent.trim() || hasComment"
          :style="{backgroundColor: mainColorDark}"
        >
          发布评论
        </button>
      </div>
    </div>

    <!-- ✅ 修改点：四字提示改为按钮样式 + 智能文字适配 -->
    <div
      v-else
      class="comment-has-tip"
      :style="{backgroundColor: mainColorDark, color: isDarkMainColorDark ? '#ffffff' : '#333'}"
    >
      你已发表评论，不可重复发布
    </div>

    <!-- ✅ 修改点：排序选项 + 全量智能文字适配 -->
    <div class="sort-options" v-if="publicComments.length > 0">
      <span class="sort-label"
            :style="{backgroundColor: mainColorWhiteDouble,color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333',borderColor:mainColorWhiteDouble}"
      >排序方式：</span>
      <button
        class="sort-btn"
        :class="{active: sortType === 'time'}"
        @click="$emit('sort-change', 'time')"
        :style="sortType==='time'?{backgroundColor:mainColorWhiteDouble,color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333',borderColor:mainColorWhiteDouble}:{color: isDarkMainColor ? '#ffffff' : '#333', borderColor: isDarkMainColor ? mainColorDark : '#ddd', backgroundColor: isDarkMainColor ? mainColorDark : '#fff'}"
      >
        最新时间
      </button>
      <button
        class="sort-btn"
        :class="{active: sortType === 'like'}"
        @click="$emit('sort-change', 'like')"
        :style="sortType==='like'?{backgroundColor:mainColorWhiteDouble,color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333',borderColor:mainColorWhiteDouble}:{color: isDarkMainColor ? '#ffffff' : '#333', borderColor: isDarkMainColor ? mainColorDark : '#ddd', backgroundColor: isDarkMainColor ? mainColorDark : '#fff'}"
      >
        最多点赞
      </button>
    </div>

    <!-- 公共评论列表 -->
    <div
        class="comments-list-container"
        v-if="(publicComments.length - blockedCommentIds.length) > 0"
    >
      <!-- ✅ 自己的评论 置顶 - 和其他用户评论 样式完全统一 -->
      <div
        class="comment-item my-comment"
        v-if="myComment"
        :key="myComment.id"
        :style="{border: '2px solid '+mainColorWhiteDouble, backgroundColor: mainColorWhiteDouble}"
      >
        <div class="comment-header" :style="{backgroundColor: mainColorWhiteDouble}">
          <span class="comment-username" :style="{color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333', fontWeight: '600'}">{{ myComment.username }}</span>
          <span class="my-tag" :style="{backgroundColor:mainColorDark, color: isDarkMainColorDark ? '#ffffff' : '#fff'}">我的评论</span>
          <span v-if="myComment.is_admin" class="admin-tag">管理员</span>
        </div>
        <div class="comment-content" :style="{color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333', backgroundColor: mainColorWhiteDouble}">{{ myComment.content }}</div>
        <div class="comment-footer" :style="{backgroundColor: mainColorWhiteDouble}">
          <span class="comment-time" :style="{color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333'}">{{ myComment.create_time }}</span>
          <div class="comment-actions">
            <button
              class="like-btn"
              @click="$emit('like-comment', myComment.id)"
              :class="{liked: myComment.like_user_ids.includes(currentUserId)}"
              :style="{color: myComment.like_user_ids.includes(currentUserId) ? '#e53935' : isDarkMainColorWhiteDouble ? '#ffffff' : '#999'}"
            >
              👍 {{ myComment.like_count }}
            </button>
            <button
              class="delete-comment-btn"
              @click="$emit('delete-comment', myComment.id)"
            >
              删除
            </button>
          </div>
        </div>
      </div>

      <!-- ✅ 他人的评论 - 和自己的评论 样式完全统一（核心修改同步处） -->
      <div
        class="comment-item"
        v-for="comment in otherComments"
        :key="comment.id"
        :style="{backgroundColor: mainColorWhiteDouble, border: '2px solid '+mainColorWhiteDouble}"
      >
        <!-- 屏蔽按钮 -->
        <button
          class="block-btn"
          @click="$emit('block-comment', comment.id)"
          title="屏蔽这条评论"
          :style="{backgroundColor:mainColorDark, color: isDarkMainColorDark ? '#ffffff' : '#fff'}"
        >
          🚫
        </button>
        <div class="comment-header" :style="{backgroundColor: mainColorWhiteDouble}">
          <span class="comment-username" :style="{color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333', fontWeight:600}">{{ comment.username }}</span>
          <span v-if="comment.is_admin" class="admin-tag">管理员</span>
        </div>
        <div class="comment-content" :style="{color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333', backgroundColor: mainColorWhiteDouble}">{{ comment.content }}</div>
        <div class="comment-footer" :style="{backgroundColor: mainColorWhiteDouble}">
          <span class="comment-time" :style="{color: isDarkMainColorWhiteDouble ? '#ffffff' : '#333'}">{{ comment.create_time }}</span>
          <div class="comment-actions">
            <button
              class="like-btn"
              @click="$emit('like-comment', comment.id)"
              :class="{liked: comment.like_user_ids.includes(currentUserId)}"
              :style="{color: comment.like_user_ids.includes(currentUserId) ? '#e53935' : isDarkMainColorWhiteDouble ? '#ffffff' : '#999'}"
            >
              👍 {{ comment.like_count }}
            </button>
            <button
              v-if="isAdmin || comment.user_id == currentUserId"
              class="delete-comment-btn"
              @click="$emit('delete-comment', comment.id)"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <p class="no-comment" :style="{color: isDarkMainColor ? '#ffffff' : '#999'}">暂无评论，快来抢沙发~</p>

    <!-- 已屏蔽评论提示 - 智能文字色适配 -->
    <div class="block-tip" v-if="blockedCommentIds.length > 0" :style="{color: isDarkMainColor ? '#ffffff' : '#666'}">
      已屏蔽 <span>{{ blockedCommentIds.length }}</span> 条评论
      <button class="unblock-all-btn" @click="$emit('unblock-all')" :style="{backgroundColor:mainColorDark, color: isDarkMainColorDark ? '#ffffff' : '#fff'}">取消全部屏蔽</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumCommentSection',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    albumPoolId: {
      type: [String, Number],
      required: true,
      default: ''
    },
    currentUserId: {
      type: String,
      required: true,
      default: ''
    },
    isAdmin: {
      type: Boolean,
      required: true,
      default: false
    },
    blockedCommentIds: {
      type: Array,
      required: true,
      default: () => []
    },
    sortType: {
      type: String,
      required: true,
      default: 'time'
    },
    publicComments: {
      type: Array,
      required: true,
      default: () => []
    },
    hasComment: {
      type: Boolean,
      required: true,
      default: false
    },
    myComment: {
      type: Object,
      default: null
    },
    otherComments: {
      type: Array,
      required: true,
      default: () => []
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
    mainColorDarkDouble: {
      type: String,
      required: true,
      default: '#257d51'
    },
    mainColorWhite: {type: String, required: true, default: '#57c592'},
    mainColorWhiteDouble: {type: String, required: true, default: '#6cd1a1'}
  },
  data() {
    return {
      commentContent: ''
    };
  },
  // ✅ 4个全色系亮度判断，全局复用
  computed: {
    isDarkMainColor() {
      return this.calculateColorBrightness(this.mainColor) < 128;
    },
    isDarkMainColorWhite() {
      return this.calculateColorBrightness(this.mainColorWhite) < 128;
    },
    isDarkMainColorWhiteDouble() {
      return this.calculateColorBrightness(this.mainColorWhiteDouble) < 128;
    },
    isDarkMainColorDark() {
      return this.calculateColorBrightness(this.mainColorDark) < 128;
    }
  },
  watch: {
    commentContent(val) {
      this.$emit('update-comment-content', val);
    }
  },
  methods: {
    handleSubmitComment() {
      this.$emit('submit-comment');
    },
    hexToRgb(hex) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `${r},${g},${b}`;
    },
    // ✅ 行业通用的RGB亮度计算公式，精准度极高
    calculateColorBrightness(hex) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return (r * 299 + g * 587 + b * 114) / 1000;
    }
  }
};
</script>

<style scoped>
/* 标题基础样式 无固定颜色 */
h2 {
  font-size: 18px;
  margin-bottom: 20px;
  font-weight: 600;
}

/* ✅ 无评论状态 - 输入框容器 带透明磨砂蒙版 无边框 */
.comment-input-card {
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.25) !important;
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  border: none !important;
}

/* ✅ 无评论状态 - 输入框本身 半透明底 无边框 有输入质感 */
.comment-textarea {
  width: 100%;
  padding: 10px;
  border: none !important;
  border-radius: 4px;
  resize: vertical;
  font-size: 14px;
  line-height: 1.6;
  background: rgba(255, 255, 255, 0.3) !important;
  outline: none;
}

.comment-textarea:disabled {
  background-color: rgba(255, 255, 255, 0.2) !important;
  cursor: not-allowed;
}

.comment-submit-area {
  margin-top: 10px;
  text-align: right;
}

/* 发布按钮 样式不变 */
.submit-btn {
  padding: 8px 20px;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:disabled {
  background: #999 !important;
  cursor: not-allowed;
  opacity: 0.7;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.95;
  filter: brightness(0.9);
}

/* ✅ 四字提示按钮样式 */
.comment-has-tip {
  width: 100%;
  padding: 12px 0;
  border: none;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
  margin-bottom: 20px;
  cursor: not-allowed;
  opacity: 0.95;
  display: block;
  font-weight: 500;
  transition: all 0.2s ease;
}

.comment-has-tip:hover {
  opacity: 1;
  filter: brightness(0.95);
}

/* ✅ 排序方式容器 纯净透明样式 */
.sort-options {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px;
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border-radius: 4px;
  border: none !important;
}

.sort-label {
  padding: 1px 8px;
  border-radius: 4px;
  cursor: default;
  font-size: 14px;
  transition: all 0.2s;
}

.sort-btn {
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  border: 1px solid;
}

.sort-btn:hover:not([style*="backgroundColor"]) {
  border-color: v-bind(mainColorDark);
  color: v-bind(mainColorDark);
}

.comments-list-container {
  margin-top: 20px;
}

/* 评论项基础样式 - 所有评论统一 */
.comment-item {
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  position: relative;
  box-sizing: border-box;
}

/* 用户名行样式优化 - 所有评论统一 */
.comment-header {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
}

.my-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
}

/* 管理员标签 红色保留 不变 */
.admin-tag {
  background: #e53935;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
}

/* 评论内容样式 - 所有评论统一 */
.comment-content {
  line-height: 1.6;
  margin-bottom: 10px;
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
}

/* 时间行样式优化 - 所有评论统一 */
.comment-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 6px 8px;
  border-radius: 4px;
}

.comment-time {
  flex: 1;
}

.comment-actions {
  display: flex;
  gap: 10px;
}

/* 点赞按钮样式 */
.like-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.like-btn:hover {
  background-color: rgba(0, 0, 0, 0.03);
}

/* 删除按钮 红色系保留 不变 */
.delete-comment-btn {
  padding: 4px 8px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.delete-comment-btn:hover {
  background: #c0392b;
  opacity: 0.95;
}

/* 屏蔽按钮样式不变 */
.block-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
  opacity: 0.7;
  transition: all 0.2s;
  z-index: 2;
}

.block-btn:hover {
  opacity: 1;
  filter: brightness(0.9);
}

.no-comment {
  font-size: 13px;
  margin: 5px 0;
  text-align: center;
  padding: 30px 0;
}

/* 已屏蔽提示样式 */
.block-tip {
  margin-top: 20px;
  padding: 10px;
  background: transparent !important;
  border-radius: 4px;
  font-size: 14px;
  text-align: center;
  border: none !important;
}

.unblock-all-btn {
  margin-left: 10px;
  padding: 2px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.unblock-all-btn:hover {
  opacity: 0.95;
  filter: brightness(0.9);
}
</style>