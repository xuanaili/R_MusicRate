# MusicRate\backend\api\audio_resource.py 音频资源专属接口 - 专辑MP3上传/查询/删除/时长解析
from flask import request, jsonify
import json
import traceback
import os
import uuid
import os.path
from ..config import AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_db, get_current_user_id
from backend.utils.decorators import login_required
import pymysql
# 音频时长解析核心库（python自带，无需额外安装）
from mutagen.mp3 import MP3
from mutagen import MutagenError

from ..utils.audio_resource import parse_audio_metadata, merge_audio_files


def register_audio_routes(app):
    """注册专辑音频资源相关路由"""

    # 1. 核心接口：管理员专属-上传/更新专辑整轨MP3 (绑定album_pool) + 删除旧文件
    @app.route('/api/album/pool/audio/upload', methods=['POST', 'OPTIONS'])
    @login_required
    def upload_album_audio():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            current_user_id = int(current_user_id)

            # ===== 校验当前用户是否为管理员 =====
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user_info = cursor.fetchone()
            if not user_info or user_info['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "仅管理员可上传/更新音频资源！"}), 403

            # ===== 获取参数和文件 =====
            album_id = request.form.get('source_pool_id') or request.form.get('album_id')
            mp3_file = request.files.get('mp3_file')
            old_mp3_url = request.form.get('old_mp3_url', '').strip()
            if not album_id or not mp3_file or not mp3_file.filename:
                cursor.close()
                return jsonify({"code": 400, "msg": "公共专辑ID和MP3文件不能为空！"}), 400

            # ===== 校验文件格式 =====
            filename = mp3_file.filename.strip()
            if not filename.lower().endswith('.mp3'):
                cursor.close()
                return jsonify({"code": 400, "msg": "仅支持上传MP3格式音频文件！"}), 400

            # ===== 校验专辑是否存在 =====
            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_id}]不存在！"}), 404

            # ===== 生成唯一文件名 防止覆盖 =====
            file_suffix = filename.split('.')[-1]
            file_prefix = filename.rsplit('.', 1)[0]
            unique_filename = f"{album_id}_{uuid.uuid4().hex[:8]}_{file_prefix}.{file_suffix}"
            save_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, unique_filename)

            # ===== 删除服务器上的旧音频文件（如果有）=====
            if old_mp3_url and old_mp3_url != '' and AUDIO_BASE_URL in old_mp3_url:
                old_filename = old_mp3_url.replace(AUDIO_BASE_URL, '')
                old_file_path = os.path.join(AUDIO_UPLOAD_FOLDER, old_filename)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        print(f"✅ 成功删除旧音频文件: {old_file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除旧音频文件失败: {str(e)}，不影响新文件上传")

            # ===== 保存新文件到本地 album_track 目录 =====
            mp3_file.save(save_file_path)

            # ===== 解析音频时长 (秒转 分:秒 格式) =====
            mp3_duration = 0
            duration_format = "0:00"
            try:
                audio = MP3(save_file_path)
                mp3_duration = int(audio.info.length)
                m = mp3_duration // 60
                s = mp3_duration % 60
                duration_format = f"{m}:{s:02d}"
            except MutagenError as e:
                print(f"⚠️ 音频时长解析失败：{str(e)}，使用默认值")
                mp3_duration = 0
                duration_format = "0:00"

            # ===== 拼接新音频访问URL =====
            mp3_url = f"{AUDIO_BASE_URL}{unique_filename}"

            # ===== 覆盖更新到album_pool表 =====
            cursor.execute('''
                UPDATE album_pool 
                SET mp3_url = %s, mp3_name = %s, mp3_duration = %s 
                WHERE id = %s
            ''', (mp3_url, filename, mp3_duration, album_id))
            db.commit()
            cursor.close()

            msg = "音频更新成功！" if old_mp3_url else "音频上传成功！"
            return jsonify({
                "code": 200,
                "msg": msg,
                "data": {
                    "mp3_url": mp3_url,
                    "mp3_name": filename,
                    "mp3_duration": mp3_duration,
                    "duration_format": duration_format
                }
            })
        except Exception as e:
            print(f"❌ 音频上传/更新出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"音频操作失败：{str(e)}"}), 500

    # 2. 通用接口：根据专辑ID查询已上传的音频信息
    @app.route('/api/album/pool/audio/info/<int:album_id>', methods=['GET'])
    @login_required
    def get_album_audio_info(album_id):
        try:
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT mp3_url, mp3_name, mp3_duration FROM album_pool WHERE id = %s
            ''', (album_id,))
            album = cursor.fetchone()
            cursor.close()

            if not album:
                return jsonify({"code": 404, "msg": "专辑不存在！"}), 404

            duration_format = "0:00"
            if album['mp3_duration'] and album['mp3_duration'] > 0:
                m = album['mp3_duration'] // 60
                s = album['mp3_duration'] % 60
                duration_format = f"{m}:{s:02d}"

            return jsonify({
                "code": 200,
                "msg": "查询成功",
                "data": {
                    "mp3_url": album['mp3_url'],
                    "mp3_name": album['mp3_name'],
                    "mp3_duration": album['mp3_duration'],
                    "duration_format": duration_format
                }
            })
        except Exception as e:
            print(f"❌ 查询专辑音频信息失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500

    # ✅ ✅ ✅ 核心新增：3. 管理员专属-删除音频资源接口 ✅ ✅ ✅
    @app.route('/api/album/pool/audio/delete', methods=['POST', 'OPTIONS'])
    @login_required
    def delete_album_audio():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            current_user_id = int(current_user_id)

            # ===== 校验当前用户是否为管理员 =====
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user_info = cursor.fetchone()
            if not user_info or user_info['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "仅管理员可删除音频资源！"}), 403

            # ===== 获取删除参数 =====
            req_data = request.get_json()
            album_id = req_data.get('source_pool_id')
            mp3_url = req_data.get('mp3_url', '').strip()

            if not album_id or not mp3_url:
                cursor.close()
                return jsonify({"code": 400, "msg": "专辑ID和音频URL不能为空！"}), 400

            # ===== 校验专辑是否存在 =====
            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_id}]不存在！"}), 404

            # ===== 1. 删除服务器上的音频文件 =====
            if mp3_url and AUDIO_BASE_URL in mp3_url:
                file_name = mp3_url.replace(AUDIO_BASE_URL, '')
                file_path = os.path.join(AUDIO_UPLOAD_FOLDER, file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"✅ 成功删除音频文件: {file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除音频文件失败: {str(e)}")

            # ===== 2. 清空数据库里的音频相关字段 核心！！！ =====
            cursor.execute('''
                UPDATE album_pool 
                SET mp3_url = NULL, mp3_name = NULL, mp3_duration = NULL 
                WHERE id = %s
            ''', (album_id,))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "音频资源删除成功！"
            })
        except Exception as e:
            print(f"❌ 音频删除出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"音频删除失败：{str(e)}"}), 500

    # 4. ✅ 核心新增：查询【当前用户】有音频资源的专辑列表 (给播放列表专用)
    # 逻辑：查用户所有album -> 提取source_pool_id -> 关联album_pool筛选有mp3_url的专辑并返回详情
    @app.route('/api/album/user/has-audio', methods=['GET'])
    @login_required
    def get_user_has_audio_albums():
        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            current_user_id = int(current_user_id)

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # ========== 核心联表查询 ==========
            # 1. 查当前用户的所有专辑，获取source_pool_id
            # 2. 关联album_pool表，只筛选 mp3_url不为空 的专辑
            # 3. 返回完整专辑信息+音频地址+时长，前端直接渲染
            cursor.execute('''
                SELECT 
                    ap.id, ap.album_name, ap.singer, ap.cover_img, ap.release_year, 
                    ap.mp3_url, ap.mp3_name, ap.mp3_duration, ap.my_score, a.create_time,
                    a.tracks, a.tracks_time, a.audioSrc
                FROM album a
                LEFT JOIN album_pool ap ON a.source_pool_id = ap.id
                WHERE a.user_id = %s AND ap.mp3_url IS NOT NULL AND ap.mp3_url != ''
                ORDER BY a.create_time DESC
            ''', (current_user_id,))

            # 查询结果转列表
            album_list = cursor.fetchall()
            cursor.close()

            # 格式化处理：1.时长转 分:秒 格式 2.处理空值 3.转json格式兼容前端
            format_album_list = []
            for album in album_list:
                # 音频时长格式化 秒 -> m:ss
                duration_format = "0:00"
                if album['mp3_duration'] and album['mp3_duration'] > 0:
                    m = album['mp3_duration'] // 60
                    s = album['mp3_duration'] % 60
                    duration_format = f"{m}:{s:02d}"

                # 处理曲目/时长字段的空值，前端无需再做判断
                tracks = json.loads(album['tracks']) if album['tracks'] else []
                tracks_time = json.loads(album['tracks_time']) if album['tracks_time'] else []

                format_album_list.append({
                    "id": album['id'],  # album_pool的id
                    "album_name": album['album_name'],
                    "singer": album['singer'],
                    "cover_img": album['cover_img'],
                    "release_year": album['release_year'],
                    "mp3_url": album['mp3_url'],  # 核心：音频地址
                    "mp3_name": album['mp3_name'],
                    "mp3_duration": album['mp3_duration'],
                    "duration_format": duration_format,  # 格式化后的时长
                    "my_score": album['my_score'] or 0.0,  # 评分
                    "create_time": album['create_time'],  # 添加时间（用于排序）
                    "tracks": tracks,  # 曲目列表
                    "tracks_time": tracks_time,  # 曲目对应时长
                    "audioSrc": album['mp3_url']  # 给前端播放用的别名，和原逻辑一致
                })

            return jsonify({
                "code": 200,
                "msg": "查询成功，共找到 {} 张带音频的专辑".format(len(format_album_list)),
                "data": format_album_list
            })
        except Exception as e:
            print(f"❌ 查询用户音频专辑失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500

    # ========== 新增：1. 音频解析接口（接收多文件，解析元数据） ==========
    @app.route('/api/audio/unlock/parse', methods=['POST', 'OPTIONS'])
    @login_required
    def parse_audio_files():
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

            # 获取上传的音频文件
            audio_files = request.files.getlist('audio_files')
            if not audio_files or len(audio_files) == 0:
                cursor.close()
                return jsonify({"code": 400, "msg": "请上传至少一个音频文件！"}), 400

            # 临时保存上传的文件
            temp_files = []
            songs_info = []
            total_duration = 0

            for idx, file in enumerate(audio_files):
                # 校验文件格式
                filename = file.filename.strip()
                ext = filename.lower().split('.')[-1]
                if ext not in ['mp3', 'flac', 'wav', 'm4a']:
                    continue

                # 生成临时文件名
                temp_filename = f"temp_{uuid.uuid4().hex[:8]}.{ext}"
                temp_path = os.path.join(AUDIO_UPLOAD_FOLDER, 'temp', temp_filename)

                # 创建临时目录
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)

                # 保存临时文件
                file.save(temp_path)
                temp_files.append(temp_path)

                # 解析元数据
                metadata = parse_audio_metadata(temp_path)
                total_duration += metadata['duration']
                songs_info.append({
                    'index': idx + 1,
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'duration': metadata['duration'],
                    'duration_format': f"{metadata['duration'] // 60}:{metadata['duration'] % 60:02d}"
                })

            if len(temp_files) == 0:
                cursor.close()
                return jsonify({"code": 400, "msg": "没有有效的音频文件！"}), 400

            # 合并音频文件
            merged_filename = f"merged_{uuid.uuid4().hex[:8]}.mp3"
            merged_path = os.path.join(AUDIO_UPLOAD_FOLDER, merged_filename)

            if not merge_audio_files(temp_files, merged_path):
                # 清理临时文件
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                cursor.close()
                return jsonify({"code": 500, "msg": "音频合并失败！"}), 500

            # 清理临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            # 生成合并后音频的URL
            merged_url = f"{AUDIO_BASE_URL}{merged_filename}"

            # 解析合并后音频的时长
            merged_duration = 0
            try:
                audio = MP3(merged_path)
                merged_duration = int(audio.info.length)
            except MutagenError as e:
                print(f"⚠️ 合并音频时长解析失败：{str(e)}，使用累加值")
                merged_duration = total_duration

            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"成功解析{len(songs_info)}首曲目并合并",
                "data": {
                    "mp3_url": merged_url,
                    "mp3_duration": merged_duration,
                    "songs": songs_info,
                    "total_songs": len(songs_info),
                    "total_duration": total_duration
                }
            })
        except Exception as e:
            print(f"❌ 音频解析合并出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"解析失败：{str(e)}"}), 500

    # ========== 新增：2. 上传合并后的音频到专辑池 ==========
    @app.route('/api/album/pool/audio/upload/merged', methods=['POST', 'OPTIONS'])
    @login_required
    def upload_merged_audio():
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
            # 从URL获取文件路径
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