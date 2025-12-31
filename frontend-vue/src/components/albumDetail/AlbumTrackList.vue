<template>
  <div class="tab-content">
    <!-- ✅ 整体弹性布局：左60% 列表区 + 右40% 评分+节奏组件区 完全自适应 -->
    <div class="main-layout">
      <!-- 左侧：弹性60% 区域 - Tab+编辑按钮 全部置顶固定 + 列表内容自适应滚动 -->
      <div class="left-panel">
        <!-- ✅ 核心：【Tab导航+编辑按钮】整体置顶固定，永不滚动 -->
        <div class="sticky-top-box">
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

          <!-- ✅ 编辑按钮和Tab联动，置顶固定 -->
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
            </div>
          </div>
        </div>

        <!-- ✅ 核心：列表内容区 自适应滚动，只有这里滚动，顶部内容完全不动 -->
        <div class="tab-content-scroll">
          <div class="tracks-container" v-show="activeTab === 'tracks'">
            <h3>单曲列表</h3>
            <div class="tracks-list">
              <div
                v-for="(track, idx) in trackList"
                :key="idx"
                class="track-item"
                @click="handleTrackClick(idx)"
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
                    type="text"
                    v-model="track.duration"
                    placeholder="0:00:00"
                    class="track-duration-input"
                    maxlength="8"
                    @input="track.duration = filterDurationInput(track.duration)"
                    @blur="formatDurationInput('tracks', idx)"
                  />
                </div>

                <div v-else class="track-show-content">
                  <div class="track-name" style="cursor: pointer;">{{ track.name || '未知曲目' }}</div>
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
            <h3>喜欢时间戳</h3>
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
                  <div class="track-name" style="cursor: pointer;">{{ track.name || '未知曲目' }}</div>
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

      <!-- ✅ 右侧：弹性40% 上=评分组件(左文右图) | 下=节奏组件【自适应固定位置】 -->
      <div class="right-panel">
        <!-- 上半部分：个人感觉评分组件 - 左侧标题分数按钮 + 右侧评分圆【修复后正常显示】 -->
        <div class="rate-container">
          <div class="rate-content-wrap">
            <!-- 左侧：标题 + 分数 + 重置按钮 -->
            <div class="rate-text-area">
              <h3>个人感觉评分 (0-100)</h3>
              <div class="rate-score">{{ score }} 分</div>
              <button class="reset-rate-btn" @click="resetRating">🔄 重置评分</button>
            </div>
            <!-- 右侧：评分圆 【修复核心区，圆形正常显示】 -->
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

        <!-- 下半部分：节奏小组件 占位区【自适应占满剩余高度，永不移位】 -->
        <div class="rhythm-container">
          <h3>节奏可视化组件</h3>
          <div class="rhythm-placeholder">
            <p>🎵 节奏组件占位区域</p>
            <p>后续可在此处接入音频波形/频谱/节奏跳动等功能</p>
          </div>
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
    }
  },
  data() {
    return {
      activeTab: 'tracks', // tracks=单曲列表 favourite=喜欢时间戳
      isTrackEditMode: false, // 普通曲目编辑状态
      isFavouriteEditMode: false, // 喜欢时间戳编辑状态
      trackList: [], // 普通曲目数据 {name: '', duration: '', sec: 秒数}
      favouriteTrackList: [], // 收藏曲目数据 {name: '', duration: '', sec: 秒数}
      // 评分组件相关数据
      score: 0,        // 最终评分 0-100
      isRating: false, // 是否正在按压评分
      ratingTimer: null// 评分定时器
    };
  },
  watch: {
    // 普通曲目数据监听
    tracks: { handler() { this.initTrackList(); }, deep: true },
    tracksTime: { handler() { this.initTrackList(); }, deep: true },
    // 收藏曲目数据监听
    favourite_tracks: { handler() { this.initFavouriteTrackList(); }, deep: true },
    favourite_tracks_time: { handler() { this.initFavouriteTrackList(); }, deep: true }
  },
  mounted() {
    this.initTrackList();
    this.initFavouriteTrackList(); // 初始化收藏曲目
  },
  activated() {
    this.initTrackList();
    this.initFavouriteTrackList(); // 初始化收藏曲目
  },
  beforeDestroy() {
    // 销毁定时器，防止内存泄漏
    clearInterval(this.ratingTimer);
  },
  methods: {
    // 完整版：将 时分秒字符串(0:00:00 / 00:00) 转为 总秒数 - 支持任意小时数
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
    // 秒数转 0:00:00 格式
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const totalSeconds = Math.floor(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const sec = Math.floor(totalSeconds % 60);
      return `${hours}:${minutes.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
    // 过滤时长输入框的内容，只允许输入 数字 和 冒号，冒号最多2个
    filterDurationInput(val) {
      if (!val) return '';
      let filterVal = val.replace(/[^0-9:]/g, '');
      const colonCount = filterVal.split(':').length - 1;
      if (colonCount > 2) {
        filterVal = filterVal.substring(0, filterVal.lastIndexOf(':'));
      }
      return filterVal;
    },
    // 初始化普通曲目列表
    initTrackList() {
      this.trackList = [];
      const trackNames = Array.isArray(this.tracks) && this.tracks.length > 0 ? this.tracks : [];
      const trackSecs = Array.isArray(this.tracksTime) && this.tracksTime.length > 0 ? this.tracksTime : [];
      if (trackNames.length > 0) {
        trackNames.forEach((name, idx) => {
          const dbSec = trackSecs[idx] || 0;
          this.trackList.push({
            name: name.trim() || '未知曲目',
            sec: dbSec,
            duration: this.secondsToTime(dbSec)
          });
        });
      } else {
        this.trackList = [{name: '未知曲目', sec: 0, duration: '0:00:00'}];
      }
    },
    // 初始化收藏曲目/喜欢时间戳列表
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
    // 格式化时长输入框数据
    formatDurationInput(type, idx) {
      if(type === 'tracks'){
        const track = this.trackList[idx];
        if (!track) return;
        track.sec = this.timeToSeconds(track.duration);
        track.duration = this.secondsToTime(track.sec);
      }else{
        const track = this.favouriteTrackList[idx];
        if (!track) return;
        track.sec = this.timeToSeconds(track.duration);
        track.duration = this.secondsToTime(track.sec);
      }
    },
    // 切换编辑状态
    async toggleEditStatus(type) {
      if(type === 'tracks'){
        if (this.isTrackEditMode) {
          await this.saveTrackList('tracks');
          this.isTrackEditMode = false;
        } else {
          this.isTrackEditMode = true;
        }
      }else{
        if (this.isFavouriteEditMode) {
          await this.saveTrackList('favourite');
          this.isFavouriteEditMode = false;
        } else {
          this.isFavouriteEditMode = true;
        }
      }
    },
    // 添加新曲目/新时间戳
    addNewTrack(type) {
      if(type === 'tracks'){
        this.trackList.push({name: '', duration: '0:00:00', sec: 0});
      }else{
        this.favouriteTrackList.push({name: '', duration: '0:00:00', sec: 0});
      }
    },
    // 删除曲目/时间戳
    deleteTrack(type, idx) {
      let targetList = type === 'tracks' ? this.trackList : this.favouriteTrackList;
      if (targetList.length <= 1) {
        alert('至少保留1条哦！');
        return;
      }
      targetList.splice(idx, 1);
    },
    // 核心修改：统一保存方法，区分调用【普通曲目接口】和【收藏曲目接口】
    async saveTrackList(type) {
      try {
        let submitList, submitSecArr, apiUrl, emitKey1, emitKey2;
        // 区分保存类型
        if(type === 'tracks'){
          // 普通曲目 - 调用原接口
          submitList = this.trackList.map(item => item.name.trim() || '未知曲目');
          submitSecArr = this.trackList.map(item => item.sec || 0);
          apiUrl = `/api/album/update/tracks/${this.album.id}`;
          emitKey1 = 'tracks';
          emitKey2 = 'tracks_time';
        }else{
          // 喜欢时间戳 - 调用你修改好的收藏接口
          submitList = this.favouriteTrackList.map(item => item.name.trim() || '未知曲目');
          submitSecArr = this.favouriteTrackList.map(item => item.sec || 0);
          apiUrl = `/api/album/update/favourite_tracks/${this.album.id}`;
          emitKey1 = 'favourite_tracks';
          emitKey2 = 'favourite_tracks_time';
        }
        const fullTrackList = submitList.map(item => ({ name: item }));

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
    // 点击普通曲目跳转播放
    handleTrackClick(idx) {
      if (this.isTrackEditMode) return;
      const targetSec = this.trackList[idx].sec || 0;
      this.$emit('track-jump', targetSec);
    },
    // 点击喜欢时间戳跳转播放
    handleFavouriteTrackClick(idx) {
      if (this.isFavouriteEditMode) return;
      const targetSec = this.favouriteTrackList[idx].sec || 0;
      this.$emit('track-jump', targetSec);
    },
    // 评分组件核心方法
    startRating() {
      this.isRating = true;
      this.ratingTimer = setInterval(() => {
        if (this.score < 100 && this.isRating) {
          this.score += 1;
        } else {
          clearInterval(this.ratingTimer);
        }
      }, 10);
    },
    stopRating() {
      this.isRating = false;
      clearInterval(this.ratingTimer);
    },
    resetRating() {
      this.score = 0;
      this.isRating = false;
      clearInterval(this.ratingTimer);
    }
  }
};
</script>

<style scoped>
/* ✅ 核心：全局完全自适应布局 无任何写死尺寸 - 父容器占满页面 */
.tab-content {
  position: relative;
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  padding: 10px;
  display: flex;
  flex-direction: column;
}
/* 左右分栏：弹性占比 左6 右4 自适应页面宽度，永远占满高度 */
.main-layout {
  display: flex;
  width: 100%;
  height: 100%;
  gap: 20px;
}
.left-panel {
  flex: 6; /* 左侧弹性占6份 自适应 */
  display: flex;
  flex-direction: column;
  height: 100%;
}
.right-panel {
  flex: 4; /* 右侧弹性占4份 自适应 */
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

/* ✅ 重中之重：Tab+编辑按钮 整体置顶固定，永不滚动 核心样式 */
.sticky-top-box {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #ffffff;
  padding-bottom: 10px;
  margin-bottom: 15px;
}
.track-tab-nav {
  display: flex;
  gap: 10px;
  padding-bottom: 8px;
	border-bottom: 1px solid #e5e7eb;
  margin-bottom: 8px;
}
.tab-item {
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  color: #6b7280;
  transition: all 0.2s;
}
.tab-item.active {
  background: #2ea0d6;
  color: #fff;
}
.tab-item:hover {
  color: #2ea0d6;
}
/* 置顶的编辑按钮样式 */
.sticky-header {
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

/* ✅ 核心：列表内容区 自适应占满剩余高度+滚动，顶部内容完全不动 */
.tab-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 5px;
}
/* 美化滚动条 - 不影响布局 */
.tab-content-scroll::-webkit-scrollbar {
  width: 6px;
}
.tab-content-scroll::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
.tab-content-scroll::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* ✅ 评分组件 - 自适应布局 左文右图 【修复核心：评分圆完整显示+样式正常】 */
.rate-container {
  width: 100%;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
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
  color: #111827;
}
.rate-score {
  font-size: 24px;
  font-weight: bold;
  color: #2ea0d6;
  line-height: 1;
}
.reset-rate-btn {
  background: #dc2626;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.reset-rate-btn:hover {
  background: #b91c1c;
  transform: scale(1.02);
}
/* ✅ 修复关键：评分圆的样式 固定尺寸+正常显示，点击评分功能正常 */
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
  border: 3px solid #2ea0d6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #f9fafb;
  transition: all 0.2s;
}
.outer-circle:hover {
  border-color: #1f759d;
  background: #fff;
}
.inner-circle {
  background: #2ea0d6;
  border-radius: 50%;
  transition: width 0.05s linear, height 0.05s linear;
  opacity: 0.85;
}

/* ✅ 节奏组件 自适应占满右侧剩余高度 永不移位 */
.rhythm-container {
  width: 100%;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  flex: 1; /* 核心：占满右侧剩余所有高度 */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.rhythm-placeholder {
  text-align: center;
  color: #6b7280;
  font-size: 15px;
	line-height: 2;
}

/* ✅ 原有所有业务样式完整保留 */
.tracks-container {
  padding: 0;
  width: 100%;
}
.tracks-header {
  display: flex;
}
.tracks-list {
  width: 100%;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}
.track-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.2s;
}
.track-item:last-child {
  border-bottom: none;
}
.track-item:hover {
  background-color: #f9fafb;
}
.track-index {
  width: 30px;
  font-size: 14px;
  color: #6b7280;
  text-align: center;
  margin-right: 10px;
}
.track-show-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
}
.track-name {
  font-size: 15px;
  color: #111827;
  font-weight: 500;
}
.track-duration {
  font-size: 14px;
  color: #6b7280;
  margin-left: 20px;
}
.track-edit-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  gap: 20px;
}
.track-name-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  color: #111827;
  outline: none;
}
.track-name-input:focus {
  border-color: #2ea0d6;
  box-shadow: 0 0 0 2px rgba(46, 160, 214, 0.2);
}
.track-duration-input {
  width: 110px;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  color: #111827;
  text-align: center;
  outline: none;
}
.track-duration-input:focus {
  border-color: #2ea0d6;
  box-shadow: 0 0 0 2px rgba(46, 160, 214, 0.2);
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
.track-del-btn button:hover {
  background: #fef2f2;
}
.add-track-btn-box {
  text-align: right;
}
.add-track-btn {
  background: #2ea0d6;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.add-track-btn:hover {
  background: #1f759d;
  transform: scale(1.02);
}
.edit-btn {
  background: #2ea0d6;
  color: #fff;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.edit-btn.active {
  background: #15803d;
}
.edit-btn:hover {
  opacity: 0.9;
  transform: scale(1.02);
}
</style>