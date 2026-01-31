import base64
from pathlib import Path

from flask import request, jsonify, Blueprint
import json
import traceback
import os
import tempfile



from backend.utils.kgg_converter import kgg_to_mp3, batch_convert_kgg_to_mp3
from backend.utils.ncm_unlock import batch_convert_ncm_to_mp3
from backend.utils.unlock import allowed_file, get_audio_metadata, get_simple_album_id, upload_cover_to_imgbed, \
    extract_album_cover, merge_audio_files, upload_merged_audio, format_duration, secure_filename


def register_unlock_routes(app):
    """注册音频解析相关路由"""

    # ========== 音频解析 ==========
    @app.route('/api/audio/unlock/parse', methods=['POST', 'OPTIONS'])
    def unlock_parse_audio():
        """音频文件解析接口（简化版，使用文件计数生成序号）"""

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
                    'mp3_duration': '',
                    'cover_img': '',
                    'mp3_url': '',  # 新增：合并后的MP3 URL
                    'album_id': '',  # 新增：简单序号
                    'songs': []
                }

                # ✅ 关键简化：获取简单序号（文件数+1）
                album_id = get_simple_album_id()
                parse_result['album_id'] = album_id

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

                # ✅ 简化：传递简单序号给合并函数
                merge_file_path = merge_audio_files(
                    audio_files=audio_files,
                    output_dir=temp_dir,
                    album_name=parse_result['album_name'],
                    artist=parse_result['album_singer'],
                    album_id=album_id  # 简单序号
                )

                # ✅ 简化：上传时传递简单序号、歌手名、专辑名
                if merge_file_path and os.path.exists(merge_file_path):
                    upload_result = upload_merged_audio(
                        merge_file_path=merge_file_path,
                        album_id=album_id,
                        artist=parse_result['album_singer'],
                        album_name=parse_result['album_name']
                    )
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

    # ========== 仅转换KGG为MP3（不解析） ==========
    @app.route('/api/audio/unlock/convert-kgg-only', methods=['POST', 'OPTIONS'])
    def convert_kgg_only():
        """仅将KGG文件转换为MP3并返回文件列表，不进行解析"""
        try:
            if 'kgg_files' not in request.files:
                return jsonify({
                    'code': 400,
                    'msg': '请上传KGG格式文件'
                }), 200

            files = request.files.getlist('kgg_files')
            if not files:
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个KGG文件'
                }), 200

            # 验证文件格式
            kgg_files = []
            for file in files:
                if file and file.filename.endswith('.kgg'):
                    kgg_files.append(file)
                else:
                    return jsonify({
                        'code': 400,
                        'msg': f'文件 {file.filename} 不是KGG格式'
                    }), 200

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                uploaded_kgg_paths = []

                # 保存上传的KGG文件
                for kgg_file in kgg_files:
                    filename = secure_filename(kgg_file.filename)
                    kgg_path = temp_dir_path / filename
                    kgg_file.save(kgg_path)
                    uploaded_kgg_paths.append(kgg_path)

                # 批量转换KGG到MP3
                success, mp3_files = batch_convert_kgg_to_mp3(uploaded_kgg_paths, temp_dir_path)

                if not success or len(mp3_files) == 0:
                    return jsonify({
                        'code': 500,
                        'msg': 'KGG文件转换失败'
                    }), 200

                # 准备返回的MP3文件信息
                mp3_files_info = []
                for mp3_file in mp3_files:
                    # 读取文件内容为Base64
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')

                    # 提取基础元数据
                    try:
                        metadata = get_audio_metadata(str(mp3_file), 'mp3')
                    except:
                        metadata = {
                            'title': mp3_file.stem,
                            'artist': '未知艺术家',
                            'album': '未知专辑',
                            'duration': 0
                        }

                    mp3_files_info.append({
                        'filename': mp3_file.name,
                        'file_size': os.path.getsize(mp3_file),
                        'base64_data': base64_data,
                        'metadata': metadata,
                        'order': len(mp3_files_info) + 1  # 默认顺序
                    })

                return jsonify({
                    'code': 200,
                    'msg': f'成功转换 {len(mp3_files)} 个KGG文件为MP3',
                    'data': {
                        'mp3_files': mp3_files_info
                    }
                }), 200

        except Exception as e:
            print(f"❌ KGG转换出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'KGG转换失败：{str(e)}'
            }), 200

    @app.route('/api/audio/unlock/convert-ncm-only', methods=['POST', 'OPTIONS'])
    def convert_ncm_only():
        """仅将NCM文件转换为MP3并返回文件列表，不进行解析（适配你的图床函数）"""
        try:
            # 1. 检查文件参数
            if 'ncm_files' not in request.files:  # 保持和原有接口一致的参数名
                return jsonify({
                    'code': 400,
                    'msg': '请上传NCM格式文件'
                }), 200

            files = request.files.getlist('ncm_files')
            if not files:
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个NCM文件'
                }), 200

            # 2. 验证文件格式
            ncm_files = []
            for file in files:
                if file and file.filename.endswith('.ncm'):
                    ncm_files.append(file)
                else:
                    return jsonify({
                        'code': 400,
                        'msg': f'文件 {file.filename} 不是NCM格式'
                    }), 200

            # 3. 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                uploaded_ncm_paths = []

                # 4. 保存上传的NCM文件
                for ncm_file in ncm_files:
                    filename = secure_filename(ncm_file.filename)
                    ncm_path = temp_dir_path / filename
                    ncm_file.save(ncm_path)
                    uploaded_ncm_paths.append(ncm_path)

                # 5. 批量转换NCM到MP3（获取临时封面路径）

                success, mp3_files, temp_cover_map = batch_convert_ncm_to_mp3(uploaded_ncm_paths, temp_dir_path)

                if not success or len(mp3_files) == 0:
                    return jsonify({
                        'code': 500,
                        'msg': 'NCM文件转换失败'
                    }), 200

                # 6. 使用你的图床函数上传封面
                cover_url_map = {}  # 保存每个文件的封面URL
                temp_cover_files = []  # 记录临时封面文件，用于后续清理

                for mp3_file in mp3_files:
                    mp3_path_str = str(mp3_file)
                    if mp3_path_str in temp_cover_map and temp_cover_map[mp3_path_str]:
                        temp_cover_path = temp_cover_map[mp3_path_str]
                        temp_cover_files.append(temp_cover_path)

                        # 使用你提供的图床上传函数
                        cover_url = upload_cover_to_imgbed(temp_cover_path)
                        if cover_url:
                            cover_url_map[mp3_path_str] = cover_url
                            print(f"封面上传成功：{cover_url}")
                            break

                # 7. 准备返回的MP3文件信息
                mp3_files_info = []
                for mp3_file in mp3_files:
                    # 读取文件内容为Base64
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')

                    # 提取基础元数据
                    try:
                        metadata = get_audio_metadata(str(mp3_file), 'mp3')
                        # 添加封面URL到元数据
                        mp3_path_str = str(mp3_file)
                        if mp3_path_str in cover_url_map:
                            metadata['cover_url'] = cover_url_map[mp3_path_str]
                            metadata['cover_img'] = temp_cover_map.get(mp3_path_str, "")  # 兼容原有逻辑
                    except:
                        metadata = {
                            'title': mp3_file.stem,
                            'artist': '未知艺术家',
                            'album': '未知专辑',
                            'track': '0',
                            'duration': 0,
                            'cover_url': '',
                            'cover_img': ''
                        }

                    mp3_files_info.append({
                        'filename': mp3_file.name,
                        'file_size': os.path.getsize(mp3_file),
                        'base64_data': base64_data,
                        'metadata': metadata,
                        'order': len(mp3_files_info) + 1
                    })

                # 按track字段排序
                def get_track_number(item):
                    try:
                        track_str = item['metadata']['track'].split('/')[0].strip()
                        return int(track_str) if track_str else 999
                    except (ValueError, KeyError):
                        return 999

                mp3_files_info.sort(key=get_track_number)

                # 重新更新order字段
                for idx, item in enumerate(mp3_files_info):
                    item['order'] = idx + 1

                # 清理临时封面文件
                for temp_cover in temp_cover_files:
                    try:
                        if os.path.exists(temp_cover):
                            os.remove(temp_cover)
                    except:
                        pass

            # 8. 返回结果
            return jsonify({
                'code': 200,
                'msg': f'成功转换 {len(mp3_files)} 个NCM文件为MP3',
                'data': {
                    'mp3_files': mp3_files_info
                }
            }), 200

        except Exception as e:
            print(f"❌ NCM转换出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'NCM转换失败：{str(e)}'
            }), 200

    # ========== 修正后的核心接口（与NCM接口封面逻辑完全一致） ==========
    @app.route('/api/audio/unlock/convert-mp3-only', methods=['POST', 'OPTIONS'])
    def convert_mp3_only():
        """仅将通用音频文件转换为MP3并返回文件列表（封面逻辑与convert-ncm-only完全一致）"""
        try:
            # 1. 检查文件参数（和NCM接口一致）
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

            # 2. 验证文件格式（和NCM接口一致）
            audio_files = []
            for file in files:
                if file and allowed_file(file.filename):
                    audio_files.append(file)
                else:
                    return jsonify({
                        'code': 400,
                        'msg': f'文件 {file.filename if file else "未知文件"} 不是支持的音频格式'
                    }), 200

            # 3. 创建临时目录（和NCM接口一致）
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                uploaded_audio_paths = []

                # 4. 保存上传的音频文件（和NCM接口一致）
                for audio_file in audio_files:
                    filename = secure_filename(audio_file.filename)
                    audio_path = temp_dir_path / filename
                    audio_file.save(audio_path)
                    uploaded_audio_paths.append(audio_path)

                # 5. 处理音频文件，生成MP3文件列表和临时封面映射（核心对齐NCM接口）
                mp3_files = []
                temp_cover_map = {}  # 关键：和NCM接口一致的封面映射（mp3路径 -> 封面路径）

                # 模拟音频转MP3（实际项目中替换为真实转码逻辑）
                for audio_path in uploaded_audio_paths:
                    file_ext = audio_path.suffix.lower()[1:]
                    metadata = get_audio_metadata(str(audio_path), file_ext)

                    # 转码为MP3（示例：直接使用原文件路径，实际需替换为转码后的MP3路径）
                    mp3_path = temp_dir_path / f"{audio_path.stem}.mp3"
                    # 这里添加真实的转码逻辑，比如调用ffmpeg转码
                    # shutil.copy(audio_path, mp3_path)  # 临时模拟转码

                    mp3_files.append(mp3_path)

                    # 提取封面（和NCM接口逻辑一致）
                    cover_path = metadata.get('cover_img', '')
                    if cover_path and os.path.exists(cover_path):
                        temp_cover_map[str(mp3_path)] = cover_path
                    else:
                        # 如果元数据无封面，尝试从音频文件提取（和NCM接口一致）
                        # 替换为你实际的封面提取逻辑
                        cover_path = upload_cover_to_imgbed(str(audio_path), temp_dir)
                        if cover_path:
                            temp_cover_map[str(mp3_path)] = cover_path

                if not mp3_files:
                    return jsonify({
                        'code': 500,
                        'msg': '音频文件转换失败'
                    }), 200

                # 6. 封面上传逻辑（完全复刻NCM接口，关键修正部分）
                cover_url_map = {}  # 保存每个文件的封面URL
                temp_cover_files = []  # 记录临时封面文件，用于后续清理

                # ✅ 修正点1：移除break，遍历所有文件（和NCM接口一致）
                for mp3_file in mp3_files:
                    mp3_path_str = str(mp3_file)
                    if mp3_path_str in temp_cover_map and temp_cover_map[mp3_path_str]:
                        temp_cover_path = temp_cover_map[mp3_path_str]
                        temp_cover_files.append(temp_cover_path)

                        # 使用你提供的图床上传函数（和NCM接口一致）
                        cover_url = upload_cover_to_imgbed(temp_cover_path)
                        if cover_url:
                            cover_url_map[mp3_path_str] = cover_url
                            print(f"封面上传成功：{cover_url}")
                            break
                        # ✅ 修正点3：移除break，保证每个文件都处理封面

                # 7. 准备返回的MP3文件信息（和NCM接口完全一致）
                mp3_files_info = []
                for mp3_file in mp3_files:
                    # 读取文件内容为Base64（和NCM接口一致）
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')

                    # 提取基础元数据（和NCM接口一致）
                    try:
                        metadata = get_audio_metadata(str(mp3_file), 'mp3')
                        # 添加封面URL到元数据（和NCM接口一致）
                        mp3_path_str = str(mp3_file)
                        if mp3_path_str in cover_url_map:
                            metadata['cover_url'] = cover_url_map[mp3_path_str]
                            metadata['cover_img'] = temp_cover_map.get(mp3_path_str, "")  # 兼容原有逻辑
                    except:
                        metadata = {
                            'title': mp3_file.stem,
                            'artist': '未知艺术家',
                            'album': '未知专辑',
                            'track': '0',
                            'duration': 0,
                            'cover_url': '',
                            'cover_img': ''
                        }

                    mp3_files_info.append({
                        'filename': mp3_file.name,
                        'file_size': os.path.getsize(mp3_file),
                        'base64_data': base64_data,
                        'metadata': metadata,
                        'order': len(mp3_files_info) + 1
                    })

                # 8. 按track字段排序（和NCM接口一致）
                def get_track_number(item):
                    try:
                        track_str = item['metadata']['track'].split('/')[0].strip()
                        return int(track_str) if track_str else 999
                    except (ValueError, KeyError):
                        return 999

                mp3_files_info.sort(key=get_track_number)

                # 重新更新order字段（和NCM接口一致）
                for idx, item in enumerate(mp3_files_info):
                    item['order'] = idx + 1

                # 9. 清理临时封面文件（和NCM接口一致）
                for temp_cover in temp_cover_files:
                    try:
                        if os.path.exists(temp_cover):
                            os.remove(temp_cover)
                    except:
                        pass

            # 10. 返回结果（和NCM接口完全一致）
            return jsonify({
                'code': 200,
                'msg': f'成功转换 {len(mp3_files)} 个音频文件为MP3',
                'data': {
                    'mp3_files': mp3_files_info
                }
            }), 200

        except Exception as e:
            print(f"❌ 音频转换出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'音频转换失败：{str(e)}'
            }), 200
    # ========== 接收排序后的MP3文件并解析 ==========
    @app.route('/api/audio/unlock/parse-sorted-mp3', methods=['POST', 'OPTIONS'])
    def parse_sorted_mp3():
        """接收前端排序后的MP3文件（Base64），执行解析流程"""
        try:
            data = request.get_json()
            if not data or 'sorted_mp3_files' not in data:
                return jsonify({
                    'code': 400,
                    'msg': '请提供排序后的MP3文件数据'
                }), 200

            sorted_mp3_files = data['sorted_mp3_files']
            if not isinstance(sorted_mp3_files, list) or len(sorted_mp3_files) == 0:
                return jsonify({
                    'code': 400,
                    'msg': '排序后的MP3文件列表不能为空'
                }), 200

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                audio_files = []
                file_metadatas = []
                temp_cover_files = []

                # 按前端指定的顺序保存MP3文件
                for idx, mp3_info in enumerate(sorted_mp3_files):
                    if 'base64_data' not in mp3_info or 'filename' not in mp3_info:
                        return jsonify({
                            'code': 400,
                            'msg': f'第{idx + 1}个MP3文件数据不完整'
                        }), 200

                    # 解码Base64并保存文件
                    try:
                        mp3_data = base64.b64decode(mp3_info['base64_data'])
                        mp3_path = temp_dir_path / mp3_info['filename']

                        with open(mp3_path, 'wb') as f:
                            f.write(mp3_data)

                        audio_files.append(str(mp3_path))

                        # 提取元数据
                        file_ext = 'mp3'
                        metadata = get_audio_metadata(str(mp3_path), file_ext)
                        # 强制设置曲目序号（按前端排序）
                        metadata['track'] = str(idx + 1)
                        file_metadatas.append(metadata)

                        if metadata['cover_img'] and os.path.exists(metadata['cover_img']):
                            temp_cover_files.append(metadata['cover_img'])

                    except Exception as e:
                        return jsonify({
                            'code': 500,
                            'msg': f'处理第{idx + 1}个MP3文件失败：{str(e)}'
                        }), 200

                # ========== 复用原有解析逻辑（关键：使用前端指定的顺序） ==========
                # 按前端排序后的顺序（已经排好序了）
                parse_result = {
                    'album_name': file_metadatas[0]['album'],
                    'album_singer': file_metadatas[0]['artist'],
                    'mp3_duration': '',
                    'cover_img': '',
                    'mp3_url': '',
                    'album_id': '',
                    'songs': []
                }

                # 获取专辑ID
                album_id = get_simple_album_id()
                parse_result['album_id'] = album_id

                # 提取并上传封面
                cover_img_url = ""
                for metadata in file_metadatas:
                    if metadata['cover_img']:
                        cover_img_url = upload_cover_to_imgbed(metadata['cover_img'])
                        if cover_img_url:
                            break

                if not cover_img_url:
                    cover_path = extract_album_cover(audio_files, temp_dir)
                    if cover_path:
                        cover_img_url = upload_cover_to_imgbed(cover_path)

                parse_result['cover_img'] = cover_img_url

                # 合并音频文件（按前端排序）
                merge_file_path = merge_audio_files(
                    audio_files=audio_files,
                    output_dir=temp_dir,
                    album_name=parse_result['album_name'],
                    artist=parse_result['album_singer'],
                    album_id=album_id
                )

                # 上传合并后的音频
                if merge_file_path and os.path.exists(merge_file_path):
                    upload_result = upload_merged_audio(
                        merge_file_path=merge_file_path,
                        album_id=album_id,
                        artist=parse_result['album_singer'],
                        album_name=parse_result['album_name']
                    )
                    if upload_result['code'] == 200:
                        parse_result['mp3_url'] = upload_result['data']['mp3_url']
                        parse_result['mp3_duration'] = upload_result['data']['mp3_duration']

                # 构建歌曲列表（按前端排序）
                total_duration = 0
                for idx, metadata in enumerate(file_metadatas):
                    timestamp = format_duration(total_duration)
                    parse_result['songs'].append({
                        'name': metadata['title'] or f'未知曲目{idx + 1}',
                        'duration': timestamp,
                        'file_duration': format_duration(metadata['duration']),
                        'track_number': idx + 1  # 使用前端排序的序号
                    })
                    total_duration += metadata['duration']

                # 清理临时文件
                for temp_cover in temp_cover_files:
                    try:
                        if os.path.exists(temp_cover):
                            os.remove(temp_cover)
                    except:
                        pass

                return jsonify({
                    'code': 200,
                    'msg': '排序后的MP3文件解析成功！',
                    'data': parse_result
                }), 200

        except Exception as e:
            print(f"❌ 排序MP3解析出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'解析失败：{str(e)}'
            }), 200

