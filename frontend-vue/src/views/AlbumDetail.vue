<!-- MusicRate\frontend-vue\src\views\AlbumDetail.vue -->
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
      <!-- 基础信息 Tab -->
      <div v-if="activeTab === 'base'" class="tab-content">
        <h1>《{{ album.album_name || '未知专辑' }}》</h1>
        <div class="base-info">
          <p>专辑名: {{ album.album_name || '未知' }}</p>
          <p>封面: {{ album.cover_img || album.album_name + '.jpg' || '未知.jpg' }}</p>
          <p>歌手: {{ album.singer || '未知' }}</p>
          <p>发行时间: "{{ album.release_year || '未知' }}"</p>
          <p>曲目数量: {{ album.track_count || 0 }}</p>
          <p>曲目时长: "{{ album.track_duration || '0.00' }}"</p>
          <p>我的评分: {{ album.my_score || 0.0 }}</p>
          <p>刻录分类: {{ album.burn_class || '-' }}</p>
          <p>tags:</p>
          <ul class="tags-list">
            <li v-for="tag in (album.tags || [])" :key="tag">- {{ tag }}</li>
          </ul>
        </div>

        <div class="bookinfo-card">
          <h3>《{{ album.album_name || '未知专辑' }}》</h3>
          <div class="cover-preview">
            <img v-if="album.cover_img" :src="album.cover_img" alt="专辑封面" class="cover-img">
            <span v-else>[{{ album.album_name || '未知' }}.jpg]</span>
          </div>
          <table class="info-table">
            <tr>
              <th>作者</th>
              <td>{{ album.singer || '未知' }}</td>
            </tr>
            <tr>
              <th>发行时间</th>
              <td>{{ album.release_year || '未知' }}</td>
            </tr>
            <tr>
              <th>曲目数量</th>
              <td>{{ album.track_count || 0 }}</td>
            </tr>
            <tr>
              <th>曲目时长</th>
              <td>{{ album.track_duration || '0.00' }}</td>
            </tr>
            <tr>
              <th>分类</th>
              <td>{{ (album.tags && album.tags.length > 0) ? album.tags.join('、') : '无' }}</td>
            </tr>
            <tr>
              <th>评分</th>
              <td>{{ album.my_score || 0.0 }}</td>
            </tr>
          </table>
        </div>
      </div>

      <!-- 曲目列表 Tab -->
      <div v-if="activeTab === 'tracks'" class="tab-content">
        <h2>内容</h2>
        <h3>简介</h3>
        <div class="tracks-list">
          <div v-for="(track, idx) in (album.tracks || [])" :key="idx">
            <h4>{{ idx+1 }}. {{ track.track_name || '未知曲目' }}  {{ track.duration || '0:00' }}</h4>
          </div>
        </div>

        <div class="tip-card">
          <h3>开始欣赏</h3>
          <div class="query-code">
            path: 音乐库/{{ album.id || '未知' }}
          </div>
        </div>
      </div>

      <!-- 听后感 Tab -->
      <div v-if="activeTab === 'review'" class="tab-content">
        <h2>{{ album.album_name || '未知专辑' }}——听后感</h2>
        <div class="audio-link">[{{ album.album_name || '未知' }}.mp3]</div>

        <!-- 新增听后感区域 -->
        <div class="review-edit-area">
          <textarea
            v-model="newFeelingContent"
            placeholder="输入你的听后感..."
            class="review-textarea"
            rows="3"
          ></textarea>
          <div class="review-actions">
            <button @click="addSingleReview" class="save-btn">新增听后感</button>
            <button @click="deleteAllReview" class="delete-btn" v-if="(album.review || {}).feelings?.length">清空所有听后感</button>
          </div>
        </div>

        <!-- 所有听后感列表 -->
        <div class="feelings-list" v-if="(album.review || {}).feelings?.length">
          <h3>历史听后感</h3>
          <div
            class="feeling-item"
            v-for="(feeling, idx) in (album.review || {}).feelings"
            :key="feeling.id || idx"
          >
            <div class="feeling-content">{{ feeling.content }}</div>
            <div class="feeling-meta">
              <span class="create-time">{{ feeling.create_time }}</span>
              <button class="delete-single-btn" @click="deleteSingleReview(feeling.id)">删除</button>
            </div>
          </div>
        </div>
        <p class="no-feeling" v-else>暂无听后感记录，快来添加吧~</p>

        <!-- 原有评分部分 -->
        <div class="score-section">
          <h4>单曲评分</h4>
          <div v-for="(track, idx) in (album.tracks || [])" :key="idx">
            <p>{{ track.score || 0 }}->>>{{ idx+1 }}. {{ track.track_name || '未知曲目' }}  {{ track.duration || '0:00' }}</p>
          </div>
          <p>最终评分：{{ album.my_score || 0.0 }}</p>
        </div>
      </div>

      <!-- 平台评论 Tab（完全重构：多用户共享评论） -->
      <div v-if="activeTab === 'comments'" class="tab-content">
        <h2>{{ album.album_name || '未知专辑' }}——公共评论区</h2>

        <!-- 评论输入框（适配新接口：已评论时禁用） -->
        <div class="comment-input-card">
          <textarea
            v-model="newCommentContent"
            placeholder="分享你的听后感..."
            class="comment-textarea"
            rows="3"
            :disabled="hasComment"
          ></textarea>
          <div class="comment-submit-area">
            <button
              @click="submitPublicComment"
              class="submit-btn"
              :disabled="!newCommentContent.trim() || hasComment"
            >
              {{ hasComment ? '你已发表评论，不可重复发布' : '发布评论' }}
            </button>
          </div>
        </div>

        <!-- 公共评论列表（显示用户名、时间、点赞） -->
        <div class="comments-list-container" v-if="publicComments.length > 0">
          <div class="comment-item" v-for="comment in publicComments" :key="comment.id">
            <!-- 评论头部：左上角显示用户名 -->
            <div class="comment-header">
              <span class="comment-username">{{ comment.username }}</span>
              <!-- 管理员标识 -->
              <span v-if="comment.is_admin" class="admin-tag">管理员</span>
            </div>
            <!-- 评论内容 -->
            <div class="comment-content">{{ comment.content }}</div>
            <!-- 评论底部：左下角时间 + 右下角点赞/删除 -->
            <div class="comment-footer">
              <span class="comment-time">{{ comment.create_time }}</span>
              <div class="comment-actions">
                <button
                  class="like-btn"
                  @click="likePublicComment(comment.id)"
                  :class="{liked: comment.like_user_ids.includes(currentUserId)}"
                >
                  👍 {{ comment.like_count }}
                </button>
                <!-- 管理员/评论作者可删除 -->
                <button
                  v-if="isAdmin || comment.user_id == currentUserId"
                  class="delete-comment-btn"
                  @click="deletePublicComment(comment.id)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
        <p class="no-comment" v-else>暂无评论，快来抢沙发~</p>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'AlbumDetail',
  data() {
    return {
      album: {},
      activeTab: 'base',
      newFeelingContent: '',
      // 新增：公共评论相关
      newCommentContent: '',       // 公共评论输入内容
      publicComments: [],          // 多用户共享评论列表
      currentUserId: localStorage.getItem('user_id') || '', // 当前用户ID（登录时存储）
      isAdmin: localStorage.getItem('is_admin') === '1',    // 是否为管理员
      albumPoolId: '',              // 公共专辑池ID（关键：初始化）
      hasComment: false,           // 是否已对该专辑发表评论
      existingCommentId: null      // 已发表的评论ID
    };
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    // 初始化用户信息
    this.currentUserId = localStorage.getItem('user_id');
    this.isAdmin = localStorage.getItem('is_admin') === '1';

    const albumId = this.$route.params.id || this.$route.query.id;
    if (!albumId) {
      alert('未找到专辑ID！');
      this.$router.push('/music');
      return;
    }
    // 先获取专辑详情，再获取/创建公共专辑ID（异步顺序保证）
    this.getAlbumDetail(Number(albumId)).then(() => {
      this.getAlbumPoolRealId().then(() => {
        // 初始化时检查是否已评论
        this.checkUserComment();
      });
    });
  },
  watch: {
    album: {
      deep: true,
      handler(newVal) {
        if (newVal.review && newVal.review.personal_feeling) {
          if (!newVal.review.feelings) {
            newVal.review.feelings = [{
              id: 'old_data',
              content: newVal.review.personal_feeling,
              create_time: newVal.review.update_time || '未知时间'
            }];
          }
        }
      }
    }
  },
  methods: {
    // 获取公共专辑池ID：不存在则自动创建
    async getAlbumPoolRealId() {
      try {
        // 校验专辑基础信息
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
          this.getPublicComments(); // 自动加载评论列表
        } else if (res.data.code === 404) {
          // 公共专辑不存在，自动创建
          await this.createAlbumPool();
          if (this.albumPoolId) {
            this.getPublicComments();
          }
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
          alert('公共专辑创建成功！');
        }
      } catch (err) {
        console.error('创建专辑池失败：', err);
        alert('创建公共专辑失败：' + err.message);
      }
    },

    // 检查当前用户是否已对该专辑发表评论
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

    // 获取专辑详情（返回Promise，保证异步顺序）
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

    // 新增单条听后感
    addSingleReview() {
      if (!this.newFeelingContent.trim()) {
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
          content: this.newFeelingContent.trim(),
          create_time: createTime
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('听后感添加成功！');
          this.newFeelingContent = '';
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
        data: {
          feeling_id: feelingId
        }
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

    // ==================== 公共评论核心方法 ====================
    // 1. 获取公共评论列表
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
        } else {
          alert('获取公共评论失败：' + res.data.msg);
        }
      }).catch(err => {
        console.error('获取公共评论失败：', err);
        alert('获取公共评论失败！');
      });
    },

    // 2. 发布公共评论（自动处理公共专辑ID + 重复评论校验）
    async submitPublicComment() {
      const content = this.newCommentContent.trim();
      if (!content) {
        alert('评论内容不能为空！');
        return;
      }

      // 自动获取/创建公共专辑ID
      if (!this.albumPoolId) {
        await this.getAlbumPoolRealId();
        if (!this.albumPoolId) {
          alert('创建公共专辑失败，无法发布评论！');
          return;
        }
      }

      // 发布前检查是否已评论
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
          this.hasComment = true; // 更新评论状态
          this.getPublicComments(); // 刷新评论列表
        } else {
          alert('发布评论失败：' + res.data.msg);
        }
      } catch (err) {
        console.error('发布失败：', err);
        alert(`发布失败：${err.response?.data?.msg || err.message}`);
      }
    },

    // 3. 公共评论点赞/取消点赞
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
        } else {
          alert(res.data.msg);
        }
      }).catch(err => {
        console.error('点赞失败：', err);
        alert('点赞失败！');
      });
    },

    // 4. 删除公共评论（保留作者+管理员权限）
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
          // 如果删除的是自己的评论，重置评论状态
          if (commentId === this.existingCommentId) {
            this.hasComment = false;
            this.existingCommentId = null;
          }
          this.getPublicComments(); // 刷新评论列表
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
/* 基础样式 */
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

.tab-content {
  width: 100%;
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

h5 {
  font-size: 14px;
  margin-bottom: 8px;
  color: #666;
}

.base-info {
  margin-bottom: 30px;
  font-size: 14px;
}

.base-info p {
  margin: 8px 0;
}

.tags-list {
  margin: 5px 0 15px 2em;
  color: #666;
  font-size: 14px;
}

.bookinfo-card {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.cover-img {
  width: 100px;
  height: 100px;
  margin: 10px 0;
  border-radius: 4px;
  object-fit: cover;
}

.cover-preview {
  margin: 10px 0;
  color: #007acc;
  font-size: 14px;
}

.info-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  font-size: 14px;
}

.info-table th, .info-table td {
  border: 1px solid #ddd;
  padding: 8px 12px;
  text-align: center;
}

.info-table th {
  background: #f5f5f5;
  font-weight: 600;
}

.tip-card {
  background: #f0f8fb;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.query-code {
  background: #2d2d2d;
  color: #fff;
  padding: 12px;
  border-radius: 4px;
  font-family: "Consolas", "Monaco", monospace;
  font-size: 13px;
  margin-top: 10px;
}

.tracks-list {
  margin: 20px 0;
  font-size: 14px;
}

.audio-link {
  color: #007acc;
  margin: 10px 0;
  font-size: 14px;
}

.score-section {
  margin: 20px 0;
  font-size: 14px;
}

.review-edit-area {
  margin: 20px 0;
}

.review-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  margin-bottom: 10px;
}

.review-actions {
  margin-bottom: 15px;
}

.save-btn {
  padding: 8px 20px;
  background: #42b983;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
}

.delete-btn {
  padding: 8px 20px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.update-time {
  color: #999;
  font-size: 12px;
  margin-top: 5px;
}

.feeling-section {
  margin: 20px 0;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 8px;
  font-size: 14px;
}

.forum-group {
  margin: 10px 0 20px 2em;
  font-size: 14px;
}

.footer-tip {
  text-align: center;
  color: #999;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px dashed #eee;
  font-size: 14px;
}

/* 原有评论样式（兼容） */
.album-comments {
  margin: 20px 0;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
}

.comments-list {
  margin: 15px 0;
}

.comments-list ul {
  list-style: none;
  padding: 0;
  margin: 8px 0;
}

.comments-list li {
  background: #fff;
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 6px;
  font-size: 13px;
  color: #555;
}

.no-comment {
  color: #999;
  font-size: 13px;
  margin: 5px 0;
  text-align: center;
  padding: 30px 0;
}

.comment-input-area {
  margin-top: 15px;
}

.comment-input {
  padding: 8px;
  width: 250px;
  margin-right: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.comment-btn {
  padding: 8px 15px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.comment-btn:hover {
  background: #3aa876;
}

/* 听后感列表样式 */
.feelings-list {
  margin: 20px 0;
}

.feeling-item {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid #eee;
}

.feeling-content {
  color: #333;
  line-height: 1.6;
  margin-bottom: 10px;
}

.feeling-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.delete-single-btn {
  padding: 4px 8px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.delete-single-btn:hover {
  background: #c0392b;
}

.no-feeling {
  color: #999;
  text-align: center;
  margin: 20px 0;
  font-size: 14px;
}

/* 公共评论专属样式 */
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

.submit-btn {
  padding: 8px 20px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.submit-btn:disabled {
  background: #999;
  cursor: not-allowed;
}

.comments-list-container {
  margin-top: 20px;
}

.comment-item {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}

.comment-header {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.comment-username {
  font-weight: 600;
  color: #42b983;
  font-size: 14px;
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
  color: #999;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.like-btn.liked {
  color: #e53935;
}

.delete-comment-btn {
  padding: 4px 8px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.delete-comment-btn:hover {
  background: #c0392b;
}
</style>