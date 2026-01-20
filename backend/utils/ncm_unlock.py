import logging
import struct
import base64
import json
from encodings import idna

import pyaes
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import io
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
from mutagen.flac import FLAC, Picture
import requests
import time
import shutil

from backend.utils.unlock import ensure_dir_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ===================== 1. 常量定义 =====================
CORE_KEY = bytes.fromhex('687a4852416d736f356b496e62617857')
META_KEY = bytes.fromhex('2331346C6A6B5F215C5D2630553C2728')
MAGIC_HEADER = bytes([0x43, 0x54, 0x45, 0x4e, 0x46, 0x44, 0x41, 0x4d])

REQUEST_TIMEOUT = 10
RETRY_TIMES = 2

# 路径配置



# ===================== 2. 辅助函数 =====================
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


def is_dir_empty(dir_path: Path) -> bool:
    if not dir_path.exists():
        return True
    return not any(dir_path.iterdir())


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
                    print("成功写入封面到MP3文件")
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
                    print("成功写入封面到FLAC文件")
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
            'cover': self.cover_data
        }


# ===================== 4. 对外接口 =====================
def decrypt_ncm(file_path: str | Path, output_dir: str | Path = '.') -> Dict[str, Any]:
    file_path = Path(file_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    raw_data = file_path.read_bytes()
    decryptor = NcmDecrypt(raw_data, file_path.name)
    result = decryptor.decrypt()

    # 关键修改1：使用原始文件名替换后缀作为输出文件名，而非歌曲标题
    # 保持和后续记录的文件名一致
    output_filename = file_path.with_suffix(f".{result['ext']}").name
    # 清理非法字符（保留）
    output_filename = output_filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace(
        '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    output_file = output_dir / output_filename

    # 处理文件重名逻辑（保留）
    counter = 1
    while output_file.exists():
        output_filename = f"{file_path.stem}_{counter}.{result['ext']}"
        output_filename = output_filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*',
                                                                                                         '_').replace(
            '?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        output_file = output_dir / output_filename
        counter += 1

    output_file.write_bytes(result['audio_data'])
    print(f"\n解密完成：{output_file}")
    print(f"封面是否写入：{result['cover']}")

    # 关键修改2：将实际输出的文件路径存入结果，方便外部调用获取
    result['output_file_path'] = output_file
    return result


# ===================== 核心转换函数 =====================


def batch_convert_ncm_to_mp3(ncm_files: list[Path], output_dir: Path) -> tuple[bool, list[Path]]:
    """
    批量解密多个NCM文件

    Args:
        ncm_files: 需要解密的NCM文件路径列表
        output_dir: 解密文件的输出目录

    Returns:
        tuple[bool, list[Path]]:
            - 第一个值：是否至少成功解密一个文件
            - 第二个值：成功解密的文件路径列表
    """
    try:
        # 确保输出目录存在（复用目标函数的工具函数）
        ensure_dir_exists(output_dir)
        success_files = []

        # 检查输入的文件列表是否为空
        if not ncm_files:
            logger.warning("未传入任何需要解密的NCM文件")
            return False, []

        logger.info(f"\n找到 {len(ncm_files)} 个NCM文件，开始批量解密...\n")

        success_count = 0
        fail_count = 0
        failed_files = []

        # 遍历处理每个NCM文件（核心逻辑完全保留）
        for idx, ncm_file in enumerate(ncm_files, 1):
            # 过滤非NCM文件（和目标函数的文件类型检查逻辑对齐）
            if not ncm_file.name.lower().endswith('.ncm'):
                logger.warning(f"跳过非NCM文件: {ncm_file.name}")
                continue

            logger.info(f"\n{'=' * 50}")
            logger.info(f"正在处理 [{idx}/{len(ncm_files)}]：{ncm_file.name}")
            logger.info(f"{'=' * 50}")

            try:
                # 解密单个文件
                decrypt_ncm(ncm_file, output_dir)
                success_count += 1
                # 记录成功解密的文件路径（假设解密后为mp3格式，可根据实际调整）
                decrypted_file = output_dir / ncm_file.with_suffix('.mp3').name
                success_files.append(decrypted_file)
                logger.info(f"成功解密: {ncm_file.name} -> {decrypted_file.name}")
            except Exception as e:
                logger.error(f"\n处理文件 {ncm_file.name} 失败：{e}")
                fail_count += 1
                failed_files.append(ncm_file.name)
                continue

        # 输出统计结果
        logger.info(f"\n{'=' * 50}")
        logger.info(f"批量解密完成！")
        logger.info(f"成功：{success_count} 个文件")
        logger.info(f"失败：{fail_count} 个文件")
        if failed_files:
            logger.warning(f"失败文件列表：{failed_files}")
        logger.info(f"所有解密文件已保存到：{output_dir}")
        logger.info(f"{'=' * 50}")

        # 注意：原函数的「清空源目录」逻辑已移除（因为输入改为文件列表，不再绑定固定源目录）
        # 如果需要保留清空逻辑，可改为遍历传入的ncm_files进行删除

        # 返回值和目标函数格式完全一致
        return len(success_files) > 0, success_files

    except Exception as e:
        logger.error(f"批量解密NCM失败: {str(e)}")
        return False, []



