from flask import g
import pymysql
import traceback
import bcrypt  # 新增：用于密码加密，需先安装 pip install bcrypt
from datetime import datetime
from .config import MYSQL_CONFIG, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PWD


# 移除模块级别的 current_user_id 变量
# current_user_id = None

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


# ========== 核心修改：更新用户专辑表结构（新增同步相关字段） ==========
def create_user_album_table(user_id):
    """为新用户创建专属的专辑表（新增同步开关、自定义标记、来源模板ID字段）"""
    try:
        db = get_db()
        cursor = db.cursor()
        table_name = get_album_table_name(user_id)
        # 移除TEXT字段的DEFAULT默认值（MySQL语法限制）
        # 新增：sync_pool_update（同步开关）、is_customized（自定义标记）、source_pool_id（来源模板ID）
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
                my_score FLOAT DEFAULT 0.0,
                burn_class VARCHAR(50) DEFAULT "",
                duration_type VARCHAR(50) DEFAULT "",
                tags TEXT,  -- TEXT字段不设默认值
                main_type TEXT,
                code VARCHAR(50) DEFAULT "",
                video_shared VARCHAR(50) DEFAULT "",
                mandopop_code VARCHAR(50) DEFAULT "",
                tracks TEXT,
                review TEXT,
                score FLOAT DEFAULT 0.0,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- ========== 核心新增：同步相关字段 ==========
                source_pool_id INT NULL COMMENT '来源公共模板ID',
                sync_pool_update TINYINT DEFAULT 1 COMMENT '是否同步模板更新（1=开启，0=关闭）',
                is_customized TINYINT DEFAULT 0 COMMENT '是否用户自定义修改（1=是，0=否）'
                -- ========== 新增字段结束 ==========
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        db.commit()
        cursor.close()
        print(f"✅ 为用户{user_id}创建专辑表{table_name}成功！已包含同步相关字段")
    except Exception as e:
        print(f"❌ 创建用户专辑表失败：{str(e)}")
        raise e


def check_and_create_user_album_table(user_id):
    """检查用户专辑表是否存在，不存在则创建"""
    try:
        db = get_db()
        cursor = db.cursor()
        table_name = get_album_table_name(user_id)
        # 检查表是否存在
        cursor.execute(f'''
            SELECT COUNT(*) FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ''', (MYSQL_CONFIG['db'], table_name))
        table_exists = cursor.fetchone()['COUNT(*)'] > 0

        if not table_exists:
            create_user_album_table(user_id)
        else:
            # ========== 核心新增：为已有用户表补充同步字段 ==========
            # 检查并添加source_pool_id字段
            cursor.execute(f'''
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'source_pool_id'
            ''', (MYSQL_CONFIG['db'], table_name))
            if cursor.fetchone()['COUNT(*)'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN source_pool_id INT NULL COMMENT "来源公共模板ID" AFTER created_at')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充source_pool_id字段")

            # 检查并添加sync_pool_update字段
            cursor.execute(f'''
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'sync_pool_update'
            ''', (MYSQL_CONFIG['db'], table_name))
            if cursor.fetchone()['COUNT(*)'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN sync_pool_update TINYINT DEFAULT 1 COMMENT "是否同步模板更新（1=开启，0=关闭）" AFTER source_pool_id')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充sync_pool_update字段")

            # 检查并添加is_customized字段
            cursor.execute(f'''
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'is_customized'
            ''', (MYSQL_CONFIG['db'], table_name))
            if cursor.fetchone()['COUNT(*)'] == 0:
                cursor.execute(
                    f'ALTER TABLE `{table_name}` ADD COLUMN is_customized TINYINT DEFAULT 0 COMMENT "是否用户自定义修改（1=是，0=否）" AFTER sync_pool_update')
                print(f"✅ 为用户{user_id}的专辑表{table_name}补充is_customized字段")

            db.commit()
        cursor.close()
    except Exception as e:
        print(f"❌ 检查/创建用户专辑表失败：{str(e)}")
        raise e


def init_base_tables():
    """初始化基础表（重构后的users + album_pool + album_comments + 新增模板历史表）"""
    try:
        db = get_db()
        cursor = db.cursor()
        # ========== 1. 重构后的users表（原有逻辑保留） ==========
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
                token VARCHAR(100) DEFAULT "" COMMENT '登录令牌'  -- 保留原有token字段，兼容旧逻辑
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表（重构版）';
        ''')

        # ========== 2. 升级后的album_pool表（新增版本号、修改日志字段） ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_pool (
                id INT PRIMARY KEY AUTO_INCREMENT,
                album_name VARCHAR(100) NOT NULL,
                cover_img VARCHAR(255) DEFAULT "",
                singer VARCHAR(100) NOT NULL,
                release_year INT NOT NULL,
                main_type VARCHAR(50) DEFAULT "",  # 改VARCHAR更适合短文本
                tags TEXT,
                my_score FLOAT DEFAULT 0.0,
                create_user INT NOT NULL COMMENT '创建用户ID',
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- ========== 核心新增：模板版本管理字段 ==========
                version INT DEFAULT 1 COMMENT '模板版本号',
                update_log TEXT COMMENT '修改日志（JSON格式）',
                -- ========== 新增字段结束 ==========
                -- TEXT字段索引指定长度，VARCHAR字段直接索引
                INDEX idx_album_name (album_name),
                INDEX idx_singer (singer),
                INDEX idx_tags (tags(50)),
                INDEX idx_main_type (main_type),
                INDEX idx_version (version)  -- 新增版本号索引
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑搜索池表（带版本管理）';
        ''')

        # ========== 3. 新增：album_pool_history 模板历史版本表 ==========
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
                my_score FLOAT DEFAULT 0.0 COMMENT '历史评分',
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '版本更新时间',
                -- 索引优化
                INDEX idx_pool_version (pool_id, version),
                INDEX idx_update_time (update_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公共专辑模板历史版本表';
        ''')

        # ========== 4. 原有album_comments表（无需修改） ==========
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
                -- 恢复外键约束
                FOREIGN KEY (album_id) REFERENCES album_pool(id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                INDEX idx_album_id (album_id),
                INDEX idx_create_time (create_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑公共评论表';
        ''')

        db.commit()
        cursor.close()
        print("✅ MySQL基础表初始化成功！包含：")
        print("  - 重构后users表")
        print("  - 带版本管理的album_pool表")
        print("  - album_pool_history模板历史表")
        print("  - album_comments公共评论表")

        # 初始化默认admin用户（适配新表结构）
        init_default_admin()
    except Exception as e:
        print(f"❌ 初始化基础表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def init_default_admin():
    """初始化默认admin用户（适配新表结构），并创建其专属专辑表"""
    try:
        db = get_db()
        cursor = db.cursor()
        # 检查admin是否存在
        cursor.execute('SELECT user_id FROM users WHERE username = %s', (DEFAULT_ADMIN_USER,))
        user = cursor.fetchone()
        if not user:
            # 创建admin用户（适配新表结构：密码加密、设置管理员权限）
            encrypted_pwd = encrypt_password(DEFAULT_ADMIN_PWD)  # 密码加密存储
            cursor.execute('''
                INSERT INTO users (
                    username, password, token, is_admin, 
                    create_time, level, is_vip, donate_amount, album_count
                ) VALUES (%s, %s, "", 1, %s, 10, 1, 0.00, 0)
            ''', (DEFAULT_ADMIN_USER, encrypted_pwd, datetime.now()))
            admin_id = cursor.lastrowid
            db.commit()
            # 为admin创建专属专辑表（包含同步字段）
            create_user_album_table(admin_id)
            print(f"✅ 默认admin用户创建成功（ID：{admin_id}），密码已加密，权限为管理员！")
        else:
            # 为已有admin用户检查并创建专辑表（补充同步字段）
            check_and_create_user_album_table(user['user_id'])
            print(f"✅ 默认admin用户已存在（ID：{user['user_id']}），已检查并补充专辑表同步字段")
        cursor.close()
    except Exception as e:
        print(f"❌ 初始化admin用户失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def get_next_id(table_name):
    """获取指定表的下一个自增ID"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'SELECT MAX(id) FROM `{table_name}`')
        max_id = cursor.fetchone()["MAX(id)"]
        cursor.close()
        return 1 if max_id is None else max_id + 1
    except Exception as e:
        print(f"❌ 生成ID失败：{str(e)}")
        return 1