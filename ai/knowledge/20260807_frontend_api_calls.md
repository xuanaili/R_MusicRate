# 前端API调用参考

## 一、API调用模式

### 标准GET请求
```javascript
this.$axios({
  url: '/api/album/list',
  method: 'GET',
  headers: { 'Authorization': localStorage.getItem('token') || '' },
  params: { page: 1, page_size: 10, sort_by: 'album_name', sort_order: 'asc' }
}).then(res => {
  if (res.data.code === 200) {
    // 处理成功
  }
}).catch(err => {
  console.error('请求失败：', err)
})
```

### 标准POST请求
```javascript
this.$axios.post('/api/album/add', data, {
  headers: { 'Authorization': localStorage.getItem('token') || '' }
}).then(res => {
  if (res.data.code === 200) {
    // 处理成功
  }
})
```

### 文件上传请求
```javascript
const formData = new FormData()
formData.append('mp3_file', file)
formData.append('source_pool_id', poolId)
this.$axios.post('/api/album/pool/audio/upload', formData, {
  headers: {
    'Authorization': localStorage.getItem('token'),
    'Content-Type': 'multipart/form-data'
  }
})
```

---

## 二、各模块API调用清单

### 登录/注册
| 组件 | API | 方法 | 参数 |
|------|-----|------|------|
| LoginPage | `/api/login` | POST | `{username, password}` |
| RegisterPage | `/api/register` | POST | `{username, password}` |

### 我的专辑列表 (MusicList)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/album/list` | GET | `page, page_size, sort_by, sort_order, search_keyword, tag_keyword` | 分页列表 |
| `/api/album/delete/{id}` | DELETE | — | 删除专辑 |

### 专辑详情 (AlbumDetail)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/album/detail/{id}` | GET | — | 专辑详情 |
| `/api/album/score/save/{id}` | PUT | `{score_list}` | 保存评分 |
| `/api/album/score/get/{id}` | GET | — | 获取评分 |
| `/api/album/update/tags/{id}` | PUT | `{tags}` | 更新标签 |
| `/api/album/update/tracks/{id}` | PUT | `{tracks, tracks_time}` | 更新曲目 |
| `/api/album/update/favourite_tracks/{id}` | PUT | `{tracks, tracks_time}` | 更新收藏曲目 |
| `/api/album/review/add/{id}` | POST | `{content, create_time, listening_duration, my_score}` | 添加听后感 |
| `/api/album/review/delete/single/{id}` | POST | `{feeling_id}` | 删除单条听后感 |
| `/api/album/review/edit/{id}` | POST | `{personal_feeling, update_time}` | 编辑听后感 |
| `/api/album/listening/start/{id}` | POST | — | 开始计时 |
| `/api/album/listening/pause/{id}` | POST | — | 暂停计时 |
| `/api/album/user/intro/save` | POST | `{album_id, intro_content}` | 保存简介 |
| `/api/album/user/intro/get/{id}` | GET | — | 获取简介 |
| `/api/album/sync/switch` | POST | `{album_id, sync_status}` | 同步开关 |

### 公共池 (SearchAlbumPool)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/album/pool/search/name-singer` | GET | `keyword, page, page_size, sort_field, sort_order` | 名字/歌手搜索 |
| `/api/album/pool/search/tags` | GET | `tag, page, page_size, sort_field, sort_order` | 标签搜索 |
| `/api/album/pool/copy/{id}` | POST | — | 复制到私有库 |
| `/api/album/pool/delete/{id}` | DELETE | — | 删除(管理员) |

### 公共池详情 (AlbumPoolDetail)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/album/pool/detail/{poolId}` | GET | — | 详情 |
| `/api/album/pool/comment/list/{id}` | GET | — | 评论列表 |
| `/api/album/pool/comment/add` | POST | `{album_id, content, listening_duration}` | 添加评论 |
| `/api/album/pool/comment/like/{id}` | POST | — | 点赞/取消 |
| `/api/album/pool/comment/delete/{id}` | DELETE | — | 删除评论 |

### 每日推荐 (DailyRecommend)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/recommend/today` | GET | — | 今日推荐 |
| `/api/recommend/refresh` | POST | — | 刷新推荐 |

### 标签 (CategoryList/TagDetail)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/tags/list` | GET | — | 标签列表 |
| `/api/tags/detail` | GET | `tagName` | 标签详情 |
| `/api/tags/tree` | GET | — | 标签树 |
| `/api/tags/album/stats` | GET | `tagName` | 标签专辑统计 |
| `/api/tags/album/list` | GET | `tagName, year, page, page_size, listenStatus` | 标签下专辑列表 |
| `/api/tags/album/year-stats` | GET | `tagName` | 年份统计 |
| `/api/tags/album/tag-stats` | GET | `tagName, albumIds` | 共现标签统计 |
| `/api/tags/parent-tags` | GET | `ids` | 父标签查询 |
| `/api/tags/add` | POST | 标签数据 | 添加标签(管理员) |
| `/api/tags/edit` | POST | 标签数据 | 编辑标签(管理员) |

### 音乐专题 (MusicSpecial)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/album/share/weekly-list` | GET | — | 周列表 |
| `/api/album/share/week-detail` | GET | `weekStart` | 周详情 |
| `/api/album/share/create` | POST | `{albumPoolId, shareText, createTime}` | 创建专题 |
| `/api/album/pool/available-list` | GET | — | 可选专辑 |

### 歌词 (AlbumLyricViewer)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/album/lyric/get/{id}` | GET | — | 获取歌词 |
| `/api/album/lyric/save/{id}` | POST | `{lyric_text, lyric_translate}` | 保存歌词 |
| `/api/lyric/fetch_auto` | POST | `{song_name, artist, duration}` | QQ音乐自动获取 |
| `/api/lyric/krc2lrc` | POST | KRC文件 | KRC转LRC |

### 音频 (PlayerPlaylist/UnlockParse)
| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/playlist/get-user-audio-albums` | GET | — | 有音频的专辑 |
| `/api/playlist/get-user-playlist-data` | GET | — | 播放列表数据 |
| `/api/playlist/save-user-playlist-data` | POST | 播放列表数据 | 保存播放列表 |
| `/api/playlist/switch-next-album` | POST | 切换参数 | 下一首 |
| `/api/album/pool/audio/upload` | POST | formData | 上传音频(管理员) |
| `/api/album/pool/audio/info/{id}` | GET | — | 音频信息 |
| `/api/album/pool/audio/delete` | POST | `{source_pool_id, mp3_url}` | 删除音频 |
| `/api/audio/unlock/parse` | POST | formData | 音频解析 |
| `/api/audio/unlock/convert-ncm-only` | POST | formData | NCM转换 |
| `/api/audio/unlock/convert-kgg-only` | POST | formData | KGG转换 |
| `/api/audio/unlock/convert-mp3-only` | POST | formData | 通用转换 |
| `/api/upload_img` | POST | formData | 图片上传 |

---

## 三、响应处理模式

```javascript
// 成功处理
if (res.data.code === 200) {
  this.data = res.data.data
}

// 业务错误处理
if (res.data.code === 409) {
  // 重复数据
}

// 网络错误处理
.catch(err => {
  if (err.response) {
    // 有响应但状态码非200
    const { code, msg } = err.response.data || {}
  } else if (err.request) {
    // 无响应（后端未启动）
    this.errorMsg = '连接服务器失败'
  }
})
```

---

## 四、管理员权限判断

```javascript
// 登录时存储
localStorage.setItem('is_admin', res.data.data.is_admin.toString())

// 使用时判断
this.isAdmin = localStorage.getItem('is_admin') === '1'
```

管理员专属UI：
- 新增专辑按钮
- 删除公共池专辑按钮
- 编辑/添加标签按钮
- 上传音频按钮
