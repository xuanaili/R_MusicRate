from flask import request, jsonify
import json
import traceback
from ..db_utils import (
    get_db, get_album_table_name, get_current_user_id,
    save_user_album_intro, get_user_album_intro
)
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, VALID_SORT_FIELDS
import pymysql


def register_album_routes(app):
    """注册专辑基础操作路由（需传入Flask app实例）"""

    # 1. 兼容前端的 /api/album/list 接口
    @app.route('/api/album/list', methods=['GET', 'OPTIONS'])
    @login_required
    def album_list_compatible():
        return get_album_list()

    # 2. 获取专辑列表 ✅核心修改：新增独立的类型搜索参数 tag_keyword
    @app.route('/api/music', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_list():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
            sort_by = request.args.get('sort_by', 'album_name')
            sort_order = request.args.get('sort_order', 'asc')
            # 原有：综合搜索关键词 → 只搜【专辑名+歌手】
            search_keyword = request.args.get('search_keyword', '').strip()
            # ✅ 新增：独立的类型搜索关键词 → 只搜【tags标签数组】
            tag_keyword = request.args.get('tag_keyword', '').strip()

            if sort_by not in VALID_SORT_FIELDS:
                sort_by = 'album_name'
            if sort_order not in ['asc', 'desc']:
                sort_order = 'asc'

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # ========== ✅✅✅ 核心修改：双搜索条件 叠加生效 ✅✅✅ ==========
            base_sql = f'SELECT COUNT(*) as total FROM `{table_name}`'
            select_sql = f'SELECT * FROM `{table_name}`'
            where_conditions = []
            sql_params = []

            # 条件1：综合搜索 → 专辑名 + 歌手
            if search_keyword:
                where_conditions.append("(album_name LIKE %s OR singer LIKE %s)")
                like_search = f"%{search_keyword}%"
                sql_params.extend([like_search, like_search])

            # 条件2：独立类型搜索 → 只匹配tags标签数组
            if tag_keyword:
                where_conditions.append("tags LIKE %s")
                like_tag = f"%{tag_keyword}%"
                sql_params.append(like_tag)

            # 拼接所有搜索条件（多个条件用 AND 连接 → 叠加筛选）
            if where_conditions:
                where_sql = " WHERE " + " AND ".join(where_conditions)
                base_sql += where_sql
                select_sql += where_sql

            cursor.execute(base_sql, tuple(sql_params))
            total = cursor.fetchone()['total']
            # ========== ✅✅✅ 核心修改结束 ✅✅✅ ==========

            offset = (page - 1) * page_size

            cursor.execute(f'''
                {select_sql}
                ORDER BY `{sort_by}` {sort_order.upper()}
                LIMIT %s OFFSET %s
            ''', tuple(sql_params) + (page_size, offset))
            albums = cursor.fetchall()
            cursor.close()

            # 增强版JSON解析容错函数 兼容 数组+字典
            def safe_json_loads(s, is_dict=False):
                if not s:
                    return {} if is_dict else []
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return {} if is_dict else []

            album_list = []
            for album in albums:
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
                    "tracks_time": safe_json_loads(album.get("tracks_time"))
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
            cursor.execute(f'SELECT * FROM `{table_name}` WHERE id = %s', (album_id,))
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
            "listening_duration": album.get("listening_duration", 0) or 0
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

            # ========== ✅✅✅ 核心修改 1：获取前端传递的 tracks_time 并格式化 ==========
            # 获取前端的单曲名数组 + 时间戳秒数数组
            tracks_list = data.get('tracks', [])
            tracks_time_list = data.get('tracks_time', [])
            # 格式化处理：保证是数组、长度一致、空值填充0
            if not isinstance(tracks_list, list):
                tracks_list = []
            if not isinstance(tracks_time_list, list):
                tracks_time_list = []
            # 过滤空的单曲名，保证数据干净
            tracks_list = [track.strip() for track in tracks_list if track.strip()]
            # 补全时间戳数组：长度不一致时，缺的部分填充0
            if len(tracks_time_list) < len(tracks_list):
                tracks_time_list += [0] * (len(tracks_list) - len(tracks_time_list))
            elif len(tracks_time_list) > len(tracks_list):
                tracks_time_list = tracks_time_list[:len(tracks_list)]
            # 转JSON字符串，存入数据库
            tracks_json = json.dumps(tracks_list, ensure_ascii=False)
            tracks_time_json = json.dumps(tracks_time_list, ensure_ascii=False)
            track_count = len(tracks_list)  # 自动计算单曲数量
            # ========== ✅✅✅ 核心修改 1 结束 ==========

            album_intro = data.get('album_intro', '').strip()
            new_album = {
                "album_name": album_name,
                "cover_img": data.get('cover_img', '').strip(),
                "singer": singer,
                "release_year": release_year,
                "start_time": data.get('start_time', ''),
                "track_count": track_count,  # ✅ 修改：自动赋值单曲数量
                "track_duration": data.get('track_duration', ''),
                "my_score": float(data.get('my_score', 0.0)),
                "burn_class": data.get('burn_class', ''),
                "duration_type": data.get('duration_type', ''),
                "tags": json.dumps(data.get('tags', [])) or "",
                "main_type": json.dumps(data.get('main_type', [])) or "",
                "code": data.get('code', ''),
                "video_shared": data.get('video_shared', ''),
                "mandopop_code": data.get('mandopop_code', ''),
                "album_intro": album_intro,
                "tracks": tracks_json,  # ✅ 修改：赋值格式化后的单曲名JSON
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
                "tracks_time": tracks_time_json  # ✅ 修改：赋值格式化后的时间戳JSON
            }
            main_type_str = json.dumps(data.get('main_type', [])) if data.get('main_type') else ""

            # ========== ✅✅✅ 核心修改 2：修改 album_pool 插入SQL → 新增 tracks_time 字段 ==========
            cursor.execute('''
                INSERT INTO album_pool (
                    album_name, cover_img, singer, release_year, 
                    main_type, tags, album_intro, tracks, tracks_time, my_score, create_user
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                new_album['album_name'],
                new_album['cover_img'],
                new_album['singer'],
                new_album['release_year'],
                main_type_str,
                new_album['tags'],
                new_album['album_intro'],
                new_album['tracks'],
                new_album['tracks_time'],  # ✅ 插入：公共池 存入 tracks_time
                new_album['my_score'],
                current_user_id
            ))
            # ========== ✅✅✅ 核心修改 2 结束 ==========

            new_pool_id = cursor.lastrowid
            new_album['source_pool_id'] = new_pool_id

            # ========== ✅✅✅ 核心修改 3：用户表插入SQL 不变，tracks_time 已在new_album赋值好 ==========
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
                new_album['tracks_time']  # ✅ 插入：用户表 存入 tracks_time
            ))
            # ========== ✅✅✅ 核心修改 3 结束 ==========

            new_album_id = cursor.lastrowid
            if album_intro:
                save_user_album_intro(current_user_id, new_album_id, album_intro)
            db.commit()
            cursor.close()
            return_album = new_album.copy()
            return_album['id'] = new_album_id
            return_album['tags'] = json.loads(return_album['tags'])
            return_album['main_type'] = json.loads(return_album['main_type'])
            return_album['tracks'] = json.loads(return_album['tracks'])
            return_album['review'] = json.loads(return_album['review'])
            return_album['comments'] = json.loads(return_album['comments'])
            return_album['tracks_time'] = json.loads(return_album['tracks_time'])  # ✅ 返回：时间戳数组
            return jsonify({
                "code": 200,
                "msg": "专辑添加成功！单曲时间戳已同步保存",
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


