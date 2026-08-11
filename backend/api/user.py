# MusicRate\backend\api\user.py 个人用户中心接口（v0.7 P0）
# 全部 @login_required；账号注销/改头像/改用户名等后续版本补充
import datetime
import traceback

import pymysql
from flask import request, jsonify

from backend.utils.auth import encrypt_password
from backend.utils.db import get_db, get_current_user_id, get_album_table_name
from backend.utils.decorators import login_required
from backend.utils.level import compute_level, level_progress, level_title, xp_to_next_level
from backend.utils.user import validate_password_change, validate_avatar_url
from backend.utils.user_stats import accumulate_daily_logs, aggregate_stats, parse_days_param
from backend.utils.xp import XP_COMMENT, XP_LISTENING, XP_RATING, XP_REVIEW
from backend.utils.xp_detail import accumulate_bonus_daily, build_daily_xp


def register_user_routes(app):
    """注册个人用户中心路由（需传入Flask app实例）"""

    # 1. 获取当前用户信息
    @app.route('/api/user/info', methods=['GET', 'OPTIONS'])
    @login_required
    def user_info():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT user_id, username, create_time, last_login, is_vip, avatar, xp
                FROM users WHERE user_id = %s
            ''', (current_user_id,))
            user = cursor.fetchone()
            if not user:
                cursor.close()
                return jsonify({"code": 401, "msg": "用户不存在！"}), 401

            # 专辑数实时 COUNT（@login_required 已保证 albums_{user_id} 表存在）
            table_name = get_album_table_name(current_user_id)
            cursor.execute(f'SELECT COUNT(*) AS cnt FROM `{table_name}`')
            album_count = cursor.fetchone()['cnt']
            cursor.close()

            # v0.7.1 P0：等级由 xp 纯函数实时推导（level = floor(sqrt(xp/3600))），不依赖遗留 level 列
            xp = float(user.get('xp') or 0)
            level = compute_level(xp)

            return jsonify({
                "code": 200,
                "msg": "ok",
                "data": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "create_time": str(user['create_time']) if user['create_time'] else '',
                    "level": level,
                    "xp": round(xp, 1),
                    "next_level_xp": xp_to_next_level(xp),
                    "xp_progress": level_progress(xp),
                    "level_title": level_title(level),
                    "last_login": str(user['last_login']) if user['last_login'] else '',
                    "is_vip": user['is_vip'],
                    "avatar": user['avatar'] or '',
                    "album_count": album_count
                }
            })
        except Exception as e:
            print(f"❌ 获取用户信息失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "获取用户信息失败，请稍后重试！"}), 500

    # 2. 修改密码（bcrypt 校验旧密码 + 更新新密码）
    @app.route('/api/user/change-password', methods=['POST', 'OPTIONS'])
    @login_required
    def change_password():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            data = request.get_json() or {}
            old_password = (data.get('oldPassword') or '').strip()
            new_password = (data.get('newPassword') or '').strip()

            current_user_id = get_current_user_id()
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT password FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            if not user:
                cursor.close()
                return jsonify({"code": 401, "msg": "用户不存在！"}), 401

            # 纯逻辑校验（复用可单测函数）
            error = validate_password_change(old_password, new_password, user['password'])
            if error:
                cursor.close()
                return jsonify({"code": 400, "msg": error}), 400

            new_hashed = encrypt_password(new_password)
            cursor.execute('UPDATE users SET password = %s WHERE user_id = %s', (new_hashed, current_user_id))
            db.commit()
            cursor.close()
            return jsonify({"code": 200, "msg": "密码修改成功！"})
        except Exception as e:
            print(f"❌ 修改密码失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "修改密码失败，请稍后重试！"}), 500

    # 3. 更新头像（图片上传复用 /api/upload_img，本接口只存 URL）
    @app.route('/api/user/avatar', methods=['POST', 'OPTIONS'])
    @login_required
    def update_avatar():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            data = request.get_json() or {}
            avatar_url = (data.get('avatarUrl') or '').strip()

            # 纯逻辑校验（复用可单测函数）
            error = validate_avatar_url(avatar_url)
            if error:
                return jsonify({"code": 400, "msg": error}), 400

            current_user_id = get_current_user_id()
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('UPDATE users SET avatar = %s WHERE user_id = %s', (avatar_url, current_user_id))
            db.commit()
            cursor.close()
            return jsonify({"code": 200, "msg": "头像更新成功！", "data": {"avatar": avatar_url}})
        except Exception as e:
            print(f"❌ 更新头像失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "更新头像失败，请稍后重试！"}), 500

    # 4. 音乐统计（v0.7 P2 + v0.7.1 P1）：统计口径纯函数见 backend/utils/user_stats.py
    #    v0.7.1 P1 口径统一：总时长改读 users.listening_total（删专辑不掉，不再 SUM albums.listening_duration）；
    #    活跃度（连续收听/近30天活跃）由近 30 天 user_listening_log 计算，柱状图窗口由 aggregate_stats 按 days 内部截取
    @app.route('/api/user/stats', methods=['GET', 'OPTIONS'])
    @login_required
    def user_stats():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            days = parse_days_param(request.args.get('days'), default=7)

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            table_name = get_album_table_name(current_user_id)

            # 1. 专辑全量行（专辑总数/已评分/听后感/标签分布/评分分布的数据源）
            cursor.execute(f'''
                SELECT my_score, review, listening_duration, score, tags
                FROM `{table_name}`
            ''')
            album_rows = cursor.fetchall()

            # 2. 近 30 天按天记录（活跃度 current_streak / active_days_30 需要完整 30 天窗口；
            #    柱状图数据源由 aggregate_stats 内部按所选 days 窗口截取，窗口外行会被忽略）
            start_date = datetime.date.today() - datetime.timedelta(days=29)
            cursor.execute('''
                SELECT listen_date, duration_seconds
                FROM user_listening_log
                WHERE user_id = %s AND listen_date >= %s
            ''', (current_user_id, start_date.isoformat()))
            daily_rows = cursor.fetchall()

            # 3. v0.7.1 P1：总时长口径统一，读 users.listening_total（删专辑不掉）
            cursor.execute('SELECT listening_total FROM users WHERE user_id = %s', (current_user_id,))
            user_row = cursor.fetchone()
            total_duration = float(user_row['listening_total'] or 0) if user_row else 0.0
            cursor.close()

            data = aggregate_stats(album_rows, daily_rows, days, total_duration)
            return jsonify({"code": 200, "msg": "ok", "data": data})
        except Exception as e:
            print(f"❌ 获取音乐统计失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "获取音乐统计失败，请稍后重试！"}), 500

    # 5. 等级经验详情（v0.7.2）：总经验 / 今日 / 近7天 / 按来源累计 / 最近明细流
    #    口径：总经验 users.xp（完整历史）；总收听 users.listening_total（完整历史）；
    #    今日收听 = user_listening_log 今日 SUM（1秒=1XP）；今日加分 = users.bonus_xp_today；
    #    近7天 / 按来源 / 明细流来自 user_xp_log（自 v0.7.2 起，source_totals 仅代表有明细之后的累计）
    @app.route('/api/user/xp-detail', methods=['GET', 'OPTIONS'])
    @login_required
    def user_xp_detail():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            today = datetime.date.today()
            start_date = today - datetime.timedelta(days=6)  # 近 7 天（含今天）

            # 1. users 累计值（完整历史）
            cursor.execute('SELECT xp, listening_total, bonus_xp_today FROM users WHERE user_id = %s', (current_user_id,))
            user_row = cursor.fetchone()
            total_xp = float(user_row['xp'] or 0) if user_row else 0.0
            total_listening_xp = float(user_row['listening_total'] or 0) if user_row else 0.0
            today_bonus = float(user_row['bonus_xp_today'] or 0) if user_row else 0.0

            # 2. 近 7 天收听经验（user_listening_log，1 秒 = 1 XP）
            cursor.execute('''
                SELECT listen_date, duration_seconds
                FROM user_listening_log
                WHERE user_id = %s AND listen_date >= %s
            ''', (current_user_id, start_date.isoformat()))
            listening_daily = accumulate_daily_logs(cursor.fetchall(), 7)

            # 3. 近 7 天加分经验（user_xp_log 加分来源）
            cursor.execute('''
                SELECT created_at, amount FROM user_xp_log
                WHERE user_id = %s AND xp_type IN (%s, %s, %s) AND created_at >= %s
            ''', (current_user_id, XP_RATING, XP_REVIEW, XP_COMMENT, start_date.isoformat() + ' 00:00:00'))
            bonus_daily = accumulate_bonus_daily(cursor.fetchall(), 7)

            # 4. 按来源累计（自 v0.7.2 起，user_xp_log 全量）
            cursor.execute('''
                SELECT xp_type, COALESCE(SUM(amount), 0) AS s FROM user_xp_log
                WHERE user_id = %s GROUP BY xp_type
            ''', (current_user_id,))
            source_totals = {XP_LISTENING: 0.0, XP_RATING: 0.0, XP_REVIEW: 0.0, XP_COMMENT: 0.0}
            for row in cursor.fetchall():
                if row['xp_type'] in source_totals:
                    source_totals[row['xp_type']] = round(float(row['s'] or 0), 1)

            # 5. 最近明细流（倒序取最近 30 条）
            cursor.execute('''
                SELECT xp_type, amount, created_at FROM user_xp_log
                WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 30
            ''', (current_user_id,))
            recent_logs = [{
                'xp_type': row['xp_type'],
                'amount': round(float(row['amount'] or 0), 1),
                'created_at': str(row['created_at']) if row['created_at'] else '',
            } for row in cursor.fetchall()]
            cursor.close()

            # 6. 等级字段由 xp 纯函数实时推导（与 /api/user/info 一致）
            level = compute_level(total_xp)
            return jsonify({
                "code": 200,
                "msg": "ok",
                "data": {
                    "total_xp": round(total_xp, 1),
                    "level": level,
                    "next_level_xp": xp_to_next_level(total_xp),
                    "xp_progress": level_progress(total_xp),
                    "level_title": level_title(level),
                    "total_listening_xp": round(total_listening_xp, 1),
                    "today_listening": round(listening_daily[-1]['duration'], 1),
                    "today_bonus": round(today_bonus, 1),
                    "today_xp": round(listening_daily[-1]['duration'] + today_bonus, 1),
                    "daily_xp": build_daily_xp(listening_daily, bonus_daily),
                    "source_totals": source_totals,
                    "recent_logs": recent_logs,
                }
            })
        except Exception as e:
            print(f"❌ 获取经验详情失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "获取经验详情失败，请稍后重试！"}), 500
