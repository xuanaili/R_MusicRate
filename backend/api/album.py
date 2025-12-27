from flask import request, jsonify
import json
import traceback
from ..db_utils import get_db, get_album_table_name, get_current_user_id
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, VALID_SORT_FIELDS
import pymysql

def register_album_routes(app):
    """注册专辑基础操作路由（需传入Flask app实例）"""

    # 1. 兼容前端的 /api/album/list 接口
    @app.route('/api/album/list', methods=['GET', 'OPTIONS'])  # 仅加OPTIONS
    @login_required
    def album_list_compatible():
        return get_album_list()

    # 2. 获取专辑列表（完全保留你原来的逻辑 + 修复JSON解析容错）
    @app.route('/api/music', methods=['GET', 'OPTIONS'])  # 仅加OPTIONS
    @login_required
    def get_album_list():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            # 以下所有代码完全保留你原来的版本，仅修改JSON解析部分
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
            sort_by = request.args.get('sort_by', 'album_name')
            sort_order = request.args.get('sort_order', 'asc')

            if sort_by not in VALID_SORT_FIELDS:
                sort_by = 'album_name'
            if sort_order not in ['asc', 'desc']:
                sort_order = 'asc'

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            cursor.execute(f'SELECT COUNT(*) as total FROM `{table_name}`')
            total = cursor.fetchone()['total']

            offset = (page - 1) * page_size

            cursor.execute(f'''
                SELECT * FROM `{table_name}` 
                ORDER BY `{sort_by}` {sort_order.upper()}
                LIMIT %s OFFSET %s
            ''', (page_size, offset))
            albums = cursor.fetchall()
            cursor.close()

            # ========== 核心修复：新增JSON解析容错函数 ==========
            def safe_json_loads(s):
                """安全解析JSON字符串，兼容空值/空字符串/非法JSON"""
                if not s:  # None/空字符串/空值
                    return []
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return []

            album_list = []
            for album in albums:
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
                    # 修复tags解析
                    "tags": safe_json_loads(album["tags"]),
                    # 修复main_type解析（核心错误点）
                    "main_type": safe_json_loads(album["main_type"]),
                    "code": album["code"],
                    "video_shared": album["video_shared"],
                    "mandopop_code": album["mandopop_code"],
                    # 修复tracks解析
                    "tracks": safe_json_loads(album["tracks"]),
                    # 修复review解析（注意review是字典，容错为{}）
                    "review": safe_json_loads(album["review"]) if safe_json_loads(album["review"]) is not None else {},
                    "score": album["score"],
                    # 修复comments解析
                    "comments": safe_json_loads(album["comments"]),
                    # 新增：同步相关字段（用于前端展示同步状态）
                    "source_pool_id": album.get("source_pool_id"),
                    "sync_pool_update": album.get("sync_pool_update", 1),
                    "is_customized": album.get("is_customized", 0)
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
            return jsonify({"code": 500, "msg": f"获取专辑出错：{str(e)}"}), 500

    # 在album.py中新增接口（用户专辑管理）
    @app.route('/api/album/sync/switch', methods=['POST'])
    @login_required
    def switch_album_sync():
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "未登录！"}), 401

            data = request.get_json()
            album_id = data.get('album_id')
            sync_status = data.get('sync_status', 1)  # 1=开启，0=关闭

            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空！"}), 400

            db = get_db()
            cursor = db.cursor()
            table_name = get_album_table_name(user_id)

            # 更新同步开关
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
            return jsonify({"code": 500, "msg": f"操作失败：{str(e)}"}), 500

    @app.route('/api/album/mark/customized', methods=['POST'])
    @login_required
    def mark_album_customized():
        try:
            user_id = get_current_user_id()
            data = request.get_json()
            album_id = data.get('album_id')

            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空！"}), 400

            db = get_db()
            cursor = db.cursor()
            table_name = get_album_table_name(user_id)

            # 标记为已自定义修改（后续不再同步模板更新）
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET is_customized = 1 
                WHERE id = %s
            ''', (album_id,))

            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "标记自定义修改成功！",
                "data": {"album_id": album_id}
            })
        except Exception as e:
            return jsonify({"code": 500, "msg": f"操作失败：{str(e)}"}), 500

    # ========== 优化：保存用户专辑标签接口 - 同步更新统计 ==========
    @app.route('/api/album/update/tags/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_album_tags(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            data = request.get_json()
            tags = data.get('tags', [])

            # 校验标签：最多5个，去重，过滤空值
            tags = list(set([tag.strip() for tag in tags if tag.strip()]))[:5]
            tags_json = json.dumps(tags)

            # 更新用户私有专辑的标签
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 检查专辑是否存在
            cursor.execute(f'SELECT id, source_pool_id FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 更新用户专辑标签
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET tags = %s 
                WHERE id = %s
            ''', (tags_json, album_id))

            # 同步更新到公共专辑关联表（如果关联了公共专辑）
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
                    # 没有关联记录则新增
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
            return jsonify({"code": 500, "msg": f"保存标签失败：{str(e)}"}), 500

    # 3. 补充专辑详情接口（关键：加OPTIONS，逻辑和列表一致）
    @app.route('/api/album/detail/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_detail(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            cursor.execute(f'SELECT * FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            cursor.close()

            if not album:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # ========== 新增容错函数 ==========
            def safe_json_loads(s):
                if not s:
                    return []
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return []

            # 解析逻辑和列表完全一致（使用容错函数）
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
                "tracks": safe_json_loads(album["tracks"]),
                "review": safe_json_loads(album["review"]) if safe_json_loads(album["review"]) is not None else {},
                "score": album["score"],
                "comments": safe_json_loads(album["comments"]),
                # 新增：同步相关字段
                "source_pool_id": album.get("source_pool_id"),
                "sync_pool_update": album.get("sync_pool_update", 1),
                "is_customized": album.get("is_customized", 0)
            }

            return jsonify({
                "code": 200,
                "msg": "获取专辑详情成功！",
                "data": album_dict
            })
        except Exception as e:
            print(f"❌ 获取专辑详情出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取专辑详情失败：{str(e)}"}), 500

    # 4. 添加专辑接口（核心修改：补充tracks写入album_pool）
    @app.route('/api/album/add', methods=['POST', 'OPTIONS'])
    @login_required
    def add_album():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            data = request.get_json()
            table_name = get_album_table_name(current_user_id)

            required_fields = ['album_name', 'singer', 'release_year']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"code": 400, "msg": f"{field}不能为空！"}), 400

            # ========== 核心修改1：处理tracks默认值（兼容MySQL TEXT无默认值） ==========
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

            new_album = {
                "album_name": data.get('album_name').strip(),
                "cover_img": data.get('cover_img', '').strip(),
                "singer": data.get('singer').strip(),
                "release_year": int(data.get('release_year')),
                "start_time": data.get('start_time', ''),
                "track_count": int(data.get('track_count', 0)),
                "track_duration": data.get('track_duration', ''),
                "my_score": float(data.get('my_score', 0.0)),
                "burn_class": data.get('burn_class', ''),
                "duration_type": data.get('duration_type', ''),
                "tags": json.dumps(data.get('tags', [])) or "",
                "main_type": json.dumps(data.get('main_type', [])) or "",
                "code": data.get('code', ''),
                "video_shared": data.get('video_shared', ''),
                "mandopop_code": data.get('mandopop_code', ''),
                "tracks": json.dumps(data.get('tracks', [])) or "",
                "review": json.dumps({
                    "feelings": [],
                    "single_score": 0.0,
                    "private_score": 0.0,
                    "final_score": 0.0,
                    "personal_feeling": "",
                    "update_time": ""
                }) or "",
                "score": float(data.get('score', 0.0)),
                "comments": json.dumps([]) or ""
            }

            db = get_db()
            cursor = db.cursor()
            # 插入用户专属表（原有逻辑不变）
            cursor.execute(f'''
                INSERT INTO `{table_name}` (
                    album_name, cover_img, singer, release_year, start_time,
                    track_count, track_duration, my_score, burn_class, duration_type,
                    tags, main_type, code, video_shared, mandopop_code,
                    tracks, review, score, comments
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            ''', (
                new_album['album_name'], new_album['cover_img'], new_album['singer'],
                new_album['release_year'], new_album['start_time'], new_album['track_count'],
                new_album['track_duration'], new_album['my_score'], new_album['burn_class'],
                new_album['duration_type'], new_album['tags'], new_album['main_type'],
                new_album['code'], new_album['video_shared'], new_album['mandopop_code'],
                new_album['tracks'], new_album['review'], new_album['score'],
                new_album['comments']
            ))
            new_album_id = cursor.lastrowid

            # ========== 核心修改2：插入album_pool时补充tracks字段 ==========
            main_type_str = json.dumps(data.get('main_type', [])) if data.get('main_type') else ""
            tracks_str = get_default_tracks_value(data.get('tracks', []))  # 处理默认值
            cursor.execute('''
                INSERT INTO album_pool (
                    album_name, cover_img, singer, release_year, 
                    main_type, tags, tracks, my_score, create_user
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                new_album['album_name'],
                new_album['cover_img'],
                new_album['singer'],
                new_album['release_year'],
                main_type_str,
                new_album['tags'],
                tracks_str,  # 新增：写入tracks字段
                new_album['my_score'],
                current_user_id
            ))

            db.commit()
            cursor.close()

            return_album = new_album.copy()
            return_album['id'] = new_album_id
            return_album['tags'] = json.loads(return_album['tags'])
            return_album['main_type'] = json.loads(return_album['main_type'])
            return_album['tracks'] = json.loads(return_album['tracks'])
            return_album['review'] = json.loads(return_album['review'])
            return_album['comments'] = json.loads(return_album['comments'])

            return jsonify({
                "code": 200,
                "msg": "专辑添加成功！",
                "data": return_album
            })
        except Exception as e:
            print(f"❌ 添加专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"添加专辑失败：{str(e)}"}), 500

    # 5. 删除专辑（删除用户专属表数据）
    @app.route('/api/album/delete/<int:album_id>', methods=['DELETE'])
    @login_required
    def delete_album(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            # 关键点1：必须用当前登录用户的分表名（current_user_id）
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 关键点2：删除条件必须包含album_id（前端传的ID）
            cursor.execute(f'DELETE FROM `{table_name}` WHERE id = %s', (album_id,))
            affected_rows = cursor.rowcount  # 关键：获取受影响行数
            db.commit()
            cursor.close()

            # 关键点3：判断是否真的删除成功（affected_rows > 0 才是成功）
            if affected_rows == 0:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            return jsonify({
                "code": 200,
                "msg": f"删除ID为{album_id}的专辑成功！"
            })
        except Exception as e:
            print(f"删除专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 500