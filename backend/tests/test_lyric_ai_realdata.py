# MusicRate\backend\tests\test_lyric_ai_realdata.py 歌词 AI 识别异步任务 realdata 集成测试（v0.8.1 P1，依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_lyric_ai_realdata.py
# 覆盖：
#   - 触发权限/校验：非管理员 403、池不存在 404、无 mp3 400、mp3 文件缺失 400
#   - 任务链路（fake transcribe，避免真模型数分钟）：触发 → queued → 线程跑 → done → album_lyric 落库
#     （P0 幻觉过滤 + OpenCC 繁转简在正式管线中生效：词曲/字幕行被滤除，繁体转简体）
#   - 状态轮询：不存在的 task_id 404
#   - 真实识别冒烟：库中带整轨 mp3 的池，限前 30s 真模型转写，验证识别器端到端（无库数据则 skip）
import io
import os
import tempfile
import time

import pytest

from backend import create_app
from backend.api.lyric_ai import _resolve_audio_path
from backend.config import AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_db
from backend.utils.lyric_recognizer import is_hallucination, segments_to_items, to_simplified, transcribe


@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    username = f'test_lyric_ai_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _promote_admin(client, user_id):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = %s', (user_id,))
        db.commit()
        cursor.close()


@pytest.fixture()
def admin_user(client, test_user):
    _promote_admin(client, test_user['user_id'])
    return test_user


@pytest.fixture()
def fake_transcribe(monkeypatch):
    """替换 lyric_ai.transcribe 为固定 segments（含 P0 过滤/转简验证样例），避免真模型慢 + 依赖真实音频
    三条 segment：1 条正常繁体歌词 + 2 条幻觉噪音（詞曲/字幕by）→ 预期只落库 1 条简体「某夜你离开」
    """
    def _fake(audio_path, model_size='small', limit_secs=None, language=None, vad_filter=False):
        segments = [
            {'start': 0.0, 'end': 2.0, 'text': '某夜你離開', 'no_speech_prob': 0.05},
            {'start': 2.5, 'end': 4.0, 'text': '詞曲 李宗盛', 'no_speech_prob': 0.05},
            {'start': 4.5, 'end': 6.0, 'text': '字幕by索兰娅', 'no_speech_prob': 0.05},
        ]
        info = type('Info', (), {'language': 'zh', 'duration': 6.0})()
        metrics = {'elapsed': 0.1, 'audio_seconds': 6.0, 'rtf': 0.017}
        return segments, info, metrics

    import backend.api.lyric_ai as mod
    monkeypatch.setattr(mod, 'transcribe', _fake)


def _insert_pool_album(client, mp3_url=None):
    """插入 album_pool 模板，返回 (id, audio_path|None)
    线上库 album_pool.tracks_time 列 DDL 漂移无默认值，必须显式传 '[]'（与 lyric_api_realdata 同款）
    """
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO album_pool (album_name, singer, release_year, create_user, tracks_time, mp3_url, mp3_duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', ('AI识别测试专辑', '测试歌手', 2026, 0, '[]', mp3_url, 6 if mp3_url else 0))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _make_mp3_file(client):
    """在 AUDIO_UPLOAD_FOLDER 创建真实存在的空 .mp3 文件（内容无关，fake transcribe 不读），返回 (filename, path)"""
    fd, path = tempfile.mkstemp(suffix='.mp3', dir=AUDIO_UPLOAD_FOLDER)
    os.close(fd)
    return os.path.basename(path), path


def _get_lyric(client, album_pool_id):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT lyric_text FROM album_lyric WHERE album_pool_id = %s', (album_pool_id,))
        row = cursor.fetchone()
        cursor.close()
        return row


def _wait_status(client, task_id, headers, timeout=10):
    """轮询任务状态直到 done/failed，超时抛错"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f'/api/album/lyric/recognize/status/{task_id}', headers=headers).get_json()
        assert r['code'] == 200, r
        last = r['data']
        if last['status'] in ('done', 'failed'):
            return last
        time.sleep(0.1)
    raise AssertionError(f'识别任务超时，最后状态={last}')


# ==================== 触发权限 / 校验 ====================

@pytest.mark.realdata
def test_recognize_non_admin_forbidden(client, test_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=test_user['headers']).get_json()
    assert r['code'] == 403, r


@pytest.mark.realdata
def test_recognize_pool_not_exists(client, admin_user):
    r = client.post('/api/album/lyric/recognize/999999', headers=admin_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_recognize_no_mp3_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)  # mp3_url 为空
    r = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r
    assert '无整轨 MP3' in r['msg']


@pytest.mark.realdata
def test_recognize_mp3_file_missing_rejected(client, admin_user):
    # mp3_url 指向磁盘上不存在的文件
    pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}not_exist_xxx.mp3')
    r = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r
    assert '文件不存在' in r['msg']


# ==================== 任务链路（fake transcribe） ====================

@pytest.mark.realdata
def test_recognize_done_persists_lyric(client, admin_user, fake_transcribe, monkeypatch):
    # 锁死服务器端无 DeepSeek key → 走 whisper 草稿路径（正确性不依赖本机 config）
    monkeypatch.setattr('backend.config.DEEPSEEK_API_KEY', '')
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        r = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=admin_user['headers']).get_json()
        assert r['code'] == 200, r
        assert r['data']['task_id']
        assert r['data']['album_name'] == 'AI识别测试专辑'

        status = _wait_status(client, r['data']['task_id'], admin_user['headers'])
        assert status['status'] == 'done', status
        assert status['saved'] is True
        assert status['item_count'] == 1, status  # 两条幻觉噪音被 P0 过滤，仅 1 条正常歌词
        assert status['lyric_lines'] == 1
        assert status['segment_count'] == 3
        assert status['rtf'] is not None
        assert status['corrected'] is False  # 无 key → 草稿落库

        # P0 生效：繁体转简体 + 幻觉噪音滤除，落库只含「某夜你离开」
        row = _get_lyric(client, pool_id)
        assert row['lyric_text'] == '00:00 某夜你离开'
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@pytest.mark.realdata
def test_recognize_with_deepseek_correction(client, admin_user, fake_transcribe, monkeypatch):
    """P2 接入验证：配置 key + 校正返回 → done + corrected=True + 落库校正文本"""
    monkeypatch.setattr('backend.config.DEEPSEEK_API_KEY', 'test-key')

    # 替换 lyric_ai 命名空间中的 correct_lyric（固定校正结果：difflib 保时间戳回 00:00）
    import backend.api.lyric_ai as mod

    def _fake_correct(lyric_text, api_key=None, timeout=60):
        return '00:00 某夜你离开（已校正）', {
            'corrected': True,
            'anchor_lines': 1,
            'corrected_lines': 1,
            'lyric_lines': 1,
        }

    monkeypatch.setattr(mod, 'correct_lyric', _fake_correct)
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        r = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=admin_user['headers']).get_json()
        assert r['code'] == 200, r

        status = _wait_status(client, r['data']['task_id'], admin_user['headers'])
        assert status['status'] == 'done', status
        assert status['corrected'] is True
        assert status['anchor_lines'] == 1
        assert status['corrected_lines'] == 1

        # 落库的是校正后文本
        row = _get_lyric(client, pool_id)
        assert row['lyric_text'] == '00:00 某夜你离开（已校正）'
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@pytest.mark.realdata
def test_recognize_repeat_creates_new_task(client, admin_user, fake_transcribe):
    # 幂等：重复触发视为新任务（README：内存任务表不持久化）
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        r1 = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=admin_user['headers']).get_json()
        r2 = client.post(f'/api/album/lyric/recognize/{pool_id}', headers=admin_user['headers']).get_json()
        assert r1['code'] == 200 and r2['code'] == 200
        assert r1['data']['task_id'] != r2['data']['task_id']
        _wait_status(client, r2['data']['task_id'], admin_user['headers'])
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


# ==================== 状态轮询 ====================

@pytest.mark.realdata
def test_status_not_found(client, admin_user):
    r = client.get('/api/album/lyric/recognize/status/nonexistent_task', headers=admin_user['headers']).get_json()
    assert r['code'] == 404, r


# ==================== 真实识别冒烟（验证 v0.8.1 P0 识别器端到端） ====================

@pytest.mark.realdata
def test_real_recognizer_pipeline_smoke(client, admin_user):
    """真模型冒烟：找库中带整轨 mp3 且文件存在的池专辑，限前 30s 转写（VAD 关 + 过滤 + 繁转简）
    验证识别器端到端不崩 + 产出全简体 + 无幻觉噪音；无数据则 skip
    """
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, album_name, mp3_url FROM album_pool WHERE mp3_url IS NOT NULL AND mp3_url != '' LIMIT 5")
        rows = cursor.fetchall()
        cursor.close()
    pool = audio_path = None
    for row in rows:
        p = _resolve_audio_path(row['mp3_url'])
        if p and os.path.exists(p):
            pool, audio_path = row, p
            break
    if not pool:
        pytest.skip('库中无带整轨 mp3 文件的池专辑，跳过真实识别冒烟')

    # VAD 关（P0 默认）+ 限前 30s（约 6s CPU）+ 强制中文
    segments, info, metrics = transcribe(audio_path, limit_secs=30, language='zh')
    items = segments_to_items(segments)

    assert metrics['rtf'] > 0, metrics
    assert all(0 <= it['time'] < 30 for it in items), items  # 时间戳在 limit 范围内
    for it in items:
        # 已转简体（to_simplified 对简体输入幂等）
        assert it['text'] == to_simplified(it['text']), it
        # 幻觉噪音（制作信息/字幕/器乐名）已滤除
        assert not is_hallucination(it['text']), it
