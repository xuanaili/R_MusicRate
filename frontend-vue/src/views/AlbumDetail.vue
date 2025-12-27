<template>
  <div class="layout-container">
    <aside class="sidebar">
      <button @click="goBack" class="back-btn">← 返回专辑列表</button>
      <div class="sidebar-menu">
        <div class="menu-item" :class="{active: activeTab === 'base'}" @click="activeTab = 'base'">基础信息</div>
        <div class="menu-item" :class="{active: activeTab === 'tracks'}" @click="activeTab = 'tracks'">曲目列表</div>
        <div class="menu-item" :class="{active: activeTab === 'review'}" @click="activeTab = 'review'">听后感</div>
        <div class="menu-item" :class="{active: activeTab === 'comments'}" @click="activeTab = 'comments'">平台评论</div>
      </div>
    </aside>

    <main class="main-content">
      <!-- 基础信息组件 - 核心修复：补充 albumPoolId 传参 -->
      <AlbumBaseInfo
        v-if="activeTab === 'base'"
        :album="album"
        :albumPoolId="albumPoolId || 0"
        @save-tags="saveMyTags"
      />

      <!-- 曲目列表组件 -->
      <AlbumTrackList
        v-if="activeTab === 'tracks'"
        :album="album"
      />

      <!-- 听后感组件 -->
      <AlbumReviewEditor
        v-if="activeTab === 'review'"
        :album="album"
        @add-review="addSingleReview"
        @delete-single="deleteSingleReview"
        @delete-all="deleteAllReview"
      />

      <!-- 评论区组件 -->
      <AlbumCommentSection
        v-if="activeTab === 'comments'"
        :album="album"
        :album-pool-id="albumPoolId"
        :current-user-id="currentUserId"
        :is-admin="isAdmin"
        :blocked-comment-ids="blockedCommentIds"
        :sort-type="sortType"
        :public-comments="publicComments"
        :has-comment="hasComment"
        :my-comment="myComment"
        :other-comments="otherComments"
        @sort-change="changeSortType"
        @block-comment="blockComment"
        @unblock-all="unblockAllComments"
        @submit-comment="submitPublicComment"
        @like-comment="likePublicComment"
        @delete-comment="deletePublicComment"
        @update-comment-content="(val) => newCommentContent = val"
      />
    </main>
  </div>
</template>

<script>
// 引入音乐业务组件
import AlbumBaseInfo from '@/components/music/AlbumBaseInfo'
import AlbumTrackList from '@/components/music/AlbumTrackList'
import AlbumReviewEditor from '@/components/music/AlbumReviewEditor'
import AlbumCommentSection from '@/components/music/AlbumCommentSection'

export default {
  name: 'AlbumDetail',
  components: {
    AlbumBaseInfo,
    AlbumTrackList,
    AlbumReviewEditor,
    AlbumCommentSection
  },
  data() {
    return {
      album: {},
      activeTab: 'base',
      // 公共评论相关
      newCommentContent: '',
      publicComments: [],
      currentUserId: localStorage.getItem('user_id') || '',
      isAdmin: localStorage.getItem('is_admin') === '1',
      albumPoolId: '',  // 公共专辑池ID
      hasComment: false,
      existingCommentId: null,
      sortType: 'time',
      blockedCommentIds: [],
      myComment: null,
      otherComments: []
    };
  },
  computed: {
    filteredComments() {
      return this.publicComments.filter(comment => !this.blockedCommentIds.includes(comment.id.toString()));
    }
  },
  watch: {
    sortType() {
      this.processComments();
    },
    filteredComments() {
      this.processComments();
    },
    album: {
      deep: true,
      handler(newVal) {
        if (newVal.review && newVal.review.personal_feeling && !newVal.review.feelings) {
          newVal.review.feelings = [{
            id: 'old_data',
            content: newVal.review.personal_feeling,
            create_time: newVal.review.update_time || '未知时间'
          }];
        }
      }
    },
    // 监听 albumPoolId 变化，重新请求气泡图数据
    albumPoolId(newVal) {
      if (newVal && this.activeTab === 'base') {
        // 触发 AlbumBaseInfo 重新请求标签统计
        this.$refs.albumBaseInfo?.getAllUsersTagStatistics(newVal);
      }
    }
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    this.currentUserId = localStorage.getItem('user_id');
    this.isAdmin = localStorage.getItem('is_admin') === '1';

    const albumId = this.$route.params.id || this.$route.query.id;
    if (!albumId) {
      alert('未找到专辑ID！');
      this.$router.push('/music');
      return;
    }
    this.getAlbumDetail(Number(albumId)).then(() => {
      this.getAlbumPoolRealId().then(() => {
        // 加载已屏蔽评论ID
        const savedBlockedIds = localStorage.getItem(`blocked_comments_${this.albumPoolId}`);
        if (savedBlockedIds) {
          this.blockedCommentIds = JSON.parse(savedBlockedIds);
        }
        this.checkUserComment();
        this.getPublicComments();
      });
    });
  },
  methods: {
    // 处理评论数据（分离+排序）
    processComments() {
      const myComment = this.filteredComments.find(comment => comment.user_id == this.currentUserId);
      const otherComments = this.filteredComments.filter(comment => comment.user_id != this.currentUserId);

      if (this.sortType === 'time') {
        otherComments.sort((a, b) => new Date(b.create_time) - new Date(a.create_time));
      } else if (this.sortType === 'like') {
        otherComments.sort((a, b) => b.like_count - a.like_count);
      }

      this.myComment = myComment;
      this.otherComments = otherComments;
    },
    // 切换排序方式
    changeSortType(type) {
      this.sortType = type;
    },
    // 屏蔽评论
    blockComment(commentId) {
      if (!this.blockedCommentIds.includes(commentId.toString())) {
        this.blockedCommentIds.push(commentId.toString());
        localStorage.setItem(`blocked_comments_${this.albumPoolId}`, JSON.stringify(this.blockedCommentIds));
        alert('已屏蔽这条评论！');
      }
    },
    // 取消全部屏蔽
    unblockAllComments() {
      this.blockedCommentIds = [];
      localStorage.removeItem(`blocked_comments_${this.albumPoolId}`);
    },
    // 获取公共专辑池ID
    async getAlbumPoolRealId() {
      try {
        if (!this.album.album_name || !this.album.singer) {
          alert('专辑名称或歌手信息缺失，无法创建公共专辑！');
          return;
        }

        const res = await this.$axios({
          url: '/api/album_pool/get_id',
          method: 'GET',
          params: {
            album_name: this.album.album_name,
            singer: this.album.singer
          },
          headers: {
            'Authorization': localStorage.getItem('token') || ''
          }
        });

        if (res.data.code === 200) {
          this.albumPoolId = res.data.data.id;
          console.log('✅ 获取到公共专辑池ID：', this.albumPoolId);
        } else if (res.data.code === 404) {
          await this.createAlbumPool();
        }
      } catch (err) {
        console.error('获取专辑池ID失败：', err);
        alert('获取公共专辑ID失败：' + err.message);
      }
    },
    // 创建专辑到公共专辑池
    async createAlbumPool() {
      try {
        const res = await this.$axios({
          url: '/api/album_pool/add',
          method: 'POST',
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          },
          data: {
            album_name: this.album.album_name,
            cover_img: this.album.cover_img || '',
            singer: this.album.singer,
            release_year: this.album.release_year || 0,
            main_type: this.album.main_type || '',
            tags: this.album.tags || [],
            my_score: this.album.my_score || 0.0
          }
        });
        if (res.data.code === 200) {
          this.albumPoolId = res.data.data.id;
          alert('公共专辑创建成功！ID：' + this.albumPoolId);
        }
      } catch (err) {
        console.error('创建专辑池失败：', err);
        alert('创建公共专辑失败：' + err.message);
      }
    },
    // 检查当前用户是否已评论
    async checkUserComment() {
      if (!this.albumPoolId) return false;
      try {
        const res = await this.$axios({
          url: '/api/album/pool/comment/check',
          method: 'GET',
          params: {
            album_id: this.albumPoolId
          },
          headers: {
            'Authorization': localStorage.getItem('token') || ''
          }
        });
        if (res.data.code === 200) {
          this.hasComment = res.data.data.has_comment;
          this.existingCommentId = res.data.data.comment_id;
          return res.data.data.has_comment;
        }
        return false;
      } catch (err) {
        console.error('检查用户评论失败：', err);
        return false;
      }
    },
    // 获取专辑详情
    getAlbumDetail(albumId) {
      return new Promise((resolve, reject) => {
        this.$axios({
          url: `/api/album/detail/${albumId}`,
          method: 'GET',
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json;charset=utf-8'
          }
        })
        .then((res) => {
          if (res.data.code === 200) {
            this.album = res.data.data;
            this.album.review = this.album.review || {};
            this.album.tracks = this.album.tracks || [];
            // 补充：如果专辑有source_pool_id，优先使用
            if (this.album.source_pool_id) {
              this.albumPoolId = this.album.source_pool_id;
            }
            resolve();
          } else {
            alert(res.data.msg);
            this.$router.push('/music');
            reject(res.data.msg);
          }
        })
        .catch((err) => {
          console.error('获取详情失败：', err);
          alert('获取专辑详情失败！' + err.message);
          this.$router.push('/music');
          reject(err);
        });
      });
    },
    // 保存我的标签
    saveMyTags(tags) {
      this.$axios({
        url: `/api/album/update/tags/${this.album.id}`,
        method: 'PUT',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: { tags }
      }).then(res => {
        if (res.data.code === 200) {
          alert('我的分类标签保存成功！');
          this.album.tags = [...tags];
          // 保存标签后重新请求统计数据
          if (this.albumPoolId) {
            this.$refs.albumBaseInfo?.getAllUsersTagStatistics(this.albumPoolId);
          }
        } else {
          alert('保存失败：' + res.data.msg);
        }
      }).catch(err => {
        console.error('保存标签失败：', err);
        alert('保存标签失败！' + err.message);
      });
    },
    // 新增单条听后感
    addSingleReview(content) {
      if (!content.trim()) {
        alert('听后感内容不能为空！');
        return;
      }
      const now = new Date();
      const createTime = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

      this.$axios({
        url: `/api/album/review/add/${this.album.id}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          content: content.trim(),
          create_time: createTime
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('听后感添加成功！');
          this.getAlbumDetail(this.album.id);
        } else {
          alert(res.data.msg);
        }
      })
      .catch((err) => {
        console.error('添加听后感失败：', err);
        alert('添加听后感失败！' + err.message);
      });
    },
    // 删除单条听后感
    deleteSingleReview(feelingId) {
      if (!confirm('确定要删除这条听后感吗？')) {
        return;
      }
      this.$axios({
        url: `/api/album/review/delete/single/${this.album.id}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: { feeling_id: feelingId }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('听后感删除成功！');
          this.getAlbumDetail(this.album.id);
        } else {
          alert(res.data.msg);
        }
      })
      .catch((err) => {
        console.error('删除听后感失败：', err);
        alert('删除听后感失败！' + err.message);
      });
    },
    // 清空所有听后感
    deleteAllReview() {
      if (!confirm('确定要清空所有听后感吗？')) {
        return;
      }
      this.$axios({
        url: `/api/album/review/delete/${this.album.id}`,
        method: 'DELETE',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('所有听后感已清空！');
          this.getAlbumDetail(this.album.id);
        } else {
          alert(res.data.msg);
        }
      })
      .catch((err) => {
        console.error('清空听后感失败：', err);
        alert('清空听后感失败！' + err.message);
      });
    },
    // 返回专辑列表
    goBack() {
      this.$router.push('/music');
    },
    // 获取公共评论列表
    getPublicComments() {
      if (!this.albumPoolId) {
        alert('公共专辑ID未初始化，请稍后重试！');
        return;
      }
      this.$axios({
        url: `/api/album/pool/comment/list/${this.albumPoolId}`,
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || ''
        }
      }).then(res => {
        if (res.data.code === 200) {
          this.publicComments = res.data.data;
          this.processComments();
        } else {
          alert('获取公共评论失败：' + res.data.msg);
        }
      }).catch(err => {
        console.error('获取公共评论失败：', err);
        alert('获取公共评论失败！');
      });
    },
    // 发布公共评论
    async submitPublicComment() {
      const content = this.newCommentContent.trim();
      if (!content) {
        alert('评论内容不能为空！');
        return;
      }

      if (!this.albumPoolId) {
        await this.getAlbumPoolRealId();
        if (!this.albumPoolId) {
          alert('创建公共专辑失败，无法发布评论！');
          return;
        }
      }

      const hasComment = await this.checkUserComment();
      if (hasComment) {
        alert('你已对该专辑发表过评论，无法重复发布！');
        return;
      }

      try {
        const res = await this.$axios({
          url: '/api/album/pool/comment/add',
          method: 'POST',
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          },
          data: {
            album_id: this.albumPoolId,
            content: content
          }
        });

        if (res.data.code === 200) {
          alert('公共评论发布成功！');
          this.newCommentContent = '';
          this.hasComment = true;
          this.getPublicComments();
        } else {
          alert('发布评论失败：' + res.data.msg);
        }
      } catch (err) {
        console.error('发布失败：', err);
        alert(`发布失败：${err.response?.data?.msg || err.message}`);
      }
    },
    // 评论点赞
    likePublicComment(commentId) {
      this.$axios({
        url: `/api/album/pool/comment/like/${commentId}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || ''
        }
      }).then(res => {
        if (res.data.code === 200) {
          const comment = this.publicComments.find(item => item.id === commentId);
          if (comment) {
            comment.like_count = res.data.data.like_count;
            if (res.data.data.is_liked) {
              comment.like_user_ids.push(this.currentUserId);
            } else {
              comment.like_user_ids = comment.like_user_ids.filter(id => id !== this.currentUserId);
            }
          }
          this.processComments();
        } else {
          alert(res.data.msg);
        }
      }).catch(err => {
        console.error('点赞失败：', err);
        alert('点赞失败！');
      });
    },
    // 删除公共评论
    deletePublicComment(commentId) {
      if (!confirm('确定要删除这条评论吗？')) return;
      this.$axios({
        url: `/api/album/pool/comment/delete/${commentId}`,
        method: 'DELETE',
        headers: {
          'Authorization': localStorage.getItem('token') || ''
        }
      }).then(res => {
        if (res.data.code === 200) {
          alert('评论删除成功！');
          if (commentId === this.existingCommentId) {
            this.hasComment = false;
            this.existingCommentId = null;
          }
          this.getPublicComments();
        } else {
          alert('删除评论失败：' + res.data.msg);
        }
      }).catch(err => {
        console.error('删除公共评论失败：', err);
        alert('删除评论失败！');
      });
    }
  }
};
</script>

<style scoped>
/* 基础布局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.layout-container {
  display: flex;
  width: 100%;
  min-height: 100vh;
  font-family: "Microsoft YaHei", "SimHei", "Arial", sans-serif;
  line-height: 1.8;
  color: #333;
}

.sidebar {
  width: 200px;
  background: #f5f5f5;
  padding: 20px;
  border-right: 1px solid #eee;
}

.back-btn {
  width: 100%;
  padding: 8px 0;
  background: #42b983;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 30px;
  font-size: 14px;
}

.menu-item {
  padding: 10px 0;
  cursor: pointer;
  color: #666;
  border-bottom: 1px solid #eee;
  font-size: 14px;
  transition: all 0.2s;
}

.menu-item.active {
  color: #42b983;
  font-weight: 600;
  background: #f0f8fb;
}

.menu-item:hover {
  color: #42b983;
  background: #f0f8fb;
}

.main-content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}

h1 {
  font-size: 24px;
  margin-bottom: 20px;
  color: #222;
}

h2 {
  font-size: 20px;
  margin-bottom: 18px;
  color: #333;
}

h3 {
  font-size: 18px;
  margin-bottom: 15px;
  color: #444;
}

h4 {
  font-size: 16px;
  margin-bottom: 10px;
  color: #555;
}
</style>