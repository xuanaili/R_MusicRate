<template>
  <div class="tab-content">
    <!-- 输入框保留蒙版+外层框纯透明 -->
    <div v-if="!hasComment" class="comment-input-card">
      <textarea
        v-model="commentContent"
        placeholder="分享你的听后感..."
        class="comment-textarea"
        rows="3"
        :disabled="hasComment"
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

    <div
      v-else
      class="comment-has-tip"
      :style="{backgroundColor: mainColorDark, color: '#ffffff'}"
    >
      你已发表评论，不可重复发布
    </div>

    <div class="sort-options" v-if="publicComments.length > 0">
      <button
        class="tab-item sort-btn"
        :class="{active: sortType === 'time'}"
        @click="$emit('sort-change', 'time')"
      >
        最新时间
      </button>
      <button
        class="tab-item sort-btn"
        :class="{active: sortType === 'like'}"
        @click="$emit('sort-change', 'like')"
      >
        最多点赞
      </button>
    </div>

    <div
        class="comments-list-container"
        v-if="(publicComments.length - blockedCommentIds.length) > 0"
    >
      <!-- 我的评论 -->
      <div
        class="comment-item my-comment"
        v-if="myComment"
        :key="myComment.id"
        :style="{border: 'none', backgroundColor: 'transparent'}"
      >
        <!-- ✅ 新增：竖线容器 - 包裹用户名+评论内容 -->
        <div class="comment-left-line-wrapper">
          <div class="comment-header" :style="{backgroundColor: 'transparent'}">
            <span class="comment-username" :style="{color: mainColorDarkDouble, fontWeight: '600'}">{{ myComment.username }}</span>
            <span class="my-tag" :style="{backgroundColor:mainColorDark, color: '#ffffff'}">我的评论</span>
            <span v-if="myComment.is_admin" class="admin-tag">管理员</span>
          </div>
          <div class="comment-content" :style="{color: mainColorDarkDouble, backgroundColor: 'transparent'}">{{ myComment.content }}</div>
        </div>
        <div class="comment-line" :style="{backgroundColor: mainColorDark, height: '4px', borderRadius: '2px', width: '100%', margin: '8px 0'}"></div>
        <div class="comment-footer" :style="{backgroundColor: 'transparent'}">
          <span class="comment-time" :style="{color: mainColorDarkDouble}">{{ myComment.create_time }}</span>
          <div class="comment-actions">
            <button
              class="like-btn"
              @click="$emit('like-comment', myComment.id)"
              :class="{liked: myComment.like_user_ids.includes(currentUserId)}"
              :style="{color: myComment.like_user_ids.includes(currentUserId) ? '#e53935' : mainColorDark}"
            >
              👍 {{ myComment.like_count }}
            </button>
            <button
              class="delete-comment-btn"
              @click="$emit('delete-comment', myComment.id)"
              :style="{backgroundColor: mainColorDark, color: '#ffffff'}"
            >
              删除
            </button>
          </div>
        </div>
      </div>

      <!-- 他人评论 -->
      <div
        class="comment-item"
        v-for="comment in otherComments"
        :key="comment.id"
        :style="{backgroundColor: 'transparent', border: 'none'}"
      >
        <button
          class="block-btn"
          @click="$emit('block-comment', comment.id)"
          title="屏蔽这条评论"
          :style="{backgroundColor:mainColorDark, color: '#ffffff'}"
        >
          🚫
        </button>
        <!-- ✅ 新增：竖线容器 - 包裹用户名+评论内容 -->
        <div class="comment-left-line-wrapper">
          <div class="comment-header" :style="{backgroundColor: 'transparent'}">
            <span class="comment-username" :style="{color: mainColorDarkDouble, fontWeight:600}">{{ comment.username }}</span>
            <span v-if="comment.is_admin" class="admin-tag">管理员</span>
          </div>
          <div class="comment-content" :style="{color: mainColorDarkDouble, backgroundColor: 'transparent'}">{{ comment.content }}</div>
        </div>
        <div class="comment-line" :style="{backgroundColor: mainColorDark, height: '4px', borderRadius: '2px', width: '100%', margin: '8px 0'}"></div>
        <div class="comment-footer" :style="{backgroundColor: 'transparent'}">
          <span class="comment-time" :style="{color: mainColorDarkDouble}">{{ comment.create_time }}</span>
          <div class="comment-actions">
            <button
              class="like-btn"
              @click="$emit('like-comment', comment.id)"
              :class="{liked: comment.like_user_ids.includes(currentUserId)}"
              :style="{color: comment.like_user_ids.includes(currentUserId) ? '#e53935' : mainColorDark}"
            >
              👍 {{ comment.like_count }}
            </button>
            <button
              v-if="isAdmin || comment.user_id == currentUserId"
              class="delete-comment-btn"
              @click="$emit('delete-comment', comment.id)"
              :style="{backgroundColor: mainColorDark, color: '#ffffff'}"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <p class="no-comment" :style="{color: mainColorDarkDouble}">暂无评论，快来抢沙发~</p>

    <div class="block-tip" v-if="blockedCommentIds.length > 0" :style="{color: mainColorDarkDouble}">
      已屏蔽 <span>{{ blockedCommentIds.length }}</span> 条评论
      <button class="unblock-all-btn" @click="$emit('unblock-all')" :style="{backgroundColor:mainColorDark, color: '#ffffff'}">取消全部屏蔽</button>
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
h2 {
  font-size: 18px;
  margin-bottom: 20px;
  font-weight: 600;
}

/* 发布评论外层容器 纯透明 */
.comment-input-card {
  padding: 20px;
	border-radius: 8px;
  margin-bottom: 20px;
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
	border: none !important;
}

/* 输入框保留轻微蒙版 */
.comment-textarea {
  width: 100%;
  padding: 8px;
  border: none !important;
	border-radius: 4px;
  resize: vertical;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
  background: rgba(255, 255, 255, 0.2) !important;
  outline: none;
  color: v-bind(mainColorDarkDouble) !important;
}

.comment-textarea::placeholder {
  color: v-bind(mainColorDarkDouble);
  opacity: 0.6;
  font-weight: 400;
}

.comment-textarea:disabled {
  background-color: rgba(255, 255, 255, 0.1) !important;
  cursor: not-allowed;
}

.comment-submit-area {
  margin-top: 10px;
  text-align: right;
}

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

.comment-has-tip {
  width: 100%;
  padding: 12px 0;
	border: none;
	border-radius: 6px;
  text-align: center;
	font-weight: 500;
	font-size: 14px;
  margin-bottom: 20px;
  cursor: not-allowed;
  opacity: 0.95;
  display: block;
  transition: all 0.2s ease;
}

.comment-has-tip:hover {
  opacity: 1;
  filter: brightness(0.95);
}

.sort-options {
  display: flex;
  gap: 10px;
	margin-bottom: 20px;
  padding-bottom: 8px;
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
	border-radius: 4px;
	border: none !important;
  width: 100%;
  box-sizing: border-box;
  text-align: left;
  position: relative;
}

.tab-item {
  padding: 8px 16px;
	border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  color: v-bind(mainColorDarkDouble);
  transition: all 0.2s;
  font-weight: 600;
  position: relative;
	border: none;
  background: transparent;
}
.tab-item.active {
  background: v-bind(mainColorDark);
  color: #fff;
}
.tab-item::after {
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

.comments-list-container {
  margin-top: 20px;
}

.comment-item {
	border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  position: relative;
  box-sizing: border-box;
}

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

.admin-tag {
  background: #e53935;
  color: white;
	font-size: 10px;
  padding: 2px 6px;
	border-radius: 10px;
}

/* ✅ 核心新增：左侧竖线容器 - 关键样式 */
.comment-left-line-wrapper {
  position: relative;
  padding-left: 16px; /* 竖线和内容的间距 */
  margin-bottom: 8px; /* 和底部横线的间距 */
}
/* ✅ 左侧竖线 - 样式与排序按钮横线完全一致 */
.comment-left-line-wrapper::before {
  content: '';
  position: absolute;
  left: -30px;
  top: 0; /* 对齐用户名顶部 */
  bottom: 0; /* 对齐评论内容底部 */
  width: 4px; /* 和排序按钮横线高度一致 */
  border-radius: 2px; /* 和排序按钮横线圆角一致 */
  background-color: v-bind(mainColorDark) !important; /* 和排序按钮横线颜色一致 */
}

.comment-content {
  line-height: 1.6;
  margin-bottom: 0;
  font-size: 14px;
  font-weight: 400;
  padding: 8px;
	border-radius: 4px;
}

.comment-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 400;
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

.delete-comment-btn {
  padding: 4px 8px;
	border: none;
	border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.delete-comment-btn:hover {
  opacity: 0.95;
  filter: brightness(0.9);
}

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
  font-size: 15px;
  font-weight: 600;
  margin: 5px 0;
  text-align: center;
	padding: 30px 0;
  background: transparent !important;
}

.block-tip {
  margin-top: 20px;
  padding: 10px;
  background: transparent !important;
	border-radius: 4px;
  font-size: 15px;
  font-weight: 600;
  text-align: center;
	border: none !important;
}
</style>