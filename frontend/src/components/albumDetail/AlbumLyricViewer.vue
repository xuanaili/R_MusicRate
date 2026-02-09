<template>
  <!-- 模板部分保持不变 -->
  <div class="lyric-detail-container">
    <!-- 主体内容：单栏布局 -->
    <div class="lyric-detail-main">
      <!-- 歌词展示区域 -->
      <div class="lyric-column">
        <!-- 无歌词提示 -->
        <div v-if="!hasLyricContent" class="no-lyric-tip">
          暂无歌词数据
          <!-- 新增：管理员显示上传/编辑歌词按钮 -->
          <button
            v-if="isAdmin"
            class="upload-lyric-btn no-lyric-upload-btn"
            :style="{backgroundColor: mainColorDark}"
            @click="showUploadLyricModal = true"
          >
            上传/编辑歌词
          </button>
        </div>

        <!-- 歌词展示区域 -->
        <div v-else class="lyrics-wrapper">
          <!-- 固定显示的歌名（整合上传编辑歌词按钮） -->
          <div class="fixed-track-title"
               @mouseenter="showUploadBtn = true"
               @mouseleave="showUploadBtn = false">
            <!-- 单曲标题区域 - 可点击展开下拉列表（移除箭头） -->
            <div class="track-title-wrapper" @click="toggleTrackDropdown">
              <h2>{{ currentPlayingTrackName }}</h2>
              <!-- 移除下拉箭头 -->
            </div>

            <!-- 上传歌词按钮（仅管理员可见，悬停时显示） -->
            <button
              v-if="isAdmin && showUploadBtn"
              class="upload-lyric-btn"
              :style="{backgroundColor: mainColorDark}"
              @click="showUploadLyricModal = true"
            >
              上传/编辑歌词
            </button>

            <!-- 单曲列表下拉框 -->
            <div v-if="trackDropdownOpen" class="track-dropdown">
              <div
                  v-for="(track, index) in trackList"
                  :key="index"
                  class="track-dropdown-item"
                  :class="{active: index === currentPlayingTrackIndex}"
                  @click="handleTrackJump(index)"
              >
                <span class="track-number">{{ index + 1 }}</span>
                <span class="track-name">{{ track.name }}</span>
                <span class="track-duration">{{ track.duration }}</span>
              </div>
            </div>
          </div>

          <!-- 滚动的歌词内容 - 重构为网易云风格 -->
          <div
              class="lyrics-content"
              ref="lyricsContent"
              @scroll="handleManualScroll"
          >
            <!-- 歌词渐变遮罩容器 -->
            <div class="lyric-scroll-container">
              <!-- 整合版：原版+中文翻译歌词成对展示 -->
              <div class="lyric-section combined-lyric-section" v-if="combinedLyrics.length > 0">
                <div
                    v-for="(item, index) in combinedLyrics"
                    :key="index"
                    class="lyric-pair"
                    :class="{
                    highlighted: index === highlightedCombinedIndex
                  }"
                    @click="handleLyricClick(item.time)"
                >
                  <!-- 原版歌词 -->
                  <div
                      class="original-lyric-item"
                      :style="getLyricItemStyle(index, highlightedCombinedIndex)"
                  >
                    <span class="lyric-text">{{ item.originalText }}</span>
                    <span class="lyric-time">{{ formatTime(item.time) }}</span>
                  </div>

                  <!-- 中文翻译歌词（有内容时显示） -->
                  <div
                      v-if="item.cnText"
                      class="cn-lyric-item"
                      :style="getLyricItemStyle(index, highlightedCombinedIndex, true)"
                  >
                    <span class="lyric-text">{{ item.cnText }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 歌词上传弹窗 -->
        <div v-if="showUploadLyricModal" class="lyric-modal-mask" @click="closeModal">
          <div class="lyric-modal-content" @click.stop>
            <div class="lyric-modal-header">
              <h3>{{ hasLyricContent ? '编辑歌词' : '上传歌词' }}</h3>
              <span class="close-btn" @click="showUploadLyricModal = false">×</span>
            </div>
            <div class="lyric-modal-body">
              <!-- 单曲选择下拉框 -->
              <div class="track-select-group" v-if="trackList.length > 0">
                <label class="track-select-label">选择单曲</label>
                <select
                    v-model="selectedTrackIndex"
                    class="track-select-input"
                >
                  <option
                      v-for="(track, index) in trackList"
                      :key="index"
                      :value="index"
                  >
                    {{ track.name }}
                  </option>
                </select>
              </div>

              <!-- 原版歌词输入框 - 新增自动获取歌词按钮 -->
              <div class="lyric-input-group">
                <div class="lyric-input-header">
                  <label class="lyric-input-label">
                    {{ trackList[selectedTrackIndex]?.name || '当前单曲' }} 原版歌词（绝对时间）
                  </label>
                  <!-- 自动获取歌词按钮 -->
                  <button
                      class="auto-fetch-lyric-btn"
                      :style="{backgroundColor: mainColorDark}"
                      @click="showAutoFetchLyricModal = true"
                      :disabled="!trackList[selectedTrackIndex]?.name"
                  >
                    <i class="icon-fetch">📝</i> 自动获取歌词
                  </button>
                </div>
                <textarea
                    v-model="currentTrackLyricContent"
                    class="lyric-textarea"
                    placeholder="请按格式输入歌词：
00:00 歌词第一句
00:05 歌词第二句
00:10 歌词第三句
（时间格式：mm:ss 或 mm:ss.xx，使用绝对时间）"
                ></textarea>
              </div>

              <!-- 翻译歌词输入框（固定为中文） -->
              <div class="lyric-input-group">
                <div class="translate-lang-select-wrapper">
                  <label class="lyric-input-label">
                    {{ trackList[selectedTrackIndex]?.name || '当前单曲' }} 中文翻译歌词（可选，绝对时间）
                  </label>
                  <!-- 固定为中文，隐藏语言选择器 -->
                  <select
                      v-model="currentTranslateLang"
                      class="translate-lang-select"
                      disabled
                  >
                    <option value="CN">中文</option>
                  </select>
                </div>
                <textarea
                    v-model="currentTrackTranslateContent"
                    class="lyric-textarea"
                    placeholder="请按相同时间格式输入中文翻译歌词：
00:00 第一句翻译
00:05 第二句翻译
00:10 第三句翻译
（时间格式：mm:ss 或 mm:ss.xx，使用绝对时间）"
                ></textarea>
              </div>

              <div class="lyric-format-tip">
                📝 格式说明：每行一个歌词条目，时间和歌词用空格分隔，支持 mm:ss 或 mm:ss.xx 格式
                <br/>
                📌 提示：请输入绝对时间（从专辑开始的总时间），系统会自动按时间轴连续展示
              </div>
            </div>
            <!-- 核心修改：合并两个按钮为一个 -->
            <div class="lyric-modal-footer">
              <button
                  class="modal-cancel-btn"
                  @click="showUploadLyricModal = false"
              >
                取消
              </button>
              <button
                  class="modal-save-all-btn"
                  :style="{backgroundColor: mainColorDarkDouble}"
                  @click="saveAndUploadAllLyrics"
              >
                保存并上传所有歌词
              </button>
            </div>
          </div>
        </div>

        <!-- 自动获取歌词弹窗 -->
        <div v-if="showAutoFetchLyricModal" class="lyric-modal-mask" @click="closeAutoFetchModal">
          <div class="auto-fetch-modal-content" @click.stop>
            <div class="lyric-modal-header">
              <h3>自动获取歌词 - {{ trackList[selectedTrackIndex]?.name || '当前单曲' }}</h3>
              <span class="close-btn" @click="showAutoFetchLyricModal = false">×</span>
            </div>
            <div class="auto-fetch-modal-body">
              <!-- 歌曲信息确认 -->
              <div class="song-info-group">
                <label class="song-info-label">歌曲信息</label>
                <div class="song-info-fields">
                  <div class="info-field">
                    <span class="field-name">歌曲名：</span>
                    <input
                        v-model="fetchSongName"
                        class="info-input"
                        placeholder="请输入歌曲名"
                    />
                  </div>
                  <div class="info-field">
                    <span class="field-name">歌手名：</span>
                    <input
                        v-model="fetchArtist"
                        class="info-input"
                        placeholder="请输入歌手名"
                    />
                  </div>
                  <div class="info-field">
                    <span class="field-name">时长(秒)：</span>
                    <input
                        v-model.number="fetchDuration"
                        class="info-input"
                        type="number"
                        placeholder="可选，用于精准匹配"
                    />
                  </div>
                </div>
              </div>

              <!-- 获取按钮 -->
              <button
                  class="fetch-lyric-btn"
                  :style="{backgroundColor: mainColorDark}"
                  @click="fetchLyrics"
                  :disabled="fetchLoading || !fetchSongName.trim()"
              >
                <span v-if="fetchLoading">获取中...</span>
                <span v-else>点击获取歌词</span>
              </button>

              <!-- 歌词选择区域 -->
              <div v-if="fetchResult" class="lyric-result-group">
                <label class="lyric-result-label">选择歌词来源</label>
                <!-- 歌词来源切换 -->
                <div class="lyric-source-tabs">
                  <button
                      v-for="source in lyricSources"
                      :key="source.key"
                      class="source-tab"
                      :class="{active: selectedSource === source.key}"
                      @click="selectedSource = source.key"
                  >
                    {{ source.name }}
                    <span v-if="fetchResult[source.key]?.status === 'success'" class="success-tag">✓</span>
                    <span v-if="fetchResult[source.key]?.status === 'failed'" class="failed-tag">✗</span>
                  </button>
                </div>

                <!-- 选中的歌词预览 -->
                <div class="lyric-preview-container">
                  <textarea
                      v-model="selectedLyricContent"
                      class="lyric-preview-textarea"
                      readonly
                      placeholder="暂无歌词..."
                  ></textarea>
                </div>

                <!-- 填入按钮 -->
                <button
                    class="fill-lyric-btn"
                    :style="{backgroundColor: mainColorDarkDouble}"
                    @click="fillLyricToInput"
                    :disabled="!selectedLyricContent.trim()"
                >
                  填入歌词输入框
                </button>
              </div>
            </div>
            <div class="lyric-modal-footer">
              <button
                  class="modal-cancel-btn"
                  @click="showAutoFetchLyricModal = false"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AlbumLyricViewer',
  props: {
    // 原有props定义
    album: {
      type: Object,
      required: true,
      default: () => ({})
    },
    tracks: {type: Array, default: () => []},
    tracksTime: {type: Array, default: () => []},
    lyrics: {
      type: Object,
      default: () => ({
        lyric_text: '',
        lyric_translate: ''
      })
    },
    currentTime: {
      type: Number,
      default: 0
    },
    isPlaying: {
      type: Boolean,
      default: false
    },
    mainColor: {
      type: String,
      default: '#42b983'
    },
    mainColorDark: {
      type: String,
      default: '#2f9465'
    },
    mainColorDarkDouble: {
      type: String,
      default: '#257d51'
    },
    mainColorWhite: {
      type: String,
      default: '#57c592'
    },
    mainColorWhiteDouble: {
      type: String,
      default: '#6cd1a1'
    },
    isAdmin: {
      type: Boolean,
      default: false
    },
    isMusicPlaying: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      trackList: [],
      trackLyricsMap: {},
      selectedTrackIndex: 0,
      currentTrackLyricContent: '',
      currentTrackTranslateContent: '',
      translateLangOptions: [
        {value: 'CN', label: '中文'},
        {value: 'EN', label: '英文'},
        {value: 'DE', label: '德语'}
      ],
      currentTranslateLang: 'CN', // 默认改为中文
      highlightedIndex: -1,
      highlightedTranslateIndex: -1,
      highlightedCombinedIndex: -1, // 新增：整合版歌词高亮索引
      scrollTimer: null,
      resetTimer: null,
      showUploadLyricModal: false,
      lyricTextareaContent: '',
      translateTextareaContent: '',
      localParsedLyrics: [],
      localParsedTranslateLyrics: {}, // 修改：改为对象存储多语言翻译
      combinedLyrics: [], // 新增：整合后的原版+中文歌词数组
      isScrolling: false,
      showUploadBtn: false,
      trackDropdownOpen: false,
      showAutoFetchLyricModal: false,
      fetchSongName: '',
      // 【修改1】初始化时设置默认值为专辑歌手名
      fetchArtist: this.album.singer || '',
      fetchDuration: 0,
      fetchLoading: false,
      fetchResult: null,
      // 修复：增加QQ音乐来源
      lyricSources: [
        {key: 'netease', name: '网易云音乐'},
        {key: 'kugou', name: '酷狗音乐'},
        {key: 'qq', name: 'QQ音乐'},
        {key: 'genius', name: 'Genius'}
      ],
      selectedSource: 'netease',
      selectedLyricContent: ''
    };
  },
  computed: {
    hasLyricContent() {
      return !!this.lyrics.lyric_text || (this.lyrics.lyric_translate && this.lyrics.lyric_translate !== '{}');
    },
    currentPlayingTrackName() {
      if (!this.trackList || this.trackList.length === 0) {
        return '未知曲目';
      }

      const currentTime = this.currentTime;
      let currentTrackIndex = 0;

      for (let i = 0; i < this.trackList.length; i++) {
        const track = this.trackList[i];
        const nextTrack = this.trackList[i + 1];

        if (currentTime >= track.sec) {
          if (!nextTrack || currentTime < nextTrack.sec) {
            currentTrackIndex = i;
            break;
          }
        }
      }

      return this.trackList[currentTrackIndex].name || '未知曲目';
    },
    currentPlayingTrackIndex() {
      if (!this.trackList || this.trackList.length === 0) {
        return 0;
      }

      const currentTime = this.currentTime;
      let currentTrackIndex = 0;

      for (let i = 0; i < this.trackList.length; i++) {
        const track = this.trackList[i];
        const nextTrack = this.trackList[i + 1];

        if (currentTime >= track.sec) {
          if (!nextTrack || currentTime < nextTrack.sec) {
            currentTrackIndex = i;
            break;
          }
        }
      }

      return currentTrackIndex;
    }
  },
  watch: {
    tracks: {
      handler() {
        this.initTrackList(true)
      }, deep: true
    },
    tracksTime: {
      handler() {
        this.initTrackList(true)
      }, deep: true
    },
    album: {
      handler(newVal, oldVal) {
        if (oldVal && oldVal.id && newVal && newVal.id && oldVal.id !== newVal.id) {
          this.initTrackList(true);
        }
        this.initTrackList(true);
        // 【修改2】专辑变化时更新歌手名
        this.fetchArtist = newVal.singer || '';
      }, deep: true
    },
    selectedTrackIndex: {
      handler(newVal) {
        const trackLyrics = this.trackLyricsMap[newVal] || {lyric: '', translate: '', lang: 'CN'};
        this.currentTrackLyricContent = trackLyrics.lyric;
        this.currentTrackTranslateContent = trackLyrics.translate;
        this.currentTranslateLang = trackLyrics.lang || 'CN';

        if (this.trackList[newVal]) {
          this.fetchSongName = this.trackList[newVal].name || '';
          // 【修改3】保留原有逻辑，但不覆盖歌手名（用户可手动修改）
          // 仅在歌手名为空时才设置，避免覆盖用户输入
          if (!this.fetchArtist) {
            this.fetchArtist = this.album.singer || '';
          }
          const currentTrack = this.trackList[newVal];
          const nextTrack = this.trackList[newVal + 1];
          if (currentTrack && nextTrack) {
            this.fetchDuration = Math.round(nextTrack.sec - currentTrack.sec);
          } else {
            this.fetchDuration = 0;
          }
        }
      },
      immediate: true
    },
    currentTime: {
      handler() {
        this.updateCurrentLyric();
      },
      immediate: true
    },
    isPlaying: {
      handler() {
        this.updateCurrentLyric();
      },
      immediate: true
    },
    lyrics: {
      handler(newVal) {
        // 解析原版歌词
        this.localParsedLyrics = this.parseLyricText(newVal.lyric_text || '');

        // 解析翻译歌词（支持多语言）
        this.localParsedTranslateLyrics = {};
        try {
          const translateObj = JSON.parse(newVal.lyric_translate || '{}');
          // 解析每种语言的翻译歌词
          Object.keys(translateObj).forEach(lang => {
            this.localParsedTranslateLyrics[lang] = this.parseLyricText(translateObj[lang] || '');
          });
          // 默认选中中文
          this.currentTranslateLang = 'CN';
        } catch (e) {
          // 兼容旧格式
          this.localParsedTranslateLyrics['CN'] = this.parseLyricText(newVal.lyric_translate || '');
        }

        // 整合原版+中文翻译歌词
        this.combineLyrics();

        this.initTrackLyricsMap();

        this.$nextTick(() => {
          this.updateCurrentLyric();
        });
      },
      immediate: true,
      deep: true
    },
    selectedSource: {
      handler(newVal) {
        // 修复：增强数据检查，确保数据存在
        if (this.fetchResult && this.fetchResult[newVal]) {
          this.selectedLyricContent = this.fetchResult[newVal].lyric || '';
        } else {
          this.selectedLyricContent = '';
        }
        // 修复：自动选中第一个成功的来源
        this.autoSelectFirstSuccessSource();
      },
      immediate: true
    },
    // 新增：监听fetchResult变化，自动选中第一个成功的来源
    fetchResult: {
      handler(newVal) {
        if (newVal) {
          this.autoSelectFirstSuccessSource();
        }
      },
      immediate: true,
      deep: true
    }
  },
  mounted() {
    this.initTrackList();
    this.startResetTimer();
    document.addEventListener('click', this.handleClickOutside);

    this.$nextTick(() => {
      this.updateCurrentLyric();
    });
  },
  beforeUnmount() {
    if (this.scrollTimer) {
      clearTimeout(this.scrollTimer);
    }
    if (this.resetTimer) {
      clearTimeout(this.resetTimer);
    }
    document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    document.removeEventListener('click', this.handleClickOutside);
  },
  methods: {
    // 修复：获取歌词的核心方法
    async fetchLyrics() {
      if (!this.fetchSongName.trim()) {
        this.$message?.warning('歌曲名不能为空！');
        return;
      }

      this.fetchLoading = true;
      // 修复：清空之前的结果，避免干扰
      this.fetchResult = null;
      this.selectedLyricContent = '';

      try {
        const res = await this.$axios.post(
            '/api/lyric/fetch_auto',
            {
              song_name: this.fetchSongName.trim(),
              artist: this.fetchArtist.trim(),
              duration: this.fetchDuration
            },
            {headers: {Authorization: localStorage.getItem('token') || ''}}
        );

        // 修复：统一数据处理逻辑，适配不同的后端返回格式
        if (res.data.code === 200) {
          // 标准化返回数据格式
          let lyricsData = res.data.data?.lyrics || res.data.data || {};

          // 适配后端日志中的格式（网易云/酷狗/QQ音乐）
          const standardSources = {
            netease: {
              status: lyricsData.netease?.status || (lyricsData.netease?.lyric ? 'success' : 'failed'),
              lyric: lyricsData.netease?.lyric || lyricsData.netease || ''
            },
            kugou: {
              status: lyricsData.kugou?.status || (lyricsData.kugou?.lyric ? 'success' : 'failed'),
              lyric: lyricsData.kugou?.lyric || lyricsData.kugou || ''
            },
            qq: {
              status: lyricsData.qq?.status || (lyricsData.qq?.lyric ? 'success' : 'failed'),
              lyric: lyricsData.qq?.lyric || lyricsData.qq || ''
            },
            genius: {
              status: lyricsData.genius?.status || (lyricsData.genius?.lyric ? 'success' : 'failed'),
              lyric: lyricsData.genius?.lyric || lyricsData.genius || ''
            }
          };

          this.fetchResult = standardSources;

          // 修复：立即自动选中第一个成功的来源，不需要等待watch触发
          this.autoSelectFirstSuccessSource();

          this.$message?.success('歌词获取成功！');
        } else {
          this.$message?.error(res.data.msg || '歌词获取失败！');
          this.fetchResult = null;
        }
      } catch (error) {
        console.error('获取歌词失败：', error);
        this.$message?.error('网络错误，歌词获取失败！');
        this.fetchResult = null;
      } finally {
        this.fetchLoading = false;
        // 修复：确保UI及时更新
        this.$forceUpdate();
      }
    },

    // 核心修复：解析LRC格式歌词，正确提取时间和歌词内容
    // 修复：解析LRC格式歌词，转换为输入框标准格式(mm:ss 歌词)
    parseLrcToStandardFormat(lrcText) {
      if (!lrcText || typeof lrcText !== 'string') return '';

      const lines = lrcText.trim().split('\n');
      const standardLyrics = [];

      lines.forEach(line => {
        // 清理行：去除空白字符
        const cleanLine = line.trim();
        if (!cleanLine) return;

        // 匹配LRC时间标签：[mm:ss.xx] 或 [mm:ss]
        // 注意：LRC格式时间标签可能在行首或多个标签连续出现
        const timeMatches = [];
        let remainingLine = cleanLine;

        // 提取所有时间标签
        const timePattern = /\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\]/g;
        let match;
        while ((match = timePattern.exec(cleanLine)) !== null) {
          const [, min, sec, ms] = match;
          const totalSeconds = parseInt(min) * 60 + parseInt(sec) + (ms ? parseInt(ms) / (ms.length === 2 ? 100 : 1000) : 0);
          timeMatches.push({
            time: totalSeconds,
            match: match[0],
            index: match.index
          });

          // 获取标签后的歌词文本
          const tagEndIndex = match.index + match[0].length;
          if (timeMatches.length === 1) {
            // 第一个标签后的文本就是歌词
            const lyricText = cleanLine.substring(tagEndIndex).trim();
            remainingLine = lyricText;
          }
        }

        // 如果没有时间标签，跳过这一行
        if (timeMatches.length === 0) return;

        // 过滤无效内容
        if (!remainingLine ||
            /词：|曲：|编曲：|制作人：|演唱：|原唱：|专辑：|歌名：|作词：|作曲：|Lyrics|Music|Album/i.test(remainingLine) ||
            remainingLine.startsWith('[') && remainingLine.endsWith(']')) {
          return;
        }

        // 为每个时间标签创建歌词行
        timeMatches.forEach(({time}) => {
          const minutes = Math.floor(time / 60);
          const seconds = Math.floor(time % 60);
          const milliseconds = time % 1;

          // 格式化时间：mm:ss 或 mm:ss.xx
          let timeStr = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
          if (milliseconds > 0) {
            // 保留1-2位小数
            const msStr = Math.round(milliseconds * 100).toString().padStart(2, '0');
            timeStr += `.${msStr}`.replace(/0+$/, ''); // 去除末尾的0
          }

          standardLyrics.push({
            time: time,
            timeStr: timeStr,
            text: remainingLine
          });
        });
      });

      // 按时间排序
      standardLyrics.sort((a, b) => a.time - b.time);

      // 转换为字符串格式
      return standardLyrics.map(item => `${item.timeStr} ${item.text}`).join('\n');
    },

    // 修复：自动选中第一个成功获取到歌词的来源
    autoSelectFirstSuccessSource() {
      if (!this.fetchResult) return;

      // 修复：立即执行来源选择，避免延迟
      const successSource = this.lyricSources.find(source => {
        return this.fetchResult[source.key]?.status === 'success' &&
            this.fetchResult[source.key]?.lyric?.trim();
      });

      if (successSource) {
        // 修复：同步更新选中状态，避免需要二次点击
        this.selectedSource = successSource.key;
        this.selectedLyricContent = this.fetchResult[successSource.key].lyric || '';
      }
    },

    // 修复：填入歌词到输入框的核心方法
    fillLyricToInput() {
      if (!this.selectedLyricContent.trim()) {
        this.$message?.warning('暂无歌词可填入！');
        return;
      }

      // 确保曲目开始时间为非负数

      // 第一步：将LRC原始歌词转换为输入框标准格式
      const standardLyricText = this.parseLrcToStandardFormat(this.selectedLyricContent);
      if (!standardLyricText) {
        this.$message?.warning('未解析到有效歌词内容！');
        return;
      }

      // 第二步：解析标准格式歌词，转换为相对时间
      const lines = standardLyricText.trim().split('\n');
      const relativeLyrics = [];

      lines.forEach(line => {
        const match = line.match(/^(\d{2}:\d{2}(?:\.\d{1,2})?)\s+(.+)$/);
        if (match) {
          const [, timeStr, lyricText] = match;
          // 解析绝对时间
          const absoluteTime = this.parseTimeStr(timeStr);
          // 计算相对时间（相对于当前单曲开始时间）
          const relativeTime = Math.max(0, absoluteTime);

          // 格式化相对时间（避免00:00.00格式）
          let formattedTime = '';
          if (relativeTime < 0.01) {
            formattedTime = '00:00';
          } else {
            const min = Math.floor(relativeTime / 60);
            const sec = Math.floor(relativeTime % 60);
            const ms = relativeTime % 1;

            if (ms < 0.01) {
              formattedTime = `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
            } else {
              // 只保留1位小数
              const msRounded = Math.round(ms * 10);
              formattedTime = `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${msRounded}`;
            }
          }

          // 过滤掉时间为00:00且歌词为空的无效行
          if (!(formattedTime === '00:00' && !lyricText.trim())) {
            relativeLyrics.push(`${formattedTime} ${lyricText}`);
          }
        }
      });

      // 第三步：填入输入框
      this.currentTrackLyricContent = relativeLyrics.join('\n');
      this.showAutoFetchLyricModal = false;
      this.$message?.success('歌词已格式化并填入输入框！');
    },

    closeAutoFetchModal() {
      this.showAutoFetchLyricModal = false;
      this.fetchResult = null;
      this.selectedLyricContent = '';
      this.selectedSource = 'netease';
    },

    toggleTrackDropdown() {
      this.trackDropdownOpen = !this.trackDropdownOpen;
    },

    handleTrackJump(index) {
      if (this.trackList[index]) {
        this.$emit('jump-to-time', this.trackList[index].sec || 0);
        this.trackDropdownOpen = false;
      }
    },

    handleClickOutside(event) {
      const fixedTitle = document.querySelector('.fixed-track-title');
      if (fixedTitle && !fixedTitle.contains(event.target)) {
        this.trackDropdownOpen = false;
      }
    },

    secondsToTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '0:00:00';
      const total = Math.floor(seconds);
      const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = Math.floor(total % 60);
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },

    initTrackList() {
      this.trackList = [];
      const names = this.tracks || [], secs = this.tracksTime || [];

      names.forEach((name, idx) => {
        const dbSec = secs[idx] || 0;
        this.trackList.push({
          name: name.trim() || '未知曲目',
          sec: dbSec,
          duration: this.secondsToTime(dbSec)
        });
      });

      if (!names.length) {
        this.trackList = [{
          name: '未知曲目',
          sec: 0,
          duration: '0:00:00'
        }];
      }

      this.initTrackLyricsMap();
    },

    initTrackLyricsMap() {
      this.trackLyricsMap = {};

      if (this.localParsedLyrics.length > 0) {
        this.trackList.forEach((track, trackIndex) => {
          const trackStartTime = track.sec;
          const nextTrack = this.trackList[trackIndex + 1];
          const trackEndTime = nextTrack ? nextTrack.sec : Infinity;

          const trackLyrics = this.localParsedLyrics.filter(lyric =>
              lyric.time >= trackStartTime && lyric.time < trackEndTime
          );

          const relativeLyrics = trackLyrics.map(lyric => {
            const relativeTime = lyric.time - trackStartTime;
            return `${this.formatTime(relativeTime)} ${lyric.text}`;
          }).join('\n');

          // 获取中文翻译歌词
          const trackTranslateLyrics = (this.localParsedTranslateLyrics['CN'] || []).filter(lyric =>
              lyric.time >= trackStartTime && lyric.time < trackEndTime
          );
          const relativeTranslate = trackTranslateLyrics.map(lyric => {
            const relativeTime = lyric.time - trackStartTime;
            return `${this.formatTime(relativeTime)} ${lyric.text}`;
          }).join('\n');

          this.trackLyricsMap[trackIndex] = {
            lyric: relativeLyrics,
            translate: relativeTranslate,
            lang: 'CN'
          };
        });
      } else {
        this.trackList.forEach((_, trackIndex) => {
          this.trackLyricsMap[trackIndex] = {
            lyric: '',
            translate: '',
            lang: 'CN'
          };
        });
      }

      this.currentTrackLyricContent = this.trackLyricsMap[this.selectedTrackIndex]?.lyric || '';
      this.currentTrackTranslateContent = this.trackLyricsMap[this.selectedTrackIndex]?.translate || '';
      this.currentTranslateLang = this.trackLyricsMap[this.selectedTrackIndex]?.lang || 'CN';
    },

    // 辅助优化：formatTime 简化，避免冗余毫秒（输入框只需要mm:ss或mm:ss.x）
    formatTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '00:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      const ms = Math.floor((seconds % 1) * 10); // 只保留1位毫秒，避免冗余
      return ms > 0
          ? `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms}`
          : `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },

    // 修复：parseTimeStr方法增强，支持更多格式
    parseTimeStr(timeStr) {
      try {
        // 支持格式：mm:ss、mm:ss.xx、mm:ss.x
        const [minPart, rest] = timeStr.split(':');
        if (!rest) return 0;

        const min = parseInt(minPart, 10);
        let sec = 0;

        if (rest.includes('.')) {
          const [secPart, msPart] = rest.split('.');
          sec = parseInt(secPart, 10);
          const ms = parseInt(msPart, 10) / Math.pow(10, msPart.length);
          sec += ms;
        } else {
          sec = parseInt(rest, 10);
        }

        return min * 60 + sec;
      } catch (e) {
        console.error('时间格式解析失败：', timeStr, e);
        return 0;
      }
    },

    parseLyricText(text) {
      if (!text) return [];

      const lines = text.trim().split('\n');
      const lyrics = [];

      lines.forEach(line => {
        if (!line.trim()) return;

        const timeMatch = line.match(/^(\d{1,2}:\d{2}(?:\.\d{1,2})?)\s+(.*)$/);
        if (timeMatch) {
          const time = this.parseTimeStr(timeMatch[1]);
          const text = timeMatch[2].trim();
          if (text) {
            lyrics.push({time, text});
          }
        }
      });

      return lyrics.sort((a, b) => a.time - b.time);
    },

    // 新增：整合原版歌词和中文翻译歌词
    combineLyrics() {
      this.combinedLyrics = [];

      // 获取中文翻译歌词数组
      const cnLyrics = this.localParsedTranslateLyrics['CN'] || [];

      // 创建翻译歌词的时间映射
      const cnLyricMap = {};
      cnLyrics.forEach(item => {
        // 四舍五入到小数点后1位，避免时间精度问题
        const timeKey = Math.round(item.time * 10) / 10;
        cnLyricMap[timeKey] = item.text;
      });

      // 遍历原版歌词，匹配对应的中文翻译
      this.localParsedLyrics.forEach(originalItem => {
        const timeKey = Math.round(originalItem.time * 10) / 10;
        this.combinedLyrics.push({
          time: originalItem.time,
          originalText: originalItem.text,
          cnText: cnLyricMap[timeKey] || '' // 匹配不到则为空
        });
      });

      // 如果有翻译歌词没有对应的原版歌词，也添加进去
      cnLyrics.forEach(cnItem => {
        const timeKey = Math.round(cnItem.time * 10) / 10;
        // 检查是否已存在
        const exists = this.combinedLyrics.some(item =>
            Math.round(item.time * 10) / 10 === timeKey
        );
        if (!exists) {
          this.combinedLyrics.push({
            time: cnItem.time,
            originalText: '',
            cnText: cnItem.text
          });
        }
      });

      // 按时间排序
      this.combinedLyrics.sort((a, b) => a.time - b.time);
    },

    integrateAllLyrics() {
      let integratedLyrics = [];
      let integratedTranslate = [];

      this.trackList.forEach((track, trackIndex) => {
        const trackLyrics = this.trackLyricsMap[trackIndex] || {lyric: '', translate: '', lang: 'CN'};
        const trackStartTime = track.sec;

        const parsedLyrics = this.parseLyricText(trackLyrics.lyric);
        parsedLyrics.forEach(lyric => {
          integratedLyrics.push({
            time: trackStartTime + lyric.time,
            text: lyric.text
          });
        });

        const parsedTranslate = this.parseLyricText(trackLyrics.translate);
        parsedTranslate.forEach(lyric => {
          integratedTranslate.push({
            time: trackStartTime + lyric.time,
            text: lyric.text
          });
        });
      });

      const lyricText = integratedLyrics
          .sort((a, b) => a.time - b.time)
          .map(lyric => `${this.formatTime(lyric.time)} ${lyric.text}`)
          .join('\n');

      const translateText = integratedTranslate
          .sort((a, b) => a.time - b.time)
          .map(lyric => `${this.formatTime(lyric.time)} ${lyric.text}`)
          .join('\n');

      const translateObj = {};
      translateObj['CN'] = translateText; // 固定为中文

      return {
        lyric_text: lyricText,
        lyric_translate: JSON.stringify(translateObj)
      };
    },

    // 新增：检查是否是当前播放的整合版歌词
    isCurrentCombinedLyric(index) {
      const currentLyric = this.combinedLyrics[index];
      if (!currentLyric) return false;

      const currentTime = this.currentTime;
      const nextLyric = this.combinedLyrics[index + 1];
      const nextLyricTime = nextLyric ? nextLyric.time : Infinity;

      return currentTime >= currentLyric.time && currentTime < nextLyricTime;
    },

    updateCurrentLyric() {
      // 更新整合版歌词高亮
      this.updateHighlightedCombinedIndex();

      this.$nextTick(() => {
        if (this.highlightedCombinedIndex !== -1 && !this.isScrolling) {
          this.scrollToCurrentCombinedLyric(this.highlightedCombinedIndex);
        }
      });
    },

    // 新增：更新整合版歌词高亮索引
    updateHighlightedCombinedIndex() {
      let currentIndex = -1;
      const currentTime = this.currentTime;

      for (let i = this.combinedLyrics.length - 1; i >= 0; i--) {
        if (currentTime >= this.combinedLyrics[i].time) {
          currentIndex = i;
          break;
        }
      }

      if (currentIndex !== -1) {
        if (currentIndex !== this.highlightedCombinedIndex) {
          this.highlightedCombinedIndex = currentIndex;
        }
      } else if (this.combinedLyrics.length > 0 && currentIndex === -1) {
        currentIndex = 0;
        this.highlightedCombinedIndex = currentIndex;
      }
    },

    // 新增：滚动到当前播放的整合版歌词
    scrollToCurrentCombinedLyric(index) {
      if (index === -1 || this.isScrolling) return;

      this.isScrolling = true;

      this.$nextTick(() => {
        const lyricsContent = this.$refs.lyricsContent;
        if (!lyricsContent) {
          this.isScrolling = false;
          return;
        }

        const lyricSection = lyricsContent.querySelector('.combined-lyric-section');
        if (lyricSection) {
          const lyricPairs = lyricSection.querySelectorAll('.lyric-pair');
          if (index >= 0 && index < lyricPairs.length) {
            const lyricPair = lyricPairs[index];
            if (lyricPair) {
              const itemOffsetTop = lyricPair.offsetTop;
              const containerHeight = lyricsContent.clientHeight;
              const itemHeight = lyricPair.offsetHeight;

              const targetScrollTop = itemOffsetTop - (containerHeight / 2) + (itemHeight / 2);
              const safeScrollTop = Math.max(0, Math.min(targetScrollTop, lyricsContent.scrollHeight - containerHeight));

              requestAnimationFrame(() => {
                lyricsContent.scrollTop = safeScrollTop;

                setTimeout(() => {
                  this.isScrolling = false;
                }, 100);
              });
            } else {
              this.isScrolling = false;
            }
          } else {
            this.isScrolling = false;
          }
        } else {
          this.isScrolling = false;
        }
      });
    },

    getLyricItemStyle(index, highlightedIndex, isCn = false) {
      if (highlightedIndex === -1) return {};

      const distance = Math.abs(index - highlightedIndex);
      let opacity = 1;
      let fontSize = isCn ? '20px' : '24px'; // 中文翻译字体稍小
      let fontWeight = 700;

      if (distance > 0) {
        opacity = Math.max(0.5, 1 - (distance * 0.15));
        fontSize = isCn
            ? `${Math.max(16, 28 - (distance * 4))}px`
            : `${Math.max(16, 28 - (distance * 4))}px`;
        fontWeight = 400;
      }

      return {
        opacity,
        fontSize,
        fontWeight,
        transition: 'opacity 0.4s ease, fontSize 0.4s ease, fontWeight 0.4s ease'
      };
    },

    handleManualScroll() {
      this.resetResetTimer();
    },

    startResetTimer() {
      this.resetTimer = setTimeout(() => {
        this.resetLyricPosition();
      }, 5000);
    },

    resetResetTimer() {
      if (this.resetTimer) {
        clearTimeout(this.resetTimer);
      }
      this.startResetTimer();
    },

    resetLyricPosition() {
      if (this.isScrolling) return;

      const lyricsContent = this.$refs.lyricsContent;
      if (lyricsContent) {
        lyricsContent.scrollTop = 0;

        this.$nextTick(() => {
          this.updateCurrentLyric();
        });
      }
      this.startResetTimer();
    },

    handleLyricClick(time) {
      this.$emit('jump-to-time', time);
      this.resetResetTimer();
    },

    closeModal() {
      this.showUploadLyricModal = false;
    },

    // 核心新增：合并保存当前单曲+上传所有歌词的方法
    async saveAndUploadAllLyrics() {
      // 1. 验证当前单曲原版歌词非空
      if (!this.currentTrackLyricContent.trim()) {
        this.$message?.warning('原版歌词内容不能为空！');
        return;
      }
      // 2. 保存当前编辑的单曲歌词到本地trackLyricsMap
      this.trackLyricsMap[this.selectedTrackIndex] = {
        lyric: this.currentTrackLyricContent.trim(),
        translate: this.currentTrackTranslateContent.trim(),
        lang: 'CN'
      };
      // 3. 整合所有歌词并上传到服务器
      try {
        const integratedData = this.integrateAllLyrics();
        if (!integratedData.lyric_text.trim()) {
          this.$message?.warning('没有可保存的歌词内容！');
          return;
        }
        const res = await this.$axios.post(
            `/api/album/lyric/save/${this.album.source_pool_id || this.album.id}`,
            integratedData,
            {headers: {Authorization: localStorage.getItem('token') || ''}}
        );
        if (res.data.code === 200) {
          this.$message?.success('所有歌词保存并上传成功！');
          this.showUploadLyricModal = false;
          this.$emit('update:lyrics', integratedData);
          // 刷新本地解析的歌词
          this.localParsedLyrics = this.parseLyricText(integratedData.lyric_text);
          let translateText = '';
          try {
            const translateObj = JSON.parse(integratedData.lyric_translate || '{}');
            translateText = translateObj['CN'] || '';
          } catch (e) {
            translateText = integratedData.lyric_translate || '';
          }
          this.localParsedTranslateLyrics['CN'] = this.parseLyricText(translateText);
          // 重新整合歌词
          this.combineLyrics();
          this.$nextTick(() => {
            this.updateCurrentLyric();
          });
        } else {
          this.$message?.error(res.data.msg || '歌词上传失败！');
        }
      } catch (error) {
        console.error('保存并上传歌词失败：', error);
        this.$message?.error('网络错误，歌词上传失败！');
      }
    },

    // 保留原方法做兼容（防止其他地方调用）
    async saveAllLyrics() {
      await this.saveAndUploadAllLyrics();
    }
  }
};
</script>

<style scoped>
/* 样式部分保持不变，新增整合版歌词样式 */
/* 整体容器 */
.lyric-detail-container {
  width: 100%;
  height: 89vh;
  font-family: "Microsoft YaHei", sans-serif;
  box-sizing: border-box;
}

/* 单栏布局 */
.lyric-detail-main {
  height: 100%;
}

/* 歌词区域 */
.lyric-column {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ==================== 歌词样式 ==================== */
.no-lyric-tip {
  text-align: center;
  font-size: 18px;
  color: #666;
  margin-top: 50px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

/* 歌词外层容器 - 包含固定标题和滚动歌词 */
.lyrics-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  margin: 20px 0;
}

/* 固定显示的歌名（整合上传按钮样式） */
.fixed-track-title {
  text-align: center;
  display: flex;
  justify-content: center; /* 改为居中对齐 */
  align-items: center;
  position: relative; /* 为下拉列表定位 */
}

/* 单曲标题包装器 - 可点击（移除箭头后调整样式） */
.track-title-wrapper {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.track-title-wrapper:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.fixed-track-title h3 {
  margin: 0;
  font-size: 20px;
  color: #333;
  font-weight: 600;
}
.fixed-track-title::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
	height: 4px;
	border-radius: 2px;
  background-color: v-bind(mainColorDark) !important;
  opacity: 1 !important;
}
/* 上传歌词按钮样式调整 */
.upload-lyric-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  position: absolute;
  right: 20px; /* 固定在右侧 */
  opacity: 0; /* 默认隐藏 */
  transform: scale(0.95);
}

/* 悬停时显示上传按钮 */
.fixed-track-title:hover .upload-lyric-btn {
  opacity: 1;
  transform: scale(1);
}

.upload-lyric-btn:hover {
  opacity: 0.9;
  transform: scale(1.05);
}

/* 单曲下拉列表样式 */
.track-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border-radius: 0 0 8px 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-top: none;
}

/* 下拉列表项样式 */
.track-dropdown-item {
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background-color 0.2s ease;
  color: #333;
}

.track-dropdown-item:last-child {
  border-bottom: none;
}

.track-dropdown-item:hover {
  background-color: rgba(0, 0, 0, 0.2);
}

/* 当前播放的单曲样式 */
.track-dropdown-item.active {
  background-color: rgba(0, 0, 0, 0.2);
  color: v-bind(mainColorDark) !important;
  font-weight: 600;
}

/* 单曲序号 */
.track-number {
  width: 20px;
  text-align: center;
  font-size: 14px;
  color: #999;
}

/* 单曲名称 */
.track-name {
  flex: 1;
  margin: 0 10px;
  font-size: 14px;
}

/* 单曲时长 */
.track-duration {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
}

/* 滚动的歌词内容 - 网易云风格重构 */
.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  /* 关键：移除smooth滚动，避免系统动画导致的抖动 */
  scroll-behavior: auto;
  position: relative;
}

/* 歌词滚动容器 - 确保居中效果 */
.lyric-scroll-container {
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100%;
}

.lyric-section {
  width: 100%;
  margin-bottom: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 整合版歌词样式 */
.combined-lyric-section {
  width: 100%;
  margin-bottom: 30px;
}

/* 歌词对（原版+翻译） */
.lyric-pair {
  margin: 8px 0;
  border-radius: 4px;
  cursor: pointer;
  width: 100%;
  max-width: 800px;
  box-sizing: border-box;
}

/* 高亮的歌词对 */
.lyric-pair.highlighted {
  padding: 4px;
  border-radius: 8px;
}








/* 高亮的歌词对 - 新增子元素颜色继承 */
.lyric-pair.highlighted .original-lyric-item,
.lyric-pair.highlighted .cn-lyric-item {
  color: v-bind(mainColorDarkDouble); /* 强制统一高亮色 */
}
/* 原版歌词项 */
.original-lyric-item {
  padding: 8px 15px;
  margin: 2px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  color: #333;
  /* 关键：硬件加速，减少动画卡顿 */
  transform: translateZ(0);
  backface-visibility: hidden;
}

/* 中文翻译歌词项 - 新增 color 绑定 */
.cn-lyric-item {
  padding: 4px 15px 8px;
  margin: 2px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  color: v-bind(mainColorDarkDouble); /* 与原版高亮颜色一致 */
  transform: translateZ(0);
  backface-visibility: hidden;
}

/* 时间戳样式优化 - 仅鼠标悬停时显示 */
.lyric-time {
  color: v-bind(mainColorDarkDouble);
  font-size: 12px;
  position: absolute;
  right: 20px;
  opacity: 0; /* 默认隐藏 */
  transition: opacity 0.2s ease;
}

/* 仅在歌词项hover时显示时间戳 */
.original-lyric-item:hover .lyric-time {
  opacity: 1;
}

/* 歌词文本样式优化 */
.lyric-text {
  text-align: center;
  width: 100%;
  /* 关键：防止文本换行导致高度变化 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 歌词内容滚动条美化 */
.lyrics-content::-webkit-scrollbar {
  width: 4px;
}

.lyrics-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.lyrics-content::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius: 2px;
}

.lyrics-content::-webkit-scrollbar-thumb:hover {

  background: v-bind(mainColorDarkDouble);
}

/* 歌词弹窗样式 */
.lyric-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.lyric-modal-content {
  width: 80%;
  max-width: 800px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 0;
}

/* 自动获取歌词弹窗样式 */
.auto-fetch-modal-content {
  width: 80%;
  max-width: 900px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 0;
}

.lyric-modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lyric-modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.close-btn {
  font-size: 24px;
  color: #999;
  cursor: pointer;
  width: 30px;
  height: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s;
}

.close-btn:hover {
  color: #333;
}

.lyric-modal-body {
  padding: 20px;
}

/* 自动获取歌词弹窗内容样式 */
.auto-fetch-modal-body {
  padding: 20px;
}

/* 歌曲信息组样式 */
.song-info-group {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.song-info-label {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.song-info-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-field {
  display: flex;
  align-items: center;
  gap: 10px;
}

.field-name {
  width: 80px;
  font-size: 14px;
  color: #666;
  text-align: right;
}

.info-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
}

/* 获取歌词按钮 */
.fetch-lyric-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
  margin-bottom: 20px;
}

.fetch-lyric-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 歌词结果组样式 */
.lyric-result-group {
  margin-top: 20px;
}

.lyric-result-label {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

/* 歌词来源标签页 */
.lyric-source-tabs {
  display: flex;
  gap: 5px;
  margin-bottom: 15px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.source-tab {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  color: #333;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 5px;
}

.source-tab.active {
  background-color: v-bind(mainColorDark);
  color: white;
  border-color: v-bind(mainColorDark);
}

.source-tab:hover:not(.active) {
  border-color: v-bind(mainColor);
  color: v-bind(mainColorDark);
}

/* 状态标签 */
.success-tag {
  color: #4cd964;
  font-weight: bold;
}

.failed-tag {
  color: #ff3b30;
  font-weight: bold;
}

/* 歌词预览容器 */
.lyric-preview-container {
  margin-bottom: 15px;
}

.lyric-preview-textarea {
  width: 100%;
  height: 200px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  background-color: #f9f9f9;
}

/* 填入歌词按钮 */
.fill-lyric-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  margin-bottom: 10px;
}

.fill-lyric-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 单曲选择样式 */
.track-select-group {
  margin-bottom: 20px;
}

.track-select-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.track-select-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
}

/* 新增：翻译语言选择器样式 */
.translate-lang-select-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 8px;
}

/* 原版歌词输入框头部（包含自动获取按钮） */
.lyric-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

/* 自动获取歌词按钮 */
.auto-fetch-lyric-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.auto-fetch-lyric-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.translate-lang-select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
  background-color: white;
}

.lyric-input-group {
  margin-bottom: 20px;
}

.lyric-input-label {
  display: block;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.lyric-textarea {
  width: 100%;
  height: 200px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  line-height: 1.8;
  resize: vertical;
  font-family: inherit;
  box-sizing: border-box;
}

.lyric-format-tip {
  margin-top: 10px;
  font-size: 12px;
  color: #666;
  line-height: 1.5;
}

.lyric-modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.modal-cancel-btn {
  padding: 8px 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  color: #666;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.modal-cancel-btn:hover {
  background: #f5f5f5;
}

.modal-save-btn, .modal-save-all-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.modal-save-btn:hover, .modal-save-all-btn:hover {
  opacity: 0.9;
}
</style>