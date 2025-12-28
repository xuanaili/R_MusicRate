<template>
  <div class="tab-content">
    <h2>{{ album.album_name || '未知专辑' }}——公共评论区</h2>

    <!-- 评论输入框 -->
    <div class="comment-input-card">
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
          {{ hasComment ? '你已发表评论，不可重复发布' : '发布评论' }}
        </button>
      </div>
    </div>

    <!-- 排序选项 -->
    <div class="sort-options" v-if="publicComments.length > 0">
      <span class="sort-label">排序方式：</span>
      <button
        class="sort-btn"
        :class="{active: sortType === 'time'}"
        @click="$emit('sort-change', 'time')"
        :style="sortType==='time'?{backgroundColor:mainColorDark,color:'#fff',borderColor:mainColorDark}:{}"
      >
        最新时间
      </button>
      <button
        class="sort-btn"
        :class="{active: sortType === 'like'}"
        @click="$emit('sort-change', 'like')"
        :style="sortType==='like'?{backgroundColor:mainColorDark,color:'#fff',borderColor:mainColorDark}:{}"
      >
        最多点赞
      </button>
    </div>

    <!-- 公共评论列表 -->
    <div class="comments-list-container" v-if="(publicComments.length - blockedCommentIds.length) > 0">
      <!-- 自己的评论 置顶 -->
      <div
        class="comment-item my-comment"
        v-if="myComment"
        :key="myComment.id"
        :style="{border: '2px solid '+mainColorDark, backgroundColor: 'rgba('+hexToRgb(mainColor)+',0.05)'}"
      >
        <div class="comment-header">
          <span class="comment-username" :style="{color:mainColorDark}">{{ myComment.username }}</span>
          <span class="my-tag" :style="{backgroundColor:mainColorDark}">我的评论</span>
          <span v-if="myComment.is_admin" class="admin-tag">管理员</span>
        </div>
        <div class="comment-content">{{ myComment.content }}</div>
        <div class="comment-footer">
          <span class="comment-time">{{ myComment.create_time }}</span>
          <div class="comment-actions">
            <button
              class="like-btn"
              @click="$emit('like-comment', myComment.id)"
              :class="{liked: myComment.like_user_ids.includes(currentUserId)}"
              :style="{color: myComment.like_user_ids.includes(currentUserId) ? '#e53935' : '#999'}"
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

      <!-- 他人的评论 -->
      <div
        class="comment-item"
        v-for="comment in otherComments"
        :key="comment.id"
      >
        <!-- 屏蔽按钮 -->
        <button
          class="block-btn"
          @click="$emit('block-comment', comment.id)"
          title="屏蔽这条评论"
          :style="{backgroundColor:mainColorDark}"
        >
          🚫
        </button>
        <div class="comment-header">
          <span class="comment-username" :style="{color:mainColorDark, fontWeight:600}">{{ comment.username }}</span>
          <span v-if="comment.is_admin" class="admin-tag">管理员</span>
        </div>
        <div class="comment-content">{{ comment.content }}</div>
        <div class="comment-footer">
          <span class="comment-time">{{ comment.create_time }}</span>
          <div class="comment-actions">
            <button
              class="like-btn"
              @click="$emit('like-comment', comment.id)"
              :class="{liked: comment.like_user_ids.includes(currentUserId)}"
              :style="{color: comment.like_user_ids.includes(currentUserId) ? '#e53935' : '#999'}"
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

    <p class="no-comment" v-else>暂无评论，快来抢沙发~</p>

    <!-- 已屏蔽评论提示 -->
    <div class="block-tip" v-if="blockedCommentIds.length > 0">
      已屏蔽 <span>{{ blockedCommentIds.length }}</span> 条评论
      <button class="unblock-all-btn" @click="$emit('unblock-all')" :style="{backgroundColor:mainColorDark}">取消全部屏蔽</button>
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
      type: String,
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
    // ✅✅✅ 接收父组件传的主色+加深色
    mainColor: {
      type: String,
      required: true,
      default: '#42b983'
    },
    mainColorDark: {
      type: String,
      required: true,
      default: '#2f9465'
    }
  },
  data() {
    return {
      commentContent: ''
    };
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
    // 辅助方法：十六进制转rgb，用于背景色透明度
    hexToRgb(hex) {
      const r = parseInt(hex.slice(1,3),16);
      const g = parseInt(hex.slice(3,5),16);
      const b = parseInt(hex.slice(5,7),16);
      return `${r},${g},${b}`;
    }
  }
};
</script>

<style scoped>
.comment-input-card {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.comment-textarea {
  width: 100%;
	padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
  font-size: 14px;
  line-height: 1.6;
}

.comment-textarea:disabled {
  background-color: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.comment-submit-area {
  margin-top: 10px;
  text-align: right;
}

/* 发布按钮 基础样式 */
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

/* 排序选项 */
.sort-options {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f8f8f8;
  border-radius: 4px;
}

.sort-label {
  font-size: 14px;
  color: #666;
}

.sort-btn {
  padding: 4px 12px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.sort-btn:hover:not([style*="backgroundColor"]) {
  border-color: v-bind(mainColorDark);
  color: v-bind(mainColorDark);
}

.comments-list-container {
  margin-top: 20px;
}

/* 评论项 */
.comment-item {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  position: relative;
}

.comment-header {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.my-tag {
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
}

.admin-tag {
  background-color: #e53935;
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
}

.comment-content {
  line-height: 1.6;
  color: #333;
  margin-bottom: 15px;
  font-size: 14px;
}

.comment-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
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
  background-color: rgba(0,0,0,0.03);
}

/* 删除按钮 红色系保留 */
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

/* 屏蔽按钮 */
.block-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  color: white;
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
}
.block-btn:hover {
  opacity: 1;
  filter: brightness(0.9);
}

.no-comment {
  color: #999;
  font-size: 13px;
	margin: 5px 0;
  text-align: center;
  padding: 30px 0;
}

/* 已屏蔽提示 */
.block-tip {
  margin-top: 20px;
  padding: 10px;
  background-color: #f8f8f8;
  border-radius: 4px;
  font-size: 14px;
  color: #666;
  text-align: center;
}

.unblock-all-btn {
  margin-left: 10px;
  padding: 2px 8px;
  color: white;
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