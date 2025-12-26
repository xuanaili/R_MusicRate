# MusicRate/backend/api/auth.py 登录/注册接口 - 独立封装用户认证逻辑
from flask import request, jsonify
import uuid
import traceback
import bcrypt  # 用于密码加密验证
import pymysql  # 新增：导入pymysql以使用字典游标
from ..db_utils import get_db, create_user_album_table, hash_password  # 导入加密函数


def register_auth_routes(app):
    """注册登录/注册路由（需传入Flask app实例）"""

    # 注册接口核心修复
    @app.route('/api/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({"code": 400, "msg": "用户名和密码不能为空！"}), 400

            # 校验用户名格式（禁用%^&*()<>）
            import re
            if re.search(r'[%^&*()<>]', username):
                return jsonify({"code": 400, "msg": "用户名不能包含%^&*()<>等特殊字符！"}), 400

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            # 修复1：查询user_id（不是id）
            cursor.execute('SELECT user_id FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                cursor.close()
                return jsonify({"code": 400, "msg": "用户名已被注册！"}), 400

            # 加密密码
            hashed_pwd = hash_password(password)
            # 修复2：插入新版users表字段（无created_at，新增is_admin等）
            cursor.execute('''
                INSERT INTO users (
                    username, password, is_admin, token
                ) VALUES (%s, %s, 0, "")
            ''', (username, hashed_pwd))
            new_user_id = cursor.lastrowid  # 获取自增的user_id
            db.commit()

            # 为新用户创建专辑表
            create_user_album_table(new_user_id)

            cursor.close()
            return jsonify({
                "code": 200,
                "msg": "注册成功！请登录",
                "data": {"username": username}
            })
        except Exception as e:
            print(f"注册出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"注册失败：{str(e)}"}), 500

    # 2. 登录接口（修复user_id字段 + 密码加密验证）
    # auth.py 登录接口核心修复
    @app.route('/api/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({"code": 400, "msg": "账号和密码不能为空！"}), 400

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            # 修复1：查询user_id、username、password（不是id）
            cursor.execute('''
                SELECT user_id, username, password FROM users 
                WHERE username = %s
            ''', (username,))
            user = cursor.fetchone()

            # 修复2：bcrypt验证（如果用加密版）
            if not user or not bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
                cursor.close()
                return jsonify({"code": 401, "msg": "账号或密码错误！"}), 401

            # 生成token
            token = str(uuid.uuid4())
            # 修复3：更新token和last_login（不是start_time/created_at）
            cursor.execute('UPDATE users SET token = %s, last_login = NOW() WHERE user_id = %s',
                           (token, user["user_id"]))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "登录成功！",
                "data": {"token": token, "username": username, "user_id": user["user_id"]}
            })
        except Exception as e:
            print(f"登录失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录失败：{str(e)}"}), 500

    # 3. 登出接口（可选，补充完整认证逻辑）
    @app.route('/api/logout', methods=['POST'])
    def logout():
        try:
            data = request.get_json()
            token = data.get('token')
            if not token:
                return jsonify({"code": 400, "msg": "token不能为空！"}), 400

            db = get_db()
            cursor = db.cursor()
            cursor.execute('UPDATE users SET token = "" WHERE token = %s', (token,))
            db.commit()
            cursor.close()

            return jsonify({"code": 200, "msg": "登出成功！"})
        except Exception as e:
            print(f"❌ 登出出错：{str(e)}")
            return jsonify({"code": 500, "msg": f"登出失败：{str(e)}"}), 500