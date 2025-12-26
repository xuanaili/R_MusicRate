# MusicRate\backend\api\album_pool.py 专辑搜索池接口 - 搜索、复制、详情
from flask import request, jsonify
import json
import traceback
from ..db_utils import get_db, get_album_table_name, get_current_user_id  # 导入get_current_user_id
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE


def register_album_pool_routes(app):
    """注册专辑搜索池相关路由（需传入Flask app实例）"""

    # 1. 获取专辑搜索池详情
    @app.route('/api/album/pool/detail/<int:pool_id>', methods=['GET'])
    @login_required
    def get_pool_album_detail(pool_id):
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            # 查询公共专辑池表
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            cursor.close()

            if not album:
                return jsonify({"code": 404, "msg": "未找到该公共专辑"}), 404

            # 处理JSON字段
            if album.get('tags'):
                album['tags'] = json.loads(album['tags'])
            if album.get('main_type'):
                album['main_type'] = json.loads(album['main_type'])

            return jsonify({
                "code": 200,
                "msg": "获取成功",
                "data": album
            })
        except Exception as e:
            print(f"❌ 获取公共专辑详情失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取失败：{str(e)}"}), 500

    # 2. 专辑搜索池 - 搜索接口
    @app.route('/api/album/pool/search', methods=['GET'])
    @login_required
    def search_album_pool():
        try:
            # 获取前端参数
            keyword = request.args.get('keyword', '').strip()
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))

            # 校验参数合法性
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 50:
                page_size = DEFAULT_PAGE_SIZE

            db = get_db()
            cursor = db.cursor()

            # 构建查询条件（模糊匹配专辑名/歌手/标签/类型）
            query = "SELECT * FROM album_pool WHERE 1=1"
            params = []
            if keyword:
                query += " AND (album_name LIKE %s OR singer LIKE %s OR tags LIKE %s OR main_type LIKE %s)"
                params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

            # 查询总条数（分页用）
            count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']

            # 计算分页偏移量
            offset = (page - 1) * page_size

            # 带分页的主查询
            query += " ORDER BY create_time DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            cursor.execute(query, params)
            album_list = cursor.fetchall()
            cursor.close()

            # 解析JSON字段
            result_list = []
            for album in album_list:
                result_list.append({
                    "id": album['id'],
                    "album_name": album['album_name'],
                    "cover_img": album['cover_img'],
                    "singer": album['singer'],
                    "release_year": album['release_year'],
                    "main_type": json.loads(album['main_type']) if album['main_type'] else [],
                    "tags": json.loads(album['tags']) if album['tags'] else [],
                    "my_score": album['my_score'],
                    "create_user": album['create_user'],
                    "create_time": album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album['create_time'] else ''
                })

            # 构造分页信息
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

    # 3. 专辑搜索池 - 复制专辑接口
    @app.route('/api/album/pool/copy/<int:album_id>', methods=['POST'])
    @login_required
    def copy_album(album_id):
        try:
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            db = get_db()
            cursor = db.cursor()

            # 1. 查询要复制的专辑池数据
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (album_id,))
            pool_album = cursor.fetchone()
            if not pool_album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑副本！"}), 404

            # 2. 获取当前用户的分表名
            table_name = get_album_table_name(current_user_id)

            # 3. 构造复制后的专辑数据
            copy_album_data = {
                "album_name": pool_album['album_name'],
                "cover_img": pool_album['cover_img'],
                "singer": pool_album['singer'],
                "release_year": pool_album['release_year'],
                "start_time": "",
                "track_count": 0,
                "track_duration": "",
                "my_score": 0.0,  # 副本默认评分为0
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

            # 4. 插入到当前用户的分表
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