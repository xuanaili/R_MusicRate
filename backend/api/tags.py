from flask import request, jsonify
import json
import traceback
from backend.utils.db import get_db, get_current_user_id, get_album_table_name

import pymysql

from backend.utils.decorators import login_required
from backend.utils.json import safe_json_loads
from backend.utils.tag import get_album_tag_stats


def register_tags_routes(app):
    """注册音乐风格标签相关路由（新增标签）"""

    # ✅ 1. 新增音乐风格标签接口（仅管理员可访问）
    @app.route('/api/tags/add', methods=['POST', 'OPTIONS'])
    @login_required
    def add_album_tag():
        try:
            # ========== 管理员权限校验 ==========
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            # 查询当前用户是否为管理员
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            # 移除 cursor.close() —— 交给 Flask 自动处理

            # 验证：is_admin=1 才是管理员
            if not user or user.get('is_admin') != 1:
                return jsonify({"code": 403, "msg": "无管理员权限，禁止添加风格！"}), 200

            # ========== 原有逻辑保留（移除手动关闭） ==========
            # 获取请求数据
            data = request.get_json()
            if not data:
                return jsonify({"code": 400, "msg": "请求参数不能为空！"}), 200

            # 提取参数并默认值处理
            tags_name = data.get('tags_name', '').strip()
            aka_name = data.get('aka_name', '').strip()
            parameter_style = data.get('parameter_style', '{}').strip()
            brief_intro = data.get('brief_intro', '').strip()
            detail_intro = data.get('detail_intro', '').strip()
            parent_tag_ids = data.get('parent_tag_ids', '').strip()

            # 必输项校验
            if not tags_name:
                return jsonify({"code": 400, "msg": "风格名称不能为空！"}), 200

            # 检查标签名是否已存在
            cursor.execute('''
                SELECT id FROM album_tags WHERE tags_name = %s AND is_enabled=1
            ''', (tags_name,))
            existing_tag = cursor.fetchone()
            if existing_tag:
                # 移除 cursor.close() 和 db.close()
                return jsonify({"code": 400, "msg": f"风格名称「{tags_name}」已存在！"}), 200

            # 构造插入数据
            insert_data = {
                'tags_name': tags_name,
                'aka_name': aka_name,
                'parameter_style': parameter_style,
                'brief_intro': brief_intro,
                'detail_intro': detail_intro,
                'parent_tag_ids': parent_tag_ids,
                'related_singers': '[]',
                'related_albums': '[]',
                'related_tags': '[]'
            }

            # 插入数据库
            cursor.execute('''
                INSERT INTO album_tags (
                    tags_name, aka_name, parameter_style, brief_intro, 
                    detail_intro, parent_tag_ids, related_singers, 
                    related_albums, related_tags
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                insert_data['tags_name'],
                insert_data['aka_name'],
                insert_data['parameter_style'],
                insert_data['brief_intro'],
                insert_data['detail_intro'],
                insert_data['parent_tag_ids'],
                insert_data['related_singers'],
                insert_data['related_albums'],
                insert_data['related_tags']
            ))
            db.commit()
            tag_id = cursor.lastrowid

            # 移除所有手动关闭连接的代码
            # cursor.close() 和 db.close() 都删掉

            return jsonify({
                "code": 200,
                "msg": "音乐风格添加成功！",
                "data": {
                    "tag_id": tag_id,
                    "tags_name": tags_name
                }
            })

        except Exception as e:
            # 回滚事务（仅当连接未关闭时）
            if 'db' in locals() and not db._closed:
                db.rollback()
            print(f"❌ 新增音乐风格出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"添加风格失败：{str(e)}"}), 200

    # ✅ 2. 获取所有标签列表接口
    @app.route('/api/tags/list', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tags_list():
        try:
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 查询所有启用的标签
            cursor.execute('''
                SELECT id, tags_name, aka_name, brief_intro 
                FROM album_tags 
                WHERE is_enabled=1 
                ORDER BY create_time DESC
            ''')
            tags_list = cursor.fetchall()

            # 移除 cursor.close() 和 db.close()

            return jsonify({
                "code": 200,
                "msg": "获取风格列表成功！",
                "data": {"tags_list": tags_list}
            })

        except Exception as e:
            print(f"❌ 获取风格列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取风格列表失败：{str(e)}"}), 200

    # ✅ 3. 新增：获取标签详情接口
    @app.route('/api/tags/detail', methods=['GET', 'OPTIONS'])
    @login_required  # 如果需要登录才能查看，保留该装饰器；否则移除
    def get_tag_detail():
        try:
            # 获取标签名参数
            tag_name = request.args.get('tagName', '').strip()
            if not tag_name:
                return jsonify({"code": 400, "msg": "标签名称不能为空！"}), 200

            # 查询标签详情
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT 
                    id, tags_name, aka_name, parameter_style, 
                    brief_intro, detail_intro, parent_tag_ids,
                    related_singers, related_albums, related_tags,
                    create_time, update_time
                FROM album_tags 
                WHERE is_enabled=1 AND (tags_name = %s OR aka_name LIKE %s)
                LIMIT 1
            ''', (tag_name, f'%{tag_name}%'))  # 支持通过别名查询

            tag_info = cursor.fetchone()

            if not tag_info:
                return jsonify({"code": 404, "msg": f"未找到标签「{tag_name}」的相关信息！"}), 200

            # 返回标签详情
            return jsonify({
                "code": 200,
                "msg": "获取标签详情成功！",
                "data": tag_info
            })

        except Exception as e:
            print(f"❌ 获取标签详情出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取标签详情失败：{str(e)}"}), 200



    # 在 register_tags_routes 函数中新增以下接口
    # ✅ 4. 新增：获取树状结构的标签列表接口
    @app.route('/api/tags/tree', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tags_tree():
        try:
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 查询所有启用的标签
            cursor.execute('''
                SELECT 
                    id, tags_name, aka_name, brief_intro, 
                    parent_tag_ids, create_time
                FROM album_tags 
                WHERE is_enabled=1 
                ORDER BY tags_name ASC
            ''')
            tags_list = cursor.fetchall()

            # 将扁平数据转换为树状结构
            def build_tag_tree(tags):
                # 1. 构建ID到标签的映射
                tag_map = {tag['id']: tag for tag in tags}

                # 2. 分离根节点（无父ID或父ID为空）和子节点
                root_tags = []
                for tag in tags:
                    # 初始化children字段
                    tag['children'] = []
                    parent_ids = tag['parent_tag_ids'].strip()

                    # 根节点：parent_tag_ids为空或0
                    if not parent_ids or parent_ids == '0':
                        root_tags.append(tag)
                    else:
                        # 处理多个父ID（取第一个作为主要父节点）
                        parent_id_list = [p.strip() for p in parent_ids.split(',') if p.strip()]
                        if parent_id_list:
                            main_parent_id = int(parent_id_list[0])
                            if main_parent_id in tag_map:
                                tag_map[main_parent_id]['children'].append(tag)

                # 3. 递归排序子节点
                def sort_children(tag):
                    # 按名称排序子节点
                    tag['children'].sort(key=lambda x: x['tags_name'])
                    # 递归处理子节点的子节点
                    for child in tag['children']:
                        sort_children(child)
                    return tag

                # 4. 对根节点排序并处理子节点
                root_tags.sort(key=lambda x: x['tags_name'])
                return [sort_children(tag) for tag in root_tags]

            # 构建树状结构
            tag_tree = build_tag_tree(tags_list)

            return jsonify({
                "code": 200,
                "msg": "获取树状风格列表成功！",
                "data": {"tag_tree": tag_tree}
            })

        except Exception as e:
            print(f"❌ 获取树状风格列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取风格树失败：{str(e)}"}), 200










    # 原有接口：add_album_tag、get_tags_list、get_tag_detail、get_tags_tree 保持不变

    # ✅ 新增：编辑音乐风格标签接口（仅管理员可访问）
    @app.route('/api/tags/edit', methods=['POST', 'OPTIONS'])
    @login_required
    def edit_album_tag():
        try:
            # 管理员权限校验
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()

            if not user or user.get('is_admin') != 1:
                return jsonify({"code": 403, "msg": "无管理员权限，禁止修改风格！"}), 200

            # 获取请求数据
            data = request.get_json()
            if not data or not data.get('id'):
                return jsonify({"code": 400, "msg": "标签ID不能为空！"}), 200

            # 提取参数
            tag_id = data.get('id')
            tags_name = data.get('tags_name', '').strip()
            aka_name = data.get('aka_name', '').strip()
            parameter_style = data.get('parameter_style', '{}').strip()
            brief_intro = data.get('brief_intro', '').strip()
            detail_intro = data.get('detail_intro', '').strip()
            parent_tag_ids = data.get('parent_tag_ids', '').strip()
            related_singers = data.get('related_singers', '[]').strip()
            related_albums = data.get('related_albums', '[]').strip()
            related_tags = data.get('related_tags', '[]').strip()

            # 必输项校验
            if not tags_name:
                return jsonify({"code": 400, "msg": "风格名称不能为空！"}), 200

            # 检查标签是否存在
            cursor.execute('SELECT id FROM album_tags WHERE id = %s AND is_enabled=1', (tag_id,))
            existing_tag = cursor.fetchone()
            if not existing_tag:
                return jsonify({"code": 404, "msg": "标签不存在或已被删除！"}), 200

            # 检查标签名是否重复（排除自身）
            cursor.execute('''
                SELECT id FROM album_tags WHERE tags_name = %s AND id != %s AND is_enabled=1
            ''', (tags_name, tag_id))
            duplicate_tag = cursor.fetchone()
            if duplicate_tag:
                return jsonify({"code": 400, "msg": f"风格名称「{tags_name}」已存在！"}), 200

            # 执行更新
            cursor.execute('''
                UPDATE album_tags 
                SET 
                    tags_name = %s, 
                    aka_name = %s, 
                    parameter_style = %s, 
                    brief_intro = %s, 
                    detail_intro = %s, 
                    parent_tag_ids = %s,
                    related_singers = %s,
                    related_albums = %s,
                    related_tags = %s,
                    update_time = NOW()
                WHERE id = %s AND is_enabled=1
            ''', (
                tags_name, aka_name, parameter_style, brief_intro, detail_intro,
                parent_tag_ids, related_singers, related_albums, related_tags, tag_id
            ))
            db.commit()

            return jsonify({
                "code": 200,
                "msg": "音乐风格修改成功！",
                "data": {"tag_id": tag_id}
            })

        except Exception as e:
            if 'db' in locals() and not db._closed:
                db.rollback()
            print(f"❌ 修改音乐风格出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"修改风格失败：{str(e)}"}), 200

    @app.route('/api/tags/album/stats', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_album_stats():
        try:
            # 获取参数：完整标签名
            tag_name = request.args.get('tagName', '').strip()
            if not tag_name:
                return jsonify({"code": 400, "msg": "标签名称不能为空！"}), 200

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # ======================
            # 第一步：统计符合条件的专辑ID（单专辑占比>10%）
            # ======================
            # ✅ 方式1：用字符串拼接+参数绑定，彻底避免占位符问题
            sql_album_stats = """
                WITH album_tag_stats AS (
                    SELECT 
                        ur.album_pool_id,
                        SUM(CASE WHEN JSON_CONTAINS(ur.tags, JSON_QUOTE(%s), '$') THEN 1 ELSE 0 END) AS target_tag_count,
                        SUM(JSON_LENGTH(ur.tags)) AS total_tag_count
                    FROM user_album_relation ur
                    WHERE ur.tags IS NOT NULL AND JSON_LENGTH(ur.tags) > 0
                    GROUP BY ur.album_pool_id
                )
                SELECT 
                    album_pool_id,
                    target_tag_count,
                    total_tag_count,
                    ROUND((target_tag_count / total_tag_count) * 100, 2) AS tag_ratio
                FROM album_tag_stats
                WHERE total_tag_count > 0 
                  AND (target_tag_count / total_tag_count) > 0.1
            """
            # 执行：只传1个参数，严格匹配1个%s
            cursor.execute(sql_album_stats, (tag_name,))
            album_stats = cursor.fetchall()
            print(f"🔍 统计标签：{tag_name}")
            print(f"🔍 专辑统计结果：{album_stats}")

            if not album_stats:
                return jsonify({
                    "code": 200,
                    "msg": "暂无该风格占比>10%的专辑",
                    "data": {"album_ids": [], "year_stats": []}
                })

            # 提取专辑ID列表
            album_ids = [str(item['album_pool_id']) for item in album_stats]  # 转字符串避免类型问题
            print(f"🔍 符合条件的专辑ID：{album_ids}")

            # ======================
            # 第二步：统计年份（改用IN+字符串拼接，避免占位符数量问题）
            # ======================
            year_stats = []
            if album_ids:
                # ✅ 方式2：直接拼接ID列表（安全，因为ID是数字）
                album_ids_str = ','.join(album_ids)
                sql_year_stats = f"""
                    SELECT 
                        release_year,
                        COUNT(id) AS album_count
                    FROM album_pool 
                    WHERE id IN ({album_ids_str})
                    GROUP BY release_year
                    ORDER BY release_year ASC
                """
                # 执行：无参数，彻底避免占位符问题
                cursor.execute(sql_year_stats)
                year_stats = cursor.fetchall()

            # 返回结果
            return jsonify({
                "code": 200,
                "msg": "获取风格专辑统计数据成功",
                "data": {
                    "album_ids": album_ids,
                    "year_stats": year_stats,
                    "album_detail_stats": album_stats
                }
            })

        except Exception as e:
            print(f"❌ 获取风格专辑统计出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取统计数据失败：{str(e)}"}), 200

    # ✅ 新增接口：获取符合条件的专辑ID+发布年份
    @app.route('/api/tags/album/year-stats', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_album_year_stats():
        try:
            # 获取参数：完整标签名
            tag_name = request.args.get('tagName', '').strip()
            if not tag_name:
                return jsonify({"code": 400, "msg": "标签名称不能为空！"}), 200

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # Step 1：先筛选出占比>10%的album_pool_id
            cursor.execute('''
                WITH album_tag_stats AS (
                    SELECT 
                        ur.album_pool_id,
                        SUM(CASE WHEN JSON_CONTAINS(ur.tags, JSON_QUOTE(%s), '$') THEN 1 ELSE 0 END) AS target_tag_count,
                        SUM(JSON_LENGTH(ur.tags)) AS total_tag_count
                    FROM user_album_relation ur
                    WHERE ur.tags IS NOT NULL AND JSON_LENGTH(ur.tags) > 0
                    GROUP BY ur.album_pool_id
                )
                SELECT album_pool_id 
                FROM album_tag_stats
                WHERE total_tag_count > 0 
                  AND (target_tag_count / total_tag_count) > 0.1
            ''', (tag_name,))

            album_ids = [item['album_pool_id'] for item in cursor.fetchall()]


            if not album_ids:
                return jsonify({
                    "code": 200,
                    "msg": "暂无该风格占比>10%的专辑",
                    "data": {"album_year_list": []}
                })

            # Step 2：查询这些ID对应的release_year（直接从album_pool表）
            placeholders = ','.join(['%s'] * len(album_ids))
            cursor.execute(f'''
                SELECT id, release_year 
                FROM album_pool 
                WHERE id IN ({placeholders})
            ''', album_ids)

            # 组装ID+年份数据
            album_year_list = cursor.fetchall()
            return jsonify({
                "code": 200,
                "msg": "获取专辑年份数据成功",
                "data": {
                    "album_year_list": album_year_list  # 格式：[{"id":1, "release_year":2020}, ...]
                }
            })

        except Exception as e:
            print(f"❌ 获取专辑年份统计出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取失败：{str(e)}"}), 200

    @app.route('/api/tags/album/list', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_album_list():
        try:
            # 获取参数
            tag_name = request.args.get('tagName', '').strip()
            release_year = request.args.get('year', '').strip()
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
            sort_field = request.args.get('sort_field', 'create_time')
            sort_order = request.args.get('sort_order', 'desc')
            keyword = request.args.get('keyword', '').strip()
            # ✅ 新增：听状态筛选参数
            listen_status = request.args.get('listenStatus', 'all').strip()

            if not tag_name:
                return jsonify({"code": 400, "msg": "标签名称不能为空！"}), 200

            # 校验排序字段
            valid_sort_fields = ['album_name', 'release_year', 'singer', 'create_time']
            if sort_field not in valid_sort_fields:
                sort_field = 'create_time'

            # 校验排序方向
            if sort_order not in ['asc', 'desc']:
                sort_order = 'desc'

            # ✅ 校验听状态参数
            valid_listen_status = ['all', 'listened', 'unlistened']
            if listen_status not in valid_listen_status:
                listen_status = 'all'

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            current_user_id = get_current_user_id()

            # ======================
            # Step 1：先获取该标签占比>10%的专辑ID
            # ======================
            cursor.execute('''
                WITH album_tag_stats AS (
                    SELECT 
                        ur.album_pool_id,
                        SUM(CASE WHEN JSON_CONTAINS(ur.tags, JSON_QUOTE(%s), '$') THEN 1 ELSE 0 END) AS target_tag_count,
                        SUM(JSON_LENGTH(ur.tags)) AS total_tag_count
                    FROM user_album_relation ur
                    WHERE ur.tags IS NOT NULL AND JSON_LENGTH(ur.tags) > 0
                    GROUP BY ur.album_pool_id
                )
                SELECT album_pool_id 
                FROM album_tag_stats
                WHERE total_tag_count > 0 
                  AND (target_tag_count / total_tag_count) > 0.1
            ''', (tag_name,))

            album_ids = [item['album_pool_id'] for item in cursor.fetchall()]
            if not album_ids:
                return jsonify({
                    "code": 200,
                    "msg": "暂无该风格的专辑数据",
                    "data": {
                        "list": [],
                        "pagination": {
                            "total": 0,
                            "page": page,
                            "page_size": page_size,
                            "total_pages": 0
                        }
                    }
                })

            # ======================
            # Step 2：获取用户已听的专辑source_pool_id列表
            # ======================
            user_listened_source_ids = []
            if current_user_id and listen_status != 'all':
                # 获取用户专辑表名
                user_album_table = get_album_table_name(current_user_id)
                # 查询用户所有专辑的source_pool_id（代表已听）
                cursor.execute(f'''
                    SELECT source_pool_id 
                    FROM `{user_album_table}` 
                    WHERE source_pool_id IS NOT NULL 
                    AND source_pool_id != 0
                ''')
                user_listened_source_ids = [item['source_pool_id'] for item in cursor.fetchall()]

            # ======================
            # Step 3：构建筛选条件（修复：添加表别名ap）
            # ======================
            query_params = []
            # 修复1：添加表别名ap，避免字段冲突
            where_conditions = ["ap.id IN ({})".format(','.join(['%s'] * len(album_ids)))]
            query_params.extend(album_ids)

            # 年份筛选
            if release_year and release_year.isdigit():
                where_conditions.append("ap.release_year = %s")
                query_params.append(int(release_year))

            # 专辑名/歌手搜索
            if keyword:
                where_conditions.append("(ap.album_name LIKE %s OR ap.singer LIKE %s)")
                query_params.extend([f'%{keyword}%', f'%{keyword}%'])

            # ✅ 新增：听状态筛选
            if listen_status == 'listened':
                # 只显示用户已听的专辑
                if user_listened_source_ids:
                    source_placeholders = ','.join(['%s'] * len(user_listened_source_ids))
                    where_conditions.append(f"ap.id IN ({source_placeholders})")
                    query_params.extend(user_listened_source_ids)
                else:
                    # 无已听专辑，直接返回空
                    return jsonify({
                        "code": 200,
                        "msg": "暂无已听的该风格专辑",
                        "data": {
                            "list": [],
                            "pagination": {
                                "total": 0,
                                "page": page,
                                "page_size": page_size,
                                "total_pages": 0
                            }
                        }
                    })
            elif listen_status == 'unlistened':
                # 只显示用户未听的专辑
                if user_listened_source_ids:
                    source_placeholders = ','.join(['%s'] * len(user_listened_source_ids))
                    where_conditions.append(f"ap.id NOT IN ({source_placeholders})")
                    query_params.extend(user_listened_source_ids)

            # ======================
            # Step 4：查询总数（修复：关联users表+添加表别名）
            # ======================
            count_sql = f'''
                SELECT COUNT(*) as total 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                WHERE {" AND ".join(where_conditions)}
            '''
            cursor.execute(count_sql, query_params)
            total = cursor.fetchone()['total']
            total_pages = (total + page_size - 1) // page_size

            # ======================
            # Step 5：分页查询专辑列表（修复：关联users表+添加表别名）
            # ======================
            offset = (page - 1) * page_size
            # 修复2：关联users表获取创建用户名称，添加表别名ap
            list_sql = f'''
                SELECT ap.*, u.username as create_user_name 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                WHERE {" AND ".join(where_conditions)}
                ORDER BY ap.{sort_field} {sort_order}
                LIMIT %s OFFSET %s
            '''
            # 修复3：先复制筛选参数，避免分页参数污染原参数列表
            list_query_params = query_params.copy()
            list_query_params.extend([page_size, offset])
            cursor.execute(list_sql, list_query_params)
            album_list = cursor.fetchall()

            # ======================
            # Step 6：格式化数据（添加创建用户和标签信息）
            # ======================
            result_list = []
            for album in album_list:
                # 添加听状态标识
                album['is_listened'] = album['id'] in user_listened_source_ids

                # 解析JSON字段（和搜索接口保持一致）
                main_type = safe_json_loads(album.get('main_type')) or []
                tags = safe_json_loads(album.get('tags')) or []
                tracks = safe_json_loads(album.get('tracks')) or []

                # 获取标签统计信息
                album_tag_stats = get_album_tag_stats(album['id'], cursor) if 'get_album_tag_stats' in globals() else []

                # 格式化创建时间
                create_time_str = album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album.get('create_time') else ''

                # 组装返回数据（和搜索接口字段一致）
                result_item = {
                    "id": album['id'],
                    "album_name": album['album_name'],
                    "cover_img": album['cover_img'],
                    "singer": album['singer'],
                    "release_year": album['release_year'],
                    "main_type": main_type,
                    "tags": tags,
                    "tracks": tracks,
                    "album_intro": album.get('album_intro', '') or '',
                    "duration_type": album.get('duration_type', 'LP') or 'LP',
                    "my_score": album['my_score'],
                    "create_user": album['create_user'],
                    "create_user_name": album.get('create_user_name') or "未知用户",
                    "create_time": create_time_str,
                    "tag_statistics": album_tag_stats,
                    "is_listened": album['is_listened']
                }
                result_list.append(result_item)

            # 构造返回数据
            return jsonify({
                "code": 200,
                "msg": "获取专辑列表成功",
                "data": {
                    "list": result_list,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": total_pages
                    }
                }
            })

        except Exception as e:
            print(f"❌ 获取标签专辑列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取专辑列表失败：{str(e)}"}), 200

    # ✅ 最终版：包含当前标签的统计逻辑
    @app.route('/api/tags/album/tag-stats', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_album_tag_stats():
        try:
            # 1. 获取前端传递的参数
            tag_name = request.args.get('tagName', '').strip()
            album_ids_str = request.args.get('albumIds', '').strip()

            # 参数校验
            if not tag_name:
                return jsonify({"code": 400, "msg": "标签名称不能为空！"}), 200
            if not album_ids_str:
                return jsonify({
                    "code": 200,
                    "msg": "暂无专辑数据",
                    "data": {"tagStats": []}
                })

            # 2. 解析专辑ID列表
            try:
                album_ids = [int(id_str.strip()) for id_str in album_ids_str.split(',') if id_str.strip().isdigit()]
            except:
                return jsonify({
                    "code": 200,
                    "msg": "专辑ID格式错误",
                    "data": {"tagStats": []}
                })

            if not album_ids:
                return jsonify({
                    "code": 200,
                    "msg": "暂无有效专辑ID",
                    "data": {"tagStats": []}
                })

            # 3. 核心逻辑：统计这些专辑ID的所有标签（包含当前标签）
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 构建IN查询的占位符
            placeholders = ','.join(['%s'] * len(album_ids))

            # 查询这些专辑的所有标签
            cursor.execute(f'''
                SELECT tags 
                FROM user_album_relation 
                WHERE album_pool_id IN ({placeholders}) 
                AND tags IS NOT NULL 
                AND JSON_VALID(tags)
            ''', album_ids)

            tag_records = cursor.fetchall()

            # 4. 统计标签出现次数（🔥 关键修改：不移除当前标签）
            tag_count = {}
            for record in tag_records:
                try:
                    tags = json.loads(record['tags'])
                    if isinstance(tags, list):
                        for tag in tags:
                            if tag and tag.strip():
                                tag = tag.strip()
                                # 移除排除当前标签的判断，保留所有标签
                                tag_count[tag] = tag_count.get(tag, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    continue

            # 5. 整理结果并返回
            tag_stats = [
                {"tag": tag, "count": count}
                for tag, count in tag_count.items()
            ]
            # 按出现次数降序排序，最多返回20个

            tag_stats = sorted(tag_stats, key=lambda x: x['count'], reverse=True)[:20]


            return jsonify({
                "code": 200,
                "msg": "获取标签统计数据成功",
                "data": {"tagStats": tag_stats}
            })

        except Exception as e:
            print(f"❌ 获取标签统计数据出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取标签统计数据失败：{str(e)}"}), 200

    # ✅ 新增：根据父标签ID列表获取父标签详情
    @app.route('/api/tags/parent-tags', methods=['GET', 'OPTIONS'])
    @login_required
    def get_parent_tags():
        try:
            # 获取前端传递的父标签ID列表（格式：1,2,3）
            parent_ids_str = request.args.get('ids', '').strip()
            if not parent_ids_str:
                return jsonify({
                    "code": 200,
                    "msg": "父标签ID列表为空",
                    "data": []
                })

            # 解析ID列表
            try:
                parent_ids = [int(id_str.strip()) for id_str in parent_ids_str.split(',') if id_str.strip().isdigit()]
            except:
                return jsonify({
                    "code": 400,
                    "msg": "父标签ID格式错误"
                })

            if not parent_ids:
                return jsonify({
                    "code": 200,
                    "msg": "无有效父标签ID",
                    "data": []
                })

            # 查询父标签详情
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            placeholders = ','.join(['%s'] * len(parent_ids))
            cursor.execute(f'''
                SELECT id, tags_name, aka_name, brief_intro 
                FROM album_tags 
                WHERE id IN ({placeholders}) AND is_enabled=1
            ''', parent_ids)
            parent_tags = cursor.fetchall()

            return jsonify({
                "code": 200,
                "msg": "获取父标签成功",
                "data": parent_tags
            })

        except Exception as e:
            print(f"❌ 获取父标签出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "code": 500,
                "msg": f"获取父标签失败：{str(e)}"
            })

    # ✅ 新增：获取标签下所有符合条件的专辑ID（不分页）
    @app.route('/api/tags/album/all-ids', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tag_album_all_ids():
        try:
            # 获取参数（和list接口保持一致）
            tag_name = request.args.get('tagName', '').strip()
            release_year = request.args.get('year', '').strip()
            keyword = request.args.get('keyword', '').strip()
            listen_status = request.args.get('listenStatus', 'all').strip()

            if not tag_name:
                return jsonify({"code": 400, "msg": "标签名称不能为空！"}), 200

            # 校验听状态参数
            valid_listen_status = ['all', 'listened', 'unlistened']
            if listen_status not in valid_listen_status:
                listen_status = 'all'

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            current_user_id = get_current_user_id()

            # ======================
            # Step 1：先获取该标签占比>10%的专辑ID
            # ======================
            cursor.execute('''
                WITH album_tag_stats AS (
                    SELECT 
                        ur.album_pool_id,
                        SUM(CASE WHEN JSON_CONTAINS(ur.tags, JSON_QUOTE(%s), '$') THEN 1 ELSE 0 END) AS target_tag_count,
                        SUM(JSON_LENGTH(ur.tags)) AS total_tag_count
                    FROM user_album_relation ur
                    WHERE ur.tags IS NOT NULL AND JSON_LENGTH(ur.tags) > 0
                    GROUP BY ur.album_pool_id
                )
                SELECT album_pool_id 
                FROM album_tag_stats
                WHERE total_tag_count > 0 
                  AND (target_tag_count / total_tag_count) > 0.1
            ''', (tag_name,))

            album_ids = [item['album_pool_id'] for item in cursor.fetchall()]
            if not album_ids:
                return jsonify({
                    "code": 200,
                    "msg": "暂无该风格的专辑数据",
                    "data": {"albumIds": []}
                })

            # ======================
            # Step 2：获取用户已听的专辑source_pool_id列表
            # ======================
            user_listened_source_ids = []
            if current_user_id and listen_status != 'all':
                # 获取用户专辑表名
                user_album_table = get_album_table_name(current_user_id)
                # 查询用户所有专辑的source_pool_id（代表已听）
                cursor.execute(f'''
                    SELECT source_pool_id 
                    FROM `{user_album_table}` 
                    WHERE source_pool_id IS NOT NULL 
                    AND source_pool_id != 0
                ''')
                user_listened_source_ids = [item['source_pool_id'] for item in cursor.fetchall()]

            # ======================
            # Step 3：构建筛选条件（和list接口一致）
            # ======================
            query_params = []
            where_conditions = ["id IN ({})".format(','.join(['%s'] * len(album_ids)))]
            query_params.extend(album_ids)

            # 年份筛选
            if release_year and release_year.isdigit():
                where_conditions.append("release_year = %s")
                query_params.append(int(release_year))

            # 专辑名/歌手搜索
            if keyword:
                where_conditions.append("(album_name LIKE %s OR singer LIKE %s)")
                query_params.extend([f'%{keyword}%', f'%{keyword}%'])

            # 听状态筛选
            if listen_status == 'listened':
                # 只显示用户已听的专辑
                if user_listened_source_ids:
                    source_placeholders = ','.join(['%s'] * len(user_listened_source_ids))
                    where_conditions.append(f"id IN ({source_placeholders})")
                    query_params.extend(user_listened_source_ids)
                else:
                    # 无已听专辑，直接返回空
                    return jsonify({
                        "code": 200,
                        "msg": "暂无已听的该风格专辑",
                        "data": {"albumIds": []}
                    })
            elif listen_status == 'unlistened':
                # 只显示用户未听的专辑
                if user_listened_source_ids:
                    source_placeholders = ','.join(['%s'] * len(user_listened_source_ids))
                    where_conditions.append(f"id NOT IN ({source_placeholders})")
                    query_params.extend(user_listened_source_ids)

            # ======================
            # Step 4：查询所有符合条件的专辑ID
            # ======================
            list_sql = f'''
                SELECT id 
                FROM album_pool 
                WHERE {" AND ".join(where_conditions)}
            '''
            cursor.execute(list_sql, query_params)
            all_album_records = cursor.fetchall()

            # 提取ID列表
            all_album_ids = [str(item['id']) for item in all_album_records]

            # 构造返回数据
            return jsonify({
                "code": 200,
                "msg": "获取全量专辑ID成功",
                "data": {
                    "albumIds": all_album_ids
                }
            })

        except Exception as e:
            print(f"❌ 获取全量专辑ID出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取全量专辑ID失败：{str(e)}"}), 200