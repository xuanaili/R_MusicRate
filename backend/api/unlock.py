# MusicRate\backend\api\audio_resource.py 音频资源专属接口 - 专辑MP3上传/查询/删除/时长解析
from flask import request, jsonify
import json
import traceback
import os
import re
import uuid
import os.path
import struct
import base64
import tempfile
import shutil
import subprocess
from datetime import datetime
from encodings import idna
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import io
import requests
import time

import pymysql
import pyaes
import mutagen
from mutagen.mp3 import MP3
from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC, Picture
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, ID3NoHeaderError
from werkzeug.utils import secure_filename
from pydub import AudioSegment

from ..config import MYSQL_CONFIG, AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER, UPLOAD_FOLDER, COVER_BASE_URL
from ..db_utils import get_db, get_current_user_id
from ..decorators import login_required

# ===================== NCM解密核心配置 =====================
CORE_KEY = bytes.fromhex('687a4852416d736f356b496e62617857')
META_KEY = bytes.fromhex('2331346C6A6B5F215C5D2630553C2728')
MAGIC_HEADER = bytes([0x43, 0x54, 0x45, 0x4e, 0x46, 0x44, 0x41, 0x4d])
REQUEST_TIMEOUT = 10
RETRY_TIMES = 2

# ✅ 修复1：获取当前文件的绝对路径，拼接FFmpeg路径（关键！）
# 获取unlock.py所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 拼接FFmpeg路径（根据你的实际目录结构调整）
FFMPEG_PATH = os.path.join(current_dir, '..', 'tools', 'ffmpeg', 'ffmpeg.exe')
FFPROBE_PATH = os.path.join(current_dir, '..', 'tools', 'ffmpeg', 'ffprobe.exe')

# 转换为绝对路径（解决相对路径层级问题）
FFMPEG_PATH = os.path.abspath(FFMPEG_PATH)
FFPROBE_PATH = os.path.abspath(FFPROBE_PATH)

# 强制设置pydub的FFmpeg/ffprobe路径
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH

# 打印路径调试（方便排查）
print(f"FFmpeg路径: {FFMPEG_PATH} (存在: {os.path.exists(FFMPEG_PATH)})")
print(f"FFprobe路径: {FFPROBE_PATH} (存在: {os.path.exists(FFPROBE_PATH)})")

# 允许的音频格式（新增ncm）
ALLOWED_EXTENSIONS = {'mp3', 'ogg', 'flac', 'ncm', 'kgg', 'kwm', 'wav', 'm4a', 'mp4'}


# ===================== NCM解密辅助函数 =====================
def pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        return data
    return data[:-pad_len]


def compress_image(img_data: bytes, max_size: int = 256 * 1024) -> bytes:
    if not img_data:
        return b''

    try:
        img = Image.open(io.BytesIO(img_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        quality = 80
        while len(img_data) > max_size and quality > 10:
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            img_data = buf.getvalue()
            quality -= 10
        return img_data
    except Exception as e:
        print(f"图片压缩失败：{e}")
        return img_data


def download_cover(url: str) -> Optional[bytes]:
    if not url or not url.startswith(('http://', 'https://')):
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://music.163.com/'
    }

    for retry in range(RETRY_TIMES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"下载封面失败（重试{retry}/{RETRY_TIMES}）：{e}")
            if retry < RETRY_TIMES:
                time.sleep(1)
            continue

    return None


# ===================== NCM解密核心类 =====================
class NcmDecrypt:
    def __init__(self, buf: bytes, filename: str):
        self.raw = buf
        self.offset = 10
        self.filename = filename
        self.format: str = ""
        self.mime: str = ""
        self.audio: Optional[bytes] = None
        self.ori_meta: Dict[str, Any] = {}
        self.new_meta: Dict[str, Any] = {}
        self.cover_data: Optional[bytes] = None

    def _get_key_data(self) -> bytes:
        key_len = struct.unpack('<I', self.raw[self.offset:self.offset + 4])[0]
        self.offset += 4

        cipher_text = bytearray(self.raw[self.offset:self.offset + key_len])
        for i in range(len(cipher_text)):
            cipher_text[i] ^= 0x64
        self.offset += key_len

        aes = pyaes.AESModeOfOperationECB(CORE_KEY)
        decrypted = bytearray()
        cipher_text_bytes = bytes(cipher_text)
        for i in range(0, len(cipher_text_bytes), 16):
            block = cipher_text_bytes[i:i + 16]
            if len(block) < 16:
                block += b'\x00' * (16 - len(block))
            decrypted.extend(aes.decrypt(block))

        plain_text = pkcs7_unpad(bytes(decrypted))
        return plain_text[17:]

    def _get_key_box(self) -> bytes:
        key_data = self._get_key_data()
        box = bytearray(range(256))
        key_data_len = len(key_data)
        j = 0

        for i in range(256):
            j = (box[i] + j + key_data[i % key_data_len]) & 0xff
            box[i], box[j] = box[j], box[i]

        key_box = bytearray(256)
        for i in range(256):
            i1 = (i + 1) & 0xff
            si = box[i1]
            sj = box[(i1 + si) & 0xff]
            key_box[i] = box[(si + sj) & 0xff]

        return bytes(key_box)

    def _get_meta_data(self) -> Dict[str, Any]:
        meta_len = struct.unpack('<I', self.raw[self.offset:self.offset + 4])[0]
        self.offset += 4
        if meta_len == 0:
            return {}

        cipher_text = bytearray(self.raw[self.offset:self.offset + meta_len])
        for i in range(len(cipher_text)):
            cipher_text[i] ^= 0x63
        self.offset += meta_len

        meta_base64 = cipher_text[22:].decode('utf-8')
        meta_encrypted = base64.b64decode(meta_base64)

        aes = pyaes.AESModeOfOperationECB(META_KEY)
        decrypted = bytearray()
        for i in range(0, len(meta_encrypted), 16):
            block = meta_encrypted[i:i + 16]
            decrypted.extend(aes.decrypt(block))

        plain_text = pkcs7_unpad(bytes(decrypted)).decode('utf-8')

        label_index = plain_text.find(':')
        if plain_text[:label_index] == 'dj':
            dj_meta = json.loads(plain_text[label_index + 1:])
            result = dj_meta['mainMusic']
        else:
            result = json.loads(plain_text[label_index + 1:])

        cover_data = None
        if 'albumPicDoc' in result and result['albumPicDoc']:
            try:
                cover_data = base64.b64decode(result['albumPicDoc'])
            except Exception as e:
                print(f"解析 albumPicDoc 失败：{e}")
        elif 'albumPic' in result and isinstance(result['albumPic'], bytes):
            cover_data = result['albumPic']
        elif 'pic' in result and result['pic']:
            try:
                cover_data = base64.b64decode(result['pic'])
            except Exception as e:
                print(f"解析 pic 失败：{e}")
        if not cover_data and 'albumPic' in result and isinstance(result['albumPic'], str):
            cover_data = download_cover(result['albumPic'])

        if cover_data:
            self.cover_data = compress_image(cover_data)

        return result

    def _get_audio(self, key_box: bytes) -> bytes:
        extra_len = struct.unpack('<I', self.raw[self.offset + 5:self.offset + 9])[0]
        self.offset += extra_len + 13

        audio_data = bytearray(self.raw[self.offset:])
        for cur in range(len(audio_data)):
            audio_data[cur] ^= key_box[cur & 0xff]

        return bytes(audio_data)

    def _get_meta_from_file(self) -> Dict[str, str]:
        name = Path(self.filename).stem
        parts = name.split('-', 1)
        if len(parts) == 2:
            return {'artist': parts[0].strip(), 'title': parts[1].strip()}
        return {'artist': '', 'title': name}

    def _build_meta(self):
        if not self.ori_meta:
            raise ValueError('元数据为空')

        file_meta = self._get_meta_from_file()
        artists: List[str] = []
        artist_raw = self.ori_meta.get('artist', [])

        if isinstance(artist_raw, list):
            for item in artist_raw:
                if isinstance(item, dict) and 'name' in item:
                    artists.append(item['name'])
                elif isinstance(item, str):
                    artists.append(item)
        elif isinstance(artist_raw, str):
            artists.append(artist_raw)

        if not artists and file_meta.get('artist'):
            artists = [file_meta['artist']]

        self.new_meta = {
            'title': self.ori_meta.get('musicName', file_meta['title']),
            'artists': artists,
            'album': self.ori_meta.get('album', ''),
            'cover': self.cover_data
        }

    def _write_meta(self):
        if not self.audio or not self.new_meta:
            return

        if self.format == 'mp3':
            buf = io.BytesIO(self.audio)
            try:
                audio = ID3(buf)
            except ID3NoHeaderError:
                audio = ID3()

            audio.delete()
            audio.add(TIT2(encoding=3, text=self.new_meta['title']))
            audio.add(TPE1(encoding=3, text='; '.join(self.new_meta['artists'])))
            audio.add(TALB(encoding=3, text=self.new_meta['album']))

            if self.new_meta['cover']:
                try:
                    audio.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=self.new_meta['cover']
                    ))
                except Exception as e:
                    print(f"写入MP3封面失败：{e}")

            audio.save(buf, v2_version=4)
            buf.seek(0)
            self.audio = buf.read()

        elif self.format == 'flac':
            buf = io.BytesIO(self.audio)
            audio = FLAC(buf)

            audio.clear()
            audio['title'] = self.new_meta['title']
            audio['artist'] = self.new_meta['artists']
            audio['album'] = self.new_meta['album']

            if self.new_meta['cover']:
                try:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = 'image/jpeg'
                    pic.data = self.new_meta['cover']
                    audio.clear_pictures()
                    audio.add_picture(pic)
                except Exception as e:
                    print(f"写入FLAC封面失败：{e}")

            audio.save()
            buf.seek(0)
            self.audio = buf.read()

    def _sniff_audio_ext(self, data: bytes) -> str:
        if data.startswith(b'fLaC'):
            return 'flac'
        elif data.startswith(b'ID3') or (len(data) > 2 and data[0] == 0xFF and data[1] in (0xFB, 0xF3, 0xF2)):
            return 'mp3'
        return 'unknown'

    def decrypt(self) -> Dict[str, Any]:
        key_box = self._get_key_box()
        self.ori_meta = self._get_meta_data()
        self.audio = self._get_audio(key_box)
        self.format = self.ori_meta.get('format', self._sniff_audio_ext(self.audio))
        self.mime = 'audio/flac' if self.format == 'flac' else 'audio/mpeg'

        try:
            self._build_meta()
            self._write_meta()
        except Exception as e:
            print(f"处理元数据失败：{e}")

        return {
            'title': self.new_meta.get('title', ''),
            'artist': '; '.join(self.new_meta.get('artists', [])),
            'album': self.new_meta.get('album', ''),
            'ext': self.format,
            'mime': self.mime,
            'audio_data': self.audio,
            'has_cover': bool(self.cover_data)
        }


# ===================== 通用工具函数 =====================
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
        cmd = [
            FFPROBE_PATH,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path.encode('utf-8').decode('utf-8')
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            shell=False
        )
        duration_str = result.stdout.strip()
        if duration_str:
            duration = float(duration_str)
            return duration
        return 0
    except Exception as e:
        print(f"ffprobe提取时长失败: {e}")
        return 0


def get_audio_metadata(file_path, file_ext):
    """提取音频文件元数据（优化封面提取）"""
    metadata = {
        'title': '',
        'artist': '',
        'album': '',
        'track': '',
        'cover_img': '',
        'duration': 0,
        'year': '2024'
    }

    try:
        if not os.path.exists(file_path):
            print(f"文件不存在：{file_path}")
            return metadata

        # 提取元数据
        if file_ext == 'mp3':
            audio = EasyID3(file_path)
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

        # 提取时长
        try:
            metadata['duration'] = get_duration_with_ffprobe(file_path)
            if metadata['duration'] <= 0:
                audio_segment = AudioSegment.from_file(file_path)
                metadata['duration'] = len(audio_segment) / 1000
        except Exception as e:
            print(f"提取时长失败 {file_path}: {e}")
            metadata['duration'] = 0

        # 提取封面
        cover_data = None
        if file_ext == 'mp3':
            try:
                id3 = ID3(file_path)
                for tag in id3.values():
                    if isinstance(tag, APIC) and tag.data:
                        cover_data = tag.data
                        break
            except Exception as e:
                print(f"MP3封面提取失败 {file_path}: {e}")
        elif file_ext in ['m4a', 'mp4']:
            try:
                if 'covr' in audio:
                    cover_data = audio['covr'][0]
            except Exception as e:
                print(f"M4A/MP4封面提取失败 {file_path}: {e}")

        # 保存封面到临时文件
        if cover_data:
            temp_cover_path = os.path.join(tempfile.gettempdir(), f"temp_cover_{uuid.uuid4()}.jpg")
            with open(temp_cover_path, 'wb') as f:
                f.write(cover_data)
            metadata['cover_img'] = temp_cover_path
        else:
            metadata['cover_img'] = ""

    except Exception as e:
        print(f"提取元数据失败 {file_path}: {e}")
        metadata['title'] = os.path.basename(file_path).replace(f'.{file_ext}', '')
        metadata['duration'] = 0

    return metadata


def extract_album_cover(audio_files, output_dir):
    """从音频文件提取专辑封面（返回临时文件路径）"""
    cover_path = ""
    for file_path in audio_files:
        try:
            if not os.path.exists(file_path):
                continue

            cover_filename = f"album_cover_{uuid.uuid4()}.jpg"
            cover_path = os.path.join(output_dir, cover_filename)

            cmd = [
                FFMPEG_PATH,
                '-i', file_path,
                '-an',
                '-vcodec', 'copy',
                '-f', 'image2',
                '-y',
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
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        ext = os.path.splitext(cover_path)[-1]
        filename = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        shutil.copy(cover_path, save_path)

        img_url = f"{COVER_BASE_URL}{filename}"
        return img_url
    except Exception as e:
        print(f"封面上传到图床失败：{e}")
        return ""


def merge_audio_files(audio_files, output_dir, album_name, artist):
    """合并多个音频文件为一个整轨MP3"""
    if not audio_files or len(audio_files) == 0:
        return ""

    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成安全的文件名
        safe_album_name = re.sub(r'[\\/:*?"<>|]', '_', album_name)
        safe_artist = re.sub(r'[\\/:*?"<>|]', '_', artist)
        merge_filename = f"{safe_artist}-{safe_album_name}_{uuid.uuid4().hex[:8]}.mp3"
        merge_file_path = os.path.join(output_dir, merge_filename)

        # 单个文件直接转换为MP3
        if len(audio_files) == 1:
            cmd = [
                FFMPEG_PATH,
                '-i', audio_files[0],
                '-acodec', 'mp3',
                '-b:a', '320k',
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                merge_file_path
            ]
        else:
            # 多个文件生成列表后合并
            list_file_path = os.path.join(output_dir, "merge_list.txt")
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for file_path in audio_files:
                    f.write(f"file '{file_path.replace("'", "\\'")}'\n")

            cmd = [
                FFMPEG_PATH,
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file_path,
                '-acodec', 'mp3',
                '-b:a', '320k',
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                merge_file_path
            ]

        # 执行合并命令
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            print(f"音频合并失败: {result.stderr}")
            return ""

        # 删除临时列表文件
        if len(audio_files) > 1 and os.path.exists(list_file_path):
            os.remove(list_file_path)

        return merge_file_path
    except Exception as e:
        print(f"音频合并异常: {e}")
        return ""


def upload_merged_audio(merge_file_path):
    """上传合并后的MP3到音频目录，返回访问URL"""
    if not merge_file_path or not os.path.exists(merge_file_path):
        return {"code": 400, "msg": "文件为空", "data": None}

    try:
        if not os.path.exists(AUDIO_UPLOAD_FOLDER):
            os.makedirs(AUDIO_UPLOAD_FOLDER)

        # 生成唯一文件名
        filename = os.path.basename(merge_file_path)
        file_suffix = filename.split('.')[-1]
        file_prefix = filename.rsplit('.', 1)[0]
        unique_filename = f"merged_{uuid.uuid4().hex[:12]}_{file_prefix}.{file_suffix}"
        save_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, unique_filename)

        # 复制文件
        shutil.copy(merge_file_path, save_file_path)

        # 解析时长
        mp3_duration = 0
        try:
            audio = MP3(save_file_path)
            mp3_duration = int(audio.info.length)
        except MutagenError as e:
            print(f"⚠️ 音频时长解析失败：{str(e)}")
            mp3_duration = get_duration_with_ffprobe(save_file_path)

        # 生成URL
        mp3_url = f"{AUDIO_BASE_URL}{unique_filename}"
        m = mp3_duration // 60
        s = mp3_duration % 60
        duration_format = f"{m}:{s:02d}"

        return {
            "code": 200,
            "msg": "音频上传成功！",
            "data": {
                "mp3_url": mp3_url,
                "mp3_name": filename,
                "mp3_duration": mp3_duration,
                "duration_format": duration_format
            }
        }
    except Exception as e:
        print(f"❌ 上传合并音频失败：{e}")
        return {"code": 500, "msg": f"上传失败：{str(e)}", "data": None}


def decrypt_ncm_to_file(ncm_file_path, output_dir):
    """解密NCM文件到指定目录，返回解密后的文件路径"""
    try:
        file_path = Path(ncm_file_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # 读取NCM文件并解密
        raw_data = file_path.read_bytes()
        decryptor = NcmDecrypt(raw_data, file_path.name)
        result = decryptor.decrypt()

        # 生成输出文件名
        output_filename = f"{result['title']}.{result['ext']}"
        output_filename = output_filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*',
                                                                                                         '_').replace(
            '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        output_file = output_dir / output_filename

        # 避免文件名重复
        counter = 1
        while output_file.exists():
            output_filename = f"{result['title']}_{counter}.{result['ext']}"
            output_filename = output_filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*',
                                                                                                             '_').replace(
                '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            output_file = output_dir / output_filename
            counter += 1

        # 写入解密后的音频数据
        output_file.write_bytes(result['audio_data'])
        print(f"✅ NCM解密完成：{output_file}")
        return str(output_file)
    except Exception as e:
        print(f"❌ NCM解密失败 {ncm_file_path}: {e}")
        return ""


# ===================== 路由注册 =====================
def register_unlock_routes(app):
    """注册专辑音频资源相关路由"""




    # 5. 音频解析接口（支持NCM解密+多文件合并）
    @app.route('/api/audio/unlock/parse', methods=['POST', 'OPTIONS'])
    @login_required
    def unlock_parse_audio():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            current_user_id = int(current_user_id)

            # 校验管理员权限
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user_info = cursor.fetchone()
            if not user_info or user_info['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "仅管理员可解析音频！"}), 403
            cursor.close()

            # 检查文件上传
            if 'audio_files' not in request.files:
                return jsonify({"code": 400, "msg": "请上传音频文件"}), 200

            files = request.files.getlist('audio_files')
            if not files:
                return jsonify({"code": 400, "msg": "请选择至少一个音频文件"}), 200

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_files = []
                file_metadatas = []
                temp_cover_files = []

                # 处理每个上传的文件
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_ext = filename.rsplit('.', 1)[1].lower()
                        file_path = os.path.join(temp_dir, filename)
                        file.save(file_path)

                        # 如果是NCM文件，先解密
                        if file_ext == 'ncm':
                            decrypted_path = decrypt_ncm_to_file(file_path, temp_dir)
                            if not decrypted_path:
                                continue
                            # 更新文件路径和扩展名
                            file_path = decrypted_path
                            file_ext = decrypted_path.rsplit('.', 1)[1].lower()

                        # 提取元数据
                        metadata = get_audio_metadata(file_path, file_ext)
                        file_metadatas.append(metadata)
                        audio_files.append(file_path)

                        # 记录临时封面文件
                        if metadata['cover_img'] and os.path.exists(metadata['cover_img']):
                            temp_cover_files.append(metadata['cover_img'])

                if not file_metadatas:
                    return jsonify({"code": 400, "msg": "没有有效的音频文件"}), 200

                # 按曲目编号排序
                file_metadatas.sort(key=lambda x: int(x['track'].split('/')[0]) if x['track'].isdigit() else 0)

                # 构建解析结果
                parse_result = {
                    'album_name': file_metadatas[0]['album'],
                    'album_singer': file_metadatas[0]['artist'],
                    'mp3_duration': '',
                    'cover_img': '',
                    'mp3_url': '',
                    'songs': []
                }

                # 提取并上传封面
                cover_img_url = ""
                # 优先使用元数据中的封面
                for metadata in file_metadatas:
                    if metadata['cover_img']:
                        cover_img_url = upload_cover_to_imgbed(metadata['cover_img'])
                        if cover_img_url:
                            break
                # 备用：用FFmpeg提取封面
                if not cover_img_url:
                    cover_path = extract_album_cover(audio_files, temp_dir)
                    if cover_path:
                        cover_img_url = upload_cover_to_imgbed(cover_path)

                parse_result['cover_img'] = cover_img_url

                # 合并音频文件
                merge_file_path = merge_audio_files(
                    audio_files=audio_files,
                    output_dir=temp_dir,
                    album_name=parse_result['album_name'],
                    artist=parse_result['album_singer']
                )

                # 上传合并后的音频
                if merge_file_path and os.path.exists(merge_file_path):
                    upload_result = upload_merged_audio(merge_file_path)
                    if upload_result['code'] == 200:
                        parse_result['mp3_url'] = upload_result['data']['mp3_url']
                        parse_result['mp3_duration'] = upload_result['data']['mp3_duration']
                    else:
                        print(f"音频上传失败：{upload_result['msg']}")
                else:
                    print(f"合并后的音频文件不存在：{merge_file_path}")

                # 构建单曲列表
                total_duration = 0
                for idx, metadata in enumerate(file_metadatas):
                    timestamp = format_duration(total_duration)
                    parse_result['songs'].append({
                        'name': metadata['title'] or f'未知曲目{idx + 1}',
                        'duration': timestamp,
                        'file_duration': format_duration(metadata['duration']),
                        'track_number': idx + 1
                    })
                    total_duration += metadata['duration']

                # 清理临时封面文件
                for temp_cover in temp_cover_files:
                    try:
                        if os.path.exists(temp_cover):
                            os.remove(temp_cover)
                    except:
                        pass

                return jsonify({
                    'code': 200,
                    'msg': '音频解析成功！',
                    'data': parse_result
                }), 200

        except Exception as e:
            print(f"❌ 音频解析出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'解析失败：{str(e)}'
            }), 200

    # 6. 上传合并后的音频到专辑池
    @app.route('/api/album/pool/audio/upload/merged', methods=['POST', 'OPTIONS'])
    @login_required
    def upload_merged_audio_to_album():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            current_user_id = int(current_user_id)

            # 校验管理员权限
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user_info = cursor.fetchone()
            if not user_info or user_info['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "仅管理员可上传合并音频！"}), 403

            # 获取参数
            req_data = request.get_json()
            album_id = req_data.get('source_pool_id')
            mp3_url = req_data.get('mp3_url')
            old_mp3_url = req_data.get('old_mp3_url', '').strip()

            if not album_id or not mp3_url:
                cursor.close()
                return jsonify({"code": 400, "msg": "专辑ID和音频URL不能为空！"}), 400

            # 校验专辑是否存在
            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_id}]不存在！"}), 404

            # 提取文件名
            mp3_name = mp3_url.split('/')[-1] if '/' in mp3_url else 'merged_audio.mp3'

            # 删除旧音频文件
            if old_mp3_url and old_mp3_url != '' and AUDIO_BASE_URL in old_mp3_url:
                old_filename = old_mp3_url.replace(AUDIO_BASE_URL, '')
                old_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, old_filename)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        print(f"✅ 成功删除旧音频文件: {old_file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除旧音频文件失败: {str(e)}")

            # 解析音频时长
            mp3_duration = 0
            duration_format = "0:00"
            mp3_filename = mp3_url.replace(AUDIO_BASE_URL, '')
            mp3_path = os.path.join(AUDIO_UPLOAD_FOLDER, mp3_filename)

            if os.path.exists(mp3_path):
                try:
                    audio = MP3(mp3_path)
                    mp3_duration = int(audio.info.length)
                    m = mp3_duration // 60
                    s = mp3_duration % 60
                    duration_format = f"{m}:{s:02d}"
                except MutagenError as e:
                    print(f"⚠️ 合并音频时长解析失败：{str(e)}")
                    mp3_duration = get_duration_with_ffprobe(mp3_path)

            # 更新到数据库
            cursor.execute('''
                UPDATE album_pool 
                SET mp3_url = %s, mp3_name = %s, mp3_duration = %s 
                WHERE id = %s
            ''', (mp3_url, mp3_name, mp3_duration, album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "合并音频上传成功！",
                "data": {
                    "mp3_url": mp3_url,
                    "mp3_name": mp3_name,
                    "mp3_duration": mp3_duration,
                    "duration_format": duration_format
                }
            })
        except Exception as e:
            print(f"❌ 上传合并音频出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"上传失败：{str(e)}"}), 500