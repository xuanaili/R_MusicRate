# MusicRate\backend\api\auth.py 登录/注册接口 - 独立封装用户认证逻辑
from flask import request, jsonify
import uuid
import traceback
from ..db_utils import get_db, create_user_album_table


def register_auth_routes(app):
    """注册登录/注册路由（需传入Flask app实例）"""

    # 1. 注册接口（自动创建用户专属专辑表）
    @app.route('/api/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            # 校验必填字段
            if not username or not password:
                return jsonify({"code": 400, "msg": "用户名和密码不能为空！"}), 400

            db = get_db()
            cursor = db.cursor()
            # 检查用户名是否已存在
            cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                cursor.close()
                return jsonify({"code": 400, "msg": "用户名已被注册！"}), 400

            # 创建新用户
            cursor.execute('''
                INSERT INTO users (username, password, token) 
                VALUES (%s, %s, "")
            ''', (username, password))
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
            return jsonify({"code": 500, "msg": f"注册失败：{str(e)}"}), 500

    # 2. 登录接口
    @app.route('/api/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            # 校验必填字段
            if not username or not password:
                return jsonify({"code": 400, "msg": "账号和密码不能为空！"}), 400

            # MySQL验证账号密码
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                SELECT id, username FROM users 
                WHERE username = %s AND password = %s
            ''', (username, password))
            user = cursor.fetchone()

            if not user:
                cursor.close()
                return jsonify({"code": 401, "msg": "账号或密码错误！"}), 401

            # 生成唯一token并更新
            token = str(uuid.uuid4())
            cursor.execute('UPDATE users SET token = %s WHERE id = %s', (token, user["id"]))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "登录成功！",
                "data": {"token": token, "username": username}
            })
        except Exception as e:
            print(f"❌ 登录出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录出错：{str(e)}"}), 500