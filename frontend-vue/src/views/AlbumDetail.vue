<template>
  <div class="layout-container">
    <!-- 全屏独立模糊封面背景层 - 保留 -->
    <div class="bg-layer" :style="bgStyle"></div>

    <aside class="sidebar">
      <!-- ✅ 修改1：返回按钮 主色加深1级底色 + hover加深再加深 -->
      <button @click="goBack" class="back-btn" :style="{backgroundColor: albumMainColorDark}">← 返回专辑列表</button>
      <div class="sidebar-menu">
        <!-- ✅ 修改2：选中菜单 文字色 = 封面主色加深再加深 -->
        <div class="menu-item" :class="{active: activeTab === 'base'}" :style="activeTab==='base'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'base'">基础信息</div>
        <div class="menu-item" :class="{active: activeTab === 'tracks'}" :style="activeTab==='tracks'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'tracks'">曲目列表</div>
        <div class="menu-item" :class="{active: activeTab === 'review'}" :style="activeTab==='review'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'review'">听后感</div>
        <div class="menu-item" :class="{active: activeTab === 'comments'}" :style="activeTab==='comments'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'comments'">平台评论</div>
      </div>
    </aside>

    <main class="main-content">
      <!-- 基础信息组件 - 传递主色参数 albumMainColor + albumMainColorDark -->
      <AlbumBaseInfo
        ref="albumBaseInfo"
        v-if="activeTab === 'base'"
        :album="album"
        :albumPoolId="albumPoolId || 0"
        :main-color="albumMainColor"
        :main-color-dark="albumMainColorDark"
        @save-tags="saveMyTags"
        @save-intro="saveAlbumIntro"
      />

      <!-- 曲目列表组件 -->
      <AlbumTrackList
        v-if="activeTab === 'tracks'"
        :album="album"
      />

      <!-- 听后感组件 - 传递主色参数 -->
      <AlbumReviewEditor
        v-if="activeTab === 'review'"
        :album="album"
        :main-color="albumMainColor"
        :main-color-dark="albumMainColorDark"
        @add-review="addSingleReview"
        @delete-single="deleteSingleReview"
        @delete-all="deleteAllReview"
      />

      <!-- 评论区组件 传参 -->
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
        :main-color="albumMainColor"
        :main-color-dark="albumMainColorDark"
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
      newCommentContent: '',
      publicComments: [],
      currentUserId: localStorage.getItem('user_id') || '',
      isAdmin: localStorage.getItem('is_admin') === '1',
      albumPoolId: '',
      hasComment: false,
      existingCommentId: null,
      sortType: 'time',
      blockedCommentIds: [],
      myComment: null,
      otherComments: [],
      bgStyle: {},
      albumMainColor: '#42b983',
      albumMainColorDark: '#2f9465', // 封面主色 加深1级
      albumMainColorDarkDouble: '#257d51', // ✅ 新增：封面主色 加深再加深（核心用色）
      activeMenuBg: 'rgba(255,255,255,0.2)'
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
        this.setFullPageBg(newVal.cover_img);
        if(newVal.cover_img) this.extractAlbumMainColor(newVal.cover_img);
      }
    },
    albumPoolId(newVal) {
      if (newVal && this.activeTab === 'base') {
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
    setFullPageBg(coverImg) {
      if (coverImg) {
        this.bgStyle = {
          backgroundImage: `url(${coverImg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }
      } else {
        this.bgStyle = { backgroundColor: '#f9f9f9' };
      }
    },
    extractAlbumMainColor(imgUrl) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 10;
        canvas.height = 10;
        ctx.drawImage(img, 0, 0, 10, 10);
        const data = ctx.getImageData(0,0,10,10).data;
        let r=0,g=0,b=0,c=0;
        for(let i=0;i<data.length;i+=4){r+=data[i];g+=data[i+1];b+=data[i+2];c++}
        r=Math.floor(r/c);g=Math.floor(g/c);b=Math.floor(b/c);
        const hex = `#${((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1)}`;
        this.albumMainColor = hex;
        this.albumMainColorDark = this.darkenColor(hex, 0.2); // 加深1级 (按钮底色/标签背景)
        this.albumMainColorDarkDouble = this.darkenColor(hex, 0.35); // ✅ 加深再加深 (选中菜单文字/按钮hover)
        this.activeMenuBg = `rgba(${r},${g},${b},0.2)`;
      };
      img.onerror = () => {
        this.albumMainColor = '#42b983';
        this.albumMainColorDark = '#2f9465';
        this.albumMainColorDarkDouble = '#257d51';
      };
      img.src = imgUrl;
    },
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1,3),16)*(1-amount);
      const g = parseInt(hex.slice(3,5),16)*(1-amount);
      const b = parseInt(hex.slice(5,7),16)*(1-amount);
      return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`;
    },
    // ============ 以下所有方法 完全未动 原样保留 ============
    saveAlbumIntro(introContent) {
      this.$axios({
        url: `/api/album/update/intro/${this.album.id}`,
        method: 'PUT',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: { album_intro: introContent.trim() }
      }).then(res => {
        if (res.data.code === 200) {
          alert('专辑简介保存成功！');
          this.album.album_intro = introContent.trim();
          if (this.isAdmin && this.albumPoolId) {
            this.syncAlbumIntroToPool(introContent.trim());
          }
        } else {
          alert('保存失败：' + res.data.msg);
        }
      }).catch(err => {
        console.error('保存专辑简介失败：', err);
        alert('保存专辑简介失败！' + err.message);
      });
    },
    syncAlbumIntroToPool(introContent) {
      this.$axios({
        url: `/api/album/pool/update/${this.albumPoolId}`,
        method: 'PUT',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: { album_intro: introContent }
      }).then(res => {
        if (res.data.code === 200) {
          console.log('✅ 公共专辑池简介同步成功');
        } else {
          console.warn('⚠️ 公共专辑池简介同步失败：', res.data.msg);
        }
      }).catch(err => {
        console.error('❌ 同步公共专辑简介失败：', err);
      });
    },
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
    changeSortType(type) {
      this.sortType = type;
    },
    blockComment(commentId) {
      if (!this.blockedCommentIds.includes(commentId.toString())) {
        this.blockedCommentIds.push(commentId.toString());
        localStorage.setItem(`blocked_comments_${this.albumPoolId}`, JSON.stringify(this.blockedCommentIds));
        alert('已屏蔽这条评论！');
      }
    },
    unblockAllComments() {
      this.blockedCommentIds = [];
      localStorage.removeItem(`blocked_comments_${this.albumPoolId}`);
    },
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
            my_score: this.album.my_score || 0.0,
            album_intro: this.album.album_intro || ''
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
    saveMyTags(tags) {
      this.$axios({
        url: `/api/album/update/tags/${this.album.id}`,
        method: 'PUT',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: {tags}
      }).then(res => {
        if (res.data.code === 200) {
          alert('我的分类标签保存成功！');
          this.album.tags = [...tags];
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
        data: {feeling_id: feelingId}
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
    goBack() {
      this.$router.push('/music');
    },
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
  position: relative;
  z-index: 1;
}

.bg-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  filter: blur(25px) brightness(1.2);
  -webkit-filter: blur(25px) brightness(1.2);
}

.sidebar {
  width: 200px;
  background: rgba(245, 245, 245, 0.3);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  padding: 20px;
  border-right: 1px solid rgba(255, 255, 255, 0.5);
  z-index: 2;
}

.back-btn {
  width: 100%;
  padding: 8px 0;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 30px;
  font-size: 14px;
  transition: all 0.2s;
}

/* ✅ 修改3：返回按钮hover 底色 = 封面主色加深再加深 */
.back-btn:hover {
  opacity: 0.95;
  transform: scale(1.02);
  background-color: v-bind(albumMainColorDarkDouble) !important;
}

.menu-item {
  padding: 10px 0;
  cursor: pointer;
  color: #555;
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
  font-size: 14px;
  transition: all 0.2s;
  border-radius: 4px;
  padding-left: 8px;
}

/* ✅ 修改4：菜单hover 文字色 = 封面主色加深再加深，保留通透背景 */
.menu-item:hover {
  color: v-bind(albumMainColorDarkDouble) !important;
  background: rgba(255, 255, 255, 0.2);
}

.main-content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 2;
}

h1 {
  font-size: 24px;
  margin-bottom: 20px;
  color: #222;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
}

h2 {
	font-size: 20px;
	margin-bottom: 18px;
	color: #333;
	text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
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