# MusicRate\backend\tests\test_level_realdata.py 等级经验 v0.7.1 P0 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 覆盖：四列迁移幂等、pause 加收听经验、每日加分上限、/api/user/info 等级字段
import time

import pytest

from backend import create_app
from backend.api.listening import PLAYING_TIMER_CACHE
from backend.config import MYSQL_CONFIG
from backend.utils.db import ensure_users_xp_columns, get_album_table_name, get_db
from backend.utils.level import compute_level
from backend.utils.user import add_bonus_xp


@pytest.fixture(scope='module', autouse=True)
def _ensure_migration():
    """模块级自动执行：确保 users 表等级经验四列已迁移（自足，不依赖后端已启动过）"""
    app = create_app()
    with app.app_context():
        ensure_users_xp_columns()


@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_level_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _insert_user_album(client, user_id, listening_duration=0.0):
    """向用户专辑表插入一行测试专辑，返回 id"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'''
            INSERT INTO `{table}` (album_name, singer, release_year, listening_duration)
            VALUES (%s, %s, %s, %s)
        ''', ('等级测试专辑', '测试歌手', 2026, listening_duration))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _get_user_row(client, user_id):
    """读 users 表等级经验相关行"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT xp, listening_total, level, bonus_date, bonus_xp_today FROM users WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return row


@pytest.mark.realdata
def test_xp_columns_exist(client):
    """users 表已含等级经验四列（迁移成功）"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
        ''', (MYSQL_CONFIG['db'],))
        cols = {r['COLUMN_NAME'] for r in cursor.fetchall()}
        cursor.close()
    for col in ['xp', 'listening_total', 'bonus_date', 'bonus_xp_today']:
        assert col in cols, f'users 表缺列 {col}'


@pytest.mark.realdata
def test_ensure_xp_columns_idempotent(client):
    """迁移函数幂等：列已存在时再次执行不报错"""
    from backend.utils.db import ensure_users_xp_columns
    app = client.application
    with app.app_context():
        ensure_users_xp_columns()  # 列已存在 → 幂等跳过


@pytest.mark.realdata
def test_pause_gives_xp_and_listening_total(client, test_user):
    """pause 后 users.xp / listening_total 都累加本次播放秒数，返回 xp/level/level_up"""
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    before = _get_user_row(client, user_id)

    now = time.time()
    PLAYING_TIMER_CACHE[f'{user_id}_{album_id}'] = {'start_timestamp': now - 2, 'origin_duration': 0.0}
    r = client.post(
        f'/api/album/listening/pause/{album_id}',
        json={'progress_seconds': 1},
        headers=test_user['headers'],
    ).get_json()
    assert r['code'] == 200, r

    after = _get_user_row(client, user_id)
    # play_seconds ≈ 2（保留1位小数），xp / listening_total 同增
    assert after['xp'] == pytest.approx(before['xp'] + r['data']['this_play_seconds'], abs=0.1)
    assert after['listening_total'] == pytest.approx(before['listening_total'] + r['data']['this_play_seconds'], abs=0.1)
    # 响应含等级反馈字段，且 level 与 xp 推导一致
    assert r['data']['xp'] == after['xp']
    assert r['data']['level'] == compute_level(after['xp'])
    assert r['data']['level_up'] == (r['data']['level'] > compute_level(before['xp']))
    # level 列已同步为推导值（保证登录/详情返回最新等级）
    assert after['level'] == compute_level(after['xp'])


@pytest.mark.realdata
def test_bonus_xp_daily_cap(client, test_user):
    """每日加分上限 100：反复加分到上限后不再累加，实际加分可为部分/0"""
    user_id = test_user['user_id']
    # 5 次听后感 +20 → 前 5 次满 100，第 6 次为 0（add_bonus_xp 需在 app context 内调用）
    gained_list = []
    for _ in range(6):
        with client.application.app_context():
            gained, _, _, _ = add_bonus_xp(user_id, 20)
        gained_list.append(gained)
    assert gained_list[:5] == [20.0] * 5
    assert gained_list[5] == 0.0
    # 当日累计已被记录
    row = _get_user_row(client, user_id)
    assert row['bonus_xp_today'] == 100.0
    assert row['xp'] == 100.0


@pytest.mark.realdata
def test_bonus_xp_partial_when_near_cap(client, test_user):
    """接近上限时部分加分：已加 90 再加 20 → 实际只加 10"""
    user_id = test_user['user_id']
    with client.application.app_context():
        add_bonus_xp(user_id, 90)
        gained, new_xp, _, _ = add_bonus_xp(user_id, 20)
    assert gained == 10.0
    assert new_xp == 100.0


@pytest.mark.realdata
def test_user_info_returns_level_fields(client, test_user):
    """/api/user/info 返回 xp/level/next_level_xp/xp_progress/level_title，且与纯函数一致"""
    user_id = test_user['user_id']
    # 先加一点经验，再查 info
    with client.application.app_context():
        add_bonus_xp(user_id, 20)
    row = _get_user_row(client, user_id)
    r = client.get('/api/user/info', headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    data = r['data']
    assert data['xp'] == 20.0
    assert data['level'] == compute_level(20.0)
    assert data['next_level_xp'] == 3600 - 20  # Lv.0 → 距 Lv.1 还差 3580
    assert data['xp_progress'] > 0
    assert isinstance(data['level_title'], str)
    assert data['level'] == row['level']
