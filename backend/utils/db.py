from flask import g
import pymysql
import traceback
import bcrypt  # 新增：用于密码加密，需先安装 pip install bcrypt
from datetime import datetime
from backend.config import MYSQL_CONFIG, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PWD, DB_URL
from backend.utils.auth import encrypt_password
from backend.utils.level import compute_level


def check_and_create_user_album_table(user_id):
    """检查用户专辑表是否存在，不存在则创建
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        table_name = get_album_table_name(user_id)
        cursor.execute(f'''
            SELECT COUNT(*) as count FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ''', (MYSQL_CONFIG['db'], table_name))
        result = cursor.fetchone()
        table_exists = result['count'] > 0

        if not table_exists:
            create_user_album_table(user_id)
        else:

            db.commit()
        cursor.close()
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 检查/创建用户专辑表失败：{str(e)}")
        traceback.print_exc()
        raise e

def get_next_id(table_name):
    """获取指定表的下一个自增ID"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(f'SELECT MAX(id) as max_id FROM `{table_name}`')
        result = cursor.fetchone()
        max_id = result['max_id']
        cursor.close()
        return 1 if max_id is None else max_id + 1
    except Exception as e:
        print(f"❌ 生成ID失败：{str(e)}")
        return 1

# ========== 原有：用户ID的获取/设置方法 ==========
def get_current_user_id():
    """获取当前登录用户ID（从Flask g对象中获取）"""
    return getattr(g, 'current_user_id', None)

def set_current_user_id(user_id):
    """设置当前登录用户ID（存储到Flask g对象）"""
    g.current_user_id = user_id

def get_db():
    """获取MySQL连接（Flask上下文隔离）"""
    db = getattr(g, '_database', None)
    if db is None:
        try:
            db = g._database = pymysql.connect(**MYSQL_CONFIG)
        except pymysql.MySQLError as e:
            print(f"MySQL连接失败：{str(e)}")
            raise e  # 抛出异常，启动时能直接发现问题
    return db

def close_db(exception):
    """关闭MySQL连接（Flask上下文销毁时自动调用）"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_album_table_name(user_id):
    """生成用户专属的专辑表名：albums_用户ID"""
    if user_id is None:
        raise ValueError("用户ID不能为空！")
    return f'albums_{user_id}'

# ========== ✅ 核心修复：my_score TEXT 无默认值 彻底解决1101 + 兼容历史数据 ==========
def create_user_album_table(user_id):
    """为新用户创建专属的专辑表
    tracks: TEXT 存储【单曲名称数组】JSON字符串 如 ["曲目1","曲目2"]
    tracks_time: TEXT 存储【对应单曲时间戳数组】JSON字符串 如 [120,240,360]
    my_score: TEXT 存储【单曲评分数组】JSON字符串 如 [8.0,9.5,7.8,0,0] ✅TEXT类型 无默认值
    favourite_tracks: TEXT 收藏曲目名称数组
    favourite_tracks_time: TEXT 收藏曲目对应秒数数组
    所有数组一一对应、索引一致、永久保存
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        table_name = get_album_table_name(user_id)
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                id INT PRIMARY KEY AUTO_INCREMENT,
                album_name VARCHAR(100) NOT NULL,
                cover_img VARCHAR(255) DEFAULT "",
                singer VARCHAR(100) NOT NULL,
                release_year INT NOT NULL,
                start_time VARCHAR(50) DEFAULT "",
                track_count INT DEFAULT 0,
                track_duration VARCHAR(50) DEFAULT "",
                my_score TEXT COMMENT '单曲评分数组【JSON】：[8.0,9.5,7.8,0] 与tracks一一对应 ✅TEXT类型 无默认值',
                burn_class VARCHAR(50) DEFAULT "",
                duration_type VARCHAR(50) DEFAULT "",
                tags TEXT,
                main_type TEXT,
                code VARCHAR(50) DEFAULT "",
                video_shared VARCHAR(50) DEFAULT "",
                mandopop_code VARCHAR(50) DEFAULT "",
                album_intro TEXT NULL COMMENT '专辑简介（支持长文本、分段、特殊符号）',
                tracks TEXT COMMENT '单曲列表【数组JSON】：["曲目1","曲目2","曲目3"]',
                review TEXT,
                score FLOAT DEFAULT 0.0,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_pool_id INT NULL COMMENT '来源公共模板ID',
                sync_pool_update TINYINT DEFAULT 1 COMMENT '是否同步模板更新（1=开启，0=关闭）',
                is_customized TINYINT DEFAULT 0 COMMENT '是否用户自定义修改（1=是，0=否）',
                tracks_time TEXT NULL COMMENT '单曲对应编辑时间戳【数组JSON】：[120,240,360]，与tracks数组索引一一匹配',
                favourite_tracks TEXT NULL COMMENT '收藏曲目列表【数组JSON】：["收藏曲目1","收藏曲目2"]',
                favourite_tracks_time TEXT NULL COMMENT '收藏曲目对应秒数【数组JSON】：[120,240,360]，与favourite_tracks数组索引一一匹配',
                listening_duration FLOAT DEFAULT 0.0 COMMENT '专辑累计播放时长(秒) 精准统计',
                listening_progress FLOAT DEFAULT 0.0 COMMENT '专辑上次听取进度(秒) 续播用',
                last_listened DATETIME NULL COMMENT '最近收听时间（打开专辑详情页时更新，用于最近收听排序）'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        db.commit()
        cursor.close()
        print(f"✅ 为用户{user_id}创建专辑表{table_name}成功！my_score为TEXT数组格式+无默认值，解决1101错误")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建用户专辑表失败：{str(e)}")
        traceback.print_exc()
        raise e



# ========== 新增：创建用户-专辑专属简介表 ==========
def create_user_album_intro_table():
    """创建用户-专辑专属简介表（核心：关联user_id + album_id，存储用户自定义简介）"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_album_intro (
                id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
                user_id INT NOT NULL COMMENT '用户ID（关联users表）',
                album_id INT NOT NULL COMMENT '专辑ID（关联用户专属专辑表/album_pool）',
                album_intro TEXT NULL COMMENT '用户自定义的专辑简介（支持长文本、分段）',
                update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
                UNIQUE KEY idx_user_album (user_id, album_id),
                INDEX idx_user_id (user_id),
                INDEX idx_album_id (album_id),
                INDEX idx_update_time (update_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户-专辑专属简介表（与账号绑定）';
        ''')
        db.commit()
        cursor.close()
        print("✅ user_album_intro表创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建user_album_intro表失败：{str(e)}")
        print(traceback.format_exc())
        raise e

# ========== ✅✅✅ 新增：创建用户播放列表表 user_playlist ✅✅✅
def create_user_playlist_table():
    """创建用户播放列表数据表【核心】- 匹配playlist.py接口需求"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_playlist (
                id INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
                user_id INT NOT NULL COMMENT '用户ID，关联users表',
                playlist JSON NOT NULL COMMENT '二维数组：[["播放列表名"],[[source_pool_id数组]]]，如[["默认列表"],[[]]]',
                current_album_id INT NOT NULL DEFAULT 0 COMMENT '当前播放到的专辑source_pool_id标识',
                current_playlist_id INT NOT NULL DEFAULT 0 COMMENT '当前选择的播放列表下标(第几个)',
                PRIMARY KEY (`id`),
                UNIQUE KEY `unique_user_id` (`user_id`)  -- 一个用户只存一条播放列表数据，唯一约束
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户播放列表数据表-侧边栏播放列表专用';
        ''')
        db.commit()
        cursor.close()
        print("✅ user_playlist 用户播放列表表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建user_playlist表失败：{str(e)}")
        print(traceback.format_exc())
        raise e

# ========== ✅ v0.7 P2：用户听取时长按天记录表 user_listening_log ==========
def create_user_listening_log():
    """创建用户听取时长按天记录表（近N天柱状图数据源）
    与 albums_{user_id}.listening_duration 记录同一秒数（防重复计数见 README P2 统计口径表）：
    该表仅用于「近N天听取时长」柱状图聚合，总时长仍以 albums 表 SUM 为准，两者不相加
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_listening_log (
                id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
                user_id INT NOT NULL COMMENT '用户ID（关联users表）',
                album_id INT NOT NULL COMMENT '专辑ID（关联用户专属专辑表/album_pool）',
                listen_date DATE NOT NULL COMMENT '收听日期（按天聚合）',
                duration_seconds FLOAT NOT NULL DEFAULT 0 COMMENT '当天累计收听秒数',
                UNIQUE KEY uniq_user_album_date (user_id, album_id, listen_date),
                INDEX idx_user_date (user_id, listen_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户听取时长按天记录表（v0.7 P2 统计柱状图数据源）';
        ''')
        db.commit()
        cursor.close()
        print("✅ user_listening_log表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建user_listening_log表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


# ========== ✅ v0.7.2：用户经验明细表 user_xp_log ==========
def create_user_xp_log():
    """创建用户经验明细表（v0.7.2 起，每次获得经验写一条：来源 + 数额 + 时间）

    与 users 表累计列（xp/listening_total/bonus_xp_today）【同事务写入、仅 amount>0 时写】，
    保证 SUM(user_xp_log) 与累计值严格一致、明细流无 +0 噪音；不回填历史（此前无记录）。
    - xp_type 枚举：listening（听歌 1秒=1XP）/ rating（评分 +5）/ review（听后感 +20）/ comment（评论 +10）
    - 索引 (user_id, created_at) 支撑「近7天按天聚合 + 最近明细流倒序」
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_xp_log (
                id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
                user_id INT NOT NULL COMMENT '用户ID（关联users表）',
                xp_type VARCHAR(20) NOT NULL COMMENT '经验来源：listening/rating/review/comment',
                amount FLOAT NOT NULL DEFAULT 0 COMMENT '本次实际获得经验（仅记录>0）',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '获得时间',
                INDEX idx_user_created (user_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户经验明细表（v0.7.2起，每次获得经验写一条）';
        ''')
        db.commit()
        cursor.close()
        print("✅ user_xp_log表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建user_xp_log表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_user_recommend():
    """创建用户推荐数据表，用于每日推荐 ✅修复外键名重复+打印文案错误"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
CREATE TABLE IF NOT EXISTS `user_recommend` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` INT NOT NULL COMMENT '用户ID，关联users表user_id',
  `recommend_daily_id` INT NOT NULL COMMENT '今日推荐专辑ID，关联album_pool表id',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user` (`user_id`) COMMENT '一个用户只存一条今日推荐数据',
  KEY `idx_recommend_daily_id` (`recommend_daily_id`),
  CONSTRAINT `fk_user_recommend_uid` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_user_recommend_aid` FOREIGN KEY (`recommend_daily_id`) REFERENCES `album_pool` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户每日推荐专辑表';
        ''')
        db.commit()
        cursor.close()
        print("✅ user_recommend 用户每日推荐表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建user_recommend表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_users():
    """创建用户表"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        # 1. 重构后的users表（原有逻辑保留）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户唯一标识',
                username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名（禁用%^&）',
                password VARCHAR(100) NOT NULL COMMENT '密码（bcrypt加密存储）',
                level INT DEFAULT 0 COMMENT '等级/经验',
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开户日期',
                last_login DATETIME COMMENT '最近登录时间',
                is_vip TINYINT DEFAULT 0 COMMENT '是否VIP（0=否，1=是）',
                is_admin TINYINT DEFAULT 0 COMMENT '是否管理员（0=否，1=是）',
                donate_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT '捐款数',
                album_count INT DEFAULT 0 COMMENT '收藏专辑数',
                avatar VARCHAR(255) DEFAULT '' COMMENT '用户头像URL（未上传为空串，前端回退首字母圆形头像）',
                token VARCHAR(100) DEFAULT "" COMMENT '登录令牌',
                xp FLOAT DEFAULT 0 COMMENT '经验（收听1秒=1XP + 评分/听后感/评论加分）',
                listening_total FLOAT DEFAULT 0 COMMENT '持久化听取总秒数（删专辑不掉，总时长口径）',
                bonus_date DATE NULL COMMENT '当日加分日期（跨天重置每日上限用）',
                bonus_xp_today FLOAT DEFAULT 0 COMMENT '当日已累计加分（每日上限100）'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表（重构版）';
        ''')
        db.commit()
        cursor.close()
        print("✅ users用户表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建users表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_album_pool():
    """创建用户表"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        # 2. album_pool表 ✅核心修改：my_score 改为 TEXT 类型 + 【删除DEFAULT默认值】解决1101错误
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_pool (
                id INT PRIMARY KEY AUTO_INCREMENT,
                album_name VARCHAR(100) NOT NULL,
                cover_img VARCHAR(255) DEFAULT "",
                singer VARCHAR(100) NOT NULL,
                release_year INT NOT NULL,
                main_type VARCHAR(50) DEFAULT "",
                tags TEXT,
                album_intro TEXT NULL COMMENT '专辑简介（支持长文本、分段、特殊符号）',
                tracks TEXT COMMENT '单曲列表（JSON字符串）',
                my_score TEXT COMMENT '单曲评分数组【JSON】：[8.0,9.5,7.8] ✅TEXT类型 无默认值',
                create_user INT NOT NULL COMMENT '创建用户ID',
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INT DEFAULT 1 COMMENT '模板版本号',
                update_log TEXT COMMENT '修改日志（JSON格式）',
                mp3_url VARCHAR(255) DEFAULT NULL COMMENT '整轨MP3访问地址',
                mp3_name VARCHAR(100) DEFAULT NULL COMMENT 'MP3原始文件名',
                mp3_duration INT DEFAULT 0 COMMENT '音频时长(秒)',
                INDEX idx_album_name (album_name),
                INDEX idx_singer (singer),
                INDEX idx_tags (tags(50)),
                INDEX idx_album_intro (album_intro(50)),
                INDEX idx_main_type (main_type),
                INDEX idx_tracks (tracks(50)),
                INDEX idx_version (version),
                INDEX idx_mp3_url (mp3_url)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑搜索池表（带版本管理 + tracks + album_intro + MP3音频）';
        ''')
        db.commit()
        cursor.close()
        print("✅ album_pool表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建album_pool表失败：{str(e)}")
        print(traceback.format_exc())
        raise e

def create_album_comments():
    """创建用户表"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        # 4. album_comments表 无需修改
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_comments (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '评论ID',
                album_id INT COMMENT '关联的专辑搜索池ID',
                user_id INT COMMENT '评论用户ID',
                username VARCHAR(50) NOT NULL COMMENT '评论用户名',
                content TEXT NOT NULL COMMENT '评论内容',
                create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
                like_count INT NOT NULL DEFAULT 0 COMMENT '点赞数',
                like_user_ids VARCHAR(255) DEFAULT '' COMMENT '点赞用户ID列表',
                FOREIGN KEY (album_id) REFERENCES album_pool(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                INDEX idx_album_id (album_id),
                INDEX idx_create_time (create_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑公共评论表';
        ''')
        db.commit()
        cursor.close()
        print("✅ album_comments表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建album_comments表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_album_tags():
    """创建专辑类型表（兼容MySQL所有版本：TEXT替代JSON，移除默认值）"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_tags (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '类型ID',
                tags_name VARCHAR(100) NOT NULL COMMENT '类型名（格式：English【中文】）',
                aka_name VARCHAR(500) DEFAULT '' COMMENT '别名（格式：别名1,别名2,别名3）',
                parameter_style TEXT COMMENT '样式参数（JSON字符串：{"type":0,"style":"a","param_b":"b","param_c":"c","param_d":"d","param_e":"e"}）',
                brief_intro VARCHAR(500) DEFAULT '' COMMENT '简洁介绍',
                detail_intro TEXT COMMENT '详细介绍',
                -- 核心修改：TEXT替代JSON，移除DEFAULT（后续代码层默认空数组）
                related_singers TEXT COMMENT '关联歌手（JSON字符串：[{"id":1,"name":"周杰伦"},{"id":2,"name":"陈奕迅"}]）',
                related_albums TEXT COMMENT '关联专辑（JSON字符串：[{"id":1,"name":"七里香"},{"id":2,"name":"U87"}]）',
                related_tags TEXT COMMENT '关联其他风格（JSON字符串：[{"id":3,"name":"Folk【民谣】"},{"id":4,"name":"Rock【摇滚】"}]）',
                parent_tag_ids VARCHAR(200) DEFAULT '' COMMENT '父标签ID（格式：1,2,3）',
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                is_enabled TINYINT UNSIGNED DEFAULT 1 COMMENT '是否启用：1-启用，0-禁用',
                UNIQUE INDEX idx_tags_name (tags_name),
                INDEX idx_parent_tag_ids (parent_tag_ids),
                INDEX idx_is_enabled (is_enabled)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT='专辑类型表';
        ''')
        db.commit()
        cursor.close()
        print("✅ album_tags表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建album_tags表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_album_singers():
    """创建歌手信息表（兼容MySQL所有版本：TEXT替代JSON，移除默认值）"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_singers (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '歌手ID',
                singer_name VARCHAR(100) NOT NULL COMMENT '歌手姓名（如：周杰伦）',
                birth_place VARCHAR(200) DEFAULT '' COMMENT '出生地（如：中国台湾省新北市）',
                singer_alias VARCHAR(500) DEFAULT '' COMMENT '别名（格式：别名1,别名2,别名3）',
                detail_intro TEXT COMMENT '详细介绍',
                -- 核心修改：TEXT替代JSON，移除DEFAULT
                related_singers TEXT COMMENT '介绍中关联歌手（JSON字符串：[{"id":1,"name":"陈奕迅"}]）',
                related_albums TEXT COMMENT '介绍中关联专辑（JSON字符串：[{"id":1,"name":"七里香"}]）',
                related_tags TEXT COMMENT '介绍中关联风格（JSON字符串：[{"id":1,"name":"Pop【流行】"}]）',
                display_singers TEXT COMMENT '展示用关联歌手（JSON字符串：[{"id":2,"name":"方文山"}]）',
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                is_enabled TINYINT UNSIGNED DEFAULT 1 COMMENT '是否启用：1-启用，0-禁用',
                UNIQUE INDEX idx_singer_name (singer_name),
                INDEX idx_is_enabled (is_enabled)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT='歌手信息表';
        ''')
        db.commit()
        cursor.close()
        print("✅ album_singers表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建album_singers表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_album_lyric():
    """创建专辑歌词表（兼容MySQL所有版本：TEXT替代JSON，移除默认值）"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
CREATE TABLE IF NOT EXISTS album_lyric (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    album_pool_id INT NOT NULL COMMENT '搜索池专辑ID',
    lyric_text TEXT NOT NULL COMMENT '歌词内容',
    lyric_translate TEXT NOT NULL COMMENT '翻译的歌词内容，比如{CN:text，EN:text这种}',
    create_user_id VARCHAR(50) NOT NULL COMMENT '创建用户ID',
    create_time DATETIME NOT NULL COMMENT '创建时间',
    update_time DATETIME NOT NULL COMMENT '更新时间',
    INDEX idx_album_pool_id (album_pool_id),
    INDEX idx_create_user (create_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑歌词表';
        ''')
        db.commit()
        cursor.close()
        print("✅ album_lyric表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建album_lyric表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def create_album_share():
    """创建专辑专题表（兼容MySQL所有版本：TEXT替代JSON，移除默认值）"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
CREATE TABLE IF NOT EXISTS album_share (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    album_pool_id INT NOT NULL COMMENT '搜索池专辑ID',
    share_text TEXT NOT NULL COMMENT '专辑分享主题',
    create_user_id VARCHAR(50) NOT NULL COMMENT '创建用户ID',
    create_time DATETIME NOT NULL COMMENT '创建时间',
    INDEX idx_album_pool_id (album_pool_id),
    INDEX idx_create_user (create_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑专题表';
        ''')
        db.commit()
        cursor.close()
        print("✅ album_share表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建album_share表失败：{str(e)}")
        print(traceback.format_exc())
        raise e

# ========== ✅ users表 avatar 列幂等迁移（v0.7 P0） ==========
def needs_avatar_column(existing_columns):
    """纯函数：判断 users 表是否需要新增 avatar 列（缺列→需迁移，已存在→幂等跳过）
    information_schema 列名大小写不敏感，统一转小写比较
    """
    return 'avatar' not in [c.lower() for c in existing_columns]


def ensure_users_avatar_column():
    """幂等迁移：users 表缺 avatar 列则 ALTER 新增（VARCHAR(255) 存图片URL，默认空串）
    查询 information_schema.columns 判断，缺列才 ALTER，重复启动不报错（复用 BookRate v0.4 已验证模式）
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
        ''', (MYSQL_CONFIG['db'],))
        columns = [row['COLUMN_NAME'] for row in cursor.fetchall()]
        if needs_avatar_column(columns):
            cursor.execute("ALTER TABLE users ADD COLUMN avatar VARCHAR(255) DEFAULT '' COMMENT '用户头像URL（未上传为空串，前端回退首字母圆形头像）'")
            db.commit()
            print("✅ users表 avatar 列迁移完成")
        else:
            print("✅ users表 avatar 列已存在，跳过迁移")
        cursor.close()
    except Exception as e:
        if db: db.rollback()
        print(f"❌ users表 avatar 列迁移失败：{str(e)}")
        traceback.print_exc()
        raise e


# ========== ✅ v0.7.1 P0：users 表等级经验四列幂等迁移 + 一次性回填 ==========
XP_COLUMNS = ['xp', 'listening_total', 'bonus_date', 'bonus_xp_today']


def needs_xp_columns(existing_columns):
    """纯函数：判断 users 表是否需要新增等级经验四列（缺任一列→需迁移，已齐全→幂等跳过）
    information_schema 列名大小写不敏感，统一转小写比较
    """
    lower = [c.lower() for c in existing_columns]
    return any(col not in lower for col in XP_COLUMNS)


def ensure_users_xp_columns():
    """幂等迁移：users 表缺等级经验四列则 ALTER 新增 + 一次性回填，重启不重复计数
    回填：xp = listening_total = SUM(albums_{user_id}.listening_duration)，level = compute_level(xp)
    （两列同源同累加，保证「经验 vs 统计」不打架；之后收听在 pause 时都 += play_seconds）
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
        ''', (MYSQL_CONFIG['db'],))
        columns = [row['COLUMN_NAME'] for row in cursor.fetchall()]
        if not needs_xp_columns(columns):
            cursor.close()
            print("✅ users表 等级经验列已存在，跳过迁移")
            return

        # 新增四列（bonus_date 用 DATE NULL 表达「当日加分日期为空 = 未加分」）
        cursor.execute("ALTER TABLE users ADD COLUMN xp FLOAT DEFAULT 0 COMMENT '经验（收听1秒=1XP + 加分）'")
        cursor.execute("ALTER TABLE users ADD COLUMN listening_total FLOAT DEFAULT 0 COMMENT '持久化听取总秒数（删专辑不掉）'")
        cursor.execute("ALTER TABLE users ADD COLUMN bonus_date DATE NULL COMMENT '当日加分日期（每日上限重置用）'")
        cursor.execute("ALTER TABLE users ADD COLUMN bonus_xp_today FLOAT DEFAULT 0 COMMENT '当日已累计加分（每日上限100）'")

        # 一次性回填：循环各用户专辑表 SUM(listening_duration)，两列同源；level 同步为推导值
        cursor.execute('SELECT user_id FROM users')
        user_ids = [row['user_id'] for row in cursor.fetchall()]
        for uid in user_ids:
            try:
                table_name = get_album_table_name(uid)
                cursor.execute(f'SELECT SUM(listening_duration) AS total FROM `{table_name}`')
                row = cursor.fetchone()
                total = float(row['total'] or 0) if row else 0.0
            except Exception:
                total = 0.0  # 用户专辑表不存在等异常容错，不中断迁移
            cursor.execute(
                'UPDATE users SET xp = %s, listening_total = %s, level = %s WHERE user_id = %s',
                (round(total, 1), round(total, 1), compute_level(total), uid)
            )

        db.commit()
        cursor.close()
        print("✅ users表 等级经验列迁移 + 回填完成")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ users表 等级经验列迁移失败：{str(e)}")
        traceback.print_exc()
        raise e


# ========== ✅ v0.8.1 P3：用户 AI 密钥配置表 ai_key ==========
def create_ai_key():
    """创建用户 AI 密钥配置表（个人中心「AI 配置」tab，镜像 BookRate）
    注意：MusicRate users.user_id 是 INT（BookRate 是 VARCHAR），此处对齐 INT
    - provider 枚举：deepseek（默认，国内直连）/ openai
    - api_key 明文存后端 DB，仅后端可见，绝不返回前端（安全铁律见 README v0.8.1）
    """
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
CREATE TABLE IF NOT EXISTS ai_key (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id INT NOT NULL COMMENT '用户ID（关联users表，MusicRate users 主键为 INT）',
    provider VARCHAR(20) NOT NULL DEFAULT 'deepseek' COMMENT 'AI服务商：deepseek/openai',
    api_key VARCHAR(200) NOT NULL COMMENT 'API密钥（仅后端可见，绝不返回前端）',
    is_enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用：1启用/0禁用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_user_id (user_id) COMMENT '用户ID唯一索引（一个用户一条配置）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户AI密钥配置表';
        ''')
        db.commit()
        cursor.close()
        print("✅ ai_key 用户AI密钥配置表 创建/检查成功！")
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 创建ai_key表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


# ========== ✅✅✅ 核心：初始化所有基础表 ==========
def init_base_tables():
    """初始化基础表"""
    try:
        # 初始化表

        create_album_comments()
        create_album_pool()
        create_users()
        # v0.7：users 表 avatar 列幂等迁移（旧库补列）
        ensure_users_avatar_column()
        # v0.7.1 P0：users 表等级经验四列幂等迁移 + 一次性回填（xp/listening_total/bonus_date/bonus_xp_today）
        ensure_users_xp_columns()
        create_user_album_intro_table()
        create_user_playlist_table()
        create_user_recommend()
        # v0.7 P2：按天听取记录表（统计柱状图数据源）
        create_user_listening_log()
        # v0.7.2：用户经验明细表（经验详情弹窗数据源）
        create_user_xp_log()

        create_album_tags()
        create_album_singers()

        create_album_lyric()
        create_album_share()

        # v0.8.1 P3：用户 AI 密钥配置表（个人中心「AI 配置」tab）
        create_ai_key()

        print("✅ MySQL基础表初始化成功！")
        init_default_admin()
    except Exception as e:
        print(f"❌ 初始化基础表失败：{str(e)}")
        print(traceback.format_exc())
        raise e

def init_default_admin():
    """初始化默认admin用户，并创建其专属专辑表"""
    db = None
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT user_id FROM users WHERE username = %s', (DEFAULT_ADMIN_USER,))
        user = cursor.fetchone()
        if not user:
            encrypted_pwd = encrypt_password(DEFAULT_ADMIN_PWD)
            cursor.execute('''
                INSERT INTO users (
                    username, password, token, is_admin, 
                    create_time, level, is_vip, donate_amount, album_count
                ) VALUES (%s, %s, "", 1, %s, 10, 1, 0.00, 0)
            ''', (DEFAULT_ADMIN_USER, encrypted_pwd, datetime.now()))
            admin_id = cursor.lastrowid
            db.commit()
            create_user_album_table(admin_id)
            print(f"✅ 默认admin用户创建成功（ID：{admin_id}）")
        else:
            check_and_create_user_album_table(user['user_id'])
            print(f"✅ 默认admin用户已存在（ID：{user['user_id']}），my_score字段已修复完成！")
        cursor.close()
    except Exception as e:
        if db: db.rollback()
        print(f"❌ 初始化admin用户失败：{str(e)}")
        print(traceback.format_exc())
        raise e


