from flask import g
import pymysql
import traceback
import bcrypt  # 新增：用于密码加密，需先安装 pip install bcrypt
from datetime import datetime
from .config import MYSQL_CONFIG, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PWD


# ========== 新增：密码加密/验证工具函数 ==========
def encrypt_password(password: str) -> str:
    """密码加密（bcrypt）"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


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


# ========== 核心修改：✅ my_score 改为 TEXT 类型 【删除DEFAULT默认值】✅ 解决1101错误 ✅ 兼容历史数据 ==========
def create_user_album_table(user_id):
    """为新用户创建专属的专辑表
    tracks: TEXT 存储【单曲名称数组】JSON字符串 如 ["曲目1","曲目2"]
    tracks_time: TEXT 存储【对应单曲时间戳数组】JSON字符串 如 [120,240,360]
    my_score: TEXT 存储【单曲评分数组】JSON字符串 如 [8.0,9.5,7.8,0,0] ✅核心修改：无默认值，解决1101
    favourite_tracks: TEXT 收藏曲目名称数组
    favourite_tracks_time: TEXT 收藏曲目对应秒数数组
    所有数组一一对应、索引一致、永久保存
    """
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
                tracks TEXT COMMENT '单曲列表【数组JSON】：[\'曲目1\',\'曲目2\',\'曲目3\']',
                review TEXT,
                score FLOAT DEFAULT 0.0,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_pool_id INT NULL COMMENT '来源公共模板ID',
                sync_pool_update TINYINT DEFAULT 1 COMMENT '是否同步模板更新（1=开启，0=关闭）',
                is_customized TINYINT DEFAULT 0 COMMENT '是否用户自定义修改（1=是，0=否）',
                tracks_time TEXT NULL COMMENT '单曲对应编辑时间戳【数组JSON】：[120,240,360]，与tracks数组索引一一匹配',
                favourite_tracks TEXT NULL COMMENT '收藏曲目列表【数组JSON】：[\'收藏曲目1\',\'收藏曲目2\']',
                favourite_tracks_time TEXT NULL COMMENT '收藏曲目对应秒数【数组JSON】：[120,240,360]，与favourite_tracks数组索引一一匹配',
                listening_duration FLOAT DEFAULT 0.0 COMMENT '专辑累计播放时长(秒) 精准统计'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        db.commit()
        cursor.close()
        print(f"✅ 为用户{user_id}创建专辑表{table_name}成功！my_score为TEXT数组格式+无默认值，解决1101错误")
    except Exception as e:
        print(f"❌ 创建用户专辑表失败：{str(e)}")
        raise e


def check_and_create_user_album_table(user_id):
    """检查用户专辑表是否存在，不存在则创建 + 补充缺失字段
    ✅ 核心修复1：my_score 字段 无DEFAULT默认值，解决1101语法错误
    ✅ 核心修复2：自动将老用户的 my_score FLOAT 字段 → TEXT 字段，并迁移历史评分数据为数组格式
    ✅ 自动补充tracks_time、listening_duration、收藏字段等所有缺失字段
    """
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
            # ========== ✅ 重中之重：修复 my_score 字段【FLOAT → TEXT】+ 数据迁移 无默认值 ==========
            cursor.execute(f'''
                SELECT COLUMN_TYPE FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'my_score'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result and result['COLUMN_TYPE'] in ['float', 'double']:
                # 1. 先把历史FLOAT类型的评分，转为数组格式的字符串（如 8.5 → "[8.5]"）
                cursor.execute(f'UPDATE `{table_name}` SET my_score = CONCAT("[", my_score, "]") WHERE my_score IS NOT NULL AND my_score != ""')
                # 2. 修改字段类型：FLOAT → TEXT，【删除默认值】，完美兼容，解决1101
                cursor.execute(f'''
                    ALTER TABLE `{table_name}` 
                    MODIFY COLUMN my_score TEXT COMMENT '单曲评分数组【JSON】：[8.0,9.5,7.8,0] 与tracks一一对应 ✅TEXT类型 无默认值'
                ''')
                print(f"✅ 为用户{user_id}的专辑表{table_name}修复my_score字段：FLOAT→TEXT，历史评分已转为数组格式！解决1101错误")

            # ========== 原有字段补充逻辑（全部保留，无任何删减） ==========
            # 1. 检查并添加album_intro字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'album_intro'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN album_intro TEXT NULL COMMENT "专辑简介（支持长文本、分段、特殊符号）" AFTER mandopop_code')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充album_intro字段")

            # 2. 检查并添加tracks字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'tracks'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN tracks TEXT COMMENT "单曲列表【数组JSON】：[\'曲目1\',\'曲目2\']" AFTER album_intro')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充tracks字段")

            # 3. 检查并添加source_pool_id字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'source_pool_id'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN source_pool_id INT NULL COMMENT "来源公共模板ID" AFTER created_at')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充source_pool_id字段")

            # 4. 检查并添加sync_pool_update字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'sync_pool_update'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN sync_pool_update TINYINT DEFAULT 1 COMMENT "是否同步模板更新（1=开启，0=关闭）" AFTER source_pool_id')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充sync_pool_update字段")

            # 5. 检查并添加is_customized字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'is_customized'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN is_customized TINYINT DEFAULT 0 COMMENT "是否用户自定义修改（1=是，0=否）" AFTER sync_pool_update')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充is_customized字段")

            # ✅ 补充 tracks_time 字段【TEXT类型】
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'tracks_time'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN tracks_time TEXT NULL COMMENT "单曲对应编辑时间戳【数组JSON】：[120,240,360]，与tracks数组索引一一匹配" AFTER is_customized')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充 tracks_time 字段【数组格式】")

            # ✅ 补充 listening_duration 播放时长统计字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'listening_duration'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN listening_duration FLOAT DEFAULT 0.0 COMMENT "专辑累计播放时长(秒) 精准统计" AFTER tracks_time')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充 listening_duration 播放时长字段")

            # ✅ 收藏曲目相关2个核心字段
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'favourite_tracks'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN favourite_tracks TEXT NULL COMMENT "收藏曲目列表【数组JSON】：[\'收藏曲目1\',\'收藏曲目2\']" AFTER listening_duration')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充 favourite_tracks 收藏曲目字段【数组格式】")

            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'favourite_tracks_time'
            ''', (MYSQL_CONFIG['db'], table_name))
            result = cursor.fetchone()
            if result['count'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN favourite_tracks_time TEXT NULL COMMENT "收藏曲目对应秒数【数组JSON】：[120,240,360]，与favourite_tracks数组索引一一匹配" AFTER favourite_tracks')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充 favourite_tracks_time 收藏时间戳字段【数组格式】")

            db.commit()
        cursor.close()
    except Exception as e:
        print(f"❌ 检查/创建用户专辑表失败：{str(e)}")
        raise e


# ========== 新增：创建用户-专辑专属简介表 ==========
def create_user_album_intro_table():
    """创建用户-专辑专属简介表（核心：关联user_id + album_id，存储用户自定义简介）"""
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
        print(f"❌ 创建user_album_intro表失败：{str(e)}")
        print(traceback.format_exc())
        raise e

# ========== ✅✅✅ 新增：创建用户播放列表表 user_playlist ✅✅✅
def create_user_playlist_table():
    """创建用户播放列表数据表【核心】- 匹配playlist.py接口需求"""
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
        print(f"❌ 创建user_playlist表失败：{str(e)}")
        print(traceback.format_exc())
        raise e
def create_user_recommend():
    """创建用户推荐数据表，用于每日推荐"""
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
  KEY `fk_recommend_album` (`recommend_daily_id`),
  CONSTRAINT `fk_recommend_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_recommend_album` FOREIGN KEY (`recommend_daily_id`) REFERENCES `album_pool` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户每日推荐专辑表';
        ''')
        db.commit()
        cursor.close()
        print("✅ user_recommend 用户播放列表表 创建/检查成功！")
    except Exception as e:
        print(f"❌ 创建user_recommend表失败：{str(e)}")
        print(traceback.format_exc())
        raise e
# ========== 核心：初始化所有基础表 【✅已整合所有修复+无报错✅】 ==========
def init_base_tables():
    """初始化基础表（album_pool/album_pool_history 同步修复my_score字段类型，删除默认值，解决1101错误）"""
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
                token VARCHAR(100) DEFAULT "" COMMENT '登录令牌'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表（重构版）';
        ''')

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

        # 3. album_pool_history ✅同步修改my_score为TEXT + 【删除DEFAULT默认值】解决1101错误
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_pool_history (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '历史记录ID',
                pool_id INT COMMENT '关联的模板主ID',
                version INT COMMENT '模板版本号',
                album_name VARCHAR(100) NOT NULL COMMENT '历史专辑名',
                singer VARCHAR(100) NOT NULL COMMENT '历史歌手',
                cover_img VARCHAR(255) DEFAULT "" COMMENT '历史封面',
                release_year INT NOT NULL COMMENT '历史发行年份',
                main_type VARCHAR(50) DEFAULT "" COMMENT '历史主类型',
                tags TEXT COMMENT '历史标签',
                album_intro TEXT NULL COMMENT '历史专辑简介',
                tracks TEXT COMMENT '历史单曲列表',
                my_score TEXT COMMENT '历史单曲评分数组【JSON】 ✅TEXT类型 无默认值',
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '版本更新时间',
                INDEX idx_pool_version (pool_id, version),
                INDEX idx_update_time (update_time),
                INDEX idx_album_intro (album_intro(50)),
                INDEX idx_tracks (tracks(50))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公共专辑模板历史版本表（含tracks + album_intro）';
        ''')

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

        # ========== ✅ 公共表补充字段+修复my_score字段类型【无默认值】 ==========
        # 补充album_pool缺失的tracks/album_intro/音频字段
        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool' AND COLUMN_NAME = 'album_intro'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute('''
                ALTER TABLE album_pool 
                ADD COLUMN album_intro TEXT NULL COMMENT '专辑简介（支持长文本、分段、特殊符号）' 
                AFTER tags
            ''')
            print("✅ 为已有album_pool表补充album_intro字段")

        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool' AND COLUMN_NAME = 'tracks'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute('''
                ALTER TABLE album_pool 
                ADD COLUMN tracks TEXT COMMENT '单曲列表（JSON字符串）' 
                AFTER album_intro
            ''')
            print("✅ 为已有album_pool表补充tracks字段")

        # ✅ 修复album_pool的my_score字段：FLOAT→TEXT 【无默认值】解决1101
        cursor.execute(f'''
            SELECT COLUMN_TYPE FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool' AND COLUMN_NAME = 'my_score'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result and result['COLUMN_TYPE'] in ['float', 'double']:
            cursor.execute(f'UPDATE album_pool SET my_score = CONCAT("[", my_score, "]") WHERE my_score IS NOT NULL AND my_score != ""')
            cursor.execute(f'''
                ALTER TABLE album_pool 
                MODIFY COLUMN my_score TEXT COMMENT '单曲评分数组【JSON】：[8.0,9.5,7.8] ✅TEXT类型 无默认值'
            ''')
            print("✅ 修复album_pool表my_score字段：FLOAT→TEXT，历史评分已转为数组！解决1101错误")

        # 补充音频字段
        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool' AND COLUMN_NAME = 'mp3_url'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute(
                'ALTER TABLE album_pool ADD COLUMN mp3_url VARCHAR(255) DEFAULT NULL COMMENT "整轨MP3访问地址" AFTER update_log')
            print("✅ 为已有album_pool表补充mp3_url字段")

        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool' AND COLUMN_NAME = 'mp3_name'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute(
                'ALTER TABLE album_pool ADD COLUMN mp3_name VARCHAR(100) DEFAULT NULL COMMENT "MP3原始文件名" AFTER mp3_url')
            print("✅ 为已有album_pool表补充mp3_name字段")

        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool' AND COLUMN_NAME = 'mp3_duration'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute(
                'ALTER TABLE album_pool ADD COLUMN mp3_duration INT DEFAULT 0 COMMENT "音频时长(秒)" AFTER mp3_name')
            print("✅ 为已有album_pool表补充mp3_duration字段")

        # 补充album_pool_history缺失的tracks/album_intro字段 + 修复my_score【无默认值】
        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool_history' AND COLUMN_NAME = 'album_intro'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute('''
                ALTER TABLE album_pool_history 
                ADD COLUMN album_intro TEXT NULL COMMENT '历史专辑简介' 
                AFTER tags
            ''')
            print("✅ 为已有album_pool_history表补充album_intro字段")

        cursor.execute('''
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool_history' AND COLUMN_NAME = 'tracks'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result['count'] == 0:
            cursor.execute('''
                ALTER TABLE album_pool_history 
                ADD COLUMN tracks TEXT COMMENT '历史单曲列表' 
                AFTER album_intro
            ''')
            print("✅ 为已有album_pool_history表补充tracks字段")

        # ✅ 修复album_pool_history的my_score字段：FLOAT→TEXT 【无默认值】解决1101
        cursor.execute(f'''
            SELECT COLUMN_TYPE FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'album_pool_history' AND COLUMN_NAME = 'my_score'
        ''', (MYSQL_CONFIG['db'],))
        result = cursor.fetchone()
        if result and result['COLUMN_TYPE'] in ['float', 'double']:
            cursor.execute(f'UPDATE album_pool_history SET my_score = CONCAT("[", my_score, "]") WHERE my_score IS NOT NULL AND my_score != ""')
            cursor.execute(f'''
                ALTER TABLE album_pool_history 
                MODIFY COLUMN my_score TEXT COMMENT '历史单曲评分数组【JSON】 ✅TEXT类型 无默认值'
            ''')
            print("✅ 修复album_pool_history表my_score字段：FLOAT→TEXT，历史评分已转为数组！解决1101错误")

        db.commit()
        cursor.close()
        # 初始化其他关联表
        create_user_album_intro_table()
        create_user_playlist_table()

        create_user_recommend()


        print("✅ MySQL基础表初始化成功！彻底解决 1265截断错误 + 1101默认值错误，所有功能正常！")
        init_default_admin()
    except Exception as e:
        print(f"❌ 初始化基础表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def init_default_admin():
    """初始化默认admin用户，并创建其专属专辑表"""
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
        print(f"❌ 初始化admin用户失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def get_next_id(table_name):
    """获取指定表的下一个自增ID"""
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


# ========== 用户专辑简介的增删改查函数 ==========
def save_user_album_intro(user_id, album_id, intro_content):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT id FROM user_album_intro WHERE user_id = %s AND album_id = %s
        ''', (user_id, album_id))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE user_album_intro 
                SET album_intro = %s 
                WHERE user_id = %s AND album_id = %s
            ''', (intro_content, user_id, album_id))
        else:
            cursor.execute('''
                INSERT INTO user_album_intro (user_id, album_id, album_intro) 
                VALUES (%s, %s, %s)
            ''', (user_id, album_id, intro_content))
        db.commit()
        cursor.close()
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ 保存用户专辑简介失败：{str(e)}")
        return False


def get_user_album_intro(user_id, album_id):
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT album_intro FROM user_album_intro 
            WHERE user_id = %s AND album_id = %s
        ''', (user_id, album_id))
        result = cursor.fetchone()
        cursor.close()
        return result['album_intro'] if result else ""
    except Exception as e:
        print(f"❌ 获取用户专辑简介失败：{str(e)}")
        return ""