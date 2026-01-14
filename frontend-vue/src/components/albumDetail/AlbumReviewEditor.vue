<template>
  <div class="tab-content-container">
    <!-- 左侧 40% 区域 - 日历统计小组件【固定高度+滚动+悬停弹窗】 -->
    <div class="calendar-statistics">
      <!-- 日历头部：年月居左 + 左右箭头全部居右 + 三角箭头替换 -->
      <div class="calendar-header">
        <span class="calendar-month">{{ currentYear }}年 {{ currentMonth < 10 ? '0' + currentMonth : currentMonth }}月</span>
        <div class="arrow-group">
          <button class="arrow-btn" @click="prevMonth" :style="{ color: mainColor }">
            ◀
          </button>
          <button class="arrow-btn" @click="nextMonth" :style="{ color: mainColor }">
            ▶
          </button>
        </div>
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
      <!-- 日历主体 - ✅今日+选中日期 均为圆形高亮 + 数量角标改为圆角矩形 -->
      <div class="calendar-days">
        <div class="day-item empty" v-for="empty in emptyStartDays" :key="'empty'+empty"></div>
        <div
          class="day-item"
          v-for="day in currentMonthDays"
          :key="day.day"
          :class="{
            hasRecord: hasRecordOnDay(day.day),
            active: selectedDay === day.day,
            today: isToday(day.day)
          }"
          :style="hasRecordOnDay(day.day) ? { backgroundColor: lightenColor(mainColor, 0.7) } : {}"
          @click="handleDayClick(day.day)"
        >
          <span class="day-num">{{ day.day }}</span>
          <span class="record-badge" v-if="hasRecordOnDay(day.day)" :style="{ backgroundColor: mainColorDark }">
            {{ getRecordCount(day.day) }}
          </span>
        </div>
      </div>

      <!-- 点击高亮日期展示：当日听后感详情列表 -->
      <div class="day-detail-list" v-if="selectedDay && hasRecordOnDay(selectedDay)">
        <h4 :style="{ color: mainColorDark, margin: '15px 0 10px 0', fontSize: '14px', fontWeight: 'bold' }">
          {{ currentYear }}-{{ currentMonth <10 ? '0'+currentMonth : currentMonth }}-{{ selectedDay <10 ? '0'+selectedDay : selectedDay }} 听后感详情
        </h4>
        <!-- ✅ 核心修改：听后感详情滚动容器 新增专属样式 进度条居左+匹配可选标签样式 -->
        <div class="detail-scroll-box">
          <div
            class="detail-item"
            v-for="(item, idx) in getDayDetailList()"
            :key="item.feeling_id || idx"
            @mouseenter="showTooltip($event, item.content)"
            @mouseleave="hideTooltip()"
          >
            <div class="album-name">{{ item.albumName }} <span>{{item.singer}}</span></div>
            <div class="album-score">评分：<span>{{ item.score }}</span></div>
            <!-- ✅ 新增时长容器，用于承载横线样式 -->
            <div class="detail-duration-wrapper">
            </div>
          </div>
        </div>
      </div>

      <!-- 无选中/无记录时展示：统计概览 -->
      <div class="stat-overview" v-else>
        <div class="stat-item" v-if="loading">加载统计数据中...</div>
      </div>

      <!-- 听后感悬浮预览弹窗 -->
      <div
        v-if="tooltipVisible"
        class="tooltip-box"
        :style="{
          left: `${tooltipX}px`,
          top: `${tooltipY}px`,
          maxWidth: '380px'
        }"
      >
        <div class="tooltip-content">{{ tooltipText }}</div>
      </div>
    </div>

    <!-- 右侧 60% 区域 - ✅ 蒙版和评论输入框一致 + 纯净无按钮遮挡 -->
    <div class="review-content">

      <!-- ✅ 历史听后感列表 -->
      <div class="feelings-list" v-if="sortedFeelingsList.length">
        <!-- ✅ 核心修改：右侧滚动容器样式和左侧完全统一 -->
        <div class="feelings-scroll-box">
          <div
            class="feeling-item"
            v-for="(feeling, idx) in sortedFeelingsList"
            :key="feeling.id || idx"
          >
            <div class="feeling-top">
              <span class="create-time">{{ feeling.create_time }}</span>
              <span class="feeling-score">{{ feeling.my_score || 0 }}分</span>
            </div>
            <div class="feeling-content">{{ feeling.content }}</div>
            <div class="duration-wrapper">
              <div class="listening-duration">已听{{ formatSecondsToHourMin(feeling.listening_duration) }}</div>
            </div>
            <button class="delete-single-btn" @click="handleDeleteSingle(feeling.id)">删除</button>
          </div>
        </div>
      </div>
      <p class="no-feeling" v-else>暂无听后感记录，快来添加吧~</p>

      <!-- ✅ 听后感输入框 去掉所有边界颜色 纯净透明 + 右上角提交按钮【核心修复】 -->
      <div class="review-edit-area">
        <textarea
          v-model="newFeelingContent"
          placeholder="输入听后感..."
          class="review-textarea"
          rows="3"
        ></textarea>
        <!-- ✅ 按钮移出列表、放到输入框容器内 → 永久显示 + 固定在右上角 -->
        <button
          @click="handleAddReview"
          class="save-btn"
          :disabled="!newFeelingContent.trim()"
        >新增听后感</button>
      </div>
    </div>
  </div>
</template>

<script>
import {calculateAlbumTotalScore} from "@/utils/scoreCalc";

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
      mainColor: 'transparent',
      mainColorDark: 'transparent',
      mainColorDarkDouble: 'transparent', // ✅ 双层深色 用于滚动条配色
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
      lastWriteDate: '暂无记录',
      // 今日日期
      todayDate: new Date().getDate()
    };
  },
  computed: {
    sortedFeelingsList() {
      const feelings = (this.album.review || {}).feelings || [];
      return [...feelings].sort((a, b) => {
        return new Date(b.create_time) - new Date(a.create_time);
      });
    }
  },
  watch: {
    album: {
      immediate: true,
      handler(newVal) {
        if(newVal.cover_img) this.extractMainColor(newVal.cover_img);
        else {
          this.mainColor = '#42b983';
          this.mainColorDark = '#2f9465';
          this.mainColorDarkDouble = '#257d51';
        }

       if (newVal.my_score) {
        console.log('AlbumReviewEditor: album.my_score 更新为', newVal.my_score);
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
    extractMainColor(imgUrl) {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 10;
        canvas.height = 10;
        ctx.drawImage(img, 0, 0, 10, 10);
        const data = ctx.getImageData(0, 0, 10, 10).data;
        let r = 0, g = 0, b = 0, c = 0;
        for (let i = 0; i < data.length; i += 4) {
          r += data[i];
          g += data[i + 1];
          b += data[i + 2];
          c++
        }
        r = Math.floor(r / c);
        g = Math.floor(g / c);
        b = Math.floor(b / c);
        const hex = `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
        this.mainColor = hex;
        this.mainColorDark = this.darkenColor(hex, 0.3);
        this.mainColorDarkDouble = this.darkenColor(hex, 0.5); // ✅ 同步双层深色
      };
      img.onerror = () => {
        this.mainColor = '#42b983';
        this.mainColorDark = '#2f9465';
        this.mainColorDarkDouble = '#257d51';
      };
      img.src = imgUrl;
    },
    darkenColor(hex, amount) {
      const r = parseInt(hex.slice(1, 3), 16) * (1 - amount);
      const g = parseInt(hex.slice(3, 5), 16) * (1 - amount);
      const b = parseInt(hex.slice(5, 7), 16) * (1 - amount);
      return `#${Math.round(r).toString(16).padStart(2, '0')}${Math.round(g).toString(16).padStart(2, '0')}${Math.round(b).toString(16).padStart(2, '0')}`;
    },
    lightenColor(hex, amount) {
      const r = Math.min(255, parseInt(hex.slice(1, 3), 16) * (1 + amount));
      const g = Math.min(255, parseInt(hex.slice(3, 5), 16) * (1 + amount));
      const b = Math.min(255, parseInt(hex.slice(5, 7), 16) * (1 + amount));
      return `#${Math.round(r).toString(16).padStart(2, '0')}${Math.round(g).toString(16).padStart(2, '0')}${Math.round(b).toString(16).padStart(2, '0')}`;
    },
    formatSecondsToHourMin(seconds) {
      if (!seconds || isNaN(seconds) || Number(seconds) <= 0) {
        return '0h0min';
      }
      const totalSeconds = Number(seconds);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      return `${hours}h${minutes}min`;
    },
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
    calcCurrentMonthStat() {
      const currentMonthRecords = this.reviewRecordData.filter(item =>
          item.year === this.currentYear && item.month === this.currentMonth
      );
      this.totalReviewCount = currentMonthRecords.length;

      if (currentMonthRecords.length > 0) {
        const totalScore = currentMonthRecords.reduce((sum, item) => sum + (item.score || 0), 0);
        this.avgScore = (totalScore / currentMonthRecords.length).toFixed(1);
        const sortedList = [...currentMonthRecords].sort((a, b) => {
          return new Date(b.year, b.month - 1, b.day) - new Date(a.year, a.month - 1, a.day);
        });
        const last = sortedList[0];
        this.lastWriteDate = `${last.year}-${last.month.toString().padStart(2, 0)}-${last.day.toString().padStart(2, 0)}`;
      } else {
        this.avgScore = '0.0';
        this.lastWriteDate = '暂无记录';
      }
    },
    initCalendar() {
      this.selectedDay = null;
      const daysInMonth = new Date(this.currentYear, this.currentMonth, 0).getDate();
      const firstDayWeek = new Date(this.currentYear, this.currentMonth - 1, 1).getDay();
      this.emptyStartDays = firstDayWeek;
      this.currentMonthDays = [];
      for (let i = 1; i <= daysInMonth; i++) {
        this.currentMonthDays.push({day: i});
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
  const dayRecords = this.reviewRecordData.filter(
      item =>
          item.year === this.currentYear &&
          item.month === this.currentMonth &&
          item.day === this.selectedDay
  );
  const correctFeelings = this.album.review?.feelings || [];
  const matchList = dayRecords.map(record => {
    const matchItem = correctFeelings.find(f => f.id === record.id);
    return matchItem
        ? {...matchItem, listening_duration: matchItem.listening_duration}
        : record;
  });
  // ========== 核心修改 - 替换原有的时长排序 ==========
  // 按 创建时间(create_time) 倒序排序 → 最新的在最上面

  return matchList.sort((a, b) => {
    return new Date(b.create_time) - new Date(a.create_time);
  });
  // ==================================================
},
    isToday(day) {
      const now = new Date()
      return now.getFullYear() === this.currentYear && now.getMonth() + 1 === this.currentMonth && now.getDate() === day
    },
    showTooltip(e, text) {
      this.tooltipVisible = true;
      this.tooltipText = text || '暂无听后感内容';
      this.tooltipX = e.clientX - 200;   // 右移 12px，不挡鼠标
      this.tooltipY = e.clientY + 50;   // 下移 12px
    },
    hideTooltip() {
      this.tooltipVisible = false;
      this.tooltipText = '';
    },
// AlbumReviewEditor.vue 中 handleAddReview 方法（已优化）
async handleAddReview() {
  if (!this.newFeelingContent.trim()) {
    this.$message?.warning('听后感内容不能为空！');
    return;
  }

  // 1. 通知父组件保存并获取最新评分（确保scoreList已同步到album.my_score）
  await this.$emit('prepare-score');

  // 2. 读取父组件同步后的 album.my_score（就是最新的scoreList）
  let scoreList = [];
  if (this.album.my_score) {
    if (typeof this.album.my_score === 'string') {
      try {
        scoreList = JSON.parse(this.album.my_score);
      } catch (err) {
        scoreList = [];
      }
    } else if (Array.isArray(this.album.my_score)) {
      // 深拷贝，避免引用问题
      scoreList = JSON.parse(JSON.stringify(this.album.my_score));
    }
  }

  console.log('🎯 子组件使用的最新scoreList（来自album.my_score）：', scoreList);
  const finalScore = calculateAlbumTotalScore(scoreList);
  console.log('🎯 计算出的综合评分：', finalScore);

  // 3. 提交听后感，传递最新计算的评分
  await this.$emit('add-review', this.newFeelingContent, finalScore);

  // 4. 重置和刷新
  this.newFeelingContent = '';
  this.fetchCalendarReviewData();
  this.$forceUpdate();
},
    async handleDeleteSingle(feelingId) {
      await this.$emit('delete-single', feelingId);
      this.fetchCalendarReviewData();
    },
    formatMinSecToHourMin(minSecStr = '') {
      if (!minSecStr || !/^\d{1,3}:\d{2}$/.test(minSecStr)) return '0h0min';
      const [min, sec] = minSecStr.split(':').map(Number);
      const totalSec = min * 60 + sec;
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      return `${h}h${m}min`;
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

/* 左侧容器 ✅ 透明纯净 无任何边框/分割线 */
.calendar-statistics {
  width: 40%;
  background: transparent;
  padding: 15px;
  border-radius: 8px;
  border: none;
  box-sizing: border-box;
  height: 700px;
  max-height: 700px;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ✅ 年月标题和Tab页单曲列表格式完全一致 */
.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: center;
  font-size: 16px;
  color: v-bind(mainColorDark);
  margin-bottom: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.calendar-month {
  font-size: inherit;
  font-weight: inherit;
  color: inherit;
}

.arrow-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.arrow-btn {
  color: v-bind(mainColorDark) !important;
  background: transparent;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 0 8px;
  line-height: 1;
}

.arrow-btn:hover {
  opacity: 0.7;
}

/* ✅ 星期栏 日/一/二 → 颜色=mainColorDark + 加粗 */
.calendar-week {
  display: flex;
  width: 100%;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.week-item {
  width: calc(100% / 7);
  text-align: center;
  font-size: 13px;
  color: v-bind(mainColorDark) !important;
  font-weight: bold !important;
}

/* 日历主体 行列间距一致 */
.calendar-days {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  margin-bottom: 10px;
  flex-shrink: 0;
  gap: 2px;
  padding: 0;
}

/* ✅ 去掉每个日期的白色边界 + 日期数字 颜色=mainColorDark + 加粗 */
.day-item {
  width: calc((100% - 12px) / 7);
  aspect-ratio: 1 / 1;
  min-height: 36px;
  border-radius: 6px;
  border: none !important;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  position: relative;
  cursor: pointer;
  transition: all 0.2s;
  box-sizing: border-box;
  padding: 0 2px;
  margin: 0;
  color: v-bind(mainColorDark) !important;
  font-weight: bold !important;
}

.day-item.empty {
  background: transparent;
  border: none;
  cursor: default;
}

.day-item.hasRecord {
  border-radius: 50% !important;
  font-weight: bold;
}

.day-item.today {
  border-radius: 50% !important;
  background-color: v-bind(mainColorDark) !important;
  color: #fff !important;
  transform: none !important;
}

.day-item.active {
  border-radius: 50% !important;
  background-color: v-bind(mainColor) !important;
  color: #fff !important;
  transform: none !important;
}

.day-item:hover:not(.empty):not(.active):not(.today) {
  transform: scale(1.05);
  background-color: rgba(47, 148, 101, 0.05);
}

/* 听后感数量角标 圆角小矩形 */
.record-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  padding: 0 4px;
  height: 12px;
  border-radius: 4px;
  color: #fff;
  font-size: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

/* 听后感详情区 - 透明无样式 */
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

/* ✅✅✅ 核心修改1：左侧听后感详情滚动条 - 无三角+样式统一 ✅✅✅ */
.detail-scroll-box {
  width: 100%;
  color: v-bind(mainColorDarkDouble) !important;
  background: transparent !important;
  white-space: pre-wrap;
  word-wrap: break-word;
  border: none !important;
  overflow-y: auto;
  overflow-x: hidden;
  direction: rtl; /* 核心：反向排版，让滚动条到左侧 */
  text-align: left; /* 强制文字还是左对齐，不影响阅读 */
  padding-left: 10px; /* 给左侧滚动条预留位置，防止遮挡文字 */
}

/* 强制内容左对齐 */
.detail-scroll-box > div {
  direction: ltr;
}

/* 滚动条轨道 - 透明无样式 */
.detail-scroll-box::-webkit-scrollbar-track {
  background: transparent !important;
  border-radius: 2px;
}

/* 滚动条宽度 - 4px 统一 */
.detail-scroll-box::-webkit-scrollbar {
  width: 4px !important;
}

/* 滚动条滑块 - 颜色+圆角统一 */
.detail-scroll-box::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble) !important;
  border-radius: 2px !important;
}

/* 隐藏webkit滚动条三角按钮 */
.detail-scroll-box::-webkit-scrollbar-button {
  display: none !important;
}

/* ✅ 去掉详情列表每个元素的白色边界 透明纯净 */
.detail-item {
  background: transparent;
  padding: 10px;
  border-radius: 6px;
  border: none !important;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-item:hover {
  background: rgba(47, 148, 101, 0.05);
}

/* ✅ 核心修改：专辑名 加粗放大 */
.album-name {
  font-size: 16px;
  color: v-bind(mainColorDark) !important;
  font-weight: 600;
  margin-bottom: 4px;
  line-height: 1.6;
}

.album-name span {
  font-size: 14px;
  color: v-bind(mainColorDark) !important;
  font-weight: 400;
}

.album-score {
  font-size: 14px;
  color: v-bind(mainColorDark) !important;
  font-weight: 400;
  line-height: 1.6;
}

.album-score span {
  color: v-bind(mainColorDark) !important;
  font-weight: 400;
}

.duration-text {
  font-size: 14px;
  color: v-bind(mainColorDark) !important;
  font-weight: 400;
  line-height: 1.6;
}

/* ✅ 核心修改：左侧时长横线容器，和右侧duration-wrapper样式完全一致 */
.detail-duration-wrapper {
  position: relative;
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
  margin-top: 8px;
}

.detail-duration-wrapper::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
}

/* ✅✅✅ 悬浮弹窗样式：透明+蒙版+和评分同色文字 ✅✅✅ */
.tooltip-box {
  position: fixed;
  z-index: 99999;
  /* 透明底色+蒙版，和输入框样式完全一致 */
  background: rgba(255, 255, 255, 0.5) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  padding: 12px 15px;
  border-radius: 8px;
  box-shadow: 0 2px 15px rgba(0, 0, 0, 0.18);
  border: none !important;
  pointer-events: none;
  word-break: break-all;
  line-height: 1.6;
  max-height: 400px;
  max-width: 380px;
  overflow-y: auto;
  /* 移除手动偏移，完全跟随鼠标坐标 */
  transform: none !important;
}

.tooltip-content {
  font-size: 13px;
  /* 弹窗内文字颜色 和评分字体颜色完全一致 */
  color: v-bind(mainColorDarkDouble) !important;
  font-weight: 400;
  line-height: 1.6;
}

/* 悬浮弹窗滚动条也隐藏三角 */
.tooltip-box::-webkit-scrollbar-button {
  display: none !important;
}

.tooltip-box::-webkit-scrollbar {
  width: 4px !important;
}

.tooltip-box::-webkit-scrollbar-track {
  background: transparent !important;
}

.tooltip-box::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble) !important;
  border-radius: 2px;
}

/* ✅ 统计概览 本月总条数/平均评分/最近编写 全部 颜色=mainColorDark + 加粗 */
.stat-overview {
  margin-top: 15px;
  padding-top: 12px;
  border: none;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: transparent;
}

.stat-item {
  font-size: 13px;
  color: v-bind(mainColorDark) !important;
  font-weight: bold !important;
  margin-bottom: 10px;
}

.stat-item span {
  color: v-bind(mainColorDark) !important;
  font-weight: bold !important;
  margin-left: 5px;
}

/* 右侧 60% 区域 */
.review-content {
  width: 60%;
  box-sizing: border-box;
  height: 700px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.feelings-list {
  flex: 1;
  margin-bottom: 20px;
  overflow: hidden;
  position: relative;
}

/* ✅✅✅ 核心修改2：右侧听后感列表滚动条 - 和左侧完全统一+无三角 ✅✅✅ */
.feelings-scroll-box {
  height: 100%;
  color: v-bind(mainColorDarkDouble) !important;
  background: transparent !important;
  white-space: pre-wrap;
  word-wrap: break-word;
  border: none !important;
  overflow-y: auto;
  overflow-x: hidden;
  text-align: left; /* 强制文字还是左对齐，不影响阅读 */
  padding-left: 10px; /* 给左侧滚动条预留位置，防止遮挡文字 */
}

/* 滚动条轨道 - 透明 */
.feelings-scroll-box::-webkit-scrollbar-track {
  background: transparent !important;
  border-radius: 2px;
}

/* 滚动条宽度 - 4px */
.feelings-scroll-box::-webkit-scrollbar {
  width: 4px !important;
}

/* 滚动条滑块 - 双层深色+圆角 */
.feelings-scroll-box::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble) !important;
  border-radius: 2px !important;
}

/* 隐藏webkit滚动条三角按钮 */
.feelings-scroll-box::-webkit-scrollbar-button {
  display: none !important;
}

.feeling-item {
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  position: relative;
  box-sizing: border-box;
  background: transparent !important;
  border: none !important;
}

.feeling-top {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  flex-wrap: nowrap;
  background: transparent !important;
}

.create-time {
  font-size: 15px;
  color: v-bind(mainColorDark) !important;
  font-weight: 600;
  line-height: 1;
  background: transparent;
  padding: 0;
  margin: 0;
  position: relative;
}

.feeling-score {
  font-size: 15px;
  color: v-bind(mainColorDark) !important;
  font-weight: 600;
  line-height: 1;
  background: transparent;
  padding: 0;
  margin: 0;
  position: relative;
}

.feeling-content {
  line-height: 1.6;
  margin-bottom: 0;
  font-size: 14px;
  font-weight: 400;
  padding: 8px;
  border-radius: 4px;
  color: v-bind(mainColorDarkDouble) !important;
  background: transparent !important;
}

.duration-wrapper {
  position: relative;
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
  margin-top: 8px;
}

.listening-duration {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
  color: v-bind(mainColorDark) !important;
  background: transparent !important;
  position: static;
  margin: 0;
  padding: 0;
}

.duration-wrapper::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
}

/* ✅ 删除按钮样式 - 统一样式到css，方便复用 */
.delete-single-btn {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  position: absolute;
  right: 15px;
  bottom: 15px;
  color: #ffffff;
  background-color: v-bind(mainColorDark) !important;
}

.delete-single-btn:hover {
  opacity: 0.95;
  filter: brightness(0.9);
}

.no-feeling {
  font-size: 15px;
  font-weight: 600;
  margin: 5px 0;
  text-align: center;
  padding: 30px 0;
  background: transparent !important;
  color: v-bind(mainColorDark) !important;
}

/* ✅ 核心修改：输入框彻底去掉所有边界颜色，纯净透明无任何边框 + 相对定位承载按钮 */
.review-edit-area {
  width: 100%;
  box-sizing: border-box;
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 0;
  background: rgba(255, 255, 255, 0.03) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: none !important;
  position: relative; /* 关键：给按钮做绝对定位的父容器 */
}

.review-textarea {
  width: 100%;
  padding: 6px 10px;
  border: none !important;
  outline: none !important;
  border-radius: 4px;
  resize: vertical;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
  background: transparent !important;
  color: v-bind(mainColorDark) !important;
  font-family: inherit;
}

.review-textarea::placeholder {
  color: v-bind(mainColorDark) !important;
  opacity: 0.8;
  font-weight: 400;
}

/* ✅✅✅ 按钮样式修改：固定在输入框右上角 + 完美间距 + 样式不变 */
.save-btn {
  position: absolute;
  top: 6px; /* 和输入框padding一致，垂直对齐 */
  right: 10px; /* 和输入框padding一致，水平对齐 */
  padding: 8px 20px;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
  background-color: v-bind(mainColorDark) !important;
  z-index: 10;
}

.save-btn:disabled {
  background: #999 !important;
  cursor: not-allowed;
  opacity: 0.7;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.95;
  filter: brightness(0.9);
}
</style>