# MusicRate\backend\api\ai.py AI 助手接口 - 个人 AI key 配置（v0.8.1 P3）
# 镜像 BookRate backend/api/ai.py 的 key 配置部分（P5 再补 chat/conversation）：
#   - POST /api/ai/key：保存/更新用户 AI key（upsert ai_key，user_id 唯一），响应绝不返回明文
#   - GET /api/ai/status：{has_key, provider, today_requests, today_chars}（今日用量来自 ai_quota，
#     P5 落 ai_quota 表后才计数；P3 阶段表未建时优雅返回 0，不阻断 status）
# 安全铁律（README v0.8.1）：key 明文只存后端 DB，前端只存「是否已配置」布尔，绝不返回明文。
import traceback
from datetime import datetime

import pymysql
from flask import jsonify, request

from backend.utils.db import get_current_user_id, get_db
from backend.utils.decorators import login_required

# 支持的 AI 服务商（OpenAI 兼容接口格式，P5 chat 复用）
PROVIDER_CONFIG = {
    'deepseek': {
        'base_url': 'https://api.deepseek.com/chat/completions',
        'model': 'deepseek-chat'
    },
    'openai': {
        'base_url': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-4o-mini'
    }
}
DEFAULT_PROVIDER = 'deepseek'

# 每日限额配置（P5 生效；置极大值 = 暂关闭限额，与 BookRate 一致）
DAILY_LIMIT_REQUESTS = 99999
DAILY_LIMIT_CHARS = 99999

# API 密钥最大长度（db.py ai_key.api_key 为 TEXT；设上限防误粘贴大文本，超限给友好 400 而非 DB 错误）
MAX_API_KEY_LENGTH = 1000


def validate_ai_key_params(provider, api_key):
    """纯函数：规范化并校验 AI key 配置参数（可单测，零 DB 依赖）
    - provider：去空白 + 小写，空则回退 DEFAULT_PROVIDER；不在 PROVIDER_CONFIG 返回错误
    - api_key：去空白；空则返回错误；超 MAX_API_KEY_LENGTH 返回错误（防误粘贴）
    返回 (normalized_provider, normalized_api_key, error_msg)，error_msg 非空表示校验失败
    """
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    api_key = (api_key or '').strip()
    if provider not in PROVIDER_CONFIG:
        return provider, api_key, f"暂不支持该AI服务商：{provider}，请重新配置密钥"
    if not api_key:
        return provider, api_key, "API密钥不能为空！"
    if len(api_key) > MAX_API_KEY_LENGTH:
        return provider, api_key, f"API密钥过长（超过{MAX_API_KEY_LENGTH}字符），请检查粘贴内容！"
    return provider, api_key, ''


def _get_user_ai_key(user_id):
    """查询用户已保存的密钥记录（含 api_key，仅后端使用，不返回前端）"""
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute('''
        SELECT id, provider, api_key, is_enabled
        FROM ai_key WHERE user_id = %s
    ''', (user_id,))
    row = cursor.fetchone()
    cursor.close()
    return row


def _get_daily_usage(db, cursor, user_id):
    """查询用户今日 AI 用量（提问次数 + 消费字符数）
    ai_quota 为 P5 建表（README DDL：requests/chars 列）；P3 阶段表未建 → 捕获异常返回 0，不阻断 status
    """
    try:
        cursor.execute('''
            SELECT requests, chars FROM ai_quota
            WHERE user_id = %s AND quota_date = CURDATE()
        ''', (user_id,))
        row = cursor.fetchone()
    except Exception:
        return 0, 0
    if not row:
        return 0, 0
    return row.get('requests', 0) or 0, row.get('chars', 0) or 0


def register_ai_routes(app):
    """注册 AI 助手路由（需传入 Flask app 实例），全部 @login_required"""

    # ========== 1. 保存/更新用户 AI 密钥（upsert ai_key，响应不含明文） ==========
    @app.route('/api/ai/key', methods=['POST', 'OPTIONS'])
    @login_required
    def save_ai_key():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            data = request.get_json() or {}
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "登录状态失效，请重新登录！"}), 401

            provider, api_key, err = validate_ai_key_params(
                data.get('provider'), data.get('api_key')
            )
            if err:
                return jsonify({"code": 400, "msg": err}), 400
            is_enabled = 1 if data.get('is_enabled', True) else 0

            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM ai_key WHERE user_id = %s', (user_id,))
            exists = cursor.fetchone()

            if exists:
                cursor.execute('''
                    UPDATE ai_key
                    SET provider = %s, api_key = %s, is_enabled = %s, update_time = %s
                    WHERE user_id = %s
                ''', (provider, api_key, is_enabled, datetime.now(), user_id))
                msg = "AI密钥更新成功！"
            else:
                cursor.execute('''
                    INSERT INTO ai_key (user_id, provider, api_key, is_enabled, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (user_id, provider, api_key, is_enabled, datetime.now(), datetime.now()))
                msg = "AI密钥保存成功！"

            db.commit()
            cursor.close()
            # 铁律：绝不返回 api_key 本体，只返回是否配置成功的状态
            return jsonify({
                "code": 200,
                "msg": msg,
                "data": {"has_key": True, "provider": provider}
            })
        except Exception as e:
            print(f"❌ 保存AI密钥出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": "保存AI密钥失败，请稍后重试！"}), 500

    # ========== 2. 查询当前用户是否已配置key + 今日用量（前端决定渲染与限额提示） ==========
    @app.route('/api/ai/status', methods=['GET', 'OPTIONS'])
    @login_required
    def get_ai_status():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "登录状态失效，请重新登录！"}), 401

            row = _get_user_ai_key(user_id)
            has_key = bool(row and row.get('is_enabled'))

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            try:
                requests_used, chars_used = _get_daily_usage(db, cursor, user_id)
            finally:
                cursor.close()

            return jsonify({
                "code": 200,
                "msg": "查询成功",
                "data": {
                    "has_key": has_key,
                    "provider": row.get('provider') if row else DEFAULT_PROVIDER,
                    "today_requests": requests_used,
                    "daily_limit_requests": DAILY_LIMIT_REQUESTS,
                    "today_chars": chars_used,
                    "daily_limit_chars": DAILY_LIMIT_CHARS
                }
            })
        except Exception as e:
            print(f"❌ 查询AI状态出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": "查询AI状态失败，请稍后重试！"}), 500

    return app


# 导出注册函数
__all__ = ['register_ai_routes']
