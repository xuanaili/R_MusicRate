# MusicRate\backend\tests\test_album_auto_recognize_realdata.py 专辑添加自动触发 AI 识别 realdata 集成测试（v0.8.1 增补，依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_album_auto_recognize_realdata.py
# 覆盖：
#   - 管理员 + 带整轨 mp3_url → album/add 自动启动识别任务，响应 data.recognize_task_id 非空 + 参数正确
#   - 管理员 + 无 mp3_url → 不自动触发（无 recognize_task_id）
#   - 非管理员 + 带 mp3_url → 不自动触发（识别仅管理员可用）
#   - 自动触发抛异常 → 不影响专辑添加成功（recognize_task_id 置空）
# 说明：start_recognize_task 被 monkeypatch 替换（避免真起 faster-whisper 线程读空 mp3）；album.py
#       add 路由在函数体内 `from backend.api.lyric_ai import start_recognize_task` 动态导入，monkeypatch
#       模块属性后动态 import 取到的即补丁版本
import time

import pytest

from backend import create_app
from backend.utils.db import get_db


@pytest.fixture(scope='module')
def client():
    # 与 test_lyric_ai_realdata 同款：不用 `with app.test_client()`（preserve_context 跨请求复用 g 会二次 close）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_auto_ai_{int(time.time() * 1000)}'
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


def _add_album(client, headers, mp3_url='', album_name=None):
    """调用 album/add 添加一张带单曲的专辑（name 含时间戳避免跨用例 409 重名），返回响应 json"""
    return client.post('/api/album/add', json={
        'album_name': album_name or f'自动识别测试{int(time.time() * 1000)}',
        'cover_img': '',
        'singer': '测试歌手',
        'mp3_duration': 6 if mp3_url else 0,
        'mp3_url': mp3_url,
        'release_year': 2026,
        'album_intro': '',
        'duration_type': 'LP',
        'tracks': ['单曲一'],
        'tracks_time': [0],
    }, headers=headers).get_json()


# ==================== 自动触发 ====================

@pytest.mark.realdata
def test_admin_add_with_mp3_auto_triggers(client, admin_user, monkeypatch):
    """管理员添加带整轨 mp3 的专辑 → 自动启动识别任务，响应带 recognize_task_id + 参数正确"""
    calls = []

    def _fake_start(app, album_pool_id, album_name, user_id):
        calls.append({'album_pool_id': album_pool_id, 'album_name': album_name, 'user_id': user_id})
        return 'fake_task_auto'

    import backend.api.lyric_ai as lyric_ai_mod
    monkeypatch.setattr(lyric_ai_mod, 'start_recognize_task', _fake_start)

    r = _add_album(client, admin_user['headers'], mp3_url='http://localhost:5000/tracks/auto_x.mp3')
    assert r['code'] == 200, r
    data = r['data']
    assert data['recognize_task_id'] == 'fake_task_auto'
    assert data['source_pool_id']  # 新池专辑 id 已生成
    # 自动触发参数正确：池 id + 专辑名 + 管理员 user_id
    assert calls and len(calls) == 1
    assert calls[-1]['album_pool_id'] == data['source_pool_id']
    assert calls[-1]['album_name'] == data['album_name']
    assert calls[-1]['user_id'] == admin_user['user_id']


@pytest.mark.realdata
def test_admin_add_without_mp3_no_auto(client, admin_user, monkeypatch):
    """管理员添加无 mp3 的专辑 → 不自动触发（无整轨可识别）"""
    called = []

    def _should_not_start(*args, **kwargs):
        called.append(args)

    import backend.api.lyric_ai as lyric_ai_mod
    monkeypatch.setattr(lyric_ai_mod, 'start_recognize_task', _should_not_start)

    r = _add_album(client, admin_user['headers'], mp3_url='')
    assert r['code'] == 200, r
    assert r['data'].get('recognize_task_id') in (None, '')
    assert called == [], '无 mp3 不应自动触发识别'


@pytest.mark.realdata
def test_non_admin_add_with_mp3_no_auto(client, test_user, monkeypatch):
    """非管理员添加带 mp3 的专辑 → 不自动触发（AI 识别仅管理员可用）"""
    called = []

    def _should_not_start(*args, **kwargs):
        called.append(args)

    import backend.api.lyric_ai as lyric_ai_mod
    monkeypatch.setattr(lyric_ai_mod, 'start_recognize_task', _should_not_start)

    r = _add_album(client, test_user['headers'], mp3_url='http://localhost:5000/tracks/auto_y.mp3')
    assert r['code'] == 200, r
    assert r['data'].get('recognize_task_id') in (None, '')
    assert called == [], '非管理员不应自动触发识别'


@pytest.mark.realdata
def test_admin_add_auto_trigger_exception_keeps_album(client, admin_user, monkeypatch):
    """自动触发抛异常 → 专辑仍添加成功，recognize_task_id 置空（识别失败不影响添加）"""
    import backend.api.lyric_ai as lyric_ai_mod

    def _boom(*args, **kwargs):
        raise RuntimeError('测试自动触发失败')

    monkeypatch.setattr(lyric_ai_mod, 'start_recognize_task', _boom)

    r = _add_album(client, admin_user['headers'], mp3_url='http://localhost:5000/tracks/auto_z.mp3')
    assert r['code'] == 200, r
    assert r['data']['source_pool_id']
    assert r['data'].get('recognize_task_id') in (None, '')
