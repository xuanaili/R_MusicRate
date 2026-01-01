<template>
  <div class="layout-container">
    <!-- 全屏独立模糊封面背景层 - 保留 -->
    <div class="bg-layer" :style="bgStyle"></div>

    <!-- 左侧侧边栏 原样保留 -->
    <aside class="sidebar">
      <button @click="goBack" class="back-btn" :style="{backgroundColor: albumMainColorDark}">← 返回专辑列表</button>
      <div class="sidebar-menu">
        <div class="menu-item" :class="{active: activeTab === 'base'}" :style="activeTab==='base'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'base'">基础信息</div>
        <div class="menu-item" :class="{active: activeTab === 'tracks'}" :style="activeTab==='tracks'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'tracks'">曲目列表</div>
        <div class="menu-item" :class="{active: activeTab === 'review'}" :style="activeTab==='review'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'review'">听后感</div>
        <div class="menu-item" :class="{active: activeTab === 'comments'}" :style="activeTab==='comments'?{color:albumMainColorDarkDouble, fontWeight:'600', backgroundColor:activeMenuBg}:{}" @click="activeTab = 'comments'">平台评论</div>
      </div>
    </aside>

    <!-- 右侧主内容区域 -->
    <main class="main-content">
      <AlbumBaseInfo
        ref="albumBaseInfo"
        v-if="activeTab === 'base'"
        :album="album"
        :albumPoolId="albumPoolId || 0"
        :main-color="albumMainColor"
        :main-color-dark="albumMainColorDark"
        :albumTotalScore="albumTotalScore"
        @save-tags="saveMyTags"
        @save-intro="saveAlbumIntro"
      />

      <AlbumTrackList
        ref="albumTrackListRef"
        v-if="activeTab === 'tracks'"
        :album="album"
        :tracks="album.tracks || ['未知曲目']"
        :tracks-time="album.tracks_time || []"
        :favourite_tracks="album.favourite_tracks"
        :favourite_tracks_time="album.favourite_tracks_time"
        @update-album-data="updateAlbumData"
        @track-jump="handleTrackJump"

        :main-color="albumMainColor"
        :main-color-dark="albumMainColorDark"
          :main-color-dark-double="albumMainColorDarkDouble"
          :main-color-white="albumMainColorWhite"
          :main-color-white-double="albumMainColorWhiteDouble"

      />

      <AlbumReviewEditor
          v-if="activeTab === 'review'"
          :album="album"
          :main-color="albumMainColor"
          :main-color-dark="albumMainColorDark"
          :main-color-dark-double="albumMainColorDarkDouble"
          @add-review="addSingleReview"
          @delete-single="deleteSingleReview"
          @delete-all="deleteAllReview"
      />

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
          :main-color-dark-double="albumMainColorDarkDouble"
          :main-color-white="albumMainColorWhite"
          :main-color-white-double="albumMainColorWhiteDouble"

          @sort-change="changeSortType"
          @block-comment="blockComment"
          @unblock-all="unblockAllComments"
          @submit-comment="submitPublicComment"
          @like-comment="likePublicComment"
          @delete-comment="deletePublicComment"
          @update-comment-content="(val) => newCommentContent = val"
      />
    </main>

    <!-- ✅ 核心修改：播放列表组件传参完整，双向绑定+防抖保存 -->
    <PlayerPlaylist
        :visible="showPlaylistSidebar"
        :main-color-dark="albumMainColorDark"
        :main-color-dark-double="albumMainColorDarkDouble"
        :active-menu-bg="activeMenuBg"
        :current-user-id="currentUserId"
        :albumList="albumList"
        :current-track-index="currentTrackIndex"
        :play-mode="playMode"
        :playlistTabs="playlistTabs"
        :activeTabIndex="activeTabIndex"
        :currentAlbumId="currentAlbumId"
        :currentPlaylistId="currentPlaylistId"
        @play-track="handlePlayTrack"
        @close-sidebar="handleClosePlaylistSidebar"
        @update:currentTrackIndex="val => currentTrackIndex = val"
        @update:playMode="val => playMode = val"
        @update:playlistTabs="val => playlistTabs = val"
        @update:activeTabIndex="val => activeTabIndex = val"
        @trigger-upload-duration="pauseListeningTimer"
    />

    <!-- ✅ 底部播放器区域 核心重构：精准坐标对齐+透明背景 -->
    <div class="full-player-wrapper">
      <div class="album-rotate-box" @click="togglePlayPause" v-if="audioSrc && album.cover_img">
        <div class="album-rotate-circle" :class="{playing: isPlaying}">
          <img :src="album.cover_img" alt="专辑封面" class="album-rotate-img"/>
        </div>
      </div>
      <div class="album-rotate-box no-cover" v-else>
        <div class="album-rotate-circle">
          <div class="no-resource-text">暂无整轨音频资源</div>
        </div>
      </div>

      <div class="player-right-box">
        <div class="music-player-core">
          <input
              type="range"
              class="progress-bar"
              :value="currentProgress"
              min="0"
              max="100"
              @input="handleProgressChange"
          />
          <div class="time-text">
            {{ formatTime(currentTime) }} / {{ durationFormat }}
          </div>

          <div class="volume-wrapper" @mouseenter="showVolume = true" @mouseleave="showVolume = false">
            <span class="volume-icon">🔊</span>
            <div class="volume-dropdown" v-show="showVolume">
              <input
                  type="range"
                  class="volume-bar"
                  v-model="volume"
                  min="0"
                  max="1"
                  step="0.05"
              />
            </div>
          </div>

          <div class="menu-icon-wrapper" @mouseenter="showMenu=true" @mouseleave="showMenu=false">
            <div class="menu-icon">☰</div>
            <div class="dropdown-menu" v-show="showMenu">
              <button class="menu-btn playlist-btn" @click="showPlaylistSidebar = true">
                播放列表
              </button>
              <button class="menu-btn upload-btn" @click="showUploadSidebar = true" v-if="isAdmin">
                {{ audioSrc ? '更新音频' : '上传音频' }}
              </button>
              <button class="menu-btn delete-btn" @click="handleDeleteAudio" v-if="isAdmin && audioSrc">删除音频
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传/更新音频弹窗 原样保留 -->
    <div class="upload-sidebar" v-show="showUploadSidebar">
      <div class="sidebar-header">
        <h4>{{ audioSrc ? '更新整轨MP3文件' : '上传整轨MP3文件' }}</h4>
        <button class="close-btn" @click="showUploadSidebar = false">×</button>
      </div>
      <div
          class="upload-area"
          @dragover.prevent
          @drop.prevent="handleDrop"
      >
        <input
            type="file"
            ref="fileInput"
            accept=".mp3"
            class="file-input"
            @change="handleFileChange"
        />
        <div class="upload-tips">
          <p>📂 点击上传 或 拖拽MP3文件到此处</p>
          <p class="tip-text">仅支持 .mp3 格式音频文件</p>
        </div>
      </div>
      <div v-if="fileName" class="file-name">{{ fileName }}</div>
      <div class="upload-status" :class="{success: statusClass === 'success', error: statusClass === 'error'}">
        {{ statusText }}
      </div>
    </div>
    <div class="mask" v-show="showUploadSidebar" @click="showUploadSidebar = false"></div>

    <!-- ✅✅✅ 修复核心报错：audio标签补全闭合标签 解决编译失败 -->
    <audio ref="audioRef" :src="audioSrc" @timeupdate="handleTimeUpdate" @ended="handleEnded" :volume="volume"></audio>
  </div>
</template>

<script>
import AlbumBaseInfo from '@/components/albumDetail/AlbumBaseInfo'
import AlbumTrackList from '@/components/albumDetail/AlbumTrackList'
import AlbumReviewEditor from '@/components/albumDetail/AlbumReviewEditor'
import AlbumCommentSection from '@/components/albumDetail/AlbumCommentSection'
import PlayerPlaylist from '@/components/sidebar/PlayerPlaylist'
// ✅ 核心新增：引入评分计算工具函数
import {calculateAlbumTotalScore} from '@/utils/scoreCalc.js'

export default {
  name: 'AlbumDetail',
  components: {
    AlbumBaseInfo,
    AlbumTrackList,
    AlbumReviewEditor,
    AlbumCommentSection,
    PlayerPlaylist
  },
  data() {
    return {
      // ✅✅✅ 核心修复1：完整初始化album对象，补全所有必填字段，杜绝undefined
      album: {
        id: 0,
        album_name: '',
        singer: '',
        release_year: '',
        duration_type: 'LP',
        cover_img: '',
        tracks: [],
        tracks_time: [],
        full_tracks: [],
        review: {},
        my_score: [], // ✅ 修正：评分字段默认是数组，不是0.0
        track_count: 0,
        source_pool_id: 0,
        sync_pool_update: 1,
        is_customized: 0,
        album_intro: '',
        tags: [],
        main_type: [],

      },
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
      albumMainColorDark: '#2f9465',
      albumMainColorDarkDouble: '#257d51',
      activeMenuBg: 'rgba(255,255,255,0.2)',
      // 播放器相关数据
      showUploadSidebar: false,
      audioSrc: '',
      fileName: '',
      volume: 0.7,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      durationFormat: '0:00',
      currentProgress: 0,
      statusText: '',
      statusClass: '',
      showVolume: false,
      oldMp3Url: '',
      showMenu: false,
      // ✅✅✅ 播放列表核心数据【完整初始化，对接后端接口】
      showPlaylistSidebar: false,
      playlistTabs: [{name: '默认歌单', tracks: []}],
      activeTabIndex: 0,
      currentTrackIndex: -1,
      playMode: 'order',
      currentAlbumId: 0,
      currentPlaylistId: 0,
      albumList: [],
      saveTimer: null,
      // ✅✅✅ 核心修复2：新增加载状态锁，控制所有异步操作时序
      albumLoading: true,
      currentPlaySourcePoolId: 0,  // 专门存 album_pool 的id=17
      currentPlayRealAlbumId: 0,   // 专门存 用户专辑表的id=27

    };
  },
  computed: {
    filteredComments() {
      return this.publicComments.filter(comment => !this.blockedCommentIds.includes(comment.id.toString()));
    },
    currentPlaylist() {
      return this.playlistTabs[this.activeTabIndex]?.tracks || []
    },
    // ✅ ✅ ✅ 核心新增：计算属性 - 自动计算专辑综合评分，响应式更新
    albumTotalScore() {
      let scoreList = []
      // 兼容两种情况：1.my_score是数组 2.my_score是JSON字符串（后端返回的格式）
      if (this.album.my_score) {
        if (typeof this.album.my_score === 'string') {
          try {
            scoreList = JSON.parse(this.album.my_score)
          } catch (err) {
            scoreList = []
          }
        } else if (Array.isArray(this.album.my_score)) {
          scoreList = this.album.my_score
        }
      }
      // 调用工具函数计算最终评分
      return calculateAlbumTotalScore(scoreList)
    }
  },
  watch: {
    volume() {
      const audio = this.$refs.audioRef;
      if (audio) audio.volume = this.volume;
    },
    sortType() {
      this.processComments();
    },
    filteredComments() {
      this.processComments();
    },
    album: {
      deep: true,
      handler(newVal) {
        if (newVal) {
          this.album.tracks = newVal.tracks && newVal.tracks.length > 0 ? newVal.tracks : ["未知曲目"];
          this.album.tracks_time = Array.isArray(newVal.tracks_time) ? newVal.tracks_time : [];
          this.album.full_tracks = Array.isArray(newVal.full_tracks) ? newVal.full_tracks : [];

          if (newVal.review && newVal.review.personal_feeling && !newVal.review.feelings) {
            newVal.review.feelings = [{
              id: 'old_data',
              content: newVal.review.personal_feeling,
              create_time: newVal.review.update_time || '未知时间'
            }];
          }
          this.album.review = newVal.review || {};

          this.setFullPageBg(newVal.cover_img);
          if (newVal.cover_img) this.extractAlbumMainColor(newVal.cover_img);
        }
      }
    },
    albumPoolId() {
      if (this.albumPoolId && this.activeTab === 'base') {
        this.$refs.albumBaseInfo?.getAllUsersTagStatistics(this.albumPoolId);
      }
    },
// ✅✅✅ 修复核心：路由监听逻辑【完美版】- 跳转后自动刷新数据+自动播放音频，无需手动刷新
    $route: {
      deep: true,
      immediate: true,
      handler(to) {
        if (to.path.includes('/album/detail') && (to.params.id || to.query.id)) {
          const albumId = Number(to.params.id || to.query.id);
          if (albumId && albumId !== this.album.id) {
            this.resetAlbumPageData();
            this.getAlbumDetail(albumId).then(() => {
              this.getAlbumPoolRealId();
              this.checkUserComment();
              this.getPublicComments();
              setTimeout(() => {
                if (this.album.source_pool_id) {
                  this.getAlbumAudioInfo().then(() => {
                    // ✅ 改为直接调用播放方法，而不是autoPlay，跳转后必播放
                    this.autoPlayCurrentAlbumAudio();
                  }).catch(() => console.log('音频加载失败'));
                }
              }, 100); // 延时100ms，确保音频资源加载完成
            });
          }
        }
      },
    },
  },
  async created() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login');
      return;
    }
    this.currentUserId = localStorage.getItem('user_id');
    this.isAdmin = localStorage.getItem('is_admin') === '1';

    const albumId = this.$route.params.id || this.$route.query.id;
    if (!albumId) {
      alert('未找到专辑ID！');
      this.$router.push('/albumDetail');
      return;
    }

    await this.getUserPlaylistData();
    await this.getAlbumDetail(Number(albumId));
    await this.getAlbumPoolRealId();
    const savedBlockedIds = localStorage.getItem(`blocked_comments_${this.albumPoolId}`);
    if (savedBlockedIds) {
      this.blockedCommentIds = JSON.parse(savedBlockedIds);
    }
    this.checkUserComment();
    this.getPublicComments();
    if (this.album.source_pool_id) await this.getAlbumAudioInfo().catch(() => console.log('音频加载失败'));
    this.currentAlbumId = -1; // ✅ 初始化默认值：无播放，下标为-1
    this.currentTrackIndex = -1;
    await this.getUserHasAudioAlbums();
    this.autoPlayCurrentAlbumAudio();
  },
  methods: {
    // ✅✅✅ 加载用户播放列表数据【对接后端GET接口】
    async getUserPlaylistData() {
      try {
        const res = await this.$axios.get('/api/playlist/get-user-playlist-data', {
          headers: {Authorization: localStorage.getItem('token') || ''}
        })
        if (res.data.code === 200 && res.data.data) {
          const data = res.data.data;
          this.playlistTabs = data.playlist || [{name: '默认歌单', tracks: []}];
          this.activeTabIndex = data.current_playlist_id || 0;
          this.currentPlaylistId = data.current_playlist_id || 0;
// ✅ 后端返回的 current_album_id 就是「歌单下标」，直接赋值
          this.currentAlbumId = data.current_album_id || -1;
// ✅ 播放索引 和 歌单下标 必须完全一致，同步赋值
          this.currentTrackIndex = this.currentAlbumId;
          this.playMode = data.play_mode || 'order';
          console.log('✅ 从后端加载播放下标：current_album_id = ', this.currentAlbumId);
        }
      } catch (_err) {
        console.error('❌ 获取用户播放列表失败');
        this.playlistTabs = [{name: '默认歌单', tracks: []}];
      }
    },

    async saveUserPlaylistData() {
      if (this.playlistTabs.length === 0 || !this.playlistTabs[0].tracks) return;
      if (this.saveTimer) clearTimeout(this.saveTimer);
      this.saveTimer = setTimeout(async () => {
        try {
          await this.$axios.post('/api/playlist/save-user-playlist-data', {
            playlist: this.playlistTabs,
            activeTabIndex: this.activeTabIndex,
            current_playlist_id: this.activeTabIndex,
            current_album_id: this.currentAlbumId,
            play_mode: this.playMode
          }, {
            headers: {Authorization: localStorage.getItem('token') || ''}
          })
          console.log('✅ 上传给后端的current_album_id(歌单下标)：', this.currentAlbumId);
        } catch (_err) {
          console.error('❌ 保存播放列表失败');
        } finally {
          this.saveTimer = null;
        }
      }, 300);
    },

    handleClosePlaylistSidebar() {
      this.showPlaylistSidebar = false;
      this.saveUserPlaylistData();
    },

// ✅✅✅ 自动播放当前专辑音频 - 兼容浏览器策略+静默失败+优化用户体验
    autoPlayCurrentAlbumAudio() {
      const audio = this.$refs.audioRef;
      if (this.audioSrc && audio) {
        // 先重置播放进度，避免上次播放残留进度
        this.currentTime = 0;
        this.currentProgress = 0;
        audio.currentTime = 0;
        // 执行自动播放
        audio.play().then(() => {
          this.isPlaying = true;
          this.startListeningTimer(); // ✅✅✅ 新增：自动播放成功，触发开始计时API
          console.log('✅ 专辑音频自动播放成功');
        }).catch((err) => {
          console.log('ℹ️ 浏览器策略限制自动播放，需要用户手动交互解锁：', err.message);
          this.isPlaying = false;
        });
      }
      this.saveUserPlaylistData();
    },

    async handlePlayTrack(index, needJumpDetail = false) {
      const currentList = this.currentPlaylist;
      if (currentList.length === 0 || index < 0 || index >= currentList.length) {
        this.$message?.warning('播放索引无效，请重试');
        return;
      }
      const playAlbum = currentList[index];
      if (!playAlbum || !playAlbum.source_pool_id) {
        this.$message?.error('该专辑暂无音频资源，无法播放');
        return;
      }

      // ========== 1. 先暂停上一首，上传时长 ==========
      await this.pauseListeningTimer();

      const audio = this.$refs.audioRef;
      if (audio && this.isPlaying) {
        audio.pause();
        this.isPlaying = false;
      }
      try {
        const res = await this.$axios.get(`/api/album/pool/audio/info/${playAlbum.source_pool_id}`, {
          headers: {Authorization: localStorage.getItem('token') || ''}
        })
        if (res.data.code === 200 && res.data.data.mp3_url) {
          this.audioSrc = res.data.data.mp3_url
          this.fileName = res.data.data.mp3_name
          this.duration = res.data.data.mp3_duration
          this.durationFormat = res.data.data.duration_format

          // ========== ✅✅✅ 核心强制赋值【重中之重】- 写死这三行，下标回归0 ==========
          this.currentTrackIndex = index;    // 歌单播放下标（高亮用）
          this.currentAlbumId = index;       // ✔️ 这个变量 100% 等于下标，再也不会是17/27
          this.currentPlaylistId = this.activeTabIndex;
          // ======================================================================

          // ========== ✅✅✅ 新增：缓存当前播放项的【两个真实ID】，解决上传时长ID=0的问题 ==========
          this.currentPlaySourcePoolId = playAlbum.source_pool_id; // 缓存 album_pool.id=17
          this.currentPlayRealAlbumId = playAlbum.id; // 缓存 用户专辑表.id=27
          // ======================================================================

          this.currentTime = 0;
          this.currentProgress = 0;
          if (needJumpDetail) {
            const albumIdRes = await this.$axios.get('/api/album/get-id-by-source', {
              params: {source_pool_id: playAlbum.source_pool_id},
              headers: {Authorization: localStorage.getItem('token') || ''}
            });
            if (albumIdRes.data.code === 200 && albumIdRes.data.data?.album_id) {
              const realAlbumId = albumIdRes.data.data.album_id;
              const currentRouteAlbumId = Number(this.$route.params.id || this.$route.query.id);
              if (realAlbumId !== currentRouteAlbumId) {
                this.$router.replace({
                  path: `/album/detail/${realAlbumId}`,
                  query: {id: realAlbumId}
                });
              }
            }
          }
          audio.currentTime = 0;
          audio.play().then(() => {
            this.isPlaying = true;
            this.startListeningTimer(); // 播放新歌，开始计时
          }).catch(() => {
            this.isPlaying = false;
            this.$message?.info('📢 点击底部专辑封面即可解锁播放～');
            audio.load();
          });
          // ✅ 打印正确日志，确认下标是0
          console.log(`✅ 播放成功：歌单下标 = current_album_id = ${index} | source_pool_id=${playAlbum.source_pool_id} | 真实专辑ID=${playAlbum.id}`);
        } else {
          this.$message.error('该专辑暂无音频资源，无法播放');
        }
      } catch (err) {
        console.error('❌ 获取播放音频失败：', err);
        this.$message.error('播放失败，该专辑暂无音频资源');
      }
      this.saveUserPlaylistData();
    },

// 曲目跳转事件 - 异常捕获
    handleTrackJump(targetSec) {
      if (!this.audioSrc) {
        alert('暂无整轨音频资源，无法跳转播放！');
        return;
      }
      const audio = this.$refs.audioRef;
      audio.currentTime = targetSec;
      this.currentTime = targetSec;
      this.currentProgress = this.duration ? (targetSec / this.duration) * 100 : 0;
      audio.play().then(() => {
        this.isPlaying = true;
        this.startListeningTimer(); // ✅✅✅ 新增：曲目跳转播放，触发开始计时API
      }).catch(() => {
        alert('📢 请点击底部专辑封面解锁播放权限后再试～');
      });
    },

    // 时间格式化
    formatTime(seconds) {
      if (!seconds) return '0:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      return `${min}:${sec.toString().padStart(2, '0')}`;
    },

    // 获取专辑音频信息
// 获取专辑音频信息 - ✅ 核心优化：增加return Promise，确保自动播放时机准确
    async getAlbumAudioInfo() {
      try {
        const res = await this.$axios.get(`/api/album/pool/audio/info/${this.album.source_pool_id}`)
        if (res.data.code === 200 && res.data.data.mp3_url) {
          this.audioSrc = res.data.data.mp3_url
          this.fileName = res.data.data.mp3_name
          this.duration = res.data.data.mp3_duration
          this.durationFormat = res.data.data.duration_format
          this.oldMp3Url = res.data.data.mp3_url
          console.log('⚠️ 跳过真实专辑ID赋值，保留歌单下标：', this.currentAlbumId);
        }
        // ✅ 新增：无论是否获取到音频，都返回promise，避免报错
        return Promise.resolve();
      } catch (err) {
        this.oldMp3Url = ''
        return Promise.reject(err);
      }
    },
    // 获取用户有音频的专辑列表
    async getUserHasAudioAlbums() {
      try {
        const res = await this.$axios.get('/api/playlist/get-user-audio-albums', {
          headers: {Authorization: localStorage.getItem('token') || ''}
        })
        if (res.data.code === 200) {
          this.albumList = res.data.data.map(item => ({
            ...item,
            my_score: item.score
          }))
        }
      } catch (err) {
        console.error('❌ 获取有音频专辑列表失败')
        this.albumList = []
        this.$message.error('加载可播放专辑失败，请重试')
      }
    },

    // 文件选择事件
    handleFileChange(e) {
      const file = e.target.files[0];
      if (file) {
        this.handleFile(file);
        this.$refs.fileInput.value = ''
      }
    },

    handleDrop(e) {
      const file = e.target.files[0] || e.dataTransfer.files[0];
      if (file) {
        this.handleFile(file);
      }
    },

    async handleFile(file) {
      if (file.type !== 'audio/mpeg' && !file.name.toLowerCase().endsWith('.mp3')) {
        this.statusText = '❌ 仅支持上传MP3格式！';
        this.statusClass = 'error';
        return;
      }
      if (!this.album.source_pool_id) {
        this.statusText = '❌ 公共专辑ID不存在，无法上传！';
        this.statusClass = 'error';
        return;
      }
      this.statusText = this.audioSrc ? '⏳ 更新中，请稍候...' : '⏳ 上传中，请稍候...';
      this.statusClass = '';
      try {
        const formData = new FormData()
        formData.append('source_pool_id', this.album.source_pool_id)
        formData.append('mp3_file', file)
        formData.append('old_mp3_url', this.oldMp3Url || '')
        const res = await this.$axios.post('/api/album/pool/audio/upload', formData)
        if (res.data.code === 200) {
          this.audioSrc = res.data.data.mp3_url
          this.fileName = res.data.data.mp3_name
          this.duration = res.data.data.mp3_duration
          this.durationFormat = res.data.data.duration_format
          this.oldMp3Url = res.data.data.mp3_url
          this.statusText = this.audioSrc ? '✅ 更新成功' : '✅ 上传成功';
          this.statusClass = 'success';
          setTimeout(() => {
            this.showUploadSidebar = false
            this.statusText = ''
            this.statusClass = ''
          }, 2000)
        } else {
          this.statusText = `❌ ${res.data.msg}`;
          this.statusClass = 'error';
        }
      } catch (err) {
        console.error('音频操作失败：')
        this.statusText = '❌ 操作失败，请重试！';
        this.statusClass = 'error';
      }
      this.isPlaying = false;
      this.currentTime = 0;
      this.currentProgress = 0;
    },

    async handleDeleteAudio() {
      const confirmDel = confirm("确定要删除该音频资源吗？删除后无法恢复！");
      if (!confirmDel) return;
      try {
        const res = await this.$axios.post('/api/album/pool/audio/delete', {
          source_pool_id: this.album.source_pool_id,
          mp3_url: this.oldMp3Url
        })
        if (res.data.code === 200) {
          this.statusText = '✅ 音频删除成功！';
          this.statusClass = 'success';
          this.clearAudioData();
          setTimeout(() => {
            this.statusText = '';
            this.statusClass = ''
          }, 2000);
        } else {
          this.statusText = `❌ ${res.data.msg}`;
          this.statusClass = 'error';
        }
      } catch (err) {
        this.statusText = '❌ 删除失败，请重试！';
        this.statusClass = 'error';
      }
    },

    clearAudioData() {
      this.audioSrc = '';
      this.fileName = '';
      this.duration = 0;
      this.durationFormat = '0:00';
      this.oldMp3Url = '';
      this.isPlaying = false;
      this.currentTime = 0;
      this.currentProgress = 0;
    },


// ✅✅✅ 终极修复版 - 播放暂停切换 【彻底解决暂停进度条归零】
    togglePlayPause() {
      const audio = this.$refs.audioRef;
      if (!audio || !this.audioSrc) {
        this.$message?.info('暂无音频资源，无法播放');
        return;
      }
      if (this.isPlaying) {
        // ----- 暂停逻辑：强制同步真实进度 + 跳过Vue异步更新，立即生效 -----
        audio.pause();
        // 1. 读取原生audio的真实进度（绝对准确，不会错）
        const realCurrentTime = audio.currentTime || 0;
        const realProgress = this.duration && this.duration > 0 ? (realCurrentTime / this.duration) * 100 : 0;
        // 2. 同步赋值给页面变量，确保是数字且非负
        this.currentTime = Math.max(0, realCurrentTime);
        this.currentProgress = Math.max(0, realProgress);
        // 3. ✅ 关键核心：强制Vue立即更新DOM，跳过异步队列，解决视觉归零
        this.$forceUpdate();
        this.isPlaying = false;
        this.pauseListeningTimer(); // 只传时长，不碰进度
      } else {
        // 播放逻辑不变
        audio.play().then(() => {
          this.isPlaying = true;
          this.startListeningTimer();
        }).catch(() => {
          this.isPlaying = false;
          this.$message?.warning('📢 播放失败，请检查音频资源是否有效～');
        });
      }
    },

// ========== ✅✅✅ 新增：调用后端 开始播放计时API ========== ✅✅✅
    async startListeningTimer() {
      const token = localStorage.getItem('token') || '';
      if (!token || !this.album.id || !this.audioSrc) return;
      try {
        await this.$axios.post(
            `/api/album/listening/start/${this.album.id}`,
            {},
            {headers: {Authorization: token}}
        );
        console.log(`✅ 触发播放计时：专辑ID=${this.album.id}，开始累计时长`);
      } catch (err) {
        console.log(`ℹ️ 播放计时接口调用失败(不影响播放)：`, err.message);
      }
    },

// ✅✅✅ 终极修复版 - 暂停计时上传时长：只暂停音频+传时长，【绝对不重置】任何进度数据！！！
    async pauseListeningTimer() {
      const token = localStorage.getItem('token') || '';
      const audio = this.$refs.audioRef;
      // 满足条件才执行上传，不满足直接静默返回
      if (!token || !this.album.id || !this.audioSrc || !audio) return;

      try {
        await this.$axios.post(
            `/api/album/listening/pause/${this.album.id}`,
            {},
            {headers: {Authorization: token}}
        );
        console.log(`✅ [成功] 上传时长到数据库：专辑ID=${this.album.id}`);
      } catch (err) {
        console.log(`⚠️ [上传失败] 专辑ID=${this.album.id}：`, err.response?.data?.msg || err.message);
      } finally {
        // ✅ 只做2件事：暂停原生音频 + 修改播放状态，【无任何其他代码】
        audio.pause();
        this.isPlaying = false;
      }
    },
    handleTimeUpdate() {
      const audio = this.$refs.audioRef;
      if (!audio) return;
      this.currentTime = audio.currentTime;
      this.duration = audio.duration || this.duration;
      this.currentProgress = this.duration ? (this.currentTime / this.duration) * 100 : 0;
    },

    handleProgressChange(e) {
      const audio = this.$refs.audioRef;
      if (!audio) return;
      const progress = e.target.value;
      this.currentProgress = progress;
      this.currentTime = (progress / 100) * this.duration;
      audio.currentTime = this.currentTime;
    },

    async handleEnded() {
      this.isPlaying = false;
      this.currentProgress = 0;
      this.currentTime = 0;
      await this.pauseListeningTimer(); // ✅ 必须await，确保时长上传完成再切歌
      const audio = this.$refs.audioRef;
      if (!audio || !this.audioSrc || this.currentPlaylist.length === 0) return;


      console.log(this)
      // 单曲循环：本地直接重播，不走接口，效率最高
      if (this.playMode === 'single') {
        audio.currentTime = 0;
        audio.play().then(() => {
          this.isPlaying = true;
          this.startListeningTimer();
        }).catch(() => this.isPlaying = false);
        this.saveUserPlaylistData();
        return;
      }

      try {
        const res = await this.$axios.post(
            '/api/playlist/switch-next-album',
            {
              playlist: this.playlistTabs,
              current_playlist_id: this.currentPlaylistId,
              current_album_id: this.currentAlbumId,
              play_mode: this.playMode
            },
            {headers: {Authorization: localStorage.getItem('token') || ''}}
        );

        if (res.data.code === 200 && res.data.data && res.data.data.current_album_id !== undefined) {
          const {current_album_id: newTrackIndex, current_playlist_id: newTabIndex} = res.data.data;
          this.currentPlaylistId = newTabIndex;
          this.currentAlbumId = newTrackIndex; // ✅ 同步赋值新下标
          this.currentTrackIndex = newTrackIndex; // ✅ 同步赋值播放索引
          await this.handlePlayTrack(newTrackIndex, true);
          console.log('✅ 切歌后新下标：current_album_id = ', newTrackIndex);
        } else {
          this.$message?.warning(res.data.msg || '已播放到最后一首，暂无更多专辑');
          this.currentTrackIndex = -1;
          this.audioSrc = '';
        }
      } catch (err) {
        console.error('❌ 切歌接口调用失败：', err);
        this.$message?.error('切换下一曲失败，请重试');
      } finally {
        this.saveUserPlaylistData();
      }
    },

    updateAlbumData(updatedData) {
      this.album = {...this.album, ...updatedData};
    },

    setFullPageBg(coverImg) {
      if (coverImg) {
        this.bgStyle = {
          backgroundImage: `url(${coverImg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }
      } else {
        this.bgStyle = {backgroundColor: '#f9f9f9'};
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
        const data = ctx.getImageData(0, 0, 10, 10).data;
        let r = 0, g = 0, b = 0, c = 0;
        for (let i = 0; i < data.length; i += 4) {
          r += data[i];
          g += data[i + 1];
          b += data[i + 2];
          c++
        }
        r = Math.floor(r / c);
        g = Math.floor(g / c);
        b = Math.floor(b / c);
        const hex = `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
        this.albumMainColor = hex;
        this.albumMainColorDark = this.darkenColor(hex, 0.2);
        this.albumMainColorDarkDouble = this.darkenColor(hex, 0.35);
        this.albumMainColorWhite = this.darkenColor(hex, -0.2);
        this.albumMainColorWhiteDouble = this.darkenColor(hex, -0.35);

        this.activeMenuBg = `rgba(${r},${g},${b},0.2)`;
      };
      img.onerror = () => {
        this.albumMainColor = '#42b983';
        this.albumMainColorDark = '#2f9465';
        this.albumMainColorDarkDouble = '#257d51';
        this.albumMainColorWhite = '#2f9465';
        this.albumMainColorWhiteDouble = '#257d51';
      };
      img.src = imgUrl;
    },

// ✅ 修正版：支持加深/提亮，自动限制RGB值在0-255之间，杜绝非法色值
    darkenColor(hex, amount) {
      const r = Math.min(255, Math.max(0, parseInt(hex.slice(1, 3), 16) * (1 - amount)));
      const g = Math.min(255, Math.max(0, parseInt(hex.slice(3, 5), 16) * (1 - amount)));
      const b = Math.min(255, Math.max(0, parseInt(hex.slice(5, 7), 16) * (1 - amount)));
      // 补零+转16进制，避免出现 #f 这种不完整色值
      const toHex = (val) => Math.round(val).toString(16).padStart(2, '0');
      return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    },

    saveAlbumIntro(introContent) {
      this.$axios({
        url: `/api/album/update/intro/${this.album.id}`,
        method: 'PUT',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json'
        },
        data: {album_intro: introContent.trim()}
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
      }).catch(() => {
        console.error('保存专辑简介失败：');
        alert('保存专辑简介失败！');
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
        data: {album_intro: introContent}
      }).then(res => {
        if (res.data.code === 200) {
          console.log('✅ 公共专辑池简介同步成功');
        } else {
          console.warn('⚠️ 公共专辑池简介同步失败：', res.data.msg);
        }
      }).catch(() => {
        console.error('❌ 同步公共专辑简介失败：');
      });
    },

    processComments() {
      const myComment = this.filteredComments.find(comment => comment.user_id == this.currentUserId);
      const otherComments = this.filteredComments.filter(comment => comment.user_id != this.currentUserId);

  if (this.sortType === 'time') {
    // 最新时间：创建时间降序 ✔️ 原有逻辑不变
    otherComments.sort((a, b) => new Date(b.create_time) - new Date(a.create_time));
  } else if (this.sortType === 'like') {
    // 最多点赞：点赞数降序 ✔️ 原有逻辑不变
    otherComments.sort((a, b) => b.like_count - a.like_count);
  } else if (this.sortType === 'listen') {
    // ✅✅✅ 新增核心：最长听取 排序规则
    // 规则：听取时间 listening_duration 数值越大，越排在前面
    // 容错处理：兼容 null/undefined/NaN，默认赋值0，防止排序报错
    otherComments.sort((a, b) => (b.listening_duration || 0) - (a.listening_duration || 0));
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

    // ✅✅✅ 核心修复3：getAlbumPoolRealId 加【加载状态+字段非空三重校验】，根治核心报错
    async getAlbumPoolRealId() {
      // 第一重：加载中不执行
      if (this.albumLoading) {
        console.log('⏳ 专辑数据加载中，稍后获取公共专辑ID');
        return;
      }
      // 第二重：核心字段非空校验，杜绝空值请求
      const {album_name, singer} = this.album;
      if (!album_name || !album_name.trim() || !singer || !singer.trim()) {
        console.warn('⚠️ 专辑名称/歌手为空，跳过公共专辑创建');
        this.albumPoolId = '';
        return;
      }
      // 第三重：发行年份容错
      if (!this.album.release_year) this.album.release_year = 0;

      try {
        const res = await this.$axios({
          url: '/api/album_pool/get_id',
          method: 'GET',
          params: {
            album_name: album_name.trim(),
            singer: singer.trim()
          },
          headers: {
            'Authorization': localStorage.getItem('token') || ''
          }
        });

        if (res.data.code === 200) {
          this.albumPoolId = res.data.data.id;
        } else if (res.data.code === 404) {
          await this.createAlbumPool();
        }
      } catch (err) {
        console.error('获取专辑池ID失败：', err);
        this.albumPoolId = '';
      }
    },

    // ✅✅✅ 核心修复4：createAlbumPool 传参修正+字段补全，无undefined
    async createAlbumPool() {
      const {album_name, singer, release_year, cover_img, main_type, tags, my_score, album_intro} = this.album;
      try {
        const res = await this.$axios({
          url: '/api/album_pool/add',
          method: 'POST',
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          },
          data: {
            album_name: album_name.trim(),
            cover_img: cover_img || '',
            singer: singer.trim(),
            release_year: Number(release_year) || 0,
            main_type: Array.isArray(main_type) ? JSON.stringify(main_type) : main_type || '',
            tags: tags || [],
            my_score: Number(my_score) || 0.0,
            album_intro: album_intro || ''
          }
        });
        if (res.data.code === 200) {
          this.albumPoolId = res.data.data.id;
          this.album.source_pool_id = this.albumPoolId;
          alert('公共专辑创建成功！ID：' + this.albumPoolId);
        }
      } catch (err) {
        console.error('创建专辑池失败：', err);
        alert(`创建公共专辑失败：${err.message || '服务器异常'}`);
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

    // ✅✅✅ 核心修复5：getAlbumDetail 加加载状态锁，异步请求有开始/结束标记
    getAlbumDetail(albumId) {
      return new Promise((resolve, reject) => {
        this.albumLoading = true;
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
                if (this.album.source_pool_id) {
                  this.albumPoolId = this.album.source_pool_id;
                }
                this.saveUserPlaylistData();
                resolve();
              } else {
                alert(res.data.msg);
                this.$router.push('/albumDetail');
                reject(res.data.msg);
              }
            })
            .catch(() => {
              console.error('获取详情失败：');
              alert('获取专辑详情失败！');
              this.$router.push('/albumDetail');
              reject();
            })
            .finally(() => {
              this.albumLoading = false;
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
      }).catch(() => {
        console.error('保存标签失败：');
        alert('保存标签失败！');
      });
    },

    addSingleReview(content) {
      if (!content.trim()) {
        alert('听后感内容不能为空！');
        return;
      }
      const now = new Date();
      const createTime = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;


            let scoreList = []
      // 兼容两种情况：1.my_score是数组 2.my_score是JSON字符串（后端返回的格式）
      if (this.album.my_score) {
        if (typeof this.album.my_score === 'string') {
          try {
            scoreList = JSON.parse(this.album.my_score)
          } catch (err) {
            scoreList = []
          }
        } else if (Array.isArray(this.album.my_score)) {
          scoreList = this.album.my_score
        }
      }




      this.$axios({
        url: `/api/album/review/add/${this.album.id}`,
        method: 'POST',
        headers: {
          'Authorization': localStorage.getItem('token') || '',
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          content: content.trim(),
          create_time: createTime,
      listening_duration: Math.floor(this.album.listening_duration), // ✅ 核心修正：传【用户实际收听时长】，取整避免小数
      my_score: calculateAlbumTotalScore(scoreList),    // ✅ 补充修正：数组转JSON字符串，后端接收正常
        }
      })
          .then((res) => {
            if (res.data.code === 200) {
              alert('听后感添加成功！');
              this.getAlbumDetail(this.album.id);
              console.log(calculateAlbumTotalScore(scoreList))
              console.log(this.album)
            } else {
              alert(res.data.msg);
            }
          })
          .catch(() => {
            console.error('添加听后感失败：');
            alert('添加听后感失败！');
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
          .catch(() => {
            console.error('删除听后感失败：');
            alert('删除听后感失败！');
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
          .catch(() => {
            console.error('清空听后感失败：');
            alert('清空听后感失败！');
          });
    },

    // ✅✅✅ 核心修复6：完整重置方法，补全所有字段，无undefined
    resetAlbumPageData() {
      this.album = {
        id: 0,
        album_name: '',
        singer: '',
        release_year: '',
        cover_img: '',
        tracks: [],
        tracks_time: [],
        full_tracks: [],
        review: {},
        my_score: [], // ✅ 修正：评分字段默认是数组
        track_count: 0,
        source_pool_id: 0,
        sync_pool_update: 1,
        is_customized: 0,
        album_intro: '',
        tags: [],
        main_type: []
      };
      this.audioSrc = '';
      this.fileName = '';
      this.isPlaying = false;
      this.currentTime = 0;
      this.duration = 0;
      this.durationFormat = '0:00';
      this.currentProgress = 0;
      this.blockedCommentIds = [];
      this.publicComments = [];
      this.myComment = null;
      this.otherComments = [];
      this.hasComment = false;
      this.existingCommentId = null;
      this.albumPoolId = '';
      this.albumLoading = true;
    },

    goBack() {
      this.$router.push('/albumDetail');
    },

    getPublicComments() {
      if (!this.albumPoolId) return;
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
      }).catch(() => {
        console.error('获取公共评论失败：');
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
            content: content,
        listening_duration: this.album.listening_duration || 0
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
        alert(`发布失败：服务器异常`);
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
      }).catch(() => {
        console.error('点赞失败：');
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
          alert('删除评论失败：', res.data.msg);
        }
      }).catch(() => {
        console.error('删除公共评论失败：');
        alert('删除公共评论失败！');
      });
    }
  },
// 路由离开守卫，强制保存播放列表 ✅✅✅ 新增暂停计时
  beforeRouteLeave(to, from, next) {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveUserPlaylistData();
    this.pauseListeningTimer(); // ✅✅✅ 新增：离开页面，自动暂停计时，保存时长
    this.$refs.albumTrackListRef?.triggerSaveScore();
    next();
  },
  beforeUnmount() {
    if (this.audioSrc && this.audioSrc.includes('blob:')) {
      URL.revokeObjectURL(this.audioSrc);
    }
    this.pauseListeningTimer(); // ✅✅✅ 新增：组件销毁，暂停计时
  },
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
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
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

.back-btn:hover {
  opacity: 0.95;
  transform: scale(1.02);
  background-color: v-bind(albumMainColorDarkDouble) !important;
}

.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 5px;
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

.menu-item:hover {
  color: v-bind(albumMainColorDarkDouble) !important;
  background: rgba(255, 255, 255, 0.2);
}

.main-content {
  flex: 1;
  margin-left: 200px;
  padding: 30px;
  padding-bottom: 140px !important;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 2;
  min-height: 100vh;
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

.full-player-wrapper {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 10px;
  background: transparent;
  backdrop-filter: none;
  border-top: none;
  z-index: 99;
  display: block;
  padding: 0;
  margin: 0;
}

.album-rotate-box {
  width: 200px;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: absolute;
  left: 0;
  bottom: 0;
  transform: translateY(-10px);
  z-index: 10;
}

.album-rotate-circle {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  overflow: hidden;
  border: 4px solid v-bind(albumMainColorDark);
  box-shadow: 0 0 15px v-bind(albumMainColorDark);
  transition: all 0.3s ease;
  animation-fill-mode: forwards;
  animation: rotate 8s linear infinite;
  animation-play-state: paused;
}

.album-rotate-circle.playing {
  animation-play-state: running;
}

.album-rotate-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.no-cover .album-rotate-circle {
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-resource-text {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  padding: 0 10px;
}

.player-right-box {
  position: absolute;
  bottom: 15px;
  left: 0;
  width: 100%;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}

.music-player-core {
  display: flex;
  align-items: center;
  gap: 8px;
  width: calc(100% - 150px);
  height: 1px;
  position: absolute;
  left: 110px;
  bottom: 0px;
  padding: 0;
  margin: 0;
}

.progress-bar {
  flex: 1;
  height: 5px;
  cursor: pointer;
  accent-color: v-bind(albumMainColorDark);
  min-width: unset;
}

.time-text {
  font-size: 11px;
  color: #666;
  width: 70px;
  text-align: center;
  flex-shrink: 0;
}

.volume-wrapper {
  position: relative;
  cursor: pointer;
  font-size: 12px;
  flex-shrink: 0;
  margin-left: 5px;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
}

.volume-icon {
  display: block;
  color: #666;
  margin-top: 5px;
  transition: color 0.2s ease;
}

.volume-wrapper:hover .volume-icon {
  color: v-bind(albumMainColorDark);
}

.volume-dropdown {
  position: absolute;
  bottom: 18px;
  right: 0;
  background: #fff;
  padding: 6px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 100;
}

.volume-bar {
  width: 5px;
  height: 60px;
  writing-mode: vertical-lr;
  direction: rtl;
  accent-color: v-bind(albumMainColorDark);
  cursor: pointer;
}

.menu-icon-wrapper {
  cursor: pointer;
  position: relative;
  width: 20px;
  height: 20px;
  margin-left: 5px;
  z-index: 11;
}

.menu-icon {
  font-size: 16px;
  color: #666;
  line-height: 20px;
  text-align: center;
  transition: color 0.2s ease;
}

.menu-icon-wrapper:hover .menu-icon {
  color: v-bind(albumMainColorDark);
}

.dropdown-menu {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 3px 0;
  min-width: 80px;
  z-index: 999;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.menu-btn.playlist-btn {
  color: v-bind(albumMainColorDark);
}

.menu-btn.playlist-btn:hover {
  background: v-bind(activeMenuBg);
}

.menu-btn {
  border: none;
  background: transparent;
  padding: 3px 6px;
  font-size: 11px;
  text-align: center;
  width: 100%;
  cursor: pointer;
  transition: all 0.2s;
}

.menu-btn.upload-btn {
  color: v-bind(albumMainColorDark);
}

.menu-btn.upload-btn:hover {
  background: v-bind(activeMenuBg);
}

.menu-btn.delete-btn {
  color: #dc2626;
}

.menu-btn.delete-btn:hover {
  background: #fef2f2;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.upload-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 360px;
  height: 100vh;
  background: white;
  z-index: 999;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
  padding: 20px;
  box-sizing: border-box;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}

.close-btn:hover {
  color: #f00;
}

.upload-area {
  width: 100%;
  height: 180px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  background: #f9f9f9;
  margin-bottom: 20px;
  transition: all 0.2s ease;
}

.upload-area:hover {
  border-color: v-bind(albumMainColorDark);
  background: v-bind(activeMenuBg);
}

.file-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-tips {
  text-align: center;
  color: #666;
}

.tip-text {
  font-size: 12px;
  color: #999;
}

.file-name {
  font-size: 14px;
  color: #333;
  margin-bottom: 10px;
  word-break: break-all;
}

.upload-status {
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  text-align: center;
}

.upload-status.success {
  color: #15803d;
  background: #f0fdf4;
}

.upload-status.error {
  color: #dc2626;
  background: #fef2f2;
}

.mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 998;
}
</style>