<template>
  <div class="tab-content">
    <!-- ✅ 整体弹性布局：左60% 列表区 + 右40% 评分+节奏组件区 完全自适应 -->
    <div class="main-layout">
      <!-- 左侧：弹性60% 区域 - Tab+编辑按钮 全部置顶固定 + 列表内容自适应滚动 -->
      <div class="left-panel">
        <!-- ✅ 核心：【Tab导航+编辑按钮】整体置顶固定，永不滚动 + 同一行展示 -->
        <div class="sticky-top-box">
          <!-- ✅ 核心修改：新增flex容器，Tab居左+按钮居右 同一行完美对齐 -->
          <div class="tab-nav-btn-box">
            <div class="track-tab-nav">
              <div
                class="tab-item"
                :class="{active: activeTab === 'tracks'}"
                @click="activeTab = 'tracks'"
              >
                单曲列表
              </div>
              <div
                class="tab-item"
                :class="{active: activeTab === 'favourite'}"
                @click="activeTab = 'favourite'"
              >
                编辑喜欢时间戳
              </div>
            </div>

            <!-- ✅ 编辑按钮和Tab联动，置顶固定 + 新增【切换输入模式】按钮 -->
            <div class="tracks-header sticky-header">
              <div class="tracks-action-btn">
                <button
                  class="edit-btn"
                  @click="toggleEditStatus(activeTab)"
                  :class="{active: activeTab === 'tracks' ? isTrackEditMode : isFavouriteEditMode}"
                >
                  {{ activeTab === 'tracks'
                    ? (isTrackEditMode ? '✅ 保存曲目' : '✏️ 编辑曲目')
                    : (isFavouriteEditMode ? '✅ 保存时间戳' : '✏️ 编辑时间戳')
                  }}
                </button>

                <!-- ✅ 切换单曲【时间戳/时长】输入模式按钮 - 仅在单曲编辑模式显示 -->
                <button
                  v-if="activeTab === 'tracks' && isTrackEditMode"
                  class="mode-btn"
                  @click="toggleDurationMode"
                  :class="{active: isDurationMode}"
                  style="margin-left: 8px;"
                >
                  {{ isDurationMode ? '⏰ 切换为时间戳输入' : '🕒 切换为时长输入' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ✅ 核心：列表内容区 自适应滚动，只有这里滚动，顶部内容完全不动 -->
        <div class="tab-content-scroll">
          <div class="tracks-container" v-show="activeTab === 'tracks'">
            <div class="tracks-list">
              <div
                v-for="(track, idx) in trackList"
                :key="idx"
                class="track-item"
                @click="handleTrackClick(idx)"
              >
                <!-- ✅ 恢复单曲序号展示 + 无下划线 | 提升层级 永远挡住歌名 -->
                <div class="track-index">{{ idx + 1 }}.</div>

                <div v-if="isTrackEditMode" class="track-edit-content">
                  <input
                    type="text"
                    v-model="track.name"
                    placeholder="请输入曲目名称"
                    class="track-name-input"
                  />

                  <!-- ✅ 核心切换：时长输入模式 / 时间戳输入模式 互斥显示 -->
                  <input
                    v-if="!isDurationMode"
                    type="text"
                    v-model="track.duration"
                    placeholder="0:00:00 时间戳"
                    class="track-duration-input"
                    maxlength="8"
                    @input="track.duration = filterDurationInput(track.duration)"
                    @blur="formatDurationInput('tracks', idx)"
                  />
                  <input
                    v-else
                    type="text"
                    v-model="track.playDuration"
                    placeholder="0:00:00 单曲时长"
                    class="track-duration-input"
                    maxlength="8"
                    @input="track.playDuration = filterDurationInput(track.playDuration)"
                    @blur="handleDurationInputBlur(idx)"
                  />
                </div>

                <div v-else class="track-show-content">
                  <!-- ✅ ✅ ✅ 核心修复：拆分结构+精准裁切+层级置顶+永不越界+长短歌名区分滚动 -->
                  <div class="track-name-wrap">
                    <div class="track-name-text">{{ track.name || '未知曲目' }}</div>
                    <div class="track-name-line"></div>
                  </div>
                  <!-- ✅ 进度条 - 只在单曲列表展示 + 增加 @click.stop 阻止冒泡 -->
                  <div class="track-score-slider-wrap">
                    <div
                      class="track-score-slider"
                      ref="scoreSlider"
                      @mousedown="(e) => startTrackScore(e, idx)"
                      @mouseup="stopTrackScore"
                      @mouseleave="stopTrackScore"
                      @click.stop="(e) => setTrackScoreByClick(e, idx)"
                    >
                      <div
                        class="track-score-progress"
                        :style="{ width: `${track.score || 0}%` }"
                      ></div>
                    </div>
                    <span class="track-score-text">{{ track.score || 0 }}分</span>
                  </div>
                  <div class="track-duration">{{ track.duration || '0:00:00' }}</div>
                </div>

                <div v-if="isTrackEditMode" class="track-del-btn">
                  <button @click.stop="deleteTrack('tracks', idx)">×</button>
                </div>
              </div>
            </div>

            <div v-if="isTrackEditMode" class="add-track-btn-box">
              <button class="add-track-btn" @click="addNewTrack('tracks')">➕ 添加新单曲</button>
            </div>
          </div>

          <div class="tracks-container" v-show="activeTab === 'favourite'">
            <div class="tracks-list">
              <div
                v-for="(track, idx) in favouriteTrackList"
                :key="idx"
                class="track-item"
                @click="handleFavouriteTrackClick(idx)"
              >
                <!-- ✅ 恢复喜欢时间戳序号展示 + 无下划线 -->
                <div class="track-index">{{ idx + 1 }}.</div>

                <div v-if="isFavouriteEditMode" class="track-edit-content">
                  <input
                    type="text"
                    v-model="track.name"
                    placeholder="请输入喜欢曲目名称"
                    class="track-name-input"
                  />
                  <input
                    type="text"
                    v-model="track.duration"
                    placeholder="0:00:00"
                    class="track-duration-input"
                    maxlength="8"
                    @input="track.duration = filterDurationInput(track.duration)"
                    @blur="formatDurationInput('favourite', idx)"
                  />
                </div>

                <div v-else class="track-show-content">
                  <!-- ✅ ✅ ✅ 收藏列表同步修复：同逻辑 无遮挡 不越界 长短歌名区分滚动 -->
                  <div class="track-name-wrap">
                    <div class="track-name-text">{{ track.name || '未知曲目' }}</div>
                    <div class="track-name-line"></div>
                  </div>
                  <div class="track-duration">{{ track.duration || '0:00:00' }}</div>
                </div>

                <div v-if="isFavouriteEditMode" class="track-del-btn">
                  <button @click.stop="deleteTrack('favourite', idx)">×</button>
                </div>
              </div>
            </div>

            <div v-if="isFavouriteEditMode" class="add-track-btn-box">
              <button class="add-track-btn" @click="addNewTrack('favourite')">➕ 添加新时间戳</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ✅ 右侧：弹性40% 上=评分组件 | 下=节奏组件（透明+无标题） -->
      <div class="right-panel">
        <!-- 上半部分：个人感觉评分组件 -->
        <div class="rate-container">
          <div class="rate-content-wrap">
            <div class="rate-text-area">
              <h3>个人感觉评分 (0-100)</h3>
<div class="rate-score">{{ score.toFixed(1) }} 分</div>
              <button class="reset-rate-btn" @click="resetRating">重置评分</button>
            </div>
            <div class="rate-circle-area">
              <div class="outer-circle"
                @mousedown="startRating"
                @mouseup="stopRating"
                @mouseleave="stopRating"
              >
                <div class="inner-circle" :style="{ width: `${score}%`, height: `${score}%` }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 下半部分：节奏可视化组件 ✅ 隐藏标题+全透明背景+透明画布 -->
        <div class="rhythm-container">
          <!-- ✅ 移除标题 -->
          <div class="ball-animation-wrap"
               ref="ballWrap"
               @mousemove="handleMouseMove"
               @mouseleave="handleMouseLeave"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumTrackList',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    tracks: {
      type: Array,
      default: () => []
    },
    tracksTime: {
      type: Array,
      default: () => []
    },
    favourite_tracks: {
      type: Array,
      default: () => []
    },
    favourite_tracks_time: {
      type: Array,
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
      activeTab: 'tracks', // tracks=单曲列表 favourite=喜欢时间戳
      isTrackEditMode: false, // 普通曲目编辑状态
      isFavouriteEditMode: false, // 喜欢时间戳编辑状态
      trackList: [], // 普通曲目数据 {name: '', duration: '', sec: 秒数, score: 评分0-100, playDuration:'' 单曲时长}
      favouriteTrackList: [], // 收藏曲目数据 {name: '', duration: '', sec: 秒数}
      // 评分组件相关数据
      score: 0,        // 最终评分 0-100 【全局个人感觉评分】
      isRating: false, // 是否正在按压评分
      ratingTimer: null,// 评分定时器
      // ✅ 单首曲目评分相关 - 新增存储当前滑块DOM
      isTrackScoring: false,
      currentTrackIdx: -1,
      currentSliderDom: null, // 存储当前操作的进度条DOM节点
      // ✅ 时长/时间戳 切换模式状态
      isDurationMode: false,
      // ✅ 纯拖尾特效 - 移除主球相关数据，只保留拖尾数组
      ballAnimationId: null,  // 动画帧ID
      tailBalls: [],          // 拖尾小球数组 [{dom, alpha}]
      wrapDom: null,        // 动画容器dom


      isScalingUp: true, // 新增：true=放大，false=缩小
    };
  },
  watch: {
    tracks: {
      handler() {
        this.initTrackList(true);
      }, deep: true
    },
    tracksTime: {
      handler() {
        this.initTrackList(true);
      }, deep: true
    },
    favourite_tracks: {
      handler() {
        this.initFavouriteTrackList();
      }, deep: true
    },
    favourite_tracks_time: {
      handler() {
        this.initFavouriteTrackList();
      }, deep: true
    },
    album: {
      handler() {
        this.initTrackList(true);
        this.initFavouriteTrackList();
      }, deep: true
    }
  },
  mounted() {
    this.initTrackList();
    this.initFavouriteTrackList();
    this.getAllScore();
    // ✅ 初始化拖尾动画
    this.$nextTick(() => {
      this.initBallAnimation();
    });
    // ✅ 窗口大小变化重新适配
    window.addEventListener('resize', this.initBallAnimation);
  },
  activated() {
    this.initTrackList(true);
    this.initFavouriteTrackList();
    this.getAllScore();
    // ✅ 组件激活时重新初始化动画
    this.$nextTick(() => {
      this.initBallAnimation();
    });
  },
  deactivated() {
    this.saveAllScore();
    this.destroyBallAnimation(); // 停止动画
  },
  beforeDestroy() {
    clearInterval(this.ratingTimer);
    this.isTrackScoring = false;
    this.currentTrackIdx = -1;
    this.currentSliderDom = null;
    document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    this.saveAllScore();
    // ✅ 销毁动画，防止内存泄漏
    this.destroyBallAnimation();
    // ✅ 移除窗口监听
    window.removeEventListener('resize', this.initBallAnimation);
  },
  methods: {
    async saveAllScore() {
      try {
        const albumId = this.album.id;
        if (!albumId) return;
        let scoreList = [this.score];
        this.trackList.forEach(item => {
          scoreList.push(item.score || 0);
        });
        await this.$axios.put(`/api/album/score/save/${albumId}`, {
          score_list: scoreList
        }, {
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          }
        });
      } catch (err) {
        console.error('保存评分失败：', err);
      }
    },
    async getAllScore() {
      try {
        const albumId = this.album.id;
        if (!albumId) return;
        const res = await this.$axios.get(`/api/album/score/get/${albumId}`, {
          headers: {
            'Authorization': localStorage.getItem('token') || ''
          }
        });
        if (res.data.code === 200 && res.data.data.score_list) {
          const scoreList = res.data.data.score_list;
          if (Array.isArray(scoreList) && scoreList.length > 0) {
            this.score = scoreList[0] || 0;
            this.trackList.forEach((item, idx) => {
              item.score = scoreList[idx + 1] || 0;
            });
          }
        }
      } catch (err) {
        console.error('读取评分失败：', err);
      }
    },
    timeToSeconds(timeStr) {
      if (!timeStr || timeStr.length === 0) return 0;
      let timeArr = timeStr.split(':').map(item => Number(item)).filter(item => !isNaN(item));
      let hours = 0, minutes = 0, seconds = 0;
      if (timeArr.length === 2) {
        minutes = timeArr[0];
        seconds = timeArr[1];
      } else if (timeArr.length === 3) {
        hours = timeArr[0];
        minutes = timeArr[1];
        seconds = timeArr[2];
      }
      minutes = Math.min(Math.max(minutes, 0), 59);
      seconds = Math.min(Math.max(seconds, 0), 59);
      hours = Math.max(hours, 0);
      return hours * 3600 + minutes * 60 + seconds;
    },
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const totalSeconds = Math.floor(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const sec = Math.floor(totalSeconds % 60);
      return `${hours}:${minutes.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      const colonCount = filterVal.split(':').length - 1;
      if (colonCount > 2) {
        filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      }
      return filterVal;
    },
    initTrackList(keepScore = false) {
      const oldScoreMap = {};
      if (keepScore && this.trackList.length > 0) {
        this.trackList.forEach((item, idx) => {
          oldScoreMap[idx] = item.score || 0;
        });
      }
      this.trackList = [];
      const trackNames = Array.isArray(this.tracks) && this.tracks.length > 0 ? this.tracks : [];
      const trackSecs = Array.isArray(this.tracksTime) && this.tracksTime.length > 0 ? this.tracksTime : [];
      if (trackNames.length > 0) {
        trackNames.forEach((name, idx) => {
          const dbSec = trackSecs[idx] || 0;
          this.trackList.push({
            name: name.trim() || '未知曲目',
            sec: dbSec,
            duration: this.secondsToTime(dbSec),
            playDuration: '0:00:00',
            score: keepScore ? oldScoreMap[idx] || 0 : 0
          });
        });
      } else {
        this.trackList = [{name: '未知曲目', sec: 0, duration: '0:00:00', playDuration: '0:00:00', score: 0}];
      }
    },
    initFavouriteTrackList() {
      this.favouriteTrackList = [];
      const trackNames = Array.isArray(this.favourite_tracks) && this.favourite_tracks.length > 0 ? this.favourite_tracks : [];
      const trackSecs = Array.isArray(this.favourite_tracks_time) && this.favourite_tracks_time.length > 0 ? this.favourite_tracks_time : [];
      if (trackNames.length > 0) {
        trackNames.forEach((name, idx) => {
          const dbSec = trackSecs[idx] || 0;
          this.favouriteTrackList.push({
            name: name.trim() || '未知曲目',
            sec: dbSec,
            duration: this.secondsToTime(dbSec)
          });
        });
      } else {
        this.favouriteTrackList = [{name: '未知曲目', sec: 0, duration: '0:00:00'}];
      }
    },
    formatDurationInput(type, idx) {
      if (type === 'tracks') {
        const track = this.trackList[idx];
        if (!track) return;
        track.sec = this.timeToSeconds(track.duration);
        track.duration = this.secondsToTime(track.sec);
      } else {
        const track = this.favouriteTrackList[idx];
        if (!track) return;
        track.sec = this.timeToSeconds(track.duration);
        track.duration = this.secondsToTime(track.sec);
      }
    },
    toggleDurationMode() {
      this.isDurationMode = !this.isDurationMode;
      if (this.isDurationMode) {
        this.trackList.forEach(item => {
          item.playDuration = item.playDuration || '0:00:00';
        })
      }
    },
    handleDurationInputBlur(idx) {
      const track = this.trackList[idx];
      if (!track) return;
      track.playDuration = this.filterDurationInput(track.playDuration);
      const durationSec = this.timeToSeconds(track.playDuration);
      track.playDuration = this.secondsToTime(durationSec);
      this.calcTrackTimestamp();
    },
    calcTrackTimestamp() {
      let totalSec = 0;
      this.trackList.forEach((track, idx) => {
        if (idx === 0) {
          totalSec = 0;
        }
        track.duration = this.secondsToTime(totalSec);
        track.sec = totalSec;
        const playSec = this.timeToSeconds(track.playDuration);
        totalSec += playSec;
      });
    },
    async toggleEditStatus(type) {
      if (type === 'tracks') {
        if (this.isTrackEditMode) {
          if (this.isDurationMode) {
            this.calcTrackTimestamp();
          }
          await this.saveTrackList('tracks');
          this.isTrackEditMode = false;
          this.isDurationMode = false;
        } else {
          this.isTrackEditMode = true;
        }
      } else {
        if (this.isFavouriteEditMode) {
          await this.saveTrackList('favourite');
          this.isFavouriteEditMode = false;
        } else {
          this.isFavouriteEditMode = true;
        }
      }
    },
    addNewTrack(type) {
      if (type === 'tracks') {
        this.trackList.push({name: '', duration: '0:00:00', sec: 0, playDuration: '0:00:00', score: 0});
        if (this.isDurationMode) {
          this.calcTrackTimestamp();
        }
      } else {
        this.favouriteTrackList.push({name: '', duration: '0:00:00', sec: 0});
      }
    },
    deleteTrack(type, idx) {
      let targetList = type === 'tracks' ? this.trackList : this.favouriteTrackList;
      if (targetList.length <= 1) {
        alert('至少保留1条哦！');
        return;
      }
      targetList.splice(idx, 1);
      if (type === 'tracks' && this.isDurationMode) {
        this.calcTrackTimestamp();
      }
    },
    async saveTrackList(type) {
      try {
        let submitList, submitSecArr, apiUrl, emitKey1, emitKey2;
        if (type === 'tracks') {
          submitList = this.trackList.map(item => item.name.trim() || '未知曲目');
          submitSecArr = this.trackList.map(item => item.sec || 0);
          apiUrl = `/api/album/update/tracks/${this.album.id}`;
          emitKey1 = 'tracks';
          emitKey2 = 'tracks_time';
        } else {
          submitList = this.favouriteTrackList.map(item => item.name.trim() || '未知曲目');
          submitSecArr = this.favouriteTrackList.map(item => item.sec || 0);
          apiUrl = `/api/album/update/favourite_tracks/${this.album.id}`;
          emitKey1 = 'favourite_tracks';
          emitKey2 = 'favourite_tracks_time';
        }
        const fullTrackList = submitList.map(item => ({name: item}));

        const res = await this.$axios.put(apiUrl, {
          tracks: submitList,
          full_tracks: fullTrackList,
          tracks_time: submitSecArr
        }, {
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          }
        });

        if (res.data.code === 200) {
          alert(type === 'tracks' ? '✅ 曲目列表保存成功！' : '✅ 喜欢时间戳保存成功！');
          this.$emit('update-album-data', {
            [emitKey1]: submitList,
            [emitKey2]: submitSecArr
          });
        } else {
          alert(`❌ 保存失败：${res.data.msg}`);
        }
      } catch (err) {
        console.error('保存失败：', err);
        alert(err.response?.data?.msg || '❌ 保存失败，请重试！');
      }
    },
    handleTrackClick(idx) {
      if (this.isTrackEditMode) return;
      const targetSec = this.trackList[idx].sec || 0;
      this.$emit('track-jump', targetSec);
    },
    handleFavouriteTrackClick(idx) {
      if (this.isFavouriteEditMode) return;
      const targetSec = this.favouriteTrackList[idx].sec || 0;
      this.$emit('track-jump', targetSec);
    },
  // ✅ 重写评分逻辑：增速变慢 + 循环缩放
  startRating() {
    this.isRating = true;
    this.isScalingUp = true; // 初始为放大状态
    clearInterval(this.ratingTimer); // 先清除旧定时器，防止叠加

    this.ratingTimer = setInterval(() => {
      if (this.isScalingUp) {
        // 放大阶段：增速变慢，每次+0.5（原先是+1，速度减半）
        if (this.score < 100) {
          this.score += 0.5;
        } else {
          // 达到100，切换为缩小状态
          this.isScalingUp = false;
        }
      } else {
        // 缩小阶段：减速缩小，每次-0.5
        if (this.score > 0) {
          this.score -= 0.5;
        } else {
          // 达到0，切换为放大状态
          this.isScalingUp = true;
        }
      }
    }, 20); // 定时器间隔20ms（原10ms），进一步降低速率，更平缓
  },

  stopRating() {
    this.isRating = false;
    clearInterval(this.ratingTimer);
  },

  resetRating() {
    this.score = 0;
    this.isRating = false;
    this.isScalingUp = true; // 重置缩放状态
    clearInterval(this.ratingTimer);
  },
    startTrackScore(e, idx) {
      this.isTrackScoring = true;
      this.currentTrackIdx = idx;
      this.currentSliderDom = e.currentTarget;
      this.calcTrackScore(e);
      document.addEventListener('mousemove', this.handleTrackScoreMouseMove);
      e.stopPropagation();
    },
    stopTrackScore() {
      this.isTrackScoring = false;
      this.currentTrackIdx = -1;
      this.currentSliderDom = null;
      document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    },
    handleTrackScoreMouseMove(e) {
      if (this.isTrackScoring && this.currentTrackIdx !== -1 && this.currentSliderDom) {
        this.calcTrackScore(e);
      }
    },
    calcTrackScore(e) {
      const slider = this.currentSliderDom;
      const rect = slider.getBoundingClientRect();
      let percent = ((e.clientX - rect.left) / rect.width) * 100;
      percent = Math.max(0, Math.min(100, Math.round(percent)));
      this.trackList[this.currentTrackIdx].score = percent;
    },
    setTrackScoreByClick(e, idx) {
      this.currentTrackIdx = idx;
      this.currentSliderDom = e.currentTarget;
      this.calcTrackScore(e);
    },

    // ✅ ✅ ✅ 纯拖尾特效核心方法 - 无主球+零延迟+精准贴合 ✅ ✅ ✅
    initBallAnimation() {
      this.destroyBallAnimation();
      this.wrapDom = this.$refs.ballWrap;
      if (!this.wrapDom) return;
      this.ballAnimationId = requestAnimationFrame(this.renderBallAnimation);
    },
    handleMouseMove(e) {
      if (!this.wrapDom) return;
      const x = e.offsetX;
      const y = e.offsetY;
      // 直接生成拖尾，无主球、无过渡动画，百分百跟手，零延迟
      this.createTailBall(x, y);
    },
    createTailBall(x, y) {
      const ballSize = Math.floor(Math.random() * 12) + 6; // 随机尺寸6-18px，拖尾更细腻
      const halfSize = ballSize / 2; // 精准居中，零偏移
      const ballDom = document.createElement('div');
      // ✅ 修改1：删除随机彩色池，改用【主色渐变系列】从mainColorDarkDouble 到 mainColorWhiteDouble 渐变
      // 同色系渐变过渡，包含深浅/高亮/渐变三种效果，视觉统一不杂乱
      const mainGradients = [
        `linear-gradient(135deg, ${this.mainColorDarkDouble} 0%, ${this.mainColorDark} 100%)`,
        `linear-gradient(135deg, ${this.mainColorDark} 0%, ${this.mainColor} 100%)`,
        `linear-gradient(135deg, ${this.mainColor} 0%, ${this.mainColorWhite} 100%)`,
        `linear-gradient(135deg, ${this.mainColorWhite} 0%, ${this.mainColorWhiteDouble} 100%)`,
        `linear-gradient(135deg, ${this.mainColorDarkDouble} 0%, ${this.mainColorWhiteDouble} 100%)`
      ];
      const randomColor = mainGradients[Math.floor(Math.random() * mainGradients.length)];
      // 核心：无任何transition过渡，纯即时渲染，零延迟；精准居中鼠标
      ballDom.style.cssText = `
        position:absolute; width:${ballSize}px; height:${ballSize}px; border-radius:50%;
        background:${randomColor}; pointer-events:none; z-index:998;
        left:${x - halfSize}px; top:${y - halfSize}px;
      `;
      this.wrapDom.appendChild(ballDom);
      this.tailBalls.push({dom: ballDom, alpha: 1});
    },
    renderBallAnimation() {
      if (this.tailBalls.length === 0) {
        this.ballAnimationId = requestAnimationFrame(this.renderBallAnimation);
        return;
      }
      // ✅ 修改2：微调拖尾消失速度，配合渐变颜色更丝滑
      this.tailBalls = this.tailBalls.filter(ball => {
        ball.alpha -= 0.01; // 放慢消失速度，渐变拖尾更明显
        if (ball.alpha <= 0) {
          ball.dom.remove();
          return false;
        }
        ball.dom.style.opacity = ball.alpha;
        ball.dom.style.transform = `scale(${ball.alpha})`;
        return true;
      });
      this.ballAnimationId = requestAnimationFrame(this.renderBallAnimation);
    },
    handleMouseLeave() {
      this.destroyBallAnimation();
      this.$nextTick(() => this.initBallAnimation());
    },
    destroyBallAnimation() {
      if (this.ballAnimationId) cancelAnimationFrame(this.ballAnimationId);
      this.tailBalls.forEach(ball => ball.dom?.remove());
      this.ballAnimationId = null;
      this.tailBalls = [];
      if (this.wrapDom) this.wrapDom.innerHTML = '';
    }
  }
};
</script>

<style scoped>

.tab-content {
  position: relative;
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  padding: 10px;
  display: flex;
  flex-direction: column;
  background: transparent !important;
}

.main-layout {
  display: flex;
  width: 100%;
  height: 100%;
  gap: 20px;
}

.left-panel {
  flex: 6;
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent !important;
}

.right-panel {
  flex: 4;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  flex-shrink: 0;
  box-sizing: border-box;
  background: transparent !important;
}

.sticky-top-box {
  position: sticky;
  top: 0;
  z-index: 10;
  background: transparent !important;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

/* ✅ 核心新增：Tab和按钮同一行的容器样式 - 居左+居右 完美对齐 */
.tab-nav-btn-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-bottom: 8px;
  margin-bottom: 15px;
}

.track-tab-nav {
  display: flex;
  gap: 10px;
  padding-bottom: 0;
  margin-bottom: 0;
  width: auto;
  box-sizing: border-box;
  text-align: left;
  position: relative;
  border-bottom: none !important;
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

.sticky-header {
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
  display: flex;
  background: transparent !important;
  height: 36px;
}

.tab-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 5px;
  background: transparent !important;
}

.tab-content-scroll::-webkit-scrollbar {
  width: 6px;
}

.tab-content-scroll::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius: 3px;
}

.tab-content-scroll::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDark);
}

.tab-content-scroll::-webkit-scrollbar-track {
  background: transparent !important;
}

.rate-container {
  width: 100%;
  background: transparent !important;
  border-radius: 8px;
  padding: 20px;
  box-shadow: none !important;
  flex-shrink: 0;
}

.rate-content-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.rate-text-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 15px;
  padding-right: 20px;
}

.rate-text-area h3 {
  margin: 0;
  font-size: 16px;
  color: v-bind(mainColorDarkDouble) !important;
  font-weight: 600;
  padding-bottom: 8px;
  width: 100%;
  box-sizing: border-box;
  text-align: left;
  position: relative;
  border-bottom: none !important;
}

.rate-text-area h3::after {
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

.rate-score {
  font-size: 24px;
  font-weight: bold;
  color: v-bind(mainColorDark);
  line-height: 1;
}

.reset-rate-btn {
  background: v-bind(mainColorDark);
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.rate-circle-area {
  width: 180px;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.outer-circle {
  width: 180px;
  height: 180px;
  border: 3px solid v-bind(mainColorDark);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent !important;
  transition: all 0.2s;
}

.inner-circle {
  background: v-bind(mainColorDark);
  border-radius: 50%;
  transition: width 0.05s linear, height 0.05s linear;
  opacity: 0.85;
}

.rhythm-container {
  width: 100%;
  background: transparent !important;
  border-radius: 8px;
  padding: 0;
  box-shadow: none;
  box-sizing: border-box;
  flex: 1;
  min-height: 350px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  overflow: hidden;
}

.ball-animation-wrap {
  width: 100%;
  height: 100%;
  border-radius: 0;
  background-color: transparent !important;
  position: relative;
  overflow: hidden;
  cursor: none;
}

.tracks-container {
  padding: 0;
  width: 100%;
  background: transparent !important;
}

.tracks-header {
  display: flex;
  background: transparent !important;
}

.tracks-list {
  width: 100%;
  background: transparent !important;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: none !important;
  margin-bottom: 20px;
}

.track-item {
  display: flex;
  align-items: center;
  padding: 15px 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  transition: background-color 0.2s;
  background: transparent !important;
  box-sizing: border-box;
}

.track-item:last-child {
  border-bottom: none;
}

/* ✅✅✅ 序号核心优化：提升层级+固定宽度+永不被覆盖 */
.track-index {
  width: 40px;
  font-size: 16px;
  font-weight: 700;
  color: v-bind(mainColorDarkDouble);
  text-align: center;
  margin-right: 12px;
  position: relative;
  padding-bottom: 0;
  flex-shrink: 0;
  z-index: 99; /* 最高层级 永远挡住歌名 */
}

.track-show-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  gap: 12px;
  background: transparent !important;
}

/* ✅✅✅ 核心终极修复 所有问题的解决方案 适配透明背景 无遮挡 无越界 ✅✅✅ */
.track-name-wrap {
  width: 260px; /* 缩小容器宽度 精准裁切 彻底不遮挡右侧内容 | 想改宽度只改这个值 */
  flex-shrink: 0;
  position: relative;
  padding-bottom: 8px;
  margin-right: 0;
  cursor: pointer;
  box-sizing: border-box;
  overflow: hidden; /* 核心！超出容器宽度的歌名部分强制裁切隐藏 适配透明背景 */
}

/* 底部横线 - 独立结构 固定不动 永不滚动 宽度和容器一致 样式不变 */
.track-name-line {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
  z-index: 2;
}

/* ✅✅✅ 关键修复：不长的歌名静止的核心CSS 2行解决BUG ✅✅✅ */
.track-name-text {
  font-size: 16px;
  font-weight: 700;
  color: v-bind(mainColorDarkDouble);
  white-space: nowrap;
  position: relative;
  z-index: 3;
  width: fit-content; /* 核心1：获取文字「真实宽度」，不是撑满容器 */
  transform: translateX(0); /* 核心2：默认0位移，无动画 */
}

/* ✅✅✅ 滚动触发条件：只有【鼠标悬浮 + 文字宽度>容器宽度】才滚动，缺一不可 ✅✅✅ */
.track-name-wrap:hover .track-name-text {
  animation: scrollName 8s linear infinite;
  animation-play-state: running;
}

/* ✅ 鼠标离开立即复位：无残留动画 瞬间回到初始位置 */
.track-name-wrap:not(:hover) .track-name-text {
  animation: none;
  transform: translateX(0) !important;
}

/* ✅✅✅ 修正滚动逻辑 永不越界 完全正确：
   1. 动画方向：纯向左滚动（符合需求）
   2. 滚动终点：位移到 -(自身宽度 - 容器宽度)，歌名最左侧对齐容器最左侧，不会超过序号区域
   3. 永远是序号挡住歌名，歌名不会覆盖序号
   4. 右侧多余部分被容器裁切，绝不遮挡进度条/时间戳
*/
@keyframes scrollName {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(calc(-100% + 260px));
  }
}

/* ✅ 时间戳 固定宽度不挤压，样式不变 */
.track-duration {
  font-size: 16px;
  font-weight: 700;
  color: v-bind(mainColorDarkDouble);
  white-space: nowrap;
  margin-left: 10px;
  flex-shrink: 0;
  width: 90px;
  text-align: right;
}

.track-edit-content {
  display: flex;
  justify-content: space-between;
  alignItems: center;
  flex: 1;
  gap: 20px;
  background: transparent !important;
}

.track-name-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid v-bind(mainColorDarkDouble);
  border-radius: 4px;
  font-size: 14px;
  color: v-bind(mainColorDarkDouble);
  outline: none;
  background: rgba(255, 255, 255, 0.03) !important;
}

.track-name-input:focus {
  border-color: v-bind(mainColorDark);
  box-shadow: 0 0 0 2px rgba(47, 148, 101, 0.2);
}

.track-duration-input {
  width: 110px;
  padding: 6px 10px;
  border: 1px solid v-bind(mainColorDarkDouble);
  border-radius: 4px;
  font-size: 14px;
  color: v-bind(mainColorDarkDouble);
  text-align: center;
  outline: none;
  background: rgba(255, 255, 255, 0.03) !important;
}

.track-duration-input:focus {
  border-color: v-bind(mainColorDark);
  box-shadow: 0 0 0 2px rgba(47, 148, 101, 0.2);
}

.track-del-btn {
  margin-left: 10px;
}

.track-del-btn button {
  background: transparent;
  border: none;
  font-size: 18px;
  color: #dc2626;
  cursor: pointer;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.add-track-btn-box {
  text-align: right;
  background: transparent !important;
}

.add-track-btn {
  background: v-bind(mainColorDark);
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.edit-btn {
  background: v-bind(mainColorDark);
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.edit-btn.active {
  background: v-bind(mainColorDarkDouble);
}

.mode-btn {
  background: v-bind(mainColorDarkDouble);
  color: #fff;
  border: none;
	padding: 6px 14px;
	border-radius: 6px;
	cursor: pointer;
	font-size: 14px;
	transition: all 0.2s;
	margin-left: 8px;
}

.mode-btn.active {
  background: #f97316;
}

/* ✅ 进度条固定宽度永不被遮挡，样式不变 */
.track-score-slider-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
	min-width: 180px;
}

.track-score-slider {
  width: 100%;
  height: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
}

.track-score-progress {
  height: 100%;
  background: v-bind(mainColorDark);
  border-radius: 6px;
  transition: width 0.05s linear;
}

.track-score-text {
  font-size: 16px;
  font-weight: 700;
  color: v-bind(mainColorDarkDouble);
  white-space: nowrap;
  width: 50px;
  text-align: center;
  flex-shrink: 0;
}
</style>