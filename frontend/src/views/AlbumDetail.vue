<template>
  <div class="layout-container">
    <!-- ✅✅✅ 核心整合：把小球动画容器 放到父组件根节点最外层【全屏底层】 -->
    <div
      class="ball-animation-wrap"
      ref="ballWrap"
      @mousemove="handleMouseMove"
      @mouseleave="handleMouseLeave"
    ></div>

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
        @toggle-ball-play="handleToggleBallPlay"
          @toggle-meteor-play="handleToggleMeteorPlay"



        :isMusicPlaying="isPlaying"
        :main-color="albumMainColor"
        :main-color-dark="albumMainColorDark"
        :main-color-dark-double="albumMainColorDarkDouble"
        :main-color-white="albumMainColorWhite"
        :main-color-white-double="albumMainColorWhiteDouble"
        @update-album-score="handleUpdateAlbumScore"
        @score-list-change="handleScoreList"


        @update-rhy-config="handleUpdateRhyConfig"

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
          @prepare-score="prepareScore"
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

    <!-- 播放列表组件传参完整，双向绑定+防抖保存 -->
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

    <!-- 底部播放器区域 核心重构：精准坐标对齐+透明背景 -->
    <div class="full-player-wrapper">
      <!-- ✅ 修改点 1：无音频时点击封面 触发上传弹窗；有音频时保留播放暂停功能 -->
      <div class="album-rotate-box" @click="audioSrc ? togglePlayPause() : handleTriggerUpload" v-if="audioSrc && album.cover_img">
        <div class="album-rotate-circle" :class="{playing: isPlaying}">
          <img :src="album.cover_img" alt="专辑封面" class="album-rotate-img"/>
        </div>
      </div>
      <!-- ✅ 修改点 2：无音频的圆形封面 - 背景色绑定 mainColor + 点击触发上传 -->
      <div class="album-rotate-box no-cover" @click="handleTriggerUpload" v-else>
        <div class="album-rotate-circle" :style="{backgroundColor: albumMainColor}">
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
<!-- 音频上传子组件 -->
<AlbumAudioUpload
  :visible="showUploadSidebar"
  :is-update="!!audioSrc"
  :source-pool-id="album.source_pool_id"
  :old-mp3-url="oldMp3Url"
  :main-color-dark="albumMainColorDark"
  :main-color-dark-double="albumMainColorDarkDouble"
  @close="showUploadSidebar = false"
  @upload-success="handleUploadSuccess"
/>
<!-- 遮罩层 -->
<div class="mask" v-show="showUploadSidebar" @click="showUploadSidebar = false"></div>
    <!-- 修复核心报错：audio标签补全闭合标签 解决编译失败 -->
    <audio ref="audioRef" :src="audioSrc" @timeupdate="handleTimeUpdate" @ended="handleEnded" :volume="volume"></audio>
  </div>
</template>

<script>
import AlbumAudioUpload from '@/components/sidebar/AlbumAudioUpload.vue'
import AlbumBaseInfo from '@/components/albumDetail/AlbumBaseInfo'
import AlbumTrackList from '@/components/albumDetail/AlbumTrackList'
import AlbumReviewEditor from '@/components/albumDetail/AlbumReviewEditor'
import AlbumCommentSection from '@/components/albumDetail/AlbumCommentSection'
import PlayerPlaylist from '@/components/sidebar/PlayerPlaylist'
// 核心新增：引入评分计算工具函数
import {calculateAlbumTotalScore} from '@/utils/scoreCalc.js'
// ✅✅✅ 整合新增：引入全局配置文件 (小球动画配置)

export default {
  name: 'AlbumDetail',
  components: {
    AlbumBaseInfo,
    AlbumTrackList,
    AlbumReviewEditor,
    AlbumCommentSection,
    PlayerPlaylist,
    AlbumAudioUpload
  },
  data() {
    return {
      // 完整初始化album对象，补全所有必填字段，杜绝undefined
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
        my_score: [], // 修正：评分字段默认是数组，不是0.0
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
      albumMainColor: 'transparent',
      albumMainColorDark: 'transparent',
      albumMainColorDarkDouble: 'transparent',
      albumMainColorWhite: 'transparent',
      albumMainColorWhiteDouble: 'transparent',
      activeMenuBg: 'rgba(255,255,255,0.2)',
      // 播放器相关数据
      showUploadSidebar: false,
      audioSrc: '',
      fileName: '',
      volume: 0.3,
      originVolume: 0.3, // 原始音量，用于渐变恢复
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
      fadeTimer: null, // 音量渐变定时器，防止内存泄漏
      volumeTimer: null, // 线性恢复音量的定时器，防止内存泄漏
      isVolumeFading: false, // 音量渐变状态锁，防止重复触发渐变
      // ✅ ✅ ✅ 核心新增：修复暂停调音量的两个关键状态
      isPaused: false, // 标记当前是否处于暂停状态
      pausedVolume: null, // 存储暂停时手动调整的音量值
      // 播放列表核心数据【完整初始化，对接后端接口】
      showPlaylistSidebar: false,
      playlistTabs: [{name: '默认歌单', tracks: []}],
      activeTabIndex: 0,
      currentTrackIndex: -1,
      playMode: 'order',
      currentAlbumId: 0,
      currentPlaylistId: 0,
      albumList: [],
      saveTimer: null,
      // 核心修复2：新增加载状态锁，控制所有异步操作时序
      albumLoading: true,
      currentPlaySourcePoolId: 0,  // 专门存 album_pool 的id=17
      currentPlayRealAlbumId: 0,   // 专门存 用户专辑表的id=27
      // ✅✅✅ 整合新增：小球动画所有核心数据 (从子组件迁移到父组件) + ✅【修复1】补全缺失的 isBallPlay
      ballAnimationId: null,
      tailBalls: [],
      wrapDom: null,
      isScalingUp: true,
      isMouseHover: false,
      autoBallTimer: null,
      isBallPlay: false, // ✅【重中之重】父组件新增核心变量，和子组件联动控制小球开关

    meteorList: [], // 存储流星DOM元素
    meteorAnimationId: null, // 流星动画帧ID
    isMeteorPlay: false, // 流星播放状态
    autoMeteorTimer: null, // 流星自动生成定时器 ✅ 新增


      //节奏组件共用配置
      rhyConfig:{
        a:1,
        b:2,
        c:3,
        d:4,
        e:5

      },
    };


  },
  computed: {
    filteredComments() {
      return this.publicComments.filter(comment => !this.blockedCommentIds.includes(comment.id.toString()));
    },
    currentPlaylist() {
      return this.playlistTabs[this.activeTabIndex]?.tracks || []
    },
    // 核心新增：计算属性 - 自动计算专辑综合评分，响应式更新
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

        // 新增：监听流星配置更新
    meteorConfig: {
      handler(newVal) {
        // 同步到currentBallConfig，确保参数统一
        this.currentBallConfig = {
          ...this.currentBallConfig,
          ...newVal
        };
      },
      deep: true
    },

  volume(val) {
    const volumeNum = Number(val);
    const validVolume = Number.isFinite(volumeNum) ? Math.max(0, Math.min(1, volumeNum)) : 0.3;

    // 更新实际值和显示值
    this.volume = validVolume;
    const audio = this.$refs.audioRef;
    if (audio) {
      audio.volume = validVolume;
    }

    console.log('【音量变化】新值:', validVolume, ' isPlaying:', this.isPlaying, ' isPaused:', this.isPaused);

    // ✅ 简化逻辑：始终更新 pausedVolume 作为期望音量
    // 无论什么状态，用户调整的音量就是他们期望的音量
    this.pausedVolume = validVolume;

    // 如果是播放状态，也更新 originVolume
    if (this.isPlaying && !this.isPaused) {
      this.originVolume = validVolume;
    }
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
          // ✅✅✅ 整合新增：专辑切换时，重新匹配小球配置
          //this.currentBallConfig = this.getBallConfigByTag(newVal.tags);
        }
      }
    },
    albumPoolId() {
      if (this.albumPoolId && this.activeTab === 'base') {
        this.$refs.albumBaseInfo?.getAllUsersTagStatistics(this.albumPoolId);
      }
    },
    // 修复核心：路由监听逻辑【完美版】- 跳转后自动刷新数据+自动播放音频，无需手动刷新
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
                    // 改为直接调用播放方法，而不是autoPlay，跳转后必播放
                    this.autoPlayCurrentAlbumAudio();
                  }).catch(() => console.log('音频加载失败'));
                }
              }, 100); // 延时100ms，确保音频资源加载完成
            });
          }
        }
      },
    },


    // ✅✅✅ 【修复2】核心新增监听：同时监听播放状态 + 小球开关状态，双重控制
  isPlaying(newVal) {
    // 小球逻辑
    this.isBallPlay && newVal ? this.startAutoBallGenerate() : this.stopAutoBallGenerate();
    // 流星逻辑
    this.isMeteorPlay && newVal ? this.startAutoMeteorGenerate() : this.stopAutoMeteorGenerate();
  },
    // ✅✅✅ 【修复2】核心新增监听：单独监听小球开关状态，子组件点击后立即生效
  isBallPlay(newVal) {
    // 先停止所有旧的动画和定时器
    this.stopAutoBallGenerate();
    this.destroyBallAnimation();

    if (newVal) {
      this.isMeteorPlay = false; // 开启小球时，主动关闭流星（内部互斥）
      this.destroyMeteorAnimation(); // 清理流星动画

      // 初始化并启动小球动画
      this.$nextTick(() => {
        this.initBallAnimation();
        if (this.isPlaying) {
          this.startAutoBallGenerate();
        }
      });
    }
  },


  isMeteorPlay(newVal) {
    newVal && this.isPlaying ? this.startAutoMeteorGenerate() : this.stopAutoMeteorGenerate();
    if (newVal) {
      this.isBallPlay = false; // 开启流星时关闭小球
      this.destroyBallAnimation(); // 清理小球动画
    }
  },


      // 新增：监听配置参数变化，实时重启动画
  currentBallConfig: {
    handler() {
      // 如果当前是小球模式且音乐在播放，重启小球生成
      if (this.isBallPlay && this.isPlaying) {
        this.stopAutoBallGenerate(); // 先停止旧定时器
        this.startAutoBallGenerate(); // 重启加载新参数
      }
      // 如果当前是流星模式且音乐在播放，重启流星生成
      if (this.isMeteorPlay && this.isPlaying) {
        this.stopAutoMeteorGenerate(); // 先停止旧定时器
        this.startAutoMeteorGenerate(); // 重启加载新参数
      }
    },
    deep: true // 深度监听对象内部属性变化
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
      // 核心修改：跳转WebHome主页 + 强制激活【我的音乐】Tab
      this.$router.push({path: '/webhome'}).then(() => {
        // 跳转后主动修改WebHome的Tab激活状态为我的音乐
        const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
        if (webHomeVm) {
          webHomeVm.activeMainTab = 'mymusic'
        }
      })
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
    this.currentAlbumId = -1; // 初始化默认值：无播放，下标为-1
    this.currentTrackIndex = -1;
    await this.getUserHasAudioAlbums();
    this.autoPlayCurrentAlbumAudio();
  },
  mounted() {
    // ✅✅✅ 整合新增：父组件挂载后初始化小球动画
    //this.currentBallConfig = this.getBallConfigByTag(this.album.tags);
    this.initBallAnimation();
      this.initMeteorAnimation(); // 初始化流星动画
    this.isBallPlay && this.isPlaying && this.startAutoBallGenerate();
    window.addEventListener("resize", this.initBallAnimation);
  },
  activated() {
    // ✅✅✅ 整合新增：组件激活时重新初始化小球动画
    //this.currentBallConfig = this.getBallConfigByTag(this.album.tags);
    this.initBallAnimation();
      this.initMeteorAnimation(); // 激活时初始化流星
    this.isBallPlay && this.isPlaying && this.startAutoBallGenerate();
  },
  deactivated() {
    // ✅✅✅ 整合新增：组件失活时销毁小球动画
    this.destroyBallAnimation();
    this.stopAutoBallGenerate();
      this.destroyMeteorAnimation(); // 失活时销毁流星
  },
  beforeDestroy() {
    // ✅✅✅ 整合新增：组件销毁时彻底销毁小球动画+移除监听
    clearInterval(this.ratingTimer);
    this.destroyBallAnimation();
      this.destroyMeteorAnimation(); // 销毁时清理流星
    this.stopAutoBallGenerate();
    window.removeEventListener("resize", this.initBallAnimation);
    // 原有清除逻辑
    if (this.fadeTimer) clearInterval(this.fadeTimer);
    if (this.volumeTimer) clearInterval(this.volumeTimer);
    this.volumeTimer = null;
    this.fadeOutVolume(() => {
      this.pauseListeningTimer();
    });
    this.$refs.albumTrackListRef?.triggerSaveScore();
  },
  beforeUnmount() {
    if (this.audioSrc && this.audioSrc.includes('blob:')) {
      URL.revokeObjectURL(this.audioSrc);
    }
    if (this.fadeTimer) clearInterval(this.fadeTimer);
    if (this.volumeTimer) clearInterval(this.volumeTimer);
    this.volumeTimer = null;
    this.fadeOutVolume(() => {
      this.pauseListeningTimer();
    });
  },
  methods: {
        // 新增：接收 rhyConfig 并更新本地数据
    handleUpdateRhyConfig(rhyConfig) {

console.log('祖父组件接收的 rhyConfig：', JSON.parse(JSON.stringify(this.rhyConfig)));
  // 2. 核心修改：只提取需要的5个字段，忽略所有其他字段
  const pureRhyConfig = {
    a: Number(rhyConfig.a) || 1,  // 加默认值，避免空值/非数字
    b: Number(rhyConfig.b) || 2,
    c: Number(rhyConfig.c) || 3,
    d: Number(rhyConfig.d) || 4,
    e: Number(rhyConfig.e) || 5
  };

  // 3. 赋值纯净的对象给 this.rhyConfig
  this.rhyConfig = pureRhyConfig;

      // 可选：如果需要根据 rhyConfig 更新动画逻辑
      if (this.isBallPlay && this.isPlaying) {
        this.stopAutoBallGenerate();
        this.startAutoBallGenerate();
      }
      if (this.isMeteorPlay && this.isPlaying) {
        this.stopAutoMeteorGenerate();
        this.startAutoMeteorGenerate();
      }
    },



    // ✅ ✅ ✅ 新增核心方法：触发上传音频弹窗
    handleTriggerUpload() {
      if (this.isAdmin) {
        this.showUploadSidebar = true;
      } else {
        this.$message?.info('只有管理员才能上传音频资源哦～');
      }
    },
    // ✅✅✅ 【修复3】父组件新增：接收子组件的小球开关事件，修改父组件状态
    handleToggleBallPlay(val) {
      this.isBallPlay = val;
    },


// 父组件的 handleScoreList 方法修改
handleScoreList(scoreList) {
  console.log('🚀 父组件接收到scoreList：', scoreList);
  console.log('🚀 数据类型：', Array.isArray(scoreList) ? '数组' : '非数组');
  this.parentScoreList = scoreList;

  // ✅ 核心：把最新的scoreList同步到album.my_score
  if (Array.isArray(scoreList)) {
    // 深拷贝，确保响应式更新且不影响原数据
    this.album.my_score = JSON.parse(JSON.stringify(scoreList));
    console.log('✅ 父组件已同步scoreList到album.my_score：', this.album.my_score);
  }
},

    // 核心新增：音量平滑渐变淡出方法 (通用，所有暂停/切歌都调用这个)
async fadeOutVolume(callback) {
  const audio = this.$refs.audioRef;
  if (!audio || !this.isPlaying) {
    callback && callback();
    return;
  }

  // ✅ 关键修复：在淡出开始前保存当前真实音量
  // 这个值应该是用户期望暂停后再播放时的音量
  const currentRealVolume = this.volume;

  // 保存到两个地方，确保后续能恢复
  this.pausedVolume = currentRealVolume;
  this.originVolume = currentRealVolume;

  console.log('【淡出前保存】真实音量:', currentRealVolume, ' pausedVolume:', this.pausedVolume);

  // 清除之前的定时器
  if (this.volumeTimer) clearInterval(this.volumeTimer);
  this.volumeTimer = null;

  if (this.fadeTimer) clearInterval(this.fadeTimer);
  let fadeVolume = currentRealVolume; // 使用临时变量进行淡出

  this.fadeTimer = setInterval(() => {
    fadeVolume -= 0.03;
    if (fadeVolume <= 0) {
      fadeVolume = 0;
      clearInterval(this.fadeTimer);
      this.fadeTimer = null;
      audio.pause();
      this.isPlaying = false;
      this.volume = 0; // UI显示为0
      audio.volume = 0; // 实际音量为0
      callback && callback();

      // ✅ 重要：淡出完成后，恢复保存的真实音量到UI显示
      // 这样用户看到的是他们期望的音量值
      setTimeout(() => {
        this.volume = currentRealVolume;
      }, 50);
    }
    audio.volume = fadeVolume;
    // 注意：不更新 this.volume，以免影响保存的值
  }, 30);
},

handleUploadSuccess(data) {
  // 更新音频信息
  this.audioSrc = data.mp3_url;
  this.fileName = data.mp3_name;
  this.duration = data.mp3_duration;
  this.durationFormat = data.duration_format;
  this.oldMp3Url = data.mp3_url;
  this.currentTime = 0;
  this.currentProgress = 0;

  // 自动播放
  this.autoPlayCurrentAlbumAudio();
},

    // ✅ ✅ ✅ 核心重构：重置音量方法【完美修复核心问题】
// ✅ ✅ ✅ 终极修复版 - 重置音量方法【完美修复核心问题+清空时机修正】
resetVolume() {
  const audio = this.$refs.audioRef;
  if (!audio) return;

  // 1. 清除所有定时器
  if (this.fadeTimer) clearInterval(this.fadeTimer);
  if (this.volumeTimer) clearInterval(this.volumeTimer);
  this.fadeTimer = null;
  this.volumeTimer = null;
  this.isVolumeFading = false;

  console.log('【重置音量】pausedVolume:', this.pausedVolume, ' originVolume:', this.originVolume);

  // 2. ✅ 优先级：pausedVolume > originVolume > 0.3
  let targetVolume = 0.3;
  if (this.pausedVolume !== null && this.pausedVolume !== undefined) {
    targetVolume = this.pausedVolume;
  } else if (this.originVolume !== null && this.originVolume !== undefined) {
    targetVolume = this.originVolume;
  }

  // 3. 合法性校验
  targetVolume = Math.max(0, Math.min(1, targetVolume));

  // 4. 如果当前已经是静音或接近0，直接设置为目标音量
  if (this.volume < 0.05) {
    this.volume = targetVolume;
    audio.volume = targetVolume;
    console.log('【直接设置】从静音恢复到:', targetVolume);
    return;
  }

  // 5. 如果音量已经接近目标值，直接设置
  if (Math.abs(this.volume - targetVolume) < 0.05) {
    this.volume = targetVolume;
    audio.volume = targetVolume;
    console.log('【直接设置】接近目标值:', targetVolume);
    return;
  }

  // 6. 渐变恢复音量
  console.log('【开始渐变】从', this.volume, '到', targetVolume);
  this.isVolumeFading = true;
  this.volumeTimer = setInterval(() => {
    const diff = targetVolume - this.volume;
    if (Math.abs(diff) <= 0.01) {
      this.volume = targetVolume;
      audio.volume = targetVolume;
      clearInterval(this.volumeTimer);
      this.volumeTimer = null;
      this.isVolumeFading = false;
      console.log('【渐变完成】最终音量:', targetVolume);
      return;
    }

    // 动态步长：差值越大，变化越快
    const step = Math.abs(diff) > 0.1 ? 0.05 : 0.02;
    this.volume += diff > 0 ? step : -step;
    audio.volume = this.volume;
  }, 20);
},

    // 加载用户播放列表数据【对接后端GET接口】
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
          this.currentAlbumId = data.current_album_id || -1;
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

    // 自动播放当前专辑音频 - 兼容浏览器策略+静默失败+优化用户体验
    autoPlayCurrentAlbumAudio() {
      const audio = this.$refs.audioRef;
      if (this.audioSrc && audio) {
        this.resetVolume();
        this.currentTime = 0;
        this.currentProgress = 0;
        audio.currentTime = 0;
        audio.play().then(() => {
          this.isPlaying = true;
          this.startListeningTimer();
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

      await new Promise(resolve => {
        this.fadeOutVolume(async () => {
          await this.pauseListeningTimer();
          resolve();
        });
      });

      const audio = this.$refs.audioRef;
      try {
        const res = await this.$axios.get(`/api/album/pool/audio/info/${playAlbum.source_pool_id}`, {
          headers: {Authorization: localStorage.getItem('token') || ''}
        })
        if (res.data.code === 200 && res.data.data.mp3_url) {
          this.audioSrc = res.data.data.mp3_url
          this.fileName = res.data.data.mp3_name
          this.duration = res.data.data.mp3_duration
          this.durationFormat = res.data.data.duration_format

          this.currentTrackIndex = index;
          this.currentAlbumId = index;
          this.currentPlaylistId = this.activeTabIndex;

          this.currentPlaySourcePoolId = playAlbum.source_pool_id;
          this.currentPlayRealAlbumId = playAlbum.id;

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
          this.resetVolume();
          audio.currentTime = 0;
          audio.play().then(() => {
            this.isPlaying = true;
            this.startListeningTimer();
          }).catch(() => {
            this.isPlaying = false;
            this.$message?.info('📢 点击底部专辑封面即可解锁播放～');
            audio.load();
          });
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
      this.resetVolume();
      audio.play().then(() => {
        this.isPlaying = true;
        this.startListeningTimer();
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

    // 获取专辑音频信息 - 核心优化：增加return Promise，确保自动播放时机准确
// 在音频加载成功后初始化音量
async getAlbumAudioInfo() {
  try {
    const res = await this.$axios.get(`/api/album/pool/audio/info/${this.album.source_pool_id}`)
    if (res.data.code === 200 && res.data.data.mp3_url) {
      this.audioSrc = res.data.data.mp3_url
      this.fileName = res.data.data.mp3_name
      this.duration = res.data.data.mp3_duration
      this.durationFormat = res.data.data.duration_format
      this.oldMp3Url = res.data.data.mp3_url

      // ✅ 初始化音量相关状态
      this.volume = 0.3;
      this.originVolume = 0.3;
      this.pausedVolume = 0.3;

      console.log('⚠️ 跳过真实专辑ID赋值，保留歌单下标：', this.currentAlbumId);
    }
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
            my_score: item.score,
            tags: item.tags,
            release_year:item.release_year,
          }))
        }
      } catch (err) {
        console.error('❌ 获取有音频专辑列表失败')
        this.albumList = []
        this.$message.error('加载可播放专辑失败，请重试')
      }
    },


    async handleDeleteAudio() {
      const confirmDel = confirm("确定要删除该音频资源吗？删除后无法恢复！");
      if (!confirmDel) return;
      await new Promise(resolve => {
        this.fadeOutVolume(async () => {
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
          resolve();
        });
      });
    },

    clearAudioData() {
      this.audioSrc = '';
      this.fileName = '';
      this.duration = 0;
      this.durationFormat = '0:00';
      this.oldMp3Url = '';
      this.currentTime = 0;
      this.currentProgress = 0;
    },

togglePlayPause() {
  console.log('【点击瞬间】isPlaying:', this.isPlaying,
        '  volume:', this.volume,
        '  originVolume:', this.originVolume,
        '  pausedVolume:', this.pausedVolume);

  const audio = this.$refs.audioRef;
  if (!audio || !this.audioSrc) {
    this.$message?.info('暂无音频资源，无法播放');
    return;
  }

  if (this.isPlaying) {
    // 暂停操作
    this.isPaused = true;
    console.log('【开始暂停】保存当前音量:', this.volume);

    this.fadeOutVolume(() => {
      // 确保时间进度正确
      const realCurrentTime = audio.currentTime || 0;
      const realProgress = this.duration && this.duration > 0 ? (realCurrentTime / this.duration) * 100 : 0;
      this.currentTime = Math.max(0, realCurrentTime);
      this.currentProgress = Math.max(0, realProgress);
      this.$forceUpdate();
      this.pauseListeningTimer();
    });
  } else {
    // 播放操作
    this.isPaused = false;

    console.log('【开始播放】使用pausedVolume:', this.pausedVolume);

    // 确保有有效的音量值
    if (this.pausedVolume === null || this.pausedVolume === undefined) {
      this.pausedVolume = this.originVolume || 0.3;
    }

    this.resetVolume();
    audio.play().then(() => {
      this.isPlaying = true;
      this.startListeningTimer();
      // 强制同步一次音量，确保生效
      audio.volume = this.volume;
      console.log('【播放成功】当前音量:', this.volume);
    }).catch((err) => {
      this.isPlaying = false;
      console.error('播放失败:', err);
      this.$message?.warning('📢 播放失败，请检查音频资源是否有效～');
    });
  }
},

    // 新增：调用后端 开始播放计时API
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

    // 终极修复版 - 暂停计时上传时长：只暂停音频+传时长，【绝对不重置】任何进度数据！！！
    async pauseListeningTimer() {
      const token = localStorage.getItem('token') || '';
      const audio = this.$refs.audioRef;
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
      await new Promise(resolve => {
        this.fadeOutVolume(async () => {
          this.currentProgress = 0;
          this.currentTime = 0;
          await this.pauseListeningTimer();
          const audio = this.$refs.audioRef;
          if (!audio || !this.audioSrc || this.currentPlaylist.length === 0) {
            resolve();
            return;
          }

          if (this.playMode === 'single') {
            this.resetVolume();
            audio.currentTime = 0;
            audio.play().then(() => {
              this.isPlaying = true;
              this.startListeningTimer();
            }).catch(() => this.isPlaying = false);
            this.saveUserPlaylistData();
            resolve();
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
              this.currentAlbumId = newTrackIndex;
              this.currentTrackIndex = newTrackIndex;
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
            resolve();
          }
        });
      });
    },

    updateAlbumData(updatedData) {
      this.album = {...this.album, ...updatedData};
    },

handleUpdateAlbumScore(scoreList) {
  if (Array.isArray(scoreList) && scoreList.length > 0) {
    // 深拷贝，确保响应式更新
    this.album.my_score = JSON.parse(JSON.stringify(scoreList));
    console.log('✅ 父组件已同步最新评分(深拷贝)：', this.album.my_score);
  }
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

    // 修正版：支持加深/提亮，自动限制RGB值在0-255之间，杜绝非法色值
    darkenColor(hex, amount) {
      const r = Math.min(255, Math.max(0, parseInt(hex.slice(1, 3), 16) * (1 - amount)));
      const g = Math.min(255, Math.max(0, parseInt(hex.slice(3, 5), 16) * (1 - amount)));
      const b = Math.min(255, Math.max(0, parseInt(hex.slice(5, 7), 16) * (1 - amount)));
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
        otherComments.sort((a, b) => new Date(b.create_time) - new Date(a.create_time));
      } else if (this.sortType === 'like') {
        otherComments.sort((a, b) => b.like_count - a.like_count);
      } else if (this.sortType === 'listen') {
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

    // 核心修复3：getAlbumPoolRealId 加【加载状态+字段非空三重校验】，根治核心报错
    async getAlbumPoolRealId() {
      if (this.albumLoading) {
        console.log('⏳ 专辑数据加载中，稍后获取公共专辑ID');
        return;
      }
      const {album_name, singer} = this.album;
      if (!album_name || !album_name.trim() || !singer || !singer.trim()) {
        console.warn('⚠️ 专辑名称/歌手为空，跳过公共专辑创建');
        this.albumPoolId = '';
        return;
      }
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

    // 核心修复4：createAlbumPool 传参修正+字段补全，无undefined
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

    // 核心修复5：getAlbumDetail 加加载状态锁，异步请求有开始/结束标记
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
                // ======== 【修改点2/4】替换跳转逻辑 ========
                this.$router.push({path: '/webhome'}).then(() => {
                  const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
                  if (webHomeVm) {
                    webHomeVm.activeMainTab = 'mymusic'
                  }
                })
                reject(res.data.msg);
              }
            })
            .catch(() => {
              console.error('获取详情失败：');
              alert('获取专辑详情失败！');
              // ======== 【修改点3/4】替换跳转逻辑 ========
              this.$router.push({path: '/webhome'}).then(() => {
                const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
                if (webHomeVm) {
                  webHomeVm.activeMainTab = 'mymusic'
                }
              })
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

// 3. 修改addSingleReview方法，移除重复的异步操作，直接使用子组件传递的评分
async addSingleReview(content, finalScore) {
  if (!content.trim()) {
    alert('听后感内容不能为空！');
    return;
  }

  const now = new Date();
  const createTime = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

  // 直接使用子组件计算好的最终评分，避免重复计算导致的不一致
  console.log('✅ 父组件最终提交的综合评分：', finalScore);

  try {
    const res = await this.$axios({
      url: `/api/album/review/add/${this.album.id}`,
      method: 'POST',
      headers: {
        'Authorization': localStorage.getItem('token') || '',
        'Content-Type': 'application/json;charset=utf-8'
      },
      data: {
        content: content.trim(),
        create_time: createTime,
        listening_duration: Math.floor(this.album.listening_duration),
        my_score: finalScore, // 使用子组件传递的评分
      }
    });

    if (res.data.code === 200) {
      // 重新加载专辑数据，确保UI同步
      await this.getAlbumDetail(this.album.id);
      this.$message?.success('听后感添加成功！');
    } else {
      this.$message?.error(res.data.msg);
    }
  } catch (err) {
    console.error('添加听后感失败：', err);
    this.$message?.error('添加听后感失败！');
  }
},
    deleteSingleReview(feelingId) {
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

    // 核心修复6：完整重置方法，补全所有字段，无undefined
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
        my_score: [],
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
      // 重置音量相关状态
      this.isPaused = false;
      this.pausedVolume = null;
    },
    // ======== 【修改点4/4】核心修改：返回按钮的跳转逻辑 ========
    goBack() {
      console.log(111)
      // 核心：定义一个Vue全局变量，存要切换的tab值
      window.targetTab = 'mymusic'
      // 正常跳转/webhome即可，不用加任何meta
      this.$router.push({path: '/webhome'})
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

    // 2. 新增prepareScore方法，专门处理评分的保存和读取
// 父组件的 prepareScore 方法（已存在，确认逻辑）
async prepareScore() {
  // 等待子组件（AlbumTrackList）保存评分并获取最新值
  if(this.$refs.albumTrackListRef) {
    await this.$refs.albumTrackListRef.triggerSaveScore();
    await this.$refs.albumTrackListRef.triggerGetScore();
  }
  // 强制更新album数据，确保子组件能拿到最新的scoreList
  this.album = {...this.album};
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
    },
    // ✅✅✅ ======================== 以下是整合新增的【小球动画所有核心方法】 ========================


    startAutoBallGenerate() {
      // ✅✅✅ 【修复4】核心判断：三重条件，缺一不可，彻底杜绝关不掉的问题
      if (this.autoBallTimer || this.isMouseHover || !this.isPlaying || !this.isBallPlay) return;

      const{a,b,c,d,e}=this.rhyConfig
      const light2Size=a
      const sizeMax=b*5
      const sizeMin=Math.floor(sizeMax/3)
      const timeLine=c*10
      const lightSize=d/100
      const numWeight=Math.floor(e/10)



      this.autoBallTimer = setInterval(() => {
        if (!this.wrapDom || this.isMouseHover || !this.isPlaying || !this.isBallPlay) return;
        for (let i = 0; i < numWeight; i++) {
          const x = Math.floor(Math.random() * this.wrapDom.offsetWidth);
          const y = Math.floor(Math.random() * this.wrapDom.offsetHeight);
          this.createTailBall(x, y,sizeMax,sizeMin,lightSize,light2Size, true);
        }
      }, timeLine);
    },
createTailBall(x, y,sizeMax,sizeMin,lightSize,light2Size, isAuto = false) {
  let ballSize;
  if (isAuto) {
    ballSize = Math.floor(Math.random() * (sizeMax - sizeMin)) + sizeMin;
  } else {
    ballSize = Math.floor(Math.random() * 12) + 8;
  }
  const halfSize = ballSize / 2;
  const ballDom = document.createElement("div");

  // ✨ 增强渐变效果：添加多色阶渐变 + 透明度渐变 + 动态发光
  const gradientVariations = [
    // 主色调渐变（更细腻的过渡）
    `linear-gradient(135deg, ${this.albumMainColorDarkDouble} 0%, ${this.albumMainColorDark} 50%, ${this.albumMainColor} 100%)`,
    `linear-gradient(45deg, ${this.albumMainColor} 0%, ${this.albumMainColorWhite} 70%, ${this.albumMainColorWhiteDouble} 100%)`,
    `linear-gradient(90deg, ${this.albumMainColorDark} 0%, rgba(${this.hexToRgb(this.albumMainColor).r}, ${this.hexToRgb(this.albumMainColor).g}, ${this.hexToRgb(this.albumMainColor).b}, 0.8) 100%)`,
    // 透明渐变（更自然的消失效果）
    `radial-gradient(circle, ${this.albumMainColor} 0%, rgba(${this.hexToRgb(this.albumMainColor).r}, ${this.hexToRgb(this.albumMainColor).g}, ${this.hexToRgb(this.albumMainColor).b}, 0.6) 70%, transparent 100%)`,
    // 双色渐变（更丰富的视觉效果）
    `linear-gradient(135deg, ${this.albumMainColorDarkDouble} 0%, ${this.albumMainColorWhiteDouble} 100%)`
  ];

  const randomGradient = gradientVariations[Math.floor(Math.random() * gradientVariations.length)];

  // ✨ 新增：随机初始透明度 + 动态发光效果
  const initialAlpha = lightSize*0.8 +Math.random() *  0.1; // 初始透明度 0.2-1.0
  const glowSize = light2Size+Math.random() * 10; // 发光大小 5-15px

  ballDom.style.cssText = `
    position:absolute;
    width:${ballSize}px;
    height:${ballSize}px;
    border-radius:50%;
    background:${randomGradient};
    pointer-events:none;
    z-index:100;
    left:${x - halfSize}px;
    top:${y - halfSize}px;
    opacity: ${initialAlpha};
    box-shadow: 0 0 ${glowSize}px rgba(${this.hexToRgb(this.albumMainColor).r}, ${this.hexToRgb(this.albumMainColor).g}, ${this.hexToRgb(this.albumMainColor).b}, 0.5);
    transition: opacity 0.3s ease-out, transform 0.3s ease-out;
  `;

  this.wrapDom.appendChild(ballDom);
  // 保存初始大小和透明度，用于渐变动画
  this.tailBalls.push({
    dom: ballDom,
    alpha: initialAlpha,
    size: ballSize,
    initialSize: ballSize
  });
},
// 十六进制颜色转RGB对象（方便生成透明渐变）
hexToRgb(hex) {
  // 去除#号
  const cleanHex = hex.replace(/^#/, '');
  // 解析RGB值
  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);
  return { r, g, b };
},
// 2. 优化初始化方法：确保销毁完成后再重建
initBallAnimation() {
  // 先彻底销毁旧动画
  this.destroyBallAnimation();

  // 重新获取容器
  this.wrapDom = this.$refs.ballWrap;
  if (!this.wrapDom) return;

  // 重新启动渲染循环
  this.ballAnimationId = requestAnimationFrame(this.renderBallAnimation);

  // 重新启动自动生成（如果需要）
  if (this.isBallPlay && this.isPlaying && !this.isMouseHover) {
    this.startAutoBallGenerate();
  }
},


// 3. 优化渲染方法：修复过滤逻辑，确保所有小球都能被清理
renderBallAnimation() {
  // 边界检查：容器不存在则停止
  if (!this.wrapDom) {
    this.destroyBallAnimation();
    return;
  }

  // 过滤并更新小球状态
  const newTailBalls = [];
  for (let i = 0; i < this.tailBalls.length; i++) {
    const ball = this.tailBalls[i];
    // 安全检查：DOM不存在则跳过
    if (!ball.dom || !ball.dom.parentNode) {
      continue;
    }

    // 渐变衰减：透明度和大小同时变化
    ball.alpha -= 0.015;
    ball.size = ball.initialSize * ball.alpha;

    if (ball.alpha <= 0) {
      // 强制移除DOM
      try {
        ball.dom.remove();
      } catch (e) {print(e)}
      continue;
    }

    // 应用渐变样式
    ball.dom.style.opacity = ball.alpha;
    ball.dom.style.transform = `scale(${ball.alpha})`;
    // 增强：添加轻微的位置偏移，模拟漂浮效果
    const currentLeft = parseFloat(ball.dom.style.left) || 0;
    const currentTop = parseFloat(ball.dom.style.top) || 0;
    ball.dom.style.left = `${currentLeft + (Math.random() * 2 - 1)}px`;
    ball.dom.style.top = `${currentTop + (Math.random() * 2 - 1)}px`;

    newTailBalls.push(ball);
  }

  // 替换数组（避免原数组引用问题）
  this.tailBalls = newTailBalls;

  // 继续循环（只有还有小球或开启状态才继续）
  if (this.tailBalls.length > 0 || this.isBallPlay) {
    this.ballAnimationId = requestAnimationFrame(this.renderBallAnimation);
  } else {
    // 没有小球且关闭状态，停止循环
    cancelAnimationFrame(this.ballAnimationId);
    this.ballAnimationId = null;
  }
},


// 1. 优化销毁方法：彻底停止所有动画和定时器
destroyBallAnimation() {
  // 停止动画帧
  if (this.ballAnimationId) {
    cancelAnimationFrame(this.ballAnimationId);
    this.ballAnimationId = null;
  }

  // 停止自动生成定时器
  this.stopAutoBallGenerate();

  // 移除所有小球DOM元素（双重保障）
  if (this.wrapDom) {
    // 方式1：清空数组并移除DOM
    this.tailBalls.forEach((ball) => {
      try {
        ball.dom?.remove();
      } catch (e) {
        console.warn('移除小球DOM失败:', e);
      }
    });
    // 方式2：直接清空容器（兜底）
    this.wrapDom.innerHTML = "";
  }

  // 清空数组
  this.tailBalls = [];
  this.isMouseHover = false; // 重置鼠标悬浮状态
},
    handleMouseMove(e) {
      if (!this.wrapDom || !this.isBallPlay) return; // ✅ 加判断：关闭状态不生成鼠标小球
      this.isMouseHover = true;
      this.stopAutoBallGenerate();
      const x = e.offsetX, y = e.offsetY;
      this.createTailBall(x, y);
    },
// 4. 优化鼠标离开事件：确保异步更新DOM后再重建
handleMouseLeave() {
  this.isMouseHover = false;
  // 立即销毁当前动画
  this.destroyBallAnimation();
  // 等待DOM更新完成后再初始化
  this.$nextTick(() => {
    this.initBallAnimation();
    // 只有同时满足开启和播放状态才重新生成
    if (this.isBallPlay && this.isPlaying) {
      this.startAutoBallGenerate();
    }
  });
},

    stopAutoBallGenerate() {
      this.autoBallTimer && (clearInterval(this.autoBallTimer), (this.autoBallTimer = null));
    },


    // 修复：自动生成流星逻辑
    startAutoMeteorGenerate() {

      // 三重条件校验
      if (this.autoMeteorTimer || this.isMouseHover || !this.isPlaying || !this.isMeteorPlay) return;

      // 正确获取参数：从meteorConfig和currentBallConfig中取值


      const {a, b, c, d,e} = this.rhyConfig;
      const angle=a/1.5
      const size=b*5
      const timeLine=c*10
      const speed=d/5
      const finalNumWeight=Math.floor(e/20)



      // 使用合理的默认值兜底

      this.autoMeteorTimer = setInterval(() => {
        if (!this.wrapDom || this.isMouseHover || !this.isPlaying || !this.isMeteorPlay) return;

        // 批量生成流星
        for (let i = 0; i < finalNumWeight; i++) {
          // 随机起始位置（屏幕顶部外）
          const x = Math.floor(Math.random() * this.wrapDom.offsetWidth);
          const y = -50;

          // 随机化参数，增加视觉多样性
          const randomParams = {
            angle: angle + (Math.random() * 10 - 5), // 角度±5度波动
            size: size * (0.8 + Math.random() * 0.4), // 大小±20%波动
            speed: speed * (0.8 + Math.random() * 0.4) // 速度±20%波动
          };

          this.createMeteor(x, y, randomParams);
        }
      },
          timeLine);
    },

    // 优化：创建流星方法，修复参数使用
    createMeteor(x, y, meteorParams) {
      if (!this.wrapDom) return;

      // 解构参数并设置默认值
      const {
        angle = this.meteorConfig.angle || 45,
        size = this.meteorConfig.size || 10,
        speed = this.meteorConfig.speed || 30,
      } = meteorParams;

      // ✨ 流星渐变优化
      const rgb = this.hexToRgb(this.albumMainColor);

      const gradient = `linear-gradient(
        ${angle}deg,
        rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 1) 0%,
        rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.7) 50%,
        transparent 100%
      )`;

      // 创建流星主体（圆形）
      const meteorDom = document.createElement("div");
      meteorDom.style.cssText = `
        position:absolute;
        width: ${size}px;
        height: ${size}px;
        background: ${gradient};
        border-radius: 50%;
        pointer-events:none;
        z-index: 101;
        left:${x}px;
        top:${y}px;
        box-shadow: 0 0 ${size * 2}px rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.8);
        opacity: 1;
        transition: all 0.05s linear;
      `;



      // 添加到容器
      this.wrapDom.appendChild(meteorDom);

      // 流星移动动画
      const moveMeteor = () => {
        // 角度转弧度，计算x/y偏移
        const radian = (angle * Math.PI) / 180;
        x += speed * Math.sin(radian);
        y += speed * Math.cos(radian);

        // 更新位置
        meteorDom.style.left = `${x}px`;
        meteorDom.style.top = `${y}px`;

        // 渐变透明度
        let alpha = 1 - (y / window.innerHeight);
        meteorDom.style.opacity = alpha > 0 ? alpha : 0;
        meteorDom.style.transform = `scale(${alpha > 0.5 ? alpha : 0.5})`;

        // 超出屏幕则移除
        if (y > window.innerHeight + size ) {
          meteorDom.remove();
          return;
        }

        requestAnimationFrame(moveMeteor);
      };

      // 启动移动动画
      requestAnimationFrame(moveMeteor);
    },

   // 停止自动生成流星
stopAutoMeteorGenerate() {
  this.autoMeteorTimer && (clearInterval(this.autoMeteorTimer), (this.autoMeteorTimer = null));
},

    // 新增：接收子组件的流星配置更新
    handleUpdateMeteorConfig(config) {
      this.meteorConfig = {
        ...this.meteorConfig,
        ...config
      };
    },

    // 修复：接收小球配置更新
    handleUpdateBallConfig(config) {
      this.currentBallConfig = {
        ...this.currentBallConfig,
        ...config
      };
    },
// 初始化流星动画
initMeteorAnimation() {
  this.destroyMeteorAnimation();
  // 清空旧数据
  this.meteorList = [];
  // 启动渲染循环（仅用于清理过期元素）
  this.meteorAnimationId = requestAnimationFrame(this.renderMeteorAnimation);
},

// 渲染流星动画（仅用于清理）
renderMeteorAnimation() {
  // 清理超出屏幕的流星元素
  this.meteorList = this.meteorList.filter(meteor => {
    const isOutOfBounds =
      meteor.y > window.innerHeight + 100 ||
      meteor.x < -100 ||
      meteor.x > window.innerWidth + 100 ||
      meteor.alpha <= 0;

    if (isOutOfBounds) {
      meteor.dom?.remove();
      return false;
    }
    return true;
  });

  // 继续循环
  this.meteorAnimationId = requestAnimationFrame(this.renderMeteorAnimation);
},

// 销毁流星动画
destroyMeteorAnimation() {
  // 停止动画帧
  this.meteorAnimationId && cancelAnimationFrame(this.meteorAnimationId);
  this.meteorAnimationId = null;

  // 停止自动生成定时器
  this.stopAutoMeteorGenerate();

  // 移除所有流星DOM
  this.meteorList.forEach(meteor => meteor.dom?.remove());
  this.meteorList = [];

  // 清空容器中的流星元素（兜底）
  if (this.wrapDom) {
    const meteors = this.wrapDom.querySelectorAll('div[style*="z-index: 101"]');
    meteors.forEach(meteor => meteor.remove());
  }
},

// 处理子组件触发的生成流星事件
handleGenerateMeteor(meteorParams = {}) {
  if (!this.wrapDom || !this.isMeteorPlay) return;

  const { count = 1, ...params } = meteorParams;
  for (let i = 0; i < count; i++) {
    const x = Math.floor(Math.random() * this.wrapDom.offsetWidth);
    const y = -50;
    this.createMeteor(x, y, params);
  }
},

// 处理流星播放状态切换
handleToggleMeteorPlay(val) {
  this.isMeteorPlay = val;

  if (val) {
    // 开启流星：初始化动画 + 自动生成（如果音乐在播放）
    this.initMeteorAnimation();
    this.isPlaying && this.startAutoMeteorGenerate();
  } else {
    // 关闭流星：销毁动画 + 停止自动生成
    this.destroyMeteorAnimation();
  }
},



  },
  // 路由离开守卫，强制保存播放列表
  beforeRouteLeave(to, from, next) {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveUserPlaylistData();
    this.fadeOutVolume(() => {
      this.pauseListeningTimer();
    });
    this.$refs.albumTrackListRef?.triggerSaveScore();
    next();
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
  height: 97vh;
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
  /*padding-bottom: 140px !important;*/
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: 2;
  height: 98vh;
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
  bottom: 3px;
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
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-resource-text {
  font-size: 12px;
  color: #fff;
  font-weight: 500;
  text-align: center;
  padding: 0 10px;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
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
  height: 3px;
  cursor: pointer;
  accent-color: v-bind(albumMainColorDark);
  min-width: unset;
  z-index: 9999;
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

/* ✅✅✅ 核心修改：小球动画容器层级提升，和Album_TrackList同层，置顶不被遮挡 */
.ball-animation-wrap {
  width: 100vw !important;
  height: 100vh !important;
  border-radius: 0 !important;
  background-color: transparent !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  z-index: 99 !important;
  overflow: hidden !important;
  cursor: none !important;
  pointer-events: none !important;
}
</style>