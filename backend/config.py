# MusicRate\backend\config.py 全局配置文件 - 包含所有基础配置项
import os
import re
import socket
import pymysql
# ================= Flask 基础配置 =================
SECRET_KEY = 'albumDetail-rate-secret-key'
DEBUG = True
PORT = 5000
FRONTEND_PORT = 8080  # 前端 npm run serve 端口（仅工具脚本拼 CORS 来源时用）


def detect_local_ip():
    """自动识别本机当前局域网 IPv4（UDP connect 技巧，不实际发包），失败回退 localhost

    为什么不再写死 HOST：封面/音频地址（COVER_BASE_URL / AUDIO_BASE_URL）都拼在 HOST 上，
    写死 localhost 时，手机通过局域网访问会拿到 http://localhost:5000/... → 指向手机自己，
    封面全裂、音频放不出来。自动探测可以保证新上传的文件地址始终与当前局域网一致。
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        sock.connect(('8.8.8.8', 80))  # 只用于让系统选出口网卡，不发包
        ip = sock.getsockname()[0]
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip) and not ip.startswith('127.'):
            return ip
    except OSError:
        pass
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
    return 'localhost'


# 优先级：环境变量 MUSICRATE_HOST > backend/data/lan_host.txt（由域名切换工具写入）> 自动探测当前局域网 IP > localhost
# 想强制用某个地址（如反向代理域名）时：set MUSICRATE_HOST=example.com 再启动后端
LAN_HOST_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', 'data', 'lan_host.txt'
)


def read_preferred_host():
    """读取工具选定的后端地址（首行），没有/读不到返回 None"""
    try:
        with open(LAN_HOST_FILE, 'r', encoding='utf-8') as f:
            return f.readline().strip() or None
    except (IOError, OSError):
        return None


HOST = os.environ.get('MUSICRATE_HOST', '').strip() or read_preferred_host() or detect_local_ip()

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

DB_URL='http://localhost:5000/tracks/1111'
    # 'http://192.168.0.105:5000/'



# ================= 本地图床配置 - 专辑封面 =================
# 图片保存路径（自动创建文件夹）
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/album_covers")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# 图片访问基础URL
COVER_BASE_URL = f"http://{HOST}:{PORT}/covers/"

# ================= 本地图床配置 - 专辑封面缩略图 =================
# 缩略图保存路径（自动创建文件夹） - 列表页小图专用，避免下载几MB原图
COVER_THUMB_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/album_covers_thumb")
if not os.path.exists(COVER_THUMB_UPLOAD_FOLDER):
    os.makedirs(COVER_THUMB_UPLOAD_FOLDER)
# 缩略图访问基础URL
COVER_THUMB_BASE_URL = f"http://{HOST}:{PORT}/covers_thumb/"

# ================= 本地音频配置 - 专辑整轨MP3 (你要修改的存歌地址 在这里改！) =================
# MP3保存路径 自动创建 album_track 文件夹
AUDIO_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/data/album_track")
if not os.path.exists(AUDIO_UPLOAD_FOLDER):
    os.makedirs(AUDIO_UPLOAD_FOLDER)
# MP3访问基础URL
AUDIO_BASE_URL = f"http://{HOST}:{PORT}/tracks/"

# ================= 常量配置 =================
# ================= 常量配置 =================

# ================= v0.8.1：DeepSeek 歌词校正（服务器端，仅管理员识别用） =================
# 管理员 AI 歌词识别产出的草稿，若配置本 key 则调用 DeepSeek 校正（difflib 保时间戳只改文字）
# 与个人用户 AI key（ai_key 表，P3）分离两套；留空则识别直接落 whisper 草稿
# key 存于 gitignore 的 backend/data/deepseek_api_key.txt（首行），不入库
DEEPSEEK_API_KEY = ''
try:
    _key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend/data/deepseek_api_key.txt')
    with open(_key_file, 'r', encoding='utf-8') as _f:
        DEEPSEEK_API_KEY = _f.readline().strip()
except (IOError, OSError):
    pass

# ================= 分页默认值 =================
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
# 排序字段白名单
VALID_SORT_FIELDS = ['album_name', 'release_year', 'singer', 'my_score','created_at' ]
# 默认管理员账号
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PWD = "123456"

# ================= NCM解密配置（新增） =================
# NCM临时上传目录（存放前端上传的NCM文件）
import tempfile
from pathlib import Path
# 基于项目目录创建ncm_temp文件夹
NCM_UPLOAD_TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "backend/data/ncm_temp"
)
# 自动创建目录
if not os.path.exists(NCM_UPLOAD_TEMP_DIR):
    os.makedirs(NCM_UPLOAD_TEMP_DIR)

# NCM解密后MP3临时目录（也可复用AUDIO_UPLOAD_FOLDER）
NCM_DECRYPT_TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "backend/data/ncm_decrypt_temp"
)
if not os.path.exists(NCM_DECRYPT_TEMP_DIR):
    os.makedirs(NCM_DECRYPT_TEMP_DIR)

# NCM文件大小限制（200MB）
NCM_MAX_FILE_SIZE = 200 * 1024 * 1024
# 临时文件过期时间（小时）
NCM_TEMP_FILE_EXPIRE_HOURS = 24






