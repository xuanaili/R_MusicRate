# MusicRate\backend\db_utils.py 数据库核心工具
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

# 以下代码保持不变...
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
    """初始化基础表（重构后的users + album_pool）"""
    try:
        db = get_db()
        cursor = db.cursor()
        # ========== 核心修改：重构users表结构 ==========
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

        # 2. 保留原有album_pool表结构（无需修改）
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
        print("✅ MySQL基础表（重构后users + album_pool）初始化成功！")

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
            # 为admin创建专属专辑表
            create_user_album_table(admin_id)
            print(f"✅ 默认admin用户创建成功（ID：{admin_id}），密码已加密，权限为管理员！")
        else:
            print(f"✅ 默认admin用户已存在（ID：{user['user_id']}），无需重复创建")
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