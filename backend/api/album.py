from flask import request, jsonify
import json
import traceback

from .unlock import format_duration
from backend.utils.db import (
    get_db, get_album_table_name, get_current_user_id
)
from backend.utils.decorators import login_required, is_admin_user
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
import pymysql

from ..utils.intro import get_user_album_intro, save_user_album_intro
from ..utils.score import calculate_album_total_score
from ..utils.last_listened import last_listened_sort_key
from ..utils.json import safe_json_loads

# ========== ✅ v0.9 P0：专辑动画样式配置规范化（纯函数） ==========
_STYLE_TYPES = ('close', 'ball', 'meteor')
_AUTO_MANUAL = ('auto', 'manual')
_RHY_KEYS = ('a', 'b', 'c', 'd', 'e')
_METEOR_KEYS = ('angle', 'size', 'tailLength', 'speed')


def normalize_style_config(data):
    """校验并规范化用户提交的样式配置（v0.9 P0，POST 边界校验）
    - style_type ∈ close/ball/meteor；auto_manual ∈ auto/manual（非法回退默认）
    - rhy_config 只保留 a-e（0-100 数字）；meteor_config 只保留 angle/size/tailLength/speed（0-100 数字）
    - 返回 {style_type, rhy_config, meteor_config, auto_manual}
    """
    data = data or {}
    style_type = str(data.get('style_type') or 'close')
    if style_type not in _STYLE_TYPES:
        style_type = 'close'
    auto_manual = str(data.get('auto_manual') or 'auto')
    if auto_manual not in _AUTO_MANUAL:
        auto_manual = 'auto'

    def _clean_nums(raw, keys):
        raw = raw or {}
        out = {}
        for k in keys:
            try:
                out[k] = int(round(max(0.0, min(100.0, float(raw.get(k, 0))))))
            except (TypeError, ValueError):
                out[k] = 0
        return out

    return {
        'style_type': style_type,
        'rhy_config': _clean_nums(data.get('rhy_config'), _RHY_KEYS),
        'meteor_config': _clean_nums(data.get('meteor_config'), _METEOR_KEYS),
        'auto_manual': auto_manual,
    }


def _get_style_row(user_id, album_id):
    """查本人该专辑样式配置行（无则 None）；归属校验（albums_{user_id} 存在专辑才可读写）"""
    db = get_db()
    cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
    table_name = get_album_table_name(user_id)
    cursor.execute(f'SELECT id FROM `{table_name}` WHERE id = %s', (album_id,))
    if not cursor.fetchone():
        cursor.close()
        return None, None  # 专辑不存在/非本人
    cursor.execute(
        'SELECT style_type, rhy_config, meteor_config, auto_manual, update_time FROM user_album_style WHERE user_id = %s AND album_id = %s',
        (user_id, album_id),
    )
    row = cursor.fetchone()
    cursor.close()
    return row, True


def register_album_routes(app):
    """注册专辑基础操作路由（需传入Flask app实例）"""

    # 1. 兼容前端的 /api/album/list 接口
    @app.route('/api/album/list', methods=['GET', 'OPTIONS'])
    @login_required
    def album_list_compatible():
        return get_album_list()

    def get_album_list():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
            sort_by = request.args.get('sort_by', 'album_name')
            sort_order = request.args.get('sort_order', 'asc')
            search_keyword = request.args.get('search_keyword', '').strip()
            tag_keyword = request.args.get('tag_keyword', '').strip()

            VALID_SORT_FIELDS = ['album_name', 'release_year', 'singer', 'my_score', 'created_at', 'listening_duration', 'last_listened']
            if sort_by not in VALID_SORT_FIELDS:
                sort_by = 'album_name'
            if sort_order not in ['asc', 'desc']:
                sort_order = 'asc'

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 构建查询条件（保持原有逻辑不变）
            base_sql = f'SELECT * FROM `{table_name}`'
            where_conditions = []
            sql_params = []
            if search_keyword:
                where_conditions.append("(album_name LIKE %s OR singer LIKE %s)")
                like_search = f"%{search_keyword}%"
                sql_params.extend([like_search, like_search])
            if tag_keyword:
                where_conditions.append("""
                    tags IS NOT NULL
                    AND JSON_VALID(tags)
                    AND LOCATE(%s, LOWER(
                        REPLACE(
                            REPLACE(
                                REPLACE(JSON_EXTRACT(tags, '$'), '"', ''),
                                '[', ''
                            ), ']', ''
                        )
                    )) > 0
                """)
                sql_params.append(tag_keyword.lower())
            if where_conditions:
                base_sql += " WHERE " + " AND ".join(where_conditions)

            # 执行查询（保持原有逻辑不变）
            cursor.execute(base_sql, tuple(sql_params))
            # ========== 核心修复：强制转为列表，避免tuple导致的sort报错 ==========
            all_albums = list(cursor.fetchall())  # 关键修改：加list()强制转列表
            # ========== 核心修复结束 ==========
            total = len(all_albums)
            cursor.close()

            # ========== 核心修复：无论什么排序维度，都先计算所有专辑的calculated_score ==========
            for album in all_albums:
                score_list = []
                # 解析my_score字段为数组（增强容错）
                if album.get('my_score'):
                    try:
                        score_list = json.loads(album['my_score'])
                        # 确保是数组，且元素都是数字
                        if not isinstance(score_list, list):
                            score_list = []
                        else:
                            score_list = [float(s) for s in score_list if isinstance(s, (int, float))]
                    except (json.JSONDecodeError, TypeError, ValueError):
                        score_list = []
                # 计算综合评分并添加字段（所有专辑都有这个字段）
                album['calculated_score'] = calculate_album_total_score(score_list)

            # ========== 排序逻辑：按指定字段排序（my_score时用calculated_score） ==========
            if sort_by == 'my_score':
                # 按计算后的评分排序
                all_albums.sort(
                    key=lambda x: x['calculated_score'],
                    reverse=(sort_order == 'desc')
                )
            elif sort_by == 'last_listened':
                # 最近收听排序：最新收听在前，从未收听（缺字段/None）固定排最后
                all_albums.sort(
                    key=lambda x: last_listened_sort_key(x, sort_order),
                    reverse=(sort_order == 'desc')
                )
            else:
                # 其他字段按原始值排序
                all_albums.sort(
                    key=lambda x: x.get(sort_by, ''),
                    reverse=(sort_order == 'desc')
                )

            # 分页处理（保持原有逻辑不变）
            offset = (page - 1) * page_size
            paginated_albums = all_albums[offset:offset + page_size]

            # 格式化返回数据（保持原有逻辑不变）
            def safe_json_loads(s, is_dict=False):
                if not s:
                    return {} if is_dict else []
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return {} if is_dict else []

            album_list = []
            for album in paginated_albums:
                user_intro = get_user_album_intro(current_user_id, album["id"])
                final_intro = user_intro if user_intro else album.get("album_intro", "")

                album_dict = {
                    "id": album["id"],
                    "album_name": album["album_name"],
                    "cover_img": album["cover_img"],
                    "singer": album["singer"],
                    "release_year": album["release_year"],
                    "start_time": album["start_time"],
                    "track_count": album["track_count"],
                    "track_duration": album["track_duration"],
                    "my_score": album["my_score"],
                    "burn_class": album["burn_class"],
                    "duration_type": album["duration_type"],
                    "tags": safe_json_loads(album["tags"]),
                    "main_type": safe_json_loads(album["main_type"]),
                    "code": album["code"],
                    "video_shared": album["video_shared"],
                    "mandopop_code": album["mandopop_code"],
                    "album_intro": final_intro,
                    "tracks": safe_json_loads(album["tracks"]),
                    "review": safe_json_loads(album["review"], is_dict=True),
                    "score": album["score"],
                    "comments": safe_json_loads(album["comments"]),
                    "source_pool_id": album.get("source_pool_id"),
                    "sync_pool_update": album.get("sync_pool_update", 1),
                    "is_customized": album.get("is_customized", 0),
                    "tracks_time": safe_json_loads(album.get("tracks_time")),
                    "listening_duration": album.get("listening_duration", 0),
                    "last_listened": album.get("last_listened"),
                    # 现在所有专辑都有这个字段了
                    "calculated_score": album.get('calculated_score', 0.0)
                }
                album_list.append(album_dict)

            total_pages = (total + page_size - 1) // page_size

            return jsonify({
                "code": 200,
                "msg": "获取专辑列表成功",
                "data": {
                    "list": album_list,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": total_pages
                    }
                }
            })
        except Exception as e:
            print(f"❌ 获取专辑列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取专辑出错：{str(e)}"}), 200

    # ✅✅✅ 以下所有接口代码完全不变，无需修改 ✅✅✅
    @app.route('/api/album/get-id-by-source', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_id_by_source_pool_id():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            source_pool_id = request.args.get('source_pool_id')
            if not source_pool_id or not source_pool_id.isdigit():
                return jsonify({"code": 400, "msg": "source_pool_id不能为空且必须为数字！"}), 200
            source_pool_id = int(source_pool_id)
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute(f'''
                SELECT id FROM `{table_name}` 
                WHERE source_pool_id = %s LIMIT 1
            ''', (source_pool_id,))
            album_info = cursor.fetchone()
            cursor.close()
            if album_info and album_info.get('id'):
                return jsonify({
                    "code": 200,
                    "msg": "查询专辑ID成功",
                    "data": {"album_id": album_info['id'], "source_pool_id": source_pool_id}
                })
            else:
                return jsonify({
                    "code": 404,
                    "msg": f"你的专辑列表中暂无source_pool_id={source_pool_id}的专辑",
                    "data": None
                })
        except Exception as e:
            print(f"❌ 根据source_pool_id查询album_id出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 200

    @app.route('/api/album/sync/switch', methods=['POST', 'OPTIONS'])
    @login_required
    def switch_album_sync():
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "未登录！"}), 200
            data = request.get_json()
            album_id = data.get('album_id')
            sync_status = data.get('sync_status', 1)
            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空！"}), 200
            db = get_db()
            cursor = db.cursor()
            table_name = get_album_table_name(user_id)
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET sync_pool_update = %s 
                WHERE id = %s
            ''', (sync_status, album_id))
            db.commit()
            cursor.close()
            return jsonify({
                "code": 200,
                "msg": f"{'开启' if sync_status else '关闭'}同步成功！",
                "data": {"album_id": album_id, "sync_status": sync_status}
            })
        except Exception as e:
            print(f"❌ 开关同步失败：{str(e)}")
            return jsonify({"code": 500, "msg": f"操作失败：{str(e)}"}), 200

    @app.route('/api/album/mark/customized', methods=['POST', 'OPTIONS'])
    @login_required
    def mark_album_customized():
        try:
            user_id = get_current_user_id()
            data = request.get_json()
            album_id = data.get('album_id')
            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空！"}), 200
            db = get_db()
            cursor = db.cursor()
            table_name = get_album_table_name(user_id)
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET is_customized = 1 
                WHERE id = %s
            ''', (album_id,))
            db.commit()
            cursor.close()
            return jsonify({"code": 200, "msg": "标记自定义修改成功！", "data": {"album_id": album_id}})
        except Exception as e:
            return jsonify({"code": 500, "msg": f"操作失败：{str(e)}"}), 200

    @app.route('/api/album/update/tags/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_album_tags(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            data = request.get_json()
            tags = data.get('tags', [])
            tags = list(set([tag.strip() for tag in tags if tag.strip()]))[:5]
            tags_json = json.dumps(tags)
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute(f'SELECT id, source_pool_id FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 200
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET tags = %s 
                WHERE id = %s
            ''', (tags_json, album_id))
            pool_id = album.get('source_pool_id')
            if pool_id:
                cursor.execute('''
                    SELECT id FROM user_album_relation 
                    WHERE user_id = %s AND album_pool_id = %s
                ''', (current_user_id, pool_id))
                relation = cursor.fetchone()
                if relation:
                    cursor.execute('''
                        UPDATE user_album_relation 
                        SET tags = %s 
                        WHERE id = %s
                    ''', (tags_json, relation['id']))
                else:
                    cursor.execute('''
                        INSERT INTO user_album_relation (user_id, album_pool_id, tags)
                        VALUES (%s, %s, %s)
                    ''', (current_user_id, pool_id, tags_json))
            db.commit()
            cursor.close()
            return jsonify({"code": 200, "msg": "标签保存成功", "data": {"tags": tags}})
        except Exception as e:
            print(f"❌ 保存标签失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存标签失败：{str(e)}"}), 200

    @app.route('/api/album/detail/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_detail(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # ✅ 关联查询 album_pool 获取 mp3_url
            cursor.execute(f'''
                SELECT u.*, p.mp3_url 
                FROM `{table_name}` u
                LEFT JOIN album_pool p ON u.source_pool_id = p.id
                WHERE u.id = %s
            ''', (album_id,))
            album = cursor.fetchone()
            cursor.close()
            if not album:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 200

            def safe_json_loads(s, is_dict=False):
                if not s:
                    return {} if is_dict else []
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return {} if is_dict else []

            user_intro = get_user_album_intro(current_user_id, album_id)
            final_intro = user_intro if user_intro else album.get("album_intro", "")
            album_dict = {
                "id": album["id"],
                "album_name": album["album_name"],
                "cover_img": album["cover_img"],
                "singer": album["singer"],
                "release_year": album["release_year"],
                "start_time": album["start_time"],
                "track_count": album["track_count"],
                "track_duration": album["track_duration"],
                "my_score": album["my_score"],
                "burn_class": album["burn_class"],
                "duration_type": album["duration_type"],
                "tags": safe_json_loads(album["tags"]),
                "main_type": safe_json_loads(album["main_type"]),
                "code": album["code"],
                "video_shared": album["video_shared"],
                "mandopop_code": album["mandopop_code"],
                "album_intro": final_intro,
                "tracks": safe_json_loads(album["tracks"]),
                "favourite_tracks": safe_json_loads(album["favourite_tracks"]),
                "review": safe_json_loads(album["review"], is_dict=True),
                "score": album["score"],
                "comments": safe_json_loads(album["comments"]),
                "source_pool_id": album.get("source_pool_id"),
                "sync_pool_update": album.get("sync_pool_update", 1),
                "is_customized": album.get("is_customized", 0),
                "tracks_time": safe_json_loads(album.get("tracks_time")),
                "favourite_tracks_time": safe_json_loads(album.get("favourite_tracks_time")),
                "listening_duration": album.get("listening_duration", 0) or 0,
                "listening_progress": album.get("listening_progress", 0) or 0,
                "mp3_url": album.get("mp3_url", ""),  # 从关联查询中获取 mp3_url
                "mp3_duration": album.get("mp3_duration", 0.0)  # 新增
            }
            return jsonify({"code": 200, "msg": "获取专辑详情成功！", "data": album_dict})
        except Exception as e:
            print(f"❌ 获取专辑详情出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取专辑详情失败：{str(e)}"}), 200

    @app.route('/api/album/add', methods=['POST', 'OPTIONS'])
    @login_required
    def add_album():
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            data = request.get_json()
            print("===== 前端传递的完整参数 =====")
            print(f"原始数据: {data}")
            print(f"mp3_duration 参数值: {data.get('mp3_duration')}")
            print(f"mp3_duration 类型: {type(data.get('mp3_duration'))}")
            # ========== 调试日志结束 ==========



            table_name = get_album_table_name(current_user_id)
            required_fields = ['album_name', 'singer', 'release_year']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"code": 400, "msg": f"{field}不能为空！"}), 200
            album_name = data.get('album_name').strip()
            singer = data.get('singer').strip()
            release_year = int(data.get('release_year'))
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            # 校验公共池是否存在相同专辑
            cursor.execute('''
                SELECT id FROM album_pool 
                WHERE album_name = %s AND singer = %s AND release_year = %s
            ''', (album_name, singer, release_year))
            existing_pool_album = cursor.fetchone()
            if existing_pool_album:
                cursor.close()
                return jsonify({
                    "code": 409,
                    "msg": f"公共专辑池中已存在【{album_name} - {singer} ({release_year})】，无法重复创建！",
                    "data": {"pool_id": existing_pool_album['id']}
                }), 200
            # 校验用户库是否存在相同专辑
            cursor.execute(f'''
                SELECT id FROM `{table_name}` 
                WHERE album_name = %s AND singer = %s AND release_year = %s
            ''', (album_name, singer, release_year))
            existing_user_album = cursor.fetchone()
            if existing_user_album:
                cursor.close()
                return jsonify({
                    "code": 409,
                    "msg": f"你的专辑中已存在【{album_name} - {singer} ({release_year})】，无法重复添加！",
                    "data": {"album_id": existing_user_album['id']}
                }), 200

            def get_default_tracks_value(tracks_data):
                if not tracks_data:
                    return json.dumps([])
                if isinstance(tracks_data, list):
                    return json.dumps(tracks_data)
                try:
                    json.loads(tracks_data)
                    return tracks_data
                except:
                    return json.dumps([])

            # ========== 核心修改 1：获取前端传递的 tracks_time 并格式化 ==========
            tracks_list = data.get('tracks', [])
            tracks_time_list = data.get('tracks_time', [])
            if not isinstance(tracks_list, list):
                tracks_list = []
            if not isinstance(tracks_time_list, list):
                tracks_time_list = []
            tracks_list = [track.strip() for track in tracks_list if track.strip()]
            if len(tracks_time_list) < len(tracks_list):
                tracks_time_list += [0] * (len(tracks_list) - len(tracks_time_list))
            elif len(tracks_time_list) > len(tracks_list):
                tracks_time_list = tracks_time_list[:len(tracks_list)]
            tracks_json = json.dumps(tracks_list, ensure_ascii=False)
            tracks_time_json = json.dumps(tracks_time_list, ensure_ascii=False)
            track_count = len(tracks_list)
            # ========== 核心修改 1 结束 ==========

            # ========== 新增：获取mp3_url和mp3_duration ==========
            mp3_url = data.get('mp3_url', '').strip()
            mp3_duration = float(data.get('mp3_duration', 0.0))  # 接收音频总时长

            album_intro = data.get('album_intro', '').strip()
            new_album = {
                "album_name": album_name,
                "cover_img": data.get('cover_img', '').strip(),
                "singer": singer,
                "release_year": release_year,
                "start_time": data.get('start_time', ''),
                "track_count": track_count,
                "track_duration": format_duration(mp3_duration) if mp3_duration > 0 else '',  # 格式化时长存入
                "my_score": float(data.get('my_score', 0.0)),
                "burn_class": data.get('burn_class', ''),
                "duration_type": data.get('duration_type', ''),
                "tags": json.dumps(data.get('tags', [])) or "",
                "main_type": json.dumps(data.get('main_type', [])) or "",
                "code": data.get('code', ''),
                "video_shared": data.get('video_shared', ''),
                "mandopop_code": data.get('mandopop_code', ''),
                "album_intro": album_intro,
                "tracks": tracks_json,
                "review": json.dumps({
                    "feelings": [],
                    "single_score": 0.0,
                    "private_score": 0.0,
                    "final_score": 0.0,
                    "personal_feeling": "",
                    "update_time": ""
                }) or "",
                "score": float(data.get('score', 0.0)),
                "comments": json.dumps([]) or "",
                "source_pool_id": 0,
                "sync_pool_update": 1,
                "is_customized": 0,
                "tracks_time": tracks_time_json
            }
            main_type_str = json.dumps(data.get('main_type', [])) if data.get('main_type') else ""

            # ========== 核心修改 2：album_pool 插入SQL 新增mp3_duration ==========


            cursor.execute('''
                INSERT INTO album_pool (
                    album_name, cover_img, singer, release_year, 
                    main_type, tags, album_intro, tracks, tracks_time, my_score, create_user,
                    mp3_url, mp3_duration  -- 新增mp3_duration字段
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                new_album['album_name'],
                new_album['cover_img'],
                new_album['singer'],
                new_album['release_year'],
                main_type_str,
                new_album['tags'],
                new_album['album_intro'],
                new_album['tracks'],
                new_album['tracks_time'],
                new_album['my_score'],
                current_user_id,
                mp3_url,
                mp3_duration  # 存入时长
            ))
            # ========== 核心修改 2 结束 ==========

            new_pool_id = cursor.lastrowid
            new_album['source_pool_id'] = new_pool_id

            # ========== 核心修改 3：用户表插入SQL ==========
            cursor.execute(f'''
                INSERT INTO `{table_name}` (
                    album_name, cover_img, singer, release_year, start_time,
                    track_count, track_duration, my_score, burn_class, duration_type,
                    tags, main_type, code, video_shared, mandopop_code,
                    album_intro, tracks, review, score, comments,
                    source_pool_id, sync_pool_update, is_customized, tracks_time
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
            ''', (
                new_album['album_name'], new_album['cover_img'], new_album['singer'],
                new_album['release_year'], new_album['start_time'], new_album['track_count'],
                new_album['track_duration'], new_album['my_score'], new_album['burn_class'],
                new_album['duration_type'], new_album['tags'], new_album['main_type'],
                new_album['code'], new_album['video_shared'], new_album['mandopop_code'],
                new_album['album_intro'],
                new_album['tracks'], new_album['review'], new_album['score'],
                new_album['comments'],
                new_album['source_pool_id'],
                new_album['sync_pool_update'],
                new_album['is_customized'],
                new_album['tracks_time']
            ))
            # ========== 核心修改 3 结束 ==========

            new_album_id = cursor.lastrowid
            if album_intro:
                save_user_album_intro(current_user_id, new_album_id, album_intro)
            db.commit()
            cursor.close()

            # v0.8.1 增补：管理员添加带整轨 mp3 的专辑 → 自动启动 AI 歌词识别（省得每次新专辑再手动识别一次）
            # 识别失败不影响专辑添加（后台任务标记 failed，可稍后在歌词弹窗手动重新触发）
            recognize_task_id = None
            if mp3_url and is_admin_user(current_user_id):
                from backend.api.lyric_ai import start_recognize_task
                try:
                    recognize_task_id = start_recognize_task(app, new_pool_id, album_name, current_user_id)
                except Exception as e:
                    print(f"⚠️ 自动触发 AI 识别失败（不影响专辑添加）：{e}")
                    traceback.print_exc()
                    recognize_task_id = None

            return_album = new_album.copy()
            return_album['id'] = new_album_id
            return_album['tags'] = json.loads(return_album['tags'])
            return_album['main_type'] = json.loads(return_album['main_type'])
            return_album['tracks'] = json.loads(return_album['tracks'])
            return_album['review'] = json.loads(return_album['review'])
            return_album['comments'] = json.loads(return_album['comments'])
            return_album['tracks_time'] = json.loads(return_album['tracks_time'])
            return_album['mp3_url'] = mp3_url
            return_album['mp3_duration'] = mp3_duration  # 返回时长给前端
            return_album['recognize_task_id'] = recognize_task_id  # 非空=已自动开始 AI 识别
            return jsonify({
                "code": 200,
                "msg": "专辑添加成功！单曲时间戳和MP3地址已同步保存到公共池",
                "data": return_album
            })
        except Exception as e:
            print(f"❌ 添加专辑出错：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"添加专辑失败：{str(e)}"}), 200

    @app.route('/api/album/delete/<int:album_id>', methods=['DELETE', 'OPTIONS'])
    @login_required
    def delete_album(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                DELETE FROM user_album_intro 
                WHERE user_id = %s AND album_id = %s
            ''', (current_user_id, album_id))
            cursor.execute(f'DELETE FROM `{table_name}` WHERE id = %s', (album_id,))
            affected_rows = cursor.rowcount
            db.commit()
            cursor.close()
            if affected_rows == 0:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 200
            return jsonify({"code": 200, "msg": f"删除ID为{album_id}的专辑成功！"})
        except Exception as e:
            print(f"删除专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 200

    @app.route('/api/album/user/intro/save', methods=['POST', 'OPTIONS'])
    @login_required
    def save_user_album_intro_api():
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "请先登录"}), 200
            data = request.get_json()
            album_id = data.get('album_id')
            intro_content = data.get('intro_content', '').strip()
            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空"}), 200
            if not intro_content:
                return jsonify({"code": 400, "msg": "简介内容不能为空"}), 200
            save_success = save_user_album_intro(user_id, album_id, intro_content)
            if save_success:
                return jsonify({
                    "code": 200,
                    "msg": "专辑简介保存成功（已关联账号）",
                    "data": {"album_id": album_id, "intro_content": intro_content}
                })
            else:
                return jsonify({"code": 500, "msg": "简介保存失败，请稍后重试"}), 200
        except Exception as e:
            print(f"❌ 保存用户专辑简介接口出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存简介失败：{str(e)}"}), 200

    @app.route('/api/album/user/intro/get/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_user_album_intro_api(album_id):
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "请先登录"}), 200
            intro_content = get_user_album_intro(user_id, album_id)
            return jsonify({
                "code": 200,
                "msg": "获取简介成功",
                "data": intro_content
            })
        except Exception as e:
            print(f"❌ 获取用户专辑简介接口出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取简介失败：{str(e)}"}), 200

    @app.route('/api/album/update/tracks/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_album_tracks(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            data = request.get_json()
            new_tracks = data.get('tracks', [])
            full_tracks = data.get('full_tracks', [])
            trackSecArr = data.get('tracks_time', [])
            if isinstance(new_tracks, list):
                new_tracks = [track.strip() for track in new_tracks if track.strip()]
            if not isinstance(trackSecArr, list) or len(trackSecArr) != len(new_tracks):
                trackSecArr = [0 for _ in new_tracks]
            tracks_json = json.dumps(new_tracks, ensure_ascii=False)
            tracks_time_json = json.dumps(trackSecArr, ensure_ascii=False)
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute(f'SELECT id FROM `{table_name}` WHERE id = %s', (album_id,))
            album_info = cursor.fetchone()
            if not album_info:
                cursor.close()
                return jsonify({"code": 404, "msg": "专辑不存在或暂无编辑权限！"}), 200
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET tracks = %s, is_customized = 1, tracks_time = %s
                WHERE id = %s
            ''', (tracks_json, tracks_time_json, album_id))
            db.commit()
            cursor.close()
            return jsonify({
                "code": 200,
                "msg": "曲目列表保存成功！秒数已同步保存",
                "data": {"tracks": new_tracks, "tracks_time": trackSecArr}
            })
        except Exception as e:
            print(f"❌ 编辑曲目保存失败：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"保存曲目失败：{str(e)}"}), 200

    @app.route('/api/album/update/favourite_tracks/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_album_favourite_tracks(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            data = request.get_json()
            # 变量名同步修改，语义对应收藏曲目
            new_favourite_tracks = data.get('tracks', [])
            full_tracks = data.get('full_tracks', [])
            favourite_trackSecArr = data.get('tracks_time', [])

            # 收藏曲目数组清洗：去空、去首尾空格
            if isinstance(new_favourite_tracks, list):
                new_favourite_tracks = [track.strip() for track in new_favourite_tracks if track.strip()]

            # 收藏曲目时长校验：长度不一致/非数组则填充默认值0
            if not isinstance(favourite_trackSecArr, list) or len(favourite_trackSecArr) != len(new_favourite_tracks):
                favourite_trackSecArr = [0 for _ in new_favourite_tracks]

            # 核心修改1：数据库列对应替换 tracks → favourite_tracks
            favourite_tracks_json = json.dumps(new_favourite_tracks, ensure_ascii=False)
            # 核心修改2：数据库列对应替换 tracks_time → favourite_tracks_time
            favourite_tracks_time_json = json.dumps(favourite_trackSecArr, ensure_ascii=False)

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute(f'SELECT id FROM `{table_name}` WHERE id = %s', (album_id,))
            album_info = cursor.fetchone()
            if not album_info:
                cursor.close()
                return jsonify({"code": 404, "msg": "专辑不存在或暂无编辑权限！"}), 200

            # 核心修改3：SQL语句的字段全部替换为收藏曲目对应字段
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET favourite_tracks = %s, is_customized = 1, favourite_tracks_time = %s
                WHERE id = %s
            ''', (favourite_tracks_json, favourite_tracks_time_json, album_id))
            db.commit()
            cursor.close()
            # 提示文案同步修改为收藏曲目相关，语义匹配
            return jsonify({
                "code": 200,
                "msg": "收藏曲目列表保存成功！收藏曲目秒数已同步保存",
                "data": {"tracks": new_favourite_tracks, "tracks_time": favourite_trackSecArr}
            })
        except Exception as e:
            print(f"❌ 收藏曲目保存失败：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"保存收藏曲目失败：{str(e)}"}), 200

    # ========== ✅ v0.9 P0：专辑动画样式配置读写（按 user_id + album_id 持久化，跨设备同步） ==========
    @app.route('/api/album/style/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_style(album_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            row, owned = _get_style_row(current_user_id, album_id)
            if not owned:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 200
            if not row:
                # 无记录 = 从未配置，首次打开由前端自动生成（data:null）
                return jsonify({"code": 200, "msg": "该专辑尚无样式配置", "data": None})
            return jsonify({
                "code": 200,
                "msg": "获取样式配置成功",
                "data": {
                    "style_type": row["style_type"],
                    "rhy_config": safe_json_loads(row["rhy_config"]) or {},
                    "meteor_config": safe_json_loads(row["meteor_config"]) or {},
                    "auto_manual": row["auto_manual"],
                    "update_time": str(row["update_time"]) if row["update_time"] else None
                }
            })
        except Exception as e:
            print(f"❌ 获取样式配置出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"获取样式配置失败：{str(e)}"}), 200

    @app.route('/api/album/style/<int:album_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def save_album_style(album_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200
            row, owned = _get_style_row(current_user_id, album_id)
            if not owned:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 200

            data = request.get_json(silent=True) or {}
            style = normalize_style_config(data)
            rhy_json = json.dumps(style["rhy_config"], ensure_ascii=False)
            meteor_json = json.dumps(style["meteor_config"], ensure_ascii=False)

            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO user_album_style (user_id, album_id, style_type, rhy_config, meteor_config, auto_manual)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    style_type = VALUES(style_type),
                    rhy_config = VALUES(rhy_config),
                    meteor_config = VALUES(meteor_config),
                    auto_manual = VALUES(auto_manual)
            ''', (current_user_id, album_id, style["style_type"], rhy_json, meteor_json, style["auto_manual"]))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "样式配置保存成功",
                "data": {
                    "album_id": album_id,
                    "style_type": style["style_type"],
                    "rhy_config": style["rhy_config"],
                    "meteor_config": style["meteor_config"],
                    "auto_manual": style["auto_manual"]
                }
            })
        except Exception as e:
            print(f"❌ 保存样式配置出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"保存样式配置失败：{str(e)}"}), 200


