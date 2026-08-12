# MusicRate\backend\api\ai.py AI 助手接口（v0.8.1 P3 + P5）
# P3：个人 AI key 配置 —— POST /api/ai/key 保存密钥、GET /api/ai/status 查询状态
# P5：AI 助手后端 —— 上下文组装 + OpenAI 兼容 chat + SSE 流式 + 配额 + 会话持久化：
#   - GET  /api/ai/conversation         查询某专辑的对话历史（最近 HISTORY_LIMIT 条）
#   - POST /api/ai/conversation/reset   清空某专辑对话历史
#   - POST /api/ai/conversation/delete  删除某条历史消息
#   - POST /api/ai/chat                 提问（context：BPM/歌词/听后感/评论/全网听后感；stream=true → SSE）
# 决策（README v0.8.1，镜像 BookRate backend/api/ai.py）：
#   - 上下文组装纯函数放 backend/utils/ai_context.py（零 DB 可单测），本模块只做 DB 查询与组装调用
#   - BPM 懒分析：album_tempo 缺失 + 池专辑有可播放整轨 mp3 → 触发异步 start_tempo_task（防重复用
#     tasks.find_active(kind='tempo')），返回「节奏分析中」提示，不阻塞提问
#   - 配额 ai_quota：提问成功才计数（requests+1 / chars 按问题+回答字符），失败/中断不落半会话
#   - SSE 事件流：delta（增量文本）/ done（含落库的 user_msg_id、assistant_msg_id、完整 answer）/ error
#   - 铁律：key 明文只存后端 DB，前端只存「是否已配置」布尔，绝不返回明文
import json
import os
import re
import traceback
from datetime import datetime

import pymysql
import requests
from flask import Response, jsonify, request

from backend.config import AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_album_table_name, get_current_user_id, get_db
from backend.utils.decorators import login_required
from backend.utils.json import safe_json_loads
from backend.utils.task_table import tasks
from backend.utils.ai_context import (
    COMMENT_LIMIT,
    HISTORY_LIMIT,
    REVIEW_PER_USER,
    REVIEW_TOTAL_CAP,
    build_system_prompt,
    extract_current_track_lyric,
    format_comments,
    format_reviews,
    format_score,
    format_tempo,
    parse_feelings,
)
from backend.api.tempo_ai import start_tempo_task

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


def _is_ascii_printable(text):
    """API 密钥必须为可打印 ASCII：请求头按 latin-1 编码发送，含中文等非 ASCII 会在 putheader 时 500
    （实测坑：误粘贴中文记事文本进密钥字段，Authorization 头编码炸 latin-1，位置恰好是中文起止）
    """
    return all(32 <= ord(c) < 127 for c in (text or ''))


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
    if not _is_ascii_printable(api_key):
        return provider, api_key, "API密钥包含非ASCII字符（可能误粘贴了中文文本），请重新粘贴正确的密钥！"
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


# ==================== 配额（ai_quota，提问成功才计数） ====================

def _check_quota(db, cursor, user_id):
    """校验今日配额是否可用；返回 (ok, error_msg)"""
    requests_used, chars_used = _get_daily_usage(db, cursor, user_id)
    if requests_used >= DAILY_LIMIT_REQUESTS:
        return False, f"今日AI提问次数已达上限（{DAILY_LIMIT_REQUESTS}次），请明天再试！"
    if chars_used >= DAILY_LIMIT_CHARS:
        return False, f"今日AI消费字符数已达上限（{DAILY_LIMIT_CHARS}），请明天再试！"
    return True, ''


def _incr_quota(db, cursor, user_id, chars):
    """今日用量 +1 次 / +chars 字符（ai_quota 按 user_id+quota_date 唯一，upsert）"""
    cursor.execute('''
        INSERT INTO ai_quota (user_id, quota_date, requests, chars)
        VALUES (%s, CURDATE(), 1, %s)
        ON DUPLICATE KEY UPDATE
            requests = requests + 1,
            chars = chars + VALUES(chars)
    ''', (user_id, int(chars or 0)))


# ==================== 会话持久化（ai_conversation） ====================

def _save_message(db, cursor, user_id, album_pool_id, role, content):
    """落一条会话消息（user/assistant），返回新消息 id"""
    cursor.execute('''
        INSERT INTO ai_conversation (user_id, album_pool_id, role, content)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, album_pool_id, role, content))
    return cursor.lastrowid


def _load_history(db, cursor, user_id, album_pool_id):
    """某专辑对话历史（按 id 升序，最近 HISTORY_LIMIT 条；去 id 字段供上下文拼接）"""
    cursor.execute('''
        SELECT id, role, content FROM ai_conversation
        WHERE user_id = %s AND album_pool_id = %s
        ORDER BY id ASC
    ''', (user_id, album_pool_id))
    rows = cursor.fetchall()
    return [{'id': r['id'], 'role': r['role'], 'content': r['content']} for r in rows][-HISTORY_LIMIT:]


# ==================== 上下文查询（DB → ai_context 纯函数组装） ====================

def _get_album_context(db, cursor, user_id, album_pool_id):
    """池专辑（album_pool 公共模板）+ 用户私有副本（albums_{user_id}.source_pool_id，best-effort）
    私有副本缺失（未收藏）不阻断 → user_album = None，AI 只见公共信息
    """
    pool_album = {}
    cursor.execute('''
        SELECT id, album_name, singer, album_intro, tracks, release_year, main_type, tags, mp3_url
        FROM album_pool WHERE id = %s
    ''', (album_pool_id,))
    row = cursor.fetchone()
    if row:
        pool_album = dict(row)
        pool_album['tracks'] = safe_json_loads(pool_album.get('tracks')) or []
        pool_album['tags'] = safe_json_loads(pool_album.get('tags')) or []

    user_album = None
    try:
        table_name = get_album_table_name(user_id)
        cursor.execute(f'''
            SELECT album_name, singer, tags, my_score, review, album_intro, tracks_time
            FROM `{table_name}` WHERE source_pool_id = %s LIMIT 1
        ''', (album_pool_id,))
        urow = cursor.fetchone()
        if urow:
            user_album = dict(urow)
            user_album['tags'] = safe_json_loads(user_album.get('tags')) or []
            user_album['my_score'] = safe_json_loads(user_album.get('my_score')) or []
            user_album['review'] = safe_json_loads(user_album.get('review')) or {}
            user_album['tracks_time'] = safe_json_loads(user_album.get('tracks_time')) or []
    except Exception as e:
        # 未收藏该专辑 → albums_{user_id} 表可能不存在该行，忽略即可
        print(f"⚠️ 查询用户专辑副本失败（可能未收藏）：{str(e)}")
    return {'pool_album': pool_album, 'user_album': user_album}


def _get_singer_intro(db, cursor, singer):
    """歌手简介 best-effort：按 album_singers.singer_name 精确匹配第一个启用歌手返回 detail_intro"""
    if not singer:
        return ''
    for name in re.split(r'[,、;/&|（(]', singer):
        name = name.strip()
        if not name:
            continue
        cursor.execute(
            'SELECT detail_intro FROM album_singers WHERE singer_name = %s AND is_enabled = 1 LIMIT 1',
            (name,),
        )
        row = cursor.fetchone()
        if row and row.get('detail_intro'):
            return row['detail_intro']
    return ''


def _get_tempo(db, cursor, album_pool_id):
    """album_tempo 缓存 JSON → dict；无缓存返回 None（触发懒分析的依据）"""
    cursor.execute('SELECT tempo FROM album_tempo WHERE album_pool_id = %s LIMIT 1', (album_pool_id,))
    row = cursor.fetchone()
    if not row or not row.get('tempo'):
        return None
    try:
        return json.loads(row['tempo'])
    except (TypeError, json.JSONDecodeError):
        return None


def _resolve_audio_path(mp3_url):
    """mp3_url（http://localhost:5000/tracks/<filename>）→ 磁盘绝对路径（复用 tempo_ai 口径）"""
    if not mp3_url:
        return None
    filename = mp3_url.split('/')[-1]
    return os.path.join(AUDIO_UPLOAD_FOLDER, filename)


def _get_current_track_lyric(db, cursor, album_pool_id, tracks_time, current_track_index):
    """当前播放曲目的歌词切片（整轨文本 + tracks_time → ai_context.extract_current_track_lyric）"""
    cursor.execute('SELECT lyric_text FROM album_lyric WHERE album_pool_id = %s LIMIT 1', (album_pool_id,))
    row = cursor.fetchone()
    if not row or not row.get('lyric_text'):
        return ''
    return extract_current_track_lyric(row['lyric_text'], tracks_time, current_track_index)


def _get_comments_context(db, cursor, album_pool_id):
    """平台评论（album_comments 按点赞降序取 COMMENT_LIMIT 条，username 已冗余存储）"""
    cursor.execute('''
        SELECT username, content FROM album_comments
        WHERE album_id = %s
        ORDER BY like_count DESC, create_time DESC
        LIMIT %s
    ''', (album_pool_id, COMMENT_LIMIT))
    return [dict(r) for r in cursor.fetchall()]


def _get_reviews_context(db, cursor, album_pool_id):
    """全网听后感精选：跨所有 albums_{user_id} 表按 source_pool_id 聚合
    - 每用户最新 REVIEW_PER_USER 条（create_time 倒序），总量 cap REVIEW_TOTAL_CAP
    - username 从 users 表取（带缓存），取不到 → 「用户{user_id}」
    - information_schema 扫表（与 BookRate 同思路），只认 albums_数字 表
    """
    cursor.execute(
        "SELECT table_name AS tname FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name LIKE 'albums\\_%'"
    )
    tables = [r['tname'] for r in cursor.fetchall()]
    tables = [t for t in tables if re.fullmatch(r'albums_\d+', t)]

    result = []
    username_cache = {}
    for tname in tables:
        uid = tname[len('albums_'):]
        try:
            cursor.execute(f'''
                SELECT review FROM `{tname}` WHERE source_pool_id = %s LIMIT 1
            ''', (album_pool_id,))
            row = cursor.fetchone()
        except Exception as e:
            # 单张用户表异常（缺列/损坏）不应阻断全网听后感 → 跳过该表
            print(f"⚠️ 扫描用户表{tname}听后感失败（跳过）：{str(e)}")
            continue
        if not row:
            continue
        feelings = parse_feelings(safe_json_loads(row.get('review')) or {})
        if not feelings:
            continue
        # 该用户最新 REVIEW_PER_USER 条（create_time 字符串倒序；无时间戳的排后面）
        feelings = sorted(
            feelings, key=lambda x: str(x.get('create_time') or ''), reverse=True,
        )[:REVIEW_PER_USER]
        if uid not in username_cache:
            cursor.execute('SELECT username FROM users WHERE user_id = %s', (int(uid),))
            urow = cursor.fetchone()
            username_cache[uid] = (urow or {}).get('username') or f'用户{uid}'
        for f in feelings:
            content = (f.get('content') or '').strip()
            if not content:
                continue
            result.append({'username': username_cache[uid], 'rating': f.get('my_score'), 'content': content})
        if len(result) >= REVIEW_TOTAL_CAP:
            break
    return result[:REVIEW_TOTAL_CAP]


def _prepare_chat_messages(db, cursor, user_id, album_pool_id, question, current_track_index):
    """组装 chat messages：[system 上下文 + 历史 + 本次提问]
    上下文含：专辑/歌手信息、你的评分/听后感/标签、BPM、当前歌歌词、平台评论、全网听后感
    """
    ctx = _get_album_context(db, cursor, user_id, album_pool_id)
    pool = ctx['pool_album']
    user = ctx['user_album']
    album_name = pool.get('album_name') or (user or {}).get('album_name') or ''
    singer = pool.get('singer') or (user or {}).get('singer') or ''

    singer_intro = _get_singer_intro(db, cursor, singer)

    tempo_dict = _get_tempo(db, cursor, album_pool_id)
    tempo_text = format_tempo(tempo_dict, pool.get('tracks')) if tempo_dict else ''

    current_lyric = ''
    if current_track_index is not None:
        tracks_time = (user or {}).get('tracks_time') or []
        current_lyric = _get_current_track_lyric(db, cursor, album_pool_id, tracks_time, current_track_index)

    system_prompt = build_system_prompt(
        album_name=album_name, singer=singer,
        album_intro=pool.get('album_intro') or '',
        tracks=pool.get('tracks'),
        release_year=pool.get('release_year'),
        main_type=pool.get('main_type'),
        own_tags=(user or {}).get('tags'),
        own_score=format_score((user or {}).get('my_score')) if user else '',
        own_feelings=parse_feelings((user or {}).get('review')) if user else [],
        singer_intro=singer_intro,
        tempo_text=tempo_text,
        current_lyric_text=current_lyric,
        comments_text=format_comments(_get_comments_context(db, cursor, album_pool_id)),
        other_reviews_text=format_reviews(_get_reviews_context(db, cursor, album_pool_id)),
    )
    history = _load_history(db, cursor, user_id, album_pool_id)
    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend({'role': m['role'], 'content': m['content']} for m in history)
    messages.append({'role': 'user', 'content': question})
    return messages


# ==================== OpenAI 兼容调用（chat 非流式 + SSE 流式） ====================

def _call_ai(provider, api_key, messages):
    """非流式调用 OpenAI 兼容 chat/completions → 完整回答文本"""
    provider_cfg = PROVIDER_CONFIG.get(provider)
    if not provider_cfg:
        raise ValueError(f"暂不支持该AI服务商：{provider}，请重新配置密钥")
    if not _is_ascii_printable(api_key):
        raise RuntimeError("API密钥格式不正确（包含非ASCII字符），请重新配置密钥！")
    resp = requests.post(
        provider_cfg['base_url'],
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': provider_cfg['model'], 'messages': messages,
            'temperature': 0.7, 'max_tokens': 2048,
        },
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"❌ AI接口返回异常：{resp.status_code} {resp.text[:500]}")
        raise RuntimeError(f"AI服务调用失败（{resp.status_code}）")
    return resp.json()['choices'][0]['message']['content']


def _call_ai_stream(provider, api_key, messages):
    """SSE 流式调用 OpenAI 兼容 chat/completions（stream=True）→ 逐段 delta 文本的生成器"""
    provider_cfg = PROVIDER_CONFIG.get(provider)
    if not provider_cfg:
        raise ValueError(f"暂不支持该AI服务商：{provider}，请重新配置密钥")
    if not _is_ascii_printable(api_key):
        raise RuntimeError("API密钥格式不正确（包含非ASCII字符），请重新配置密钥！")
    resp = requests.post(
        provider_cfg['base_url'],
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'model': provider_cfg['model'], 'messages': messages,
            'temperature': 0.7, 'max_tokens': 2048, 'stream': True,
        },
        stream=True,
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"❌ AI流式接口返回异常：{resp.status_code} {resp.text[:500]}")
        raise RuntimeError(f"AI服务调用失败（{resp.status_code}）")
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        line = line.strip()
        if not line.startswith('data:'):
            continue
        payload = line[5:].strip()
        if payload == '[DONE]':
            break
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if 'error' in chunk:
            err = chunk['error']
            msg = err.get('message') if isinstance(err, dict) else str(err)
            raise RuntimeError(f"AI服务错误：{msg}")
        choices = chunk.get('choices') or []
        if not choices:
            continue
        delta = (choices[0].get('delta') or {}).get('content') or ''
        if delta:
            yield delta


def _pool_has_playable_mp3(pool):
    """池专辑是否含磁盘上真实存在的整轨 mp3（懒分析前置条件）"""
    mp3_url = pool.get('mp3_url') or ''
    if not mp3_url:
        return False
    audio_path = _resolve_audio_path(mp3_url)
    return bool(audio_path and os.path.exists(audio_path))


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

    # ========== 3. 查询某专辑的对话历史（最近 HISTORY_LIMIT 条） ==========
    @app.route('/api/ai/conversation', methods=['GET', 'OPTIONS'])
    @login_required
    def get_ai_conversation():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "登录状态失效，请重新登录！"}), 401
            album_pool_id = request.args.get('album_pool_id')
            if not album_pool_id:
                return jsonify({"code": 400, "msg": "缺少专辑ID！"}), 400
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            try:
                history = _load_history(db, cursor, user_id, int(album_pool_id))
            finally:
                cursor.close()
            return jsonify({"code": 200, "msg": "查询成功", "data": {"messages": history}})
        except Exception as e:
            print(f"❌ 查询AI会话历史出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": "查询AI会话历史失败，请稍后重试！"}), 500

    # ========== 4. 清空某专辑的对话历史 ==========
    @app.route('/api/ai/conversation/reset', methods=['POST', 'OPTIONS'])
    @login_required
    def reset_ai_conversation():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "登录状态失效，请重新登录！"}), 401
            data = request.get_json() or {}
            album_pool_id = data.get('album_pool_id')
            if not album_pool_id:
                return jsonify({"code": 400, "msg": "缺少专辑ID！"}), 400
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            try:
                cursor.execute(
                    'DELETE FROM ai_conversation WHERE user_id = %s AND album_pool_id = %s',
                    (user_id, int(album_pool_id)),
                )
                deleted = cursor.rowcount
                db.commit()
            finally:
                cursor.close()
            return jsonify({"code": 200, "msg": f"已清空该专辑的对话历史（{deleted} 条）！", "data": {"deleted": deleted}})
        except Exception as e:
            print(f"❌ 清空AI会话历史出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": "清空AI会话历史失败，请稍后重试！"}), 500

    # ========== 5. 删除某条历史消息（校验归属） ==========
    @app.route('/api/ai/conversation/delete', methods=['POST', 'OPTIONS'])
    @login_required
    def delete_ai_conversation():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "登录状态失效，请重新登录！"}), 401
            data = request.get_json() or {}
            message_id = data.get('message_id')
            if not message_id:
                return jsonify({"code": 400, "msg": "缺少消息ID！"}), 400
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            try:
                cursor.execute(
                    'DELETE FROM ai_conversation WHERE id = %s AND user_id = %s',
                    (int(message_id), user_id),
                )
                deleted = cursor.rowcount
                db.commit()
            finally:
                cursor.close()
            if not deleted:
                return jsonify({"code": 404, "msg": "消息不存在或无权删除！"}), 404
            return jsonify({"code": 200, "msg": "消息已删除！", "data": {"deleted": deleted}})
        except Exception as e:
            print(f"❌ 删除AI会话消息出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": "删除AI会话消息失败，请稍后重试！"}), 500

    # ========== 6. AI 提问（chat）：上下文组装 + OpenAI 兼容调用；stream=true → SSE 流式 ==========
    @app.route('/api/ai/chat', methods=['POST', 'OPTIONS'])
    @login_required
    def ai_chat():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            data = request.get_json() or {}
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({"code": 401, "msg": "登录状态失效，请重新登录！"}), 401
            album_pool_id = data.get('album_pool_id')
            question = (data.get('question') or '').strip()
            if not album_pool_id:
                return jsonify({"code": 400, "msg": "缺少专辑ID！"}), 400
            if not question:
                return jsonify({"code": 400, "msg": "提问内容不能为空！"}), 400

            key_row = _get_user_ai_key(user_id)
            if not key_row or not key_row.get('is_enabled'):
                return jsonify({"code": 403, "msg": "请先配置AI密钥再使用AI助手！"}), 403
            provider = key_row.get('provider') or DEFAULT_PROVIDER
            if provider not in PROVIDER_CONFIG:
                return jsonify({"code": 400, "msg": f"暂不支持该AI服务商：{provider}，请重新配置密钥"}), 400

            try:
                current_track_index = int(data.get('current_track_index'))
            except (TypeError, ValueError):
                current_track_index = None

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            try:
                cursor.execute(
                    'SELECT id, album_name, mp3_url FROM album_pool WHERE id = %s',
                    (album_pool_id,),
                )
                pool = cursor.fetchone()
                if not pool:
                    return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404

                # BPM 懒分析：album_tempo 缺失 + 池专辑有可播放整轨 mp3 → 异步分析（防重复触发），
                # 本次提问返回「节奏分析中」提示，不阻塞请求（README：避免请求线程等几十秒）
                if not _get_tempo(db, cursor, album_pool_id) and _pool_has_playable_mp3(pool):
                    if not tasks.find_active(kind='tempo', album_pool_id=album_pool_id):
                        start_tempo_task(app, album_pool_id, pool['album_name'], user_id)
                    return jsonify({
                        "code": 200,
                        "msg": "正在分析专辑节奏",
                        "data": {
                            "tempo_analyzing": True,
                            "answer": "正在分析该专辑的单曲节奏（BPM），稍后再提问即可获得节奏上下文…",
                        }
                    })

                # ---------- SSE 流式 ----------
                if data.get('stream'):
                    def generate():
                        with app.app_context():
                            gdb = None
                            gcur = None
                            full_answer = ''
                            try:
                                gdb = get_db()
                                gcur = gdb.cursor(pymysql.cursors.DictCursor)
                                quota_ok, quota_msg = _check_quota(gdb, gcur, user_id)
                                if not quota_ok:
                                    yield f"data: {json.dumps({'type': 'error', 'msg': quota_msg}, ensure_ascii=False)}\n\n"
                                    return
                                messages = _prepare_chat_messages(
                                    gdb, gcur, user_id, album_pool_id, question, current_track_index,
                                )
                                for delta in _call_ai_stream(provider, key_row['api_key'], messages):
                                    full_answer += delta
                                    yield f"data: {json.dumps({'type': 'delta', 'content': delta}, ensure_ascii=False)}\n\n"
                                # 流式成功才落库 + 计数（失败/中断不留半会话，避免 ai_conversation 垃圾数据）
                                user_msg_id = _save_message(gdb, gcur, user_id, album_pool_id, 'user', question)
                                assistant_msg_id = _save_message(gdb, gcur, user_id, album_pool_id, 'assistant', full_answer)
                                _incr_quota(gdb, gcur, user_id, len(question) + len(full_answer))
                                gdb.commit()
                                done_payload = json.dumps({
                                    'type': 'done', 'user_msg_id': user_msg_id,
                                    'assistant_msg_id': assistant_msg_id, 'answer': full_answer,
                                }, ensure_ascii=False)
                                yield f"data: {done_payload}\n\n"
                            except Exception as e:
                                if gdb:
                                    gdb.rollback()
                                print(f"❌ AI流式对话出错：{str(e)}")
                                traceback.print_exc()
                                # 透传具体原因（如密钥格式错误/服务商报错），方便前端定位，而非一律「暂不可用」
                                err_msg = (str(e) or 'AI服务暂不可用，请稍后重试')[:200]
                                yield f"data: {json.dumps({'type': 'error', 'msg': err_msg}, ensure_ascii=False)}\n\n"
                            finally:
                                if gcur:
                                    gcur.close()
                    return Response(generate(), mimetype='text/event-stream', headers={
                        'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'
                    })

                # ---------- 非流式 ----------
                quota_ok, quota_msg = _check_quota(db, cursor, user_id)
                if not quota_ok:
                    return jsonify({"code": 429, "msg": quota_msg}), 200
                messages = _prepare_chat_messages(db, cursor, user_id, album_pool_id, question, current_track_index)
                try:
                    answer = _call_ai(provider, key_row['api_key'], messages)
                except Exception as e:
                    db.rollback()
                    print(f"❌ AI调用失败：{str(e)}")
                    return jsonify({"code": 502, "msg": str(e) or "AI服务暂不可用，请稍后重试！"}), 502
                user_msg_id = _save_message(db, cursor, user_id, album_pool_id, 'user', question)
                assistant_msg_id = _save_message(db, cursor, user_id, album_pool_id, 'assistant', answer)
                _incr_quota(db, cursor, user_id, len(question) + len(answer))
                db.commit()
                return jsonify({
                    "code": 200,
                    "msg": "回答成功",
                    "data": {
                        "answer": answer,
                        "user_msg_id": user_msg_id,
                        "assistant_msg_id": assistant_msg_id,
                    }
                })
            finally:
                cursor.close()
        except Exception as e:
            print(f"❌ AI对话外层异常：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": "AI对话失败，请稍后重试！"}), 500

    return app


# 导出注册函数
__all__ = ['register_ai_routes']
