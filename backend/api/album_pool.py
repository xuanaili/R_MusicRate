from flask import request, jsonify, g
import json
import traceback
import random
import os  # 文件操作模块
from ..db_utils import get_db, get_album_table_name, get_current_user_id
from ..decorators import login_required
# 导入所有需要的配置，包含音频相关
from ..config import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, UPLOAD_FOLDER, AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER

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

    # ========== ✅ 核心复用：封装标签统计复用函数（所有接口共用） ==========
    def get_album_tag_stats(album_pool_id, cursor):
        """
        复用标签统计逻辑，给搜索接口调用
        :param album_pool_id: 专辑池id
        :param cursor: 数据库游标（复用连接，提升性能）
        :return: 统计后的标签数组
        """
        tag_count = {}
        total_tags = 0

        # 1. 查公共专辑池的基础标签
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

        # 2. 遍历所有用户表统计标签
        cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
        user_tables = cursor.fetchall()
        for table in user_tables:
            table_name = table['TABLE_NAME']
            try:
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

        # 3. 计算占比，过滤<10%的标签，生成颜色和大小
        result = []
        if total_tags > 0:
            for tag, count in tag_count.items():
                percent = (count / total_tags) * 100
                if percent >= 10:
                    size = int(percent * 2 + 40)
                    color = f"#{random.randint(0, 0xFFFFFF):06x}"
                    result.append({
                        "tag": tag,
                        "count": count,
                        "percent": round(percent, 1),
                        "size": size,
                        "color": color
                    })
        return result

    # ========== 通用JSON解析容错函数 ==========
    def safe_json_loads(s):
        if s is None or s == "":
            return None
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return None

    # ========== 修复：获取专辑标签统计接口（气泡图用） - 修正数据来源 ==========
    @app.route('/api/album/<int:album_pool_id>/tag-statistics', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_statistics(album_pool_id):
        # 处理OPTIONS预检请求，必加！！！
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
        try:
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 修复：从所有用户的专辑表中统计标签（而非仅user_album_relation）
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()

            # 步骤1：统计所有用户对该专辑的标签
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
            # 异常返回 200状态码 + 500业务码，前端不报错，只提示文案
            return jsonify({"code": 500, "msg": f"统计失败：{str(e)}", "data": {}}), 200

    # 1. 获取专辑搜索池详情（完整修复：新增tracks字段返回+JSON容错 + 新增album_intro）
    @app.route('/api/album/pool/detail/<int:pool_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_pool_album_detail(pool_id):
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
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
                # 无数据返回200状态码 + 404业务码，友好提示
                return jsonify({"code": 404, "msg": "未找到该公共专辑", "data": {}}), 200

            # 处理所有JSON字段（包含tracks）
            album['tags'] = safe_json_loads(album.get('tags')) or []
            album['main_type'] = safe_json_loads(album.get('main_type')) or []
            # 核心：处理tracks字段（兼容字典/数组/空值）
            album['tracks'] = safe_json_loads(album.get('tracks')) or []
            # 处理时长类型 duration_type
            album['duration_type'] = album.get('duration_type', 'LP') or 'LP'
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
            return jsonify({"code": 500, "msg": f"获取失败：{str(e)}", "data": {}}), 200

    # ✅✅✅ 拆分接口1：【专辑名+歌手 专属搜索】- 只搜专辑名、歌手、专辑简介，精准匹配基础信息
    @app.route('/api/album/pool/search/name-singer', methods=['GET', 'OPTIONS'])
    @login_required
    def search_album_pool_by_name_singer():
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
        try:
            keyword = request.args.get('keyword', '').strip()
            keyword_lower = keyword.lower()
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))

            if page < 1:
                page = 1
            if page_size < 1 or page_size > 50:
                page_size = DEFAULT_PAGE_SIZE

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 核心：只对【专辑名、歌手、专辑简介】做模糊搜索，纯基础信息匹配，无标签逻辑
            query = """
                SELECT ap.*, u.username as create_user_name 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                WHERE 1=1
            """
            params = []
            if keyword_lower:
                query += " AND (ap.album_name LIKE %s OR ap.singer LIKE %s OR ap.album_intro LIKE %s)"
                params.extend([
                    f'%{keyword}%',
                    f'%{keyword}%',
                    f'%{keyword}%'
                ])

            # 查询总条数
            count_query = query.replace("SELECT ap.*, u.username as create_user_name", "SELECT COUNT(*) as total")
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']

            offset = (page - 1) * page_size
            query += " ORDER BY ap.create_time DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            cursor.execute(query, params)
            album_list = cursor.fetchall()

            # 最终返回的结果集
            result_list = []
            for album in album_list:
                create_user_name = album.get('create_user_name') or "未知用户"
                # 计算聚合标签（仅前端展示，不参与搜索）
                album_tag_stats = get_album_tag_stats(album['id'], cursor)

                result_list.append({
                    "id": album['id'],
                    "album_name": album['album_name'],
                    "cover_img": album['cover_img'],
                    "singer": album['singer'],
                    "release_year": album['release_year'],
                    "main_type": safe_json_loads(album.get('main_type')) or [],
                    "tags": safe_json_loads(album.get('tags')) or [],
                    "tracks": safe_json_loads(album.get('tracks')) or [],
                    "album_intro": album.get('album_intro', '') or '',
                    "duration_type": album.get('duration_type', 'LP') or 'LP',
                    "my_score": album['my_score'],
                    "create_user": album['create_user'],
                    "create_user_name": create_user_name,
                    "create_time": album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album.get(
                        'create_time') else '',
                    "tag_statistics": album_tag_stats,
                })

            total_pages = (total + page_size - 1) // page_size
            pagination = {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "按专辑名/歌手搜索成功",
                "data": {
                    "list": result_list,
                    "pagination": pagination
                }
            })
        except Exception as e:
            print(f"❌ 按专辑名/歌手搜索出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"搜索失败：{str(e)}", "data": {}}), 200

    # ✅✅✅ 拆分接口2：【标签 专属搜索】- 只搜聚合标签+原始标签，纯标签维度精准匹配，无基础信息干扰
    @app.route('/api/album/pool/search/tags', methods=['GET', 'OPTIONS'])
    @login_required
    def search_album_pool_by_tags():
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
        try:
            tag_keyword = request.args.get('tag', '').strip()
            tag_keyword_lower = tag_keyword.lower()
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))

            if page < 1:
                page = 1
            if page_size < 1 or page_size > 50:
                page_size = DEFAULT_PAGE_SIZE

            if not tag_keyword_lower:
                return jsonify({
                    "code": 400,
                    "msg": "标签搜索关键词不能为空！",
                    "data": {"list": [],
                             "pagination": {"total": 0, "page": page, "page_size": page_size, "total_pages": 0}}
                }), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 核心：查询全部公共专辑，不做SQL过滤，所有过滤逻辑在Python中按标签匹配
            query = """
                SELECT ap.*, u.username as create_user_name 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                ORDER BY ap.create_time DESC
            """
            cursor.execute(query)
            album_list = cursor.fetchall()
            total = len(album_list)

            # 分页切片处理
            offset = (page - 1) * page_size
            album_list = album_list[offset:offset + page_size]

            # 最终返回的结果集
            result_list = []
            # 遍历每一条专辑数据，纯标签匹配逻辑
            for album in album_list:
                create_user_name = album.get('create_user_name') or "未知用户"
                # 第一步：为当前专辑，计算出【前端展示的完整聚合标签】
                album_tag_stats = get_album_tag_stats(album['id'], cursor)
                # 提取聚合标签的纯文本列表（转小写去重）
                album_all_tags = [item['tag'].lower() for item in album_tag_stats]
                # 提取专辑原始标签的纯文本列表（兼容数据库里的JSON原始标签）
                album_origin_tags = safe_json_loads(album.get('tags')) or []
                album_origin_tags = [tag.lower().strip() for tag in album_origin_tags if tag and tag.strip()]
                # 合并：原始标签+聚合标签 = 所有可能的标签，去重
                all_match_tags = list(set(album_all_tags + album_origin_tags))

                # 核心判断【标签关键词是否匹配】精准匹配+包含匹配
                tag_match = False
                if tag_keyword_lower:
                    tag_match = tag_keyword_lower in all_match_tags or any(
                        [tag_keyword_lower in tag for tag in all_match_tags])

                # 符合标签匹配条件的专辑，才加入最终结果集
                if tag_match:
                    result_list.append({
                        "id": album['id'],
                        "album_name": album['album_name'],
                        "cover_img": album['cover_img'],
                        "singer": album['singer'],
                        "release_year": album['release_year'],
                        "main_type": safe_json_loads(album.get('main_type')) or [],
                        "tags": safe_json_loads(album.get('tags')) or [],
                        "tracks": safe_json_loads(album.get('tracks')) or [],
                        "album_intro": album.get('album_intro', '') or '',
                        "duration_type": album.get('duration_type', 'LP') or 'LP',
                        "my_score": album['my_score'],
                        "create_user": album['create_user'],
                        "create_user_name": create_user_name,
                        "create_time": album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album.get(
                            'create_time') else '',
                        "tag_statistics": album_tag_stats,  # 前端展示的标签，原样返回
                    })

            total_pages = (total + page_size - 1) // page_size
            pagination = {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "按标签搜索专辑池成功",
                "data": {
                    "list": result_list,
                    "pagination": pagination
                }
            })
        except Exception as e:
            print(f"❌ 按标签搜索专辑池出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"标签搜索失败：{str(e)}", "data": {}}), 200

    # 3. 删除公共专辑接口（✅最终完美版：级联删除【音频资源+封面+用户数据+专辑】，无残留+无报错）
    @app.route('/api/album/pool/delete/<int:pool_id>', methods=['DELETE', 'OPTIONS'])
    @login_required
    def delete_pool_album(pool_id):
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200

        try:
            current_user_id = getattr(g, 'current_user_id', None)
            if not current_user_id:
                # 未登录返回200+401，友好提示，不报错
                return jsonify({"code": 401, "msg": "未登录或登录已过期！", "data": {}}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 检查管理员权限
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            if not user or user['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "无管理员权限，禁止删除！", "data": {}}), 200

            # ========== 查询专辑完整信息：包含封面+音频相关字段 ==========
            cursor.execute('SELECT id, cover_img, mp3_url, mp3_name, mp3_duration FROM album_pool WHERE id = %s',
                           (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！", "data": {}}), 200

            delete_audio_flag = False
            # ========== 步骤1：删除【专辑音频资源文件】+ 清空音频数据库字段 ==========
            mp3_url = album.get('mp3_url', '')
            if mp3_url and mp3_url.strip() and AUDIO_BASE_URL in mp3_url:
                try:
                    audio_filename = mp3_url.replace(AUDIO_BASE_URL, '')
                    full_audio_path = os.path.join(AUDIO_UPLOAD_FOLDER, audio_filename)
                    if os.path.exists(full_audio_path):
                        os.remove(full_audio_path)
                        delete_audio_flag = True
                        print(f"✅ 成功删除专辑音频文件：{full_audio_path}")
                    # 无论文件是否删除成功，都清空音频字段，保证数据一致性
                    cursor.execute('''
                        UPDATE album_pool 
                        SET mp3_url = NULL, mp3_name = NULL, mp3_duration = NULL 
                        WHERE id = %s
                    ''', (pool_id,))
                    print(f"✅ 成功清空专辑ID[{pool_id}]的音频数据库字段")
                except Exception as e:
                    print(f"⚠️ 删除音频文件/清空字段失败：{str(e)}")

            # ========== 步骤2：删除【专辑封面图片】 ==========
            cover_img_url = album.get('cover_img', '')
            if cover_img_url and cover_img_url.strip():
                try:
                    filename = cover_img_url.split('/')[-1]
                    full_img_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.exists(full_img_path):
                        os.remove(full_img_path)
                        print(f"✅ 成功删除本地图床封面图片：{full_img_path}")
                    else:
                        print(f"⚠️ 本地封面图片不存在：{full_img_path}")
                except Exception as e:
                    print(f"❌ 解析/删除封面图片失败：{str(e)}")

            # ========== 步骤3：级联删除 - 所有用户表中关联该专辑的记录 ==========
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()
            delete_user_count = 0
            for table in user_tables:
                table_name = table['TABLE_NAME']
                try:
                    cursor.execute(f'DELETE FROM `{table_name}` WHERE source_pool_id = %s', (pool_id,))
                    delete_user_count += cursor.rowcount
                except Exception as e:
                    print(f"❌ 删除用户表 {table_name} 关联数据失败：{str(e)}")
                    continue

            # ========== 步骤4：删除【公共专辑池本身】的记录 ==========
            cursor.execute('DELETE FROM album_pool WHERE id = %s', (pool_id,))
            db.commit()
            cursor.close()

            # 拼接返回提示语
            audio_tip = "并删除音频资源文件" if delete_audio_flag else "音频文件不存在/删除失败"
            return jsonify({
                "code": 200,
                "msg": f"成功删除ID为{pool_id}的公共专辑！{audio_tip}，清理封面图片，同时删除了{delete_user_count}条用户关联的专辑数据",
                "data": {}
            })
        except Exception as e:
            print(f"❌ 删除公共专辑失败：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"删除公共专辑失败：{str(e)}", "data": {}}), 200

    # ========== 新增核心接口：获取拥有当前公共专辑的所有用户 ==========
    @app.route('/api/album/pool/users/<int:pool_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_pool_users(pool_id):
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
        try:
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            cursor.execute('''
                SELECT ur.create_time, u.username as name
                FROM user_album_relation ur
                LEFT JOIN users u ON ur.user_id = u.user_id
                WHERE ur.album_pool_id = %s
                AND u.username IS NOT NULL AND u.username != ''
                ORDER BY ur.create_time DESC
                LIMIT 100
            ''', (pool_id,))
            user_list = cursor.fetchall()
            cursor.close()

            def format_create_time(time_str):
                if not time_str:
                    return "未知时间"
                try:
                    return str(time_str).split(' ')[0]
                except Exception:
                    return "未知时间"

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
            return jsonify({"code": 500, "msg": f"获取用户列表失败：{str(e)}", "data": {}}), 200

    # 4. 修改公共专辑接口（核心修改：只同步专辑名/歌手/发行时间，保留用户所有自定义内容 + 重复友好提示）
    @app.route('/api/album/pool/update/<int:pool_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def update_pool_album(pool_id):
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200

        try:
            current_user_id = getattr(g, 'current_user_id', None)
            if not current_user_id:
                return jsonify({"code": 401, "msg": "未登录或登录已过期！", "data": {}}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            if not user or user['is_admin'] != 1:
                cursor.close()
                return jsonify({"code": 403, "msg": "无管理员权限，禁止修改！", "data": {}}), 200

            data = request.get_json()
            if not data:
                cursor.close()
                return jsonify({"code": 400, "msg": "修改数据不能为空！", "data": {}}), 200

            # 查询原专辑信息
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (pool_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{pool_id}的公共专辑！", "data": {}}), 200

            # ========== 核心：修改时防重复校验（专辑名+歌手+发行时间） ==========
            new_album_name = data.get('album_name', album['album_name']).strip()
            new_singer = data.get('singer', album['singer']).strip()
            new_release_year = int(data.get('release_year', album['release_year']))
            new_duration_type = data.get('duration_type', album.get('duration_type', 'LP')).strip()

            cursor.execute('''
                SELECT id FROM album_pool 
                WHERE album_name = %s AND singer = %s AND release_year = %s AND id != %s
            ''', (new_album_name, new_singer, new_release_year, pool_id))
            duplicate_album = cursor.fetchone()
            if duplicate_album:
                cursor.close()
                # ✅ 重点：返回200状态码 + 409业务码，前端正常解析文案，不报错！
                return jsonify({
                    "code": 409,
                    "msg": f"公共专辑池中已存在【{new_album_name} - {new_singer} ({new_release_year})】，无法修改！",
                    "data": {"duplicate_pool_id": duplicate_album['id']}
                }), 200

            update_fields = []
            params = []
            allowed_fields = ['album_name', 'singer', 'release_year', 'cover_img', 'tags', 'main_type', 'my_score',
                              'tracks', 'album_intro', 'duration_type']
            update_log = []

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
                elif field == 'duration_type':
                    old_val = album.get('duration_type', 'LP')
                    if new_duration_type != old_val:
                        update_log.append(f"{field}：{old_val} → {new_duration_type}")
                        update_fields.append(f"`{field}` = %s")
                        params.append(new_duration_type)
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
                return jsonify({"code": 400, "msg": "没有需要更新的字段！", "data": {}}), 200

            # 版本号+更新日志
            current_version = album.get('version', 1)
            new_version = current_version + 1
            update_fields.extend(["`version` = %s", "`update_log` = %s"])
            params.extend([new_version, json.dumps(update_log)])
            params.append(pool_id)

            # 执行公共专辑更新
            update_sql = f"UPDATE `album_pool` SET {', '.join(update_fields)} WHERE `id` = %s"
            cursor.execute(update_sql, params)

            # ========== ✅ 核心还原：只同步【专辑名、歌手、发行时间】这三个字段 ==========
            cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
            user_tables = cursor.fetchall()
            sync_count = 0

            only_sync_fields = {
                "album_name": new_album_name,
                "singer": new_singer,
                "release_year": new_release_year
            }

            for table in user_tables:
                table_name = table['TABLE_NAME']
                try:
                    cursor.execute(f'SELECT `id` FROM `{table_name}` WHERE `source_pool_id` = %s', (pool_id,))
                    user_albums = cursor.fetchall()

                    for user_album in user_albums:
                        user_album_id = user_album['id']
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
            return jsonify({"code": 500, "msg": f"修改公共专辑失败：{str(e)}", "data": {}}), 200

    # 5. 复制专辑接口 ✅【终极修复核心】：重复时友好提示+无报错 + 所有BUG修复
    @app.route('/api/album/pool/copy/<int:album_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def copy_album(album_id):
        # ✅ 必加：处理OPTIONS预检请求，解决跨域预检失败导致的后端报错提示
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200

        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                # ✅ 未登录：返回200+401，友好提示，不触发服务异常
                return jsonify({"code": 401, "msg": "用户未登录，请先登录！", "data": {}}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # ===== 第一步：检查公共专辑池是否存在 =====
            cursor.execute('SELECT * FROM album_pool WHERE id = %s', (album_id,))
            pool_album = cursor.fetchone()
            if not pool_album:
                cursor.close()
                # ✅ 无数据：返回200+404，友好提示
                return jsonify({"code": 404, "msg": f"公共专辑池中未找到ID为{album_id}的专辑！", "data": {}}), 200

            table_name = get_album_table_name(current_user_id)

            # ===== ✅✅✅ 核心：双重重复校验【公共库规则+私有库规则】，全部友好提示 =====
            album_name = pool_album['album_name'].strip()
            singer = pool_album['singer'].strip()
            release_year = pool_album['release_year']

            # 校验1：当前用户【私有库】是否已存在 → 专辑名+歌手+发行年份 重复
            cursor.execute(f'''
                SELECT id FROM `{table_name}` 
                WHERE TRIM(album_name) = %s AND TRIM(singer) = %s AND release_year = %s
            ''', (album_name, singer, release_year))
            duplicate_private_album = cursor.fetchone()
            if duplicate_private_album:
                cursor.close()
                # ✅ 最重要修复：返回【200 HTTP状态码】+ 【409 业务错误码】
                # ✅ 前端能正常解析msg文案，弹窗显示「私有列表已存在」，不会出现「检查后端是否启动」
                return jsonify({
                    "code": 409,
                    "msg": f"✅ 你的私有专辑列表中已存在【{album_name} - {singer} ({release_year})】，无需重复复制！",
                    "data": {"duplicate_album_id": duplicate_private_album['id']}
                }), 200

            # 校验2：公共专辑池是否重复（兜底校验）
            cursor.execute('''
                SELECT id FROM album_pool 
                WHERE TRIM(album_name) = %s AND TRIM(singer) = %s AND release_year = %s
            ''', (album_name, singer, release_year))
            duplicate_pool_album = cursor.fetchone()
            if duplicate_pool_album and duplicate_pool_album['id'] != album_id:
                cursor.close()
                return jsonify({
                    "code": 409,
                    "msg": f"✅ 公共专辑搜索池中已存在相同专辑【{album_name} - {singer} ({release_year})】，请勿重复添加！",
                    "data": {"duplicate_pool_id": duplicate_pool_album['id']}
                }), 200

            # ===== 数据处理，原有逻辑不变 =====
            pool_tracks = safe_json_loads(pool_album.get('tracks')) or []
            pool_tracks = [track.strip() for track in pool_tracks if track and track.strip()]
            tracks_json = json.dumps(pool_tracks) if pool_tracks else json.dumps([])

            copy_album_data = {
                "album_name": pool_album['album_name'],
                "cover_img": pool_album['cover_img'],
                "singer": pool_album['singer'],
                "release_year": pool_album['release_year'],
                "start_time": "",
                "track_count": len(pool_tracks),
                "track_duration": "",
                "my_score": pool_album['my_score'],
                "burn_class": "",
                "duration_type": pool_album.get('duration_type', 'LP') or 'LP',
                "tags": pool_album['tags'],
                "main_type": pool_album['main_type'],
                "tracks": tracks_json,
                "album_intro": pool_album.get('album_intro', '') or '',
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
                "source_pool_id": album_id,
                "sync_pool_update": 1,
                "is_customized": 0
            }

            cursor.execute(f'''
                INSERT INTO `{table_name}` (
                    album_name, cover_img, singer, release_year, start_time,
                    track_count, track_duration, my_score, burn_class, duration_type,
                    tags, main_type, code, video_shared, mandopop_code,
                    tracks, album_intro, review, score, comments,
                    source_pool_id, sync_pool_update, is_customized
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
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
                copy_album_data['album_intro'],
                copy_album_data['review'],
                copy_album_data['score'],
                copy_album_data['comments'],
                copy_album_data['source_pool_id'],
                copy_album_data['sync_pool_update'],
                copy_album_data['is_customized']
            ))

            new_copy_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO user_album_relation (user_id, album_pool_id, tags)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE create_time = NOW()
            ''', (current_user_id, album_id, pool_album['tags']))

            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "复制成功！该专辑已添加到你的私有专辑列表中",
                "data": {
                    "copy_album_id": new_copy_id,
                    "source_pool_id": album_id,
                    "sync_pool_update": 1,
                    "album_intro": copy_album_data['album_intro'][:50] + "..." if len(
                        copy_album_data['album_intro']) > 50 else copy_album_data['album_intro'],
                    "duration_type": copy_album_data['duration_type']
                }
            })
        except Exception as e:
            print(f"❌ 复制专辑出错：{str(e)}")
            print(traceback.format_exc())
            # ✅ 异常也返回200状态码，前端只提示文案，不报错
            return jsonify({"code": 500, "msg": f"复制专辑失败：{str(e)}", "data": {}}), 200

    # 6. 获取专辑池ID接口（修正路由路径，和前端保持一致）
    @app.route('/api/album_pool/get_id', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_pool_id():
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200
        try:
            album_name = request.args.get('album_name')
            singer = request.args.get('singer')
            if not album_name or not singer:
                return jsonify({"code": 400, "msg": "专辑名和歌手不能为空！", "data": {}}), 200

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
                return jsonify({"code": 404, "msg": "专辑池不存在！", "data": {}}), 200
        except Exception as e:
            print(f"查询专辑池ID失败：{str(e)}")
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}", "data": {}}), 200