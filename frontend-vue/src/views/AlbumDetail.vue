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
            <h4>{{ idx+1 }}. {{ track.name || '未知曲目' }}  {{ track.time || '0:00' }}</h4>
          </div>
        </div>

        <div class="tip-card">
          <h3>开始欣赏</h3>
          <div class="query-code">
            path: 音乐库/{{ album.code || '未知' }}
          </div>
        </div>
      </div>

      <!-- 听后感 Tab -->
      <div v-if="activeTab === 'review'" class="tab-content">
        <h2>{{ album.album_name || '未知专辑' }}——听后感</h2>
        <div class="audio-link">[{{ album.album_name || '未知' }}.mp3]</div>

        <div class="review-edit-area">
          <textarea
            v-model="reviewContent"
            placeholder="输入你的听后感..."
            class="review-textarea"
            rows="6"
          ></textarea>
          <div class="review-actions">
            <button @click="saveReview" class="save-btn">保存听后感</button>
            <button @click="deleteReview" class="delete-btn" v-if="reviewContent">删除听后感</button>
          </div>

          <div v-if="(album.review || {}).update_time" class="update-time">
            最后编辑时间：{{ (album.review || {}).update_time }}
          </div>
        </div>

        <div class="score-section">
          <h4>评分</h4>
          <div v-for="(track, idx) in (album.tracks || [])" :key="idx">
            <p>{{ track.score || 0 }}->>>{{ idx+1 }}. {{ track.name || '未知曲目' }}  {{ track.time || '0:00' }}</p>
          </div>
          <p>单曲打分：{{ (album.review || {}).single_score || 0.0 }}</p>
          <p>私自打分：{{ (album.review || {}).private_score || 0.0 }}</p>
          <p>最终评分：{{ (album.review || {}).final_score || 0.0 }}</p>
        </div>

        <div class="feeling-section" v-if="(album.review || {}).personal_feeling">
          <h4>个人感想</h4>
          <p>{{ (album.review || {}).personal_feeling }}</p>
        </div>
      </div>

      <!-- 平台评论 Tab -->
      <div v-if="activeTab === 'comments'" class="tab-content">
        <h2>{{ album.album_name || '未知专辑' }}——评论</h2>

        <!-- 新增：专辑评论区 -->
        <div class="album-comments">
          <h3>专辑评论</h3>
          <div class="comments-list">
            <ul v-if="album.comments && album.comments.length > 0">
              <li v-for="(comment, idx) in album.comments" :key="idx">{{ comment }}</li>
            </ul>
            <p v-else class="no-comment">暂无评论</p>
          </div>
          <div class="comment-input-area">
            <input
              v-model="newComment"
              placeholder="输入评论"
              class="comment-input"
            >
            <button @click="submitComment" class="comment-btn">提交评论</button>
          </div>
        </div>


        <div class="footer-tip">
          别忘记评分，写标签，以及记录读完时间
        </div>
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
      reviewContent: '',
      newComment: '' // 新增：评论输入框绑定值
    };
  },
  created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    const albumId = this.$route.params.id || this.$route.query.id;
    if (!albumId) {
      alert('未找到专辑ID！');
      this.$router.push('/music');
      return;
    }
    this.getAlbumDetail(Number(albumId));
  },
  watch: {
    album: {
      deep: true,
      handler(newVal) {
        // 修复：先判断review是否存在
        if (newVal.review && newVal.review.personal_feeling) {
          this.reviewContent = newVal.review.personal_feeling;
        }
      }
    }
  },
  methods: {
    getAlbumDetail(albumId) {
      this.$axios({
        url: `http://127.0.0.1:5000/api/album/detail/${albumId}`,
        method: 'GET',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          this.album = res.data.data;
          // 修复：默认review为空对象
          this.album.review = this.album.review || {};
          // 确保comments字段存在
          this.album.comments = this.album.comments || [];
          this.reviewContent = this.album.review.personal_feeling || '';
        } else {
          alert(res.data.msg);
          this.$router.push('/music');
        }
      })
      .catch((err) => {
        console.error('获取详情失败：', err);
        alert('获取专辑详情失败！' + err.message);
        this.$router.push('/music');
      });
    },
    saveReview() {
      if (!this.reviewContent.trim()) {
        alert('听后感内容不能为空！');
        return;
      }
      const now = new Date();
      const updateTime = `${now.getFullYear()}-${(now.getMonth()+1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

      this.$axios({
        url: `http://127.0.0.1:5000/api/album/review/edit/${this.album.id}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          personal_feeling: this.reviewContent,
          update_time: updateTime
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('听后感保存成功！');
          this.getAlbumDetail(this.album.id);
        } else {
          alert(res.data.msg);
        }
      })
      .catch((err) => {
        console.error('保存听后感失败：', err);
        alert('保存听后感失败！' + err.message);
      });
    },
    deleteReview() {
      if (!confirm('确定要删除听后感吗？')) {
        return;
      }
      this.$axios({
        url: `http://127.0.0.1:5000/api/album/review/delete/${this.album.id}`,
        method: 'DELETE',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('听后感删除成功！');
          this.reviewContent = '';
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
    // 新增：提交评论方法
    submitComment() {
      const comment = this.newComment.trim()
      if (!comment) {
        alert('评论不能为空！')
        return
      }

      // 方式1：如果后端有添加评论的接口，调用接口
      this.$axios({
        url: `http://127.0.0.1:5000/api/album/comment/add/${this.album.id}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          comment: comment
        }
      })
      .then((res) => {
        if (res.data.code === 200) {
          alert('评论提交成功！');
          this.newComment = '';
          this.getAlbumDetail(this.album.id); // 重新获取数据刷新评论列表
        } else {
          alert(res.data.msg);
        }
      })
      .catch((err) => {
        console.error('提交评论失败：', err);
        alert('提交评论失败！' + err.message);
      });

      // 方式2：如果暂时没有后端接口，先本地添加（注释掉方式1，启用方式2）
      // this.album.comments.push(comment);
      // this.newComment = '';
      // alert('评论提交成功！');
    },
    goBack() {
      this.$router.push('/music');
    }
  }
};
</script>

<style scoped>
/* 原有样式保持不变 */
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

/* 新增：评论相关样式 */
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
</style>