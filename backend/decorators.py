# MusicRate/backend/decorators.py 登录校验装饰器 - 独立封装登录验证逻辑
from functools import wraps
from flask import request, jsonify
import traceback
from .db_utils import get_db, check_and_create_user_album_table, current_user_id
import pymysql


def login_required(func):
    """登录校验装饰器：验证token有效性，设置当前登录用户ID"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global current_user_id
        current_user_id = None  # 重置当前用户ID
        try:
            # 获取请求头中的token
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({"code": 401, "msg": "请先登录！"}), 401

            # MySQL验证token
            db = get_db()
            # 关键修改1：使用字典游标，才能用user["user_id"]取值
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT user_id, username FROM users WHERE token = %s', (token,))
            user = cursor.fetchone()
            cursor.close()

            if not user:
                return jsonify({"code": 401, "msg": "登录已过期，请重新登录！"}), 401

            # 设置当前登录用户ID
            current_user_id = user["user_id"]
            # 检查并创建用户专辑表（确保表存在）
            check_and_create_user_album_table(current_user_id)

            # 执行原函数
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ 登录校验失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录校验出错：{str(e)}"}), 500

    return wrapper