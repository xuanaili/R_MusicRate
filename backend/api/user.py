# MusicRate\backend\api\user.py 个人用户中心接口（v0.7 P0）
# 全部 @login_required；账号注销/改头像/改用户名等后续版本补充
import traceback
import pymysql

from flask import request, jsonify

from backend.utils.auth import encrypt_password
from backend.utils.db import get_db, get_current_user_id, get_album_table_name
from backend.utils.decorators import login_required
from backend.utils.user import validate_password_change


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
                SELECT user_id, username, create_time, level, last_login, is_vip, avatar
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

            return jsonify({
                "code": 200,
                "msg": "ok",
                "data": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "create_time": str(user['create_time']) if user['create_time'] else '',
                    "level": user['level'],
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
