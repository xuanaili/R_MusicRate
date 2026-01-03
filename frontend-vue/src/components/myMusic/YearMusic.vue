<template>
  <div class="year-music-container">
    <div class="placeholder-content">
      <h3>🎧 年度音乐</h3>
      <p>该模块正在开发中，敬请期待～</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'YearMusic'
}
</script>

<style scoped>
.year-music-container {
  width: 100%;
  min-height: 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(4px);
  border-radius: 12px;
  padding: 20px;
}
.placeholder-content {
  text-align: center;
  color: #666;
}
.placeholder-content h3 {
  font-size: 20px;
  margin-bottom: 10px;
  color: #333;
}
.placeholder-content p {
  font-size: 16px;
}
</style>