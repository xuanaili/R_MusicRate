<template>
  <div class="root-container">
    <div class="tab-content">
      <div class="main-layout">
        <div class="left-panel">
          <div class="sticky-top-box">
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
                  喜欢时刻
                </div>
              </div>
              <div class="tracks-header sticky-header">
                <div class="tracks-action-btn">
                  <button
                    class="edit-btn"
                    @click="toggleEditStatus(activeTab)"
                    :class="{active: activeTab === 'tracks' ? isTrackEditMode : isFavouriteEditMode}"
                  >
                    {{ activeTab === 'tracks'
                      ? (isTrackEditMode ? '保存' : '编辑')
                      : (isFavouriteEditMode ? '保存' : '编辑')
                    }}
                  </button>
                  <button
                    v-if="activeTab === 'tracks' && isTrackEditMode"
                    class="mode-btn"
                    @click="toggleDurationMode"
                    :class="{active: isDurationMode}"
                    style="margin-left: 8px;"
                  >
                    {{ isDurationMode ? '切换为时间戳' : '切换为时长' }}
                  </button>
                  <button
                    v-if="activeTab === 'tracks' && isTrackEditMode"
                    class="mode-btn"
                    @click="showParseModal = true"
                    style="margin-left: 8px;"
                  >
                    文本解析
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="tab-content-scroll">
            <div class="tracks-container" v-show="activeTab === 'tracks'">
              <div class="tracks-list">
                <div
                  v-for="(track, idx) in trackList"
                  :key="idx"
                  class="track-item"
                >
                  <div class="track-index">{{ idx + 1 }}.</div>
                  <div v-if="isTrackEditMode" class="track-edit-content">
                    <input
                      type="text"
                      v-model="track.name"
                      placeholder="请输入曲目名称"
                      class="track-name-input"
                    />
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
                    <div class="track-name-wrap" @click="handleTrackClick(idx)">
                      <div class="track-name-text">{{ track.name || '未知曲目' }}</div>
                      <div class="track-name-line"></div>
                    </div>
                    <!-- ✨ 新增：添加滚轮事件监听 -->
                    <div class="track-score-slider-wrap"
                         @click.stop @mousedown.stop @mouseup.stop @mouseleave.stop
                         @wheel.prevent="handleTrackScoreWheel($event, idx)">
                      <div
                        class="track-score-slider"
                        ref="scoreSlider"
                        @mousedown="(e) => startTrackScore(e, idx)"
                        @mouseup="stopTrackScore"
                        @mouseleave="stopTrackScore"
                        @click="(e) => setTrackScoreByClick(e, idx)"
                      >
                        <div
                          class="track-score-progress"
                          :style="{ width: `${track.score || 0}%` }"
                        ></div>
                      </div>
                      <span class="track-score-text">{{ track.score || 0 }}分</span>
                    </div>
                    <div class="track-duration" @click="handleTrackClick(idx)">{{ track.duration || '0:00:00' }}</div>
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
        <div class="right-panel">
          <div class="rate-container">
            <div class="rate-content-wrap">
              <div class="rate-text-area">
                <h3>整体感觉</h3>
                <div class="rate-score">{{ score.toFixed(1) }} 分</div>
                <button class="reset-rate-btn" @click="resetRating">重置评分</button>
              </div>
              <div class="rate-circle-area">
                <div class="outer-circle"
                     @mouseenter="enterRatingArea"
                     @mouseleave="leaveRatingArea"
                     @wheel.prevent="handleRatingWheel"
                     @click="handleRatingClick"
                >
                  <div class="inner-circle" :style="{ width: `${score}%`, height: `${score}%` }"></div>
                </div>
              </div>
            </div>
          </div>
          <!-- 引入节奏小球子组件 -->
          <RhythmBall
            :album="album"
            :isMusicPlaying="isMusicPlaying"
            :mainColorDark="mainColorDark"
            :mainColorDarkDouble="mainColorDarkDouble"


            :initialBallConfig="currentBallConfig"
            @toggle-ball-play="handleBallPlayToggle"
            @toggle-meteor-play="handleMeteorPlayToggle"
            @generate-meteor="handleGenerateMeteor"

            @update-rhy-config="$emit('update-rhy-config', $event);"

          />
        </div>
      </div>
    </div>
    <TrackParse
      :visible="showParseModal"
      :mainColorDark="mainColorDark"
      :mainColorDarkDouble="mainColorDarkDouble"
      @close="showParseModal = false"
      @parse-success="handleParseSuccess"
    />
  </div>
</template>

<script>
import globalConfig from '@/config/index.js';
import TrackParse from '@/components/sidebar/TrackParse.vue';
// 引入节奏小球子组件
import RhythmBall from '@/components/RhythmBall.vue';

export default {
  name: 'AlbumTrackList',
  components: {TrackParse, RhythmBall},
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    tracks: {type: Array, default: () => []},
    tracksTime: {type: Array, default: () => []},
    favourite_tracks: {type: Array, default: () => []},
    favourite_tracks_time: {type: Array, default: () => []},
    mainColor: {type: String, required: true, default: '#42b983'},
    mainColorDark: {type: String, required: true, default: '#2f9465'},
    mainColorDarkDouble: {type: String, required: true, default: '#257d51'},
    mainColorWhite: {type: String, required: true, default: '#57c592'},
    mainColorWhiteDouble: {type: String, required: true, default: '#6cd1a1'},
    isMusicPlaying: {
      type: Boolean,
      required: true,
      default: true
    }
  },
  data() {
    return {
      activeTab: 'tracks',
      isTrackEditMode: false,
      isFavouriteEditMode: false,
      trackList: [],
      favouriteTrackList: [],
      score: 0,
      isTrackScoring: false,
      currentTrackIdx: -1,
      currentSliderDom: null,
      isDurationMode: false,
      showParseModal: false,
      // 仅保留小球配置传递给子组件
      currentBallConfig: globalConfig.ballConfig.default,
      isHoverRatingArea: false,
      isMeteorPlay: false, // 新增：流星播放状态
      // 评分防抖保存（v0.6 收尾）：打分隔评分也能落盘，不必等离开页面/切歌
      saveScoreTimer: null,
      pendingScoreSave: null, // { albumId, scoreList } 防抖期间快照，避免切歌写错专辑
      // 本地打分版本号：每次用户打分 +1；getAllScore 依据版本号判断
      // 请求期间是否已被用户继续打分，避免过期 GET 用旧值覆盖新分数
      scoreEditVersion: 0
    };
  },
  watch: {
    tracks: {handler() {this.initTrackList(true)}, deep: true},
    tracksTime: {handler() {this.initTrackList(true)}, deep: true},
    favourite_tracks: {handler() {this.initFavouriteTrackList()}, deep: true},
    favourite_tracks_time: {handler() {this.initFavouriteTrackList()}, deep: true},
    album: {
      handler(newVal, oldVal) {
        const oldId = oldVal && oldVal.id;
        const newId = newVal && newVal.id;
        // 仅当专辑切换（含经 id=0 的重置过渡）时才重置并重新拉取评分。
        // 同一专辑的深层变化（如保存评分后父组件同步 my_score）不重拉，
        // 否则 "保存→emit→my_score→重拉GET→旧值覆盖刚打的分数" 会把用户打分回退。
        // 同专辑内 tracks/favourite_tracks 的更新由对应 prop watcher 处理。
        if (oldId !== newId) {
          // 离开旧专辑（旧 id 有效）时先落盘待保存快照，避免写错专辑
          if (oldId) this.flushScoreSave();
          this.initTrackList(false);
          this.initFavouriteTrackList(false);
          this.getAllScore();
        }
        // 更新小球配置（传递给子组件）
        //this.currentBallConfig = this.getBallConfigByTag(newVal.tags);
      }, deep: true
    },
    isTrackEditMode(newVal) {if (!newVal) this.showParseModal = false;},
    activeTab(newVal) {
      this.showParseModal = false;
      this[newVal === 'tracks' ? 'isFavouriteEditMode' : 'isTrackEditMode'] = false;
    }
  },
  mounted() {
    this.initTrackList();
    this.initFavouriteTrackList();
    this.getAllScore();
    this.$nextTick(() => {
      //this.currentBallConfig = this.getBallConfigByTag(this.album.tags);
    });
  },
  activated() {
    this.initTrackList(true);
    this.initFavouriteTrackList();
    this.getAllScore();
    this.$nextTick(() => {
      //this.currentBallConfig = this.getBallConfigByTag(this.album.tags);
    });
  },
  deactivated() {
    this.saveAllScore();
  },
  beforeDestroy() {
    this.isTrackScoring = false;
    this.currentTrackIdx = -1;
    this.currentSliderDom = null;
    document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    this.saveAllScore();
  },
  methods: {
        // 新增：处理流星开关事件
    handleMeteorPlayToggle(isPlay) {
      this.isMeteorPlay = isPlay;
      this.$emit('toggle-meteor-play', isPlay);
    },

    // 新增：处理流星生成事件
    handleGenerateMeteor(meteorParams) {
      this.$emit('generate-meteor', meteorParams);
    },





    // ========== 评分防抖即时保存（v0.6 收尾） ==========
    // 构建当前评分数组：[专辑整体分, 单曲1分, 单曲2分, ...]
    buildScoreList() {
      const scoreList = [this.score];
      this.trackList.forEach(item => scoreList.push(item.score || 0));
      return scoreList;
    },
    // 打分时调用：防抖 800ms 保存；快照 albumId + scoreList，
    // 即使防抖期间切歌/离开页面，也能把评分写回正确的专辑
    scheduleScoreSave() {
      const albumId = this.album.id;
      if (!albumId) return;
      this.pendingScoreSave = {albumId, scoreList: this.buildScoreList()};
      if (this.saveScoreTimer) clearTimeout(this.saveScoreTimer);
      this.saveScoreTimer = setTimeout(() => {
        this.saveScoreTimer = null;
        const pending = this.pendingScoreSave;
        this.pendingScoreSave = null;
        if (pending) this.doScoreSave(pending.albumId, pending.scoreList);
      }, 800);
    },
    // 立即落盘待执行的防抖快照（切歌/离开页面前调用）
    flushScoreSave() {
      if (this.saveScoreTimer) {
        clearTimeout(this.saveScoreTimer);
        this.saveScoreTimer = null;
      }
      const pending = this.pendingScoreSave;
      this.pendingScoreSave = null;
      if (pending) this.doScoreSave(pending.albumId, pending.scoreList);
    },
    // 真正发请求的保存；仅保存的是当前专辑时才同步父组件展示，
    // 避免切歌后旧专辑快照污染新专辑的显示分数
    async doScoreSave(albumId, scoreList) {
      try {
        if (!albumId) return;
        if (albumId === this.album.id) {
          console.log('📤 AlbumTrackList 发射的scoreList：', scoreList);
          this.$emit('score-list-change', scoreList); // 发射给父组件
        }
        await this.$axios.put(`/api/album/score/save/${albumId}`, {score_list: scoreList}, {
          headers: {'Authorization': localStorage.getItem('token') || '', 'Content-Type': 'application/json'}
        });
        console.log('✅ 评分保存成功：', albumId, scoreList);
      } catch (err) {
        console.error('保存评分失败：', err);
      }
    },
    // AlbumTrackList 的 saveAllScore 方法（离开页面/切歌/保存曲目列表时调用）
    async saveAllScore() {
      const albumId = this.album.id;
      if (!albumId) return;

      // 1. 先落盘待执行的防抖快照（可能是切歌前的旧专辑评分）
      const pending = this.pendingScoreSave;
      if (this.saveScoreTimer) {
        clearTimeout(this.saveScoreTimer);
        this.saveScoreTimer = null;
        this.pendingScoreSave = null;
      }
      if (pending) {
        await this.doScoreSave(pending.albumId, pending.scoreList);
      }

      // 2. 保存当前最新状态；若与刚保存的快照一致则跳过，避免重复请求
      const scoreList = this.buildScoreList();
      if (pending && pending.albumId === albumId &&
          JSON.stringify(pending.scoreList) === JSON.stringify(scoreList)) {
        return;
      }
      await this.doScoreSave(albumId, scoreList);
    },
    async getAllScore() {
      try {
        const albumId = this.album.id;
        if (!albumId) return;
        const reqVersion = this.scoreEditVersion; // 发起请求时的本地打分版本号
        const res = await this.$axios.get(`/api/album/score/get/${albumId}`, {headers: {'Authorization': localStorage.getItem('token') || ''}});
        // 请求期间已切换专辑：丢弃过期响应，避免污染新专辑显示
        if (this.album.id !== albumId) return;
        // 请求期间用户已继续打分：丢弃过期 GET，避免旧值覆盖新分数
        if (this.scoreEditVersion !== reqVersion) return;
        if (res.data.code === 200 && res.data.data.score_list) {
          const scoreList = res.data.data.score_list;
          this.score = scoreList[0] || 0;
          this.trackList.forEach((item, idx) => item.score = scoreList[idx + 1] || 0);
        }
        console.log('✅ 评分读取成功：', albumId, this.score);
      } catch (err) {
        console.error('读取评分失败：', err);
      }
    },
    async triggerSaveScore() {
      await this.saveAllScore();
    },
    async triggerGetScore() {
      await this.getAllScore();
    },
    handleParseSuccess(newTrackList) {
      this.showParseModal = false;
      this.trackList = newTrackList;
      this.trackList.forEach((item, idx) => this.formatDurationInput('tracks', idx));
      this.isDurationMode && this.calcTrackTimestamp();
      this.$message?.success(`✅ 文本解析完成，已填充 ${newTrackList.length} 首曲目！`) || alert(`✅ 文本解析完成，已填充 ${newTrackList.length} 首曲目！`);
    },
    timeToSeconds(timeStr) {
      if (!timeStr) return 0;
      let timeArr = timeStr.split(':').map(Number).filter(n => !isNaN(n));
      let [hours = 0, minutes = 0, seconds = 0] = timeArr.length === 2 ? [0, ...timeArr] : timeArr;
      minutes = Math.min(Math.max(minutes, 0), 59);
      seconds = Math.min(Math.max(seconds, 0), 59);
      hours = Math.max(hours, 0);
      return hours * 3600 + minutes * 60 + seconds;
    },
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const total = Math.floor(seconds);
      const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = Math.floor(total % 60);
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      if (filterVal.split(':').length - 1 > 2) filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      return filterVal;
    },
    initTrackList(keepScore = false) {
      const oldScoreMap = keepScore ? this.trackList.reduce((m, i, idx) => (m[idx] = i.score || 0, m), {}) : {};
      this.trackList = [];
      const names = this.tracks || [], secs = this.tracksTime || [];
      names.forEach((name, idx) => {
        const dbSec = secs[idx] || 0;
        this.trackList.push({
          name: name.trim() || '未知曲目',
          sec: dbSec,
          duration: this.secondsToTime(dbSec),
          playDuration: '0:00:00',
          score: oldScoreMap[idx] || 0
        });
      });
      if (!names.length) this.trackList = [{
        name: '未知曲目',
        sec: 0,
        duration: '0:00:00',
        playDuration: '0:00:00',
        score: 0
      }];
    },
    // 修复initFavouriteTrackList方法，支持保留编辑后的数据
    initFavouriteTrackList(keepCurrentData = false) {
      // 如果标记为保留当前数据，且已有编辑后的列表，则不重置
      if (keepCurrentData && this.favouriteTrackList.length > 0) {
        return;
      }

      this.favouriteTrackList = [];
      const names = this.favourite_tracks || [], secs = this.favourite_tracks_time || [];
      names.forEach((name, idx) => {
        const dbSec = secs[idx] || 0;
        this.favouriteTrackList.push({
          name: name.trim() || '未知曲目',
          sec: dbSec,
          duration: this.secondsToTime(dbSec)
        });
      });
      if (!names.length) this.favouriteTrackList = [{name: '未知曲目', sec: 0, duration: '0:00:00'}];
    },
    // 优化saveTrackList方法的错误提示
    formatDurationInput(type, idx) {
      const list = type === 'tracks' ? this.trackList : this.favouriteTrackList;
      const track = list[idx];
      if (!track) return;
      track.sec = this.timeToSeconds(track.duration);
      track.duration = this.secondsToTime(track.sec);
    },
    toggleDurationMode() {
      this.isDurationMode = !this.isDurationMode;
      this.isDurationMode && this.trackList.forEach(item => item.playDuration = item.playDuration || '0:00:00');
    },
    handleDurationInputBlur(idx) {
      const track = this.trackList[idx];
      if (!track) return;
      track.playDuration = this.filterDurationInput(track.playDuration);
      const sec = this.timeToSeconds(track.playDuration);
      track.playDuration = this.secondsToTime(sec);
      this.calcTrackTimestamp();
    },
    calcTrackTimestamp() {
      let totalSec = 0;
      this.trackList.forEach((track, idx) => {
        idx === 0 && (totalSec = 0);
        track.duration = this.secondsToTime(totalSec);
        track.sec = totalSec;
        totalSec += this.timeToSeconds(track.playDuration);
      });
    },
    // 重点修复的方法
    async toggleEditStatus(type) {
      const key = type === 'tracks' ? 'isTrackEditMode' : 'isFavouriteEditMode';
      if (this[key]) {
        // 只执行对应类型的列表保存，完全分离逻辑
        await this.saveTrackList(type);
        // 只有「单曲列表」才需要保存评分，喜欢时刻不碰评分
        if (type === 'tracks') {
          await this.saveAllScore();
        } else {
          // 喜欢时刻保存后，刷新列表但不影响单曲评分
          this.initFavouriteTrackList(true);
        }
        this[key] = false;
        type === 'tracks' && (this.showParseModal = false);
      } else {
        this[key] = true;
      }
    },
    addNewTrack(type) {
      if (type === 'tracks') {
        this.trackList.push({name: '', duration: '0:00:00', sec: 0, playDuration: '0:00:00', score: 0});
        this.isDurationMode && this.calcTrackTimestamp();
      } else {
        this.favouriteTrackList.push({name: '', duration: '0:00:00', sec: 0});
      }
    },
    deleteTrack(type, idx) {
      const list = type === 'tracks' ? this.trackList : this.favouriteTrackList;
      if (list.length <= 1) return alert('至少保留1条哦！');
      list.splice(idx, 1);
      type === 'tracks' && this.isDurationMode && this.calcTrackTimestamp();
    },
    // 优化saveTrackList方法的错误提示
    async saveTrackList(type) {
      try {
        // 先校验album.id是否存在
        if (!this.album.id) {
          alert('❌ 保存失败：未找到专辑ID');
          return;
        }

        let submitList, submitSecArr, apiUrl, emitKey1, emitKey2;
        if (type === 'tracks') {
          submitList = this.trackList.map(i => i.name.trim() || '未知曲目');
          submitSecArr = this.trackList.map(i => i.sec || 0);
          apiUrl = `/api/album/update/tracks/${this.album.id}`;
          emitKey1 = 'tracks';
          emitKey2 = 'tracks_time';
        } else {
          submitList = this.favouriteTrackList.map(i => i.name.trim() || '未知曲目');
          submitSecArr = this.favouriteTrackList.map(i => i.sec || 0);
          apiUrl = `/api/album/update/favourite_tracks/${this.album.id}`;
          emitKey1 = 'favourite_tracks';
          emitKey2 = 'favourite_tracks_time';
        }

        const fullTrackList = submitList.map(n => ({name: n}));
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
          // 保存成功后立即更新父组件数据
          this.$emit('update-album-data', {[emitKey1]: submitList, [emitKey2]: submitSecArr});
        } else {
          alert(`❌ 保存失败：${res.data.msg || '服务器返回错误'}`);
        }
      } catch (err) {
        console.error('保存失败：', err);
        const errorMsg = err.response?.data?.msg ||
            (err.message.includes('401') ? '登录已过期，请重新登录' : '网络异常，请重试');
        alert(`❌ 保存失败：${errorMsg}`);
      }
    },
    handleTrackClick(idx) {
      !this.isTrackEditMode && this.$emit('track-jump', this.trackList[idx].sec || 0);
    },
    handleFavouriteTrackClick(idx) {
      !this.isFavouriteEditMode && this.$emit('track-jump', this.favouriteTrackList[idx].sec || 0);
    },
    resetRating() {
      this.score = 0;
      this.scoreEditVersion++; // 本地打分版本号递增
      this.scheduleScoreSave();
    },
    enterRatingArea() {
      this.isHoverRatingArea = true;
    },
    leaveRatingArea() {
      this.isHoverRatingArea = false;
    },
    handleRatingWheel(e) {
      if (!this.isHoverRatingArea) return;
      const delta = e.deltaY < 0 ? 0.5 : -0.5;
      this.score = Math.max(0, Math.min(100, this.score + delta));
      this.scoreEditVersion++; // 本地打分版本号递增
      this.scheduleScoreSave();
    },
    handleRatingClick(e) {
      const outerCircle = e.currentTarget;
      const rect = outerCircle.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const clickX = e.clientX;
      const clickY = e.clientY;
      const distance = Math.sqrt(Math.pow(clickX - centerX, 2) + Math.pow(clickY - centerY, 2));
      const radius = rect.width / 2;
      let percent = (distance / radius) * 100;
      percent = Math.max(0, Math.min(100, Math.round(percent * 2) / 2));
      this.score = percent;
      this.scoreEditVersion++; // 本地打分版本号递增
      this.scheduleScoreSave();
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
      this.isTrackScoring && this.currentTrackIdx !== -1 && this.currentSliderDom && this.calcTrackScore(e);
    },
    calcTrackScore(e) {
      const rect = this.currentSliderDom.getBoundingClientRect();
      let percent = ((e.clientX - rect.left) / rect.width) * 100;
      percent = Math.max(0, Math.min(100, Math.round(percent)));
      this.trackList[this.currentTrackIdx].score = percent;
      this.scoreEditVersion++; // 本地打分版本号递增（滑块拖拽/点击/滚轮共用）
      this.scheduleScoreSave();
    },
    setTrackScoreByClick(e, idx) {
      this.currentTrackIdx = idx;
      this.currentSliderDom = e.currentTarget;
      this.calcTrackScore(e);
    },
    // ✨ 新增：单曲评分滚轮微调方法
    handleTrackScoreWheel(e, idx) {
      // 滚轮向上（deltaY < 0）分数+1，向下（deltaY > 0）分数-1
      const step = e.deltaY < 0 ? 1 : -1;
      // 获取当前曲目分数
      let currentScore = this.trackList[idx].score || 0;
      // 计算新分数，限制在0-100范围内
      let newScore = Math.max(0, Math.min(100, currentScore + step));
      // 更新分数
      this.trackList[idx].score = newScore;
      this.scoreEditVersion++; // 本地打分版本号递增
      this.scheduleScoreSave();
    },
    // 获取小球配置（仅用于初始化传递给子组件）
    getBallConfigByTag(tags) {
      if (!tags || !Array.isArray(tags) || tags.length === 0) {
        return globalConfig.ballConfig.default;
      }
      const firstTag = tags[0];
      return globalConfig.ballConfig[firstTag] || globalConfig.ballConfig.default;
    },
    // 子组件事件处理方法
    handleBallPlayToggle(isPlay) {
      // 向父组件发射小球开关状态
      this.$emit('toggle-ball-play', isPlay);
    },
    handleBallConfigUpdate(newConfig) {
      // 更新父组件中的小球配置
      this.currentBallConfig = newConfig;
      // 向父组件的父组件发射配置更新事件
      this.$emit('update-ball-config', newConfig);
    },
    handleGenerateRhythmBall(ballInfo) {
      // 向父组件发射生成小球事件
      this.$emit('generate-rhythm-ball', ballInfo);
    }
  }
};
</script>

<style scoped>
.tab-content {
  position: relative;
  width: 100%;
  height: 90vh;
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
  padding-bottom: 8px;
  margin-bottom: 15px;
}

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

  &:hover {
    border-color: v-bind(mainColorWhite);
    transform: scale(1.02);
  }
}

.inner-circle {
  background: v-bind(mainColorDark);
  border-radius: 50%;
  transition: width 0.05s linear, height 0.05s linear;
  opacity: 0.85;
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
  z-index: 99;
}

.track-show-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  gap: 12px;
  background: transparent !important;
}

.track-name-wrap {
  width: 260px;
  flex-shrink: 0;
  position: relative;
  padding-bottom: 8px;
  margin-right: 0;
  cursor: pointer;
  box-sizing: border-box;
  overflow: hidden;
}

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

.track-name-text {
  font-size: 16px;
  font-weight: 700;
  color: v-bind(mainColorDarkDouble);
  white-space: nowrap;
  position: relative;
  z-index: 3;
  width: fit-content;
  transform: translateX(0);
}

.track-name-wrap:hover .track-name-text {
  animation: scrollName 8s linear infinite;
  animation-play-state: running;
}

.track-name-wrap:not(:hover) .track-name-text {
  animation: none;
  transform: translateX(0) !important;
}

@keyframes scrollName {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(calc(-100% + 260px));
  }
}

.track-duration {
  font-size: 16px;
  font-weight: 700;
  color: v-bind(mainColorDarkDouble);
  white-space: nowrap;
  margin-left: 10px;
  flex-shrink: 0;
  width: 90px;
  text-align: right;
  cursor: pointer;
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


.root-container {
  height: 88vh;
}
</style>