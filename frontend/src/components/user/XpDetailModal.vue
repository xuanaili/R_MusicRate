<template>
  <!-- 等级经验详情弹窗（v0.7.2）：点击个人资料等级徽章触发；mask+content 复用 AlbumLyricViewer 弹窗模式 -->
  <div v-if="visible" class="xp-modal-mask" @click="$emit('close')">
    <div class="xp-modal-content" @click.stop>
      <div class="xp-modal-header">
        <h3>等级经验详情</h3>
        <span class="xp-close-btn" @click="$emit('close')">×</span>
      </div>

      <div class="xp-modal-body">
        <!-- 加载失败兜底：避免误以为全是 0（后端未重启 / 接口 404 时给出明确提示） -->
        <div v-if="loadError" class="xp-error">
          <p>⚠️ 经验详情加载失败：{{ loadError }}</p>
          <p class="xp-error-tip">请确认后端已重启（/api/user/xp-detail 接口 404 说明后端还是旧进程）。</p>
        </div>

        <!-- 加载中 -->
        <div v-else-if="loading" class="xp-loading">加载中…</div>

        <!-- 详情主体 -->
        <div v-else-if="detail">
          <!-- 等级大卡：Lv + 称号 + 进度条 + 距下一级 -->
          <div class="xp-level-card">
            <div class="xp-level-row">
              <span class="xp-level-num" :style="{ color: safeMainColorDark }">Lv.{{ detail.level }}</span>
              <span class="xp-level-title">{{ detail.level_title || '初听者' }}</span>
            </div>
            <div class="xp-bar">
              <div class="xp-bar-fill" :style="{ width: xpPercent, backgroundColor: safeMainColorDark }"></div>
            </div>
            <div class="xp-bar-meta">
              <span>总经验 {{ formatXp(detail.total_xp) }}</span>
              <span>距 Lv.{{ detail.level + 1 }} 还差 {{ formatXp(detail.next_level_xp) }}</span>
            </div>
          </div>

          <!-- 今日 + 累计卡片 -->
          <div class="xp-summary-grid">
            <div class="xp-summary-card common-card">
              <div class="xp-summary-value" :style="{ color: safeMainColorDarkDouble }">{{ formatXp(detail.today_xp) }}</div>
              <div class="xp-summary-label">今日经验</div>
            </div>
            <div class="xp-summary-card common-card">
              <div class="xp-summary-value" :style="{ color: safeMainColorDarkDouble }">{{ formatXp(detail.today_listening) }}</div>
              <div class="xp-summary-label">今日听歌</div>
            </div>
            <div class="xp-summary-card common-card">
              <div class="xp-summary-value" :style="{ color: safeMainColorDarkDouble }">{{ formatXp(detail.today_bonus) }}</div>
              <div class="xp-summary-label">今日加分</div>
            </div>
            <div class="xp-summary-card common-card">
              <div class="xp-summary-value" :style="{ color: safeMainColorDarkDouble }">{{ formatXp(detail.total_listening_xp) }}</div>
              <div class="xp-summary-label">总听歌经验<span class="xp-note">（完整历史）</span></div>
            </div>
          </div>

          <!-- 近 7 天经验堆叠柱状图（听歌 + 加分） -->
          <div class="xp-chart-card common-card">
            <div class="card-title">近 7 天经验</div>
            <div ref="dailyChart" class="xp-chart-box"></div>
            <p v-if="isDailyEmpty" class="xp-chart-empty">近 7 天暂无经验记录</p>
          </div>

          <!-- 按来源累计（自 v0.7.2 起统计） -->
          <div class="xp-source-card common-card">
            <div class="card-title">按来源累计<span class="xp-note">（自 v0.7.2 起记录明细后统计）</span></div>
            <div class="xp-source-grid">
              <div v-for="s in sourceList" :key="s.key" class="xp-source-item">
                <span class="xp-source-icon" :style="{ backgroundColor: safeMainColor }">{{ s.icon }}</span>
                <div class="xp-source-info">
                  <div class="xp-source-label">{{ s.label }}</div>
                  <div class="xp-source-value">{{ formatXp(detail.source_totals[s.key]) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 最近经验明细流 -->
          <div class="xp-recent-card common-card">
            <div class="card-title">最近经验</div>
            <div v-if="detail.recent_logs && detail.recent_logs.length" class="xp-recent-list">
              <div v-for="(log, idx) in detail.recent_logs" :key="idx" class="xp-recent-item">
                <span class="xp-recent-type" :style="{ color: safeMainColorDark }">{{ sourceLabel(log.xp_type) }}</span>
                <span class="xp-recent-time">{{ formatTime(log.created_at) }}</span>
                <span class="xp-recent-amount" :style="{ color: safeMainColorDarkDouble }">+{{ formatXp(log.amount) }}</span>
              </div>
            </div>
            <p v-else class="xp-chart-empty">暂无明细（自 v0.7.2 起的新操作才会记录）</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts/dist/echarts.min.js'
// 主题色合法性兜底：props 传入 'transparent' 时（localStorage 坏值），图表渐变色不能直接用
import { sanitizeThemeColor } from '@/utils/themeColor'

// 来源顺序与标签（与后端 backend/utils/xp.py SOURCE_LABELS 一致）
const SOURCE_META = [
  { key: 'listening', label: '听歌', icon: '🎧' },
  { key: 'rating', label: '评分', icon: '⭐' },
  { key: 'review', label: '听后感', icon: '📝' },
  { key: 'comment', label: '评论', icon: '💬' }
]

const EMPTY_DETAIL = {
  total_xp: 0,
  level: 0,
  next_level_xp: 0,
  xp_progress: 0,
  level_title: '',
  total_listening_xp: 0,
  today_listening: 0,
  today_bonus: 0,
  today_xp: 0,
  daily_xp: [],
  source_totals: { listening: 0, rating: 0, review: 0, comment: 0 },
  recent_logs: []
}

export default {
  name: 'XpDetailModal',
  props: {
    visible: { type: Boolean, default: false },
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      detail: null,
      loading: false,
      loadError: '',
      chart: null
    }
  },
  computed: {
    // 兜底后的主题色：'transparent'/坏值一律换成默认 #409eff，避免文字透明、渐变色抛 addColorStop 异常
    safeMainColor() { return sanitizeThemeColor(this.mainColor) },
    safeMainColorDark() { return sanitizeThemeColor(this.mainColorDark) },
    safeMainColorDarkDouble() { return sanitizeThemeColor(this.mainColorDarkDouble) },
    xpPercent() {
      const p = Number(this.detail ? this.detail.xp_progress : 0) || 0
      return `${Math.max(0, Math.min(1, p)) * 100}%`
    },
    sourceList() { return SOURCE_META },
    isDailyEmpty() {
      const list = (this.detail && this.detail.daily_xp) || []
      return list.length === 0 || list.every(d => (Number(d.total) || 0) === 0)
    }
  },
  watch: {
    visible(val) {
      if (val) {
        this.fetchDetail()
        // 等 DOM 渲染完成后再初始化图表
        this.$nextTick(() => this.renderChart())
      } else {
        this.disposeChart()
      }
    }
  },
  beforeDestroy() {
    this.disposeChart()
  },
  methods: {
    fetchDetail() {
      this.loading = true
      this.loadError = ''
      this.$axios.get('/api/user/xp-detail').then(res => {
        if (res.data.code === 200 && res.data.data) {
          this.detail = { ...EMPTY_DETAIL, ...res.data.data }
          this.$nextTick(() => this.renderChart())
        } else {
          this.loadError = res.data.msg || '接口返回异常'
        }
      }).catch(err => {
        this.loadError = (err.response && (err.response.data && err.response.data.msg || `HTTP ${err.response.status}`)) || err.message
      }).finally(() => {
        this.loading = false
      })
    },
    // ===== 近 7 天堆叠柱状图（听歌 + 加分） =====
    renderChart() {
      const dom = this.$refs.dailyChart
      if (!dom) return
      this.disposeChart()
      const chart = echarts.init(dom)
      this.chart = chart
      const list = (this.detail && this.detail.daily_xp) || []
      const dates = list.map(d => (d.date || '').slice(5))
      const listening = list.map(d => Number(d.listening || 0))
      const bonus = list.map(d => Number(d.bonus || 0))
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: params => {
            const p = params[0]
            const item = list[params[0].dataIndex] || {}
            return `${p.axisValue}<br/>听歌：${this.formatXp(item.listening)}<br/>加分：${this.formatXp(item.bonus)}<br/><b>合计：${this.formatXp(item.total)}</b>`
          }
        },
        legend: { data: ['听歌', '加分'], top: 0, textStyle: { fontSize: 11 } },
        grid: { left: '10%', right: '4%', top: '18%', bottom: '8%', containLabel: true },
        xAxis: {
          type: 'category',
          data: dates,
          axisTick: { show: false },
          axisLine: { lineStyle: { color: this.safeMainColorDark || '#e5e5e5' } },
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666' }
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
          axisLabel: { fontSize: 11, color: this.safeMainColorDark || '#666' }
        },
        series: [
          {
            name: '听歌',
            type: 'bar',
            stack: 'xp',
            barMaxWidth: 22,
            data: listening,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: this.safeMainColor || 'rgba(64,158,255,0.85)' },
                { offset: 1, color: `${this.safeMainColor || 'rgba(64,158,255,0.85)'}33` }
              ]),
              borderRadius: [3, 3, 0, 0]
            }
          },
          {
            name: '加分',
            type: 'bar',
            stack: 'xp',
            barMaxWidth: 22,
            data: bonus,
            itemStyle: {
              color: this.safeMainColorDarkDouble || 'rgba(255,170,64,0.75)',
              borderRadius: [3, 3, 0, 0]
            }
          }
        ]
      })
    },
    disposeChart() {
      if (this.chart) {
        try { this.chart.dispose() } catch (e) { /* ignore */ }
        this.chart = null
      }
    },
    // ===== 展示格式化 =====
    sourceLabel(key) {
      const meta = SOURCE_META.find(s => s.key === key)
      return meta ? meta.label : key
    },
    formatXp(n) {
      const v = Number(n) || 0
      return Number.isInteger(v) ? String(v) : v.toFixed(1)
    },
    // 'YYYY-MM-DD HH:MM:SS' → 'MM-DD HH:MM'
    formatTime(str) {
      if (!str) return ''
      const s = String(str)
      if (s.length >= 16) return `${s.slice(5, 10)} ${s.slice(11, 16)}`
      if (s.length >= 10) return s.slice(5, 10)
      return s
    }
  }
}
</script>

<style scoped>
.xp-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.xp-modal-content {
  width: 92%;
  max-width: 480px;
  max-height: 86vh;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.xp-modal-header {
  padding: 14px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.xp-modal-header h3 {
  margin: 0;
  font-size: 17px;
  color: #333;
}

.xp-close-btn {
  font-size: 24px;
  color: #999;
  cursor: pointer;
  width: 30px;
  height: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: color 0.2s;
}

.xp-close-btn:hover {
  color: #333;
}

.xp-modal-body {
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 加载失败 / 加载中 */
.xp-error {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.25);
  color: #b91c1c;
  font-size: 13px;
  line-height: 1.6;
  padding: 12px;
  border-radius: 8px;
}

.xp-error p {
  margin: 0;
}

.xp-error-tip {
  font-size: 12px;
  opacity: 0.85;
}

.xp-loading {
  text-align: center;
  color: #999;
  font-size: 13px;
  padding: 30px 0;
}

/* 等级大卡 */
.xp-level-card {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.xp-level-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.xp-level-num {
  font-size: 24px;
  font-weight: 800;
}

.xp-level-title {
  font-size: 14px;
  color: #666;
  font-weight: 600;
}

.xp-bar {
  height: 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.xp-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.xp-bar-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #888;
}

/* 今日 + 累计卡片 */
.xp-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.xp-summary-card {
  text-align: center;
  padding: 10px 4px;
}

.xp-summary-value {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
}

.xp-summary-label {
  font-size: 11px;
  color: #888;
  margin-top: 3px;
}

/* 通用卡片 */
.common-card {
  background: rgba(255, 255, 255, 0.3);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #333;
}

.xp-note {
  font-size: 11px;
  font-weight: 400;
  color: #aaa;
  margin-left: 4px;
}

/* 图表 */
.xp-chart-box {
  width: 100%;
  height: 180px;
}

.xp-chart-empty {
  font-size: 12px;
  color: #999;
  text-align: center;
  padding: 6px 0 2px;
}

/* 按来源累计 */
.xp-source-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.xp-source-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.xp-source-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.xp-source-info {
  min-width: 0;
}

.xp-source-label {
  font-size: 11px;
  color: #888;
}

.xp-source-value {
  font-size: 15px;
  font-weight: 700;
  color: #333;
}

/* 最近经验明细流 */
.xp-recent-list {
  max-height: 200px;
  overflow-y: auto;
}

.xp-recent-item {
  display: flex;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed #eee;
  font-size: 13px;
}

.xp-recent-item:last-child {
  border-bottom: none;
}

.xp-recent-type {
  font-weight: 600;
  width: 52px;
  flex-shrink: 0;
}

.xp-recent-time {
  flex: 1;
  color: #999;
  font-size: 12px;
}

.xp-recent-amount {
  font-weight: 700;
}

/* 窄屏：今日卡片两列 */
@media (max-width: 380px) {
  .xp-summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
