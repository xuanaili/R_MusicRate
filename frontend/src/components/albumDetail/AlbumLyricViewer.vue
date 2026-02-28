<template>
  <!-- 模板部分保持不变，仅添加一键获取按钮 -->
  <div class="lyric-detail-container">
    <!-- 主体内容：单栏布局 -->
    <div class="lyric-detail-main">
      <!-- 歌词展示区域 -->
      <div class="lyric-column">
        <!-- 无歌词提示 -->
        <div v-if="!hasLyricContent" class="no-lyric-tip">
          暂无歌词数据
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
          <!-- 固定显示的歌名 -->
          <div class="fixed-track-title"
               @mouseenter="showUploadBtn = true"
               @mouseleave="showUploadBtn = false">
            <div class="track-title-wrapper" @click="toggleTrackDropdown">
              <h2>{{ currentPlayingTrackName }}</h2>
            </div>

            <button
              v-if="isAdmin && showUploadBtn"
              class="upload-lyric-btn"
              :style="{backgroundColor: mainColorDark}"
              @click="showUploadLyricModal = true"
            >
              上传/编辑歌词
            </button>

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

          <!-- 滚动的歌词内容 -->
          <div
              class="lyrics-content"
              ref="lyricsContent"
              @scroll="handleManualScroll"
          >
            <div class="lyric-scroll-container">
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
                  <div
                      class="original-lyric-item"
                      :style="getLyricItemStyle(index, highlightedCombinedIndex)"
                  >
                    <span class="lyric-text">{{ item.originalText }}</span>
                    <span class="lyric-time">{{ formatTime(item.time) }}</span>
                  </div>

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

              <!-- 原版歌词输入框 - 添加ref用于绑定粘贴事件 -->
              <div class="lyric-input-group">
                <div class="lyric-input-header">
                  <label class="lyric-input-label">
                    {{ trackList[selectedTrackIndex]?.name || '当前单曲' }} 原版歌词（绝对时间）
                  </label>
                  <div class="lyric-btn-group">
                    <!-- 新增：一键获取所有歌词按钮 -->
                    <button
                      class="batch-fetch-lyric-btn"
                      :style="{backgroundColor: mainColorDarkDouble}"
                      @click="startBatchFetchLyrics"
                      :disabled="!trackList.length || batchFetchLoading"
                    >
                      <i class="icon-batch-fetch">🔄</i>
                      <span v-if="!batchFetchLoading">一键获取所有歌词</span>
                      <span v-if="batchFetchLoading">处理中: {{batchFetchCurrent}}/{{batchFetchTotal}}</span>
                    </button>

                    <button
                        class="auto-fetch-lyric-btn"
                        :style="{backgroundColor: mainColorDark}"
                        @click="showAutoFetchLyricModal = true"
                        :disabled="!trackList[selectedTrackIndex]?.name"
                    >
                      <i class="icon-fetch">📝</i> 自动获取歌词
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
                <!-- 关键修改：添加ref="originalLyricTextarea" -->
                <textarea
                    ref="originalLyricTextarea"
                    v-model="currentTrackLyricContent"
                    class="lyric-textarea"
                    placeholder="请按格式输入歌词：
00:00 歌词第一句
00:05 歌词第二句
00:10 歌词第三句
（时间格式：mm:ss 或 mm:ss.xx，使用绝对时间）"
                    @change="handleLyricInputChange(currentTrackLyricContent)"
                ></textarea>
              </div>

              <!-- 翻译歌词输入框 -->
              <div class="lyric-input-group">
                <div class="translate-lang-select-wrapper">
                  <label class="lyric-input-label">
                    {{ trackList[selectedTrackIndex]?.name || '当前单曲' }} 中文翻译歌词（可选，绝对时间）
                  </label>
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
                    @change="handleTranslateLyricInputChange(currentTrackTranslateContent)"
                ></textarea>
              </div>

              <div class="lyric-format-tip">
                📝 格式说明：每行一个歌词条目，时间和歌词用空格分隔，支持 mm:ss 或 mm:ss.xx 格式
                <br/>
                📌 提示：请输入绝对时间（从专辑开始的总时间），系统会自动按时间轴连续展示
              </div>
            </div>
            <div class="lyric-modal-footer" style="display: none;">
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
                  <div class="info-field">
                    <span class="field-name">网易云链接：</span>
                    <input
                        v-model="fetchNeteaseUrl"
                        class="info-input"
                        placeholder="例如：https://music.163.com/#/song?id=3315852235"
                    />
                  </div>
                </div>
              </div>

              <button
                  class="fetch-lyric-btn"
                  :style="{backgroundColor: mainColorDark}"
                  @click="fetchLyrics"
                  :disabled="fetchLoading || (!fetchSongName.trim() && !fetchNeteaseUrl.trim())"
              >
                <span v-if="fetchLoading">获取中...</span>
                <span v-else>点击获取歌词</span>
              </button>

              <div v-if="fetchResult" class="lyric-result-group">
                <label class="lyric-result-label">选择歌词来源</label>
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

                <div class="lyric-preview-container">
                  <textarea
                      v-model="selectedLyricContent"
                      class="lyric-preview-textarea"
                      readonly
                      placeholder="暂无歌词..."
                  ></textarea>
                </div>

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
      currentTranslateLang: 'CN',
      highlightedIndex: -1,
      highlightedTranslateIndex: -1,
      highlightedCombinedIndex: -1,
      scrollTimer: null,
      // 1. 移除：删除resetTimer变量
      showUploadLyricModal: false,
      lyricTextareaContent: '',
      translateTextareaContent: '',
      localParsedLyrics: [],
      localParsedTranslateLyrics: {},
      combinedLyrics: [],
      isScrolling: false,
      showUploadBtn: false,
      trackDropdownOpen: false,
      showAutoFetchLyricModal: false,
      fetchSongName: '',
      fetchArtist: this.album.singer || '',
      fetchDuration: 0,
      fetchNeteaseUrl: '',
      fetchLoading: false,
      fetchResult: null,
      lyricSources: [
        {key: 'netease', name: '网易云音乐'},
        {key: 'kugou', name: '酷狗音乐'},
        {key: 'qq', name: 'QQ音乐'},
        {key: 'genius', name: 'Genius'}
      ],
      selectedSource: 'netease',
      selectedLyricContent: '',
      scrollAnimationTimer: null,
      // 新增批量获取相关状态
      batchFetchLoading: false,
      batchFetchCurrent: 0,
      batchFetchTotal: 0,
      batchFetchTimer: null,
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
          this.fetchNeteaseUrl = '';
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
        this.localParsedLyrics = this.parseLyricText(newVal.lyric_text || '');

        this.localParsedTranslateLyrics = {};
        try {
          const translateObj = JSON.parse(newVal.lyric_translate || '{}');
          Object.keys(translateObj).forEach(lang => {
            this.localParsedTranslateLyrics[lang] = this.parseLyricText(translateObj[lang] || '');
          });
          this.currentTranslateLang = 'CN';
        } catch (e) {
          this.localParsedTranslateLyrics['CN'] = this.parseLyricText(newVal.lyric_translate || '');
        }

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
        if (this.fetchResult && this.fetchResult[newVal]) {
          this.selectedLyricContent = this.fetchResult[newVal].lyric || '';
        } else {
          this.selectedLyricContent = '';
        }
        this.autoSelectFirstSuccessSource();
      },
      immediate: true
    },
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
    // 2. 移除：删除startResetTimer()调用
    document.addEventListener('click', this.handleClickOutside);

    // 关键修改：绑定粘贴事件
    this.$nextTick(() => {
      this.bindLyricPasteEvent();
      this.updateCurrentLyric();
    });
  },
  beforeUnmount() {
    if (this.scrollTimer) {
      clearTimeout(this.scrollTimer);
    }
    // 3. 移除：删除resetTimer的清理逻辑
    document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    document.removeEventListener('click', this.handleClickOutside);

    clearTimeout(this.scrollAnimationTimer);

    // 清理批量获取计时器
    if (this.batchFetchTimer) {
      clearTimeout(this.batchFetchTimer);
    }

    // 关键修改：解绑粘贴事件
    if (this.$refs.originalLyricTextarea) {
      this.$refs.originalLyricTextarea.removeEventListener('paste', this.handleLyricPaste);
    }
  },
  methods: {
    // 关键新增：绑定粘贴事件
    bindLyricPasteEvent() {
      const textarea = this.$refs.originalLyricTextarea;
      if (textarea) {
        // 先移除可能存在的旧事件
        textarea.removeEventListener('paste', this.handleLyricPaste);
        // 绑定新的粘贴事件
        textarea.addEventListener('paste', this.handleLyricPaste);
      }
    },

    // 关键修复：处理歌词粘贴拆分逻辑
    async handleLyricPaste(e) {
      e.preventDefault(); // 阻止默认粘贴行为

      try {
        // 读取剪贴板内容
        const pastedContent = await navigator.clipboard.readText();
        if (!pastedContent.trim()) return;

        // 按行分割并清理空行
        const lines = pastedContent.split(/\r?\n/).map(line => line.trim()).filter(Boolean);

        // 统一解析所有 [xx:xx.xxx] 格式的歌词行
        const allItems = [];
        for (const line of lines) {
          // 匹配 [mm:ss.xxx] 或 mm:ss.xxx 格式（兼容带/不带中括号）
          const regex = /(?:\[)?(\d{2}:\d{2}\.\d+)(?:\])?\s*(.+)/;
          const match = line.match(regex);
          if (!match) continue;

          let timeStr = match[1]; // 原始时间字符串（如 01:41.532）
          const text = match[2].trim();
          if (!text) continue;

          // 过滤掉作词作曲/by: 等无效行
          if (/^[:：by:作词作曲编曲演唱专辑]/.test(text)) continue;

          // 解析时间并格式化
          const time = this.parseTimeStr(timeStr);
          const formattedTimeStr = this.formatTimeForOutput(time);

          allItems.push({
            time: parseFloat(time.toFixed(1)), // 保留1位小数用于分组
            rawTimeStr: timeStr,
            timeStr: formattedTimeStr,
            text
          });
        }

        if (allItems.length === 0) {
          // 没有解析到有效歌词，直接粘贴原始内容
          this.currentTrackLyricContent = pastedContent;
          return;
        }

        // 按格式化后的时间（1位毫秒）分组，确保精准匹配
        const groups = {};
        for (const item of allItems) {
          const key = item.time.toFixed(1); // 01:41.532 → 101.5 → 分组key
          if (!groups[key]) groups[key] = [];
          groups[key].push(item);
        }

        // 检查是否包含双语（同一时间戳下有多个文本）
        const hasMulti = Object.values(groups).some(g => g.length >= 2);
        if (!hasMulti) {
          // 不是双语，直接输出格式化后的歌词
          this.currentTrackLyricContent = allItems.map(i => `${i.timeStr} ${i.text}`).join('\n');
          return;
        }

        // 开始拆分：第一组=原版（非中文），第二组=翻译（中文）
        const originalLines = [];
        const translateLines = [];
        // 检测是否为中文的辅助函数（更精准的中文检测）
        const isChinese = (str) => {
          // 匹配中文字符、中文标点
          return /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(str);
        };

        // 按时间排序处理
        const sortedKeys = Object.keys(groups).sort((a, b) => a - b);
        for (const key of sortedKeys) {
          const items = groups[key];
          if (items.length === 0) continue;

          // 分离中文和非中文内容
          const chineseItems = items.filter(item => isChinese(item.text));
          const originalItems = items.filter(item => !isChinese(item.text));

          // 优先使用非中文作为原版，没有则取第一个
          const originalItem = originalItems.length > 0 ? originalItems[0] : items[0];
          // 中文作为翻译
          const chineseItem = chineseItems.length > 0 ? chineseItems[0] : null;

          if (originalItem) {
            originalLines.push(`${originalItem.timeStr} ${originalItem.text}`);
          }
          if (chineseItem) {
            translateLines.push(`${chineseItem.timeStr} ${chineseItem.text}`);
          }
        }

        // 核心修复：确保数据更新触发视图刷新
        this.$nextTick(() => {
          this.currentTrackLyricContent = originalLines.join('\n');
          this.currentTrackTranslateContent = translateLines.join('\n');

          // 提示用户拆分成功
          if (this.$message) {
            this.$message.success('已自动拆分双语歌词，格式适配为 mm:ss.x！');
          }
        });

      } catch (err) {
        console.error('粘贴失败', err);
        // 降级处理：直接粘贴原始内容
        try {
          this.currentTrackLyricContent = await navigator.clipboard.readText();
        } catch (e) {
          this.currentTrackLyricContent = '';
        }
      }
    },

    // 新增：专门用于输出的时间格式化方法（mm:ss.x）
    formatTimeForOutput(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '00:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      const ms = Math.floor((seconds % 1) * 10); // 只保留1位毫秒
      return ms > 0
          ? `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms}`
          : `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },

    async fetchLyrics() {
      if (!this.fetchSongName.trim() && !this.fetchNeteaseUrl.trim()) {
        this.$message?.warning('歌曲名和网易云链接不能同时为空！');
        return;
      }

      this.fetchLoading = true;
      this.fetchResult = null;
      this.selectedLyricContent = '';

      try {
        let res;
        if (this.fetchNeteaseUrl.trim()) {
          res = await this.$axios.post(
              '/api/lyric/parse_netease_url',
              {
                song_url: this.fetchNeteaseUrl.trim()
              },
              {headers: {Authorization: localStorage.getItem('token') || ''}}
          );

          if (res.data.code === 200) {
            this.fetchResult = {
              netease: {
                status: 'success',
                lyric: res.data.data.lyric_text || ''
              },
              kugou: {status: 'failed', lyric: ''},
              qq: {status: 'failed', lyric: ''},
              genius: {status: 'failed', lyric: ''}
            };
            this.$message?.success('通过网易云链接获取歌词成功！');
          } else {
            this.$message?.error(res.data.msg || '通过网易云链接获取歌词失败！');
            this.fetchResult = null;
          }
        } else {
          res = await this.$axios.post(
              '/api/lyric/fetch_auto',
              {
                song_name: this.fetchSongName.trim(),
                artist: this.fetchArtist.trim(),
                duration: this.fetchDuration
              },
              {headers: {Authorization: localStorage.getItem('token') || ''}}
          );

          if (res.data.code === 200) {
            let lyricsData = res.data.data?.lyrics || res.data.data || {};

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
            this.autoSelectFirstSuccessSource();
            this.$message?.success('歌词获取成功！');
          } else {
            this.$message?.error(res.data.msg || '歌词获取失败！');
            this.fetchResult = null;
          }
        }
      } catch (error) {
        console.error('获取歌词失败：', error);
        this.$message?.error('网络错误，歌词获取失败！');
        this.fetchResult = null;
      } finally {
        this.fetchLoading = false;
        this.$forceUpdate();
      }
    },

    parseLrcToStandardFormat(lrcText) {
      if (!lrcText || typeof lrcText !== 'string') return '';

      const lines = lrcText.trim().split('\n');
      const standardLyrics = [];
      const processedTimes = new Set();

      lines.forEach(line => {
        const cleanLine = line.trim();
        if (!cleanLine) return;

        const timePattern = /\[(\d{2}):(\d{2})(?:\.(\d{1,3}))?\]/g;
        let match;
        let lyricText = cleanLine;
        const timeTags = [];

        while ((match = timePattern.exec(cleanLine)) !== null) {
          const [fullMatch, min, sec, ms] = match;
          const totalSeconds =
              parseInt(min) * 60 +
              parseInt(sec) +
              (ms ? parseInt(ms) / (ms.length === 3 ? 1000 : 100) : 0);

          timeTags.push({
            tag: fullMatch,
            time: Math.round(totalSeconds * 10) / 10
          });

          lyricText = lyricText.replace(fullMatch, '').trim();
        }

        if (timeTags.length === 0) return;

        const invalidPatterns = [
          /作词\s*[:：]/i,
          /作曲\s*[:：]/i,
          /编曲\s*[:：]/i,
          /制作人\s*[:：]/i,
          /演唱\s*[:：]/i,
          /原唱\s*[:：]/i,
          /专辑\s*[:：]/i,
          /歌名\s*[:：]/i,
          /Lyrics\s*[:：]/i,
          /Music\s*[:：]/i,
          /Album\s*[:：]/i,
          /by:/i
        ];

        const isInvalid = invalidPatterns.some(pattern => pattern.test(lyricText));
        if (isInvalid || !lyricText) return;

        timeTags.forEach(({ time }) => {
          if (processedTimes.has(time)) return;
          processedTimes.add(time);

          const minutes = Math.floor(time / 60);
          const seconds = Math.floor(time % 60);
          const milliseconds = Math.round((time % 1) * 10);

          let timeStr = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
          if (milliseconds > 0) {
            timeStr += `.${milliseconds}`;
          }

          standardLyrics.push({
            time: time,
            timeStr: timeStr,
            text: lyricText
          });
        });
      });

      return standardLyrics
          .sort((a, b) => a.time - b.time)
          .map(item => `${item.timeStr} ${item.text}`)
          .join('\n');
    },

    handleLyricInputChange(content) {
      const lrcPattern = /\[\d{2}:\d{2}\.\d{1,3}\]/;
      if (lrcPattern.test(content)) {
        const standardContent = this.parseLrcToStandardFormat(content);
        if (standardContent) {
          this.currentTrackLyricContent = standardContent;
          this.$message?.info('已自动将LRC格式歌词转换为标准格式');
        }
      }
    },

    handleTranslateLyricInputChange(content) {
      const lrcPattern = /\[\d{2}:\d{2}\.\d{1,3}\]/;
      if (lrcPattern.test(content)) {
        const standard = this.parseLrcToStandardFormat(content);
        if (standard) {
          this.currentTrackTranslateContent = standard;
          this.$message?.info('已自动将翻译LRC歌词转换为标准格式');
        }
      }
    },

    autoSelectFirstSuccessSource() {
      if (!this.fetchResult) return;

      const successSource = this.lyricSources.find(source => {
        return this.fetchResult[source.key]?.status === 'success' &&
            this.fetchResult[source.key]?.lyric?.trim();
      });

      if (successSource) {
        this.selectedSource = successSource.key;
        this.selectedLyricContent = this.fetchResult[successSource.key].lyric || '';
      }
    },

    fillLyricToInput() {
      if (!this.selectedLyricContent.trim()) {
        this.$message?.warning('暂无歌词可填入！');
        return;
      }

      const standardLyricText = this.parseLrcToStandardFormat(this.selectedLyricContent);
      if (!standardLyricText) {
        this.$message?.warning('未解析到有效歌词内容！');
        return;
      }

      const lines = standardLyricText.trim().split('\n');
      const relativeLyrics = [];

      lines.forEach(line => {
        const match = line.match(/^(\d{2}:\d{2}(?:\.\d{1,2})?)\s+(.+)$/);
        if (match) {
          const [, timeStr, lyricText] = match;
          const absoluteTime = this.parseTimeStr(timeStr);
          const relativeTime = Math.max(0, absoluteTime);

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
              const msRounded = Math.round(ms * 10);
              formattedTime = `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${msRounded}`;
            }
          }

          if (!(formattedTime === '00:00' && !lyricText.trim())) {
            relativeLyrics.push(`${formattedTime} ${lyricText}`);
          }
        }
      });

      this.currentTrackLyricContent = relativeLyrics.join('\n');
      this.showAutoFetchLyricModal = false;
      this.$message?.success('歌词已格式化并填入输入框！');
    },

    closeAutoFetchModal() {
      this.showAutoFetchLyricModal = false;
      this.fetchResult = null;
      this.selectedLyricContent = '';
      this.selectedSource = 'netease';
      this.fetchNeteaseUrl = '';

      // 清理批量计时器
      if (this.batchFetchTimer) {
        clearTimeout(this.batchFetchTimer);
        this.batchFetchTimer = null;
      }
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

    formatTime(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '00:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      const ms = Math.floor((seconds % 1) * 10);
      return ms > 0
          ? `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms}`
          : `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },

    // 解析时间字符串为秒数 (兼容 mm:ss.xxx 格式)
    parseTimeStr(timeStr) {
      try {
        const [minPart, rest] = timeStr.split(':');
        if (!rest) return 0;

        const min = parseInt(minPart, 10);
        let sec = 0;

        if (rest.includes('.')) {
          const [secPart, msPart] = rest.split('.');
          sec = parseInt(secPart, 10);
          // 处理3位毫秒数
          const ms = parseInt(msPart, 10) / 1000;
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
          let time = this.parseTimeStr(timeMatch[1]);
          time = Math.floor(time * 10) / 10;

          const text = timeMatch[2].trim();
          if (text) {
            lyrics.push({time, text});
          }
        }
      });

      return lyrics.sort((a, b) => a.time - b.time);
    },

    combineLyrics() {
      this.combinedLyrics = [];

      const cnLyrics = this.localParsedTranslateLyrics['CN'] || [];

      const cnLyricMap = new Map();
      cnLyrics.forEach(item => {
        const timeKey = Math.floor(item.time * 10) / 10;
        cnLyricMap.set(timeKey, item.text);
      });

      const processedTimeKeys = new Set();
      this.localParsedLyrics.forEach(originalItem => {
        const timeKey = Math.floor(originalItem.time * 10) / 10;
        processedTimeKeys.add(timeKey);

        this.combinedLyrics.push({
          time: originalItem.time,
          originalText: originalItem.text,
          cnText: cnLyricMap.get(timeKey) || ''
        });

        if (cnLyricMap.has(timeKey)) {
          cnLyricMap.delete(timeKey);
        }
      });

      cnLyricMap.forEach((text, timeKey) => {
        if (!processedTimeKeys.has(timeKey)) {
          this.combinedLyrics.push({
            time: timeKey,
            originalText: '',
            cnText: text
          });
        }
      });

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
      translateObj['CN'] = translateText;

      return {
        lyric_text: lyricText,
        lyric_translate: JSON.stringify(translateObj)
      };
    },

    isCurrentCombinedLyric(index) {
      const currentLyric = this.combinedLyrics[index];
      if (!currentLyric) return false;

      const currentTime = this.currentTime;
      const nextLyric = this.combinedLyrics[index + 1];
      const nextLyricTime = nextLyric ? nextLyric.time : Infinity;

      return currentTime >= currentLyric.time && currentTime < nextLyricTime;
    },

    updateCurrentLyric() {
      if (this.isScrolling) return;

      this.updateHighlightedCombinedIndex();

      this.$nextTick(() => {
        if (this.highlightedCombinedIndex !== -1 && !this.isScrolling) {
          clearTimeout(this.scrollAnimationTimer);
          this.scrollAnimationTimer = setTimeout(() => {
            this.scrollToCurrentCombinedLyric(this.highlightedCombinedIndex);
          }, 50);
        }
      });
    },

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

              this.smoothScrollTo(lyricsContent, safeScrollTop, 300);
              return;
            }
          }
        }

        setTimeout(() => {
          this.isScrolling = false;
        }, 100);
      });
    },

    smoothScrollTo(element, targetPosition, duration = 300) {
      const startPosition = element.scrollTop;
      const distance = targetPosition - startPosition;
      const startTime = performance.now();

      const easeOutQuad = (t, b, c, d) => {
        t /= d;
        return -c * t * (t - 2) + b;
      };

      const animateScroll = (currentTime) => {
        const timeElapsed = currentTime - startTime;
        const scrollPosition = easeOutQuad(
            Math.min(timeElapsed, duration),
            startPosition,
            distance,
            duration
        );

        element.scrollTop = scrollPosition;

        if (timeElapsed < duration) {
          requestAnimationFrame(animateScroll);
        } else {
          setTimeout(() => {
            this.isScrolling = false;
          }, 50);
        }
      };

      requestAnimationFrame(animateScroll);
    },

    getLyricItemStyle(index, highlightedIndex, isCn = false) {
      if (highlightedIndex === -1) return {};

      const distance = Math.abs(index - highlightedIndex);
      let opacity = 1;
      let baseFontSize = isCn ? 22 : 26;
      let fontSize = baseFontSize - (distance * 4);
      fontSize = Math.max(16, fontSize);
      fontSize = `${fontSize}px`;

      let fontWeight = distance === 0 ? 700 : 400;

      if (distance > 0) {
        opacity = Math.max(0.5, 1 - (distance * 0.15));
      }

      return {
        opacity,
        fontSize,
        fontWeight,
        transition: 'opacity 0.4s ease, fontSize 0.4s ease, fontWeight 0.4s ease'
      };
    },

    // 4. 修改：清空handleManualScroll方法内容
    handleManualScroll() {
      // 移除：删除重置计时器的逻辑
    },

    // 5. 移除：删除startResetTimer方法
    // 6. 移除：删除resetResetTimer方法
    // 7. 移除：删除resetLyricPosition方法

    handleLyricClick(time) {
      this.$emit('jump-to-time', time);
      // 8. 移除：删除resetResetTimer()调用
    },

    closeModal() {
      this.showUploadLyricModal = false;
    },

    async saveAndUploadAllLyrics() {
      if (!this.currentTrackLyricContent.trim()) {
        this.$message?.warning('原版歌词内容不能为空！');
        return;
      }
      this.trackLyricsMap[this.selectedTrackIndex] = {
        lyric: this.currentTrackLyricContent.trim(),
        translate: this.currentTrackTranslateContent.trim(),
        lang: 'CN'
      };
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
          this.$emit('update:lyrics', integratedData);
          this.localParsedLyrics = this.parseLyricText(integratedData.lyric_text);
          let translateText = '';
          try {
            const translateObj = JSON.parse(integratedData.lyric_translate || '{}');
            translateText = translateObj['CN'] || '';
          } catch (e) {
            translateText = integratedData.lyric_translate || '';
          }
          this.localParsedTranslateLyrics['CN'] = this.parseLyricText(translateText);
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

    async saveAllLyrics() {
      await this.saveAndUploadAllLyrics();
    },

    // 新增：批量获取所有歌词
    async startBatchFetchLyrics() {
      if (this.trackList.length === 0) {
        this.$message?.warning('暂无歌曲可处理！');
        return;
      }

      // 确认操作
      const confirm = window.confirm('确认要批量获取所有歌曲的歌词吗？这个过程可能需要较长时间，请耐心等待！');
      if (!confirm) return;

      this.batchFetchLoading = true;
      this.batchFetchCurrent = 0;
      this.batchFetchTotal = this.trackList.length;

      // 开始处理第一首
      await this.processNextTrackInBatch();
    },

    // 处理批量获取中的下一首歌曲
    async processNextTrackInBatch() {
      // 检查是否处理完所有歌曲
      if (this.batchFetchCurrent >= this.batchFetchTotal) {
        this.batchFetchLoading = false;
        this.$message?.success(`批量获取完成！共处理 ${this.batchFetchTotal} 首歌曲`);
        return;
      }

      try {
        // 1. 选择当前要处理的歌曲
        const currentIndex = this.batchFetchCurrent;
        this.selectedTrackIndex = currentIndex;

        // 等待DOM更新和数据加载
        await this.$nextTick();

        // 2. 打开自动获取歌词弹窗
        this.showAutoFetchLyricModal = true;
        await this.$nextTick();

        // 3. 自动点击获取歌词按钮
        if (!this.fetchSongName.trim()) {
          this.$message?.warning(`第 ${currentIndex + 1} 首歌曲无名称，跳过处理`);
          this.batchFetchCurrent++;
          this.processNextTrackInBatch();
          return;
        }

        // 调用获取歌词方法
        await this.fetchLyrics();

        // 4. 等待10秒，让歌词获取完成
        this.batchFetchTimer = setTimeout(async () => {
          try {
            // 检查是否获取到歌词
            if (this.fetchResult && this.selectedLyricContent.trim()) {
              // 填入歌词输入框
              this.fillLyricToInput();
              this.$message?.info(`第 ${currentIndex + 1} 首歌曲歌词获取成功并填入`);

              // 保存当前歌词到映射表
              this.trackLyricsMap[currentIndex] = {
                lyric: this.currentTrackLyricContent.trim(),
                translate: this.currentTrackTranslateContent.trim(),
                lang: 'CN'
              };
            } else {
              this.$message?.warning(`第 ${currentIndex + 1} 首歌曲未获取到有效歌词`);
            }

            // 关闭弹窗
            this.closeAutoFetchModal();

            // 处理下一首
            this.batchFetchCurrent++;
            this.processNextTrackInBatch();
          } catch (error) {
            console.error(`处理第 ${currentIndex + 1} 首歌曲失败`, error);
            this.$message?.error(`第 ${currentIndex + 1} 首歌曲处理失败：${error.message}`);

            // 继续处理下一首
            this.batchFetchCurrent++;
            this.processNextTrackInBatch();
          }
        }, 10000); // 等待10秒

      } catch (error) {
        console.error('批量处理歌曲失败', error);
        this.$message?.error(`处理第 ${this.batchFetchCurrent + 1} 首歌曲时出错：${error.message}`);

        // 继续处理下一首
        this.batchFetchCurrent++;
        this.processNextTrackInBatch();
      }
    }
  }
};
</script>
<style scoped>
/* 样式部分保持不变，新增整合版歌词样式 */
/* 批量获取歌词按钮样式 */
.batch-fetch-lyric-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  margin-right: 8px;
}

.batch-fetch-lyric-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.batch-fetch-lyric-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: scale(1.02);
}
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
/* 原版歌词项 */
.original-lyric-item {
  padding: 8px 15px;
  margin: 2px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  /* 未高亮：中灰，不抢风头 */
  color: #888888;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: opacity, font-size, font-weight, color;
}
/* 中文翻译歌词项 */
.cn-lyric-item {
  padding: 4px 15px 8px;
  margin: 2px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  /* 翻译同色系，更协调 */
  color: #888888;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: opacity, font-size, font-weight, color;
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

/* 优化歌词项的过渡效果 */
.original-lyric-item, .cn-lyric-item {
  /* 增强过渡效果，包含所有变化属性 */
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  /* 硬件加速，提升动画流畅度 */
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: opacity, font-size, font-weight, color;
}

/* 歌词滚动容器优化 */
.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  /* 保留 auto，避免和自定义动画冲突 */
  scroll-behavior: auto;
  position: relative;
  /* 添加硬件加速 */
  transform: translateZ(0);
}

/* 优化高亮歌词的过渡 */
.lyric-pair {
  transition: all 0.2s ease;
}

.lyric-pair.highlighted {
  padding: 4px;
  border-radius: 8px;
  /* 添加轻微的缩放效果，增强视觉反馈 */
  transform: scale(1.02);
  transition: all 0.3s ease;
}
</style>