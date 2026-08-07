# 后端API路由完整参考

## 一、路由注册机制

所有API路由通过 `backend/api/__init__.py` 的 `register_all_api_routes(app)` 统一注册。每个模块导出 `register_*_routes(app)` 函数。

**注册顺序**：auth → album → album_pool → review → comment → audio_resource → playlist → listening → score → recommend → unlock → tags → lyric → share

---

## 二、认证模块 `auth.py`

### POST `/api/register`
- **参数**：`{username, password}`
- **逻辑**：校验用户名非法字符(%^&) → 检查用户名重复 → bcrypt加密密码 → 创建用户 → 创建用户专属专辑表
- **返回**：`{code:200, data:{username}}`

### POST `/api/login`
- **参数**：`{username, password}`
- **逻辑**：查用户 → bcrypt验证密码 → 生成UUID token → 更新token和last_login
- **返回**：`{code:200, data:{token, username, user_id, is_admin, is_vip, level}}`

---

## 三、用户专辑模块 `album.py`

### GET `/api/album/list`
- **认证**：@login_required
- **参数**：`page, page_size, sort_by, sort_order, search_keyword, tag_keyword`
- **排序白名单**：`album_name, release_year, singer, my_score, created_at, listening_duration`
- **逻辑**：查用户专辑表 → 计算calculated_score → 排序 → 分页
- **返回**：`{list, pagination}`

### GET `/api/album/detail/<int:album_id>`
- **逻辑**：关联查询album_pool获取mp3_url
- **返回**：包含所有字段的专辑详情，含mp3_url和mp3_duration

### POST `/api/album/add`
- **参数**：完整专辑数据（含tracks, tracks_time, mp3_url, mp3_duration）
- **逻辑**：双重校验（公共池+私有库重复）→ 插入album_pool → 插入用户表 → 保存简介
- **返回**：`{code:200, data:完整专辑对象}`

### DELETE `/api/album/delete/<int:album_id>`
- **逻辑**：删除user_album_intro记录 → 删除用户专辑表记录

### PUT `/api/album/update/tags/<int:album_id>`
- **参数**：`{tags:[]}`（最多5个标签）
- **逻辑**：更新用户表tags → 同步更新user_album_relation表

### PUT `/api/album/update/tracks/<int:album_id>`
- **参数**：`{tracks:[], tracks_time:[]}`
- **逻辑**：更新tracks和tracks_time → 标记is_customized=1

### PUT `/api/album/update/favourite_tracks/<int:album_id>`
- **参数**：`{tracks:[], tracks_time:[]}`
- **逻辑**：更新favourite_tracks和favourite_tracks_time

### GET `/api/album/get-id-by-source`
- **参数**：`source_pool_id`
- **返回**：`{album_id, source_pool_id}`

### POST `/api/album/sync/switch`
- **参数**：`{album_id, sync_status}`
- **逻辑**：开关sync_pool_update字段

### POST `/api/album/mark/customized`
- **参数**：`{album_id}`
- **逻辑**：标记is_customized=1

### POST `/api/album/user/intro/save`
- **参数**：`{album_id, intro_content}`
- **逻辑**：双表同步保存（user_album_intro + albums_用户ID表）

### GET `/api/album/user/intro/get/<int:album_id>`
- **返回**：简介文本字符串

---

## 四、公共专辑池模块 `album_pool.py`

### GET `/api/album/pool/detail/<int:pool_id>`
- **逻辑**：LEFT JOIN users获取创建者名 → 解析JSON字段

### GET `/api/album/pool/search/name-singer`
- **参数**：`keyword, page, page_size, sort_field, sort_order`
- **排序白名单**：`create_time, release_year, album_name, singer`
- **搜索范围**：album_name, singer, album_intro

### GET `/api/album/pool/search/tags`
- **参数**：`tag, page, page_size, sort_field, sort_order`
- **逻辑**：查全量专辑 → 逐专辑计算标签统计 → 过滤匹配 → 分页

### GET `/api/album/<int:album_pool_id>/tag-statistics`
- **逻辑**：统计公共池+所有用户表的标签 → 计算占比 → 过滤<10% → 生成气泡图数据

### POST `/api/album/pool/copy/<int:album_id>`
- **逻辑**：双重重复校验（私有库+公共池）→ 复制数据到用户表 → 创建user_album_relation
- **返回**：`{copy_album_id, source_pool_id, tracks_time}`

### PUT `/api/album/pool/update/<int:pool_id>`
- **权限**：仅管理员
- **逻辑**：更新公共池 → 差异化同步用户专辑（强制同步：专辑名/歌手/发行年/时长类型；简介：仅同步空值/未自定义）
- **版本管理**：version+1, 记录update_log

### DELETE `/api/album/pool/delete/<int:pool_id>`
- **权限**：仅管理员
- **级联删除**：删除音频文件 → 删除封面图片 → 删除所有用户表关联记录 → 删除公共池记录

### GET `/api/album/pool/users/<int:pool_id>`
- **逻辑**：查询user_album_relation获取拥有该专辑的用户

### GET `/api/album_pool/get_id`
- **参数**：`album_name, singer`

---

## 五、评分模块 `score.py`

### PUT `/api/album/score/save/<int:album_id>`
- **参数**：`{score_list:[]}` — [专辑整体评分, 单曲1, 单曲2, ...]
- **逻辑**：JSON序列化存入my_score字段

### GET `/api/album/score/get/<int:album_id>`
- **返回**：`{score_list:[]}`

---

## 六、听后感模块 `review.py`

### POST `/api/album/review/add/<int:album_id>`
- **参数**：`{content, create_time, listening_duration, my_score}`
- **逻辑**：追加到review.feelings数组

### POST `/api/album/review/delete/single/<int:album_id>`
- **参数**：`{feeling_id}`
- **逻辑**：从feelings数组中过滤指定ID

### DELETE `/api/album/review/delete/<int:album_id>`
- **逻辑**：清空feelings和personal_feeling

### POST `/api/album/review/edit/<int:album_id>`
- **参数**：`{personal_feeling, update_time}`
- **逻辑**：更新review对象的personal_feeling和update_time

### GET `/api/album/review/calendar`
- **逻辑**：遍历所有专辑的review → 解析feelings → 按日期聚合返回日历数据

---

## 七、评论模块 `comment.py`

### POST `/api/music/comment`
- **参数**：`{musicId, comment, score, listening_duration}`
- **逻辑**：私有评论，追加到comments数组

### POST `/api/album/comment/add/<int:album_id>`
- **参数**：`{comment, listening_duration}`
- **逻辑**：私有评论，不修改评分

### GET `/api/album/pool/comment/check`
- **参数**：`album_id`
- **返回**：`{has_comment, comment_id}`

### POST `/api/album/pool/comment/add`
- **参数**：`{album_id, content, listening_duration}`
- **逻辑**：唯一性校验（同一用户同一专辑只能评论一次）

### GET `/api/album/pool/comment/list/<int:album_id>`
- **返回**：评论列表（含listening_duration, like_count, like_user_ids）

### POST `/api/album/pool/comment/like/<int:comment_id>`
- **逻辑**：点赞/取消点赞切换

### DELETE `/api/album/pool/comment/delete/<int:comment_id>`
- **权限**：评论作者或管理员

---

## 八、播放列表模块 `playlist.py`

### GET `/api/playlist/get-user-audio-albums`
- **逻辑**：INNER JOIN album_pool筛选有mp3_url的专辑 → 计算综合评分

### GET `/api/playlist/get-user-playlist-data`
- **逻辑**：获取/初始化播放列表数据（默认歌单）
- **返回**：`{playlist, current_album_id, current_playlist_id, play_mode}`

### POST `/api/playlist/save-user-playlist-data`
- **参数**：`{playlist, current_album_id, activeTabIndex, play_mode}`
- **逻辑**：JSON序列化playlist → INSERT/UPDATE

### POST `/api/playlist/switch-next-album`
- **参数**：`{current_playlist_id, current_album_id, play_mode, playlist}`
- **播放模式**：`single`（单曲循环）、`order`（顺序）、`random`（随机）

---

## 九、听取时长模块 `listening.py`

### POST `/api/album/listening/start/<int:album_id>`
- **逻辑**：记录开始时间戳到内存缓存PLAYING_TIMER_CACHE

### POST `/api/album/listening/pause/<int:album_id>`
- **逻辑**：计算本次播放秒数 → 累加到listening_duration → 更新数据库 → 清除内存缓存
- **自动补字段**：如果用户表缺少listening_duration字段，自动ALTER TABLE添加

---

## 十、推荐模块 `recommend.py`

### GET `/api/recommend/today`
- **逻辑**：检查用户是否已有推荐 → 判断是否跨天 → 需要刷新则随机选专辑 → 写入/更新user_recommend

### POST `/api/recommend/refresh` 或 `/api/recommend/change-today`
- **逻辑**：随机获取专辑池ID → 更新推荐

---

## 十一、标签模块 `tags.py`

### POST `/api/tags/add` — 仅管理员
### GET `/api/tags/list` — 启用标签列表
### GET `/api/tags/detail` — 参数：tagName
### GET `/api/tags/tree` — 树状结构
### POST `/api/tags/edit` — 仅管理员
### GET `/api/tags/album/stats` — 标签专辑统计（占比>10%）
### GET `/api/tags/album/year-stats` — 年份统计
### GET `/api/tags/album/list` — 分页专辑列表（支持listenStatus: all/listened/unlistened/unrecorded）
### GET `/api/tags/album/tag-stats` — 标签下共现标签统计
### GET `/api/tags/parent-tags` — 参数：ids(逗号分隔)
### GET `/api/tags/album/all-ids` — 全量专辑ID（不分页）

---

## 十二、歌词模块 `lyric.py`

### POST `/api/album/lyric/save/<int:album_pool_id>`
- **参数**：`{lyric_text, lyric_translate}`
- **逻辑**：INSERT/UPDATE album_lyric表

### GET `/api/album/lyric/get/<int:album_pool_id>`
- **返回**：`{lyric_text, lyric_translate}`

### POST `/api/lyric/fetch_auto`
- **参数**：`{song_name, artist, duration}`
- **逻辑**：QQ音乐歌词获取（搜索→获取songmid→获取歌词→base64解码→清理格式）

### POST `/api/lyric/krc2lrc`
- **参数**：上传.krc文件
- **逻辑**：XOR解密（固定KEY）→ JSON解析 → 生成LRC格式

---

## 十三、专题模块 `share.py`

### GET `/api/album/share/weekly-list` — 按周聚合专题列表
### GET `/api/album/share/week-detail` — 参数：weekStart
### POST `/api/album/share/create` — 参数：albumPoolId, shareText, createTime
### POST `/api/album/share/update-title` — 参数：weekStart, newTitle
### GET `/api/album/pool/available-list` — 可选专辑（10年限制）
### POST `/api/album/share/delete-week` — 参数：weekStart
### POST `/api/album/share/delete-album` — 参数：shareId

---

## 十四、音频资源模块 `audio_resource.py`

### POST `/api/album/pool/audio/upload` — 管理员上传MP3
- **参数**：source_pool_id, mp3_file, old_mp3_url
- **逻辑**：校验管理员 → 生成唯一文件名 → 删除旧文件 → 保存新文件 → 解析时长 → 更新album_pool

### GET `/api/album/pool/audio/info/<int:album_id>`
### POST `/api/album/pool/audio/delete` — 管理员删除音频
### GET `/api/album/user/has-audio` — 查询用户有音频的专辑
### POST `/api/album/pool/audio/upload/merged` — 管理员上传合并音频

---

## 十五、音频解密模块 `unlock.py`

### POST `/api/audio/unlock/parse` — 音频解析（多文件→合并→上传）
### POST `/api/audio/unlock/convert-kgg-only` — KGG转MP3
### POST `/api/audio/unlock/convert-ncm-only` — NCM转MP3
### POST `/api/audio/unlock/convert-mp3-only` — 通用音频转MP3
### POST `/api/audio/unlock/parse-sorted-mp3` — 排序后MP3解析

---

## 十六、图床/文件模块 `upload_utils.py`

### GET `/covers/<filename>` — 封面图片访问
### GET `/tracks/<filename>` — 音频文件访问
### POST `/api/upload_img` — 图片上传（UUID文件名）

---

## 通用响应格式

```json
{
  "code": 200,       // 200=成功, 401=未登录, 403=无权限, 404=不存在, 409=重复, 500=错误
  "msg": "操作描述",
  "data": {}         // 业务数据
}
```

**注意**：大多数接口错误时返回HTTP 200 + 业务码，仅少数接口（如auth）使用HTTP状态码。
