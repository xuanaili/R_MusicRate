<template>
  <div class="tab-content">
    <h2>内容</h2>
    <h3>简介</h3>
    <div class="tracks-list">
      <div v-for="(track, idx) in (album.tracks || [])" :key="idx" class="track-item">
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
</template>

<script>
export default {
  name: 'AlbumTrackList',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    }
  }
};
</script>

<style scoped>
.tracks-list {
  margin: 20px 0;
  font-size: 14px;
}

.track-item {
  margin-bottom: 8px;
  padding: 4px 0;
  border-bottom: 1px dashed #eee;
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
</style>