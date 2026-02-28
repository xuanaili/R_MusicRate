from flask import request, jsonify
import traceback
from backend.utils.db import get_db, get_current_user_id
from backend.utils.decorators import login_required
import pymysql
from datetime import datetime, timedelta


def register_share_routes(app):
    """注册专辑专题相关路由"""

    # 1. 获取按周聚合的专辑专题列表接口（仅修复参数不匹配错误，保留原有逻辑）
    @app.route('/api/album/share/weekly-list', methods=['GET', 'OPTIONS'])
    @login_required
    def get_weekly_share_list():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            cursor.execute('''
                SELECT 
                    s.id,  # 直接取 album_share 表的主键 id
                    s.album_pool_id,
                    s.share_text,
                    s.create_time,
                    s.create_user_id,
                    p.album_name,
                    p.cover_img,
                    p.singer,
                    p.album_intro,
                    DATE_FORMAT(DATE_SUB(s.create_time, INTERVAL WEEKDAY(s.create_time) DAY), '%Y-%m-%d') as week_start,
                    DATE_FORMAT(DATE_ADD(s.create_time, INTERVAL (6 - WEEKDAY(s.create_time)) DAY), '%Y-%m-%d') as week_end,
                    WEEK(s.create_time, 1) as week_num,
                    YEAR(s.create_time) as year_num
                FROM album_share s
                LEFT JOIN album_pool p ON s.album_pool_id = p.id
                WHERE 1=1
                ORDER BY s.create_time DESC
            ''')

            share_records = cursor.fetchall()
            cursor.close()

            weekly_groups = {}
            for record in share_records:
                week_key = f"{record['year_num']}-{record['week_num']}"
                date_range = f"{record['week_start']} - {record['week_end']}"

                # 关键修改：shareId 对应 album_share 表的 id 字段
                album_info = {
                    "shareId": record['id'],  # 直接用 s.id 而非 share_id
                    "id": record['album_pool_id'],
                    "cover": record['cover_img'] or "",
                    "name": record['album_name'] or "未知专辑",
                    "singer": record['singer'] or "未知歌手",
                    "desc": record['album_intro'] or "暂无简介"
                }

                if week_key not in weekly_groups:
                    weekly_groups[week_key] = {
                        "dateRange": date_range,
                        "title": record['share_text'] or f"{record['week_start']} - {record['week_end']} 专题",
                        "albums": []
                    }

                weekly_groups[week_key]['albums'].append(album_info)

            week_list = sorted(weekly_groups.values(),
                               key=lambda x: x['dateRange'].split(' - ')[0],
                               reverse=True)

            return jsonify({
                "code": 200,
                "msg": "获取每周专辑专题列表成功！",
                "data": {"weekList": week_list}
            })

        except Exception as e:
            print(f"❌ 获取每周专辑专题出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取专题列表失败：{str(e)}"}), 200

    # 2. 获取单周详情（原有逻辑完全保留）
    @app.route('/api/album/share/week-detail', methods=['GET', 'OPTIONS'])
    @login_required
    def get_week_detail():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            week_start = request.args.get('weekStart')
            if not week_start:
                return jsonify({"code": 400, "msg": "缺少周起始日期参数！"}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            cursor.execute('''
                SELECT 
                    s.id,  # 直接取 album_share 表的主键 id
                    s.album_pool_id,
                    s.share_text,
                    s.create_time,
                    p.album_name,
                    p.cover_img,
                    p.singer,
                    p.album_intro
                FROM album_share s
                LEFT JOIN album_pool p ON s.album_pool_id = p.id
                WHERE DATE_FORMAT(DATE_SUB(s.create_time, INTERVAL WEEKDAY(s.create_time) DAY), '%%Y-%%m-%%d') = %s
                ORDER BY s.create_time DESC
            ''', (week_start,))

            share_records = cursor.fetchall()
            cursor.close()

            albums = []
            week_title = f"{week_start} - {(datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')} 专题"
            if share_records:
                week_title = share_records[0]['share_text'] or week_title

            for record in share_records:
                albums.append({
                    "shareId": record['id'],  # 直接用 s.id
                    "id": record['album_pool_id'],
                    "cover": record['cover_img'] or "",
                    "name": record['album_name'] or "未知专辑",
                    "singer": record['singer'] or "未知歌手",
                    "desc": record['album_intro'] or "暂无简介"
                })

            week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
            week_detail = {
                "dateRange": f"{week_start} - {week_end}",
                "title": week_title,
                "albums": albums
            }

            return jsonify({
                "code": 200,
                "msg": "获取单周专题详情成功！",
                "data": week_detail
            })

        except Exception as e:
            print(f"❌ 获取单周专题详情出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取单周详情失败：{str(e)}"}), 200

    # 3. 创建/添加专辑专题（支持自定义创建时间，原有逻辑完全保留）
    @app.route('/api/album/share/create', methods=['POST', 'OPTIONS'])
    @login_required
    def create_album_share():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            data = request.get_json()
            album_pool_id = data.get('albumPoolId')
            share_text = data.get('shareText', '')
            create_time = data.get('createTime')

            # 参数校验
            if not album_pool_id:
                return jsonify({"code": 400, "msg": "缺少专辑ID参数！"}), 200
            if not share_text:
                return jsonify({"code": 400, "msg": "专题描述不能为空！"}), 200
            if not create_time:
                return jsonify({"code": 400, "msg": "请选择创建/添加时间！"}), 200

            # 格式化时间（兼容datetime-local格式）
            try:
                # 转换前端传的 "YYYY-MM-DDTHH:MM" 为 "YYYY-MM-DD HH:MM:SS"
                formatted_create_time = create_time.replace('T', ' ') + ':00'
                # 验证时间格式
                datetime.strptime(formatted_create_time, '%Y-%m-%d %H:%M:%S')
            except:
                return jsonify({"code": 400, "msg": "时间格式错误！"}), 200

            db = get_db()
            cursor = db.cursor()

            # 插入新专题（使用自定义创建时间）
            cursor.execute('''
                INSERT INTO album_share (album_pool_id, share_text, create_user_id, create_time)
                VALUES (%s, %s, %s, %s)
            ''', (album_pool_id, share_text, current_user_id, formatted_create_time))

            share_id = cursor.lastrowid
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "创建专辑专题成功！",
                "data": {"shareId": share_id}
            })

        except Exception as e:
            print(f"❌ 创建专辑专题出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"创建专题失败：{str(e)}"}), 200

    # 4. 更新专题标题（原有逻辑完全保留）
    @app.route('/api/album/share/update-title', methods=['POST', 'OPTIONS'])
    @login_required
    def update_share_title():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            data = request.get_json()
            week_start = data.get('weekStart')
            new_title = data.get('newTitle')

            if not week_start or not new_title:
                return jsonify({"code": 400, "msg": "缺少周起始日期或新标题参数！"}), 200

            db = get_db()
            cursor = db.cursor()

            # 更新该周第一条记录的share_text作为专题标题
            cursor.execute('''
                UPDATE album_share s
                SET s.share_text = %s
                WHERE DATE_FORMAT(DATE_SUB(s.create_time, INTERVAL WEEKDAY(s.create_time) DAY), '%%Y-%%m-%%d') = %s
                ORDER BY s.create_time ASC
                LIMIT 1
            ''', (new_title, week_start))

            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "更新专题标题成功！"
            })

        except Exception as e:
            print(f"❌ 更新专题标题出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"更新专题标题失败：{str(e)}"}), 200

    # 5. 获取可选择的专辑列表（保留10年限制，原有逻辑完全不变）
    @app.route('/api/album/pool/available-list', methods=['GET', 'OPTIONS'])
    @login_required
    def get_available_album_list():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 计算10年前的日期（保留原有逻辑）
            ten_years_ago = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d %H:%M:%S')

            # 查询符合条件的专辑（保留10年限制）
            cursor.execute('''
                SELECT DISTINCT p.* 
                FROM album_pool p
                LEFT JOIN album_share s ON p.id = s.album_pool_id
                WHERE 
                    -- 条件1：未被加入过专题
                    s.album_pool_id IS NULL 
                    OR 
                    -- 条件2：已加入但超过10年
                    (s.album_pool_id IS NOT NULL AND s.create_time < %s)
                ORDER BY p.album_name ASC
            ''', (ten_years_ago,))

            album_list = cursor.fetchall()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "获取可选择专辑列表成功！",
                "data": album_list
            })

        except Exception as e:
            print(f"❌ 获取可选择专辑列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取专辑列表失败：{str(e)}"}), 200

    # 6. 删除整个专题（根据周起始日期删除该周所有专辑分享记录）
    @app.route('/api/album/share/delete-week', methods=['POST', 'OPTIONS'])
    @login_required
    def delete_week_share():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            data = request.get_json()
            week_start = data.get('weekStart')

            if not week_start:
                return jsonify({"code": 400, "msg": "缺少周起始日期参数！"}), 200

            db = get_db()
            cursor = db.cursor()

            # 删除该周所有专辑分享记录
            cursor.execute('''
                DELETE FROM album_share 
                WHERE DATE_FORMAT(DATE_SUB(create_time, INTERVAL WEEKDAY(create_time) DAY), '%%Y-%%m-%%d') = %s
            ''', (week_start,))

            affected_rows = cursor.rowcount
            db.commit()
            cursor.close()

            if affected_rows > 0:
                return jsonify({
                    "code": 200,
                    "msg": "删除专题成功！"
                })
            else:
                return jsonify({
                    "code": 404,
                    "msg": "未找到该专题数据！"
                })

        except Exception as e:
            print(f"❌ 删除专题出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除专题失败：{str(e)}"}), 200

    # 7. 删除专题中的单张专辑（根据share_id删除）
    @app.route('/api/album/share/delete-album', methods=['POST', 'OPTIONS'])
    @login_required
    def delete_album_from_share():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            data = request.get_json()
            share_id = data.get('shareId')  # 前端传的 shareId 就是 album_share.id

            if not share_id:
                return jsonify({"code": 400, "msg": "缺少分享记录ID参数！"}), 200

            db = get_db()
            cursor = db.cursor()

            # 删除指定的专辑分享记录（用 album_share.id 删除）
            cursor.execute('''
                DELETE FROM album_share 
                WHERE id = %s
            ''', (share_id,))

            affected_rows = cursor.rowcount
            db.commit()
            cursor.close()

            if affected_rows > 0:
                return jsonify({
                    "code": 200,
                    "msg": "删除专辑成功！"
                })
            else:
                return jsonify({
                    "code": 404,
                    "msg": "未找到该专辑分享记录！"
                })

        except Exception as e:
            print(f"❌ 删除专辑出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 200