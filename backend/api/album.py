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

    # 2. 获取专辑列表（完全保留原逻辑 + 修复JSON解析 + 新增专辑简介 + 修复分页BUG + 返回正确的tracks_time【秒数数组】）
    @app.route('/api/music', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_list():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

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

            # ========== 增强版JSON解析容错函数 兼容 数组+字典 ==========
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
                    "tracks_time": safe_json_loads(album.get("tracks_time"))  # ✅ 正确解析：曲目开始秒数数组
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

    # ✅✅✅ 新增核心接口：根据source_pool_id查询当前用户的专属album_id ✅✅✅
    @app.route('/api/album/get-id-by-source', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_id_by_source_pool_id():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            # 获取前端传入的source_pool_id
            source_pool_id = request.args.get('source_pool_id')
            if not source_pool_id or not source_pool_id.isdigit():
                return jsonify({"code": 400, "msg": "source_pool_id不能为空且必须为数字！"}), 400
            source_pool_id = int(source_pool_id)

            # 查询当前用户自己的专辑表，精准匹配source_pool_id
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 核心SQL：只查当前用户的表 + 精准匹配source_pool_id
            cursor.execute(f'''
                SELECT id FROM `{table_name}` 
                WHERE source_pool_id = %s LIMIT 1
            ''', (source_pool_id,))
            album_info = cursor.fetchone()
            cursor.close()

            if album_info and album_info.get('id'):
                # 查询成功，返回精准匹配的album_id
                return jsonify({
                    "code": 200,
                    "msg": "查询专辑ID成功",
                    "data": {
                        "album_id": album_info['id'],
                        "source_pool_id": source_pool_id
                    }
                })
            else:
                # 无匹配数据，返回提示，不报错
                return jsonify({
                    "code": 404,
                    "msg": f"你的专辑列表中暂无source_pool_id={source_pool_id}的专辑",
                    "data": None
                })
        except Exception as e:
            print(f"❌ 根据source_pool_id查询album_id出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500

    # 专辑同步开关
    @app.route('/api/album/sync/switch', methods=['POST'])
    @login_required
    def switch_album_sync():
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "未登录！"}), 401

            data = request.get_json()
            album_id = data.get('album_id')
            sync_status = data.get('sync_status', 1)

            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空！"}), 400

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
            return jsonify({"code": 500, "msg": f"操作失败：{str(e)}"}), 500

    # 标记自定义
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

    # 更新专辑标签
    @app.route('/api/album/update/tags/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_album_tags(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

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
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

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
            return jsonify({"code": 500, "msg": f"保存标签失败：{str(e)}"}), 500

    # 专辑详情接口（返回正确的tracks_time【秒数数组】）
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
                "review": safe_json_loads(album["review"], is_dict=True),
                "score": album["score"],
                "comments": safe_json_loads(album["comments"]),
                "source_pool_id": album.get("source_pool_id"),
                "sync_pool_update": album.get("sync_pool_update", 1),
                "is_customized": album.get("is_customized", 0),
                "tracks_time": safe_json_loads(album.get("tracks_time"))  # ✅ 正确解析：曲目开始秒数数组
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

    # 添加专辑接口
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

            album_name = data.get('album_name').strip()
            singer = data.get('singer').strip()
            release_year = int(data.get('release_year'))

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

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
                }), 409

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
                }), 409

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

            album_intro = data.get('album_intro', '').strip()

            new_album = {
                "album_name": album_name,
                "cover_img": data.get('cover_img', '').strip(),
                "singer": singer,
                "release_year": release_year,
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
                "album_intro": album_intro,
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
                "comments": json.dumps([]) or "",
                "source_pool_id": 0,
                "sync_pool_update": 1,
                "is_customized": 0,
                "tracks_time": json.dumps([])  # ✅ 新增专辑默认空秒数数组
            }

            main_type_str = json.dumps(data.get('main_type', [])) if data.get('main_type') else ""
            tracks_str = get_default_tracks_value(data.get('tracks', []))
            cursor.execute('''
                INSERT INTO album_pool (
                    album_name, cover_img, singer, release_year, 
                    main_type, tags, album_intro, tracks, my_score, create_user
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                new_album['album_name'],
                new_album['cover_img'],
                new_album['singer'],
                new_album['release_year'],
                main_type_str,
                new_album['tags'],
                new_album['album_intro'],
                tracks_str,
                new_album['my_score'],
                current_user_id
            ))
            new_pool_id = cursor.lastrowid
            new_album['source_pool_id'] = new_pool_id

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
            return_album['tracks_time'] = json.loads(return_album['tracks_time'])

            return jsonify({
                "code": 200,
                "msg": "专辑添加成功！",
                "data": return_album
            })
        except Exception as e:
            print(f"❌ 添加专辑出错：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"添加专辑失败：{str(e)}"}), 500

    # 删除专辑
    @app.route('/api/album/delete/<int:album_id>', methods=['DELETE'])
    @login_required
    def delete_album(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
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
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            return jsonify({
                "code": 200,
                "msg": f"删除ID为{album_id}的专辑成功！"
            })
        except Exception as e:
            print(f"删除专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 500

    # 保存专辑简介
    @app.route('/api/album/user/intro/save', methods=['POST', 'OPTIONS'])
    @login_required
    def save_user_album_intro_api():
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "请先登录"}), 401

            data = request.get_json()
            album_id = data.get('album_id')
            intro_content = data.get('intro_content', '').strip()

            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空"}), 400
            if not intro_content:
                return jsonify({"code": 400, "msg": "简介内容不能为空"}), 400

            save_success = save_user_album_intro(user_id, album_id, intro_content)
            if save_success:
                return jsonify({
                    "code": 200,
                    "msg": "专辑简介保存成功（已关联账号）",
                    "data": {"album_id": album_id, "intro_content": intro_content}
                })
            else:
                return jsonify({"code": 500, "msg": "简介保存失败，请稍后重试"}), 500

        except Exception as e:
            print(f"❌ 保存用户专辑简介接口出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存简介失败：{str(e)}"}), 500

    # 获取专辑简介
    @app.route('/api/album/user/intro/get/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_user_album_intro_api(album_id):
        try:
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "请先登录"}), 401

            intro_content = get_user_album_intro(user_id, album_id)
            return jsonify({
                "code": 200,
                "msg": "获取简介成功",
                "data": intro_content
            })

        except Exception as e:
            print(f"❌ 获取用户专辑简介接口出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取简介失败：{str(e)}"}), 500

    # ✅ ✅ ✅ 核心修复接口：保存曲目列表 + 接收并存储【前端传的曲目开始秒数数组】✅ ✅ ✅
    @app.route('/api/album/update/tracks/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_album_tracks(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            # 1. 获取前端传过来的所有参数：曲目名称数组、完整曲目信息、曲目开始秒数数组
            data = request.get_json()
            new_tracks = data.get('tracks', [])
            full_tracks = data.get('full_tracks', [])
            trackSecArr = data.get('tracks_time', []) # ✅ 接收前端的 曲目开始秒数数组

            # 2. 数据容错处理
            if isinstance(new_tracks, list):
                new_tracks = [track.strip() for track in new_tracks if track.strip()]
            # 秒数数组容错：必须是数组，长度和曲目一致，默认补0
            if not isinstance(trackSecArr, list) or len(trackSecArr) != len(new_tracks):
                trackSecArr = [0 for _ in new_tracks]

            # 3. 转成JSON字符串 存入数据库
            tracks_json = json.dumps(new_tracks, ensure_ascii=False)
            tracks_time_json = json.dumps(trackSecArr, ensure_ascii=False)

            # 4. 写入用户专属表 albums_用户ID
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 权限校验：确认专辑属于当前用户
            cursor.execute(f'SELECT id FROM `{table_name}` WHERE id = %s', (album_id,))
            album_info = cursor.fetchone()
            if not album_info:
                cursor.close()
                return jsonify({"code": 404, "msg": "专辑不存在或暂无编辑权限！"}), 404

            # ✅ 核心SQL：同时更新 tracks + is_customized + tracks_time(前端传的秒数数组JSON) ✅
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET tracks = %s, is_customized = 1, tracks_time = %s
                WHERE id = %s
            ''', (tracks_json, tracks_time_json, album_id))

            db.commit()
            cursor.close()

            # 返回给前端：正确的秒数数组，前端可直接渲染和跳转
            return jsonify({
                "code": 200,
                "msg": "曲目列表保存成功！秒数已同步保存",
                "data": {
                    "tracks": new_tracks,
                    "tracks_time": trackSecArr
                }
            })
        except Exception as e:
            print(f"❌ 编辑曲目保存失败：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"保存曲目失败：{str(e)}"}), 500