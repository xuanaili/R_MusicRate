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
          <!-- v0.8.1 P2：无歌词时也可直接触发 AI 识别整轨（生成草稿歌词），与上传按钮同排展示 -->
          <div v-if="isAdmin" class="no-lyric-btn-group">
            <button
              class="upload-lyric-btn no-lyric-upload-btn"
              :style="{backgroundColor: mainColorDark}"
              @click="showUploadLyricModal = true"
            >
              上传/编辑歌词
            </button>
            <button
              class="upload-lyric-btn no-lyric-upload-btn"
              :style="{backgroundColor: mainColor}"
              @click="$emit('trigger-ai-recognize')"
              :disabled="aiRecognizeLoading"
              title="对该专辑整轨 MP3 进行 AI 语音识别（需已上传整轨 MP3），识别结果自动写入全专辑歌词"
            >
              <i class="icon-ai-recognize">🤖</i>
              <span v-if="!aiRecognizeLoading">AI 识别整轨歌词</span>
              <span v-if="aiRecognizeLoading">识别中… {{ aiRecognizeProgress }}%</span>
            </button>
          </div>
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

            <!-- v0.8.1 P2：AI 识别整轨歌词按钮（悬停显示，与上传/编辑歌词对称放左侧，仅歌词展示页、仅管理员；
                 轮询逻辑在父组件 AlbumDetail，切换子页面识别持续） -->
            <button
              v-if="isAdmin && (showUploadBtn || aiRecognizeLoading)"
              class="ai-recognize-btn"
              :style="{backgroundColor: mainColor}"
              @click="$emit('trigger-ai-recognize')"
              :disabled="aiRecognizeLoading"
              title="对该专辑整轨 MP3 进行 AI 语音识别（需已上传整轨 MP3），识别结果自动写入全专辑歌词"
            >
              <i class="icon-ai-recognize">🤖</i>
              <span v-if="!aiRecognizeLoading">AI 识别整轨歌词</span>
              <span v-if="aiRecognizeLoading">识别中… {{ aiRecognizeProgress }}%</span>
            </button>

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

          <!-- v0.8.1 P2：AI 识别进度条（识别进行中显示，实时转写进度 + 阶段提示） -->
          <div
            v-if="aiRecognizeLoading || aiRecognizeProgress > 0"
            class="ai-recognize-progress-row"
          >
            <div class="ai-recognize-progress-track">
              <div
                class="ai-recognize-progress-fill"
                :style="{width: aiRecognizeProgress + '%', backgroundColor: mainColor}"
              ></div>
            </div>
            <span class="ai-recognize-progress-text">
              {{ aiRecognizeProgress }}% · {{ aiRecognizeStatusMsg }}
            </span>
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
                    <!-- 新增：批量上传 LRC 文件 -->
                    <button
                      class="batch-upload-lrc-btn"
                      :style="{backgroundColor: mainColorDarkDouble}"
                      @click="triggerLrcFileInput"
                      :disabled="batchUploadLoading"
                    >
                      <i class="icon-batch-upload">📁</i>
                      <span v-if="!batchUploadLoading">批量上传LRC文件</span>
                      <span v-if="batchUploadLoading">处理中: {{ batchUploadCurrent }}/{{ batchUploadTotal }}</span>
                    </button>
                    <input
                      ref="lrcFileInput"
                      type="file"
                      accept=".lrc,.krc"
                      multiple
                      class="lrc-file-input"
                      @change="handleLrcFileUpload"
                    >

                    <input
                      ref="wholeLrcFileInput"
                      type="file"
                      accept=".lrc"
                      class="lrc-file-input"
                      @change="handleWholeTrackLrcUpload"
                    >
                    <button
                      class="whole-lrc-upload-btn"
                      :style="{backgroundColor: mainColor}"
                      @click="triggerWholeLrcFileInput"
                      :disabled="wholeLrcUploadLoading"
                    >
                      <i class="icon-whole-lrc">🎵</i>
                      <span v-if="!wholeLrcUploadLoading">上传整轨LRC（绝对时间）</span>
                      <span v-if="wholeLrcUploadLoading">上传中...</span>
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
    },
    // v0.8.1 P2：AI 识别状态（轮询逻辑在父组件 AlbumDetail 常驻，本组件只接收展示）
    aiRecognizeLoading: {
      type: Boolean,
      default: false
    },
    aiRecognizeProgress: {
      type: Number,
      default: 0
    },
    aiRecognizeStatusMsg: {
      type: String,
      default: ''
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
      showUploadLyricModal: false,
      lyricTextareaContent: '',
      translateTextareaContent: '',
      localParsedLyrics: [],
      localParsedTranslateLyrics: {},
      combinedLyrics: [],
      isScrolling: false,
      showUploadBtn: false,
      trackDropdownOpen: false,
      scrollAnimationTimer: null,
      wholeLrcUploadLoading: false,
      batchUploadLoading: false,
      batchUploadCurrent: 0,
      batchUploadTotal: 0,
      batchUploadTimer: null,
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
      }, deep: true
    },
    selectedTrackIndex: {
      handler(newVal) {
        const trackLyrics = this.trackLyricsMap[newVal] || {lyric: '', translate: '', lang: 'CN'};
        this.currentTrackLyricContent = trackLyrics.lyric;
        this.currentTrackTranslateContent = trackLyrics.translate;
        this.currentTranslateLang = trackLyrics.lang || 'CN';
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
    }
  },
  mounted() {
    this.initTrackList();
    document.addEventListener('click', this.handleClickOutside);

    this.$nextTick(() => {
      this.bindLyricPasteEvent();
      this.updateCurrentLyric();
    });
  },
  beforeUnmount() {
    if (this.scrollTimer) clearTimeout(this.scrollTimer);
    document.removeEventListener('mousemove', this.handleTrackScoreMouseMove);
    document.removeEventListener('click', this.handleClickOutside);

    clearTimeout(this.scrollAnimationTimer);
    if (this.batchUploadTimer) clearTimeout(this.batchUploadTimer);

    if (this.$refs.originalLyricTextarea) {
      this.$refs.originalLyricTextarea.removeEventListener('paste', this.handleLyricPaste);
    }
  },
  methods: {
    bindLyricPasteEvent() {
      const textarea = this.$refs.originalLyricTextarea;
      if (textarea) {
        textarea.removeEventListener('paste', this.handleLyricPaste);
        textarea.addEventListener('paste', this.handleLyricPaste);
      }
    },

    async handleLyricPaste(e) {
      e.preventDefault();
      try {
        const pastedContent = await navigator.clipboard.readText();
        if (!pastedContent.trim()) return;

        const lines = pastedContent.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
        const allItems = [];
        const regex = /(?:\[)?(\d{2}:\d{2}\.\d+)(?:\])?\s*(.+)/;
        for (const line of lines) {
          const match = line.match(regex);
          if (!match) continue;
          let timeStr = match[1];
          const text = match[2].trim();
          if (!text) continue;
          if (/^[:：by:作词作曲编曲演唱专辑]/.test(text)) continue;

          const time = this.parseTimeStr(timeStr);
          const formattedTimeStr = this.formatTimeForOutput(time);
          allItems.push({
            time: parseFloat(time.toFixed(1)),
            rawTimeStr: timeStr,
            timeStr: formattedTimeStr,
            text
          });
        }

        if (allItems.length === 0) {
          this.currentTrackLyricContent = pastedContent;
          return;
        }

        const groups = {};
        for (const item of allItems) {
          const key = item.time.toFixed(1);
          if (!groups[key]) groups[key] = [];
          groups[key].push(item);
        }

        const hasMulti = Object.values(groups).some(g => g.length >= 2);
        if (!hasMulti) {
          this.currentTrackLyricContent = allItems.map(i => `${i.timeStr} ${i.text}`).join('\n');
          return;
        }

        const originalLines = [];
        const translateLines = [];
        const isChinese = (str) => /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(str);
        const sortedKeys = Object.keys(groups).sort((a, b) => a - b);

        for (const key of sortedKeys) {
          const items = groups[key];
          if (items.length === 0) continue;
          const chineseItems = items.filter(item => isChinese(item.text));
          const originalItems = items.filter(item => !isChinese(item.text));
          const originalItem = originalItems.length > 0 ? originalItems[0] : items[0];
          const chineseItem = chineseItems.length > 0 ? chineseItems[0] : null;

          if (originalItem) originalLines.push(`${originalItem.timeStr} ${originalItem.text}`);
          if (chineseItem) translateLines.push(`${chineseItem.timeStr} ${chineseItem.text}`);
        }

        this.$nextTick(() => {
          this.currentTrackLyricContent = originalLines.join('\n');
          this.currentTrackTranslateContent = translateLines.join('\n');
          this.$message?.success('已自动拆分双语歌词！');
        });

      } catch (err) {
        console.error('粘贴失败', err);
        this.currentTrackLyricContent = await navigator.clipboard.readText();
      }
    },

    formatTimeForOutput(seconds) {
      if (!seconds || isNaN(seconds) || seconds < 0) return '00:00';
      const min = Math.floor(seconds / 60);
      const sec = Math.floor(seconds % 60);
      const ms = Math.floor((seconds % 1) * 10);
      return ms > 0
        ? `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms}`
        : `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    },

    triggerLrcFileInput() {
      const fileInput = this.$refs.lrcFileInput;
      if (fileInput) fileInput.click();
    },

    // ========== 【核心修改】支持 KRC + LRC 自动识别转换 ==========
    async handleLrcFileUpload(e) {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      const confirmUpload = window.confirm(`检测到 ${files.length} 个文件，是否批量解析并自动匹配歌曲？`);
      if (!confirmUpload) {
        e.target.value = '';
        return;
      }

      this.batchUploadLoading = true;
      this.batchUploadCurrent = 0;
      this.batchUploadTotal = files.length;

      try {
        const trackNameMap = this.createTrackNameMatchMap();
        for (const file of files) {
          this.batchUploadCurrent++;
          await this.$nextTick();

          let lrcText = '';
          const ext = file.name.toLowerCase().split('.').pop();

          // 1. KRC 文件：调用后端接口转 LRC
          if (ext === 'krc') {
            try {
              const formData = new FormData();
              formData.append('krc_file', file);
              const res = await this.$axios.post('/api/lyric/krc2lrc', formData, {
                headers: {
                  Authorization: localStorage.getItem('token') || '',
                  'Content-Type': 'multipart/form-data'
                }
              });
              if (res.data.code === 200) {
                lrcText = res.data.data.lrc_text;
                this.$message?.success(`KRC转LRC成功: ${file.name}`);
              } else {
                this.$message?.warning(`KRC解析失败: ${file.name}`);
                continue;
              }
            } catch (err) {
              this.$message?.error(`KRC上传异常: ${file.name}`);
              continue;
            }
          }
          // 2. LRC 文件：直接读取
          else if (ext === 'lrc') {
            lrcText = await this.readFileContent(file);
          }
          else {
            this.$message?.warning(`不支持格式: ${file.name}`);
            continue;
          }

          if (!lrcText) continue;

          const matchedIndex = this.matchTrackByFileName(file.name, trackNameMap);
          if (matchedIndex === -1) {
            this.$message?.warning(`未匹配：${file.name}`);
            continue;
          }

          const standard = this.parseLrcToStandardFormat(lrcText);
          if (!standard) {
            this.$message?.warning(`解析失败：${file.name}`);
            continue;
          }

          this.trackLyricsMap[matchedIndex] = {
            ...this.trackLyricsMap[matchedIndex],
            lyric: standard
          };

          if (matchedIndex === this.selectedTrackIndex) {
            this.currentTrackLyricContent = standard;
          }
          await this.sleep(100);
        }
        this.$message?.success(`批量上传完成！共处理 ${this.batchUploadCurrent} 个文件`);
      } catch (error) {
        console.error('批量上传失败', error);
        this.$message?.error('批量上传失败');
      } finally {
        this.batchUploadLoading = false;
        e.target.value = '';
      }
    },

    createTrackNameMatchMap() {
      const map = new Map();
      this.trackList.forEach((track, index) => {
        const std = this.standardizeFileName(track.name);
        map.set(std, index);
        const simple = track.name.toLowerCase().replace(/\s+/g, '');
        map.set(simple, index);
      });
      return map;
    },

    standardizeFileName(name) {
      return name.replace(/\.[^.]+$/, '')
        .toLowerCase()
        .replace(/[^\w\u4e00-\u9fff]/g, '')
        .replace(/\s+/g, '');
    },

    matchTrackByFileName(fileName, trackNameMap) {
      const std = this.standardizeFileName(fileName);
      if (trackNameMap.has(std)) return trackNameMap.get(std);
      for (const [key, idx] of trackNameMap.entries()) {
        if (std.includes(key) || key.includes(std)) return idx;
      }
      return -1;
    },

    readFileContent(file) {
      return new Promise(resolve => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = () => resolve(null);
        reader.readAsText(file, 'utf-8');
      });
    },

    sleep(ms) {
      return new Promise(r => setTimeout(r, ms));
    },

    parseLrcToStandardFormat(lrcText) {
      if (!lrcText) return '';
      const lines = lrcText.trim().split('\n');
      const list = [];
      const set = new Set();
      lines.forEach(line => {
        const clean = line.trim();
        if (!clean) return;
        const reg = /\[(\d{2}):(\d{2})(?:\.(\d{1,3}))?\]/g;
        let m;
        let text = clean;
        const times = [];
        while ((m = reg.exec(clean)) !== null) {
          const min = parseInt(m[1]), sec = parseInt(m[2]), ms = m[3] ? parseInt(m[3]) / (m[3].length === 3 ? 1000 : 100) : 0;
          const t = min * 60 + sec + ms;
          times.push({t: Math.round(t * 10) / 10});
          text = text.replace(m[0], '').trim();
        }
        if (!times.length) return;
        if (/作词|作曲|编曲|演唱|专辑|by:/i.test(text) || !text) return;
        times.forEach(({t}) => {
          if (set.has(t)) return;
          set.add(t);
          const min = Math.floor(t / 60);
          const sec = Math.floor(t % 60);
          const ms = Math.round((t % 1) * 10);
          const ts = ms > 0
            ? `${min.toString().padStart(2,0)}:${sec.toString().padStart(2,0)}.${ms}`
            : `${min.toString().padStart(2,0)}:${sec.toString().padStart(2,0)}`;
          list.push({t, ts, text});
        });
      });
      return list.sort((a,b)=>a.t-b.t).map(i=>`${i.ts} ${i.text}`).join('\n');
    },

    handleLyricInputChange(c) {
      if (/\[\d{2}:\d{2}\.\d{1,3}\]/.test(c)) {
        const s = this.parseLrcToStandardFormat(c);
        if (s) this.currentTrackLyricContent = s;
      }
    },
    handleTranslateLyricInputChange(c) {
      if (/\[\d{2}:\d{2}\.\d{1,3}\]/.test(c)) {
        const s = this.parseLrcToStandardFormat(c);
        if (s) this.currentTrackTranslateContent = s;
      }
    },

    toggleTrackDropdown() {
      this.trackDropdownOpen = !this.trackDropdownOpen;
    },
    handleTrackJump(index) {
      this.$emit('jump-to-time', this.trackList[index].sec || 0);
      this.trackDropdownOpen = false;
    },
    handleClickOutside(e) {
      const el = document.querySelector('.fixed-track-title');
      if (el && !el.contains(e.target)) this.trackDropdownOpen = false;
    },
    secondsToTime(s) {
      if (!s || isNaN(s)) return '0:00:00';
      const h = Math.floor(s/3600), m = Math.floor(s%3600/60), sec = Math.floor(s%60);
      return `${h}:${m.toString().padStart(2,0)}:${sec.toString().padStart(2,0)}`;
    },

    initTrackList() {
      this.trackList = [];
      const names = this.tracks || [], secs = this.tracksTime || [];
      names.forEach((name, i) => {
        this.trackList.push({
          name: name.trim() || '未知曲目',
          sec: secs[i] || 0,
          duration: this.secondsToTime(secs[i] || 0)
        });
      });
      if (!this.trackList.length) this.trackList = [{name:'未知曲目',sec:0,duration:'0:00:00'}];
      this.initTrackLyricsMap();
    },

    initTrackLyricsMap() {
      this.trackLyricsMap = {};
      if (this.localParsedLyrics.length > 0) {
        this.trackList.forEach((t, i) => {
          const st = t.sec, et = this.trackList[i+1]?.sec || Infinity;
          const lyr = this.localParsedLyrics.filter(x => x.time >= st && x.time < et);
          const tlyr = (this.localParsedTranslateLyrics.CN || []).filter(x => x.time >= st && x.time < et);
          this.trackLyricsMap[i] = {
            lyric: lyr.map(x => `${this.formatTime(x.time - st)} ${x.text}`).join('\n'),
            translate: tlyr.map(x => `${this.formatTime(x.time - st)} ${x.text}`).join('\n'),
            lang: 'CN'
          };
        });
      } else {
        this.trackList.forEach((_, i) => {
          this.trackLyricsMap[i] = {lyric:'', translate:'', lang:'CN'};
        });
      }
      this.currentTrackLyricContent = this.trackLyricsMap[this.selectedTrackIndex]?.lyric || '';
      this.currentTrackTranslateContent = this.trackLyricsMap[this.selectedTrackIndex]?.translate || '';
    },

    formatTime(s) {
      if (!s || isNaN(s) || s < 0) return '00:00';
      const min = Math.floor(s/60), sec = Math.floor(s%60), ms = Math.floor((s%1)*10);
      return ms > 0
        ? `${min.toString().padStart(2,0)}:${sec.toString().padStart(2,0)}.${ms}`
        : `${min.toString().padStart(2,0)}:${sec.toString().padStart(2,0)}`;
    },

    parseTimeStr(str) {
      try {
        const [mPart, rest] = str.split(':');
        const m = parseInt(mPart);
        let sec = 0;
        if (rest.includes('.')) {
          const [sPart, msPart] = rest.split('.');
          sec = parseInt(sPart) + parseInt(msPart) / 1000;
        } else {
          sec = parseInt(rest);
        }
        return m * 60 + sec;
      } catch { return 0; }
    },

    parseLyricText(text) {
      if (!text) return [];
      const lines = text.trim().split('\n');
      const out = [];
      lines.forEach(line => {
        const m = line.match(/^(\d{1,2}:\d{2}(?:\.\d{1,2})?)\s+(.*)$/);
        if (m) {
          const t = this.parseTimeStr(m[1]);
          out.push({time: Math.floor(t*10)/10, text: m[2].trim()});
        }
      });
      return out.sort((a,b)=>a.time-b.time);
    },

    combineLyrics() {
      this.combinedLyrics = [];
      const cn = this.localParsedTranslateLyrics.CN || [];
      const map = new Map();
      cn.forEach(i => map.set(Math.floor(i.time*10)/10, i.text));
      this.localParsedLyrics.forEach(i => {
        const k = Math.floor(i.time*10)/10;
        this.combinedLyrics.push({time:i.time, originalText:i.text, cnText:map.get(k)||''});
        map.delete(k);
      });
      map.forEach((text, k) => {
        this.combinedLyrics.push({time:k, originalText:'', cnText:text});
      });
      this.combinedLyrics.sort((a,b)=>a.time-b.time);
    },

    integrateAllLyrics() {
      const lyr = [], tr = [];
      this.trackList.forEach((t, i) => {
        const st = t.sec;
        const m = this.trackLyricsMap[i] || {lyric:'', translate:''};
        this.parseLyricText(m.lyric).forEach(x => lyr.push({time:st+x.time, text:x.text}));
        this.parseLyricText(m.translate).forEach(x => tr.push({time:st+x.time, text:x.text}));
      });
      const lt = lyr.sort((a,b)=>a.time-b.time).map(x=>`${this.formatTime(x.time)} ${x.text}`).join('\n');
      const tt = tr.sort((a,b)=>a.time-b.time).map(x=>`${this.formatTime(x.time)} ${x.text}`).join('\n');
      return {
        lyric_text: lt,
        lyric_translate: JSON.stringify({CN: tt})
      };
    },

    updateCurrentLyric() {
      if (this.isScrolling) return;
      this.updateHighlightedCombinedIndex();
      this.$nextTick(() => {
        if (this.highlightedCombinedIndex !== -1) {
          clearTimeout(this.scrollAnimationTimer);
          this.scrollAnimationTimer = setTimeout(() => {
            this.scrollToCurrentCombinedLyric(this.highlightedCombinedIndex);
          }, 50);
        }
      });
    },

    updateHighlightedCombinedIndex() {
      let idx = -1;
      const now = this.currentTime;
      for (let i = this.combinedLyrics.length-1; i >=0; i--) {
        if (now >= this.combinedLyrics[i].time) {
          idx = i; break;
        }
      }
      this.highlightedCombinedIndex = idx;
    },

    scrollToCurrentCombinedLyric(idx) {
      if (idx === -1 || this.isScrolling) return;
      this.isScrolling = true;
      this.$nextTick(() => {
        const box = this.$refs.lyricsContent;
        if (!box) { this.isScrolling = false; return; }
        const items = box.querySelectorAll('.lyric-pair');
        if (!items[idx]) { this.isScrolling = false; return; }
        const h = box.clientHeight, ih = items[idx].offsetHeight;
        const top = items[idx].offsetTop - h/2 + ih/2;
        this.smoothScrollTo(box, Math.max(0, top), 300);
      });
    },

    smoothScrollTo(el, to, dur) {
      const st = el.scrollTop, d = to - st;
      const beg = performance.now();
      const ease = t => -t*(t-2);
      const run = now => {
        const p = Math.min(1, (now-beg)/dur);
        el.scrollTop = st + d*ease(p);
        if (p < 1) requestAnimationFrame(run);
        else setTimeout(()=>this.isScrolling=false, 50);
      };
      requestAnimationFrame(run);
    },

    getLyricItemStyle(i, hi, isCn=false) {
      if (hi === -1) return {};
      const dist = Math.abs(i-hi);
      const base = isCn ? 22 : 26;
      const size = Math.max(16, base - dist*4);
      const w = dist === 0 ? 700 : 400;
      const opa = dist > 0 ? Math.max(0.5, 1-dist*0.15) : 1;
      return {
        opacity: opa,
        fontSize: size+'px',
        fontWeight: w,
        transition: 'opacity 0.4s ease,font-size 0.4s ease,font-weight 0.4s ease'
      };
    },

    handleManualScroll() {},
    handleLyricClick(t) {
      this.$emit('jump-to-time', t);
    },
    closeModal() { this.showUploadLyricModal = false; },

    async saveAndUploadAllLyrics() {
      if (!this.currentTrackLyricContent.trim()) {
        this.$message?.warning('原版歌词不能为空');
        return;
      }
      this.trackLyricsMap[this.selectedTrackIndex] = {
        lyric: this.currentTrackLyricContent.trim(),
        translate: this.currentTrackTranslateContent.trim(),
        lang: 'CN'
      };
      try {
        const data = this.integrateAllLyrics();
        const res = await this.$axios.post(
          `/api/album/lyric/save/${this.album.source_pool_id || this.album.id}`,
          data,
          {headers: {Authorization: localStorage.getItem('token')||''}}
        );
        if (res.data.code === 200) {
          this.$message?.success('保存上传成功！');
          this.$emit('update:lyrics', data);
          this.localParsedLyrics = this.parseLyricText(data.lyric_text);
          const tr = JSON.parse(data.lyric_translate||'{}').CN || '';
          this.localParsedTranslateLyrics.CN = this.parseLyricText(tr);
          this.combineLyrics();
          this.$nextTick(()=>this.updateCurrentLyric());
        }
      } catch (e) {
        this.$message?.error('上传失败');
      }
    },

    // ========== 【新增 v0.8】整轨 LRC 文件上传（绝对时间覆盖全专辑，仅管理员） ==========
    triggerWholeLrcFileInput() {
      const fileInput = this.$refs.wholeLrcFileInput;
      if (fileInput) fileInput.click();
    },

    async handleWholeTrackLrcUpload(e) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith('.lrc')) {
        this.$message?.warning('仅支持 .lrc 格式文件');
        e.target.value = '';
        return;
      }

      this.wholeLrcUploadLoading = true;
      try {
        const formData = new FormData();
        formData.append('lrc_file', file);
        const res = await this.$axios.post(
          `/api/album/lyric/upload/${this.album.source_pool_id || this.album.id}`,
          formData,
          {
            headers: {
              Authorization: localStorage.getItem('token') || '',
              'Content-Type': 'multipart/form-data'
            }
          }
        );
        if (res.data.code === 200) {
          const data = res.data.data;
          const lyricsData = {
            lyric_text: data.lyric_text,
            lyric_translate: data.lyric_translate || '{}'
          };
          this.showUploadLyricModal = false;
          this.$message?.success('整轨 LRC 上传成功，已按单曲时间戳自动切分！');
          // 触发父组件 update:lyrics → 更新 album.lyric_text/lyric_translate → lyrics watcher
          // 调 initTrackLyricsMap 按 tracks_time 自动切分到各单曲（与逐单曲保存同机制）
          this.$emit('update:lyrics', lyricsData);
        } else {
          this.$message?.error(res.data.msg || '整轨 LRC 上传失败');
        }
      } catch (err) {
        this.$message?.error('整轨 LRC 上传异常：' + (err.response?.data?.msg || err.message));
      } finally {
        this.wholeLrcUploadLoading = false;
        e.target.value = '';
      }
    },

  }
};
</script>
<style scoped>
/* 样式部分保持不变 */
.whole-lrc-upload-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  margin-right: 8px;
}

.whole-lrc-upload-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.whole-lrc-upload-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: scale(1.02);
}

.lyric-detail-container {
  width: 100%;
  height: 89vh;
  font-family: "Microsoft YaHei", sans-serif;
  box-sizing: border-box;
}

.lyric-detail-main {
  height: 100%;
}

.lyric-column {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.batch-upload-lrc-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  margin-right: 8px;
}

.batch-upload-lrc-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.batch-upload-lrc-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: scale(1.02);
}

.lrc-file-input {
  display: none;
}

.no-lyric-tip {
  text-align: center;
  font-size: 18px;
  color: #666;
  margin-top: 50px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

/* 无歌词提示内的按钮组：覆盖 .upload-lyric-btn 的 absolute+opacity:0（悬停才显示）样式，改为正常静态排布可见 */
.no-lyric-btn-group {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 16px;
}
.no-lyric-btn-group .no-lyric-upload-btn {
  position: static;
  opacity: 1;
  transform: none;
}
.no-lyric-btn-group .no-lyric-upload-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: scale(1.02);
}
.no-lyric-btn-group .no-lyric-upload-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.lyrics-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  margin: 20px 0;
}

.fixed-track-title {
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}

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

.upload-lyric-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  position: absolute;
  right: 20px;
  opacity: 0;
  transform: scale(0.95);
}

.fixed-track-title:hover .upload-lyric-btn {
  opacity: 1;
  transform: scale(1);
}

.upload-lyric-btn:hover {
  opacity: 0.9;
  transform: scale(1.05);
}

/* v0.8.1 P2：AI 识别整轨歌词按钮（与上传/编辑歌词对称放左侧，悬停显示；识别中保持可见显示进度） */
.ai-recognize-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  position: absolute;
  left: 20px;
  opacity: 0;
  transform: scale(0.95);
}

.fixed-track-title:hover .ai-recognize-btn {
  opacity: 1;
  transform: scale(1);
}

.ai-recognize-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: scale(1.05);
}

.ai-recognize-btn:disabled {
  cursor: not-allowed;
  opacity: 1; /* 识别中保持可见，用于展示实时进度百分比 */
}

/* v0.8.1 P2：AI 识别进度条（歌词展示页标题下方，识别进行中显示） */
.ai-recognize-progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 4px;
}
.ai-recognize-progress-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: #eee;
  overflow: hidden;
}
.ai-recognize-progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.ai-recognize-progress-text {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
}

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

.track-dropdown-item.active {
  background-color: rgba(0, 0, 0, 0.2);
  color: v-bind(mainColorDark) !important;
  font-weight: 600;
}

.track-number {
  width: 20px;
  text-align: center;
  font-size: 14px;
  color: #999;
}

.track-name {
  flex: 1;
  margin: 0 10px;
  font-size: 14px;
}

.track-duration {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
}

.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  scroll-behavior: auto;
  position: relative;
}

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

.combined-lyric-section {
  width: 100%;
  margin-bottom: 30px;
}

.lyric-pair {
  margin: 8px 0;
  border-radius: 4px;
  cursor: pointer;
  width: 100%;
  max-width: 800px;
  box-sizing: border-box;
}

.lyric-pair.highlighted {
  padding: 4px;
  border-radius: 8px;
}

.lyric-pair.highlighted .original-lyric-item,
.lyric-pair.highlighted .cn-lyric-item {
  color: v-bind(mainColorDarkDouble);
}

.original-lyric-item {
  padding: 8px 15px;
  margin: 2px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  color: #888888;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: opacity, font-size, font-weight, color;
}

.cn-lyric-item {
  padding: 4px 15px 8px;
  margin: 2px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  color: #888888;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: opacity, font-size, font-weight, color;
}

.lyric-time {
  color: v-bind(mainColorDarkDouble);
  font-size: 12px;
  position: absolute;
  right: 20px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.original-lyric-item:hover .lyric-time {
  opacity: 1;
}

.lyric-text {
  text-align: center;
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

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

.translate-lang-select-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 8px;
}

.lyric-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
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

.original-lyric-item, .cn-lyric-item {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: opacity, font-size, font-weight, color;
}

.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  scroll-behavior: auto;
  position: relative;
  transform: translateZ(0);
}

.lyric-pair {
  transition: all 0.2s ease;
}

.lyric-pair.highlighted {
  padding: 4px;
  border-radius: 8px;
  transform: scale(1.02);
  transition: all 0.3s ease;
}
</style>