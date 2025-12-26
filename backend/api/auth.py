# MusicRate\backend\api\auth.py 登录/注册接口 - 适配新users表结构
from flask import request, jsonify
import uuid
import traceback
from datetime import datetime
from ..db_utils import get_db, create_user_album_table, encrypt_password, verify_password  # 导入加密/验证函数


def register_auth_routes(app):
    """注册登录/注册路由（需传入Flask app实例）"""

    # 1. 注册接口（适配新表结构 + 密码加密）
    @app.route('/api/register', methods=['POST', 'OPTIONS'])
    def register():
        try:
            # 处理OPTIONS预检请求
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            data = request.get_json()
            # 容错处理（如果请求体不是JSON，返回友好提示）
            if not data:
                return jsonify({"code": 400, "msg": "请求体必须是JSON格式！"}), 400

            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            # 校验必填字段 + 用户名非法字符过滤
            if not username:
                return jsonify({"code": 400, "msg": "用户名不能为空！"}), 400
            if not password:
                return jsonify({"code": 400, "msg": "密码不能为空！"}), 400
            # 过滤禁用字符 %^&
            if any(char in username for char in ['%', '^', '&']):
                return jsonify({"code": 400, "msg": "用户名不能包含 %、^、& 字符！"}), 400

            db = get_db()
            cursor = db.cursor()
            # 检查用户名是否已存在
            cursor.execute('SELECT user_id FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                cursor.close()
                return jsonify({"code": 400, "msg": "用户名已被注册！"}), 400

            # 密码加密 + 创建新用户（适配新表结构）
            encrypted_pwd = encrypt_password(password)
            cursor.execute('''
                INSERT INTO users (
                    username, password, create_time, 
                    level, is_vip, is_admin, donate_amount, album_count
                ) VALUES (%s, %s, %s, 0, 0, 0, 0.00, 0)
            ''', (username, encrypted_pwd, datetime.now()))
            new_user_id = cursor.lastrowid
            db.commit()

            # 为新用户创建专属专辑表
            create_user_album_table(new_user_id)

            cursor.close()
            return jsonify({
                "code": 200,
                "msg": "注册成功！请登录",
                "data": {"username": username}
            })
        except Exception as e:
            print(f"❌ 注册出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "注册失败，请稍后重试！"}), 500

    # 2. 登录接口（适配新表结构 + 密码验证）
    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login():
        try:
            # 处理OPTIONS预检请求
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            data = request.get_json()
            if not data:
                return jsonify({"code": 400, "msg": "请求体必须是JSON格式！"}), 400

            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            # 增强参数校验
            if not username:
                return jsonify({"code": 400, "msg": "账号不能为空！"}), 400
            if not password:
                return jsonify({"code": 400, "msg": "密码不能为空！"}), 400

            # 数据库验证（适配新表结构）
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT user_id, username, password, is_admin, is_vip, level
                FROM users 
                WHERE username = %s
            ''', (username,))
            user = cursor.fetchone()

            # 账号不存在 或 密码验证失败
            if not user or not verify_password(password, user["password"]):
                cursor.close()
                return jsonify({"code": 401, "msg": "账号或密码错误！"}), 401

            # 生成唯一token并更新（同时更新最近登录时间）
            token = str(uuid.uuid4())
            cursor.execute('''
                UPDATE users 
                SET token = %s, last_login = %s 
                WHERE user_id = %s
            ''', (token, datetime.now(), user["user_id"]))
            db.commit()
            cursor.close()

            # 返回统一格式的成功响应（包含新字段）
            return jsonify({
                "code": 200,
                "msg": "登录成功！",
                "data": {
                    "token": token,
                    "username": user["username"],
                    "user_id": user["user_id"],
                    "is_admin": user["is_admin"],
                    "is_vip": user["is_vip"],
                    "level": user["level"]
                }
            })
        except Exception as e:
            print(f"❌ 登录出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": "登录失败，请稍后重试！"}), 500