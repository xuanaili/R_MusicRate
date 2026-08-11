# MusicRate\backend\tests\test_lyric_api_realdata.py 歌词接口 realdata 集成测试（v0.8 P0-B，依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_lyric_api_realdata.py
# 覆盖：save 权限收紧（非管理员 403）/ 校验规范化落库 / 补专辑存在性校验；
#       upload 整轨 LRC（utf-8 与 gbk 回退、翻译文件、超限拒绝、扩展名拒绝）；
#       fetch_auto 已移除（404）
import io
import time

import pytest

from backend import create_app
from backend.utils.db import get_db


@pytest.fixture(scope='module')
def client():
    # 与 test_user_stats_realdata.py 同款模式：不用 with test_client()
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_lyric_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _promote_admin(client, user_id):
    """把测试用户提升为管理员（直改 users.is_admin，隔离于默认 admin）"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = %s', (user_id,))
        db.commit()
        cursor.close()


@pytest.fixture()
def admin_user(client, test_user):
    """管理员测试用户（在 test_user 基础上提升权限）"""
    _promote_admin(client, test_user['user_id'])
    return test_user


def _insert_pool_album(client):
    """插入一张 album_pool 模板，返回 id
    注意：线上库 album_pool.tracks_time 列存在但 db.py DDL 未收录（DDL 漂移，无默认值），必须显式插入
    """
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO album_pool (album_name, singer, release_year, create_user, tracks_time)
            VALUES (%s, %s, %s, %s, %s)
        ''', ('歌词测试专辑', '测试歌手', 2026, 0, '[]'))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _get_lyric(client, album_pool_id):
    """直查 album_lyric 表返回当前存储内容"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT lyric_text, lyric_translate FROM album_lyric WHERE album_pool_id = %s', (album_pool_id,))
        row = cursor.fetchone()
        cursor.close()
        return row


def _upload(client, url, filename, content, headers, extra=None):
    """multipart 上传辅助：content 为 bytes（utf-8 默认），extra 为 {字段名: (bytes, 文件名)}"""
    data = {'lrc_file': (io.BytesIO(content), filename)}
    for key, (b, fn) in (extra or {}).items():
        data[key] = (io.BytesIO(b), fn)
    return client.post(url, data=data, headers=headers, content_type='multipart/form-data').get_json()


# ==================== save 接口 ====================

@pytest.mark.realdata
def test_save_non_admin_forbidden(client, test_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/album/lyric/save/{pool_id}', json={'lyric_text': '00:00 歌词'}, headers=test_user['headers']).get_json()
    assert r['code'] == 403, r


@pytest.mark.realdata
def test_save_admin_normalizes_and_persists(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/album/lyric/save/{pool_id}', json={
        'lyric_text': '[00:00.00]第一句\n[00:05.50]第二句\n[00:10]作词：方文山',
        'lyric_translate': '{"CN": "00:00 第一句翻译"}'
    }, headers=admin_user['headers']).get_json()
    assert r['code'] == 200, r
    # 规范化落库：作词行过滤、10.50 → 10.5
    assert r['data']['lyric_text'] == '00:00 第一句\n00:05.5 第二句'
    assert r['data']['lyric_text_length'] == len(r['data']['lyric_text'])
    assert r['data']['has_translate'] is True
    row = _get_lyric(client, pool_id)
    assert row['lyric_text'] == '00:00 第一句\n00:05.5 第二句'
    assert row['lyric_translate'] == '{"CN": "00:00 第一句翻译"}'


@pytest.mark.realdata
def test_save_album_not_exists(client, admin_user):
    r = client.post('/api/album/lyric/save/999999', json={'lyric_text': '00:00 歌词'}, headers=admin_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_save_invalid_lyric_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/album/lyric/save/{pool_id}', json={'lyric_text': '没有时间的纯文字'}, headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r
    assert '有效' in r['msg']


@pytest.mark.realdata
def test_save_invalid_translate_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/album/lyric/save/{pool_id}', json={
        'lyric_text': '00:00 歌词',
        'lyric_translate': '{"CN": "不是歌词"}'
    }, headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r


@pytest.mark.realdata
def test_save_empty_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = client.post(f'/api/album/lyric/save/{pool_id}', json={'lyric_text': ''}, headers=admin_user['headers']).get_json()
    assert r['code'] == 400, r
    assert '不能为空' in r['msg']


# ==================== upload 接口 ====================

@pytest.mark.realdata
def test_upload_non_admin_forbidden(client, test_user):
    pool_id = _insert_pool_album(client)
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.lrc', '[00:00.00]歌词'.encode('utf-8'), test_user['headers'])
    assert r['code'] == 403, r


@pytest.mark.realdata
def test_upload_lrc_normalized(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.lrc',
                '[ti:七里香]\n[00:00.00]第一句\n[00:05.123]第二句\n[00:10]作词：方文山'.encode('utf-8'),
                admin_user['headers'])
    assert r['code'] == 200, r
    assert r['data']['lyric_text'] == '00:00 第一句\n00:05.1 第二句'
    assert r['data']['has_translate'] is False
    row = _get_lyric(client, pool_id)
    assert row['lyric_text'] == '00:00 第一句\n00:05.1 第二句'


@pytest.mark.realdata
def test_upload_gbk_fallback(client, admin_user):
    pool_id = _insert_pool_album(client)
    gbk_bytes = '[00:00.00]中文歌词\n[00:05.00]第二句'.encode('gbk')
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.lrc', gbk_bytes, admin_user['headers'])
    assert r['code'] == 200, r
    assert r['data']['lyric_text'] == '00:00 中文歌词\n00:05 第二句'


@pytest.mark.realdata
def test_upload_with_translate_file(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.lrc', '[00:00.00]第一句'.encode('utf-8'),
                admin_user['headers'],
                extra={'translate_file': (b'[00:00.00]first', 'trans.lrc')})
    assert r['code'] == 200, r
    assert r['data']['has_translate'] is True
    row = _get_lyric(client, pool_id)
    assert row['lyric_translate'] == '{"CN": "00:00 first"}'


@pytest.mark.realdata
def test_upload_wrong_ext_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.txt', '[00:00.00]歌词'.encode('utf-8'), admin_user['headers'])
    assert r['code'] == 400, r
    assert '.lrc' in r['msg']


@pytest.mark.realdata
def test_upload_too_large_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)
    big = b'[00:00.00]x\n' * (1024 * 1024 // 12 + 10000)  # 远超 1MB
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.lrc', big, admin_user['headers'])
    assert r['code'] == 400, r
    assert '过大' in r['msg']


@pytest.mark.realdata
def test_upload_invalid_lyric_rejected(client, admin_user):
    pool_id = _insert_pool_album(client)
    r = _upload(client, f'/api/album/lyric/upload/{pool_id}', 'song.lrc', '纯文字没有时间戳'.encode('utf-8'), admin_user['headers'])
    assert r['code'] == 400, r


# ==================== get 接口 + QQ 移除 ====================

@pytest.mark.realdata
def test_get_returns_saved(client, admin_user):
    pool_id = _insert_pool_album(client)
    client.post(f'/api/album/lyric/save/{pool_id}', json={'lyric_text': '00:03 歌词'}, headers=admin_user['headers'])
    r = client.get(f'/api/album/lyric/get/{pool_id}', headers=admin_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['lyric_text'] == '00:03 歌词'


@pytest.mark.realdata
def test_fetch_auto_removed(client, test_user):
    # v0.8 决策：QQ 音乐自动获取彻底移除 → 路由应 404
    r = client.post('/api/lyric/fetch_auto', json={'song_name': 'test'}, headers=test_user['headers'])
    assert r.status_code == 404
