# MusicRate\backend\tests\test_listening_progress_realdata.py 听取进度续播 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 覆盖：pause 接口持久化 listening_progress；超整轨时长 clamp；负进度归零
import time

import pytest

from backend import create_app
from backend.api.listening import PLAYING_TIMER_CACHE
from backend.utils.db import get_album_table_name, get_db


@pytest.fixture(scope='module')
def client():
    # 与 test_user_stats_realdata.py 同款模式：不用 with test_client()（preserve_context 会跨请求复用
    # app context/g，导致 close_db 对已关闭连接二次 close 抛 "Already closed"）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_progress_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _insert_pool_album(client, mp3_duration):
    """插入一张 album_pool 模板（带整轨时长），返回 id"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO album_pool (album_name, singer, release_year, create_user, mp3_duration, tracks_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', ('进度测试专辑', '测试歌手', 2026, 0, mp3_duration, '[]'))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _insert_user_album(client, user_id, source_pool_id=None):
    """向用户专辑表插入一行测试专辑，返回 id"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'''
            INSERT INTO `{table}` (album_name, singer, release_year, source_pool_id, listening_duration)
            VALUES (%s, %s, %s, %s, %s)
        ''', ('进度测试专辑', '测试歌手', 2026, source_pool_id, 0.0))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _get_progress(client, user_id, album_id):
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'SELECT listening_progress FROM `{table}` WHERE id = %s', (album_id,))
        row = cursor.fetchone()
        cursor.close()
        return row['listening_progress'] if row else None


def _seed_and_pause(client, user_id, album_id, headers, progress_seconds):
    """种入内存计时缓存（模拟已播放1秒）并调用 pause 接口，返回响应 JSON"""
    now = time.time()
    PLAYING_TIMER_CACHE[f'{user_id}_{album_id}'] = {'start_timestamp': now - 1, 'origin_duration': 0.0}
    return client.post(
        f'/api/album/listening/pause/{album_id}',
        json={'progress_seconds': progress_seconds},
        headers=headers,
    ).get_json()


@pytest.mark.realdata
def test_pause_persists_progress(client, test_user):
    # 无 album_pool 关联（source_pool_id 为空）→ 跳过 clamp，原样存 1 位小数
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    r = _seed_and_pause(client, user_id, album_id, test_user['headers'], 120.5)
    assert r['code'] == 200, r
    assert r['data']['listening_progress'] == 120.5
    assert _get_progress(client, user_id, album_id) == 120.5


@pytest.mark.realdata
def test_pause_progress_clamped_to_mp3_duration(client, test_user):
    # 关联 album_pool 整轨时长 300s，上报 999 → clamp 到 300
    user_id = test_user['user_id']
    pool_id = _insert_pool_album(client, mp3_duration=300)
    album_id = _insert_user_album(client, user_id, source_pool_id=pool_id)
    r = _seed_and_pause(client, user_id, album_id, test_user['headers'], 999)
    assert r['code'] == 200, r
    assert r['data']['listening_progress'] == 300.0
    assert _get_progress(client, user_id, album_id) == 300.0


@pytest.mark.realdata
def test_pause_negative_progress_resets_to_zero(client, test_user):
    # 负进度 → 归零（从头续播）
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    r = _seed_and_pause(client, user_id, album_id, test_user['headers'], -5)
    assert r['code'] == 200, r
    assert r['data']['listening_progress'] == 0.0
    assert _get_progress(client, user_id, album_id) == 0.0
