# 数据库核心工具 - 包含连接、分表、表初始化等功能
from flask import g
import pymysql
import traceback
from .config import MYSQL_CONFIG, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PWD

# 全局变量：当前登录用户ID（跨模块共享）
current_user_id = None


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
    return f'albums_{user_id}'


def create_user_album_table(user_id):
    """为新用户创建专属的专辑表"""
    try:
        db = get_db()
        cursor = db.cursor()
        table_name = get_album_table_name(user_id)
        # 移除TEXT字段的DEFAULT默认值（MySQL语法限制）
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        db.commit()
        cursor.close()
        print(f"✅ 为用户{user_id}创建专辑表{table_name}成功！")
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
        cursor.close()
    except Exception as e:
        print(f"❌ 检查/创建用户专辑表失败：{str(e)}")
        raise e


def init_base_tables():
    """初始化基础表（users + album_pool）"""
    try:
        db = get_db()
        cursor = db.cursor()
        # 1. 创建用户表（核心基础表，不分表）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(50) NOT NULL,
                token VARCHAR(100) DEFAULT "",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')

        # 2. 创建专辑搜索池表（解决TEXT索引长度问题）
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
                -- TEXT字段索引指定长度，VARCHAR字段直接索引
                INDEX idx_album_name (album_name),
                INDEX idx_singer (singer),
                INDEX idx_tags (tags(50)),
                INDEX idx_main_type (main_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑搜索池表';
        ''')

        db.commit()
        cursor.close()
        print("✅ MySQL基础表（users + album_pool）初始化成功！")

        # 初始化默认admin用户
        init_default_admin()
    except Exception as e:
        print(f"❌ 初始化基础表失败：{str(e)}")
        print(traceback.format_exc())
        raise e


def init_default_admin():
    """初始化默认admin用户，并创建其专属专辑表"""
    try:
        db = get_db()
        cursor = db.cursor()
        # 检查admin是否存在
        cursor.execute('SELECT id FROM users WHERE username = %s', (DEFAULT_ADMIN_USER,))
        user = cursor.fetchone()
        if not user:
            # 创建admin用户
            cursor.execute('''
                INSERT INTO users (username, password, token) 
                VALUES (%s, %s, "")
            ''', (DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PWD))
            admin_id = cursor.lastrowid
            db.commit()
            # 为admin创建专属专辑表
            create_user_album_table(admin_id)
            print(f"✅ 默认admin用户创建成功（ID：{admin_id}），并生成专属专辑表！")
        else:
            print(f"✅ 默认admin用户已存在（ID：{user['id']}），无需重复创建")
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