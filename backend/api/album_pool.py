from flask import request, jsonify, g
import json
import traceback
import random
from ..db_utils import get_db, get_album_table_name, get_current_user_id
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE

import pymysql.cursors


def register_album_pool_routes(app):
    """注册专辑搜索池相关路由"""

    # ========== 修复：获取专辑标签统计接口（气泡图用） - 修正数据来源 ==========
    @app.route('/api/album/<int:album_pool_id>/tag-statistics', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_statistics(album_pool_id):
        try:
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 修复：从所有用户的专辑表中统计标签（而非仅user_album_relation）
            # 步骤1：获取所有用户专辑表
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()

            # 步骤2：统计所有用户对该专辑的标签
            tag_count = {}
            total_tags = 0

            # 先查公共专辑池的基础标签
            cursor.execute('SELECT tags FROM album_pool WHERE id = %s', (album_pool_id,))
            pool_album = cursor.fetchone()
            if pool_album and pool_album['tags']:
                try:
                    pool_tags = json.loads(pool_album['tags'])
                    for tag in pool_tags:
                        tag = tag.strip()
                        if tag:
                            tag_count[tag] = tag_count.get(tag, 0) + 1
                            total_tags += 1
                except:
                    pass

            # 遍历所有用户表统计标签
            for table in user_tables:
                table_name = table['TABLE_NAME']
                try:
                    # 查询该用户表中关联到当前专辑池的专辑
                    cursor.execute(f'''
                        SELECT tags FROM `{table_name}` 
                        WHERE source_pool_id = %s AND tags IS NOT NULL
                    ''', (album_pool_id,))
                    user_albums = cursor.fetchall()
                    print(album_pool_id)
                    for album in user_albums:
                        if album['tags']:
                            try:
                                tags = json.loads(album['tags'])
                                for tag in tags:
                                    tag = tag.strip()
                                    if tag:
                                        tag_count[tag] = tag_count.get(tag, 0) + 1
                                        total_tags += 1
                            except:
                                continue
                except Exception as e:
                    print(f"统计用户表 {table_name} 失败：{str(e)}")
                    continue

            # 步骤3：计算占比，过滤<10%的标签
            result = []
            if total_tags > 0:
                for tag, count in tag_count.items():
                    percent = (count / total_tags) * 100
                    if percent >= 10:
                        # 计算气泡大小（按占比动态调整）
                        size = int(percent * 2 + 40)
                        # 随机生成颜色
                        color = f"#{random.randint(0, 0xFFFFFF):06x}"
                        result.append({
                            "tag": tag,
                            "count": count,
                            "percent": round(percent, 1),
                            "size": size,
                            "color": color
                        })

            cursor.close()
            print(f"专辑{album_pool_id}标签统计结果：{result}")
            return jsonify({"code": 200, "msg": "成功", "data": result})
        except Exception as e:
            print(f"❌ 标签统计失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"统计失败：{str(e)}"}), 500

    # 1. 获取专辑搜索池详情（完整修复：新增tracks字段返回+JSON容错）
    @app.route('/api/album/pool/detail/<int:pool_id>', methods=['GET'])
    @login_required
    def get_pool_album_detail(pool_id):
        try:
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 核心修复：用u.username匹配users表的用户名字段
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

            # 统一的JSON解析容错函数（优化：保留None，不强制转空数组）
            def safe_json_loads(s):
                if s is None or s == "":
                    return None
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return None

            # 处理所有JSON字段（包含tracks）
            album['tags'] = safe_json_loads(album.get('tags')) or []
            album['main_type'] = safe_json_loads(album.get('main_type')) or []
            # 核心：处理tracks字段（兼容字典/数组/空值）
            album['tracks'] = safe_json_loads(album.get('tracks')) or []

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

    # 2. 专辑搜索池 - 搜索接口（完整修复：新增tracks字段返回）
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
                query += " AND (ap.album_name LIKE %s OR ap.singer LIKE %s OR ap.tags LIKE %s OR ap.main_type LIKE %s OR ap.tracks LIKE %s)"
                params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

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

            # 统一的JSON解析容错函数（优化：保留None，不强制转空数组）
            def safe_json_loads(s):
                if s is None or s == "":
                    return None
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return None

            # 解析结果（新增tracks字段）
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
                    "main_type": safe_json_loads(album.get('main_type')) or [],
                    "tags": safe_json_loads(album.get('tags')) or [],
                    "tracks": safe_json_loads(album.get('tracks')) or [],  # 新增tracks字段
                    "my_score": album['my_score'],
                    "create_user": album['create_user'],  # 保留原user_id
                    "create_user_name": create_user_name,  # 新增：用户名
                    "create_time": album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album.get(
                        'create_time') else ''
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

    # 4. 修改公共专辑接口（仅管理员可调用，新增tracks字段支持 + 核心修复tracks同步置空问题）
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
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！"}), 404

            # 4. 构造更新字段 + 记录修改日志（新增tracks字段支持）
            update_fields = []
            params = []
            # 允许修改的字段新增tracks
            allowed_fields = ['album_name', 'singer', 'release_year', 'cover_img', 'tags', 'main_type', 'my_score',
                              'tracks']
            update_log = []  # 记录字段修改前后的值

            # 统一的JSON解析容错函数（优化：保留None，不强制转空数组）
            def safe_json_loads(s):
                if s is None or s == "":
                    return None
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return None

            # ========== 核心修复1：预处理tracks，过滤空值 ==========
            # 解析公共专辑原有tracks
            original_pool_tracks = safe_json_loads(album.get('tracks')) or []
            # 解析前端提交的tracks
            new_pool_tracks = data.get('tracks')
            # 过滤空值：确保是有效非空数组
            if isinstance(new_pool_tracks, list):
                new_pool_tracks = [track.strip() for track in new_pool_tracks if track and track.strip()]
            else:
                # 非数组格式，用原有值
                new_pool_tracks = original_pool_tracks

            for field in allowed_fields:
                if field == 'tracks':
                    # tracks字段单独处理：只在前端传了有效非空tracks时才更新
                    if new_pool_tracks and new_pool_tracks != original_pool_tracks:
                        old_val = json.dumps(original_pool_tracks)
                        new_val = json.dumps(new_pool_tracks)
                        update_log.append(f"{field}：{old_val} → {new_val}")
                        update_fields.append(f"{field} = %s")
                        params.append(json.dumps(new_pool_tracks))
                elif field in data and data[field] != album[field]:
                    # 其他字段原有逻辑
                    old_val = album[field] if album[field] is not None else ""
                    new_val = data[field] if data[field] is not None else ""
                    update_log.append(f"{field}：{old_val} → {new_val}")

                    # 处理JSON字段（列表转JSON字符串）
                    if field in ['tags', 'main_type'] and isinstance(data[field], list):
                        update_fields.append(f"{field} = %s")
                        params.append(json.dumps(data[field]))
                    else:
                        update_fields.append(f"{field} = %s")
                        params.append(data[field])

            # 无更新字段直接返回
            if not update_fields:
                cursor.close()
                return jsonify({"code": 400, "msg": "没有需要更新的字段！"}), 400

            # 5. 版本号递增 + 写入修改日志
            current_version = album.get('version', 1)
            new_version = current_version + 1
            update_fields.append("version = %s")
            params.append(new_version)
            update_fields.append("update_log = %s")
            params.append(json.dumps(update_log))
            params.append(pool_id)  # WHERE 条件的 pool_id

            # 6. 执行公共模板更新
            update_sql = f"UPDATE album_pool SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(update_sql, params)

            # ========== 核心同步逻辑（修复tracks同步置空问题） ==========
            # 7. 获取所有用户专辑表（修复：字段名大写 TABLE_NAME）
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()
            sync_count = 0  # 累计同步成功的用户数据条数

            # 准备同步数据（确保tracks是JSON字符串且非空）
            sync_tracks = json.dumps(new_pool_tracks) if new_pool_tracks else album.get('tracks')

            for table in user_tables:
                table_name = table['TABLE_NAME']  # 修复：大写字段名取值
                try:
                    # 先查询该表中需要同步的用户专辑（获取原有tracks，避免空覆盖）
                    cursor.execute(f'''
                        SELECT id FROM `{table_name}` 
                        WHERE source_pool_id = %s AND sync_pool_update = 1 AND is_customized = 0
                    ''', (pool_id,))
                    user_albums = cursor.fetchall()

                    for user_album in user_albums:
                        user_album_id = user_album['id']
                        # 构造用户专辑更新字段
                        user_update_fields = [
                            'album_name = %s',
                            'singer = %s',
                            'release_year = %s',
                            'cover_img = %s',
                            'tags = %s',
                            'main_type = %s',
                            'my_score = %s'
                        ]
                        user_params = [
                            data.get('album_name', album['album_name']),
                            data.get('singer', album['singer']),
                            data.get('release_year', album['release_year']),
                            data.get('cover_img', album['cover_img']),
                            json.dumps(safe_json_loads(data.get('tags', album.get('tags'))) or []),
                            json.dumps(safe_json_loads(data.get('main_type', album.get('main_type'))) or []),
                            data.get('my_score', album['my_score'])
                        ]

                        # ========== 核心修复2：tracks非空才同步 ==========
                        if sync_tracks and sync_tracks != "[]":
                            user_update_fields.append('tracks = %s')
                            user_params.append(sync_tracks)

                        # 加入WHERE条件
                        user_update_fields.append('id = %s')
                        user_params.append(user_album_id)

                        # 执行单条更新（避免批量更新的空覆盖问题）
                        user_update_sql = f'''
                            UPDATE `{table_name}` 
                            SET {', '.join(user_update_fields)}
                            WHERE id = %s
                        '''
                        cursor.execute(user_update_sql, user_params)
                        sync_count += 1

                except Exception as e:
                    print(f"❌ 同步表 {table_name} 失败：{str(e)}")
                    continue
            # ========== 同步逻辑结束 ==========

            db.commit()  # 提交事务
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"成功修改ID为{pool_id}的公共专辑！同步更新了{sync_count}条用户数据",
                "data": {
                    "sync_count": sync_count,
                    "new_version": new_version,
                    "update_log": update_log
                }
            })
        except Exception as e:
            print(f"❌ 修改公共专辑失败：{str(e)}")
            print(traceback.format_exc())
            # 异常时回滚事务，防止数据不一致
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"修改公共专辑失败：{str(e)}"})

    # 5. 复制专辑接口（修复路由多写的<符号 + 新增同步字段 + tracks同步）
    @app.route('/api/album/pool/copy/<int:album_id>', methods=['POST'])
    @login_required
    def copy_album(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            db = get_db()
            # 关键：使用DictCursor，方便按字段名取值
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 查询公共模板数据（用DictCursor获取字典格式）
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (album_id,))
            pool_album = cursor.fetchone()
            if not pool_album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑副本！"}), 404

            table_name = get_album_table_name(current_user_id)

            # 统一的JSON解析容错函数（优化：保留None，不强制转空数组）
            def safe_json_loads(s):
                if s is None or s == "":
                    return None
                try:
                    return json.loads(s)
                except (json.JSONDecodeError, TypeError):
                    return None

            # ========== 修复：过滤tracks空值，确保复制的tracks有效 ==========
            pool_tracks = safe_json_loads(pool_album.get('tracks')) or []
            pool_tracks = [track.strip() for track in pool_tracks if track and track.strip()]
            tracks_json = json.dumps(pool_tracks) if pool_tracks else json.dumps([])

            # 构造复制数据（新增tracks字段同步）
            copy_album_data = {
                "album_name": pool_album['album_name'],
                "cover_img": pool_album['cover_img'],
                "singer": pool_album['singer'],
                "release_year": pool_album['release_year'],
                "start_time": "",
                "track_count": len(pool_tracks),  # 同步track_count（基于有效tracks）
                "track_duration": "",
                "my_score": pool_album['my_score'],  # 同步模板的评分
                "burn_class": "",
                "duration_type": "",
                "tags": pool_album['tags'],
                "main_type": pool_album['main_type'],
                "tracks": tracks_json,  # 修复：使用过滤后的tracks
                "code": "",
                "video_shared": "",
                "mandopop_code": "",
                "review": json.dumps({
                    "feelings": [],
                    "single_score": 0.0,
                    "private_score": 0.0,
                    "final_score": 0.0,
                    "personal_feeling": "",
                    "update_time": ""
                }),
                "score": 0.0,
                "comments": json.dumps([]),
                # 核心新增：同步相关字段
                "source_pool_id": album_id,  # 关联公共模板ID
                "sync_pool_update": 1,  # 默认开启同步
                "is_customized": 0  # 默认未自定义
            }

            # 插入SQL（新增tracks和同步字段）
            cursor.execute(f'''
                INSERT INTO `{table_name}` (
                    album_name, cover_img, singer, release_year, start_time,
                    track_count, track_duration, my_score, burn_class, duration_type,
                    tags, main_type, code, video_shared, mandopop_code,
                    tracks, review, score, comments,
                    source_pool_id, sync_pool_update, is_customized  -- 新增同步字段
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s  -- 同步字段对应的值
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
                copy_album_data['tracks'],  # 新增tracks参数
                copy_album_data['review'],
                copy_album_data['score'],
                copy_album_data['comments'],
                # 同步字段的值
                copy_album_data['source_pool_id'],
                copy_album_data['sync_pool_update'],
                copy_album_data['is_customized']
            ))

            new_copy_id = cursor.lastrowid
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "复制专辑副本成功！已开启模板同步",
                "data": {
                    "copy_album_id": new_copy_id,
                    "source_pool_id": album_id,  # 返回模板ID，方便前端验证
                    "sync_pool_update": 1
                }
            })
        except Exception as e:
            print(f"❌ 复制专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"复制专辑失败：{str(e)}"}), 500

    # 6. 获取专辑池ID接口（修正路由路径，和前端保持一致）
    @app.route('/api/album_pool/get_id', methods=['GET', 'OPTIONS'])
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