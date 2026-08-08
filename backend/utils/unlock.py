from pathlib import Path
import logging
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TRCK, ID3NoHeaderError
from flask import request, jsonify, Blueprint
import json
import traceback
import os
import re
import tempfile
import shutil
from mutagen.easyid3 import EasyID3
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
import subprocess
import uuid
import pymysql
import warnings

# ✅ 修复：在导入pydub之前，先将ffmpeg目录加入系统PATH
# 这样pydub在import时就能找到ffmpeg，不会报"Couldn't find ffmpeg"警告
current_dir = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.abspath(os.path.join(current_dir, '..', '..', 'portable', 'ffmpeg', 'ffmpeg.exe'))
FFPROBE_PATH = os.path.abspath(os.path.join(current_dir, '..', '..', 'portable', 'ffmpeg', 'ffprobe.exe'))

ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
if ffmpeg_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')

from pydub import AudioSegment

# 强制设置pydub的FFmpeg/ffprobe路径（双保险）
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

# 导入配置（确保路径正确）
from backend.config import UPLOAD_FOLDER, COVER_BASE_URL, AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER, MYSQL_CONFIG

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 允许的音频格式
ALLOWED_EXTENSIONS = {'mp3', 'ogg', 'flac', 'wav', 'm4a', 'mp4'}

def ensure_dir_exists(dir_path: str | Path) -> bool:
    """确保目录存在，不存在则创建"""
    try:
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {dir_path}: {str(e)}")
        return False


def get_ffmpeg_exe():
    """获取有效的FFmpeg可执行文件路径"""
    global FFMPEG_PATH
    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        return FFMPEG_PATH

    # 检查常见路径
    possible_paths = [
        r"portable/ffmpeg/ffmpeg.exe",
        r"U:\project\python\AudioConnect\tools\ffmpeg\ffmpeg.exe",
        r"G:\project\python\AudioConnect\ffmpeg\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        "ffmpeg.exe"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            FFMPEG_PATH = path
            return path

    raise FileNotFoundError("未找到FFmpeg可执行文件！")


# ✅ 新增：简单的序号生成函数（统计文件数+1）
def get_simple_album_id():
    """
    统计album_track目录下的文件数量，返回 数量+1 作为序号
    （如果目录不存在则返回1）
    """
    # 定义album_track目录路径（根据你的实际路径调整）
    album_track_dir = AUDIO_UPLOAD_FOLDER  # 假设音频都存在这个目录下
    try:
        # 确保目录存在
        if not os.path.exists(album_track_dir):
            os.makedirs(album_track_dir)
            return 1

        # 统计目录下的所有文件（排除子目录）
        file_count = 0
        for item in os.listdir(album_track_dir):
            item_path = os.path.join(album_track_dir, item)
            if os.path.isfile(item_path):
                file_count += 1

        # 返回 数量+1 作为新序号
        return file_count + 1
    except Exception as e:
        print(f"统计文件数量失败：{e}")
        # 失败时返回随机数保底
        return int(uuid.uuid4().hex[:8], 16) % 10000 + 1


def allowed_file(filename):
    """检查文件格式是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_duration(seconds):
    """格式化时长为 时:分:秒"""
    if not seconds or seconds < 0:
        return '0:00:00'
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


def get_duration_with_ffprobe(file_path):
    """使用ffprobe提取音频时长（备用方案）- 修复路径问题"""
    if not os.path.exists(file_path):
        print(f"文件不存在：{file_path}")
        return 0

    try:
        # 修复：使用原始字符串和正确的编码处理
        cmd = [
            FFPROBE_PATH,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path.encode('utf-8').decode('utf-8')  # 处理特殊字符路径
        ]
        # 修复：使用shell=False + 正确的编码
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            shell=False  # 关键：Windows下禁用shell
        )
        duration_str = result.stdout.strip()
        if duration_str:
            duration = float(duration_str)
            return duration
        return 0
    except Exception as e:
        print(f"ffprobe提取时长失败: {e}")
        return 0

def add_mp3_metadata(mp3_file: Path, metadata: dict):
    """为MP3文件添加元数据"""
    try:
        try:
            audio = ID3(mp3_file)
        except ID3NoHeaderError:
            audio = ID3()

        audio.delete()
        audio.add(TIT2(encoding=3, text=metadata["title"]))
        audio.add(TPE1(encoding=3, text=metadata["artist"]))
        audio.add(TALB(encoding=3, text=metadata["album"]))

        # 添加封面
        if metadata.get("cover"):
            audio.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=metadata["cover"]
            ))

        audio.save(mp3_file, v2_version=4)
    except Exception as e:
        logger.warning(f"添加MP3元数据失败: {str(e)}")

def get_audio_metadata(file_path, file_ext):
    """提取音频文件元数据（优化封面提取）"""
    metadata = {
        'title': '',
        'artist': '',
        'album': '',
        'track': '',
        'cover_img': '',
        'duration': 0,
        'year': '2024'  # 新增：默认年份
    }

    try:
        # 先检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在：{file_path}")
            return metadata

        # 提取元数据
        if file_ext == 'mp3':
            audio = EasyID3(file_path)
            # 提取年份
            metadata['year'] = audio.get('date', ['2024'])[0] or '2024'
        elif file_ext == 'ogg':
            audio = OggVorbis(file_path)
            metadata['year'] = audio.get('date', ['2024'])[0] or '2024'
        elif file_ext == 'flac':
            audio = FLAC(file_path)
            metadata['year'] = audio.get('date', ['2024'])[0] or '2024'
        elif file_ext == 'wav':
            audio = WAVE(file_path)
            metadata['year'] = '2024'
        elif file_ext in ['m4a', 'mp4']:
            audio = MP4(file_path)
            metadata['year'] = audio.get('\xa9day', ['2024'])[0] or '2024'
        else:
            return metadata

        # 提取基础信息
        metadata['title'] = audio.get('title', [''])[0] or os.path.basename(file_path).replace(f'.{file_ext}', '')
        metadata['artist'] = audio.get('artist', ['未知歌手'])[0]
        metadata['album'] = audio.get('album', ['未知专辑'])[0]
        metadata['track'] = audio.get('tracknumber', ['0'])[0]

        # 提取时长（增加异常捕获 + 优先使用ffprobe）
        try:
            # 优先使用ffprobe提取时长（更稳定）
            metadata['duration'] = get_duration_with_ffprobe(file_path)
            # 如果ffprobe失败，再尝试pydub
            if metadata['duration'] <= 0:
                audio_segment = AudioSegment.from_file(file_path)
                metadata['duration'] = len(audio_segment) / 1000
        except Exception as e:
            print(f"提取时长失败 {file_path}: {e}")
            # 最终备用：返回0
            metadata['duration'] = 0

        # 提取封面（仅返回二进制数据，不上传到图床）
        cover_data = None
        if file_ext == 'mp3':
            try:
                from mutagen.id3 import ID3, APIC
                id3 = ID3(file_path)
                # 遍历所有APIC标签（封面标签）
                for tag in id3.values():
                    if isinstance(tag, APIC) and tag.data:
                        cover_data = tag.data
                        break
            except Exception as e:
                print(f"MP3封面提取失败 {file_path}: {e}")
        elif file_ext in ['m4a', 'mp4']:
            try:
                # MP4的封面标签是covr
                if 'covr' in audio:
                    cover_data = audio['covr'][0]  # 获取第一个封面
            except Exception as e:
                print(f"M4A/MP4封面提取失败 {file_path}: {e}")

        # 如果有封面数据，先保存到临时文件（后续统一上传）
        if cover_data:
            # 创建临时封面文件
            temp_cover_path = os.path.join(tempfile.gettempdir(), f"temp_cover_{uuid.uuid4()}.jpg")
            with open(temp_cover_path, 'wb') as f:
                f.write(cover_data)
            metadata['cover_img'] = temp_cover_path  # 暂存临时文件路径
        else:
            metadata['cover_img'] = ""

    except Exception as e:
        print(f"提取元数据失败 {file_path}: {e}")
        # 使用文件名作为标题
        metadata['title'] = os.path.basename(file_path).replace(f'.{file_ext}', '')
        metadata['duration'] = 0

    return metadata


def extract_album_cover(audio_files, output_dir):
    """从音频文件提取专辑封面（返回临时文件路径）"""
    cover_path = ""
    # 优先从第一个文件提取封面
    for file_path in audio_files:
        try:
            if not os.path.exists(file_path):
                continue

            cover_filename = f"album_cover_{uuid.uuid4()}.jpg"
            cover_path = os.path.join(output_dir, cover_filename)

            cmd = [
                FFMPEG_PATH,  # 使用配置好的绝对路径
                '-i', file_path,
                '-an',  # 忽略音频流
                '-vcodec', 'copy',  # 直接复制封面编码
                '-f', 'image2',
                '-y',  # 覆盖已有文件
                '-hide_banner',
                '-loglevel', 'error',
                cover_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            if result.returncode == 0 and os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
                return cover_path
        except Exception as e:
            print(f"提取封面失败 {file_path}: {e}")
            continue

    return cover_path


def upload_cover_to_imgbed(cover_path):
    """将封面文件上传到本地图床，返回访问URL"""
    if not cover_path or not os.path.exists(cover_path):
        return ""

    try:
        # 确保上传目录存在
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # 生成唯一文件名
        ext = os.path.splitext(cover_path)[-1]
        filename = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        # 复制文件到图床目录
        shutil.copy(cover_path, save_path)

        # 生成访问URL
        img_url = f"{COVER_BASE_URL}{filename}"
        return img_url
    except Exception as e:
        print(f"封面上传到图床失败：{e}")
        return ""


# 合并音频文件
def merge_audio_files(audio_files, output_dir, album_name, artist, album_id):
    """
    合并多个音频文件为一个整轨MP3（修复版：使用concat滤镜强制重编码）
    """
    if not audio_files or len(audio_files) == 0:
        return ""

    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        safe_album_name = re.sub(r'[\\/:*?"<>|]', '_', album_name)
        safe_artist = re.sub(r'[\\/:*?"<>|]', '_', artist)
        merge_filename = f"{album_id}_{safe_artist}_{safe_album_name}.mp3"
        merge_file_path = os.path.join(output_dir, merge_filename)

        if len(audio_files) == 1:
            # 单个文件直接转码
            cmd = [
                FFMPEG_PATH,
                '-i', audio_files[0],
                '-acodec', 'libmp3lame',
                '-b:a', '320k',
                '-ar', '44100',  # 统一采样率
                '-ac', '2',  # 统一声道
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                merge_file_path
            ]
        else:
            # ✅ 修复：使用concat滤镜进行重编码合并
            # 构建filter_complex输入
            inputs = []
            filter_parts = []

            for i, file_path in enumerate(audio_files):
                inputs.extend(['-i', file_path])
                filter_parts.append(f'[{i}:a:0]')

            # 构建concat滤镜字符串: [0:a:0][1:a:0]...concat=n=19:v=0:a=1[out]
            concat_filter = ''.join(filter_parts) + f'concat=n={len(audio_files)}:v=0:a=1[out]'

            cmd = [
                FFMPEG_PATH,
                *inputs,  # 展开所有输入文件
                '-filter_complex', concat_filter,
                '-map', '[out]',
                '-acodec', 'libmp3lame',
                '-b:a', '320k',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                merge_file_path
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding='utf-8')

        if result.returncode != 0:
            print(f"❌ FFmpeg合并失败: {result.stderr}")
            print(f"命令: {' '.join(cmd)}")
            return ""

        # ✅ 验证：检查输出文件时长是否合理
        actual_duration = get_duration_with_ffprobe(merge_file_path)
        expected_duration = sum(get_duration_with_ffprobe(f) for f in audio_files)

        print(f"📊 合并验证：期望时长 {expected_duration:.2f}s, 实际时长 {actual_duration:.2f}s")

        if actual_duration < expected_duration * 0.9:  # 允许10%误差
            print(f"⚠️ 警告：合并后时长异常，可能丢失数据！")

        return merge_file_path

    except Exception as e:
        print(f"音频合并异常: {e}")
        traceback.print_exc()
        return ""

# ✅ 简化：上传函数使用简单序号生成文件名
def upload_merged_audio(merge_file_path, album_id, artist, album_name):
    """
    上传合并后的MP3到音频目录，使用简单序号生成文件名
    :param merge_file_path: 合并后的文件路径
    :param album_id: 简单序号（文件数+1）
    :param artist: 歌手名
    :param album_name: 专辑名
    :return: 上传结果
    """
    if not merge_file_path or not os.path.exists(merge_file_path):
        return {"code": 400, "msg": "文件为空", "data": None}

    try:
        # 确保音频上传目录存在
        if not os.path.exists(AUDIO_UPLOAD_FOLDER):
            os.makedirs(AUDIO_UPLOAD_FOLDER)

        # ===== 1. 生成指定格式的文件名 =====
        # 处理特殊字符
        safe_album_name = re.sub(r'[\\/:*?"<>|]', '_', album_name)
        safe_artist = re.sub(r'[\\/:*?"<>|]', '_', artist)
        # 最终文件名格式：序号_歌手名_专辑名.mp3
        final_filename = f"{album_id}_{safe_artist}_{safe_album_name}.mp3"

        # 检查文件是否已存在，避免覆盖
        save_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, final_filename)
        if os.path.exists(save_file_path):
            # 如果已存在，添加4位随机后缀
            final_filename = f"{album_id}_{safe_artist}_{safe_album_name}_{uuid.uuid4().hex[:4]}.mp3"
            save_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, final_filename)

        # ===== 2. 复制合并后的文件到音频目录 =====
        shutil.copy(merge_file_path, save_file_path)

        # ===== 3. 解析音频时长 =====
        from mutagen.mp3 import MP3
        from mutagen import MutagenError
        mp3_duration = 0
        try:
            audio = MP3(save_file_path)
            mp3_duration = int(audio.info.length)
        except MutagenError as e:
            print(f"⚠️ 音频时长解析失败：{str(e)}")
            # 备用：用ffprobe
            mp3_duration = get_duration_with_ffprobe(save_file_path)

        # ===== 4. 生成访问URL =====
        mp3_url = f"{AUDIO_BASE_URL}{final_filename}"

        # 格式化时长
        m = mp3_duration // 60
        s = mp3_duration % 60
        duration_format = f"{m}:{s:02d}"
        print(mp3_duration)
        return {
            "code": 200,
            "msg": "音频上传成功！",
            "data": {
                "mp3_url": mp3_url,
                "mp3_name": final_filename,  # 返回最终的文件名
                "mp3_duration": mp3_duration,
                "duration_format": duration_format
            }
        }
    except Exception as e:
        print(f"❌ 上传合并音频失败：{e}")
        return {"code": 500, "msg": f"上传失败：{str(e)}", "data": None}


def write_cover_to_mp3(mp3_file_path: str | Path, cover_data: bytes) -> str:
    """
    直接将封面图片写入MP3文件的ID3标签，并返回临时封面文件路径（供图床上传使用）

    Args:
        mp3_file_path: MP3文件路径
        cover_data: 封面图片二进制数据

    Returns:
        str: 临时封面文件路径（用于后续上传到图床），失败返回空字符串
    """
    try:
        mp3_file_path = Path(mp3_file_path)
        if not mp3_file_path.exists():
            print(f"MP3文件不存在：{mp3_file_path}")
            return ""

        # 第一步：将封面数据保存为临时文件（供图床上传）
        temp_cover_path = os.path.join(os.path.dirname(str(mp3_file_path)), f"temp_cover_{uuid.uuid4()}.jpg")
        with open(temp_cover_path, 'wb') as f:
            f.write(cover_data)

        # 第二步：写入MP3文件
        audio = ID3(str(mp3_file_path))

        # 清空原有封面
        for tag in audio.keys():
            if tag.startswith('APIC'):
                del audio[tag]

        # 添加新封面
        audio.add(APIC(
            encoding=3,  # UTF-8
            mime='image/jpeg',
            type=3,  # 3=封面
            desc='Cover',
            data=cover_data
        ))

        # 保存修改
        audio.save(v2_version=4)
        print(f"封面已成功写入MP3文件：{mp3_file_path.name}")

        return temp_cover_path  # 返回临时文件路径，供图床上传使用

    except Exception as e:
        print(f"写入封面到MP3失败：{e}")
        return ""


# 替换werkzeug的secure_filename，保留中文/合法字符
def secure_filename(filename: str) -> str:
    """
    安全的文件名处理函数：
    1. 保留中文、字母、数字、-、_、.
    2. 仅替换Windows系统非法字符
    3. 处理首尾空白字符
    """
    if not filename:
        return "unknown_file"

    # 要清理的Windows非法字符
    illegal_chars = r'\/:*?"<>|'
    for char in illegal_chars:
        filename = filename.replace(char, '_')

    # 去除首尾空白字符
    filename = filename.strip()

    # 处理空文件名（防止全是非法字符的情况）
    if not filename:
        return "unknown_file"

    # 处理连续的点/下划线（可选）
    filename = filename.replace('..', '.').replace('__', '_')

    return filename