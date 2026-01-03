from flask import request, jsonify, g
import json
import traceback
import random
from datetime import datetime, date
from ..db_utils import get_db, get_current_user_id
from ..decorators import login_required
import pymysql.cursors


# ========== 复用你原有代码的安全JSON解析函数 ==========
def safe_json_loads(s):
    if s is None or s == "":
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def register_recommend_routes(app):
    """注册用户每日推荐相关路由"""

    # ========== ✅ 核心接口：获取用户今日推荐专辑 (修复空表写入+完整逻辑闭环) ==========
    @app.route('/api/recommend/today', methods=['GET', 'OPTIONS'])
    @login_required
    def get_today_recommend():
        # 处理跨域预检请求
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200

        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录或登录过期", "data": None}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)
            today = date.today()
            need_refresh = False
            random_album_id = None

            # 1. 【第一步：优先查询用户是否已有今日推荐数据】核心修复点
            cursor.execute('''
                SELECT recommend_daily_id FROM user_recommend WHERE user_id = %s
            ''', (current_user_id,))
            recommend_res = cursor.fetchone()

            # ✅ 核心修复：用户无推荐数据 → 直接标记需要刷新写入
            if not recommend_res:
                need_refresh = True
            else:
                # 有数据的情况，再判断是否跨天需要更新
                cursor.execute('SELECT last_login FROM users WHERE user_id = %s', (current_user_id,))
                user_info = cursor.fetchone()
                last_login_time = user_info.get('last_login') if user_info else None

                # 判断是否需要刷新今日推荐：无登录时间 / 最后登录不是今天 → 需要刷新
                if not last_login_time:
                    need_refresh = True
                else:
                    # 提取最后登录的日期 和 当前日期对比
                    last_login_date = last_login_time.date() if isinstance(last_login_time, datetime) else today
                    if last_login_date < today:
                        need_refresh = True

            # 2. 刷新逻辑：随机获取album_pool的专辑ID，【新增/更新】用户推荐数据
            if need_refresh:
                # 从专辑池随机获取1个有效的专辑ID
                cursor.execute('SELECT id FROM album_pool WHERE id > 0 ORDER BY RAND() LIMIT 1')
                random_album = cursor.fetchone()
                if not random_album:
                    cursor.close()
                    return jsonify({"code": 200, "msg": "暂无推荐专辑", "data": None}), 200

                random_album_id = random_album['id']

                # ✅ 核心SQL：存在即更新，不存在即新增 (一个用户永远只有一条数据，空表会自动写入user_id+专辑id)
                cursor.execute('''
                    INSERT INTO user_recommend (user_id, recommend_daily_id, update_time)
                    VALUES (%s, %s, NOW())
                    ON DUPLICATE KEY UPDATE recommend_daily_id = %s, update_time = NOW()
                ''', (current_user_id, random_album_id, random_album_id))

                # 同步更新用户的最后登录时间为当前时间
                cursor.execute('UPDATE users SET last_login = NOW() WHERE user_id = %s', (current_user_id,))
                db.commit()

            # 3. 二次查询推荐的专辑ID（确保一定能拿到，无论是新增还是原有）
            cursor.execute('''
                SELECT recommend_daily_id FROM user_recommend WHERE user_id = %s
            ''', (current_user_id,))
            final_recommend_res = cursor.fetchone()
            if not final_recommend_res:
                cursor.close()
                return jsonify({"code": 200, "msg": "暂无推荐专辑", "data": None}), 200

            recommend_album_id = final_recommend_res['recommend_daily_id']

            # 4. 查询推荐专辑的完整信息 (和AlbumPoolDetail接口返回结构完全一致)
            cursor.execute('''
                SELECT ap.*, u.username as create_user_name 
                FROM album_pool ap
                LEFT JOIN users u ON ap.create_user = u.user_id
                WHERE ap.id = %s
            ''', (recommend_album_id,))
            album_data = cursor.fetchone()
            cursor.close()

            if not album_data:
                return jsonify({"code": 200, "msg": "推荐专辑已下架", "data": None}), 200

            # 格式化专辑数据，和原有接口一致
            album_data['tags'] = safe_json_loads(album_data.get('tags')) or []
            album_data['main_type'] = safe_json_loads(album_data.get('main_type')) or []
            album_data['tracks'] = safe_json_loads(album_data.get('tracks')) or []
            album_data['tracks_time'] = safe_json_loads(album_data.get('tracks_time')) or []
            album_data['duration_type'] = album_data.get('duration_type', 'LP') or 'LP'
            album_data['album_intro'] = album_data.get('album_intro', '') or ''
            album_data['create_user_name'] = album_data.get('create_user_name') or "未知用户"

            return jsonify({
                "code": 200,
                "msg": "获取今日推荐成功",
                "data": album_data
            })

        except Exception as e:
            print(f"❌ 获取今日推荐失败：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"获取推荐失败：{str(e)}", "data": None}), 200

    # ========== ✅ 关键修改：给这个接口【新增别名路由】，完美匹配前端调用地址 ==========
    # 原路由 /api/recommend/refresh 保留 + 新增 /api/recommend/change-today 双路由兼容
    @app.route('/api/recommend/refresh', methods=['POST', 'OPTIONS'])
    @app.route('/api/recommend/change-today', methods=['POST', 'OPTIONS'])
    @login_required
    def refresh_today_recommend():
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "success"}), 200

        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录或登录过期", "data": None}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 随机获取新专辑ID
            cursor.execute('SELECT id FROM album_pool WHERE id > 0 ORDER BY RAND() LIMIT 1')
            random_album = cursor.fetchone()
            if not random_album:
                cursor.close()
                return jsonify({"code": 200, "msg": "暂无推荐专辑", "data": None}), 200

            random_album_id = random_album['id']

            # 更新推荐数据，空表自动写入
            cursor.execute('''
                INSERT INTO user_recommend (user_id, recommend_daily_id, update_time)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE recommend_daily_id = %s, update_time = NOW()
            ''', (current_user_id, random_album_id, random_album_id))

            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "今日推荐已刷新",
                "data": {"recommend_id": random_album_id}
            })

        except Exception as e:
            print(f"❌ 刷新今日推荐失败：{str(e)}")
            print(traceback.format_exc())
            if 'db' in locals():
                db.rollback()
            if 'cursor' in locals():
                cursor.close()
            return jsonify({"code": 500, "msg": f"刷新推荐失败：{str(e)}", "data": None}), 200