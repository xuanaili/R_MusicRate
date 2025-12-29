<template>
  <div class="tab-content">
    <!-- 只保留：单曲列表区域 -->
    <div class="tracks-container">
      <h3>单曲列表</h3>
      <div class="tracks-header">
        <div class="tracks-action-btn">
          <button
            class="edit-btn"
            @click="toggleEditStatus"
            :class="{active: isEditMode}"
          >
            {{ isEditMode ? '✅ 保存曲目' : '✏️ 编辑曲目' }}
          </button>
        </div>
      </div>

      <div class="tracks-list">
        <div
          v-for="(track, idx) in trackList"
          :key="idx"
          class="track-item"
          @click="handleTrackClick(idx)"
        >
          <div class="track-index">{{ idx + 1 }}.</div>

          <div v-if="isEditMode" class="track-edit-content">
            <input
              type="text"
              v-model="track.name"
              placeholder="请输入曲目名称"
              class="track-name-input"
            />
            <input
              type="text"
              v-model="track.duration"
              placeholder="00:00"
              class="track-duration-input"
              maxlength="5"
              @blur="formatDurationInput(idx)"
            />
          </div>

          <div v-else class="track-show-content">
            <div class="track-name" style="cursor: pointer;">{{ track.name || '未知曲目' }}</div>
            <div class="track-duration">{{ track.duration || '00:00' }}</div>
          </div>

          <div v-if="isEditMode" class="track-del-btn">
            <button @click.stop="deleteTrack(idx)">×</button>
          </div>
        </div>
      </div>

      <div v-if="isEditMode" class="add-track-btn-box">
        <button class="add-track-btn" @click="addNewTrack">➕ 添加新单曲</button>
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
    }
  },
  data() {
    return {
      isEditMode: false,
      trackList: [] // {name: '', duration: '分秒文本', sec: 数据库纯秒数}
    };
  },
  watch: {
    tracks: {
      handler() {
        this.initTrackList();
      },
      deep: true
    },
    tracksTime: {
      handler() {
        this.initTrackList();
      },
      deep: true
    }
  },
  mounted() {
    this.initTrackList();
  },
  activated() {
    this.initTrackList();
  },
  methods: {
    timeToSeconds(timeStr) {
      if (!timeStr || timeStr.indexOf(':') === -1) return 0;
      const [minutes, seconds] = timeStr.split(':').map(Number);
      return (isNaN(minutes) ? 0 : minutes) * 60 + (isNaN(seconds) ? 0 : seconds);
    },
    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '00:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      return `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },
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
        this.trackList = [{name: '未知曲目', sec: 0, duration: '00:00'}];
      }
    },
    formatDurationInput(idx) {
      const track = this.trackList[idx];
      if (!track) return;
      track.sec = this.timeToSeconds(track.duration);
      track.duration = this.secondsToTime(track.sec);
    },
    async toggleEditStatus() {
      if (this.isEditMode) {
        await this.saveTrackList();
        this.isEditMode = false;
      } else {
        this.isEditMode = true;
      }
    },
    addNewTrack() {
      this.trackList.push({name: '', duration: '00:00', sec: 0});
    },
    deleteTrack(idx) {
      if (this.trackList.length <= 1) {
        alert('至少保留1首单曲哦！');
        return;
      }
      this.trackList.splice(idx, 1);
    },
    async saveTrackList() {
      try {
        const pureTrackNames = this.trackList.map(item => item.name.trim() || '未知曲目');
        const trackSecArr = this.trackList.map(item => item.sec || 0);
        const fullTrackList = this.trackList.map(item => ({
          name: item.name.trim() || '未知曲目'
        }));

        const res = await this.$axios.put(`/api/album/update/tracks/${this.album.id}`, {
          tracks: pureTrackNames,
          full_tracks: fullTrackList,
          tracks_time: trackSecArr
        }, {
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          }
        });

        if (res.data.code === 200) {
          alert('✅ 曲目列表保存成功！');
          this.$emit('update-album-data', {
            tracks: pureTrackNames,
            tracks_time: trackSecArr
          });
        } else {
          alert(`❌ 保存失败：${res.data.msg}`);
        }
      } catch (err) {
        console.error('保存曲目失败：', err);
        alert(err.response?.data?.msg || '❌ 保存失败，请重试！');
      }
    },
    // 核心：点击曲目 向父组件传事件+跳转秒数，父组件播放器接收并跳转播放
    handleTrackClick(idx) {
      if (this.isEditMode) return;
      const targetSec = this.trackList[idx].sec || 0;
      this.$emit('track-jump', targetSec);
    }
  }
};
</script>

<style scoped>
.tab-content {
  position: relative;
  width: 100%;
  box-sizing: border-box;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.tracks-container {
  padding: 0;
  width: 100%;
}
.tracks-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
	margin-bottom: 15px;
  padding-bottom: 8px;
	border-bottom: 1px solid #e5e7eb;
}
.tracks-list {
  width: 100%;
  background: rgba(255,255,255,0.8);
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
	width: 80px;
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