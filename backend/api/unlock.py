from flask import request, jsonify, Blueprint
import json
import traceback
import os
import re
import tempfile
import shutil
from werkzeug.utils import secure_filename
from mutagen.easyid3 import EasyID3
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
import subprocess
from pydub import AudioSegment
import uuid
import pymysql

# 导入配置（确保路径正确）
from backend.config import UPLOAD_FOLDER, COVER_BASE_URL, AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER, MYSQL_CONFIG
# 移除不需要的db_utils导入（不再操作数据库）

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

# 允许的音频格式
ALLOWED_EXTENSIONS = {'mp3', 'ogg', 'flac', 'wav', 'm4a', 'mp4'}


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


# ✅ 新增：合并多个音频文件为一个整轨MP3
def merge_audio_files(audio_files, output_dir, album_name, artist):
    """
    合并多个音频文件为一个整轨MP3
    :param audio_files: 音频文件路径列表（已排序）
    :param output_dir: 输出目录
    :param album_name: 专辑名（用于生成文件名）
    :param artist: 歌手名（用于生成文件名）
    :return: 合并后的MP3文件路径
    """
    if not audio_files or len(audio_files) == 0:
        return ""

    try:
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成合并后的文件名（修复特殊字符）
        safe_album_name = re.sub(r'[\\/:*?"<>|]', '_', album_name)
        safe_artist = re.sub(r'[\\/:*?"<>|]', '_', artist)
        merge_filename = f"{safe_artist}-{safe_album_name}_{uuid.uuid4().hex[:8]}.mp3"
        merge_file_path = os.path.join(output_dir, merge_filename)

        # 如果只有一个文件，直接转换为MP3（确保格式统一）
        if len(audio_files) == 1:
            cmd = [
                FFMPEG_PATH,
                '-i', audio_files[0],
                '-acodec', 'mp3',
                '-b:a', '320k',  # 320kbps高质量
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                merge_file_path
            ]
        else:
            # 多个文件，先生成文件列表，再合并（修复路径问题）
            list_file_path = os.path.join(output_dir, "merge_list.txt")
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for file_path in audio_files:
                    # FFmpeg的文件列表格式：file '路径' - 修复特殊字符
                    f.write(f"file '{file_path.replace("'", "\\'")}'\n")

            # 执行合并命令
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

        # 执行FFmpeg命令（修复shell=False）
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


# ✅ 修改：仅上传合并后的MP3文件，不更新数据库
def upload_merged_audio(merge_file_path):
    """
    上传合并后的MP3到音频目录，返回访问URL（不再操作数据库）
    """
    if not merge_file_path or not os.path.exists(merge_file_path):
        return {"code": 400, "msg": "文件为空", "data": None}

    try:
        # 确保音频上传目录存在
        if not os.path.exists(AUDIO_UPLOAD_FOLDER):
            os.makedirs(AUDIO_UPLOAD_FOLDER)

        # ===== 1. 生成唯一文件名 =====
        filename = os.path.basename(merge_file_path)
        file_suffix = filename.split('.')[-1]
        file_prefix = filename.rsplit('.', 1)[0]
        # 生成唯一文件名（不再关联album_id）
        unique_filename = f"merged_{uuid.uuid4().hex[:12]}_{file_prefix}.{file_suffix}"
        save_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, unique_filename)

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
        mp3_url = f"{AUDIO_BASE_URL}{unique_filename}"

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
                "mp3_name": filename,
                "mp3_duration": mp3_duration,
                "duration_format": duration_format
            }
        }
    except Exception as e:
        print(f"❌ 上传合并音频失败：{e}")
        return {"code": 500, "msg": f"上传失败：{str(e)}", "data": None}


def register_unlock_routes(app):
    """注册音频解析相关路由"""

    # ========== 音频解析 ==========
    @app.route('/api/audio/unlock/parse', methods=['POST', 'OPTIONS'])
    def unlock_parse_audio():
        """音频文件解析接口（批量上传解析）- 不再操作数据库"""

        try:
            # 检查是否有文件上传
            if 'audio_files' not in request.files:
                return jsonify({
                    'code': 400,
                    'msg': '请上传音频文件'
                }), 200

            files = request.files.getlist('audio_files')
            if not files:
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个音频文件'
                }), 200

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_files = []
                file_metadatas = []
                temp_cover_files = []  # 记录临时封面文件，用于清理

                # 保存上传的文件并提取元数据
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_ext = filename.rsplit('.', 1)[1].lower()
                        file_path = os.path.join(temp_dir, filename)
                        file.save(file_path)

                        # 提取元数据
                        metadata = get_audio_metadata(file_path, file_ext)
                        file_metadatas.append(metadata)
                        audio_files.append(file_path)

                        # 记录临时封面文件
                        if metadata['cover_img'] and os.path.exists(metadata['cover_img']):
                            temp_cover_files.append(metadata['cover_img'])

                if not file_metadatas:
                    return jsonify({
                        'code': 400,
                        'msg': '没有有效的音频文件'
                    }), 200

                # 按曲目编号排序
                file_metadatas.sort(key=lambda x: int(x['track'].split('/')[0]) if x['track'].isdigit() else 0)

                # 构建解析结果
                parse_result = {
                    'album_name': file_metadatas[0]['album'],
                    'album_singer': file_metadatas[0]['artist'],
                    'mp3_duration':'',
                    'cover_img': '',
                    'mp3_url': '',  # 新增：合并后的MP3 URL
                    'songs': []
                }

                # 提取专辑封面并上传到本地图床
                cover_img_url = ""
                # 优先使用元数据中的封面
                for metadata in file_metadatas:
                    if metadata['cover_img']:
                        cover_img_url = upload_cover_to_imgbed(metadata['cover_img'])
                        if cover_img_url:
                            break
                # 如果元数据中没有封面，用FFmpeg提取
                if not cover_img_url:
                    cover_path = extract_album_cover(audio_files, temp_dir)
                    if cover_path:
                        cover_img_url = upload_cover_to_imgbed(cover_path)

                # 赋值封面URL
                parse_result['cover_img'] = cover_img_url

                # ✅ 步骤1：合并音频文件
                merge_file_path = merge_audio_files(
                    audio_files=audio_files,
                    output_dir=temp_dir,
                    album_name=parse_result['album_name'],
                    artist=parse_result['album_singer']
                )

                # ✅ 步骤2：上传合并后的音频（不再需要album_id）
                if merge_file_path and os.path.exists(merge_file_path):
                    upload_result = upload_merged_audio(merge_file_path)
                    if upload_result['code'] == 200:
                        parse_result['mp3_url'] = upload_result['data']['mp3_url']
                        parse_result['mp3_duration'] = upload_result['data']['mp3_duration']  # 关键赋值
                    else:
                        print(f"音频上传失败：{upload_result['msg']}")
                else:
                    print(f"合并后的音频文件不存在：{merge_file_path}")

                # 计算时间戳并构建单曲列表
                total_duration = 0
                for idx, metadata in enumerate(file_metadatas):
                    # 格式化时间戳
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