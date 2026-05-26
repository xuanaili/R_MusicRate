import base64
from pathlib import Path

from flask import request, jsonify, Blueprint
import json
import traceback
import os
import tempfile
import time  # 新增：用于时间戳记录

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
            # 记录请求开始时间
            start_time = time.time()
            print(f"\n=== 音频解析请求开始 [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===")

            # 检查是否有文件上传
            if 'audio_files' not in request.files:
                print("❌ 请求错误：未上传音频文件")
                return jsonify({
                    'code': 400,
                    'msg': '请上传音频文件'
                }), 200

            files = request.files.getlist('audio_files')
            if not files:
                print("❌ 请求错误：未选择任何音频文件")
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个音频文件'
                }), 200

            print(f"✅ 接收到 {len(files)} 个文件，开始处理")

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_files = []
                file_metadatas = []
                temp_cover_files = []  # 记录临时封面文件，用于清理

                # 保存上传的文件并提取元数据
                for idx, file in enumerate(files):
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_ext = filename.rsplit('.', 1)[1].lower()
                        file_path = os.path.join(temp_dir, filename)
                        file.save(file_path)
                        print(f"\n📄 处理文件 {idx + 1}/{len(files)}: {filename}")

                        # 提取元数据
                        metadata = get_audio_metadata(file_path, file_ext)
                        print(f"   - 元数据提取结果：{json.dumps(metadata, ensure_ascii=False, indent=2)}")
                        print(
                            f"   - 提取的时长：{metadata['duration']} 秒 (格式化：{format_duration(metadata['duration'])})")

                        file_metadatas.append(metadata)
                        audio_files.append(file_path)

                        # 记录临时封面文件
                        if metadata['cover_img'] and os.path.exists(metadata['cover_img']):
                            temp_cover_files.append(metadata['cover_img'])
                    else:
                        print(f"❌ 文件 {file.filename if file else '未知文件'} 格式不被支持")

                if not file_metadatas:
                    print("❌ 错误：没有有效的音频文件元数据")
                    return jsonify({
                        'code': 400,
                        'msg': '没有有效的音频文件'
                    }), 200

                # 按曲目编号排序
                print(f"\n🔍 排序前文件元数据：")
                for i, meta in enumerate(file_metadatas):
                    print(
                        f"   {i + 1}. {meta['title'] or '未知标题'} - track: {meta['track']} - 时长: {meta['duration']}s")

                file_metadatas.sort(key=lambda x: int(x['track'].split('/')[0]) if x['track'].isdigit() else 0)

                print(f"\n🔍 排序后文件元数据：")
                for i, meta in enumerate(file_metadatas):
                    print(
                        f"   {i + 1}. {meta['title'] or '未知标题'} - track: {meta['track']} - 时长: {meta['duration']}s")

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
                print(f"\n📀 专辑ID：{album_id}，专辑名：{parse_result['album_name']}，歌手：{parse_result['album_singer']}")

                # 提取专辑封面并上传到本地图床
                cover_img_url = ""
                # 优先使用元数据中的封面
                for metadata in file_metadatas:
                    if metadata['cover_img']:
                        cover_img_url = upload_cover_to_imgbed(metadata['cover_img'])
                        if cover_img_url:
                            print(f"✅ 使用元数据封面：{cover_img_url}")
                            break
                # 如果元数据中没有封面，用FFmpeg提取
                if not cover_img_url:
                    cover_path = extract_album_cover(audio_files, temp_dir)
                    if cover_path:
                        cover_img_url = upload_cover_to_imgbed(cover_path)
                        print(f"✅ 从音频提取封面：{cover_img_url}")
                    else:
                        print("⚠️  未提取到专辑封面")

                # 赋值封面URL
                parse_result['cover_img'] = cover_img_url

                # 计算合并前总时长
                pre_merge_total_duration = sum([meta['duration'] for meta in file_metadatas])
                print(f"\n📊 合并前统计：")
                print(f"   - 单个文件时长列表：{[meta['duration'] for meta in file_metadatas]}")
                print(
                    f"   - 合并前总时长：{pre_merge_total_duration} 秒 (格式化：{format_duration(pre_merge_total_duration)})")

                # ✅ 简化：传递简单序号给合并函数
                print(f"\n🔗 开始合并音频文件，输入文件列表：{audio_files}")
                merge_file_path = merge_audio_files(
                    audio_files=audio_files,
                    output_dir=temp_dir,
                    album_name=parse_result['album_name'],
                    artist=parse_result['album_singer'],
                    album_id=album_id  # 简单序号
                )
                print(f"✅ 合并完成，合并文件路径：{merge_file_path}")

                # 验证合并文件时长
                if merge_file_path and os.path.exists(merge_file_path):
                    # 读取合并后文件的真实时长
                    merge_metadata = get_audio_metadata(merge_file_path, 'mp3')
                    merge_real_duration = merge_metadata.get('duration', 0)
                    print(
                        f"📊 合并后文件真实时长：{merge_real_duration} 秒 (格式化：{format_duration(merge_real_duration)})")
                    print(
                        f"⚠️  时长对比：合并前计算 {pre_merge_total_duration}s vs 合并后真实 {merge_real_duration}s (差值：{abs(pre_merge_total_duration - merge_real_duration)}s)")

                    # ✅ 简化：上传时传递简单序号、歌手名、专辑名
                    print(f"\n📤 开始上传合并后的音频文件")
                    upload_result = upload_merged_audio(
                        merge_file_path=merge_file_path,
                        album_id=album_id,
                        artist=parse_result['album_singer'],
                        album_name=parse_result['album_name']
                    )
                    print(f"📤 上传结果：{json.dumps(upload_result, ensure_ascii=False, indent=2)}")

                    if upload_result['code'] == 200:
                        parse_result['mp3_url'] = upload_result['data']['mp3_url']
                        parse_result['mp3_duration'] = upload_result['data']['mp3_duration']
                        print(f"✅ 上传成功：URL={parse_result['mp3_url']}，返回时长={parse_result['mp3_duration']}")
                    else:
                        print(f"❌ 音频上传失败：{upload_result['msg']}")
                else:
                    print(f"❌ 合并后的音频文件不存在：{merge_file_path}")

                # 计算时间戳并构建单曲列表
                total_duration = 0
                print(f"\n📝 构建单曲列表：")
                for idx, metadata in enumerate(file_metadatas):
                    # 格式化时间戳
                    timestamp = format_duration(total_duration)
                    file_duration_formatted = format_duration(metadata['duration'])

                    song_info = {
                        'name': metadata['title'] or f'未知曲目{idx + 1}',
                        'duration': timestamp,
                        'file_duration': file_duration_formatted,
                        'track_number': idx + 1
                    }
                    parse_result['songs'].append(song_info)

                    print(f"   {idx + 1}. {song_info['name']} - 开始时间：{timestamp} - 时长：{file_duration_formatted}")
                    total_duration += metadata['duration']

                print(f"\n📊 最终统计：")
                print(f"   - 单曲列表总时长累加：{total_duration} 秒")
                print(f"   - 合并文件真实时长：{merge_real_duration if 'merge_real_duration' in locals() else 0} 秒")
                print(f"   - 上传返回时长：{parse_result['mp3_duration']}")
                print(f"   - 请求总耗时：{time.time() - start_time:.2f} 秒")

                # 清理临时封面文件
                for temp_cover in temp_cover_files:
                    try:
                        if os.path.exists(temp_cover):
                            os.remove(temp_cover)
                    except Exception as e:
                        print(f"⚠️  清理临时封面文件失败：{temp_cover} - {str(e)}")

                return jsonify({
                    'code': 200,
                    'msg': '音频解析成功！',
                    'data': parse_result
                }), 200

        except Exception as e:
            print(f"\n❌ 音频解析出错：{str(e)}")
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
            print(f"\n=== KGG转换请求开始 [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===")

            if 'kgg_files' not in request.files:
                print("❌ 请求错误：未上传KGG文件")
                return jsonify({
                    'code': 400,
                    'msg': '请上传KGG格式文件'
                }), 200

            files = request.files.getlist('kgg_files')
            if not files:
                print("❌ 请求错误：未选择任何KGG文件")
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个KGG文件'
                }), 200

            # 验证文件格式
            kgg_files = []
            for file in files:
                if file and file.filename.endswith('.kgg'):
                    kgg_files.append(file)
                    print(f"✅ 有效KGG文件：{file.filename}")
                else:
                    print(f"❌ 无效文件：{file.filename} 不是KGG格式")
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
                    print(f"📄 保存KGG文件：{kgg_path}")

                # 批量转换KGG到MP3
                print(f"\n🔄 开始批量转换KGG文件：{uploaded_kgg_paths}")
                success, mp3_files = batch_convert_kgg_to_mp3(uploaded_kgg_paths, temp_dir_path)
                print(f"✅ 转换完成：成功={success}，生成MP3文件数={len(mp3_files)}")

                if not success or len(mp3_files) == 0:
                    print("❌ KGG转换失败：无MP3文件生成")
                    return jsonify({
                        'code': 500,
                        'msg': 'KGG文件转换失败'
                    }), 200

                # 准备返回的MP3文件信息
                mp3_files_info = []
                total_duration = 0
                print(f"\n📊 KGG转换结果统计：")
                for mp3_file in mp3_files:
                    # 读取文件内容为Base64
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')

                    # 提取基础元数据
                    try:
                        metadata = get_audio_metadata(str(mp3_file), 'mp3')
                        file_duration = metadata['duration']
                        total_duration += file_duration
                        print(f"   - {mp3_file.name}：时长={file_duration}s (格式化：{format_duration(file_duration)})")
                    except Exception as e:
                        metadata = {
                            'title': mp3_file.stem,
                            'artist': '未知艺术家',
                            'album': '未知专辑',
                            'duration': 0
                        }
                        print(f"⚠️  {mp3_file.name}：提取元数据失败 - {str(e)}")

                    mp3_files_info.append({
                        'filename': mp3_file.name,
                        'file_size': os.path.getsize(mp3_file),
                        'base64_data': base64_data,
                        'metadata': metadata,
                        'order': len(mp3_files_info) + 1  # 默认顺序
                    })

                print(f"📊 KGG转换总时长：{total_duration}s (格式化：{format_duration(total_duration)})")

                return jsonify({
                    'code': 200,
                    'msg': f'成功转换 {len(mp3_files)} 个KGG文件为MP3',
                    'data': {
                        'mp3_files': mp3_files_info
                    }
                }), 200

        except Exception as e:
            print(f"\n❌ KGG转换出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'KGG转换失败：{str(e)}'
            }), 200

    @app.route('/api/audio/unlock/convert-ncm-only', methods=['POST', 'OPTIONS'])
    def convert_ncm_only():
        """仅将NCM文件转换为MP3并返回文件列表，不进行解析（适配你的图床函数）"""
        try:
            print(f"\n=== NCM转换请求开始 [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===")

            # 1. 检查文件参数
            if 'ncm_files' not in request.files:  # 保持和原有接口一致的参数名
                print("❌ 请求错误：未上传NCM文件")
                return jsonify({
                    'code': 400,
                    'msg': '请上传NCM格式文件'
                }), 200

            files = request.files.getlist('ncm_files')
            if not files:
                print("❌ 请求错误：未选择任何NCM文件")
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个NCM文件'
                }), 200

            # 2. 验证文件格式
            ncm_files = []
            for file in files:
                if file and file.filename.endswith('.ncm'):
                    ncm_files.append(file)
                    print(f"✅ 有效NCM文件：{file.filename}")
                else:
                    print(f"❌ 无效文件：{file.filename} 不是NCM格式")
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
                    print(f"📄 保存NCM文件：{ncm_path}")

                # 5. 批量转换NCM到MP3（获取临时封面路径）
                print(f"\n🔄 开始批量转换NCM文件：{uploaded_ncm_paths}")
                success, mp3_files, temp_cover_map = batch_convert_ncm_to_mp3(uploaded_ncm_paths, temp_dir_path)
                print(f"✅ 转换完成：成功={success}，生成MP3文件数={len(mp3_files)}")

                if not success or len(mp3_files) == 0:
                    print("❌ NCM转换失败：无MP3文件生成")
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
                            print(f"✅ 封面上传成功：{cover_url}")
                            break

                # 7. 准备返回的MP3文件信息
                mp3_files_info = []
                total_duration = 0
                print(f"\n📊 NCM转换结果统计：")
                for mp3_file in mp3_files:
                    # 读取文件内容为Base64
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')

                    # 提取基础元数据
                    try:
                        metadata = get_audio_metadata(str(mp3_file), 'mp3')
                        file_duration = metadata['duration']
                        total_duration += file_duration
                        print(f"   - {mp3_file.name}：时长={file_duration}s (格式化：{format_duration(file_duration)})")
                        # 添加封面URL到元数据
                        mp3_path_str = str(mp3_file)
                        if mp3_path_str in cover_url_map:
                            metadata['cover_url'] = cover_url_map[mp3_path_str]
                            metadata['cover_img'] = temp_cover_map.get(mp3_path_str, "")  # 兼容原有逻辑
                    except Exception as e:
                        metadata = {
                            'title': mp3_file.stem,
                            'artist': '未知艺术家',
                            'album': '未知专辑',
                            'track': '0',
                            'duration': 0,
                            'cover_url': '',
                            'cover_img': ''
                        }
                        print(f"⚠️  {mp3_file.name}：提取元数据失败 - {str(e)}")

                    mp3_files_info.append({
                        'filename': mp3_file.name,
                        'file_size': os.path.getsize(mp3_file),
                        'base64_data': base64_data,
                        'metadata': metadata,
                        'order': len(mp3_files_info) + 1
                    })

                print(f"📊 NCM转换总时长：{total_duration}s (格式化：{format_duration(total_duration)})")

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
                    except Exception as e:
                        print(f"⚠️  清理临时封面文件失败：{temp_cover} - {str(e)}")

            # 8. 返回结果
            return jsonify({
                'code': 200,
                'msg': f'成功转换 {len(mp3_files)} 个NCM文件为MP3',
                'data': {
                    'mp3_files': mp3_files_info
                }
            }), 200

        except Exception as e:
            print(f"\n❌ NCM转换出错：{str(e)}")
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
            print(f"\n=== 通用音频转换请求开始 [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===")

            # 1. 检查文件参数（和NCM接口一致）
            if 'audio_files' not in request.files:
                print("❌ 请求错误：未上传音频文件")
                return jsonify({
                    'code': 400,
                    'msg': '请上传音频文件'
                }), 200

            files = request.files.getlist('audio_files')
            if not files:
                print("❌ 请求错误：未选择任何音频文件")
                return jsonify({
                    'code': 400,
                    'msg': '请选择至少一个音频文件'
                }), 200

            # 2. 验证文件格式（和NCM接口一致）
            audio_files = []
            for file in files:
                if file and allowed_file(file.filename):
                    audio_files.append(file)
                    print(f"✅ 有效音频文件：{file.filename}")
                else:
                    print(f"❌ 无效文件：{file.filename if file else '未知文件'} 格式不被支持")
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
                    print(f"📄 保存音频文件：{audio_path}")

                # 5. 处理音频文件，生成MP3文件列表和临时封面映射（核心对齐NCM接口）
                mp3_files = []
                temp_cover_map = {}  # 关键：和NCM接口一致的封面映射（mp3路径 -> 封面路径）

                # 模拟音频转MP3（实际项目中替换为真实转码逻辑）
                print(f"\n🔄 开始转换音频文件：{uploaded_audio_paths}")
                for audio_path in uploaded_audio_paths:
                    file_ext = audio_path.suffix.lower()[1:]
                    metadata = get_audio_metadata(str(audio_path), file_ext)

                    # 转码为MP3（示例：直接使用原文件路径，实际需替换为转码后的MP3路径）
                    mp3_path = temp_dir_path / f"{audio_path.stem}.mp3"
                    # shutil.copy(audio_path, mp3_path)  # 临时模拟转码

                    mp3_files.append(mp3_path)
                    print(f"   - 转换：{audio_path.name} -> {mp3_path.name}")

                    # 提取封面（和NCM接口逻辑一致）
                    cover_path = metadata.get('cover_img', '')
                    if cover_path and os.path.exists(cover_path):
                        temp_cover_map[str(mp3_path)] = cover_path
                        print(f"   - 提取封面：{cover_path}")
                    else:
                        # 如果元数据无封面，尝试从音频文件提取（和NCM接口一致）
                        # 替换为你实际的封面提取逻辑
                        cover_path = upload_cover_to_imgbed(str(audio_path))
                        if cover_path:
                            temp_cover_map[str(mp3_path)] = cover_path
                            print(f"   - 从音频提取封面：{cover_path}")
                        else:
                            print(f"   - 未提取到封面")

                if not mp3_files:
                    print("❌ 音频转换失败：无MP3文件生成")
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
                            print(f"✅ 封面上传成功：{cover_url}")
                            break
                        # ✅ 修正点3：移除break，保证每个文件都处理封面

                # 7. 准备返回的MP3文件信息（和NCM接口完全一致）
                mp3_files_info = []
                total_duration = 0
                print(f"\n📊 通用音频转换结果统计：")
                for mp3_file in mp3_files:
                    # 读取文件内容为Base64（和NCM接口一致）
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')

                    # 提取基础元数据（和NCM接口一致）
                    try:
                        metadata = get_audio_metadata(str(mp3_file), 'mp3')
                        file_duration = metadata['duration']
                        total_duration += file_duration
                        print(f"   - {mp3_file.name}：时长={file_duration}s (格式化：{format_duration(file_duration)})")
                        # 添加封面URL到元数据（和NCM接口一致）
                        mp3_path_str = str(mp3_file)
                        if mp3_path_str in cover_url_map:
                            metadata['cover_url'] = cover_url_map[mp3_path_str]
                            metadata['cover_img'] = temp_cover_map.get(mp3_path_str, "")  # 兼容原有逻辑
                    except Exception as e:
                        metadata = {
                            'title': mp3_file.stem,
                            'artist': '未知艺术家',
                            'album': '未知专辑',
                            'track': '0',
                            'duration': 0,
                            'cover_url': '',
                            'cover_img': ''
                        }
                        print(f"⚠️  {mp3_file.name}：提取元数据失败 - {str(e)}")

                    mp3_files_info.append({
                        'filename': mp3_file.name,
                        'file_size': os.path.getsize(mp3_file),
                        'base64_data': base64_data,
                        'metadata': metadata,
                        'order': len(mp3_files_info) + 1
                    })

                print(f"📊 通用音频转换总时长：{total_duration}s (格式化：{format_duration(total_duration)})")

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
                    except Exception as e:
                        print(f"⚠️  清理临时封面文件失败：{temp_cover} - {str(e)}")

            # 10. 返回结果（和NCM接口完全一致）
            return jsonify({
                'code': 200,
                'msg': f'成功转换 {len(mp3_files)} 个音频文件为MP3',
                'data': {
                    'mp3_files': mp3_files_info
                }
            }), 200

        except Exception as e:
            print(f"\n❌ 音频转换出错：{str(e)}")
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
            # 记录请求开始时间
            start_time = time.time()
            print(f"\n=== 排序MP3解析请求开始 [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===")

            data = request.get_json()
            if not data or 'sorted_mp3_files' not in data:
                print("❌ 请求错误：未提供排序后的MP3文件数据")
                return jsonify({
                    'code': 400,
                    'msg': '请提供排序后的MP3文件数据'
                }), 200

            sorted_mp3_files = data['sorted_mp3_files']
            if not isinstance(sorted_mp3_files, list) or len(sorted_mp3_files) == 0:
                print("❌ 请求错误：排序后的MP3文件列表为空")
                return jsonify({
                    'code': 400,
                    'msg': '排序后的MP3文件列表不能为空'
                }), 200

            print(f"✅ 接收到 {len(sorted_mp3_files)} 个排序后的MP3文件")

            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                audio_files = []
                file_metadatas = []
                temp_cover_files = []

                # 按前端指定的顺序保存MP3文件
                for idx, mp3_info in enumerate(sorted_mp3_files):
                    if 'base64_data' not in mp3_info or 'filename' not in mp3_info:
                        print(f"❌ 第{idx + 1}个MP3文件数据不完整：{mp3_info}")
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

                        print(f"\n📄 处理排序文件 {idx + 1}/{len(sorted_mp3_files)}: {mp3_info['filename']}")
                        audio_files.append(str(mp3_path))

                        # 提取元数据
                        file_ext = 'mp3'
                        metadata = get_audio_metadata(str(mp3_path), file_ext)
                        # 强制设置曲目序号（按前端排序）
                        metadata['track'] = str(idx + 1)
                        print(f"   - 元数据：{json.dumps(metadata, ensure_ascii=False, indent=2)}")
                        print(f"   - 时长：{metadata['duration']} 秒 (格式化：{format_duration(metadata['duration'])})")

                        file_metadatas.append(metadata)

                        if metadata['cover_img'] and os.path.exists(metadata['cover_img']):
                            temp_cover_files.append(metadata['cover_img'])

                    except Exception as e:
                        print(f"❌ 处理第{idx + 1}个MP3文件失败：{str(e)}")
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

                # 计算合并前总时长
                pre_merge_total_duration = sum([meta['duration'] for meta in file_metadatas])
                print(f"\n📊 合并前统计：")
                print(f"   - 单个文件时长列表：{[meta['duration'] for meta in file_metadatas]}")
                print(
                    f"   - 合并前总时长：{pre_merge_total_duration} 秒 (格式化：{format_duration(pre_merge_total_duration)})")

                # 获取专辑ID
                album_id = get_simple_album_id()
                parse_result['album_id'] = album_id
                print(f"\n📀 专辑ID：{album_id}，专辑名：{parse_result['album_name']}，歌手：{parse_result['album_singer']}")

                # 提取并上传封面
                cover_img_url = ""
                for metadata in file_metadatas:
                    if metadata['cover_img']:
                        cover_img_url = upload_cover_to_imgbed(metadata['cover_img'])
                        if cover_img_url:
                            print(f"✅ 使用元数据封面：{cover_img_url}")
                            break

                if not cover_img_url:
                    cover_path = extract_album_cover(audio_files, temp_dir)
                    if cover_path:
                        cover_img_url = upload_cover_to_imgbed(cover_path)
                        print(f"✅ 从音频提取封面：{cover_img_url}")
                    else:
                        print("⚠️  未提取到专辑封面")

                parse_result['cover_img'] = cover_img_url

                # 合并音频文件（按前端排序）
                print(f"\n🔗 开始合并音频文件，输入文件列表：{audio_files}")
                merge_file_path = merge_audio_files(
                    audio_files=audio_files,
                    output_dir=temp_dir,
                    album_name=parse_result['album_name'],
                    artist=parse_result['album_singer'],
                    album_id=album_id
                )
                print(f"✅ 合并完成，合并文件路径：{merge_file_path}")

                # 验证合并文件时长
                merge_real_duration = 0
                if merge_file_path and os.path.exists(merge_file_path):
                    # 读取合并后文件的真实时长
                    merge_metadata = get_audio_metadata(merge_file_path, 'mp3')
                    merge_real_duration = merge_metadata.get('duration', 0)
                    print(
                        f"📊 合并后文件真实时长：{merge_real_duration} 秒 (格式化：{format_duration(merge_real_duration)})")
                    print(
                        f"⚠️  时长对比：合并前计算 {pre_merge_total_duration}s vs 合并后真实 {merge_real_duration}s (差值：{abs(pre_merge_total_duration - merge_real_duration)}s)")

                    # 上传合并后的音频
                    print(f"\n📤 开始上传合并后的音频文件")
                    upload_result = upload_merged_audio(
                        merge_file_path=merge_file_path,
                        album_id=album_id,
                        artist=parse_result['album_singer'],
                        album_name=parse_result['album_name']
                    )
                    print(f"📤 上传结果：{json.dumps(upload_result, ensure_ascii=False, indent=2)}")

                    if upload_result['code'] == 200:
                        parse_result['mp3_url'] = upload_result['data']['mp3_url']
                        parse_result['mp3_duration'] = upload_result['data']['mp3_duration']
                        print(f"✅ 上传成功：URL={parse_result['mp3_url']}，返回时长={parse_result['mp3_duration']}")

                # 构建歌曲列表（按前端排序）
                total_duration = 0
                print(f"\n📝 构建单曲列表：")
                for idx, metadata in enumerate(file_metadatas):
                    timestamp = format_duration(total_duration)
                    file_duration_formatted = format_duration(metadata['duration'])

                    song_info = {
                        'name': metadata['title'] or f'未知曲目{idx + 1}',
                        'duration': timestamp,
                        'file_duration': file_duration_formatted,
                        'track_number': idx + 1  # 使用前端排序的序号
                    }
                    parse_result['songs'].append(song_info)

                    print(f"   {idx + 1}. {song_info['name']} - 开始时间：{timestamp} - 时长：{file_duration_formatted}")
                    total_duration += metadata['duration']

                print(f"\n📊 最终统计：")
                print(f"   - 单曲列表总时长累加：{total_duration} 秒")
                print(f"   - 合并文件真实时长：{merge_real_duration} 秒")
                print(f"   - 上传返回时长：{parse_result['mp3_duration']}")
                print(f"   - 请求总耗时：{time.time() - start_time:.2f} 秒")

                # 清理临时文件
                for temp_cover in temp_cover_files:
                    try:
                        if os.path.exists(temp_cover):
                            os.remove(temp_cover)
                    except Exception as e:
                        print(f"⚠️  清理临时封面文件失败：{temp_cover} - {str(e)}")

                return jsonify({
                    'code': 200,
                    'msg': '排序后的MP3文件解析成功！',
                    'data': parse_result
                }), 200

        except Exception as e:
            print(f"\n❌ 排序MP3解析出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'code': 500,
                'msg': f'解析失败：{str(e)}'
            }), 200