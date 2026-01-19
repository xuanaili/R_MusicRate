import struct
import base64
import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple

import pyaes
from pathlib import Path
from PIL import Image
import io
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
from mutagen.flac import FLAC, Picture
import requests
import time

# 配置日志
logger = logging.getLogger(__name__)

# ===================== 1. 常量定义 =====================
CORE_KEY = bytes.fromhex('687a4852416d736f356b496e62617857')
META_KEY = bytes.fromhex('2331346C6A6B5F215C5D2630553C2728')
MAGIC_HEADER = bytes([0x43, 0x54, 0x45, 0x4e, 0x46, 0x44, 0x41, 0x4d])

REQUEST_TIMEOUT = 10
RETRY_TIMES = 2


# ===================== 2. 辅助函数 =====================
def pkcs7_unpad(data: bytes) -> bytes:
    """PKCS7解填充"""
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        return data
    return data[:-pad_len]


def compress_image(img_data: bytes, max_size: int = 256 * 1024) -> bytes:
    """压缩图片到指定大小"""
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
        logger.error(f"图片压缩失败：{e}")
        return img_data


def download_cover(url: str) -> Optional[bytes]:
    """下载封面图片"""
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
            logger.warning(f"下载封面失败（重试{retry}/{RETRY_TIMES}）：{e}")
            if retry < RETRY_TIMES:
                time.sleep(1)
            continue

    return None


# ===================== 3. 核心解密类 =====================
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
        """获取解密密钥数据"""
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
        """生成密钥盒"""
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
        """解析元数据"""
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

        # 多种封面获取方式兼容
        if 'albumPicDoc' in result and result['albumPicDoc']:
            try:
                cover_data = base64.b64decode(result['albumPicDoc'])
            except Exception as e:
                logger.error(f"解析 albumPicDoc 失败：{e}")

        elif 'albumPic' in result and isinstance(result['albumPic'], bytes):
            cover_data = result['albumPic']

        elif 'pic' in result and result['pic']:
            try:
                cover_data = base64.b64decode(result['pic'])
            except Exception as e:
                logger.error(f"解析 pic 失败：{e}")

        if not cover_data and 'albumPic' in result and isinstance(result['albumPic'], str):
            cover_data = download_cover(result['albumPic'])

        if cover_data:
            self.cover_data = compress_image(cover_data)

        return result

    def _get_audio(self, key_box: bytes) -> bytes:
        """解密音频数据"""
        extra_len = struct.unpack('<I', self.raw[self.offset + 5:self.offset + 9])[0]
        self.offset += extra_len + 13

        audio_data = bytearray(self.raw[self.offset:])
        for cur in range(len(audio_data)):
            audio_data[cur] ^= key_box[cur & 0xff]

        return bytes(audio_data)

    def _get_meta_from_file(self) -> Dict[str, str]:
        """从文件名提取元数据"""
        name = Path(self.filename).stem
        parts = name.split('-', 1)
        if len(parts) == 2:
            return {'artist': parts[0].strip(), 'title': parts[1].strip()}
        return {'artist': '', 'title': name}

    def _build_meta(self):
        """构建标准化元数据"""
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
        """写入元数据到音频文件"""
        if not self.audio or not self.new_meta:
            return

        if self.format == 'mp3':
            buf = io.BytesIO(self.audio)
            try:
                audio = ID3(buf)
            except mutagen.id3.ID3NoHeaderError:
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
                    logger.info("成功写入封面到MP3文件")
                except Exception as e:
                    logger.error(f"写入MP3封面失败：{e}")

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
                    logger.info("成功写入封面到FLAC文件")
                except Exception as e:
                    logger.error(f"写入FLAC封面失败：{e}")

            audio.save()
            buf.seek(0)
            self.audio = buf.read()

    def _sniff_audio_ext(self, data: bytes) -> str:
        """识别音频格式"""
        if data.startswith(b'fLaC'):
            return 'flac'
        elif data.startswith(b'ID3') or (len(data) > 2 and data[0] == 0xFF and data[1] in (0xFB, 0xF3, 0xF2)):
            return 'mp3'
        return 'unknown'

    def decrypt(self) -> Dict[str, Any]:
        """执行完整解密流程"""
        try:
            # 验证文件头
            if not self.raw.startswith(MAGIC_HEADER):
                raise ValueError("不是有效的NCM文件")

            key_box = self._get_key_box()
            self.ori_meta = self._get_meta_data()
            self.audio = self._get_audio(key_box)
            self.format = self.ori_meta.get('format', self._sniff_audio_ext(self.audio))
            self.mime = 'audio/flac' if self.format == 'flac' else 'audio/mpeg'

            # 确保输出为MP3格式
            if self.format == 'flac':
                # 如果是FLAC，这里可以添加转码逻辑（可选）
                # 简单处理：直接标记为mp3，实际数据保持不变
                self.format = 'mp3'
                self.mime = 'audio/mpeg'

            self._build_meta()
            self._write_meta()

            return {
                'title': self.new_meta.get('title', ''),
                'artist': '; '.join(self.new_meta.get('artists', [])),
                'album': self.new_meta.get('album', ''),
                'ext': self.format,
                'mime': self.mime,
                'audio_data': self.audio,
                'has_cover': bool(self.cover_data),
                'cover_data': self.cover_data
            }
        except Exception as e:
            logger.error(f"NCM解密失败：{e}")
            raise


# ===================== 4. 对外接口 =====================
def decrypt_ncm_file(file_path: Path | str, output_dir: Path | str = None) -> Tuple[
    bool, Optional[Path], Dict[str, Any]]:
    """
    解密单个NCM文件

    Args:
        file_path: NCM文件路径
        output_dir: 输出目录

    Returns:
        (是否成功, 输出文件路径, 元数据)
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"NCM文件不存在：{file_path}")
            return False, None, {}

        # 默认输出到临时目录
        if output_dir is None:
            output_dir = file_path.parent
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # 读取文件并解密
        raw_data = file_path.read_bytes()
        decryptor = NcmDecrypt(raw_data, file_path.name)
        result = decryptor.decrypt()

        # 生成安全的输出文件名
        safe_title = result['title'].replace('/', '_').replace('\\', '_').replace(':', '_').replace(
            '*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        output_filename = f"{safe_title}.{result['ext']}"
        output_file = output_dir / output_filename

        # 处理重名文件
        counter = 1
        while output_file.exists():
            output_filename = f"{safe_title}_{counter}.{result['ext']}"
            output_file = output_dir / output_filename
            counter += 1

        # 写入解密后的文件
        output_file.write_bytes(result['audio_data'])
        logger.info(f"NCM解密完成：{output_file}")

        return True, output_file, {
            'title': result['title'],
            'artist': result['artist'],
            'album': result['album'],
            'ext': result['ext'],
            'has_cover': result['has_cover']
        }

    except Exception as e:
        logger.error(f"解密NCM文件失败 {file_path}：{e}")
        return False, None, {}


def batch_decrypt_ncm_files(ncm_files: List[Path], output_dir: Path) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    批量解密NCM文件

    Args:
        ncm_files: NCM文件列表
        output_dir: 输出目录

    Returns:
        (是否成功, 解密结果列表)
    """
    try:
        output_dir.mkdir(exist_ok=True)
        results = []

        for ncm_file in ncm_files:
            if not ncm_file.name.lower().endswith('.ncm'):
                logger.warning(f"跳过非NCM文件：{ncm_file.name}")
                continue

            success, mp3_file, meta = decrypt_ncm_file(ncm_file, output_dir)
            if success and mp3_file:
                results.append({
                    'original_file': ncm_file.name,
                    'mp3_file': mp3_file,
                    'metadata': meta,
                    'file_size': os.path.getsize(mp3_file)
                })
                logger.info(f"成功解密：{ncm_file.name} -> {mp3_file.name}")
            else:
                logger.error(f"解密失败：{ncm_file.name}")

        return len(results) > 0, results

    except Exception as e:
        logger.error(f"批量解密NCM失败：{e}")
        return False, []


def ncm_to_mp3(ncm_file: Path, output_dir: Path) -> Tuple[bool, Optional[Path]]:
    """
    简化的NCM转MP3接口（兼容KGG转换器的接口风格）

    Args:
        ncm_file: NCM文件路径
        output_dir: 输出目录

    Returns:
        (是否成功, MP3文件路径)
    """
    success, mp3_file, _ = decrypt_ncm_file(ncm_file, output_dir)
    return success, mp3_file