<template>
  <div class="playlist-root-container">
    <div class="playlist-sidebar" v-show="visible">
      <!-- 顶部横向歌单列表 - 可滚动+加号新建+叉号删除+默认选中+拖拽排序 -->
      <div class="playlist-tab-container">
        <div
          class="tab-scroll-box"
          @dragover.prevent="handleTabDragover"
          @dragenter.prevent
        >
          <div
            class="playlist-tab-item"
            v-for="(item, idx) in localPlaylistTabs"
            :key="`playlist-tab-${idx}-${item.name}`"
            :class="{
              active: localActiveTabIndex === idx,
              dragging: tabDragStartIndex === idx,
              tabPlaceholder: tabDragPlaceholderIndex === idx
            }"
            @click="handleTabChange(idx)"
            draggable="true"
            @dragstart="(e) => idx > 0 && handleTabDragStart(idx, e)"
            @dragover.prevent="(e) => handleTabDragOver(idx, e)"
            @dragenter.prevent="(e) => handleTabDragEnter(idx, e)"
            @dragleave="handleTabDragLeave(idx)"
            @dragend="handleTabDragEnd"
            @drop.prevent="(e) => handleTabDrop(idx, e)"
          >
            <span class="tab-name">{{ item.name }}</span>
            <span class="tab-close-icon" @click.stop="delPlaylistTab(idx)" v-if="idx > 0">×</span>
          </div>
          <div class="playlist-tab-add" @click="addPlaylistTab">+</div>
        </div>
      </div>

      <!-- 原有代码保持不变 -->
      <div class="playlist-section">
        <div class="playlist-top-bar common-tool-bar">
          <div class="playlist-right-group">
            <div class="play-mode-single-icon" :title="playModeTipText">
              <i
                class="mode-icon"
                @click="togglePlayMode"
                :style="activeTextColor"
              >{{playModeIcon}}</i>
            </div>
            <button
              class="oper-btn remove-all-btn common-oper-btn"
              @click="handleRemoveAllTracks"
              :style="primaryBgColor"
              :disabled="currentPlaylist.length === 0"
            >
              清空当前歌单
            </button>
          </div>
        </div>

        <div
          class="playlist-list common-scroll-list"
          ref="playlistScrollContainer"
          v-if="currentPlaylist.length > 0"
          @drop.prevent="handleDropAlbum"
          @dragover.prevent="handlePlaylistDragover"
          @dragenter.prevent

          @wheel="handleDragWheel"
        >
          <div
            class="playlist-item album-play-item common-album-card"
            :class="{active: currentTrackIndex === idx, dragging: dragStartIndex === idx, placeholder: dragPlaceholderIndex === idx}"
            v-for="(album, idx) in currentPlaylist"
            :key="`playlist-item-${album.sortId || idx}`"
            draggable="true"
            @dragstart="handleDragStart(idx, $event)"
            @dragover.prevent="handleDragOver(idx)"
            @dragenter.prevent
            @dragleave="handleDragLeave(idx)"
            @dragend="handleDragEnd($event)"
            @drop.prevent="handleDrop(idx)"
            @click="handleJumpAlbumDetail(idx)"
          >
            <div class="track-info album-info full-single-line">
              <span class="track-num" @click.stop="handlePlayTrack(idx)">{{ idx + 1 }}</span>
              <span class="track-name">{{ album.album_name }}</span>
              <span class="track-album"> {{ album.singer }} | 评分:{{ album.my_score || 0.0 }}</span>
            </div>
            <span class="track-del" @click.stop="delTrack(idx)">×</span>
          </div>
        </div>
        <div class="empty-playlist" v-else>
          暂无专辑，从下方拖拽/点击添加整张专辑吧～
        </div>
      </div>

      <div class="album-section common-fixed-section">
        <input
          type="text"
          class="album-search-input common-search-input"
          v-model="albumSearchKey"
          placeholder="搜索专辑名称/歌手..."
          @input="filterAndSortAlbums"
        />
        <div class="album-tool-bar common-tool-bar">
          <div class="sort-group common-sort-group">
            <button
              class="sort-btn common-sort-btn"
              :class="{active: sortType === 'addTime'}"
              @click="handleChangeSort('addTime')"
            >
              添加时间
            </button>
            <button
              class="sort-btn common-sort-btn"
              :class="{active: sortType === 'name'}"
              @click="handleChangeSort('name')"
            >
              名称排序
            </button>
            <button
              class="sort-btn common-sort-btn"
              :class="{active: sortType === 'score'}"
              @click="handleChangeSort('score')"
            >
              评分排序
            </button>
          </div>
          <button
            class="oper-btn add-all-btn common-oper-btn"
            @click="handleAddAllAlbumTracks"
            :style="primaryBgColor"
            :disabled="filterAlbums.length === 0"
          >
            添加全部专辑
          </button>
        </div>

        <div class="album-list common-scroll-list">
          <div
            class="album-item common-album-card"
            v-for="album in filterAlbums"
            :key="`album-item-${album.source_pool_id}`"
            @click="handleAddThisAlbumTracks(album)"
            draggable="true"
            @dragstart="handleDragAlbumStart(album, $event)"
            @dragend="handleDragAlbumEnd"
          >
            <div class="album-info no-cover full-single-line">
              <span class="album-name" @click.stop="handleJumpAlbumDetailByItem(album)">{{ album.album_name }}</span>
              <span class="album-singer"> {{ album.singer }} | 评分:{{ album.my_score || 0.0 }}</span>
            </div>
            <span class="add-icon">+</span>
          </div>
        </div>
      </div>
    </div>
    <div class="playlist-mask" v-show="visible" @click="handleClose"></div>
  </div>
</template>

<script>
export default {
  name: 'PlayerPlaylist',
  props: {
    visible: {type: Boolean, required: true, default: false},
    mainColorDark: {type: String, required: true},
    mainColorDarkDouble: {type: String, required: true},
    activeMenuBg: {type: String, required: true},
    currentUserId: {type: String, required: true},
    currentTrackIndex: {type: Number, required: true, default: -1},
    playMode: {type: String, required: true, default: 'order'},
    albumList: {type: Array, required: true, default: () => []},
    playlistTabs: {type: Array, required: true, default: () => [{name: '默认歌单', tracks: []}]},
    activeTabIndex: {type: Number, required: true, default: 0},
    currentAlbumId: {type: Number, required: true, default: 0},
    currentPlaylistId: {type: Number, required: true, default: 0}
  },
  data() {
    return {
      albumSearchKey: '',
      sortType: 'addTime',
      dragStartIndex: -1,
      dragPlaceholderIndex: -1,
      dragAlbumData: null,
      filterAlbums: [],
      sortIdSeed: Date.now(),
      localPlaylistTabs: [],
      localActiveTabIndex: 0,
      isDragging: false,
      dragTimer: null,
      playModeMap: {order: '顺序播放', single: '单曲循环', random: '随机播放'},
      isDraggingAction: false,
      isMounted: false,
      backupKey: 'user_playlist_backup_',
      isBackingUp: false,
      isRestoring: false,
      isEmiting: false,
      lastBackupTime: 0,
      backupDebounce: 1000,
      dragScrollTimer: null,
      scrollSpeed: 3,
      scrollThreshold: 50,
      // 新增：歌单标签拖拽相关状态
      tabDragStartIndex: -1,      // 歌单拖拽起始索引
      tabDragPlaceholderIndex: -1, // 歌单拖拽占位符索引
      isTabDragging: false        // 是否正在拖拽歌单
    };
  },
  computed: {
    primaryBgColor() {
      return {backgroundColor: this.mainColorDark};
    },
    activeTextColor() {
      return {color: this.mainColorDark, fontSize: '20px'};
    },
    currentPlaylist() {
      return (this.localPlaylistTabs[this.localActiveTabIndex]?.tracks || []);
    },
    playModeIcon() {
      switch (this.playMode) {
        case 'order':
          return '▶️';
        case 'single':
          return '🔂';
        case 'random':
          return '🔀';
        default:
          return '▶️';
      }
    },
    playModeText() {
      switch (this.playMode) {
        case 'order':
          return '顺序播放';
        case 'single':
          return '单曲循环';
        case 'random':
          return '随机播放';
        default:
          return '顺序播放';
      }
    },
    playModeTipText() {
      return `点击切换播放模式：${this.playModeText}`
    },
    currentPlayingAlbum() {
      if (this.currentTrackIndex > -1 && this.currentPlaylist.length) {
        return this.currentPlaylist[this.currentTrackIndex];
      }
      return null;
    }
  },
  watch: {
    visible(val) {
      if (val && this.isMounted) {
        this.filterAlbums = [...this.albumList];
      }
    },
    albumList(newVal) {
      if (this.isMounted) {
        this.filterAlbums = [...newVal];
        this.filterAndSortAlbums();
      }
    },
    sortType() {
      if (this.isMounted) this.filterAndSortAlbums();
    },
    albumSearchKey() {
      if (this.isMounted) this.filterAndSortAlbums();
    },
    playlistTabs: {
      deep: true,
      immediate: true,
      handler(newVal) {
        if (this.isMounted && !this.isEmiting && !this.isBackingUp && !this.isRestoring) {
          if (Array.isArray(newVal) && newVal.length > 0) {
            const newValStr = JSON.stringify(newVal);
            const localValStr = JSON.stringify(this.localPlaylistTabs);
            if (newValStr !== localValStr) {
              this.localPlaylistTabs = JSON.parse(JSON.stringify(newVal));
              this.safeBackupPlaylistData();
            }
          }
        }
      }
    },
    activeTabIndex: {
      immediate: true,
      handler(newVal) {
        if (this.isMounted) {
          this.localActiveTabIndex = newVal;
        }
      }
    },
    localPlaylistTabs: {
      deep: true,
      handler(newVal) {
        if (this.isMounted && !this.isDragging && !this.isDraggingAction && !this.isRestoring && !this.isBackingUp && !this.isEmiting && !this.isTabDragging) {
          clearTimeout(this.dragTimer);
          this.dragTimer = setTimeout(() => {
            if (Array.isArray(newVal) && newVal.length > 0) {
              this.isEmiting = true;
              this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(newVal)));
              setTimeout(() => {
                this.isEmiting = false;
                this.safeBackupPlaylistData();
              }, 50);
            }
          }, 30);
        }
      }
    },
    localActiveTabIndex(newVal) {
      if (this.isMounted) {
        this.$emit('update:activeTabIndex', newVal);
      }
    }
  },
  mounted() {
    this.isMounted = true;
    this.isRestoring = true;
    this.restorePlaylistData();
    this.isRestoring = false;

    if (this.localPlaylistTabs.length === 0) {
      this.localPlaylistTabs = JSON.parse(JSON.stringify(this.playlistTabs));
    }
    this.filterAlbums = [...this.albumList];
    this.localActiveTabIndex = this.activeTabIndex;
  },
  beforeDestroy() {
    clearTimeout(this.dragTimer);
    clearTimeout(this.dragScrollTimer);
    this.isBackingUp = true;
    this.backupPlaylistData();
    this.isBackingUp = false;

    this.handlePauseAndUploadDuration();
    this.isMounted = false;
  },
  methods: {
    // 原有方法保持不变
    safeBackupPlaylistData() {
      const now = Date.now();
      if (now - this.lastBackupTime < this.backupDebounce) {
        return;
      }
      this.lastBackupTime = now;
      this.backupPlaylistData();
    },
    backupPlaylistData() {
      if (this.isRestoring || this.isBackingUp || this.isEmiting) return;

      try {
        this.isBackingUp = true;

        if (this.currentUserId && Array.isArray(this.localPlaylistTabs) && this.localPlaylistTabs.length > 0) {
          const backupData = {
            tabs: JSON.parse(JSON.stringify(this.localPlaylistTabs)),
            activeIndex: this.localActiveTabIndex,
            timestamp: Date.now()
          };
          localStorage.setItem(`${this.backupKey}${this.currentUserId}`, JSON.stringify(backupData));
          console.log('✅ 歌单数据已备份到本地存储');
        }
      } catch (err) {
        console.warn('⚠️ 歌单数据备份失败：', err);
      } finally {
        setTimeout(() => {
          this.isBackingUp = false;
        }, 100);
      }
    },
    restorePlaylistData() {
      if (this.isBackingUp || this.isEmiting) return;

      try {
        if (this.currentUserId) {
          const backupStr = localStorage.getItem(`${this.backupKey}${this.currentUserId}`);
          if (backupStr) {
            const backupData = JSON.parse(backupStr);
            if (backupData.tabs && Date.now() - backupData.timestamp < 7 * 24 * 60 * 60 * 1000) {
              this.localPlaylistTabs = JSON.parse(JSON.stringify(backupData.tabs));
              this.localActiveTabIndex = backupData.activeIndex || 0;
              console.log('✅ 从本地备份恢复歌单数据成功');
            }
          }
        }
      } catch (err) {
        console.warn('⚠️ 歌单数据恢复失败：使用默认数据');
      }
    },
    handlePauseAndUploadDuration() {
      try {
        if (this.$parent?.handlePauseAndUploadDuration) {
          this.$parent.handlePauseAndUploadDuration();
        }
      } catch (err) {
        console.error('暂停/上传时长/保存评分 失败：', err);
      }
    },
    triggerGetAlbumScore() {
      try {
        if (this.$parent?.$refs?.albumTrackListRef) {
          this.$parent.$refs.albumTrackListRef.triggerGetScore();
          console.log('✅ 父组件触发：读取专辑评分成功');
        }
      } catch (err) {
        console.error('读取专辑评分失败：', err);
      }
    },
    addPlaylistTab() {
      const tabName = prompt('请输入歌单名称：', '我的新歌单');
      if (tabName && tabName.trim()) {
        this.localPlaylistTabs.push({name: tabName.trim(), tracks: []});
        this.localActiveTabIndex = this.localPlaylistTabs.length - 1;
        this.safeBackupPlaylistData();
      }
    },
    delPlaylistTab(idx) {
      if (idx === 0) return this.$message?.warning('默认歌单不能删除！');
      if (confirm('确定删除这个歌单吗？')) {
        this.handlePauseAndUploadDuration();
        this.localPlaylistTabs.splice(idx, 1);
        this.localActiveTabIndex = Math.max(0, this.localActiveTabIndex - 1);
        this.safeBackupPlaylistData();
      }
    },
    handleTabChange(idx) {
      if (this.localActiveTabIndex === idx) return;
      this.handlePauseAndUploadDuration();
      this.localActiveTabIndex = idx;
      this.safeBackupPlaylistData();
    },
    handleDragStart(idx, event) {
      this.dragStartIndex = idx;
      this.dragPlaceholderIndex = -1;
      this.isDragging = true;
      this.isDraggingAction = true;

      if (event && event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', idx.toString());
        event.dataTransfer.setDragImage(event.target.cloneNode(true), 10, 10);
      }

      setTimeout(() => {
        this.isDraggingAction = false;
      }, 300);
    },
    handlePlaylistDragover(event) {
      if (!this.isDragging) return;

      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';

      const container = this.$refs.playlistScrollContainer;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const y = event.clientY;

      clearInterval(this.dragScrollTimer);

      if (y - rect.top < this.scrollThreshold) {
        this.dragScrollTimer = setInterval(() => {
          container.scrollTop -= this.scrollSpeed;
        }, 10);
      } else if (rect.bottom - y < this.scrollThreshold) {
        this.dragScrollTimer = setInterval(() => {
          container.scrollTop += this.scrollSpeed;
        }, 10);
      } else {
        clearInterval(this.dragScrollTimer);
      }
    },
    handleDragWheel(event) {
      if (this.isDragging) {
        event.preventDefault();
        const container = this.$refs.playlistScrollContainer;
        if (container) {
          container.scrollTop += event.deltaY;
        }
      }
    },
    handleDragOver(idx) {
      if (this.dragStartIndex === -1 || this.dragStartIndex === idx) return;

      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';

      this.dragPlaceholderIndex = idx;
    },
    handleDragLeave(idx) {
      if (this.dragPlaceholderIndex === idx) {
        this.dragPlaceholderIndex = -1;
      }
    },
    handleDrop(dropIndex) {
      if (this.dragStartIndex === -1 || this.dragStartIndex === dropIndex) return;

      const currTracks = [...this.currentPlaylist];
      const [dragItem] = currTracks.splice(this.dragStartIndex, 1);
      currTracks.splice(dropIndex, 0, dragItem);

      this.localPlaylistTabs[this.localActiveTabIndex].tracks = currTracks;
      this.$message?.success('歌单排序已更新');
      this.resetDragStatus();
    },
    handleDragEnd() {
      clearInterval(this.dragScrollTimer);
      this.resetDragStatus();
    },
    resetDragStatus() {
      this.isDragging = false;
      this.dragStartIndex = -1;
      this.dragPlaceholderIndex = -1;

      setTimeout(() => {
        this.isDraggingAction = false;
        this.safeBackupPlaylistData();
      }, 100);
    },
    handleDragAlbumStart(album, event) {
      this.dragAlbumData = album;
      if (event && event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'copy';
        event.dataTransfer.setData('application/json', JSON.stringify(album));
      }
    },
    handleDragAlbumEnd() {
      this.dragAlbumData = null;
    },
    handleDropAlbum(event) {
      event.preventDefault();
      if (!this.dragAlbumData) return;

      this.handleAddThisAlbumTracks(this.dragAlbumData);
      this.$message?.success(`已添加《${this.dragAlbumData.album_name}》到歌单`);
      this.dragAlbumData = null;
    },
    togglePlayMode() {
      let newMode = 'order';
      if (this.playMode === 'order') newMode = 'single';
      else if (this.playMode === 'single') newMode = 'random';
      else if (this.playMode === 'random') newMode = 'order';
      this.$emit('update:playMode', newMode);
      const newModeText = this.playModeMap[newMode];
      this.$message?.success(`✅ 已切换为：${newModeText}`);
    },
    filterAndSortAlbums() {
      if (!this.albumList || !this.isMounted) return;
      let filterList = [...this.albumList];
      const searchKey = this.albumSearchKey.trim().toLowerCase();
      if (searchKey) {
        filterList = filterList.filter(item => {
          const albumName = (item.album_name || '').toLowerCase();
          const singer = (item.singer || '').toLowerCase();
          return albumName.includes(searchKey) || singer.includes(searchKey);
        });
      }
      switch (this.sortType) {
        case 'addTime':
          filterList.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
          break;
        case 'name':
          filterList.sort((a, b) => (a.album_name || '').localeCompare(b.album_name || '', 'zh-CN'));
          break;
        case 'score':
          filterList.sort((a, b) => (b.my_score || 0) - (a.my_score || 0));
          break;
      }
      this.filterAlbums = filterList;
    },
    handlePlayTrack(index) {
      this.$emit('play-track', index);
    },
    delTrack(index) {
      this.localPlaylistTabs[this.localActiveTabIndex].tracks.splice(index, 1);
      if (index === this.currentTrackIndex) this.$emit('update:currentTrackIndex', -1);
      this.safeBackupPlaylistData();
    },
    handleRemoveAllTracks() {
      this.handlePauseAndUploadDuration();
      this.localPlaylistTabs[this.localActiveTabIndex].tracks = [];
      this.$emit('update:currentTrackIndex', -1);
      this.$message?.success('已清空当前歌单');
      this.safeBackupPlaylistData();
    },
    handleAddThisAlbumTracks(album) {
      if (!album) return;
      this.localPlaylistTabs[this.localActiveTabIndex].tracks.push({
        ...album,
        sortId: this.sortIdSeed++
      });
      this.safeBackupPlaylistData();
    },
    handleAddAllAlbumTracks() {
      let addCount = 0;
      this.filterAlbums.forEach(album => {
        if (album) {
          this.localPlaylistTabs[this.localActiveTabIndex].tracks.push({
            ...album,
            sortId: this.sortIdSeed++
          });
          addCount++;
        }
      });
      this.$message?.success(`已添加 ${addCount} 张专辑到当前歌单`);
      this.safeBackupPlaylistData();
    },
    handleChangeSort(type) {
      this.sortType = type;
    },
    handleClose() {
      this.handlePauseAndUploadDuration();
      this.$emit('close-sidebar');
      this.safeBackupPlaylistData();

      if (this.saveUserPlaylistData) {
        this.saveUserPlaylistData();
      }
    },
    handleJumpAlbumDetail(idx) {
      if (this.isDraggingAction) return;
      const albumItem = this.currentPlaylist[idx];
      console.log('👉 点击专辑块，准备查询专辑ID并跳转', albumItem);
      if (!albumItem || !albumItem.source_pool_id) {
        this.$message?.warning('该专辑信息异常，无关联ID');
        return;
      }
      const sourcePoolId = Number(albumItem.source_pool_id);
      if (sourcePoolId < 1) {
        this.$message?.warning('无效的专辑关联ID');
        return;
      }

      try {
        this.$axios.get('/api/album/get-id-by-source', {
          params: {source_pool_id: sourcePoolId}
        }).then(res => {
          if (res.data.code === 200 && res.data.data?.album_id) {
            const realAlbumId = res.data.data.album_id;
            console.log('✅ 精准匹配成功：source_pool_id=', sourcePoolId, ' → album_id=', realAlbumId);

            this.handlePauseAndUploadDuration();

            this.$router.push({
              path: `/album/detail/${realAlbumId}`,
              query: {id: realAlbumId}
            });
            this.handleClose();
            this.$emit('update:currentTrackIndex', -1);
          } else if (res.data.code === 404) {
            this.$message?.info(res.data.msg);
          } else {
            this.$message?.error(res.data.msg || '查询专辑信息失败');
          }
        }).catch(err => {
          console.error('❌ 查询专辑ID失败：', err);
          this.$message?.error('跳转失败，请稍后重试');
        });
      } catch (err) {
        console.error('❌ 查询专辑ID失败：', err);
        this.$message?.error('跳转失败，请稍后重试');
      }
    },
    handleJumpAlbumDetailByItem(album) {
      console.log('👉 点击可添加专辑名，准备查询专辑ID并跳转', album);
      if (!album || !album.source_pool_id) {
        this.$message?.warning('该专辑信息异常，无关联ID');
        return;
      }
      const sourcePoolId = Number(album.source_pool_id);
      if (sourcePoolId < 1) {
        this.$message?.warning('无效的专辑关联ID');
        return;
      }
      try {
        this.$axios.get('/api/album/get-id-by-source', {
          params: {source_pool_id: sourcePoolId}
        }).then(res => {
          if (res.data.code === 200 && res.data.data?.album_id) {
            this.handlePauseAndUploadDuration();
            this.$router.push({
              path: `/album/detail/${res.data.data.album_id}`,
              query: {id: res.data.data.album_id}
            });
            this.handleClose();
          } else if (res.data.code === 404) {
            this.$message?.info(res.data.msg);
          } else {
            this.$message?.error(res.data.msg || '查询专辑信息失败');
          }
        }).catch(err => {
          console.error('❌ 查询专辑ID失败：', err);
          this.$message?.error('跳转失败，请稍后重试');
        });
      } catch (err) {
        console.error('❌ 查询专辑ID失败：', err);
        this.$message?.error('跳转失败，请稍后重试');
      }
    },

    // ========== 新增：歌单标签拖拽相关方法 ==========
    /**
     * 歌单标签拖拽开始
     * @param {number} idx - 歌单索引
     * @param {Event} e - 拖拽事件
     */
    handleTabDragStart(idx, e) {
      this.tabDragStartIndex = idx;
      this.tabDragPlaceholderIndex = -1;
      this.isTabDragging = true;

      // 设置拖拽数据
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', idx.toString());
      e.dataTransfer.setDragImage(e.target.cloneNode(true), 50, 20);
    },

    /**
     * 歌单标签容器dragover处理
     * @param {Event} e - 拖拽事件
     */
    handleTabDragover(e) {
      if (!this.isTabDragging) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    },

    /**
     * 歌单标签dragover处理
     * @param {number} idx - 目标歌单索引
     * @param {Event} e - 拖拽事件
     */
    handleTabDragOver(idx, e) {
      // 跳过默认歌单和起始歌单
      if (idx === 0 || idx === this.tabDragStartIndex) return;

      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    },

    /**
     * 歌单标签dragenter处理
     * @param {number} idx - 目标歌单索引
     * @param {Event} e - 拖拽事件
     */
    handleTabDragEnter(idx, e) {
      // 跳过默认歌单和起始歌单
      if (idx === 0 || idx === this.tabDragStartIndex) return;

      e.preventDefault();
      this.tabDragPlaceholderIndex = idx;
    },

    /**
     * 歌单标签dragleave处理
     * @param {number} idx - 目标歌单索引
     */
    handleTabDragLeave(idx) {
      if (this.tabDragPlaceholderIndex === idx) {
        this.tabDragPlaceholderIndex = -1;
      }
    },

    /**
     * 歌单标签拖拽结束
     */
    handleTabDragEnd() {
      // 重置拖拽状态
      this.isTabDragging = false;
      this.tabDragStartIndex = -1;
      this.tabDragPlaceholderIndex = -1;
    },

    /**
     * 歌单标签drop处理（完成排序）
     * @param {number} dropIndex - 放下位置索引
     * @param {Event} e - 拖拽事件
     */
    handleTabDrop(dropIndex, e) {
      e.preventDefault();

      // 验证条件
      if (
          !this.isTabDragging ||
          dropIndex === 0 ||
          this.tabDragStartIndex === -1 ||
          this.tabDragStartIndex === dropIndex
      ) {
        this.handleTabDragEnd();
        return;
      }

      // 复制歌单数组并调整顺序
      const newTabs = [...this.localPlaylistTabs];
      // 移除拖拽项
      const [draggedTab] = newTabs.splice(this.tabDragStartIndex, 1);
      // 插入到目标位置
      newTabs.splice(dropIndex, 0, draggedTab);

      // 更新歌单列表
      this.localPlaylistTabs = newTabs;

      // 如果拖拽的是当前激活的歌单，更新激活索引
      if (this.localActiveTabIndex === this.tabDragStartIndex) {
        this.localActiveTabIndex = dropIndex;
      }
      // 如果目标位置是当前激活的歌单，调整激活索引
      else if (this.localActiveTabIndex === dropIndex) {
        this.localActiveTabIndex = this.tabDragStartIndex;
      }

      // 保存数据
      this.safeBackupPlaylistData();
      this.$message?.success('歌单顺序已更新');

      // 重置拖拽状态
      this.handleTabDragEnd();
    }
  }
};
</script>

<style scoped>
/* 原有样式保持不变 */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.playlist-root-container {
  position: relative;
  z-index: 9999;
}

.playlist-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 380px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border-left: 1px solid rgba(255, 255, 255, 0.5);
  z-index: 9999;
  padding: 15px;
  color: #333;
  font-family: "Microsoft YaHei", "SimHei", sans-serif;
  display: flex;
  flex-direction: column;
  gap: 15px;
  transform: translateZ(0);
  will-change: transform;
}

.playlist-tab-container {
  width: 100%;
  padding-bottom: 10px;
  border-bottom: 2px solid v-bind(mainColorDark);
}

.tab-scroll-box {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  overflow-x: auto;
  white-space: nowrap;
  padding-bottom: 5px;
}

.playlist-tab-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  border: 1px solid transparent;
  flex-shrink: 0;
}

.playlist-tab-item.active {
  background: v-bind(activeMenuBg);
  border-color: v-bind(mainColorDark);
  color: v-bind(mainColorDarkDouble);
  font-weight: 600;
}

.playlist-tab-item:hover:not(.active) {
  background: rgba(255, 255, 255, 0.5);
}

/* 新增：歌单拖拽相关样式 */
.playlist-tab-item.dragging {
  opacity: 0.5;
  background: rgba(255, 255, 255, 0.2);
  cursor: grabbing;
}

.playlist-tab-item.tab-placeholder {
  background: rgba(255, 255, 255, 0.4);
  border: 1px dashed v-bind(mainColorDark);
}

/* 禁用默认歌单的拖拽光标 */
.playlist-tab-item:nth-child(1) {
  cursor: default !important;
}

.tab-close-icon {
  font-size: 12px;
  color: #999;
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-close-icon:hover {
  color: #dc2626;
}

.playlist-tab-add {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: v-bind(mainColorDark);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.playlist-tab-add:hover {
  background: v-bind(activeMenuBg);
  transform: scale(1.05);
}

.common-tool-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 8px;
}

.common-sort-group {
  display: flex;
  gap: 5px;
}

.common-sort-btn {
  background: transparent;
  border: none;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.common-sort-btn.active {
  font-weight: 600;
  background: v-bind(activeMenuBg);
  color: v-bind(mainColorDarkDouble);
}

.common-oper-btn {
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.common-oper-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.common-oper-btn:hover:not(:disabled) {
  background-color: v-bind(mainColorDarkDouble) !important;
  opacity: 0.95;
}

.common-album-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  transition: all 0.1s;
  font-size: 13px;
  width: 100%;
  margin-bottom: 6px;
  transform: translateZ(0);
  user-select: none;
  height: 50px;
  flex-shrink: 0;
}

.common-album-card:hover {
  background: rgba(255, 255, 255, 0.5);
}

.full-single-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.track-num {
  display: inline-block;
  width: 20px;
  text-align: center;
  color: v-bind(mainColorDarkDouble);
  font-weight: 500;
  flex-shrink: 0;
  cursor: pointer;
}

.track-num:hover {
  color: #dc2626;
}

.track-name {
  font-size: 14px;
  font-weight: 600;
  color: v-bind(mainColorDarkDouble);
  cursor: pointer;
}

.track-name:hover {
  text-decoration: underline;
}

.track-album {
  font-size: 11px;
  color: #666;
}

.album-name {
  font-size: 14px;
  font-weight: 600;
  color: v-bind(mainColorDarkDouble);
  cursor: pointer;
}

.album-name:hover {
  text-decoration: underline;
}

.album-singer {
  font-size: 11px;
  color: #666;
}

.playlist-section {
  width: 100%;
  flex-shrink: 0;
}

.playlist-right-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.play-mode-single-icon {
  cursor: pointer;
}

.mode-icon {
  cursor: pointer;
  transition: all 0.2s;
}

.mode-icon:hover {
  transform: scale(1.15);
  filter: brightness(1.2);
}

.album-play-item.active {
  background: v-bind(activeMenuBg);
  border-left: 3px solid v-bind(mainColorDark);
}

.album-play-item {
  cursor: pointer;
}

.album-play-item.dragging {
  opacity: 0.4;
  background: rgba(255, 255, 255, 0.1);
  cursor: move;
}

.album-play-item.placeholder {
  background: v-bind(activeMenuBg);
  opacity: 0.8;
  border: 1px dashed v-bind(mainColorDark);
  height: 50px;
  flex-shrink: 0;
}

.track-del {
  color: #999;
  font-size: 18px;
  cursor: pointer;
  padding: 0 6px;
  transition: all 0.1s;
  flex-shrink: 0;
}

.track-del:hover {
  color: #dc2626;
  transform: scale(1.1);
}

.empty-playlist {
  text-align: center;
  padding: 20px 0;
  color: #666;
  font-size: 14px;
}

.common-fixed-section {
  width: 100%;
  flex-shrink: 0;
  position: relative;
}

.common-search-input {
  width: 100%;
  padding: 8px 10px;
  border-radius: 4px;
  border: none;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(3px);
  color: v-bind(mainColorDarkDouble);
  font-size: 13px;
  margin-bottom: 8px;
}

.common-search-input::placeholder {
  color: #999;
}

.add-icon {
  color: v-bind(mainColorDark);
  font-size: 18px;
  font-weight: 600;
  opacity: 0.7;
  transition: all 0.1s;
  flex-shrink: 0;
}

.add-icon:hover {
  opacity: 1;
  transform: scale(1.1);
}

.playlist-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(2px);
  z-index: 9998;
}

.common-scroll-list {
  width: 100%;
  overflow-y: auto;
  max-height: 260px;
  min-height: 100px;
  cursor: default;
}

.album-list {
  width: 100%;
  overflow-y: auto;
}

/* 滚动条样式 */
.tab-scroll-box::-webkit-scrollbar,
.common-scroll-list::-webkit-scrollbar,
.album-list::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.tab-scroll-box::-webkit-scrollbar-thumb,
.common-scroll-list::-webkit-scrollbar-thumb,
.album-list::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDarkDouble);
  border-radius: 3px;
}

.tab-scroll-box::-webkit-scrollbar-thumb:hover,
.common-scroll-list::-webkit-scrollbar-thumb:hover,
.album-list::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDark);
}

.tab-scroll-box::-webkit-scrollbar-track,
.common-scroll-list::-webkit-scrollbar-track,
.album-list::-webkit-scrollbar-track {
  background: transparent !important;
}

.tab-scroll-box::-webkit-scrollbar-button,
.common-scroll-list::-webkit-scrollbar-button,
.album-list::-webkit-scrollbar-button {
  display: none !important;
}

/* 拖拽相关样式优化 */
[draggable="true"] {
  cursor: grab;
}

[draggable="true"]:active {
  cursor: grabbing;
}
</style>