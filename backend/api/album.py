# 专辑基础操作接口 - 增删改查、列表、详情
from flask import request, jsonify
import json
import traceback
from ..db_utils import get_db, get_album_table_name, current_user_id
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, VALID_SORT_FIELDS


def register_album_routes(app):
    """注册专辑基础操作路由（需传入Flask app实例）"""

    # 1. 兼容前端的 /api/album/list 接口（转发到/get_album_list）
    @app.route('/api/album/list', methods=['GET'])
    @login_required
    def album_list_compatible():
        return get_album_list()

    # 2. 获取专辑列表（带分页、排序）
    @app.route('/api/music', methods=['GET'])
    @login_required
    def get_album_list():
        try:
            # 获取分页和排序参数
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
            sort_by = request.args.get('sort_by', 'album_name')
            sort_order = request.args.get('sort_order', 'asc')

            # 验证排序参数合法性
            if sort_by not in VALID_SORT_FIELDS:
                sort_by = 'album_name'
            if sort_order not in ['asc', 'desc']:
                sort_order = 'asc'

            # 获取当前用户的专辑表名
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 1. 查询总条数（用于分页）
            cursor.execute(f'SELECT COUNT(*) as total FROM `{table_name}`')
            total = cursor.fetchone()['total']

            # 2. 计算分页偏移量
            offset = (page - 1) * page_size

            # 3. 带排序和分页的查询
            cursor.execute(f'''
                SELECT * FROM `{table_name}` 
                ORDER BY `{sort_by}` {sort_order.upper()}
                LIMIT %s OFFSET %s
            ''', (page_size, offset))
            albums = cursor.fetchall()
            cursor.close()

            # 解析JSON字段（tags/main_type等）
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
                    "tags": json.loads(album["tags"] or "") if album["tags"] is not None else [],
                    "main_type": json.loads(album["main_type"] or "") if album["main_type"] is not None else [],
                    "code": album["code"],
                    "video_shared": album["video_shared"],
                    "mandopop_code": album["mandopop_code"],
                    "tracks": json.loads(album["tracks"] or "") if album["tracks"] is not None else [],
                    "review": json.loads(album["review"] or "") if album["review"] is not None else {},
                    "score": album["score"],
                    "comments": json.loads(album["comments"] or "") if album["comments"] is not None else []
                }
                album_list.append(album_dict)

            # 构造分页数据
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

    # 3. 添加专辑（写入用户专属表 + 同步到专辑搜索池）
    @app.route('/api/album/add', methods=['POST'])
    @login_required
    def add_album():
        try:
            data = request.get_json()
            table_name = get_album_table_name(current_user_id)

            # 校验必填字段
            required_fields = ['album_name', 'singer', 'release_year', 'main_type']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"code": 400, "msg": f"{field}不能为空！"}), 400

            # 整理专辑数据（兼容重构后的review结构）
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
                # 重构后的review结构
                "review": json.dumps({
                    "feelings": [],  # 原有听后感列表
                    "single_score": 0.0,
                    "private_score": 0.0,
                    "final_score": 0.0,
                    "personal_feeling": "",  # 新增单条听后感
                    "update_time": ""
                }) or "",
                "score": float(data.get('score', 0.0)),
                "comments": json.dumps([]) or ""
            }

            # 写入用户专属表
            db = get_db()
            cursor = db.cursor()
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

            # 同步插入专辑搜索池
            main_type_str = json.dumps(data.get('main_type', [])) if data.get('main_type') else ""
            cursor.execute('''
                INSERT INTO album_pool (
                    album_name, cover_img, singer, release_year, 
                    main_type, tags, my_score, create_user
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                new_album['album_name'],
                new_album['cover_img'],
                new_album['singer'],
                new_album['release_year'],
                main_type_str,
                new_album['tags'],
                new_album['my_score'],
                current_user_id
            ))

            db.commit()
            cursor.close()

            # 构造返回数据（解析JSON字段）
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

    # 4. 删除专辑（删除用户专属表数据）
    @app.route('/api/album/delete/<int:album_id>', methods=['DELETE'])
    @login_required
    def delete_album(album_id):
        try:
            # 获取当前用户的专辑表名
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 执行删除操作
            cursor.execute(f'DELETE FROM `{table_name}` WHERE id = %s', (album_id,))
            affected_rows = cursor.rowcount  # 获取受影响行数
            db.commit()
            cursor.close()

            # 判断是否删除成功
            if affected_rows == 0:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            return jsonify({
                "code": 200,
                "msg": f"删除ID为{album_id}的专辑成功！"
            })
        except Exception as e:
            print(f"❌ 删除专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 500

    # 5. 获取专辑详情
    @app.route('/api/album/detail/<int:album_id>', methods=['GET'])
    @login_required
    def get_album_detail(album_id):
        try:
            # 获取当前用户的专辑表名
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询专辑详情
            cursor.execute(f'SELECT * FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            cursor.close()

            if not album:
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 解析JSON字段
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
                "tags": json.loads(album["tags"]) if album["tags"] else [],
                "main_type": json.loads(album["main_type"]) if album["main_type"] else [],
                "code": album["code"],
                "video_shared": album["video_shared"],
                "mandopop_code": album["mandopop_code"],
                "tracks": json.loads(album["tracks"]) if album["tracks"] else [],
                "review": json.loads(album["review"]) if album["review"] else {},
                "score": album["score"],
                "comments": json.loads(album["comments"]) if album["comments"] else []
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