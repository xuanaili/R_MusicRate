<template>
  <div class="stats-panel">
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: mainColorDarkDouble }">{{ stats.album_count }}</div>
        <div class="stat-label">专辑总数</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: mainColorDarkDouble }">{{ stats.scored_count }}</div>
        <div class="stat-label">已评分</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: mainColorDarkDouble }">{{ formatDuration(stats.total_duration) }}</div>
        <div class="stat-label">听取总时长</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: mainColorDarkDouble }">{{ stats.review_count }}</div>
        <div class="stat-label">听后感</div>
      </div>
    </div>

    <!-- 近N天听取时长柱状图 -->
    <div class="chart-card common-card">
      <div class="chart-head">
        <span class="card-title">近{{ days }}天听取时长</span>
        <div class="days-toggle">
          <button
            v-for="d in [7, 14, 30]"
            :key="d"
            class="days-btn"
            :class="{ active: days === d }"
            :style="days === d ? { backgroundColor: mainColorDark, color: '#fff' } : { color: mainColorDark }"
            @click="handleDaysChange(d)"
          >{{ d }}天</button>
        </div>
      </div>
      <div ref="dailyChart" class="chart-box"></div>
      <p v-if="isDailyEmpty" class="chart-empty">近{{ days }}天暂无播放记录</p>
    </div>

    <!-- 标签分布气泡图 -->
    <div class="chart-card common-card">
      <div class="chart-head"><span class="card-title">标签分布</span></div>
      <div ref="tagChart" class="chart-box"></div>
      <p v-if="stats.tag_distribution && stats.tag_distribution.length === 0" class="chart-empty">暂无标签数据</p>
    </div>

    <!-- 评分分布柱状图 -->
    <div class="chart-card common-card">
      <div class="chart-head"><span class="card-title">专辑评分分布</span></div>
      <div ref="scoreChart" class="chart-box"></div>
      <p v-if="isScoreEmpty" class="chart-empty">暂无已评分专辑</p>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts/dist/echarts.min.js'

const DEFAULT_STATS = {
  album_count: 0,
  scored_count: 0,
  review_count: 0,
  total_duration: 0,
  daily_listening: [],
  tag_distribution: [],
  score_distribution: []
}

export default {
  name: 'StatsPanel',
  props: {
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      stats: { ...DEFAULT_STATS },
      days: 7,
      loading: false,
      charts: []
    }
  },
  computed: {
    isDailyEmpty() {
      const list = this.stats.daily_listening || []
      return list.length === 0 || list.every(d => d.duration === 0)
    },
    isScoreEmpty() {
      const list = this.stats.score_distribution || []
      return list.every(b => b.count === 0)
    }
  },
  created() {
    this.fetchStats()
    window.addEventListener('resize', this.handleResize)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)
    this.disposeCharts()
  },
  methods: {
    fetchStats() {
      this.loading = true
      this.$axios.get('/api/user/stats', { params: { days: this.days } }).then(res => {
        if (res.data.code === 200 && res.data.data) {
          this.stats = { ...DEFAULT_STATS, ...res.data.data }
          this.$nextTick(() => this.renderCharts())
        } else {
          console.error('获取音乐统计失败：', res.data.msg)
        }
      }).catch(err => {
        console.error('获取音乐统计失败：', err)
      }).finally(() => {
        this.loading = false
      })
    },
    handleDaysChange(d) {
      if (this.days === d) return
      this.days = d
      this.fetchStats()
    },
    // ===== ECharts 三图 =====
    renderCharts() {
      this.disposeCharts()
      this.renderDailyChart()
      this.renderTagChart()
      this.renderScoreChart()
    },
    renderDailyChart() {
      const dom = this.$refs.dailyChart
      if (!dom) return
      const chart = echarts.init(dom)
      this.charts.push(chart)
      const list = this.stats.daily_listening || []
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: params => {
            const p = params[0]
            return `${p.axisValue}：${p.value} 秒`
          }
        },
        grid: { left: '6%', right: '4%', top: '12%', bottom: '10%', containLabel: true },
        xAxis: {
          type: 'category',
          data: list.map(d => d.date.slice(5)),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: this.mainColorDark || '#e5e5e5' } },
          axisLabel: { fontSize: 11, color: this.mainColorDark || '#666', rotate: list.length > 12 ? 45 : 0 }
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
          axisLabel: { fontSize: 11, color: this.mainColorDark || '#666' }
        },
        series: [{
          data: list.map(d => d.duration),
          type: 'bar',
          barMaxWidth: 22,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: this.mainColor || 'rgba(64,158,255,0.85)' },
              { offset: 1, color: `${this.mainColor || 'rgba(64,158,255,0.85)'}33` }
            ]),
            borderRadius: [3, 3, 0, 0]
          }
        }]
      })
    },
    renderTagChart() {
      const dom = this.$refs.tagChart
      if (!dom) return
      const chart = echarts.init(dom)
      this.charts.push(chart)
      const list = this.stats.tag_distribution || []
      const points = list.map((item, idx) => ({ name: item.name, value: [idx, item.value] }))
      const maxValue = Math.max(1, ...list.map(i => i.value))
      chart.setOption({
        tooltip: {
          formatter: params => {
            const d = params.data
            return `${d.name}：${d.value[1]} 张专辑`
          }
        },
        grid: { left: '8%', right: '6%', top: '12%', bottom: '12%', containLabel: true },
        xAxis: {
          type: 'category',
          show: false,
          data: list.map((_, idx) => idx)
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: maxValue + 1,
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
          axisLabel: { fontSize: 11, color: this.mainColorDark || '#666' }
        },
        series: [{
          type: 'scatter',
          data: points,
          symbolSize: data => Math.max(22, Math.min(70, 14 + data[1] * (60 / maxValue))),
          itemStyle: {
            color: new echarts.graphic.RadialGradient(0.4, 0.3, 1, [
              { offset: 0, color: '#ffffff' },
              { offset: 0.35, color: this.mainColor || 'rgba(64,158,255,0.85)' },
              { offset: 1, color: this.mainColorDark || 'rgba(64,158,255,0.5)' }
            ]),
            borderColor: '#fff',
            borderWidth: 1,
            opacity: 0.9
          },
          label: {
            show: true,
            formatter: p => (p.data.name || '').split('【')[0].trim() || p.data.name,
            position: 'inside',
            color: '#fff',
            fontSize: 12,
            fontWeight: 600
          },
          emphasis: { scale: 1.15 }
        }]
      })
    },
    renderScoreChart() {
      const dom = this.$refs.scoreChart
      if (!dom) return
      const chart = echarts.init(dom)
      this.charts.push(chart)
      const list = this.stats.score_distribution || []
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: params => {
            const p = params[0]
            return `${p.axisValue} 分：${p.value} 张专辑`
          }
        },
        grid: { left: '6%', right: '4%', top: '12%', bottom: '10%', containLabel: true },
        xAxis: {
          type: 'category',
          data: list.map(b => b.bucket),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: this.mainColorDark || '#e5e5e5' } },
          axisLabel: { fontSize: 11, color: this.mainColorDark || '#666', rotate: 30 }
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
          axisLabel: { fontSize: 11, color: this.mainColorDark || '#666' }
        },
        series: [{
          data: list.map(b => b.count),
          type: 'bar',
          barMaxWidth: 24,
          itemStyle: {
            color: this.mainColorDark || 'rgba(64,158,255,0.7)',
            borderRadius: [3, 3, 0, 0]
          }
        }]
      })
    },
    disposeCharts() {
      this.charts.forEach(chart => {
        try { chart.dispose() } catch (e) { /* ignore */ }
      })
      this.charts = []
    },
    handleResize() {
      this.charts.forEach(chart => chart && chart.resize())
    },
    // 秒数 → 可读时长（如 2小时30分钟 / 45分钟 / 30秒）
    formatDuration(seconds) {
      const s = Number(seconds) || 0
      if (s <= 0) return '0'
      if (s < 60) return `${Math.round(s)}秒`
      if (s < 3600) return `${Math.floor(s / 60)}分钟`
      const h = Math.floor(s / 3600)
      const m = Math.floor((s % 3600) / 60)
      return m ? `${h}小时${m}分钟` : `${h}小时`
    }
  }
}
</script>

<style scoped>
.stats-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.common-card {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  padding: 12px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.stat-card {
  text-align: center;
  padding: 12px 6px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
  word-break: break-all;
}

.stat-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

/* 图表卡片 */
.chart-card {
  padding: 12px;
}

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.days-toggle {
  display: flex;
  gap: 4px;
}

.days-btn {
  padding: 3px 10px;
  border: none;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.2s;
}

.chart-box {
  width: 100%;
  height: 190px;
}

.chart-empty {
  font-size: 12px;
  color: #999;
  text-align: center;
  padding: 8px 0 4px;
}

/* 窄屏：统计卡片两列 */
@media (max-width: 420px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
