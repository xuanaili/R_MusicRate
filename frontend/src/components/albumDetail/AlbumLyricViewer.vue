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
                      <i class="icon-fetch">📝</i> 从QQ音乐获取歌词
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
              <h3>从QQ音乐获取歌词 - {{ trackList[selectedTrackIndex]?.name || '当前单曲' }}</h3>
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
                        disabled
                    />
                  </div>
                  <div class="info-field" style="display: none;">
                    <span class="field-name">网易云链接：</span>
                    <input
                        v-model="fetchNeteaseUrl"
                        class="info-input"
                        placeholder="例如：https://music.163.com/#/song?id=3315852235"
                        disabled
                    />
                  </div>
                </div>
              </div>

              <button
                  class="fetch-lyric-btn"
                  :style="{backgroundColor: mainColorDark}"
                  @click="fetchLyrics"
                  :disabled="fetchLoading || (!fetchSongName.trim())"
              >
                <span v-if="fetchLoading">获取中...</span>
                <span v-else>从QQ音乐获取歌词</span>
              </button>

              <div v-if="fetchResult" class="lyric-result-group">
                <label class="lyric-result-label">QQ音乐歌词</label>
                <div class="lyric-source-tabs">
                  <button
                      class="source-tab active"
                  >
                    QQ音乐
                    <span v-if="fetchResult.qq?.status === 'success'" class="success-tag">✓</span>
                    <span v-if="fetchResult.qq?.status === 'failed'" class="failed-tag">✗</span>
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
        {key: 'qq', name: 'QQ音乐'}
      ],
      selectedSource: 'qq',
      selectedLyricContent: '',
      scrollAnimationTimer: null,
      batchFetchLoading: false,
      batchFetchCurrent: 0,
      batchFetchTotal: 0,
      batchFetchTimer: null,
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
          this.$nextTick(() => {
            this.fillLyricToInput();
          });
        }
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
    if (this.batchFetchTimer) clearTimeout(this.batchFetchTimer);
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

    async fetchLyrics() {
      if (!this.fetchSongName.trim()) {
        this.$message?.warning('歌曲名不能为空！');
        return;
      }
      this.fetchLoading = true;
      this.fetchResult = null;
      this.selectedLyricContent = '';
      try {
        const res = await this.$axios.post('/api/lyric/fetch_auto', {
          song_name: this.fetchSongName.trim(),
          artist: this.fetchArtist.trim(),
          duration: this.fetchDuration
        }, {headers: {Authorization: localStorage.getItem('token') || ''}});

        if (res.data.code === 200) {
          this.fetchResult = res.data.data.lyrics;
          const hasLyric = res.data.data.summary.success_count > 0;

          if (hasLyric) {
            this.$message?.success('从QQ音乐获取歌词成功！');
            this.$nextTick(() => {
              this.fillLyricToInput();
            });
          } else {
            this.$message?.warning('QQ音乐未找到该歌曲的歌词');
          }
        }
      } catch (e) {
        this.$message?.error('获取失败：' + (e.response?.data?.msg || e.message));
      } finally {
        this.fetchLoading = false;
      }
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

    autoSelectFirstSuccessSource() {
      if (!this.fetchResult) return;
      const ok = this.lyricSources.find(s =>
        this.fetchResult[s.key]?.status === 'success' && this.fetchResult[s.key]?.lyric?.trim()
      );
      if (ok) {
        this.selectedSource = ok.key;
        this.selectedLyricContent = this.fetchResult[ok.key].lyric;
      }
    },

    fillLyricToInput() {
      if (!this.selectedLyricContent.trim()) {
        this.autoSelectFirstSuccessSource();
      }

      if (!this.selectedLyricContent.trim()) return;

      const std = this.parseLrcToStandardFormat(this.selectedLyricContent);
      if (!std) return;

      this.currentTrackLyricContent = std;
      this.$message?.success('已填入并格式化歌词');
    },

    closeAutoFetchModal() {
      this.showAutoFetchLyricModal = false;
      this.fetchResult = null;
      this.selectedLyricContent = '';
      this.selectedSource = 'qq';
      this.fetchNeteaseUrl = '';
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

    async startBatchFetchLyrics() {
      if (!this.trackList.length) return;
      if (!window.confirm('确定从QQ音乐批量获取所有歌词？')) return;

      this.batchFetchLoading = true;
      this.batchFetchCurrent = 0;
      this.batchFetchTotal = this.trackList.length;

      for (let i = 0; i < this.trackList.length; i++) {
        this.batchFetchCurrent = i + 1;
        await this.$nextTick();

        try {
          this.selectedTrackIndex = i;
          await this.$nextTick();

          const res = await this.$axios.post('/api/lyric/fetch_auto', {
            song_name: this.trackList[i].name.trim(),
            artist: this.album.singer || '',
            duration: 0
          }, {headers: {Authorization: localStorage.getItem('token') || ''}});

          if (res.data.code === 200 && res.data.data.summary.success_count > 0) {
            const qqLyric = res.data.data.lyrics.qq.lyric;
            const stdLyric = this.parseLrcToStandardFormat(qqLyric);
            this.trackLyricsMap[i] = {
              ...this.trackLyricsMap[i],
              lyric: stdLyric
            };

            if (i === this.selectedTrackIndex) {
              this.currentTrackLyricContent = stdLyric;
            }

            this.$message?.success(`成功获取《${this.trackList[i].name}》的歌词`);
          } else {
            this.$message?.warning(`未找到《${this.trackList[i].name}》的歌词`);
          }
        } catch (e) {
          console.error(`获取第${i+1}首歌歌词失败`, e);
          this.$message?.error(`获取《${this.trackList[i].name}》歌词失败`);
        }

        await this.sleep(1500);
      }

      this.batchFetchLoading = false;
      this.$message?.success(`批量获取完成！共处理 ${this.batchFetchTotal} 首歌曲`);
    }
  }
};
</script>
<style scoped>
/* 样式部分保持不变 */
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

.auto-fetch-modal-body {
  padding: 20px;
}

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

.success-tag {
  color: #4cd964;
  font-weight: bold;
}

.failed-tag {
  color: #ff3b30;
  font-weight: bold;
}

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