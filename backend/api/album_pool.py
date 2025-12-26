# MusicRate\backend\api\album_pool.py 专辑搜索池接口 - 搜索、复制、详情
from flask import request, jsonify, g
import json
import traceback
from ..db_utils import get_db, get_album_table_name, get_current_user_id
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE

import pymysql.cursors


def register_album_pool_routes(app):
    """注册专辑搜索池相关路由"""

    # 1. 获取专辑搜索池详情（修复路由多写的<符号 + 字段名错误）
    @app.route('/api/album/pool/detail/<int:pool_id>', methods=['GET'])
    @login_required
    def get_pool_album_detail(pool_id):
        try:
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 核心修复：用u.username（不是u.user_name）匹配users表的用户名字段
            cursor.execute('''
                SELECT ap.*, u.username as create_user_name 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                WHERE ap.id = %s
            ''', (pool_id,))
            album = cursor.fetchone()
            cursor.close()

            if not album:
                return jsonify({"code": 404, "msg": "未找到该公共专辑"}), 404

            # 处理JSON字段
            if album.get('tags'):
                album['tags'] = json.loads(album['tags'])
            if album.get('main_type'):
                album['main_type'] = json.loads(album['main_type'])

            # 无匹配用户时，显示"未知用户"
            if not album.get('create_user_name'):
                album['create_user_name'] = "未知用户"

            return jsonify({
                "code": 200,
                "msg": "获取成功",
                "data": album
            })
        except Exception as e:
            print(f"❌ 获取公共专辑详情失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取失败：{str(e)}"}), 500

    # 2. 专辑搜索池 - 搜索接口（修复字段名错误）
    @app.route('/api/album/pool/search', methods=['GET'])
    @login_required
    def search_album_pool():
        try:
            keyword = request.args.get('keyword', '').strip()
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))

            if page < 1:
                page = 1
            if page_size < 1 or page_size > 50:
                page_size = DEFAULT_PAGE_SIZE

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 核心修复：字段名改为u.username，移除多余符号
            query = """
                SELECT ap.*, u.username as create_user_name 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                WHERE 1=1
            """
            params = []
            if keyword:
                query += " AND (ap.album_name LIKE %s OR ap.singer LIKE %s OR ap.tags LIKE %s OR ap.main_type LIKE %s)"
                params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

            # 查询总条数（修复字段名引用）
            count_query = query.replace("SELECT ap.*, u.username as create_user_name", "SELECT COUNT(*) as total")
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']

            offset = (page - 1) * page_size
            query += " ORDER BY ap.create_time DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            cursor.execute(query, params)
            album_list = cursor.fetchall()
            cursor.close()

            # 解析结果
            result_list = []
            for album in album_list:
                # 无用户名时显示"未知用户"
                create_user_name = album.get('create_user_name') or "未知用户"

                result_list.append({
                    "id": album['id'],
                    "album_name": album['album_name'],
                    "cover_img": album['cover_img'],
                    "singer": album['singer'],
                    "release_year": album['release_year'],
                    "main_type": json.loads(album['main_type']) if album['main_type'] else [],
                    "tags": json.loads(album['tags']) if album['tags'] else [],
                    "my_score": album['my_score'],
                    "create_user": album['create_user'],  # 保留原user_id
                    "create_user_name": create_user_name,  # 新增：用户名
                    "create_time": album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album['create_time'] else ''
                })

            total_pages = (total + page_size - 1) // page_size
            pagination = {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

            return jsonify({
                "code": 200,
                "msg": "搜索专辑池成功",
                "data": {
                    "list": result_list,
                    "pagination": pagination
                }
            })
        except Exception as e:
            print(f"❌ 搜索专辑池出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"搜索专辑池失败：{str(e)}"}), 500

    # 3. 删除公共专辑接口（修复路由多写的<符号）
    @app.route('/api/album/pool/delete/<int:pool_id>', methods=['DELETE', 'OPTIONS'])
    @login_required
    def delete_pool_album(pool_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = getattr(g, 'current_user_id', None)
            if not current_user_id:
                return jsonify({"code": 401, "msg": "未登录或登录已过期！"}), 401

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()

            if not user or user['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "无管理员权限，禁止删除！"}), 403

            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！"}), 404

            cursor.execute('DELETE FROM album_pool WHERE id = %s', (pool_id,))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"成功删除ID为{pool_id}的公共专辑！"
            })
        except Exception as e:
            print(f"❌ 删除公共专辑失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除公共专辑失败：{str(e)}"}), 500

    # 新增：修改公共专辑接口（仅管理员可调用）
    @app.route('/api/album/pool/update/<int:pool_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_pool_album(pool_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            # 1. 校验管理员权限
            current_user_id = getattr(g, 'current_user_id', None)
            if not current_user_id:
                return jsonify({"code": 401, "msg": "未登录或登录已过期！"}), 401

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            if not user or user['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "无管理员权限，禁止修改！"}), 403

            # 2. 获取前端提交的修改数据
            data = request.get_json()
            if not data:
                cursor.close()
                return jsonify({"code": 400, "msg": "修改数据不能为空！"}), 400

            # 3. 检查专辑是否存在
            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！"}), 404

            # 4. 构造更新字段
            update_fields = []
            params = []

            # 支持修改的字段列表
            allowed_fields = [
                'album_name', 'singer', 'release_year', 'cover_img',
                'tags', 'main_type', 'my_score'
            ]

            for field in allowed_fields:
                if field in data:
                    # 处理JSON字段（tags/main_type）
                    if field in ['tags', 'main_type'] and isinstance(data[field], list):
                        update_fields.append(f"{field} = %s")
                        params.append(json.dumps(data[field]))
                    else:
                        update_fields.append(f"{field} = %s")
                        params.append(data[field])

            if not update_fields:
                cursor.close()
                return jsonify({"code": 400, "msg": "没有需要更新的字段！"}), 400

            # 5. 执行更新
            update_sql = f"UPDATE album_pool SET {', '.join(update_fields)} WHERE id = %s"
            params.append(pool_id)

            cursor.execute(update_sql, params)
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"成功修改ID为{pool_id}的公共专辑！"
            })
        except Exception as e:
            print(f"❌ 修改公共专辑失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"修改公共专辑失败：{str(e)}"}), 500

    # 4. 复制专辑接口（修复路由多写的<符号）
    @app.route('/api/album/pool/copy/<int:album_id>', methods=['POST'])
    @login_required
    def copy_album(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            db = get_db()
            cursor = db.cursor()

            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (album_id,))
            pool_album = cursor.fetchone()
            if not pool_album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑副本！"}), 404

            table_name = get_album_table_name(current_user_id)

            copy_album_data = {
                "album_name": pool_album['album_name'],
                "cover_img": pool_album['cover_img'],
                "singer": pool_album['singer'],
                "release_year": pool_album['release_year'],
                "start_time": "",
                "track_count": 0,
                "track_duration": "",
                "my_score": 0.0,
                "burn_class": "",
                "duration_type": "",
                "tags": pool_album['tags'],
                "main_type": pool_album['main_type'],
                "code": "",
                "video_shared": "",
                "mandopop_code": "",
                "tracks": json.dumps([]),
                "review": json.dumps({
                    "feelings": [],
                    "single_score": 0.0,
                    "private_score": 0.0,
                    "final_score": 0.0,
                    "personal_feeling": "",
                    "update_time": ""
                }),
                "score": 0.0,
                "comments": json.dumps([])
            }

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
                copy_album_data['album_name'],
                copy_album_data['cover_img'],
                copy_album_data['singer'],
                copy_album_data['release_year'],
                copy_album_data['start_time'],
                copy_album_data['track_count'],
                copy_album_data['track_duration'],
                copy_album_data['my_score'],
                copy_album_data['burn_class'],
                copy_album_data['duration_type'],
                copy_album_data['tags'],
                copy_album_data['main_type'],
                copy_album_data['code'],
                copy_album_data['video_shared'],
                copy_album_data['mandopop_code'],
                copy_album_data['tracks'],
                copy_album_data['review'],
                copy_album_data['score'],
                copy_album_data['comments']
            ))

            new_copy_id = cursor.lastrowid
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "复制专辑副本成功！",
                "data": {"copy_album_id": new_copy_id}
            })
        except Exception as e:
            print(f"❌ 复制专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"复制专辑失败：{str(e)}"}), 500

    # 5. 获取专辑池ID接口（无需修改）
    @app.route('/api/album_pool/get_id', methods=['GET'])
    @login_required
    def get_album_pool_id():
        try:
            album_name = request.args.get('album_name')
            singer = request.args.get('singer')
            if not album_name or not singer:
                return jsonify({"code": 400, "msg": "专辑名和歌手不能为空！"}), 400

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT id FROM album_pool 
                WHERE album_name = %s AND singer = %s
            ''', (album_name, singer))
            album = cursor.fetchone()
            cursor.close()

            if album:
                return jsonify({"code": 200, "msg": "查询成功！", "data": {"id": album['id']}})
            else:
                return jsonify({"code": 404, "msg": "专辑池不存在！"}), 404
        except Exception as e:
            print(f"查询专辑池ID失败：{str(e)}")
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500