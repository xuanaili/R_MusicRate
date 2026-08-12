# MusicRate\backend\tests\test_ai_chat_realdata.py AI 助手 chat/conversation/quota realdata 集成测试（v0.8.1 P5，依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_ai_chat_realdata.py
# 覆盖（README P5：chat + 上下文组装 + OpenAI 兼容调用 + SSE 流式 + 配额 + 会话持久化）：
#   - 权限/校验：未登录 401、缺专辑ID 400、空提问 400、无key 403、池专辑不存在 404
#   - 非流式 chat：mock _call_ai → 回答 + ai_conversation 落库(user/assistant) + ai_quota 计数 + 历史可见
#   - 上下文组装（prompt spy）：专辑/歌手信息、你的评分/听后感/标签、当前歌歌词（按 tracks_time 切片）、平台评论、全网听后感
#   - 未收藏该专辑（无私有副本）→ 优雅降级，省略「你的评分/听后感/标签」段落，仍正常回答
#   - SSE 流式：mock _call_ai_stream → delta 事件 + done 事件（含落库 id + 完整 answer）+ 落库/计数
#   - 流式失败：中途异常 → error 事件兜底，不留半会话、不计数
#   - 会话历史：GET 空/已存、reset 清空、delete 删除单条、删不存在的消息 404
#   - BPM 懒分析：tempo 缺失 + 有整轨 mp3 → 触发异步分析返回「节奏分析中」；已有活跃任务不重复触发；
#     已有 tempo 缓存 → 正常回答且 system 含【单曲节奏 BPM】
import json
import os
import tempfile
import time

import pytest

from backend import create_app
from backend.config import AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_album_table_name, get_db
from backend.utils.task_table import tasks


@pytest.fixture(scope='module')
def client():
    # 与 test_ai_key_realdata 同款：不用 `with app.test_client()`（preserve_context 跨请求复用 g 会二次 close）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture(scope='module', autouse=True)
def ensure_ai_tables(client):
    """create_app() 不跑 init_base_tables（仅 run.py 启动时跑）→ 模块级确保 P3/P5 三张 AI 表存在（幂等 CREATE）"""
    from backend.utils.db import create_ai_conversation, create_ai_key, create_ai_quota
    with client.application.app_context():
        create_ai_key()
        create_ai_conversation()
        create_ai_quota()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_ai_chat_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _register_second_user(client):
    """额外注册一个用户（全网听后感测试用），返回 user_id"""
    username = f'test_ai_chat_b_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return login['data']['user_id']


# ==================== DB 数据插入 helpers ====================

def _save_key(client, headers, provider='deepseek', api_key='sk-test-1234567890abcdef'):
    r = client.post('/api/ai/key', json={'provider': provider, 'api_key': api_key, 'is_enabled': True}, headers=headers)
    assert r.get_json()['code'] == 200, r.get_json()


def _insert_pool_album(client, mp3_url=None, singer='测试歌手', tracks='["歌一", "歌二"]',
                       album_intro='', main_type='', tracks_time='[]'):
    """插入 album_pool 模板，返回 id（线上库 tracks_time 列 DDL 漂移无默认值，必须显式传）"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO album_pool (album_name, singer, release_year, create_user, main_type, album_intro, tracks, mp3_url, mp3_duration, tracks_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', ('AI对话测试专辑', singer, 2026, 0, main_type, album_intro, tracks, mp3_url, 6 if mp3_url else 0, tracks_time))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _insert_user_album(client, user_id, pool_id, my_score='[]', review='{}', tags='[]',
                       tracks_time='[0, 10]', singer='测试歌手'):
    """在 albums_{user_id} 插入私有副本（source_pool_id 关联池专辑），review 用 feelings 格式 JSON"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            f'INSERT INTO `{table}` (album_name, singer, release_year, source_pool_id, my_score, review, tags, tracks_time) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            ('AI对话用户专辑', singer, 2026, pool_id, my_score, review, tags, tracks_time),
        )
        db.commit()
        cursor.close()


def _insert_lyric(client, pool_id, lyric_text):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO album_lyric (album_pool_id, lyric_text, lyric_translate, create_user_id, create_time, update_time) "
            "VALUES (%s, %s, '', '0', NOW(), NOW())",
            (pool_id, lyric_text),
        )
        db.commit()
        cursor.close()


def _insert_comment(client, pool_id, user_id, username, content):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO album_comments (album_id, user_id, username, content) VALUES (%s, %s, %s, %s)',
            (pool_id, user_id, username, content),
        )
        db.commit()
        cursor.close()


def _insert_singer(client, singer, intro):
    """album_singers upsert（singer_name 唯一，重复执行不报错）"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO album_singers (singer_name, detail_intro, is_enabled)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE detail_intro = VALUES(detail_intro)
        ''', (singer, intro))
        db.commit()
        cursor.close()


def _insert_tempo(client, pool_id, tempo_dict):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO album_tempo (album_pool_id, tempo) VALUES (%s, %s)',
            (pool_id, json.dumps(tempo_dict, ensure_ascii=False)),
        )
        db.commit()
        cursor.close()


def _make_mp3_file(client):
    """在 AUDIO_UPLOAD_FOLDER 创建真实存在的空 .mp3 文件（懒分析只校验文件存在），返回 (filename, path)"""
    fd, path = tempfile.mkstemp(suffix='.mp3', dir=AUDIO_UPLOAD_FOLDER)
    os.close(fd)
    return os.path.basename(path), path


# ==================== 断言 helpers ====================

def _count_conversation(client, user_id, pool_id):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT COUNT(*) AS c FROM ai_conversation WHERE user_id = %s AND album_pool_id = %s', (user_id, pool_id))
        row = cursor.fetchone()
        cursor.close()
        return row['c']


def _get_quota(client, user_id):
    """今日配额 (requests, chars)；无记录 → (0, 0)"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT requests, chars FROM ai_quota WHERE user_id = %s AND quota_date = CURDATE()', (user_id,))
        row = cursor.fetchone()
        cursor.close()
    return (row['requests'], row['chars']) if row else (0, 0)


def _get_messages(client, headers, pool_id):
    """GET /api/ai/conversation → 消息列表（含 id/role/content）"""
    r = client.get(f'/api/ai/conversation?album_pool_id={pool_id}', headers=headers).get_json()
    assert r['code'] == 200, r
    return r['data']['messages']


def _parse_sse(resp):
    """解析 SSE 响应 → [{type, ...}, ...]（resp.data 为 test client 全量缓冲）"""
    events = []
    for line in resp.data.decode('utf-8').splitlines():
        line = line.strip()
        if line.startswith('data:'):
            events.append(json.loads(line[5:].strip()))
    return events


def _chat(client, headers, pool_id, question, **extra):
    payload = {'album_pool_id': pool_id, 'question': question, **extra}
    return client.post('/api/ai/chat', json=payload, headers=headers)


def _mock_call_ai(monkeypatch):
    """替换 ai._call_ai 为固定回答，记录 (provider, api_key, messages) 供断言"""
    captured = []

    def fake(provider, api_key, messages):
        captured.append((provider, api_key, messages))
        return '这是AI的测试回答'

    import backend.api.ai as mod
    monkeypatch.setattr(mod, '_call_ai', fake)
    return captured


def _mock_call_ai_stream(monkeypatch, chunks, fail_after=None):
    """替换 ai._call_ai_stream 为固定分片生成器；fail_after：第 N 个分片后抛异常（模拟流式中断）"""
    import backend.api.ai as mod

    def fake(provider, api_key, messages):
        for i, c in enumerate(chunks):
            if fail_after is not None and i >= fail_after:
                raise RuntimeError('模拟流式中断')
            yield c

    monkeypatch.setattr(mod, '_call_ai_stream', fake)


def _mock_start_tempo_task(monkeypatch):
    """替换 ai.start_tempo_task 记录调用（避免真起后台线程），返回 calls 列表"""
    import backend.api.ai as mod
    calls = []

    def fake(app, album_pool_id, album_name, user_id):
        calls.append({'album_pool_id': album_pool_id, 'album_name': album_name, 'user_id': user_id})
        return 'fake-task'

    monkeypatch.setattr(mod, 'start_tempo_task', fake)
    return calls


def _system_of(captured):
    """从 _call_ai spy 捕获的 (provider, api_key, messages) 取 system prompt 文本"""
    return captured[0][2][0]['content']


# ==================== 权限 / 校验 ====================

@pytest.mark.realdata
def test_chat_requires_login(client):
    r = _chat(client, {}, 1, '你好')
    assert r.get_json()['code'] == 401, r.get_json()


@pytest.mark.realdata
def test_chat_missing_album_pool_id(client, test_user):
    r = client.post('/api/ai/chat', json={'question': '你好'}, headers=test_user['headers']).get_json()
    assert r['code'] == 400, r


@pytest.mark.realdata
def test_chat_empty_question(client, test_user):
    pool_id = _insert_pool_album(client)
    r = _chat(client, test_user['headers'], pool_id, '   ').get_json()
    assert r['code'] == 400, r


@pytest.mark.realdata
def test_chat_without_key_403(client, test_user):
    pool_id = _insert_pool_album(client)
    r = _chat(client, test_user['headers'], pool_id, '你好').get_json()
    assert r['code'] == 403, r
    assert 'AI密钥' in r['msg']


@pytest.mark.realdata
def test_chat_pool_not_exists(client, test_user):
    _save_key(client, test_user['headers'])
    r = _chat(client, test_user['headers'], 999999, '你好').get_json()
    assert r['code'] == 404, r


# ==================== 非流式 chat（mock _call_ai） ====================

@pytest.mark.realdata
def test_chat_non_stream_saves_conversation_and_quota(client, test_user, monkeypatch):
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    captured = _mock_call_ai(monkeypatch)
    question = '这首歌讲了什么？'

    r = _chat(client, test_user['headers'], pool_id, question).get_json()
    assert r['code'] == 200, r
    assert r['data']['answer'] == '这是AI的测试回答'
    assert r['data']['user_msg_id'] and r['data']['assistant_msg_id']

    # 会话落库：user + assistant 两条
    assert _count_conversation(client, test_user['user_id'], pool_id) == 2
    # 配额计数：1 次 / 问题+回答字符数
    assert _get_quota(client, test_user['user_id']) == (1, len(question) + len('这是AI的测试回答'))
    # 上下文：provider/api_key 正确传入，messages 结构 system + 提问
    provider, api_key, messages = captured[0]
    assert provider == 'deepseek'
    assert messages[0]['role'] == 'system'
    assert messages[-1] == {'role': 'user', 'content': question}

    # GET 历史可见（user → assistant 顺序）
    msgs = _get_messages(client, test_user['headers'], pool_id)
    assert [m['role'] for m in msgs] == ['user', 'assistant']


@pytest.mark.realdata
def test_chat_prompt_contains_own_context(client, test_user, monkeypatch):
    """上下文组装：专辑/歌手信息、你的评分/听后感/标签、当前歌歌词（按 tracks_time 切片）、平台评论"""
    _save_key(client, test_user['headers'])
    singer = '测试歌手'
    pool_id = _insert_pool_album(
        client, singer=singer, album_intro='春天主题专辑', main_type='Pop【流行】',
        tracks='["春日光", "花与树"]', tracks_time='[0, 10]',
    )
    _insert_singer(client, singer, '台湾独立乐团')
    _insert_user_album(
        client, test_user['user_id'], pool_id,
        my_score='[85, 88, 90]',
        review='{"feelings": [{"content": "春天的感觉", "create_time": "2026-08-12 10:00", "my_score": 90}], "personal_feeling": ""}',
        tags='["Spring【春天】"]',
    )
    # 歌词：track1 = [0,10) 第一首，track2 = [10,∞) 第二首（tracks_time 切片）
    _insert_lyric(client, pool_id, '00:00.5 第一首歌词\n00:05.0 第一首续\n00:11.0 第二首歌词\n00:20.0 第二首续')
    _insert_comment(client, pool_id, test_user['user_id'], '小明', '太好听了')
    captured = _mock_call_ai(monkeypatch)

    r = _chat(client, test_user['headers'], pool_id, '评价一下这张专辑', current_track_index=1).get_json()
    assert r['code'] == 200, r
    sysp = _system_of(captured)
    assert '【专辑信息】' in sysp and '春天主题专辑' in sysp
    assert '曲目（共2首）：春日光 / 花与树' in sysp
    assert '【歌手信息】' in sysp and '台湾独立乐团' in sysp
    assert '【你的评分】' in sysp and '专辑整体评分：85分' in sysp
    assert '【你的听后感】' in sysp and '1. 春天的感觉' in sysp
    assert '【你的标签】' in sysp and 'Spring【春天】' in sysp
    assert '【当前播放歌曲歌词】' in sysp and '第二首歌词' in sysp and '第一首歌词' not in sysp
    assert '【平台评论】' in sysp and '小明：太好听了' in sysp


@pytest.mark.realdata
def test_chat_prompt_includes_other_users_reviews(client, test_user, monkeypatch):
    """全网听后感：另一用户对同一池专辑的听后感进入 system prompt"""
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    other_id = _register_second_user(client)
    _insert_user_album(
        client, other_id, pool_id,
        review='{"feelings": [{"content": "全网用户的神专评价", "create_time": "2026-08-12 09:00", "my_score": 95}], "personal_feeling": ""}',
    )
    captured = _mock_call_ai(monkeypatch)
    r = _chat(client, test_user['headers'], pool_id, '别人怎么评价？').get_json()
    assert r['code'] == 200, r
    sysp = _system_of(captured)
    assert '【其他用户听后感精选】' in sysp
    assert '全网用户的神专评价' in sysp


@pytest.mark.realdata
def test_chat_without_own_album_omits_own_sections(client, test_user, monkeypatch):
    """未收藏该专辑（无私有副本）→ 优雅降级：省略「你的评分/听后感/标签」，仍正常回答"""
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    captured = _mock_call_ai(monkeypatch)
    r = _chat(client, test_user['headers'], pool_id, '介绍一下').get_json()
    assert r['code'] == 200, r
    sysp = _system_of(captured)
    assert '【专辑信息】' in sysp
    for section in ['【你的评分】', '【你的听后感】', '【你的标签】']:
        assert section not in sysp, section


# ==================== 流式 chat（mock _call_ai_stream） ====================

@pytest.mark.realdata
def test_chat_stream_sse_delta_done(client, test_user, monkeypatch):
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    _mock_call_ai_stream(monkeypatch, ['第一', '段回答'])
    question = '用一句话介绍'

    r = _chat(client, test_user['headers'], pool_id, question, stream=True)
    assert r.status_code == 200
    assert 'text/event-stream' in r.headers.get('Content-Type', '')

    events = _parse_sse(r)
    assert [e['type'] for e in events] == ['delta', 'delta', 'done'], events
    assert events[0]['content'] == '第一'
    assert events[1]['content'] == '段回答'
    assert events[2]['answer'] == '第一段回答'
    assert events[2]['user_msg_id'] and events[2]['assistant_msg_id']
    # 流式成功 → 落库 + 计数
    assert _count_conversation(client, test_user['user_id'], pool_id) == 2
    assert _get_quota(client, test_user['user_id']) == (1, len(question) + len('第一段回答'))


@pytest.mark.realdata
def test_chat_stream_error_no_partial_persist(client, test_user, monkeypatch):
    """流式中途失败 → error 事件兜底；不留半会话、不计数"""
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    _mock_call_ai_stream(monkeypatch, ['开头', '中断'], fail_after=1)

    r = _chat(client, test_user['headers'], pool_id, '问题', stream=True)
    events = _parse_sse(r)
    assert events[-1]['type'] == 'error', events
    assert any(e['type'] == 'delta' and e['content'] == '开头' for e in events)
    # 失败不落库、不计数
    assert _count_conversation(client, test_user['user_id'], pool_id) == 0
    assert _get_quota(client, test_user['user_id']) == (0, 0)


# ==================== 会话历史（get / reset / delete） ====================

@pytest.mark.realdata
def test_conversation_get_empty(client, test_user):
    pool_id = _insert_pool_album(client)
    msgs = _get_messages(client, test_user['headers'], pool_id)
    assert msgs == []


@pytest.mark.realdata
def test_conversation_requires_login(client):
    r = client.get('/api/ai/conversation?album_pool_id=1').get_json()
    assert r['code'] == 401, r


@pytest.mark.realdata
def test_conversation_reset_clears(client, test_user, monkeypatch):
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    _mock_call_ai(monkeypatch)
    r = _chat(client, test_user['headers'], pool_id, '第一条提问').get_json()
    assert r['code'] == 200, r
    assert _count_conversation(client, test_user['user_id'], pool_id) == 2

    r = client.post('/api/ai/conversation/reset', json={'album_pool_id': pool_id}, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['deleted'] == 2
    assert _count_conversation(client, test_user['user_id'], pool_id) == 0


@pytest.mark.realdata
def test_conversation_delete_single_message(client, test_user, monkeypatch):
    _save_key(client, test_user['headers'])
    pool_id = _insert_pool_album(client)
    _mock_call_ai(monkeypatch)
    r = _chat(client, test_user['headers'], pool_id, '要删的消息').get_json()
    assert r['code'] == 200, r
    user_msg_id = r['data']['user_msg_id']

    r = client.post('/api/ai/conversation/delete', json={'message_id': user_msg_id}, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert _count_conversation(client, test_user['user_id'], pool_id) == 1


@pytest.mark.realdata
def test_conversation_delete_not_found(client, test_user):
    r = client.post('/api/ai/conversation/delete', json={'message_id': 999999}, headers=test_user['headers']).get_json()
    assert r['code'] == 404, r


# ==================== BPM 懒分析 ====================

@pytest.mark.realdata
def test_chat_tempo_missing_with_mp3_lazy_triggers(client, test_user, monkeypatch):
    """album_tempo 缺失 + 池专辑有整轨 mp3 → 触发异步分析，返回「节奏分析中」提示"""
    _save_key(client, test_user['headers'])
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        calls = _mock_start_tempo_task(monkeypatch)
        r = _chat(client, test_user['headers'], pool_id, '这首歌什么节奏？').get_json()
        assert r['code'] == 200, r
        assert r['data']['tempo_analyzing'] is True
        assert '节奏' in r['data']['answer']
        assert len(calls) == 1 and calls[0]['album_pool_id'] == pool_id
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.realdata
def test_chat_tempo_missing_no_retrigger_if_active(client, test_user, monkeypatch):
    """已有活跃 tempo 任务 → find_active 防抖，不再重复触发，仍返回「节奏分析中」"""
    _save_key(client, test_user['headers'])
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        tasks.create(
            task_id='fake-active-tempo',
            kind='tempo', album_pool_id=pool_id, album_name='AI对话测试专辑',
            user_id=test_user['user_id'],
            status='queued', message='预置活跃任务', progress=0, created_at=None,
        )
        calls = _mock_start_tempo_task(monkeypatch)
        r = _chat(client, test_user['headers'], pool_id, '这首歌什么节奏？').get_json()
        assert r['code'] == 200, r
        assert r['data']['tempo_analyzing'] is True
        assert calls == [], f'已存在活跃任务仍重复触发：{calls}'
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.realdata
def test_chat_tempo_present_skips_lazy_and_includes_bpm(client, test_user, monkeypatch):
    """已有 album_tempo 缓存 → 不触发懒分析，正常回答，且 system 含【单曲节奏 BPM】"""
    _save_key(client, test_user['headers'])
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}', tracks='["歌一", "歌二"]')
        _insert_tempo(client, pool_id, {
            'track_tempos': [120.0, 90.0], 'avg_bpm': 105.0, 'min_bpm': 90.0, 'max_bpm': 120.0,
        })
        calls = _mock_start_tempo_task(monkeypatch)
        captured = _mock_call_ai(monkeypatch)
        r = _chat(client, test_user['headers'], pool_id, '节奏怎么样？').get_json()
        assert r['code'] == 200, r
        assert r['data']['answer'] == '这是AI的测试回答'
        assert calls == [], '有 tempo 缓存仍触发懒分析！'
        sysp = _system_of(captured)
        assert '【单曲节奏 BPM】' in sysp
        assert '歌一：120.0 BPM' in sysp
        assert '整专平均：105.0 BPM' in sysp
    finally:
        if os.path.exists(path):
            os.remove(path)
