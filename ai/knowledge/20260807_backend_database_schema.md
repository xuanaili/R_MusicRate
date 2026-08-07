# 后端数据库Schema完整参考

## 一、数据库配置

- **引擎**：MySQL 8, InnoDB, utf8mb4
- **连接**：`localhost:3306`, 用户 `music_user`, 密码 `123456`, 库名 `music_rate`
- **游标**：默认使用 `pymysql.cursors.DictCursor`（返回字典格式）
- **连接管理**：Flask g对象隔离，teardown自动关闭

---

## 二、核心表结构

### 1. `users` — 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | INT PK AUTO_INCREMENT | 用户唯一标识 |
| username | VARCHAR(50) UNIQUE | 用户名（禁用%^&） |
| password | VARCHAR(100) | bcrypt加密密码 |
| level | INT DEFAULT 0 | 等级/经验 |
| create_time | DATETIME | 开户日期 |
| last_login | DATETIME | 最近登录时间 |
| is_vip | TINYINT DEFAULT 0 | 是否VIP |
| is_admin | TINYINT DEFAULT 0 | 是否管理员 |
| donate_amount | DECIMAL(10,2) | 捐款数 |
| album_count | INT DEFAULT 0 | 收藏专辑数 |
| token | VARCHAR(100) | 登录令牌(UUID) |

**默认管理员**：admin/123456，is_admin=1, is_vip=1, level=10

### 2. `album_pool` — 公共专辑池（共享模板）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 主键 |
| album_name | VARCHAR(100) | 专辑名 |
| cover_img | VARCHAR(255) | 封面URL |
| singer | VARCHAR(100) | 歌手 |
| release_year | INT | 发行年份 |
| main_type | VARCHAR(50) | 主类型(JSON) |
| tags | TEXT | 标签(JSON数组) |
| album_intro | TEXT | 专辑简介 |
| tracks | TEXT | 单曲列表(JSON数组) |
| my_score | TEXT | 单曲评分数组(JSON) |
| create_user | INT | 创建用户ID |
| create_time | TIMESTAMP | 创建时间 |
| version | INT DEFAULT 1 | 模板版本号 |
| update_log | TEXT | 修改日志(JSON) |
| mp3_url | VARCHAR(255) | 整轨MP3地址 |
| mp3_name | VARCHAR(100) | MP3原始文件名 |
| mp3_duration | INT DEFAULT 0 | 音频时长(秒) |

**索引**：album_name, singer, tags(50), album_intro(50), main_type, tracks(50), version, mp3_url

### 3. `albums_{user_id}` — 用户专属专辑表（每用户一张）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 主键 |
| album_name | VARCHAR(100) | 专辑名 |
| cover_img | VARCHAR(255) | 封面URL |
| singer | VARCHAR(100) | 歌手 |
| release_year | INT | 发行年份 |
| start_time | VARCHAR(50) | 开始时间 |
| track_count | INT DEFAULT 0 | 曲目数 |
| track_duration | VARCHAR(50) | 时长 |
| my_score | TEXT | 单曲评分数组(JSON) |
| burn_class | VARCHAR(50) | 烧录等级 |
| duration_type | VARCHAR(50) | 时长类型(LP/EP/SIN/COM) |
| tags | TEXT | 标签(JSON数组) |
| main_type | TEXT | 主类型(JSON) |
| code | VARCHAR(50) | 编码 |
| video_shared | VARCHAR(50) | 视频分享 |
| mandopop_code | VARCHAR(50) | 华语流行编码 |
| album_intro | TEXT | 专辑简介 |
| tracks | TEXT | 单曲列表(JSON数组) |
| tracks_time | TEXT | 单曲时间戳(JSON数组，秒) |
| review | TEXT | 听后感(JSON) |
| score | FLOAT DEFAULT 0.0 | 评分 |
| comments | TEXT | 私有评论(JSON数组) |
| source_pool_id | INT | 来源公共模板ID |
| sync_pool_update | TINYINT DEFAULT 1 | 是否同步模板更新 |
| is_customized | TINYINT DEFAULT 0 | 是否用户自定义修改 |
| favourite_tracks | TEXT | 收藏曲目列表(JSON) |
| favourite_tracks_time | TEXT | 收藏曲目时间戳(JSON) |
| listening_duration | FLOAT DEFAULT 0.0 | 累计播放时长(秒) |
| created_at | TIMESTAMP | 创建时间 |

**关键设计**：
- `my_score` 为TEXT类型且无默认值（解决MySQL 1101错误）
- `tracks` 和 `tracks_time` 数组一一对应、索引一致
- `favourite_tracks` 和 `favourite_tracks_time` 同理

### 4. `album_comments` — 公共评论表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 评论ID |
| album_id | INT FK→album_pool.id | 关联专辑ID |
| user_id | INT FK→users.user_id | 评论用户ID |
| username | VARCHAR(50) | 评论用户名(冗余) |
| content | TEXT | 评论内容 |
| create_time | DATETIME | 评论时间 |
| like_count | INT DEFAULT 0 | 点赞数 |
| like_user_ids | VARCHAR(255) | 点赞用户ID列表(逗号分隔) |

### 5. `album_tags` — 风格标签表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT UNSIGNED PK | 类型ID |
| tags_name | VARCHAR(100) UNIQUE | 类型名（格式：English【中文】） |
| aka_name | VARCHAR(500) | 别名(逗号分隔) |
| parameter_style | TEXT | 样式参数(JSON) |
| brief_intro | VARCHAR(500) | 简洁介绍 |
| detail_intro | TEXT | 详细介绍 |
| related_singers | TEXT | 关联歌手(JSON) |
| related_albums | TEXT | 关联专辑(JSON) |
| related_tags | TEXT | 关联风格(JSON) |
| parent_tag_ids | VARCHAR(200) | 父标签ID(逗号分隔) |
| is_enabled | TINYINT UNSIGNED DEFAULT 1 | 是否启用 |

### 6. `album_singers` — 歌手信息表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT UNSIGNED PK | 歌手ID |
| singer_name | VARCHAR(100) UNIQUE | 歌手姓名 |
| birth_place | VARCHAR(200) | 出生地 |
| singer_alias | VARCHAR(500) | 别名(逗号分隔) |
| detail_intro | TEXT | 详细介绍 |
| related_singers/albums/tags | TEXT | 关联信息(JSON) |
| display_singers | TEXT | 展示用关联歌手(JSON) |
| is_enabled | TINYINT UNSIGNED DEFAULT 1 | 是否启用 |

### 7. `user_album_intro` — 用户专辑简介表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| user_id | INT | 用户ID |
| album_id | INT | 专辑ID |
| album_intro | TEXT | 用户自定义简介 |
| update_time | TIMESTAMP | 更新时间 |

**唯一约束**：`(user_id, album_id)`

### 8. `user_playlist` — 用户播放列表表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| user_id | INT UNIQUE | 用户ID |
| playlist | JSON | 播放列表数据 |
| current_album_id | INT DEFAULT 0 | 当前播放专辑ID |
| current_playlist_id | INT DEFAULT 0 | 当前歌单下标 |
| play_mode | VARCHAR(10) DEFAULT 'order' | 播放模式 |

### 9. `user_recommend` — 用户每日推荐表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| user_id | INT UNIQUE FK→users | 用户ID |
| recommend_daily_id | INT FK→album_pool | 推荐专辑ID |
| update_time | DATETIME | 更新时间 |

### 10. `album_lyric` — 歌词表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| album_pool_id | INT | 专辑池ID |
| lyric_text | TEXT | 原版歌词 |
| lyric_translate | TEXT | 翻译歌词(JSON: {CN:text, EN:text}) |
| create_user_id | VARCHAR(50) | 创建用户ID |
| create_time | DATETIME | 创建时间 |
| update_time | DATETIME | 更新时间 |

### 11. `album_share` — 专辑专题表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 主键 |
| album_pool_id | INT | 专辑池ID |
| share_text | TEXT | 专题描述 |
| create_user_id | VARCHAR(50) | 创建用户ID |
| create_time | DATETIME | 创建时间 |

---

## 三、JSON字段格式约定

### my_score 评分数组
```json
[50, 100, 20, 30, 0, 0]
```
- 第一个值 = 专辑整体评分
- 后续 = 各单曲评分，0表示未评分

### tracks / tracks_time
```json
["曲目1", "曲目2", "曲目3"]
[120, 240, 360]
```
- 两个数组一一对应，索引一致

### review 听后感
```json
{
  "feelings": [
    {"id": "uuid", "content": "...", "create_time": "...", "listening_duration": 120, "my_score": 8.0}
  ],
  "personal_feeling": "整体感受",
  "single_score": 0.0,
  "private_score": 0.0,
  "final_score": 0.0,
  "update_time": ""
}
```

### comments 私有评论
```json
[{"content": "评论内容", "listening_duration": 120}]
```

### tags / main_type
```json
["Pop【流行】", "Rock【摇滚】"]
```

### playlist 播放列表
```json
[{"name": "默认歌单", "tracks": [source_pool_id1, source_pool_id2]}]
```

---

## 四、初始化流程

`init_base_tables()` 按顺序创建：
1. album_comments → 2. album_pool → 3. users → 4. user_album_intro → 5. user_playlist → 6. user_recommend → 7. album_tags → 8. album_singers → 9. album_lyric → 10. album_share

然后 `init_default_admin()` 创建默认admin用户及其专属专辑表。

---

## 五、数据库异常处理模式

### try/except 中 db 变量安全模式（强制规范）

所有 `create_*` 函数和 `init_default_admin()` 必须遵循以下模式：

```python
def some_db_operation():
    db = None              # ① try前初始化，防止get_db()失败时db未赋值
    try:
        db = get_db()
        cursor = db.cursor()
        ...
        db.commit()
        cursor.close()
    except Exception as e:
        if db: db.rollback()  # ② 安全检查后再rollback，防止UnboundLocalError
        raise e
```

**为什么必须这样做**：`get_db()` 连接失败时会抛 `pymysql.OperationalError`，此时 `db` 未被赋值。如果 `except` 块直接调用 `db.rollback()`，会触发 `UnboundLocalError`，掩盖真正的连接错误。

### MySQL连接失败常见原因

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `Can't connect to MySQL server on 'localhost' ([WinError 10061])` | MySQL未启动/端口未监听 | 检查MySQL服务或手动启动mysqld |
| `Access denied for user 'music_user'@'localhost'` | 用户名/密码错误 | 检查config.py中的MYSQL_CONFIG |
| `Unknown database 'music_rate'` | 数据库不存在 | 需先 `CREATE DATABASE music_rate` |
| `MySQL service not installed` | 移动硬盘MySQL未注册为Windows服务 | 直接启动mysqld.exe --defaults-file |
