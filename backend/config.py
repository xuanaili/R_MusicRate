# MusicRate\backend\config.py 全局配置文件 - 包含所有基础配置项
import os
import pymysql

# ================= Flask 基础配置 =================
SECRET_KEY = 'music-rate-secret-key'
DEBUG = True
HOST = '127.0.0.1'
PORT = 5000

# ================= MySQL 数据库配置 =================
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'music_user',
    'password': '123456',  # 请替换为你的实际密码
    'db': 'music_rate',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor  # 默认返回字典格式
}

# ================= 本地图床配置 =================
# 图片保存路径（自动创建文件夹）
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/album_covers")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# 图片访问基础URL
COVER_BASE_URL = f"http://{HOST}:{PORT}/covers/"

# ================= 常量配置 =================
# 分页默认值
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
# 排序字段白名单
VALID_SORT_FIELDS = ['album_name', 'release_year', 'singer', 'my_score']
# 默认管理员账号
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PWD = "123456"