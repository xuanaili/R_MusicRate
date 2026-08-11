# MusicRate\backend\tests\test_touch_last_listened_realdata.py 最近收听时间 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 覆盖：touch 接口为「自动切下一张专辑」场景持久化 last_listened（创建/更新）；专辑不存在返回 404
# 背景：前端播放完自动跳下一张专辑时需对新专辑调 touch，本测试锁定该接口的 DB 行为契约
import time
from datetime import datetime, timedelta

import pytest

from backend import create_app
from backend.utils.db import get_album_table_name, get_db


@pytest.fixture(scope='module')
def client():
    # 与 test_listening_progress_realdata.py 同款模式：不用 with test_client()（preserve_context 会跨请求复用
    # app context/g，导致 close_db 对已关闭连接二次 close 抛 "Already closed"）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_touch_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _insert_user_album(client, user_id):
    """向用户专辑表插入一行测试专辑，返回 id（新表默认已含 last_listened 列，值为 NULL）"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'''
            INSERT INTO `{table}` (album_name, singer, release_year)
            VALUES (%s, %s, %s)
        ''', ('最近收听测试专辑', '测试歌手', 2026))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _set_last_listened(client, user_id, album_id, dt):
    """直接改 DB 里的 last_listened 为指定时间，用于验证 touch 会覆盖旧值"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'UPDATE `{table}` SET last_listened = %s WHERE id = %s', (dt, album_id))
        db.commit()
        cursor.close()


def _get_last_listened(client, user_id, album_id):
    """读取 DB 中的 last_listened 值"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'SELECT last_listened FROM `{table}` WHERE id = %s', (album_id,))
        row = cursor.fetchone()
        cursor.close()
        return row['last_listened'] if row else None


@pytest.mark.realdata
def test_touch_creates_last_listened_for_new_album(client, test_user):
    # 新专辑 last_listened 初始为 NULL → touch 后应被赋值为当前时间（自动切下一张专辑场景）
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    assert _get_last_listened(client, user_id, album_id) is None

    r = client.post(f'/api/album/listening/touch/{album_id}', json={}, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['album_id'] == album_id

    db_val = _get_last_listened(client, user_id, album_id)
    assert db_val is not None, 'touch 后 last_listened 仍为 NULL'
    # 校验写入的是「最近」时间（距 now 不超过 1 分钟）
    assert abs((datetime.now() - db_val).total_seconds()) < 60


@pytest.mark.realdata
def test_touch_updates_existing_last_listened(client, test_user):
    # 已收听过（有旧时间）→ 再次 touch 应更新为当前时间（自动切到已听过的专辑场景）
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    old_time = datetime.now() - timedelta(days=3)
    _set_last_listened(client, user_id, album_id, old_time)

    r = client.post(f'/api/album/listening/touch/{album_id}', json={}, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r

    db_val = _get_last_listened(client, user_id, album_id)
    assert abs((datetime.now() - db_val).total_seconds()) < 60
    assert db_val > old_time, 'touch 后 last_listened 未比旧时间更新'


@pytest.mark.realdata
def test_touch_returns_404_for_missing_album(client, test_user):
    # 专辑不存在（如来源被删）→ 返回 404 而非 500
    r = client.post('/api/album/listening/touch/99999999', json={}, headers=test_user['headers']).get_json()
    assert r['code'] == 404, r
