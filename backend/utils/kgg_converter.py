import os
import shutil
import subprocess
import time
from pathlib import Path
import logging
from mutagen.oggvorbis import OggVorbis
import base64
from io import BytesIO
from PIL import Image

from backend.utils.unlock import add_mp3_metadata, ensure_dir_exists, get_ffmpeg_exe

# ===================== 配置区域 =====================
# 请根据你的实际路径配置
KGG_DEC_EXE_PATH = Path("portable/unlock/kgg-dec.exe")  # kgg-dec.exe路径
FFMPEG_PATH = None  # FFmpeg路径，会自动检测
OGG_TITLE_FILE_PATH = ""  # 标题列表文件路径（可选）

# 音频转换参数
BITRATE = "192k"  # MP3比特率
SAMPLING_RATE = 44100  # 采样率
CHANNELS = 2  # 声道数

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ===================== 工具函数 =====================





def run_command(cmd: list, timeout: int = 60, cwd: str = None) -> tuple[bool, str]:
    """运行系统命令"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            cwd=cwd
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, f"命令执行超时（{timeout}秒）"
    except Exception as e:
        return False, str(e)


def kgg_to_ogg(kgg_file: Path, output_dir: Path) -> tuple[bool, Path | None]:
    """将KGG文件转换为OGG文件"""
    try:
        # 确保输出目录存在
        ensure_dir_exists(output_dir)

        # 复制kgg-dec.exe到输出目录
        dec_exe_dst = output_dir / KGG_DEC_EXE_PATH.name
        shutil.copy2(KGG_DEC_EXE_PATH, dec_exe_dst)

        # 复制KGG文件到输出目录
        kgg_dst = output_dir / kgg_file.name
        shutil.copy2(kgg_file, kgg_dst)

        # 运行kgg-dec.exe
        logger.info(f"开始转换KGG到OGG: {kgg_file.name}")
        success, output = run_command([str(dec_exe_dst)], cwd=str(output_dir))

        if not success:
            logger.error(f"kgg-dec.exe运行失败: {output}")
            return False, None

        # 等待文件生成
        time.sleep(2)

        # 查找生成的OGG文件
        ogg_files = list(output_dir.glob("*.ogg")) + list(output_dir.glob("*.OGG"))
        if not ogg_files:
            logger.error("未找到生成的OGG文件")
            return False, None

        # 重命名OGG文件（移除_kgg-dec后缀）
        ogg_file = ogg_files[0]
        new_ogg_name = ogg_file.name.replace("_kgg-dec", "")
        new_ogg_path = output_dir / new_ogg_name

        if ogg_file != new_ogg_path and os.path.exists(new_ogg_path):
            os.remove(new_ogg_path)
        if ogg_file != new_ogg_path:
            os.rename(ogg_file, new_ogg_path)

        # 清理临时文件
        for temp_file in [dec_exe_dst, kgg_dst, ogg_file]:
            if temp_file.exists() and temp_file != new_ogg_path:
                os.remove(temp_file)

        logger.info(f"KGG转OGG成功: {new_ogg_path.name}")
        return True, new_ogg_path

    except Exception as e:
        logger.error(f"KGG转OGG失败: {str(e)}")
        return False, None


def extract_ogg_cover(ogg_file: Path) -> bytes | None:
    """提取OGG文件封面"""
    try:
        audio = OggVorbis(ogg_file)

        # 查找封面标签
        cover_tags = ["metadata_block_picture", "COVERART", "albumart"]
        for tag_name in cover_tags:
            if tag_name in audio:
                cover_data = audio[tag_name]
                if isinstance(cover_data, list):
                    cover_data = cover_data[0]

                # 解码封面数据
                if isinstance(cover_data, str):
                    cover_bytes = base64.b64decode(cover_data)
                elif isinstance(cover_data, bytes):
                    cover_bytes = cover_data
                else:
                    continue

                # 去除OGG封面头信息
                if len(cover_bytes) > 22:
                    img_data = cover_bytes[22:]
                    img = Image.open(BytesIO(img_data))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    buf = BytesIO()
                    img.save(buf, format='JPEG', quality=90)
                    return buf.getvalue()

        return None
    except Exception as e:
        logger.warning(f"提取封面失败: {str(e)}")
        return None


def get_ogg_metadata(ogg_file: Path) -> dict:
    """提取OGG文件元数据"""
    try:
        audio = OggVorbis(ogg_file)
        metadata = {
            "title": audio.get("title", [ogg_file.stem.replace("_kgg-dec", "")])[0],
            "artist": audio.get("artist", ["未知艺术家"])[0],
            "album": audio.get("album", ["未知专辑"])[0],
            "tracknumber": "",
            "cover": extract_ogg_cover(ogg_file)
        }
        return metadata
    except Exception as e:
        logger.warning(f"读取OGG元数据失败: {str(e)}")
        return {
            "title": ogg_file.stem.replace("_kgg-dec", ""),
            "artist": "未知艺术家",
            "album": "未知专辑",
            "tracknumber": "",
            "cover": None
        }




def ogg_to_mp3(ogg_file: Path, output_dir: Path) -> tuple[bool, Path | None]:
    """将OGG文件转换为MP3文件"""
    try:
        ensure_dir_exists(output_dir)

        # 获取FFmpeg路径
        ffmpeg_exe = get_ffmpeg_exe()

        # 生成输出文件名
        mp3_filename = ogg_file.stem + ".mp3"
        mp3_path = output_dir / mp3_filename

        # 构建FFmpeg命令
        cmd = [
            ffmpeg_exe,
            "-i", str(ogg_file),
            "-acodec", "libmp3lame",
            "-b:a", BITRATE,
            "-ar", str(SAMPLING_RATE),
            "-ac", str(CHANNELS),
            "-y",
            "-loglevel", "error",
            str(mp3_path)
        ]

        # 执行转换
        logger.info(f"开始转换OGG到MP3: {ogg_file.name}")
        success, output = run_command(cmd)

        if not success:
            logger.error(f"FFmpeg转换失败: {output}")
            if mp3_path.exists():
                os.remove(mp3_path)
            return False, None

        # 添加元数据
        metadata = get_ogg_metadata(ogg_file)
        add_mp3_metadata(mp3_path, metadata)

        logger.info(f"OGG转MP3成功: {mp3_path.name}")
        return True, mp3_path

    except Exception as e:
        logger.error(f"OGG转MP3失败: {str(e)}")
        return False, None


def kgg_to_mp3(kgg_file: Path, output_dir: Path) -> tuple[bool, Path | None]:
    """一站式将KGG转换为MP3"""
    try:
        # 创建临时目录
        temp_dir = output_dir / "temp_kgg_convert"
        ensure_dir_exists(temp_dir)

        # Step 1: KGG转OGG
        success, ogg_file = kgg_to_ogg(kgg_file, temp_dir)
        if not success or not ogg_file:
            return False, None

        # Step 2: OGG转MP3
        success, mp3_file = ogg_to_mp3(ogg_file, output_dir)

        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

        if success and mp3_file:
            return True, mp3_file
        else:
            return False, None

    except Exception as e:
        logger.error(f"KGG转MP3失败: {str(e)}")
        return False, None


# 在原有代码基础上，新增批量转换函数
def batch_convert_kgg_to_mp3(kgg_files: list[Path], output_dir: Path) -> tuple[bool, list[Path]]:
    """批量转换多个KGG文件到MP3"""
    try:
        ensure_dir_exists(output_dir)
        success_files = []

        for kgg_file in kgg_files:
            if not kgg_file.name.lower().endswith('.kgg'):
                logger.warning(f"跳过非KGG文件: {kgg_file.name}")
                continue

            # 转换单个KGG文件
            success, mp3_file = kgg_to_mp3(kgg_file, output_dir)
            if success and mp3_file:
                success_files.append(mp3_file)
                logger.info(f"成功转换: {kgg_file.name} -> {mp3_file.name}")
            else:
                logger.error(f"转换失败: {kgg_file.name}")

        return len(success_files) > 0, success_files

    except Exception as e:
        logger.error(f"批量转换KGG失败: {str(e)}")
        return False, []