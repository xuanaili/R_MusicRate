# MusicRate\backend\tests\test_tempo_realdata.py BPM 节奏分析异步任务 realdata 集成测试（v0.8.1 P4，依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_tempo_realdata.py
# 覆盖：
#   - 触发权限/校验：非管理员 403、池不存在 404、无 mp3 400、mp3 文件缺失 400
#   - 任务链路（fake analyze_tempo，避免真 librosa 读空文件）：触发 → queued → 线程跑 → done → album_tempo 缓存落库
#   - 单曲边界回退：池专辑 tracks_time 为空 → 回退触发用户私有副本（albums_{user_id}.source_pool_id）；非空则优先池
#   - 幂等：重复触发视为新任务；状态轮询：不存在的 task_id 404；分析异常 → failed
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
    # 与 test_lyric_ai_realdata 同款：不用 `with app.test_client()`（preserve_context 跨请求复用 g 会二次 close）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture(scope='module', autouse=True)
def ensure_album_tempo_table(client):
    """create_app() 不跑 init_base_tables（仅 run.py 启动时跑）→ 模块级确保 album_tempo 表存在（幂等 CREATE）"""
    from backend.utils.db import create_album_tempo
    with client.application.app_context():
        create_album_tempo()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_tempo_{int(time.time() * 1000)}'
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
def fake_analyze_tempo(monkeypatch):
    """替换 tempo_ai.analyze_tempo 为固定节奏结果（避免真 librosa 读空 mp3 文件），记录调用参数供断言"""
    calls = []

    def _fake(audio_path, tracks_time=None):
        calls.append({'audio_path': audio_path, 'tracks_time': tracks_time})
        return {
            'track_tempos': [120.0, 90.0],
            'avg_bpm': 105.0,
            'min_bpm': 90.0,
            'max_bpm': 120.0,
            'track_durations': [3.0, 3.0],
        }

    import backend.api.tempo_ai as mod
    monkeypatch.setattr(mod, 'analyze_tempo', _fake)
    return calls


def _insert_pool_album(client, mp3_url=None, tracks_time='[]'):
    """插入 album_pool 模板，返回 id
    线上库 album_pool.tracks_time 列 DDL 漂移无默认值，必须显式传（与 lyric realdata 同款）
    """
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO album_pool (album_name, singer, release_year, create_user, tracks_time, mp3_url, mp3_duration)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', ('节奏分析测试专辑', '测试歌手', 2026, 0, tracks_time, mp3_url, 6 if mp3_url else 0))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _insert_user_album(client, user_id, pool_id, tracks_time='[10, 20]'):
    """在 albums_{user_id} 插入一条私有副本（source_pool_id 关联池专辑），tracks_time 用于回退路径测试"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            f'INSERT INTO `{table}` (album_name, singer, release_year, source_pool_id, tracks_time) '
            'VALUES (%s, %s, %s, %s, %s)',
            ('测试用户专辑', '测试歌手', 2026, pool_id, tracks_time),
        )
        db.commit()
        cursor.close()


def _make_mp3_file(client):
    """在 AUDIO_UPLOAD_FOLDER 创建真实存在的空 .mp3 文件（内容无关，fake analyze_tempo 不读），返回 (filename, path)"""
    fd, path = tempfile.mkstemp(suffix='.mp3', dir=AUDIO_UPLOAD_FOLDER)
    os.close(fd)
    return os.path.basename(path), path


def _get_tempo(client, album_pool_id):
    """读取 album_tempo 缓存行，返回 tempo JSON dict（无则 None）"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT tempo FROM album_tempo WHERE album_pool_id = %s', (album_pool_id,))
        row = cursor.fetchone()
        cursor.close()
        return json.loads(row['tempo']) if row else None


def _insert_tempo_cache(client, album_pool_id, tempo_dict):
    """直接插入 album_tempo 缓存行（ensure ready 短路测试用）"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO album_tempo (album_pool_id, tempo) VALUES (%s, %s)',
            (album_pool_id, json.dumps(tempo_dict, ensure_ascii=False)),
        )
        db.commit()
        cursor.close()


def _mock_start_tempo_task(monkeypatch):
    """替换 tempo_ai.start_tempo_task 记录调用（避免真起后台线程），返回 calls 列表"""
    import backend.api.tempo_ai as mod
    calls = []

    def fake(app, album_pool_id, album_name, user_id):
        calls.append({'album_pool_id': album_pool_id, 'album_name': album_name, 'user_id': user_id})
        return 'fake-ensure-task'

    monkeypatch.setattr(mod, 'start_tempo_task', fake)
    return calls


def _wait_status(client, task_id, headers, timeout=10):
    """轮询任务状态直到 done/failed，超时抛错"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f'/api/ai/tempo/status/{task_id}', headers=headers).get_json()
        assert r['code'] == 200, r
        last = r['data']
        if last['status'] in ('done', 'failed'):
            return last
        time.sleep(0.1)
    raise AssertionError(f'节奏分析任务超时，最后状态={last}')


# ==================== 触发权限 / 校验 ====================

@pytest.mark.realdata
def test_tempo_analyze_non_admin_forbidden(client, test_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=test_user['headers']).get_json()
    assert r['code'] == 403, r


@pytest.mark.realdata
def test_tempo_analyze_pool_not_exists(client, admin_user):
    r = client.post('/api/ai/tempo/analyze/999999', headers=admin_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_tempo_analyze_no_mp3_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)  # mp3_url 为空
    r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r
    assert '无整轨 MP3' in r['msg']


@pytest.mark.realdata
def test_tempo_analyze_mp3_file_missing_rejected(client, admin_user):
    pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}not_exist_xxx.mp3')
    r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r
    assert '文件不存在' in r['msg']


# ==================== BPM 预触发 ensure（v0.8.3 P1：任意登录用户 get-or-trigger） ====================

@pytest.mark.realdata
def test_tempo_ensure_pool_not_found(client, test_user):
    r = client.post('/api/ai/tempo/ensure/999999', headers=test_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_tempo_ensure_any_user_allowed(client, test_user, monkeypatch):
    """ensure 任意登录用户可调用（非管理员也 200，不再校验 is_admin）"""
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        _mock_start_tempo_task(monkeypatch)
        r = client.post(f'/api/ai/tempo/ensure/{pool_id}', headers=test_user['headers']).get_json()
        assert r['code'] == 200, r
        assert r['data']['analyzing'] is True
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.realdata
def test_tempo_ensure_no_mp3_reports_has_mp3_false(client, test_user):
    """池无整轨 mp3 → ready:false + has_mp3:false（前端忽略，不 400）"""
    pool_id = _insert_pool_album(client)  # mp3_url 为空
    r = client.post(f'/api/ai/tempo/ensure/{pool_id}', headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['ready'] is False
    assert r['data']['has_mp3'] is False


@pytest.mark.realdata
def test_tempo_ensure_cached_ready(client, test_user, monkeypatch):
    """album_tempo 已有缓存 → ready:true，不启动新任务"""
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        _insert_tempo_cache(client, pool_id, {
            'track_tempos': [120.0], 'avg_bpm': 120.0, 'min_bpm': 120.0, 'max_bpm': 120.0,
        })
        calls = _mock_start_tempo_task(monkeypatch)
        r = client.post(f'/api/ai/tempo/ensure/{pool_id}', headers=test_user['headers']).get_json()
        assert r['code'] == 200, r
        assert r['data']['ready'] is True
        assert r['data'].get('analyzing') is None
        assert calls == [], '已有缓存仍启动任务！'
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.realdata
def test_tempo_ensure_starts_task(client, test_user, monkeypatch):
    """tempo 缺失 + 有整轨 mp3 + 无活跃任务 → 启动任务，返回 analyzing:true + task_id"""
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        calls = _mock_start_tempo_task(monkeypatch)
        r = client.post(f'/api/ai/tempo/ensure/{pool_id}', headers=test_user['headers']).get_json()
        assert r['code'] == 200, r
        assert r['data']['ready'] is False
        assert r['data']['has_mp3'] is True
        assert r['data']['analyzing'] is True
        assert r['data']['task_id'] == 'fake-ensure-task'
        assert len(calls) == 1 and calls[0]['album_pool_id'] == pool_id
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.realdata
def test_tempo_ensure_active_task_reused(client, test_user, monkeypatch):
    """已有活跃 tempo 任务 → 复用其 task_id，不重复启动（find_active 防抖）"""
    filename, path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        tasks.create(
            task_id='active-ensure-tempo',
            kind='tempo', album_pool_id=pool_id, album_name='节奏分析测试专辑',
            user_id=test_user['user_id'],
            status='running', message='预置活跃任务', progress=50, created_at=None,
        )
        calls = _mock_start_tempo_task(monkeypatch)
        r = client.post(f'/api/ai/tempo/ensure/{pool_id}', headers=test_user['headers']).get_json()
        assert r['code'] == 200, r
        assert r['data']['ready'] is False
        assert r['data']['analyzing'] is True
        assert r['data']['task_id'] == 'active-ensure-tempo'
        assert calls == [], '已有活跃任务仍重复启动！'
    finally:
        if os.path.exists(path):
            os.remove(path)


# ==================== 任务链路（fake analyze_tempo） ====================

@pytest.mark.realdata
def test_tempo_analyze_done_persists_cache(client, admin_user, fake_analyze_tempo):
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
        assert r['code'] == 200, r
        assert r['data']['task_id']
        assert r['data']['album_name'] == '节奏分析测试专辑'

        status = _wait_status(client, r['data']['task_id'], admin_user['headers'])
        assert status['status'] == 'done', status
        assert status['saved'] is True
        assert status['segments'] == 2
        assert status['avg_bpm'] == 105.0
        assert status['min_bpm'] == 90.0
        assert status['max_bpm'] == 120.0
        assert status['track_tempos'] == [120.0, 90.0]
        assert status['progress'] == 100

        # album_tempo 缓存落库（upsert）
        cached = _get_tempo(client, pool_id)
        assert cached['track_tempos'] == [120.0, 90.0]
        assert cached['avg_bpm'] == 105.0
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@pytest.mark.realdata
def test_tempo_analyze_pool_tracks_time_priority(client, admin_user, fake_analyze_tempo):
    """池专辑 tracks_time 非空 → 直接用池的，不回退用户副本"""
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}', tracks_time='[30, 40]')
        _insert_user_album(client, admin_user['user_id'], pool_id, tracks_time='[10, 20]')
        r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
        assert r['code'] == 200, r
        _wait_status(client, r['data']['task_id'], admin_user['headers'])
        assert fake_analyze_tempo[-1]['tracks_time'] == [30, 40]
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@pytest.mark.realdata
def test_tempo_analyze_fallback_user_copy(client, admin_user, fake_analyze_tempo):
    """池专辑 tracks_time 为空 → 回退触发用户私有副本的 tracks_time"""
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}', tracks_time='[]')
        _insert_user_album(client, admin_user['user_id'], pool_id, tracks_time='[10, 20]')
        r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
        assert r['code'] == 200, r
        _wait_status(client, r['data']['task_id'], admin_user['headers'])
        assert fake_analyze_tempo[-1]['tracks_time'] == [10, 20]
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@pytest.mark.realdata
def test_tempo_analyze_failed_status(client, admin_user, monkeypatch):
    """analyze_tempo 抛异常 → 任务 failed（错误路径不落库）"""
    import backend.api.tempo_ai as mod

    def _boom(audio_path, tracks_time=None):
        raise RuntimeError('测试分析失败')

    monkeypatch.setattr(mod, 'analyze_tempo', _boom)
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        r = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
        assert r['code'] == 200, r
        status = _wait_status(client, r['data']['task_id'], admin_user['headers'])
        assert status['status'] == 'failed', status
        assert '测试分析失败' in status['message']
        assert _get_tempo(client, pool_id) is None  # 失败不落库
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@pytest.mark.realdata
def test_tempo_analyze_repeat_creates_new_task(client, admin_user, fake_analyze_tempo):
    # 幂等：重复触发视为新任务（README：内存任务表不持久化）
    filename, audio_path = _make_mp3_file(client)
    try:
        pool_id = _insert_pool_album(client, mp3_url=f'{AUDIO_BASE_URL}{filename}')
        r1 = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
        r2 = client.post(f'/api/ai/tempo/analyze/{pool_id}', headers=admin_user['headers']).get_json()
        assert r1['code'] == 200 and r2['code'] == 200
        assert r1['data']['task_id'] != r2['data']['task_id']
        _wait_status(client, r2['data']['task_id'], admin_user['headers'])
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


# ==================== 状态轮询 ====================

@pytest.mark.realdata
def test_tempo_status_not_found(client, admin_user):
    r = client.get('/api/ai/tempo/status/nonexistent_task', headers=admin_user['headers']).get_json()
    assert r['code'] == 404, r


# ==================== 直读 album_tempo 缓存（v0.9 P0，GET /api/ai/tempo/get） ====================

@pytest.mark.realdata
def test_tempo_get_pool_not_found(client, test_user):
    r = client.get('/api/ai/tempo/get/999999', headers=test_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_tempo_get_no_cache_ready_false(client, test_user):
    pool_id = _insert_pool_album(client)  # 无 mp3 也无缓存
    r = client.get(f'/api/ai/tempo/get/{pool_id}', headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['ready'] is False


@pytest.mark.realdata
def test_tempo_get_cached_returns_tempo(client, test_user):
    pool_id = _insert_pool_album(client)
    _insert_tempo_cache(client, pool_id, {
        'track_tempos': [120.0, 90.0], 'avg_bpm': 105.0, 'min_bpm': 90.0, 'max_bpm': 120.0,
    })
    r = client.get(f'/api/ai/tempo/get/{pool_id}', headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['ready'] is True
    assert r['data']['tempo']['avg_bpm'] == 105.0
    assert r['data']['tempo']['track_tempos'] == [120.0, 90.0]


# ==================== 真实 librosa 冒烟（验证正式管线端到端） ====================

@pytest.mark.realdata
def test_real_tempo_pipeline_smoke(client, admin_user):
    """真实冒烟：找库中带整轨 mp3 且文件存在的池专辑，走正式异步接口（真 librosa 后台测拍）
    验证 analyze → 后台线程 analyze_tempo → done → album_tempo 缓存全链路；无数据则 skip
    """
    from backend.api.tempo_ai import _resolve_audio_path
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, album_name, mp3_url FROM album_pool WHERE mp3_url IS NOT NULL AND mp3_url != '' LIMIT 5")
        rows = cursor.fetchall()
        cursor.close()
    pool = None
    for row in rows:
        if _resolve_audio_path(row['mp3_url']) and os.path.exists(_resolve_audio_path(row['mp3_url'])):
            pool = row
            break
    if not pool:
        pytest.skip('库中无带整轨 mp3 文件的池专辑，跳过真实节奏分析冒烟')

    r = client.post(f"/api/ai/tempo/analyze/{pool['id']}", headers=admin_user['headers']).get_json()
    assert r['code'] == 200, r

    status = _wait_status(client, r['data']['task_id'], admin_user['headers'], timeout=120)
    assert status['status'] == 'done', status
    assert status['saved'] is True
    assert status['segments'] >= 1
    assert status['avg_bpm'] > 0, status  # 真 librosa 测回有效 BPM
    assert status['max_bpm'] >= status['min_bpm'] >= 0

    cached = _get_tempo(client, pool['id'])
    assert cached and cached['avg_bpm'] == status['avg_bpm']
