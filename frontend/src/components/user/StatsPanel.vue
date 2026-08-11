<template>
  <div class="stats-panel">
    <!-- 加载失败提示（后端未重启/接口404时，避免误以为数据全是 0） -->
    <div v-if="loadError" class="stats-error common-card">
      <p>⚠️ 音乐统计加载失败：{{ loadError }}</p>
      <p class="stats-error-tip">请确认后端已重启（/api/user/stats 接口 404 说明后端还是旧进程）。</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: safeMainColorDarkDouble }">{{ stats.album_count }}</div>
        <div class="stat-label">专辑总数</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: safeMainColorDarkDouble }">{{ stats.scored_count }}</div>
        <div class="stat-label">已评分</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: safeMainColorDarkDouble }">{{ formatDuration(stats.total_duration) }}</div>
        <div class="stat-label">听取总时长</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: safeMainColorDarkDouble }">{{ stats.review_count }}</div>
        <div class="stat-label">听后感</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: safeMainColorDarkDouble }">{{ stats.current_streak }}<span class="stat-unit">天</span></div>
        <div class="stat-label">连续收听</div>
      </div>
      <div class="stat-card common-card">
        <div class="stat-value" :style="{ color: safeMainColorDarkDouble }">{{ stats.active_days_30 }}<span class="stat-unit">天</span></div>
        <div class="stat-label">近30天活跃</div>
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
            :style="days === d ? { backgroundColor: safeMainColorDark, color: '#fff' } : { color: safeMainColorDark }"
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
// 主题色合法性兜底：props 传入 'transparent' 时（localStorage 坏值），图表渐变色不能直接用
import { sanitizeThemeColor } from '@/utils/themeColor'

const DEFAULT_STATS = {
  album_count: 0,
  scored_count: 0,
  review_count: 0,
  total_duration: 0,
  current_streak: 0,
  active_days_30: 0,
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
      loadError: '',
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
    },
    // 兜底后的主题色：'transparent'/坏值一律换成默认 #409eff，避免文字透明、渐变色抛 addColorStop 异常
    safeMainColor() { return sanitizeThemeColor(this.mainColor) },
    safeMainColorDark() { return sanitizeThemeColor(this.mainColorDark) },
    safeMainColorDarkDouble() { return sanitizeThemeColor(this.mainColorDarkDouble) }
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
      this.loadError = ''
      this.$axios.get('/api/user/stats', { params: { days: this.days } }).then(res => {
        if (res.data.code === 200 && res.data.data) {
          this.stats = { ...DEFAULT_STATS, ...res.data.data }
          this.$nextTick(() => this.renderCharts())
        } else {
          console.error('获取音乐统计失败：', res.data.msg)
          this.loadError = res.data.msg || '接口返回异常'
        }
      }).catch(err => {
        console.error('获取音乐统计失败：', err)
        this.loadError = (err.response && (err.response.data && err.response.data.msg || `HTTP ${err.response.status}`)) || err.message
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
            return `${p.axisValue}：${(Number(p.value) || 0).toFixed(1)} 小时`
          }
        },
        grid: { left: '6%', right: '4%', top: '12%', bottom: '10%', containLabel: true },
        xAxis: {
          type: 'category',
          data: list.map(d => d.date.slice(5)),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: this.safeMainColorDark || '#e5e5e5' } },
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666', rotate: list.length > 12 ? 45 : 0 }
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666', formatter: v => `${Number(v).toFixed(1)}` }
        },
        series: [{
          data: list.map(d => Number(d.duration || 0) / 3600),   // 秒 → 小时（保留浮点精度，轴刻度自动取整）
          type: 'bar',
          barMaxWidth: 22,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: this.safeMainColor || 'rgba(64,158,255,0.85)' },
              { offset: 1, color: `${this.safeMainColor || 'rgba(64,158,255,0.85)'}33` }
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
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666' }
        },
        series: [{
          type: 'scatter',
          data: points,
          symbolSize: data => Math.max(22, Math.min(70, 14 + data[1] * (60 / maxValue))),
          itemStyle: {
            color: new echarts.graphic.RadialGradient(0.4, 0.3, 1, [
              { offset: 0, color: '#ffffff' },
              { offset: 0.35, color: this.safeMainColor || 'rgba(64,158,255,0.85)' },
              { offset: 1, color: this.safeMainColorDark || 'rgba(64,158,255,0.5)' }
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
          axisLine: { lineStyle: { color: this.safeMainColorDark || '#e5e5e5' } },
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666', rotate: 30 }
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666' }
        },
        series: [{
          data: list.map(b => b.count),
          type: 'bar',
          barMaxWidth: 24,
          itemStyle: {
            color: this.safeMainColorDark || 'rgba(64,158,255,0.7)',
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
    // 秒数 → 小时（h + 1 位小数）：听取总时长统一小时口径（v0.7.1 P1），如 0.4小时 / 4.0小时
    formatDuration(seconds) {
      const s = Number(seconds) || 0
      return `${(s / 3600).toFixed(1)}小时`
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

/* 统计卡片（6 张：专辑/评分/总时长/听后感/连续收听/近30天活跃 → 3 列两行） */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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

.stat-unit {
  font-size: 12px;
  font-weight: 400;
  margin-left: 2px;
}

.stat-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

/* 加载失败提示 */
.stats-error {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.25);
  color: #b91c1c;
  font-size: 13px;
  line-height: 1.6;
}

.stats-error p {
  margin: 0;
}

.stats-error-tip {
  font-size: 12px;
  opacity: 0.85;
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
