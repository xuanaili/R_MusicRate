<template>
  <div class="tag-detail-container">
    <!-- 全屏模糊背景层【和首页保持一致】 -->
    <div class="bg-layer" :style="bgStyle"></div>

    <div v-if="loading" class="loading-container">
      <div class="loading-text">正在加载标签详情...</div>
    </div>

    <div v-else-if="!tagInfo" class="empty-container">
      <div class="empty-text">未找到该标签的相关信息</div>
      <button class="back-btn" @click="$router.go(-1)">返回上一页</button>
    </div>

    <!-- 磨砂玻璃容器【和首页nav-mask-container风格统一】 -->
    <div v-else class="tag-detail-mask">
      <div class="tag-detail-content">
        <!-- 顶部导航栏 -->
        <div class="header-nav">
          <!-- 左侧：父标签展示 -->
          <div class="parent-tags-wrapper">
            <div class="parent-tags" v-if="parentTags.length">
              <router-link
                v-for="(tag, index) in parentTags"
                :key="tag.id"
                :to="{ path: '/tag-detail', query: { tagName: tag.tags_name } }"
                class="parent-tag-item"
              >
                {{ tag.tags_name }}
                <span class="plus-sign" v-if="index < parentTags.length - 1">+</span>
              </router-link>
            </div>
            <!-- 无父标签时占位 -->
            <div class="parent-tags-placeholder" v-else>&nbsp;</div>
          </div>

          <!-- 右侧：操作按钮 -->
          <div class="header-actions">
            <button class="back-btn" @click="$router.go(-1)">返回上一页</button>
            <button
              v-if="isAdmin"
              class="edit-tag-btn"
              @click="handleOpenEditTagSidebar"
            >
              ✏️ 编辑标签
            </button>
          </div>
        </div>

        <div class="tag-basic-info">
          <h1 class="tag-name">{{ tagInfo.tags_name }}</h1>
          <div v-if="tagInfo.aka_name" class="tag-aka">别名：{{ tagInfo.aka_name }}</div>
        </div>

        <!-- 简介 + 详细介绍 并排切换区域 -->
        <div class="intro-tabs-container" v-if="tagInfo.brief_intro || tagInfo.detail_intro">
          <!-- 切换按钮组 - 样式改为和升序降序一致 -->
          <div class="intro-tabs">
            <button
              class="intro-tab-item tab-item"
              :class="{active: introActiveTab === 'brief'}"
              @click="switchIntroTab('brief')"
            >
              简介
            </button>
            <button
              class="intro-tab-item tab-item"
              :class="{active: introActiveTab === 'detail'}"
              @click="switchIntroTab('detail')"
            >
              详情
            </button>
          </div>

          <!-- 内容展示区 -->
          <div class="intro-content-wrap">
            <div
              class="intro-panel brief-panel"
              v-if="tagInfo.brief_intro && introActiveTab === 'brief'"
            >
              <p>{{ tagInfo.brief_intro }}</p>
            </div>
            <div
              class="intro-panel detail-panel"
              v-if="tagInfo.detail_intro && introActiveTab === 'detail'"
            >
              <div class="intro-content" v-html="tagInfo.detail_intro"></div>
            </div>
          </div>
        </div>

        <!-- 气泡图 + 折线图 3:7 布局容器 -->
        <div class="charts-container">
          <!-- 气泡图区域 - 占3份 -->
          <div class="chart-col chart-col-3">
            <div class="tag-bubble-section">
              <TagBubbleChart
                :tagStats="tagBubbleStats"
                :loading="bubbleChartLoading"
                :mainColor="localMainColor"
                :mainColorDark="localMainColorDark"
                :mainColorDarkDouble="localMainColorDarkDouble"
                :sizeRange="{min: 50, max: 150}"
              >
                <template #empty>暂无该风格相关的标签数据</template>
              </TagBubbleChart>
            </div>
          </div>

          <!-- 折线图区域 - 占7份 -->
          <div class="chart-col chart-col-7">
            <div class="tag-album-chart" v-if="chartLoading">
              <div class="chart-loading">正在加载专辑统计数据...</div>
            </div>
            <div class="tag-album-chart" v-else>
              <div id="albumYearChart" style="width: 100%; height: 250px; background: white; padding: 10px; border-radius: 4px;"></div>
              <div v-show="albumYearList.length === 0" class="chart-empty">暂无该风格的专辑统计数据</div>
            </div>
          </div>
        </div>

        <!-- 专辑列表展示区块 -->
        <div class="album-list-container">
          <!-- 顶部操作区 -->
          <div class="all-actions-wrapper">
            <!-- 听状态筛选下拉 -->
            <div class="dropdown-btn-container">
              <button
                class="dropdown-btn"
                @click="toggleDropdown('listenStatus')"
              >
                {{ listenStatusMap[listenStatus] }}
                <span class="arrow-icon" :class="{active: dropdownShow.listenStatus}">▼</span>
              </button>
              <ul class="dropdown-options" v-show="dropdownShow.listenStatus">
                <li
                  v-for="(label, key) in listenStatusMap"
                  :key="key"
                  @click="handleListenStatusChange(key); toggleDropdown('listenStatus')"
                  :class="{active: listenStatus === key}"
                >
                  {{ label }}
                </li>
              </ul>
            </div>

            <!-- 排序方式下拉 -->
            <div class="dropdown-btn-container">
              <button
                class="dropdown-btn"
                @click="toggleDropdown('sortBy')"
              >
                {{ sortByMap[sortBy] }}
                <span class="arrow-icon" :class="{active: dropdownShow.sortBy}">▼</span>
              </button>
              <ul class="dropdown-options" v-show="dropdownShow.sortBy">
                <li
                  v-for="(label, key) in sortByMap"
                  :key="key"
                  @click="handleSortChange(key); toggleDropdown('sortBy')"
                  :class="{active: sortBy === key}"
                >
                  {{ label }}
                </li>
              </ul>
            </div>

            <!-- 升序/降序按钮 -->
            <div class="sort-options">
              <button
                class="tab-item sort-btn"
                :class="{active: sortOrder === 'asc'}"
                @click="handleOrderChange('asc')"
              >
                升序
              </button>
              <button
                class="tab-item sort-btn"
                :class="{active: sortOrder === 'desc'}"
                @click="handleOrderChange('desc')"
              >
                降序
              </button>
            </div>

            <!-- 每页条数下拉 -->
            <div class="dropdown-btn-container">
              <button
                class="dropdown-btn"
                @click="toggleDropdown('pageSize')"
              >
                {{ pageSize }}条
                <span class="arrow-icon" :class="{active: dropdownShow.pageSize}">▼</span>
              </button>
              <ul class="dropdown-options" v-show="dropdownShow.pageSize">
                <li
                  v-for="size in pageSizeOptions"
                  :key="size"
                  @click="handleSizeChange(size); toggleDropdown('pageSize')"
                  :class="{active: pageSize === size}"
                >
                  {{ size }}条
                </li>
              </ul>
            </div>

            <!-- 搜索区域 -->
            <div class="search-area">
              <!-- 年份筛选提示 -->
              <div v-if="selectedYear" class="year-filter-tip">
                已筛选：<span>{{ selectedYear }}年</span>
                <button @click="clearYearFilter" class="clear-year-btn">清空筛选</button>
              </div>

              <!-- 专辑名/歌手搜索框 -->
              <div class="search-container">
                <input
                  v-model="nameSingerKeyword"
                  type="text"
                  placeholder="搜索专辑名/歌手..."
                  class="search-input"
                  @keyup.enter="getAlbumList"
                >
                <button @click="getAlbumList" class="search-btn">搜索</button>
                <button v-if="nameSingerKeyword" @click="clearNameSingerSearch" class="clear-btn">清空</button>
              </div>
            </div>
          </div>

          <!-- 搜索结果列表 -->
          <div v-if="albumListLoading" class="loading-tip">加载中...</div>
          <div v-else-if="albumList.length === 0" class="empty-tip">
            {{ hasFilter ? '未找到匹配的专辑' : '暂无该风格的专辑数据' }}
          </div>
          <div v-else class="album-list">
            <div v-for="album in albumList" :key="album.id" class="album-item-wrapper">
              <AlbumPoolItem
                :album="album"
                :is-admin="isAdmin"
                :mainColor="mainColor"
                :mainColorDark="mainColorDark"
                :mainColorDarkDouble="mainColorDarkDouble"
                @copy-album="copyAlbum"
                @view-detail="viewAlbumDetail"
                @delete-album="deletePoolAlbum"
                @sendCoverBg="getCoverBgUrl"
                @sendThemeColor="getThemeColor"
              />
            </div>
          </div>

          <!-- 分页组件 -->
          <div class="pagination" v-show="pagination.total > 0">
            <button
              @click="changePage(1)"
              :disabled="pagination.page === 1 || albumListLoading"
              class="page-btn"
            >首页</button>
            <button
              @click="changePage(pagination.page - 1)"
              :disabled="pagination.page === 1 || albumListLoading"
              class="page-btn"
            >上一页</button>
            <div class="page-info-wrapper">
              <span class="page-info">
                第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页 (总 {{ pagination.total }} 条)
              </span>
            </div>
            <button
              @click="changePage(pagination.page + 1)"
              :disabled="pagination.page === pagination.total_pages || albumListLoading"
              class="page-btn"
            >下一页</button>
            <button
              @click="changePage(pagination.total_pages)"
              :disabled="pagination.page === pagination.total_pages || albumListLoading"
              class="page-btn"
            >尾页</button>
            <!-- 跳转页码 -->
            <div class="jump-page">
              <input
                type="number"
                v-model="jumpPageNum"
                min="1"
                :max="pagination.total_pages"
                placeholder="页码"
                class="page-input"
              >
              <button @click="jumpToPage()" class="jump-btn">跳转</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑标签侧边栏 -->
    <EditTag
      :visible="showEditTagSidebar"
      :main-color-dark="mainColorDark"
      :main-color-dark-double="mainColorDarkDouble"
      :edit-tag-data="tagInfo"
      :unique-uid="'edit-tag-detail'"
      @close="handleEditTagClose"
      @refresh="refreshTagDetail"
    />
  </div>
</template>

<script>
import axios from 'axios'
import EditTag from '@/components/sidebar/EditTag.vue'
import AlbumPoolItem from '@/components/item/AlbumPoolItem.vue'
import TagBubbleChart from '@/components/TagBubbleChart.vue'
import * as echarts from 'echarts/dist/echarts.min.js'

export default {
  name: 'TagDetail',
  components: {
    EditTag,
    AlbumPoolItem,
    TagBubbleChart
  },
  props: {
    mainColor: {
      type: String,
      default: 'transparent'
    },
    mainColorDark: {
      type: String,
      default: '#333'
    },
    mainColorDarkDouble: {
      type: String,
      default: '#111'
    }
  },
  data() {
    return {
      // 标签详情相关
      loading: true,
      tagInfo: null,
      parentTags: [], // 存储父标签列表
      relatedSingers: [],
      relatedAlbums: [],
      relatedTags: [],
      isAdmin: false,
      showEditTagSidebar: false,
      // 简介/详细介绍 切换控制 - 初始改为只显示简介
      introActiveTab: 'brief', // 初始值改为brief，默认只显示简介
      // 图表相关
      chartLoading: false,
      albumYearList: [],
      myChart: null,
      selectedYear: '', // 选中的年份
      // 气泡图相关
      bubbleChartLoading: false,
      tagBubbleStats: [], // 标签统计数据
      currentAlbumIds: [], // 核心：存储当前筛选后的专辑ID列表
      // 专辑列表相关
      nameSingerKeyword: '',
      albumList: [],
      allAlbumIds: [], // 新增：存储该标签下的所有专辑ID（不分页）
      albumListLoading: false,
      page: 1,
      pageSize: 10,
      pageSizeOptions: [5, 10, 20, 50],
      pagination: {
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0
      },
      sortBy: 'release_year',
      sortOrder: 'desc',
      jumpPageNum: 1,
      sortByMap: {
        album_name: '专辑名称',
        release_year: '发行年份',
        singer: '歌手'
      },
      // 听状态筛选
      listenStatus: 'all', // all:全部, listened:已听, unlistened:未听
      listenStatusMap: {
        all: '全部',
        listened: '已听',
        unlistened: '未听'
      },
      dropdownShow: {
        sortBy: false,
        pageSize: false,
        listenStatus: false
      },
      // 背景和主题色【和首页保持一致】
      coverBgUrl: localStorage.getItem('persistCoverBg') || '',
      localMainColor: 'transparent',
      localMainColorDark: '#333',
      localMainColorDarkDouble: '#111'
    }
  },
  computed: {
    // 判断是否有筛选条件
    hasFilter() {
      return this.nameSingerKeyword.trim() || this.selectedYear || this.listenStatus !== 'all'
    },
    // 获取当前标签名
    currentTagName() {
      return decodeURIComponent(this.$route.query.tagName || '')
    },
    // 背景样式【和首页完全一致】
    bgStyle() {
      if (this.coverBgUrl) {
        return {
          backgroundImage: `url(${this.coverBgUrl})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }
      } else {
        return { backgroundColor: 'transparent' }
      }
    }
  },
  created() {
    this.isAdmin = localStorage.getItem('is_admin') === '1'
    // 初始化主题色
    this.initThemeColor()
    if (this.currentTagName) {
      this.getTagDetail()
      this.getAlbumYearStats()
      this.getAlbumList() // 先加载专辑列表，再自动加载气泡图
    } else {
      this.loading = false
    }
  },
  watch: {
    '$route'() {
      if (this.currentTagName) {
        this.getTagDetail()
        this.getAlbumYearStats()
        this.getAlbumList()
      }
    },
    albumYearList: {
      handler(newVal) {
        if (newVal.length > 0) {
          setTimeout(() => {
            this.renderChart()
          }, 300)
        }
      },
      deep: true
    },
    // 监听主题色变化并保存到本地
    coverBgUrl(newVal) {
      localStorage.setItem('persistCoverBg', newVal)
    },
    localMainColor(newVal) {
      localStorage.setItem('persistMainColor', newVal)
    },
    localMainColorDark(newVal) {
      localStorage.setItem('persistMainColorDark', newVal)
    },
    localMainColorDarkDouble(newVal) {
      localStorage.setItem('persistMainColorDarkDouble', newVal)
    }
  },
  beforeDestroy() {
    if (this.myChart) {
      this.myChart.dispose()
      this.myChart = null
    }
  },
  methods: {
    // 切换简介/详细介绍标签 - 简化逻辑，只切换选中状态
    switchIntroTab(tabType) {
      this.introActiveTab = tabType // 直接切换，不再有"全部显示"状态
    },
    // 初始化主题色【和首页一致】
    initThemeColor() {
      this.localMainColor = localStorage.getItem('persistMainColor') || 'transparent';
      this.localMainColorDark = localStorage.getItem('persistMainColorDark') || '#333';
      this.localMainColorDarkDouble = localStorage.getItem('persistMainColorDarkDouble') || '#111';
      this.coverBgUrl = localStorage.getItem('persistCoverBg') || '';
    },
    // 获取封面背景【和首页一致】
    getCoverBgUrl(url) {
      this.coverBgUrl = url
    },
    // 获取主题色【和首页一致】
    getThemeColor(colorObj) {
      this.localMainColor = colorObj.mainColor
      this.localMainColorDark = colorObj.mainColorDark
      this.localMainColorDarkDouble = colorObj.mainColorDarkDouble
    },

    // ========== 修改：气泡图数据获取逻辑（使用全量ID） ==========
    async getTagBubbleStats() {
      // 改用allAlbumIds（全量）而非currentAlbumIds（当前页）
      if (!this.allAlbumIds || this.allAlbumIds.length === 0) {
        this.tagBubbleStats = []
        this.bubbleChartLoading = false
        return
      }

      try {
        this.bubbleChartLoading = true
        const headers = {
          'Authorization': localStorage.getItem('token') || ''
        }

        // 只传递专辑ID和当前标签名
        const params = {
          tagName: this.currentTagName,
          albumIds: this.allAlbumIds.join(',') // 使用全量ID
        }

        const response = await axios.get('/api/tags/album/tag-stats', {
          params,
          headers
        })

        if (response.data.code === 200) {
          this.tagBubbleStats = response.data.data.tagStats || []
        }
      } catch (error) {
        console.error('获取标签气泡图数据失败：', error)
        this.tagBubbleStats = []
      } finally {
        this.bubbleChartLoading = false
      }
    },

    // ========== 标签详情相关方法 ==========
    async getTagDetail() {
      try {
        this.loading = true
        const headers = {
          'Authorization': localStorage.getItem('token') || ''
        }

        const response = await axios.get('/api/tags/detail', {
          params: { tagName: this.currentTagName },
          headers
        })

        if (response.data.code === 200 && response.data.data) {
          this.tagInfo = response.data.data
          this.relatedSingers = this.parseJsonData(this.tagInfo.related_singers)
          this.relatedAlbums = this.parseJsonData(this.tagInfo.related_albums)
          this.relatedTags = this.parseJsonData(this.tagInfo.related_tags)

          // 获取父标签信息
          await this.getParentTags(this.tagInfo.parent_tag_ids)
        } else {
          this.tagInfo = null
          this.parentTags = []
        }
      } catch (error) {
        console.error('获取标签详情失败：', error)
        this.tagInfo = null
        this.parentTags = []
      } finally {
        this.loading = false
      }
    },

    // 根据父标签ID获取父标签详情
    async getParentTags(parentTagIds) {
      if (!parentTagIds || parentTagIds.trim() === '') {
        this.parentTags = []
        return
      }

      try {
        const headers = {
          'Authorization': localStorage.getItem('token') || ''
        }

        const response = await axios.get('/api/tags/parent-tags', {
          params: { ids: parentTagIds },
          headers
        })

        if (response.data.code === 200) {
          this.parentTags = response.data.data || []
        } else {
          this.parentTags = []
        }
      } catch (error) {
        console.error('获取父标签失败：', error)
        this.parentTags = []
      }
    },

    parseJsonData(jsonStr) {
      try {
        const data = JSON.parse(jsonStr || '[]')
        return Array.isArray(data) ? data : []
      } catch (e) {
        return []
      }
    },
    handleOpenEditTagSidebar() {
      this.showEditTagSidebar = true
    },
    handleEditTagClose() {
      this.showEditTagSidebar = false
    },
    refreshTagDetail() {
      this.getTagDetail()
      this.getAlbumYearStats()
      this.getAlbumList() // 刷新专辑列表后自动更新气泡图
    },

    // ========== 图表相关方法 ==========
    async getAlbumYearStats() {
      try {
        this.chartLoading = true
        const headers = {
          'Authorization': localStorage.getItem('token') || ''
        }

        const response = await axios.get('/api/tags/album/year-stats', {
          params: { tagName: this.currentTagName },
          headers
        })

        if (response.data.code === 200) {
          this.albumYearList = JSON.parse(JSON.stringify(response.data.data.album_year_list || []))
        }
      } catch (error) {
        console.error('获取专辑年份数据失败：', error)
        this.albumYearList = []
      } finally {
        this.chartLoading = false
      }
    },

    // ========== 新增：获取该标签下的所有专辑ID（不分页） ==========
    async getAllAlbumIds() {
      try {
        const headers = {
          'Authorization': localStorage.getItem('token') || ''
        }

        // 构建基础筛选参数（不含分页）
        const params = {
          tagName: this.currentTagName,
          listenStatus: this.listenStatus,
          // 只传筛选条件，不传分页参数
        }

        // 添加年份筛选
        if (this.selectedYear) {
          params.year = this.selectedYear
        }

        // 添加关键词搜索
        if (this.nameSingerKeyword.trim()) {
          params.keyword = this.nameSingerKeyword.trim()
        }

        // 请求全部专辑ID（后端需支持返回全量ID接口，或page_size设为极大值）
        const response = await axios.get('/api/tags/album/all-ids', {
          params,
          headers
        })

        if (response.data.code === 200) {
          this.allAlbumIds = response.data.data.albumIds || []
          // 获取到全量ID后立即加载气泡图
          this.getTagBubbleStats()
        } else {
          this.allAlbumIds = []
          this.tagBubbleStats = []
        }
      } catch (error) {
        console.error('获取全量专辑ID失败：', error)
        this.allAlbumIds = []
        this.tagBubbleStats = []
      }
    },

    // 处理图表点击（包括x轴和数据点）
    handleChartClick(params) {
      // 处理x轴标签点击
      if (params.componentType === 'xAxis') {
        const year = params.value
        this.handleYearSelect(year)
      }
      // 处理数据点点击
      else if (params.componentType === 'series') {
        const year = this.myChart.getOption().xAxis[0].data[params.dataIndex]
        this.handleYearSelect(year)
      }
    },

    // 年份选择统一处理逻辑
    handleYearSelect(year) {
      if (year && !isNaN(year)) {
        const yearStr = String(year).padStart(4, '2000').slice(-4)
        this.selectedYear = yearStr
        this.page = 1
        this.getAlbumList()
      }
    },

    renderChart() {
      // 销毁旧实例
      if (this.myChart) {
        this.myChart.dispose()
        this.myChart = null
      }

      const chartDom = document.getElementById('albumYearChart')
      if (!chartDom) return

      // 创建图表实例
      this.myChart = echarts.init(chartDom)

      // 统计年份数据
      const yearCount = {}
      this.albumYearList.forEach(item => {
        const year = String(Number(item.release_year))
        if (year && year !== 'NaN') {
          yearCount[year] = (yearCount[year] || 0) + 1
        }
      })

      // 准备图表数据
      const years = Object.keys(yearCount).sort((a, b) => a - b)
      const counts = years.map(year => yearCount[year])

      // 图表配置 - 修复居中问题
      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: '年份 {b}：{c} 张专辑',
          triggerOn: 'mousemove'
        },
        xAxis: {
          type: 'category',
          data: years,
          axisTick: {
            show: false
          },
          axisLine: {
            lineStyle: {
              color: this.localMainColorDark || '#e5e5e5'
            }
          },
          axisLabel: {
            fontSize: 12,
            rotate: 45,
            show: true,
            color: this.localMainColorDark || '#666'
          },
          triggerEvent: true
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisTick: {
            show: false
          },
          axisLine: {
            show: false
          },
          splitLine: {
            show: false
          },
          axisLabel: {
            show: false
          }
        },
        series: [
          {
            data: counts,
            type: 'line',
            smooth: true,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: `${this.localMainColor || 'rgba(64, 158, 255, 0.6)'}` },
                { offset: 1, color: `${this.localMainColor || 'rgba(64, 158, 255, 0.1)'}` }
              ])
            },
            lineStyle: {
              width: 2,
              color: this.localMainColor || '#409eff'
            },
            itemStyle: {
              color: this.localMainColor || '#409eff',
              borderColor: '#fff',
              borderWidth: 2
            },
            symbol: 'circle',
            symbolSize: 8, // 增大数据点尺寸，提升点击体验
            triggerEvent: true // 开启数据点的事件触发
          }
        ],
        // 修复grid配置，让图表居中显示
        grid: {
          left: '5%',    // 调整左侧边距适配3:7布局
          right: '5%',   // 调整右侧边距
          top: '15%',
          bottom: '25%',  // 增加底部边距容纳旋转的标签
          containLabel: true
        },
        // 自适应配置
        responsive: true
      }

      this.myChart.setOption(option)

      // 统一监听图表点击事件（包含x轴和数据点）
      this.myChart.on('click', this.handleChartClick)

      // 自适应窗口
      window.addEventListener('resize', () => {
        if (this.myChart) {
          this.myChart.resize()
        }
      })
    },
    // 清空年份筛选
    clearYearFilter() {
      this.selectedYear = ''
      this.page = 1
      this.getAlbumList()
    },

    // ========== 专辑列表相关方法 ==========
    toggleDropdown(type) {
      Object.keys(this.dropdownShow).forEach(key => {
        this.dropdownShow[key] = key === type ? !this.dropdownShow[key] : false
      })
    },
    handleSortChange(sortBy) {
      this.sortBy = sortBy
      this.getAlbumList()
    },
    handleOrderChange(sortOrder) {
      this.sortOrder = sortOrder
      this.getAlbumList()
    },
    handleSizeChange(pageSize) {
      this.pageSize = pageSize
      this.page = 1
      this.getAlbumList()
    },
    // 听状态筛选变更
    // ========== 修改：筛选条件变更时重新加载全量ID ==========
    handleListenStatusChange(status) {
      this.listenStatus = status
      this.page = 1
      this.getAlbumList() // 会自动触发getAllAlbumIds
    },
    // ========== 修改：专辑列表获取逻辑（新增全量ID加载） ==========
    async getAlbumList() {
      try {
        this.albumListLoading = true
        console.log('开始加载专辑列表：', {
          tagName: this.currentTagName,
          year: this.selectedYear,
          keyword: this.nameSingerKeyword,
          listenStatus: this.listenStatus,
          page: this.page,
          page_size: this.pageSize,
          sort_field: this.sortBy,
          sort_order: this.sortOrder
        })

        const headers = {
          'Authorization': localStorage.getItem('token') || ''
        }

        // 构建请求参数
        const params = {
          tagName: this.currentTagName,
          page: this.page,
          page_size: this.pageSize,
          sort_field: this.sortBy,
          sort_order: this.sortOrder,
          listenStatus: this.listenStatus
        }

        // 添加年份筛选
        if (this.selectedYear) {
          params.year = this.selectedYear
        }

        // 添加关键词搜索
        if (this.nameSingerKeyword.trim()) {
          params.keyword = this.nameSingerKeyword.trim()
        }

        const response = await axios.get('/api/tags/album/list', {
          params,
          headers
        })

        console.log('专辑列表返回结果：', response.data)

        if (response.data.code === 200) {
          this.albumList = response.data.data.list || []
          // 原有逻辑：保存当前页ID（仅用于备份）
          this.currentAlbumIds = this.albumList.map(item => item.id)
          this.pagination = response.data.data.pagination || {
            total: 0,
            page: 1,
            page_size: this.pageSize,
            total_pages: 0
          }
          this.jumpPageNum = this.pagination.page

          // 关键修改：加载全量专辑ID用于气泡图
          this.getAllAlbumIds()
        } else {
          this.albumList = []
          this.currentAlbumIds = []
          this.allAlbumIds = [] // 清空全量ID
          this.pagination = {
            total: 0,
            page: 1,
            page_size: this.pageSize,
            total_pages: 0
          }
          // 清空气泡图
          this.tagBubbleStats = []
        }
      } catch (error) {
        console.error('获取专辑列表失败：', error)
        this.albumList = []
        this.currentAlbumIds = []
        this.allAlbumIds = [] // 清空全量ID
        this.tagBubbleStats = []
        if (this.$message) {
          this.$message.error('获取专辑列表失败，请稍后重试')
        }
      } finally {
        this.albumListLoading = false
      }
    },
    // 清空关键词搜索
    clearNameSingerSearch() {
      this.nameSingerKeyword = ''
      this.page = 1
      this.getAlbumList()
    },
    // 分页切换
    changePage(newPage) {
      if (newPage < 1 || newPage > this.pagination.total_pages || newPage === this.page) return
      this.page = newPage
      this.getAlbumList()
    },
    // 页码跳转
    jumpToPage() {
      const num = parseInt(this.jumpPageNum)
      if (isNaN(num) || num < 1 || num > this.pagination.total_pages) {
        this.jumpPageNum = this.pagination.page
        return
      }
      this.changePage(num)
    },
    // 专辑操作方法
    copyAlbum(albumId) {
      if (!albumId) return
      axios({
        url: `/api/album/pool/copy/${albumId}`,
        method: 'POST',
        headers: {'Authorization': localStorage.getItem('token') || ''}
      }).then(res => {
        const {code, data} = res.data
        if (code === 200) {
          this.$router.push(`/webhome`).then(() => {
            const webHomeVm = this.$router.app.$children.find(vm => vm.$options.name === 'WebHome')
            if (webHomeVm) webHomeVm.activeMainTab = 'mymusic'
          })
        } else if (code === 409 && data) {
          const duplicateAlbumId = Number(data) || data
          this.$router.push(`/album/detail/${duplicateAlbumId}?id=${duplicateAlbumId}`)
        }
      }).catch(err => {
        console.error('复制专辑失败：', err)
      })
    },
    viewAlbumDetail(poolId) {
      this.$router.push(`/album/pool/detail/${poolId}`)
    },
    deletePoolAlbum(poolId) {
      if (!this.isAdmin) return
      if (!confirm('确定要删除该专辑吗？删除后不可恢复！')) return
      axios({
        url: `/api/album/pool/delete/${poolId}`,
        method: 'DELETE',
        headers: {'Authorization': localStorage.getItem('token') || ''}
      }).then(res => {
        if (res.data.code === 200) this.getAlbumList()
      }).catch(err => {
        console.error('删除专辑失败：', err)
      })
    }
  }
}
</script>

<style scoped>
/* 主容器 - 相对定位，层级管理【和首页一致】 */
.tag-detail-container {
  max-width: 1600px;
  margin: 20px auto;
  padding: 0 20px;
  position: relative;
  min-height: calc(100vh - 40px);
  z-index: 2;
  font-family: "Microsoft YaHei", sans-serif;
}

/* 全屏模糊背景层【1:1复刻首页的bg-layer】 */
.bg-layer {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: -1;
  filter: blur(25px) brightness(1.2);
  -webkit-filter: blur(25px) brightness(1.2);
  background-attachment: fixed;
}

/* 加载/空状态容器 */
.loading-container, .empty-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  color: v-bind(localMainColorDarkDouble);
  position: relative;
  z-index: 2;
}

/* 磨砂玻璃容器【和首页nav-mask-container风格统一】 */
.tag-detail-mask {
  background-color: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  -moz-backdrop-filter: blur(8px);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  z-index: 2;
  width: 100%;
  box-sizing: border-box;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

/* 内容容器 */
.tag-detail-content {
  width: 100%;
  box-sizing: border-box;
  position: relative;
  z-index: 3;
}

/* 顶部导航栏样式 */
.header-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0,0,0,0.05);
  position: relative;
  z-index: 3;
}

.parent-tags-wrapper {
  flex: 1;
}

.parent-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.parent-tags-placeholder {
  height: 24px;
}

.parent-tag-item {
  color: v-bind(localMainColor);
  text-decoration: none;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.parent-tag-item:hover {
  text-decoration: underline;
}

.plus-sign {
  color: v-bind(localMainColorDark);
  font-size: 16px;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 10px;
  white-space: nowrap;
}

.back-btn {
  padding: 8px 16px;
  background-color: v-bind(localMainColor);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
}

.edit-tag-btn {
  padding: 8px 16px;
  background-color: v-bind(localMainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

/* 标签基础信息 */
.tag-basic-info .tag-name {
  font-size: 28px;
  margin-bottom: 10px;
  color: v-bind(localMainColorDarkDouble);
  font-weight: 600;
}

.tag-aka {
  color: v-bind(localMainColorDark);
  margin-bottom: 20px;
  font-style: italic;
}

/* 简介+详细介绍 并排切换样式 - 移除原有样式，复用tab-item样式 */
.intro-tabs-container {
  margin-bottom: 30px;
  background: rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.intro-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

/* 移除原有intro-tab-item样式，完全复用tab-item样式 */
.intro-tab-item {
  /* 样式完全由tab-item控制 */
}

.intro-content-wrap {
  display: flex;
  gap: 20px;
  width: 100%;
}

.intro-panel {
  flex: 1;
  padding: 15px;
  border-radius: 6px;
  background: rgba(255,255,255,0.2);
}

.intro-panel h3 {
  margin: 0 0 10px 0;
  color: v-bind(localMainColorDarkDouble);
  font-size: 16px;
  font-weight: 600;
}

.intro-panel p, .intro-panel .intro-content {
  line-height: 1.8;
  color: v-bind(localMainColorDark);
  white-space: pre-line;
}

/* 气泡图+折线图 3:7 布局样式 */
.charts-container {
  display: flex;
  gap: 20px;
  margin: 30px 0;
  width: 100%;
  box-sizing: border-box;
}

/* 3份列 */
.chart-col-3 {
  flex: 3;
  min-width: 0; /* 防止内容溢出 */
}

/* 7份列 */
.chart-col-7 {
  flex: 7;
  min-width: 0; /* 防止内容溢出 */
}

/* 气泡图区域样式 */
.tag-bubble-section {
  padding: 20px;
  background: rgba(255,255,255,0.1);
  border-radius: 8px;
  backdrop-filter: blur(4px);
  height: 100%; /* 让气泡图容器高度和折线图一致 */
  box-sizing: border-box;
}

.tag-bubble-section h3 {
  margin: 0 0 15px 0;
  color: v-bind(localMainColorDarkDouble);
  font-size: 18px;
  font-weight: 600;
}

/* 图表样式 - 优化居中显示 */
.tag-album-chart {
  padding: 20px;
  background: rgba(255,255,255,0.1);
  border-radius: 8px;
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%; /* 让折线图容器高度和气泡图一致 */
  box-sizing: border-box;
}

.chart-loading, .chart-empty {
  text-align: center;
  padding: 40px 0;
  color: v-bind(localMainColorDark);
  font-size: 14px;
  width: 100%;
}

#albumYearChart {
  width: 100% !important;  /* 适配7份列宽度 */
  height: 250px !important;
  min-height: 250px !important;
  cursor: pointer;
  border-radius: 8px;
  background:transparent !important;
  backdrop-filter: blur(4px);
  margin: 0 auto !important; /* 强制居中 */
}

/* 标签详情其他样式 */
.tag-brief-intro, .tag-detail-intro, .tag-related-info {
  margin-bottom: 30px;
}

.tag-brief-intro h3, .tag-detail-intro h3, .tag-related-info h3 {
  color: v-bind(localMainColorDarkDouble);
  font-weight: 600;
  margin-bottom: 10px;
}

.tag-detail-intro .intro-content {
  line-height: 1.8;
  color: v-bind(localMainColorDark);
  white-space: pre-line;
}

.related-item h4 {
  color: v-bind(localMainColorDark);
  font-weight: 600;
  margin-bottom: 10px;
}

.related-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.related-tag {
  padding: 6px 12px;
  background-color: rgba(255,255,255,0.1);
  border-radius: 20px;
  font-size: 14px;
  color: v-bind(localMainColorDark);
  text-decoration: none;
  backdrop-filter: blur(4px);
}

.related-tag:hover {
  background-color: v-bind(localMainColor);
  color: #fff;
}

/* 专辑列表容器样式 */
.album-list-container {
  margin-top: 30px;
  width: 100%;
}

/* 顶部操作区样式【和首页统一】 */
.all-actions-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  width: 100%;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
  padding: 10px 16px;
  border-radius: 8px;
  box-sizing: border-box;
  position: relative;
  z-index: 99;
}

.dropdown-btn-container {
  position: relative;
  z-index: 9999;
}

.dropdown-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  background: v-bind(localMainColorDark);
  color: #fafafa;
  position: relative;
}

.dropdown-btn::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(localMainColorDark) !important;
  opacity: 1 !important;
}

.arrow-icon {
  font-size: 12px;
  transition: transform 0.2s;
}

.arrow-icon.active {
  transform: rotate(180deg);
}

.dropdown-options {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  padding: 8px 0;
  list-style: none;
  border-radius: 6px;
  z-index: 99999;
  background: v-bind(localMainColorDark) !important;
  backdrop-filter: none !important;
  border: none;
  overflow: visible;
}

.dropdown-options li {
  padding: 8px 16px;
  font-size: 14px;
  color: #ffffff !important;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.dropdown-options li:hover {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.dropdown-options li.active {
  color: #ffffff !important;
  font-weight: 600;
  background: rgba(255,255,255,0.3);
}

.sort-options {
  display: flex;
  gap: 10px;
  background: transparent !important;
  backdrop-filter: none !important;
  border-radius: 4px;
  border: none !important;
  width: fit-content;
  box-sizing: border-box;
}

/* 核心样式：升序/降序按钮样式，简介/详细介绍按钮复用此样式 */
.tab-item {
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  color: v-bind(localMainColorDark);
  transition: all 0.2s;
  font-weight: 600;
  position: relative;
  border: none;
  background: transparent;
}

/* 激活状态：背景有颜色，文字白色 */
.tab-item.active {
  background: v-bind(localMainColorDark);
  color: #fff;
}

/* 未激活状态：底部横线，透明背景，有字体颜色 */
.tab-item::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(localMainColorDark) !important;
  opacity: 1 !important;
}

/* 搜索区域样式 */
.search-area {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-left: auto;
}

/* 年份筛选提示样式 */
.year-filter-tip {
  padding: 6px 12px;
  background: rgba(64, 158, 255, 0.1);
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.year-filter-tip span {
  color: v-bind(localMainColor);
  font-weight: 600;
}

.clear-year-btn {
  padding: 2px 8px;
  background: v-bind(localMainColor);
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 搜索框样式 */
.search-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  padding: 6px 10px;
  width: 200px;
  border-radius: 4px;
  font-size: 14px;
  background: rgba(255,255,255,0.2) !important;
  border: none !important;
  color: v-bind(localMainColorDarkDouble) !important;
  outline: none;
  backdrop-filter: blur(4px);
}

.search-input::placeholder {
  color: v-bind(localMainColorDarkDouble) !important;
  opacity: 0.7;
}

.search-btn {
  padding: 6px 12px;
  background: v-bind(localMainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.clear-btn {
  padding: 6px 12px;
  background: v-bind(localMainColorDarkDouble);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.clear-btn:hover {
  background: v-bind(localMainColorDark);
}

/* 搜索结果样式 */
.loading-tip, .empty-tip {
  text-align: center;
  color: v-bind(localMainColorDark);
  padding: 30px 0;
}

.album-list {
  margin-top: 20px;
  position: relative;
  z-index: 1;
}

.album-item-wrapper {
  position: relative;
  margin-bottom: 2px;
  padding: 3px 20px;
  border: none;
  border-radius: 8px;
  background: transparent;
  z-index: 2;
}

/* 分页样式【和首页统一】 */
.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 30px;
  padding: 10px 16px;
  flex-wrap: wrap;
  width: 100%;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  box-sizing: border-box;
  justify-content: flex-start;
}

.page-info-wrapper {
  position: relative;
  padding: 4px 0;
  display: inline-block;
}

.page-info {
  color: v-bind(localMainColorDarkDouble);
  font-size: 14px;
  line-height: 1.5;
}

.page-info-wrapper::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background-color: v-bind(localMainColorDark) !important;
  opacity: 1 !important;
}

.jump-page {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-input {
  padding: 6px 10px;
  width: 60px;
  border-radius: 4px;
  font-size: 14px;
  background: rgba(255,255,255,0.2) !important;
  border: none !important;
  color: v-bind(localMainColorDarkDouble) !important;
  outline: none;
  backdrop-filter: blur(4px);
  text-align: center;
}

.jump-btn {
  padding: 6px 12px;
  background: v-bind(localMainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.page-btn {
  padding: 6px 12px;
  background: v-bind(localMainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.page-btn:disabled {
  background: #999;
  cursor: not-allowed;
  opacity: 0.7;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .charts-container {
    flex-direction: column;
  }
  .chart-col-3, .chart-col-7 {
    flex: none;
    width: 100%;
  }
}
</style>