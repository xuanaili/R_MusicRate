<template>
  <div class="tab-content-container">
    <!-- 左侧 40% 区域 - 日历统计小组件【固定高度+滚动+悬停弹窗】 -->
    <div class="calendar-statistics">
      <h3 :style="{ color: mainColor }">我的听后感统计</h3>
      <!-- 日历头部：左右箭头 + 当前月份 -->
      <div class="calendar-header">
        <button class="arrow-btn" @click="prevMonth" :style="{ color: mainColor }">
          ←
        </button>
        <span class="calendar-month">{{ currentYear }}年 {{ currentMonth < 10 ? '0' + currentMonth : currentMonth }}月</span>
        <button class="arrow-btn" @click="nextMonth" :style="{ color: mainColor }">
          →
        </button>
      </div>
      <!-- 星期头部 - 7列固定，和下方日期严格对齐 -->
      <div class="calendar-week">
        <div class="week-item">日</div>
        <div class="week-item">一</div>
        <div class="week-item">二</div>
        <div class="week-item">三</div>
        <div class="week-item">四</div>
        <div class="week-item">五</div>
        <div class="week-item">六</div>
      </div>
      <!-- 日历主体 - ✅每行固定7个日期 + 和星期精准对齐 -->
      <div class="calendar-days">
        <div class="day-item empty" v-for="empty in emptyStartDays" :key="'empty'+empty"></div>
        <div
          class="day-item"
          v-for="day in currentMonthDays"
          :key="day.day"
          :class="{ hasRecord: hasRecordOnDay(day.day), active: selectedDay === day.day }"
          :style="hasRecordOnDay(day.day) ? { backgroundColor: lightenColor(mainColor, 0.7), borderColor: mainColor } : {}"
          @click="handleDayClick(day.day)"
        >
          <span class="day-num">{{ day.day }}</span>
          <span class="record-badge" v-if="hasRecordOnDay(day.day)" :style="{ backgroundColor: mainColorDark }">
            {{ getRecordCount(day.day) }}
          </span>
        </div>
      </div>

      <!-- 点击高亮日期展示：当日听后感详情列表 ✅悬停只显示纯听后感内容 -->
      <div class="day-detail-list" v-if="selectedDay && hasRecordOnDay(selectedDay)">
        <h4 :style="{ color: mainColor, margin: '15px 0 10px 0', fontSize: '14px' }">
          {{ currentYear }}-{{ currentMonth <10 ? '0'+currentMonth : currentMonth }}-{{ selectedDay <10 ? '0'+selectedDay : selectedDay }} 听后感详情
        </h4>
        <div class="detail-scroll-box">
          <div
            class="detail-item"
            v-for="(item, idx) in getDayDetailList()"
            :key="item.feeling_id || idx"
            @mouseenter="showTooltip($event, item.content)"
            @mouseleave="hideTooltip()"
          >
            <div class="album-name">{{ item.albumName }} <span style="font-size:11px;color:#999;">{{item.singer}}</span></div>
            <div class="album-score">评分：<span>{{ item.score }}</span></div>
            <div style="font-size:11px;color:#999;margin-top:2px;">时长：{{ formatSecondsToHourMin(item.listening_duration) }}</div>
          </div>
        </div>
      </div>

      <!-- 无选中/无记录时展示：统计概览 -->
      <div class="stat-overview" v-else>
        <div class="stat-item" v-if="!loading">本月总条数：<span>{{ totalReviewCount }}</span></div>
        <div class="stat-item" v-if="!loading">平均评分：<span>{{ avgScore }}</span></div>
        <div class="stat-item" v-if="!loading">最近编写：<span>{{ lastWriteDate }}</span></div>
        <div class="stat-item" v-if="loading">加载统计数据中...</div>
      </div>

      <!-- 听后感悬浮预览弹窗 - ✅只展示纯听后感内容 -->
      <div
        v-if="tooltipVisible"
        class="tooltip-box"
        :style="{
          left: `${tooltipX + 10}px`,
          top: `${tooltipY + 10}px`,
          maxWidth: '380px'
        }"
      >
        <div class="tooltip-content">{{ tooltipText }}</div>
      </div>
    </div>

    <!-- 右侧 60% 区域 - 听后感编辑内容 ✅听取时长统一转 xxhxxmin 格式 -->
    <div class="review-content">
      <h2>{{ album.album_name || '未知专辑' }}——听后感</h2>
      <div class="audio-link">[{{ album.album_name || '未知' }}.mp3]</div>

      <div class="review-edit-area">
        <textarea
          v-model="newFeelingContent"
          placeholder="输入你的听后感..."
          class="review-textarea"
          rows="3"
        ></textarea>
        <div class="review-actions">
          <button
            @click="handleAddReview"
            class="save-btn"
            :disabled="!newFeelingContent.trim()"
            :style="{backgroundColor: newFeelingContent.trim() ? mainColorDark : '#999'}"
          >新增听后感</button>
          <button
            @click="handleDeleteAll"
            class="delete-btn"
            v-if="(album.review || {}).feelings?.length"
            :style="{backgroundColor: mainColorDark}"
          >清空所有听后感</button>
        </div>
      </div>

      <div class="feelings-list" v-if="(album.review || {}).feelings?.length">
        <h3 :style="{color: mainColor}">历史听后感</h3>
        <div
          class="feeling-item"
          v-for="(feeling, idx) in (album.review || {}).feelings"
          :key="feeling.id || idx"
        >
          <div class="feeling-top">
            <span class="create-time">{{ feeling.create_time }}</span>
            <span class="feeling-score">评分：{{ feeling.my_score || 0 }}</span>
          </div>
          <div class="feeling-content">{{ feeling.content }}</div>
          <div class="listening-duration">听取时长：{{ formatSecondsToHourMin(feeling.listening_duration) }}</div>
          <button class="delete-single-btn" @click="handleDeleteSingle(feeling.id)" :style="{backgroundColor: mainColorDark}">删除</button>
        </div>
      </div>
      <p class="no-feeling" v-else>暂无听后感记录，快来添加吧~</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumReviewEditor',
  props: {
    album: {
      type: Object,
      required: true,
      default: () => ({})
    }
  },
  data() {
    return {
      newFeelingContent: '',
      mainColor: '#42b983',
      mainColorDark: '#2f9465',
      // 日历核心变量
      currentYear: new Date().getFullYear(),
      currentMonth: new Date().getMonth() + 1,
      selectedDay: null,
      emptyStartDays: 5,
      currentMonthDays: [],
      // 悬浮弹窗核心变量
      tooltipVisible: false,
      tooltipText: '',
      tooltipX: 0,
      tooltipY: 0,
      reviewRecordData: [],
      loading: false,
      totalReviewCount: 0,
      avgScore: '0.0',
      lastWriteDate: '暂无记录'
    };
  },
  watch: {
    album: {
      immediate: true,
      handler(newVal) {
        if(newVal.cover_img) this.extractMainColor(newVal.cover_img);
        else {
          this.mainColor = '#42b983';
          this.mainColorDark = '#2f9465';
        }
      }
    },
    currentYear: { immediate: true, handler() { this.initCalendar() } },
    currentMonth: { immediate: true, handler() { this.initCalendar(); this.calcCurrentMonthStat() } },
    reviewRecordData: { immediate: true, handler() { this.calcCurrentMonthStat() } }
  },
  mounted() {
    this.fetchCalendarReviewData();
  },
  methods: {
    // 提取封面主色【原有方法】
    extractMainColor(imgUrl) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 10;
        canvas.height = 10;
        ctx.drawImage(img, 0, 0, 10, 10);
        const data = ctx.getImageData(0,0,10,10).data;
        let r=0,g=0,b=0,c=0;
        for(let i=0;i<data.length;i+=4){r+=data[i];g+=data[i+1];b+=data[i+2];c++}
        r=Math.floor(r/c);g=Math.floor(g/c);b=Math.floor(b/c);
        const hex = `#${((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1)}`;
        this.mainColor = hex;
        this.mainColorDark = this.darkenColor(hex, 0.3);
      };
      img.onerror = () => {
        this.mainColor = '#42b983';
        this.mainColorDark = '#2f9465';
      };
      img.src = imgUrl;
    },
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1,3),16)*(1-amount);
      const g = parseInt(hex.slice(3,5),16)*(1-amount);
      const b = parseInt(hex.slice(5,7),16)*(1-amount);
      return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`;
    },
    lightenColor(hex, amount) {
      const r = Math.min(255, parseInt(hex.slice(1,3),16)*(1+amount));
      const g = Math.min(255, parseInt(hex.slice(3,5),16)*(1+amount));
      const b = Math.min(255, parseInt(hex.slice(5,7),16)*(1+amount));
      return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`;
    },

    // ===== ✅ 核心新增：通用时长格式化方法 秒数 → xxhxxmin 格式 =====
    formatSecondsToHourMin(seconds) {
      // 兼容 空/0/负数/字符串格式的秒数
      if (!seconds || isNaN(seconds) || Number(seconds) <= 0) {
        return '0h0min';
      }
      const totalSeconds = Number(seconds);
      const hours = Math.floor(totalSeconds / 3600); // 1小时=3600秒
      const minutes = Math.floor((totalSeconds % 3600) / 60); // 剩余的秒数转分钟
      return `${hours}h${minutes}min`;
    },

    // 日历接口请求方法
    async fetchCalendarReviewData() {
      this.loading = true;
      try {
        const res = await this.$axios.get('/api/album/review/calendar');
        if (res.data && res.data.code === 200) {
          this.reviewRecordData = res.data.data || [];
        } else {
          this.$message?.warning(res.data?.msg || '获取日历数据失败');
          this.reviewRecordData = [];
        }
      } catch (err) {
        console.error('日历接口请求失败：', err);
        this.$message?.error('网络异常，日历数据加载失败');
        this.reviewRecordData = [];
      } finally {
        this.loading = false;
      }
    },

    // 计算当月统计数据
    calcCurrentMonthStat() {
      const currentMonthRecords = this.reviewRecordData.filter(item =>
        item.year === this.currentYear && item.month === this.currentMonth
      );
      this.totalReviewCount = currentMonthRecords.length;

      if (currentMonthRecords.length > 0) {
        const totalScore = currentMonthRecords.reduce((sum, item) => sum + (item.score || 0), 0);
        this.avgScore = (totalScore / currentMonthRecords.length).toFixed(1);
        const sortedList = [...currentMonthRecords].sort((a, b) => {
          return new Date(b.year, b.month-1, b.day) - new Date(a.year, a.month-1, a.day);
        });
        const last = sortedList[0];
        this.lastWriteDate = `${last.year}-${last.month.toString().padStart(2,0)}-${last.day.toString().padStart(2,0)}`;
      } else {
        this.avgScore = '0.0';
        this.lastWriteDate = '暂无记录';
      }
    },

    // 日历核心功能方法
    initCalendar() {
      this.selectedDay = null;
      const daysInMonth = new Date(this.currentYear, this.currentMonth, 0).getDate();
      const firstDayWeek = new Date(this.currentYear, this.currentMonth - 1, 1).getDay();
      this.emptyStartDays = firstDayWeek;
      this.currentMonthDays = [];
      for (let i = 1; i <= daysInMonth; i++) {
        this.currentMonthDays.push({ day: i });
      }
    },
    prevMonth() {
      if (this.currentMonth === 1) {
        this.currentYear -= 1;
        this.currentMonth = 12;
      } else {
        this.currentMonth -= 1;
      }
    },
    nextMonth() {
      if (this.currentMonth === 12) {
        this.currentYear += 1;
        this.currentMonth = 1;
      } else {
        this.currentMonth += 1;
      }
    },
    handleDayClick(day) {
      this.selectedDay = day;
    },
    hasRecordOnDay(day) {
      return this.reviewRecordData.some(item => item.year === this.currentYear && item.month === this.currentMonth && item.day === day);
    },
    getRecordCount(day) {
      return this.reviewRecordData.filter(item => item.year === this.currentYear && item.month === this.currentMonth && item.day === day).length;
    },
    getDayDetailList() {
      return this.reviewRecordData.filter(item => item.year === this.currentYear && item.month === this.currentMonth && item.day === this.selectedDay);
    },

    // ===== ✅ 核心修改：悬浮弹窗只传纯听后感内容 =====
    showTooltip(e, text) {
      this.tooltipVisible = true;
      this.tooltipText = text || '暂无听后感内容';
      this.tooltipX = e.pageX;
      this.tooltipY = e.pageY;
    },
    hideTooltip() {
      this.tooltipVisible = false;
      this.tooltipText = '';
    },

    // 业务方法
    async handleAddReview() {
      await this.$emit('add-review', this.newFeelingContent);
      this.newFeelingContent = '';
      this.fetchCalendarReviewData();
    },
    async handleDeleteSingle(feelingId) {
      await this.$emit('delete-single', feelingId);
      this.fetchCalendarReviewData();
    },
    async handleDeleteAll() {
      await this.$emit('delete-all');
      this.fetchCalendarReviewData();
    }
  }
};
</script>

<style scoped>
/* 核心布局：父容器 flex 实现 左40% 右60% */
.tab-content-container {
  display: flex;
  gap: 20px;
  width: 100%;
  box-sizing: border-box;
}
/* 左侧容器 完整flex垂直布局，height/max-height固定，内部元素高度自适应分配 */
.calendar-statistics {
  width: 40%;
  background: #f9f9f9;
	padding: 15px;
	border-radius: 8px;
	border: 1px solid #eee;
	box-sizing: border-box;
	height: 700px;
	max-height: 700px;
	position: relative;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}
.calendar-statistics h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
	font-weight: 500;
  flex-shrink: 0;
}
/* 日历头部 箭头+月份 */
.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: center;
	font-size: 15px;
	color: #333;
	margin-bottom: 10px;
	font-weight: 500;
  flex-shrink: 0;
}
.arrow-btn {
  background: transparent;
	border: none;
	font-size: 16px;
	cursor: pointer;
	padding: 0 8px;
}
.arrow-btn:hover {
  opacity: 0.7;
}
/* ✅ 星期栏 宽度100%+无间距+7列均分，和下方日期严格同尺寸对齐 */
.calendar-week {
  display: flex;
  width: 100%;
  margin-bottom: 8px;
  flex-shrink: 0;
}
.week-item {
  width: calc(100% / 7);
  text-align: center;
	font-size: 12px;
	color: #666;
}
/* ✅ 日历主体 核心关键 - 每行只显7个日期，永不折行 */
.calendar-days {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  margin-bottom: 10px;
  flex-shrink: 0;
  padding: 2px;
}
/* ✅ 日期格子 精准宽度+内间距替代外间距，每行必显7个，和星期一一对应 */
.day-item {
  width: calc(100% / 7);
  height: 40px;
	border-radius: 6px;
	border:1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  position: relative;
  cursor: pointer;
  transition: all 0.2s;
  box-sizing: border-box;
  padding: 0 2px;
  margin: 2px 0;
}
.day-item.empty {
  background: transparent;
	border: none;
	cursor: default;
}
.day-item.hasRecord {
  font-weight: 500;
}
.day-item.active {
  transform: scale(1.08);
	box-shadow: 0 0 8px rgba(66, 185, 131, 0.4);
  background-color: v-bind(mainColor) !important;
  color: #fff;
  border-color: v-bind(mainColor) !important;
}
.day-item:hover:not(.empty) {
  transform: scale(1.05);
}
.record-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 14px;
	height: 14px;
	border-radius: 50%;
	color: #fff;
	font-size: 8px;
	display: flex;
	align-items: center;
	justify-content: center;
}

/* 听后感详情区 - 滚动正常无遮挡 */
.day-detail-list {
  width: 100%;
  margin-top: 5px;
  box-sizing: border-box;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.day-detail-list h4 {
  margin: 0 0 8px 0;
  padding: 0;
	line-height: 1.2;
  flex-shrink: 0;
}
.detail-scroll-box {
  width: 100%;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: #ccc #f5f5f5;
  scroll-behavior: smooth;
}
.detail-scroll-box:hover {
  scrollbar-color: v-bind(mainColor) #f5f5f5;
}
.detail-scroll-box::-webkit-scrollbar {
  width: 6px;
}
.detail-scroll-box::-webkit-scrollbar-track {
  background: #f5f5f5;
	border-radius: 3px;
}
.detail-scroll-box::-webkit-scrollbar-thumb {
  background: #ccc;
	border-radius: 3px;
}
.detail-scroll-box::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColor);
}

.detail-item {
  background: #fff;
	padding: 10px;
	border-radius: 6px;
	border:1px solid #eee;
	margin-bottom: 8px;
	cursor: pointer;
	transition: all 0.2s;
}
.detail-item:last-child {
  margin-bottom: 0;
}
.detail-item:hover {
  border-color: v-bind(mainColor);
  background: #fcfcfc;
}
.album-name {
  font-size: 13px;
  color: #333;
  font-weight: 500;
  margin-bottom: 4px;
}
.album-score {
  font-size: 12px;
	color: #666;
}
.album-score span {
  color: #e6a23c;
	font-weight: 500;
}

/* 悬浮弹窗 - 纯听后感内容展示 */
.tooltip-box {
  position: fixed;
  z-index: 99999;
  background: #fff;
	padding: 12px 15px;
	border-radius: 8px;
	box-shadow: 0 2px 15px rgba(0,0,0,0.18);
	border: 1px solid #eee;
	pointer-events: none;
	word-break: break-all;
	line-height: 1.6;
	max-height: 400px;
	max-width: 380px;
	overflow-y: auto;
  transform: translate(-5px, -5px);
}
.tooltip-content {
  font-size: 13px;
  color: #333;
}

/* 统计概览样式 */
.stat-overview {
  margin-top: 15px;
	padding-top: 12px;
	border-top: 1px solid #eee;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stat-item {
  font-size: 13px;
  color: #666;
	margin-bottom: 8px;
}
.stat-item span {
  color: #333;
	font-weight: 500;
	margin-left: 5px;
}

/* 右侧听后感编辑区 60% */
.review-content {
  width: 60%;
  box-sizing: border-box;
}
.audio-link {
  color: #007acc;
  margin: 10px 0;
	font-size: 14px;
}
.review-edit-area {
  margin: 20px 0;
}
.review-textarea {
  width: 100%;
	padding: 10px;
	border: 1px solid #ddd;
	border-radius: 8px;
	font-size: 14px;
	resize: vertical;
	margin-bottom: 10px;
}
.review-actions {
  margin-bottom: 15px;
}
.save-btn {
	padding: 8px 20px;
	color: #fff;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	margin-right: 10px;
	transition: all 0.2s;
}
.save-btn:disabled {
	cursor: not-allowed;
	opacity: 0.7;
}
.save-btn:hover:not(:disabled) {
	background-color: #257d51 !important;
	opacity: 0.95;
}
.delete-btn {
	padding: 8px 20px;
	color: #fff;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	transition: all 0.2s;
}
.delete-btn:hover {
	background-color: #257d51 !important;
	opacity: 0.95;
}
.feelings-list {
  margin: 20px 0;
}
.feeling-item {
	background: #f9f9f9;
	padding: 15px;
	border-radius: 8px;
	margin-bottom: 10px;
	border: 1px solid #eee;
  position: relative;
  min-height: 100px;
  box-sizing: border-box;
}
.feeling-top {
  display: flex;
  align-items: center;
  gap: 10px;
	margin-bottom: 12px;
}
.create-time {
	font-size: 12px;
	color: #999;
}
.feeling-score {
	font-size: 12px;
	color: #666;
	font-weight: 500;
}
.feeling-content {
	color: #333;
	line-height: 1.6;
	font-size: 14px;
  margin-bottom: 20px;
}
.listening-duration {
  position: absolute;
	left: 15px;
	bottom: 15px;
	font-size: 12px;
	color: #999;
}
.delete-single-btn {
	padding: 4px 8px;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	font-size: 12px;
	transition: all 0.2s;
  position: absolute;
	right: 15px;
	bottom: 15px;
}
.delete-single-btn:hover {
	background-color: #257d51 !important;
	opacity: 0.95;
}
.no-feeling {
	color: #999;
	text-align: left;
	margin: 20px 0;
	font-size: 14px;
}
</style>