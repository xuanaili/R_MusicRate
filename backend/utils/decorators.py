# MusicRate\backend\decorators.py 登录校验装饰器 - 独立封装登录验证逻辑
from functools import wraps
from flask import request, jsonify
import traceback
from backend.utils.db import get_db, check_and_create_user_album_table, set_current_user_id

def login_required(func):
    """登录校验装饰器：验证token有效性，设置当前登录用户ID"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # ========== 核心修改：跳过 OPTIONS 请求的 token 校验 ==========
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
        try:
            # 获取请求头中的token（兼容 'Bearer <token>' 与裸 token 两种写法：
            # 前端重构后部分请求（今日推荐/音乐专题/专辑池详情等）带 Bearer 前缀，
            # 而拦截器走裸 token —— 统一剥掉前缀后按原始 token 精确匹配）
            token = request.headers.get('Authorization') or ''
            if token.lower().startswith('bearer '):
                token = token[7:].strip()
            if not token:
                return jsonify({"code": 401, "msg": "请先登录！"}), 401

            # MySQL验证token
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT user_id, username FROM users WHERE token = %s', (token,))
            user = cursor.fetchone()
            cursor.close()

            if not user:
                return jsonify({"code": 401, "msg": "登录已过期，请重新登录！"}), 401

            # 设置当前登录用户ID到Flask g对象（线程安全）
            set_current_user_id(user["user_id"])
            # 检查并创建用户专辑表（确保表存在）
            check_and_create_user_album_table(user["user_id"])

            # 执行原函数
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ 登录校验失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录校验出错：{str(e)}"}), 500

    return wrapper