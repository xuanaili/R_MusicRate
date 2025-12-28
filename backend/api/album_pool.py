from flask import request, jsonify, g
import json
import traceback
import random
import os  # 新增：文件操作模块
from ..db_utils import get_db, get_album_table_name, get_current_user_id
from ..decorators import login_required
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, UPLOAD_FOLDER  # 新增：导入上传文件夹配置

import pymysql.cursors


def register_album_pool_routes(app):
    """注册专辑搜索池相关路由"""

    # ========== 通用工具函数：安全切片（修复核心） ==========
    def safe_slice(value, max_length=50):
        """
        安全的字符串切片函数，处理None和非字符串类型
        :param value: 原始值（可能为None/字符串/数字等）
        :param max_length: 最大长度
        :return: 截断后的字符串
        """
        if value is None:
            return ""
        # 统一转为字符串（兼容数字/布尔等类型）
        value_str = str(value)
        # 切片并返回
        return value_str[:max_length]

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
            return jsonify({"code": 200, "msg": "成功", "data": result})
        except Exception as e:
            print(f"❌ 标签统计失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"统计失败：{str(e)}"}), 500

    # 1. 获取专辑搜索池详情（完整修复：新增tracks字段返回+JSON容错 + 新增album_intro）
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
            # 新增：处理专辑简介字段
            album['album_intro'] = album.get('album_intro', '') or ''  # 直接保留字符串，无需JSON解析

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

    # 2. 专辑搜索池 - 搜索接口（完整修复：新增tracks字段返回 + 新增album_intro）
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
                query += " AND (ap.album_name LIKE %s OR ap.singer LIKE %s OR ap.tags LIKE %s OR ap.main_type LIKE %s OR ap.tracks LIKE %s OR ap.album_intro LIKE %s)"
                params.extend(
                    [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

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

            # 解析结果（新增tracks字段 + album_intro）
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
                    "album_intro": album.get('album_intro', '') or '',  # 新增专辑简介字段
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

    # 3. 删除公共专辑接口（核心修改：级联删除所有用户的关联专辑 + 删除本地封面图片）
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

            # 检查管理员权限
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            if not user or user['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "无管理员权限，禁止删除！"}), 403

            # 查询专辑信息（重点获取cover_img字段）
            cursor.execute('SELECT id, cover_img FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！"}), 404

            # ========== 核心修改1：解析本地图床URL，提取文件名并删除封面图片 ==========
            cover_img_url = album.get('cover_img', '')
            if cover_img_url and cover_img_url.strip():
                try:
                    filename = cover_img_url.split('/')[-1]
                    full_img_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.exists(full_img_path):
                        os.remove(full_img_path)
                        print(f"✅ 成功删除本地图床封面图片：{full_img_path}")
                    else:
                        print(f"⚠️ 本地图片不存在：{full_img_path}")
                except Exception as e:
                    print(f"❌ 解析/删除封面图片失败：{str(e)}")
                    print(traceback.format_exc())

            # ========== 核心新增：级联删除 - 先删除所有用户表中关联该专辑的记录 ==========
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()
            delete_user_count = 0
            for table in user_tables:
                table_name = table['TABLE_NAME']
                try:
                    # 删除当前用户表中关联此专辑池的所有数据
                    cursor.execute(f'DELETE FROM `{table_name}` WHERE source_pool_id = %s', (pool_id,))
                    delete_user_count += cursor.rowcount
                except Exception as e:
                    print(f"❌ 删除用户表 {table_name} 关联数据失败：{str(e)}")
                    continue

            # ========== 删除公共专辑池本身的记录 ==========
            cursor.execute('DELETE FROM album_pool WHERE id = %s', (pool_id,))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"成功删除ID为{pool_id}的公共专辑！已清理相关封面图片，同时删除了{delete_user_count}条用户关联的专辑数据"
            })
        except Exception as e:
            print(f"❌ 删除公共专辑失败：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"删除公共专辑失败：{str(e)}"}), 500

    # ========== 新增核心接口：获取拥有当前公共专辑的所有用户（按create_time倒序，最多100条，适配你的表结构） ==========
    @app.route('/api/album/pool/users/<int:pool_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_pool_users(pool_id):
        try:
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # ✅ 核心修改：全部用 create_time 替代 add_time，完美匹配你的表结构
            cursor.execute('''
                SELECT ur.create_time, u.username as name
                FROM user_album_relation ur
                LEFT JOIN users u ON ur.user_id = u.user_id
                WHERE ur.album_pool_id = %s
                AND u.username IS NOT NULL AND u.username != ''
                ORDER BY ur.create_time DESC  -- 按【创建时间倒序】，最新添加的用户在最上面
                LIMIT 100  -- 最多显示最近的100个用户
            ''', (pool_id,))
            user_list = cursor.fetchall()
            cursor.close()

            # 格式化时间：统一转为 2025-12-28 格式，和你前端原假数据格式完全一致，前端不用改一行代码
            def format_create_time(time_str):
                if not time_str:
                    return "未知时间"
                try:
                    return str(time_str).split(' ')[0]
                except Exception:
                    return "未知时间"

            # 返回格式严格匹配前端：name(用户名) + listenTime(时间)，前端无缝对接
            formatted_users = []
            for user in user_list:
                formatted_users.append({
                    "name": user["name"],
                    "listenTime": format_create_time(user["create_time"])
                })

            return jsonify({
                "code": 200,
                "msg": "获取专辑用户列表成功",
                "data": formatted_users
            })
        except Exception as e:
            print(f"❌ 获取专辑用户列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取用户列表失败：{str(e)}"}), 500
    # 4. 修改公共专辑接口（核心修改：只同步专辑名/歌手/发行时间，保留用户所有自定义内容）
    @app.route('/api/album/pool/update/<int:pool_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_pool_album(pool_id):
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
                return jsonify({"code": 403, "msg": "无管理员权限，禁止修改！"}), 403

            data = request.get_json()
            if not data:
                cursor.close()
                return jsonify({"code": 400, "msg": "修改数据不能为空！"}), 400

            # 查询原专辑信息
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！"}), 404

            # ========== 核心：修改时防重复校验（专辑名+歌手+发行时间） ==========
            new_album_name = data.get('album_name', album['album_name']).strip()
            new_singer = data.get('singer', album['singer']).strip()
            new_release_year = int(data.get('release_year', album['release_year']))

            cursor.execute('''
                SELECT id FROM album_pool 
                WHERE album_name = %s AND singer = %s AND release_year = %s AND id != %s
            ''', (new_album_name, new_singer, new_release_year, pool_id))
            duplicate_album = cursor.fetchone()
            if duplicate_album:
                cursor.close()
                return jsonify({
                    "code": 409,
                    "msg": f"公共专辑池中已存在【{new_album_name} - {new_singer} ({new_release_year})】，无法修改！",
                    "data": {"duplicate_pool_id": duplicate_album['id']}
                }), 409

            update_fields = []
            params = []
            allowed_fields = ['album_name', 'singer', 'release_year', 'cover_img', 'tags', 'main_type', 'my_score',
                              'tracks', 'album_intro']
            update_log = []

            def safe_json_loads(s):
                if not s:
                    return None
                try:
                    return json.loads(s)
                except:
                    return None

            # 预处理tracks
            original_pool_tracks = safe_json_loads(album.get('tracks')) or []
            new_pool_tracks = data.get('tracks', original_pool_tracks)
            if isinstance(new_pool_tracks, list):
                new_pool_tracks = [track.strip() for track in new_pool_tracks if track and track.strip()]
            sync_tracks = json.dumps(new_pool_tracks) if new_pool_tracks else album.get('tracks', '[]')

            # 构造公共专辑更新语句
            for field in allowed_fields:
                if field == 'tracks':
                    if new_pool_tracks != original_pool_tracks:
                        old_val = json.dumps(original_pool_tracks)
                        new_val = sync_tracks
                        update_log.append(f"{field}：{safe_slice(old_val)}... → {safe_slice(new_val)}...")
                        update_fields.append(f"`{field}` = %s")
                        params.append(sync_tracks)
                elif field == 'album_intro':
                    new_val = data.get('album_intro', album.get('album_intro', '')).strip()
                    old_val = album.get('album_intro', '')
                    if new_val != old_val:
                        update_log.append(f"{field}：{safe_slice(old_val)}... → {safe_slice(new_val)}...")
                        update_fields.append(f"`{field}` = %s")
                        params.append(new_val)
                elif field in data and str(data[field]).strip() != str(album.get(field, '')).strip():
                    old_val = album.get(field, '')
                    new_val = data[field]
                    update_log.append(f"{field}：{safe_slice(old_val)}... → {safe_slice(new_val)}...")
                    if field in ['tags', 'main_type'] and isinstance(new_val, list):
                        update_fields.append(f"`{field}` = %s")
                        params.append(json.dumps(new_val))
                    else:
                        update_fields.append(f"`{field}` = %s")
                        params.append(new_val)

            if not update_fields:
                cursor.close()
                return jsonify({"code": 400, "msg": "没有需要更新的字段！"}), 400

            # 版本号+更新日志
            current_version = album.get('version', 1)
            new_version = current_version + 1
            update_fields.extend(["`version` = %s", "`update_log` = %s"])
            params.extend([new_version, json.dumps(update_log)])
            params.append(pool_id)

            # 执行公共专辑更新
            update_sql = f"UPDATE `album_pool` SET {', '.join(update_fields)} WHERE `id` = %s"
            cursor.execute(update_sql, params)

            # ========== ✅ 核心修改2：只同步【专辑名、歌手、发行时间】三个字段 ✅ ==========
            # 重点：不再同步 tags/main_type/cover_img/my_score/tracks/album_intro 等任何内容
            # 彻底保留用户自己设置的所有分类、标签、评分、简介等自定义信息，不会被覆盖消失
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()
            sync_count = 0

            # 只定义需要同步的三个核心字段，其他字段全部舍弃
            only_sync_fields = {
                "album_name": new_album_name,
                "singer": new_singer,
                "release_year": new_release_year
            }

            for table in user_tables:
                table_name = table['TABLE_NAME']
                try:
                    # 查询所有关联该公共池的用户专辑
                    cursor.execute(f'SELECT `id` FROM `{table_name}` WHERE `source_pool_id` = %s', (pool_id,))
                    user_albums = cursor.fetchall()

                    for user_album in user_albums:
                        user_album_id = user_album['id']
                        # 极简更新SQL - 只更新三个核心字段
                        user_update_sql = f'''
                            UPDATE `{table_name}` 
                            SET 
                                `album_name` = %s,
                                `singer` = %s,
                                `release_year` = %s
                            WHERE `id` = %s
                        '''
                        user_params = [
                            only_sync_fields['album_name'],
                            only_sync_fields['singer'],
                            only_sync_fields['release_year'],
                            user_album_id
                        ]
                        cursor.execute(user_update_sql, user_params)
                        sync_count += 1

                except Exception as e:
                    print(f"❌ 同步用户表 {table_name} 失败：{str(e)}")
                    continue

            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"成功修改ID为{pool_id}的公共专辑！仅同步专辑名/歌手/发行时间，共同步{sync_count}条用户数据，用户自定义内容全部保留",
                "data": {
                    "sync_count": sync_count,
                    "new_version": new_version,
                    "update_log": update_log,
                    "only_sync_fields": only_sync_fields
                }
            })
        except Exception as e:
            print(f"❌ 修改公共专辑失败：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"修改公共专辑失败：{str(e)}"})

    # 5. 复制专辑接口（修复路由多写的<符号 + 新增同步字段 + tracks同步 + 新增album_intro复制）
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

            # 查询公共模板数据（用DictCursor获取字典格式 + 新增album_intro字段）
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

            # 构造复制数据（新增tracks字段同步 + 新增album_intro字段）
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
                "album_intro": pool_album.get('album_intro', '') or '',  # 新增：复制专辑简介
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

            # 插入SQL（新增tracks和同步字段 + 新增album_intro字段）
            cursor.execute(f'''
                INSERT INTO `{table_name}` (
                    album_name, cover_img, singer, release_year, start_time,
                    track_count, track_duration, my_score, burn_class, duration_type,
                    tags, main_type, code, video_shared, mandopop_code,
                    tracks, album_intro, review, score, comments,
                    source_pool_id, sync_pool_update, is_customized  -- 新增同步字段
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
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
                copy_album_data['album_intro'],  # 新增：专辑简介参数
                copy_album_data['review'],
                copy_album_data['score'],
                copy_album_data['comments'],
                # 同步字段的值
                copy_album_data['source_pool_id'],
                copy_album_data['sync_pool_update'],
                copy_album_data['is_customized']
            ))

            new_copy_id = cursor.lastrowid

            # ================ ✅ 新增核心代码 - 开始 (用create_time，无报错版本) ================
            # 用户复制专辑时，向【用户-专辑关联表】插入记录，用于统计用户列表
            # 适配你的表结构：用create_time，没有add_time字段，tags字段正常传值
            cursor.execute('''
                INSERT INTO user_album_relation (user_id, album_pool_id, tags)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE create_time = NOW()
            ''', (current_user_id, album_id, pool_album['tags']))
            # ON DUPLICATE KEY UPDATE：同一用户+同一专辑重复添加时，只更新最新的创建时间，不重复插入
            # ================ ✅ 新增核心代码 - 结束 ================
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "复制专辑副本成功！已开启模板同步（包含专辑简介）",
                "data": {
                    "copy_album_id": new_copy_id,
                    "source_pool_id": album_id,  # 返回模板ID，方便前端验证
                    "sync_pool_update": 1,
                    "album_intro": copy_album_data['album_intro'][:50] + "..." if len(
                        copy_album_data['album_intro']) > 50 else copy_album_data['album_intro']  # 返回简介预览
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