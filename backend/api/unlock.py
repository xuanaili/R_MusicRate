# MusicRate\backend\api\audio_resource.py 音频资源专属接口 - 专辑MP3上传/查询/删除/时长解析
from flask import request, jsonify
import traceback
import os
import os.path
import tempfile

import pymysql
from mutagen.mp3 import MP3
from mutagen import MutagenError
from werkzeug.utils import secure_filename
from pydub import AudioSegment

from ..config import AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_db, get_current_user_id
from backend.utils.decorators import login_required
from ..utils.audio_resource import merge_audio_files
from ..utils.unlock import allowed_file, decrypt_ncm_to_file, get_audio_metadata, upload_cover_to_imgbed, \
    extract_album_cover, upload_merged_audio, format_duration, get_duration_with_ffprobe

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