<template>
  <div class="playlist-root-container">
    <div class="playlist-sidebar" v-show="visible">
      <!-- 顶部横向歌单列表 - 可滚动+加号新建+叉号删除+默认选中 -->
      <div class="playlist-tab-container">
        <div class="tab-scroll-box">
          <div
            class="playlist-tab-item"
            v-for="(item, idx) in localPlaylistTabs"
            :key="idx"
            :class="{active: localActiveTabIndex === idx}"
            @click="localActiveTabIndex = idx"
          >
            <span class="tab-name">{{ item.name }}</span>
            <span class="tab-close-icon" @click.stop="delPlaylistTab(idx)" v-if="idx > 0">×</span>
          </div>
          <div class="playlist-tab-add" @click="addPlaylistTab">+</div>
        </div>
      </div>

      <!-- 上半部分：当前歌单-专辑列表【纯自定义拖拽排序+拖拽到外部删除 永久开启拖拽】 -->
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

        <!-- ✅ 核心优化：解决卡死+拖拽占位视觉反馈+性能拉满 -->
        <div
          class="playlist-list common-scroll-list"
          v-if="currentPlaylist.length > 0"
        >
          <div
            class="playlist-item album-play-item common-album-card"
            :class="{active: currentTrackIndex === idx, dragging: dragStartIndex === idx, placeholder: dragPlaceholderIndex === idx}"
            v-for="(album, idx) in currentPlaylist"
            :key="album.sortId"
            @click="handlePlayTrack(idx)"
            draggable="true"
            @dragstart="handleDragStart(idx)"
            @dragover.prevent="handleDragOver(idx)"
            @dragleave="handleDragLeave(idx)"
            @dragend="handleDragEnd(idx)"
            @drop.prevent="handleDrop(idx)"
          >
            <div class="track-info album-info full-single-line">
              <span class="track-num">{{ idx + 1 }}</span>
              <!-- ✅ 核心新增：专辑名点击跳转详情页，阻止冒泡避免触发播放 -->
              <span class="track-name" @click.stop="handleJumpAlbumDetail(idx)">{{ album.album_name }}</span>
              <span class="track-album"> {{ album.singer }} | 评分:{{ album.my_score || 0.0 }}</span>
            </div>
            <span class="track-del" @click.stop="handleDelTrack(idx)">×</span>
          </div>
        </div>
        <div class="empty-playlist" v-else>
          暂无专辑，从下方拖拽/点击添加整张专辑吧～
        </div>
      </div>

      <!-- 下半部分：固定位置 + 样式和上半部分完全统一 + 同尺寸卡片 + 搜索框固定 【无任何修改】-->
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
            :key="album.source_pool_id"
            @click="handleAddThisAlbumTracks(album)"
            draggable="true"
            @dragstart="handleDragAlbumStart(album)"
            @dragend="handleDragAlbumEnd"
          >
            <div class="album-info no-cover full-single-line">
              <!-- ✅ 核心新增：下方专辑名点击跳转详情页，阻止冒泡避免触发添加 -->
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
    visible: { type: Boolean, required: true, default: false },
    mainColorDark: { type: String, required: true },
    mainColorDarkDouble: { type: String, required: true },
    activeMenuBg: { type: String, required: true },
    currentUserId: { type: String, required: true },
    currentTrackIndex: { type: Number, required: true, default: -1 },
    playMode: { type: String, required: true, default: 'order' },
    albumList: { type: Array, required: true, default: ()=>[] },
    playlistTabs: { type: Array, required: true, default: ()=>[{ name: '默认歌单', tracks: [] }] },
    activeTabIndex: { type: Number, required: true, default: 0},
    currentAlbumId: {type: Number, required: true, default: 0},
    currentPlaylistId: {type: Number, required: true, default: 0}
  },
  data() {
    return {
      albumSearchKey: '',
      sortType: 'addTime',
      dragStartIndex: -1,
      dragPlaceholderIndex: -1, // ✅ 新增：拖拽占位索引，实现视觉反馈
      dragAlbumData: null,
      filterAlbums: [],
      sortIdSeed: Date.now(), // ✅ 优化：用时间戳做唯一ID，永不重复
      localPlaylistTabs: JSON.parse(JSON.stringify(this.playlistTabs)),
      localActiveTabIndex: this.activeTabIndex,
      isDragging: false,
      dragTimer: null // ✅ 新增：防抖定时器，杜绝高频触发
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
      return this.localPlaylistTabs[this.localActiveTabIndex].tracks || [];
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
    }
  },
  watch: {
    visible(val) {
      if (val) this.filterAlbums = [...this.albumList];
    },
    albumList(newVal) {
      this.filterAlbums = [...newVal];
      this.filterAndSortAlbums();
    },
    sortType() {
      this.filterAndSortAlbums();
    },
    albumSearchKey() {
      this.filterAndSortAlbums();
    },
    playlistTabs: {
      deep: true,
      immediate: true,
      handler(newVal) {
        if (!this.isDragging) {
          this.localPlaylistTabs = JSON.parse(JSON.stringify(newVal));
        }
      }
    },
    activeTabIndex: {
      immediate: true,
      handler(newVal) {
        this.localActiveTabIndex = newVal;
      }
    },
    // ✅ 优化：拖拽锁+防抖emit，彻底杜绝主线程阻塞
    localPlaylistTabs: {
      deep: true,
      handler(newVal) {
        if (!this.isDragging) {
          clearTimeout(this.dragTimer)
          this.dragTimer = setTimeout(() => {
            this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(newVal)));
          }, 30);
        }
      }
    },
    localActiveTabIndex(newVal) {
      this.$emit('update:activeTabIndex', newVal);
    }
  },
  mounted() {
    this.filterAlbums = [...this.albumList];
  },
  beforeDestroy() {
    clearTimeout(this.dragTimer) // ✅ 销毁定时器，防止内存泄漏
  },
  methods: {
    addPlaylistTab() {
      const tabName = prompt('请输入歌单名称：', '我的新歌单');
      if (tabName && tabName.trim()) {
        this.localPlaylistTabs.push({name: tabName.trim(), tracks: []});
        this.localActiveTabIndex = this.localPlaylistTabs.length - 1;
      }
    },
    delPlaylistTab(idx) {
      if (idx === 0) return this.$message?.warning('默认歌单不能删除！');
      if (confirm('确定删除这个歌单吗？')) {
        this.localPlaylistTabs.splice(idx, 1);
        this.localActiveTabIndex = Math.max(0, this.localActiveTabIndex - 1);
      }
    },

    // ✅✅✅ 【彻底修复卡死 - 重写所有拖拽逻辑 零卡顿核心】
    // 核心原则：1.拖拽全程 非响应式操作 2.只在结束时一次性更新 3.防抖emit 4.新增占位视觉反馈
    handleDragStart(idx) {
      this.dragStartIndex = idx;
      this.dragPlaceholderIndex = -1;
      this.isDragging = true;
      // ✅ 拖拽元素透明化，体验更好
      event.dataTransfer.effectAllowed = 'move';
    },
    // ✅ 新增：拖拽悬浮时的占位索引，实现视觉跟随
    handleDragOver(idx) {
      if (this.dragStartIndex === -1 || this.dragStartIndex === idx) return;
      this.dragPlaceholderIndex = idx;
    },
    // ✅ 优化：离开时清空占位
    handleDragLeave(idx) {
      if (this.dragPlaceholderIndex === idx) {
        this.dragPlaceholderIndex = -1;
      }
    },
    // ✅ 核心：拖拽放下，只执行一次数组操作+一次更新，零重渲染
    handleDrop(dropIndex) {
      if (this.dragStartIndex === -1 || this.dragStartIndex === dropIndex) return;
      const currTracks = [...this.currentPlaylist];
      const dragItem = currTracks.splice(this.dragStartIndex, 1)[0];
      currTracks.splice(dropIndex, 0, dragItem);
      // 一次性赋值，仅触发1次响应式更新
      this.localPlaylistTabs[this.localActiveTabIndex].tracks = currTracks;
      this.resetDragStatus();
    },
    // ✅ 修复BUG：拖拽到外部删除，逻辑严谨+无状态混乱，是卡死的核心修复点
    handleDragEnd(dragIndex) {
      // 判断：拖拽开始过 + 不在歌单区域内 = 拖拽到外部，执行删除
      if (this.dragStartIndex !== -1 && this.dragPlaceholderIndex === -1) {
        this.localPlaylistTabs[this.localActiveTabIndex].tracks.splice(dragIndex, 1);
        if (dragIndex === this.currentTrackIndex) {
          this.$emit('update:currentTrackIndex', -1);
        }
        this.$message?.success('已删除该专辑');
      }
      this.resetDragStatus();
    },
    // ✅ 新增：统一重置拖拽状态，避免状态混乱导致的无限更新
    resetDragStatus() {
      this.isDragging = false;
      this.dragStartIndex = -1;
      this.dragPlaceholderIndex = -1;
      // 防抖同步父组件，杜绝高频emit阻塞
      clearTimeout(this.dragTimer)
      this.dragTimer = setTimeout(() => {
        this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(this.localPlaylistTabs)));
      }, 50);
    },

    // 下半区专辑拖拽添加歌单 - 保留原逻辑+轻微优化
    handleDragAlbumStart(album) {
      this.dragAlbumData = album;
      event.dataTransfer.effectAllowed = 'copy';
    },
    handleDragAlbumEnd() {
      if (this.dragAlbumData) {
        this.handleAddThisAlbumTracks(this.dragAlbumData);
        this.$message?.success(`已添加《${this.dragAlbumData.album_name}》到歌单`);
        this.dragAlbumData = null;
      }
    },

    // 播放模式切换 - 无修改
    togglePlayMode() {
      let newMode = 'order';
      if (this.playMode === 'order') newMode = 'single';
      else if (this.playMode === 'single') newMode = 'random';
      else if (this.playMode === 'random') newMode = 'order';
      this.$emit('update:playMode', newMode);
      this.$message?.success(`已切换为：${this.playModeText}`);
      // ✅ 新增：播放模式变更后，强制更新父组件并保存
      this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(this.localPlaylistTabs)));
    },

    // 筛选排序 - 优化：浅拷贝改为直接赋值，减少内存占用
    filterAndSortAlbums() {
      let filterList = this.albumList;
      const searchKey = this.albumSearchKey.trim().toLowerCase();
      if (searchKey) {
        filterList = filterList.filter(item => {
          const albumName = item.album_name?.toLowerCase() || '';
          const singer = item.singer?.toLowerCase() || '';
          return albumName.includes(searchKey) || singer.includes(searchKey);
        });
      }
      // 排序不生成新数组，原地排序，提升性能
      switch (this.sortType) {
        case 'addTime':
          filterList.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          break;
        case 'name':
          filterList.sort((a, b) => a.album_name.localeCompare(b.album_name, 'zh-CN'));
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
    handleDelTrack(index) {
      this.localPlaylistTabs[this.localActiveTabIndex].tracks.splice(index, 1);
      if (index === this.currentTrackIndex) this.$emit('update:currentTrackIndex', -1);
      // ========== ✅ 新增：删除歌曲后，强制emit更新父组件，触发保存 ==========
      this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(this.localPlaylistTabs)));
    },
    handleRemoveAllTracks() {
      this.localPlaylistTabs[this.localActiveTabIndex].tracks = [];
      this.$emit('update:currentTrackIndex', -1);
      this.$message?.success('已清空当前歌单');
      // ========== ✅ 新增：清空歌单后，强制emit更新父组件，触发保存 ==========
      this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(this.localPlaylistTabs)));
    },
    handleAddThisAlbumTracks(album) {
      this.localPlaylistTabs[this.localActiveTabIndex].tracks.push({...album, sortId: this.sortIdSeed++});
    },
    handleAddAllAlbumTracks() {
      let addCount = 0;
      this.filterAlbums.forEach(album => {
        this.localPlaylistTabs[this.localActiveTabIndex].tracks.push({...album, sortId: this.sortIdSeed++});
        addCount++;
      });
      this.$message?.success(`已添加 ${addCount} 张专辑到当前歌单`);
    },
    handleChangeSort(type) {
      this.sortType = type;
    },
    handleClose() {
      this.$emit('close-sidebar');
      // ========== ✅ 新增：主动触发父组件保存，兜底逻辑，百分百触发 ==========
      this.$emit('update:playlistTabs', JSON.parse(JSON.stringify(this.localPlaylistTabs)));
      this.saveUserPlaylistData && this.saveUserPlaylistData()
    },

// ✅✅✅ 播放列表-专辑名跳转详情页 【最终终极版 地址绝对正确：/album/detail/真实album_id】
    async handleJumpAlbumDetail(idx) {
      const albumItem = this.currentPlaylist[idx];
      console.log('👉 点击专辑名，准备查询专辑ID并跳转', albumItem);
      // 1. 第一层校验：防空、防数据异常
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
        // 2. 调用后端新增的专属接口，精准查询当前用户的真实album_id
        const res = await this.$axios.get('/api/album/get-id-by-source', {
          params: {source_pool_id: sourcePoolId}
        });
        // 3. 接口返回成功，拿到真实album_id，执行【正确路径跳转】
        if (res.data.code === 200 && res.data.data?.album_id) {
          const realAlbumId = res.data.data.album_id;
          console.log('✅ 精准匹配成功：source_pool_id=', sourcePoolId, ' → album_id=', realAlbumId);
          // ========== ✅核心修正：跳转地址改为【路径参数】，绝对正确 ✅ ==========
          this.$router.push({
            path: `/album/detail/${realAlbumId}`, // 路径参数：/album/detail/27
            query: {id: realAlbumId}             // 查询参数：?id=27
          });
          // ========== 原有体验优化逻辑 ==========
          this.handleClose(); // 跳转后关闭播放列表
          this.$emit('update:currentTrackIndex', -1); // 暂停当前播放的音频
        } else if (res.data.code === 404) {
          this.$message?.info(res.data.msg);
        } else {
          this.$message?.error(res.data.msg || '查询专辑信息失败');
        }
      } catch (err) {
        console.error('❌ 查询专辑ID失败：', err);
        this.$message?.error('跳转失败，请稍后重试');
      }
    },

// ✅✅✅ 下方可添加专辑列表-专辑名跳转 【同逻辑 地址修正版】
    async handleJumpAlbumDetailByItem(album) {
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
        const res = await this.$axios.get('/api/album/get-id-by-source', {
          params: {source_pool_id: sourcePoolId}
        });
        if (res.data.code === 200 && res.data.data?.album_id) {
          // ========== ✅核心修正：正确路径跳转 ✅ ==========
          console.log('yyyyyyy')
          this.$router.push({
            path: `/album/detail/${res.data.data.album_id}`, // 路径参数：/album/detail/27
            query: {id: res.data.data.album_id}             // 查询参数：?id=27
          });
          this.handleClose();
        } else if (res.data.code === 404) {
          this.$message?.info(res.data.msg);
        } else {
          this.$message?.error(res.data.msg || '查询专辑信息失败');
        }
      } catch (err) {
        console.error('❌ 查询专辑ID失败：', err);
        this.$message?.error('跳转失败，请稍后重试');
      }
    }
  }
};
</script>

<style scoped>
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

/* 顶部横向歌单样式 */
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
  scrollbar-width: thin;
  padding-bottom: 5px;
}

.tab-scroll-box::-webkit-scrollbar {
  height: 4px;
}

.tab-scroll-box::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDark);
  border-radius: 2px;
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

/* 全局统一样式 - 上下排序/按钮/卡片完全一致 核心类 */
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
  user-select: none; /* ✅ 新增：禁止拖拽时选中文本，减少卡顿 */
}

.common-album-card:hover {
  background: rgba(255, 255, 255, 0.5);
}

.common-scroll-list {
  width: 100%;
  overflow-y: auto;
  scrollbar-width: thin;
  max-height: 260px;
}

.common-scroll-list::-webkit-scrollbar {
  width: 4px;
}

.common-scroll-list::-webkit-scrollbar-thumb {
  background: v-bind(mainColorDark);
  border-radius: 2px;
}

/* 序号+专辑名+歌手+评分 完全在同一行 */
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

/* 上半部分样式 */
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
  cursor: move;
}

/* ✅ 新增：拖拽元素样式 - 透明化+占位高亮，核心视觉优化 */
.album-play-item.dragging {
  opacity: 0.4;
  background: rgba(255, 255, 255, 0.1);
}

.album-play-item.placeholder {
  background: v-bind(activeMenuBg);
  opacity: 0.8;
  border: 1px dashed v-bind(mainColorDark);
}

.track-del {
  color: #999;
  font-size: 18px;
  cursor: pointer;
  padding: 0 6px;
  transition: all 0.1s;
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

/* 下半部分核心：固定位置 + 不滚动 + 样式完全和上半部分统一 */
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
</style>