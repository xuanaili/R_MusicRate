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
        <div class="rhythm-container">
          <div class="ball-config-panel">
            <div class="ball-switch-wrap">
              <h3>节奏小球参数</h3>
              <div
                class="ball-toggle-switch"
                :class="{active: isBallPlay}"
                @click="toggleBallPlay"
              >
                <span>{{ isBallPlay ? '开启中' : '已关闭' }}</span>
              </div>
            </div>
            <div class="ball-config-list">
              <div class="config-item">
                <span class="config-label">最小尺寸</span>
                <div class="config-progress-vertical" @mousedown="(e) => startBallConfigDrag(e, 'minSize')" @click="(e) => setBallConfigByClick(e, 'minSize')">
                  <div class="progress-inner" :style="{height: `${getPercent('minSize')}%`}"></div>
                </div>
                <span class="config-value">{{ currentBallConfig.minSize }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">最大尺寸</span>
                <div class="config-progress-vertical" @mousedown="(e) => startBallConfigDrag(e, 'maxSize')" @click="(e) => setBallConfigByClick(e, 'maxSize')">
                  <div class="progress-inner" :style="{height: `${getPercent('maxSize')}%`}"></div>
                </div>
                <span class="config-value">{{ currentBallConfig.maxSize }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">最小速率</span>
                <div class="config-progress-vertical" @mousedown="(e) => startBallConfigDrag(e, 'minRate')" @click="(e) => setBallConfigByClick(e, 'minRate')">
                  <div class="progress-inner" :style="{height: `${getPercent('minRate')}%`}"></div>
                </div>
                <span class="config-value">{{ currentBallConfig.minRate }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">最大速率</span>
                <div class="config-progress-vertical" @mousedown="(e) => startBallConfigDrag(e, 'maxRate')" @click="(e) => setBallConfigByClick(e, 'maxRate')">
                  <div class="progress-inner" :style="{height: `${getPercent('maxRate')}%`}"></div>
                </div>
                <span class="config-value">{{ currentBallConfig.maxRate }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">数量权重</span>
                <div class="config-progress-vertical" @mousedown="(e) => startBallConfigDrag(e, 'numWeight')" @click="(e) => setBallConfigByClick(e, 'numWeight')">
                  <div class="progress-inner" :style="{height: `${getPercent('numWeight')}%`}"></div>
                </div>
                <span class="config-value">{{ currentBallConfig.numWeight }}</span>
              </div>
            </div>
          </div>
        </div>
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

export default {
  name: 'AlbumTrackList',
  components: {TrackParse},
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
      isBallPlay: false,
      currentBallConfig: globalConfig.ballConfig.default,
      isBallConfigDragging: false,
      currentConfigKey: '',
      autoBallTimer: null,
      isHoverRatingArea: false
    };
  },
  watch: {
    tracks: {handler() {this.initTrackList(true)}, deep: true},
    tracksTime: {handler() {this.initTrackList(true)}, deep: true},
    favourite_tracks: {handler() {this.initFavouriteTrackList()}, deep: true},
    favourite_tracks_time: {handler() {this.initFavouriteTrackList()}, deep: true},
    album: {
      handler(newVal, oldVal) {
        if (oldVal && oldVal.id && newVal && newVal.id && oldVal.id !== newVal.id) {
          this.saveAllScore();
        }
        this.initTrackList(true);
        this.initFavouriteTrackList();
        this.getAllScore();
        this.currentBallConfig = this.getBallConfigByTag(newVal.tags);
      }, deep: true
    },
    isTrackEditMode(newVal) {if (!newVal) this.showParseModal = false;},
    activeTab(newVal) {
      this.showParseModal = false;
      this[newVal === 'tracks' ? 'isFavouriteEditMode' : 'isTrackEditMode'] = false;
    },
    isMusicPlaying(newVal) {
      newVal && this.isBallPlay ? this.startAutoBallGenerate() : this.stopAutoBallGenerate();
    },
    isBallPlay(newVal) {
      this.$emit('toggle-ball-play', newVal);
      newVal && this.isMusicPlaying ? this.startAutoBallGenerate() : this.stopAutoBallGenerate();
    }
  },
  mounted() {
    this.initTrackList();
    this.initFavouriteTrackList();
    this.getAllScore();
    this.$nextTick(() => {
      this.currentBallConfig = this.getBallConfigByTag(this.album.tags);
      this.isMusicPlaying && this.isBallPlay && this.startAutoBallGenerate();
    });
  },
  activated() {
    this.initTrackList(true);
    this.initFavouriteTrackList();
    this.getAllScore();
    this.$nextTick(() => {
      this.currentBallConfig = this.getBallConfigByTag(this.album.tags);
      this.isMusicPlaying && this.isBallPlay && this.startAutoBallGenerate();
    });
  },
  deactivated() {
    this.saveAllScore();
    this.stopAutoBallGenerate();
  },
  beforeDestroy() {
    clearInterval(this.autoBallTimer);
    this.isTrackScoring = false;
    this.currentTrackIdx = -1;
    this.currentSliderDom = null;
    document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    document.removeEventListener('mousemove', this.handleBallConfigMouseMove);
    document.removeEventListener('mouseup', this.stopBallConfigDrag);
    this.saveAllScore();
    this.stopAutoBallGenerate();
  },
  methods: {
// AlbumTrackList 的 saveAllScore 方法
async saveAllScore() {
  try {
    const albumId = this.album.id;
    if (!albumId) return;
    let scoreList = [this.score];
    this.trackList.forEach(item => scoreList.push(item.score || 0));

    console.log('📤 AlbumTrackList 发射的scoreList：', scoreList);
    this.$emit('score-list-change', scoreList); // 发射给父组件

    await this.$axios.put(`/api/album/score/save/${albumId}`, {score_list: scoreList}, {
      headers: {'Authorization': localStorage.getItem('token') || '', 'Content-Type': 'application/json'}
    });
    console.log('✅ 评分保存成功：', albumId, scoreList);
  } catch (err) {
    console.error('保存评分失败：', err);
  }
},
    async getAllScore() {
      try {
        const albumId = this.album.id;
        if (!albumId) return;
        const res = await this.$axios.get(`/api/album/score/get/${albumId}`, {headers: {'Authorization': localStorage.getItem('token') || ''}});
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
    initFavouriteTrackList() {
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
    async toggleEditStatus(type) {
      const key = type === 'tracks' ? 'isTrackEditMode' : 'isFavouriteEditMode';
      if (this[key]) {
        await this.saveAllScore();
        await this.saveTrackList(type);
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
    async saveTrackList(type) {
      try {
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
          headers: {'Authorization': localStorage.getItem('token') || '', 'Content-Type': 'application/json'}
        });
        if (res.data.code === 200) {
          this.$emit('update-album-data', {[emitKey1]: submitList, [emitKey2]: submitSecArr});
        } else {
          alert(`❌ 保存失败：${res.data.msg}`);
        }
      } catch (err) {
        console.error('保存失败：', err);
        alert(err.response?.data?.msg || '❌ 保存失败，请重试！');
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
    },
    getBallConfigByTag(tags) {
      if (!tags || !Array.isArray(tags) || tags.length === 0) {
        return globalConfig.ballConfig.default;
      }
      const firstTag = tags[0];
      return globalConfig.ballConfig[firstTag] || globalConfig.ballConfig.default;
    },
    toggleBallPlay() {
      this.isBallPlay = !this.isBallPlay;
    },
    getPercent(key) {
      const config = this.currentBallConfig;
      let val = config[key];
      let max, min;
      switch (key) {
        case 'minSize':
          min = 0;
          max = 1000;
          break;
        case 'maxSize':
          min = 0;
          max = 1000;
          break;
        case 'minRate':
          min = 10;
          max = 4000;
          break;
        case 'maxRate':
          min = 10;
          max = 4000;
          break;
        case 'numWeight':
          min = 0;
          max = 10;
          break;
        default:
          return 0;
      }
      const percent = ((val - min) / (max - min)) * 100;
      return Math.max(0, Math.min(100, percent));
    },
    startBallConfigDrag(e, key) {
      this.isBallConfigDragging = true;
      this.currentConfigKey = key;
      this.calcBallConfigValueByMouse(e, key);
      document.addEventListener('mousemove', this.handleBallConfigMouseMove);
      document.addEventListener('mouseup', this.stopBallConfigDrag);
      e.stopPropagation();
      e.preventDefault();
    },
    handleBallConfigMouseMove(e) {
      if (this.isBallConfigDragging && this.currentConfigKey) {
        this.calcBallConfigValueByMouse(e, this.currentConfigKey);
      }
    },
    stopBallConfigDrag() {
      this.isBallConfigDragging = false;
      this.currentConfigKey = '';
      document.removeEventListener('mousemove', this.handleBallConfigMouseMove);
      document.removeEventListener('mouseup', this.stopBallConfigDrag);
    },
    calcBallConfigValueByMouse(e, key) {
      const progressDom = e.currentTarget.querySelector('.progress-inner').parentNode;
      const rect = progressDom.getBoundingClientRect();
      let percent = ((rect.bottom - e.clientY) / rect.height) * 100;
      percent = Math.max(0, Math.min(100, percent));
      this.setBallConfigValueByPercent(key, percent);
    },
    setBallConfigValueByPercent(key, percent) {
      let min, max, step = 1;
      switch (key) {
        case 'minSize':
          min = 0;
          max = 1000;
          step = 1;
          break;
        case 'maxSize':
          min = 0;
          max = 1000;
          step = 1;
          break;
        case 'minRate':
          min = 10;
          max = 4000;
          step = 10;
          break;
        case 'maxRate':
          min = 10;
          max = 4000;
          step = 10;
          break;
        case 'numWeight':
          min = 0;
          max = 10;
          step = 1;
          break;
        default:
          return;
      }
      let realValue = ((max - min) * (percent / 100)) + min;
      realValue = Math.round(realValue / step) * step;
      realValue = Math.max(min, Math.min(max, realValue));
      this.currentBallConfig[key] = realValue;
      this.$emit('update-ball-config', {...this.currentBallConfig});
    },
    setBallConfigByClick(e, key) {
      this.currentConfigKey = key;
      this.calcBallConfigValueByMouse(e, key);
    },
    startAutoBallGenerate() {
      if (!this.isBallPlay) return;
      const {minRate, maxRate, numWeight} = this.currentBallConfig;
      this.autoBallTimer = setInterval(() => {
        if (!this.isBallPlay || !this.isMusicPlaying) return;
        for (let i = 0; i < numWeight; i++) {
          const size = Math.floor(Math.random() * (this.currentBallConfig.maxSize - this.currentBallConfig.minSize)) + this.currentBallConfig.minSize;
          this.$emit('generate-rhythm-ball', {size});
        }
      }, Math.floor(Math.random() * (maxRate - minRate)) + minRate);
    },
    stopAutoBallGenerate() {
      this.autoBallTimer && (clearInterval(this.autoBallTimer), this.autoBallTimer = null);
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

.rhythm-container {
  width: 100%;
  background: transparent !important;
  border-radius: 8px;
  padding: 20px;
  box-shadow: none;
  box-sizing: border-box;
  flex: 1;
  min-height: 350px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.ball-config-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.ball-switch-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.ball-switch-wrap h3 {
  margin: 0;
  font-size: 16px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 4px solid v-bind(mainColorDark);
}

.ball-toggle-switch {
  padding: 6px 14px;
  border-radius: 6px;
  background: #94a3b8;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.ball-toggle-switch.active {
  background: v-bind(mainColorDark);
}

.ball-config-list {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  width: 100%;
  height: calc(100% - 150px);
  gap: 8px;
}

.config-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.config-label {
  font-size: 12px;
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
  white-space: nowrap;
}

.config-value {
  font-size: 13px;
  color: v-bind(mainColorDark);
  font-weight: bold;
}

.config-progress-vertical {
  width: 8px;
  height: 220px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  flex-direction: column-reverse;
  cursor: pointer;
}

.progress-inner {
  width: 100%;
  background: v-bind(mainColorDark);
  border-radius: 4px;
  transition: height 0.3s ease;
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
</style>