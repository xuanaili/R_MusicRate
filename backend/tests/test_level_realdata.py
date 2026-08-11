# MusicRate\backend\tests\test_level_realdata.py 等级经验 v0.7.1 P0 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 覆盖：四列迁移幂等、pause 加收听经验、每日加分上限、/api/user/info 等级字段
import time

import pytest

from backend import create_app
from backend.api.listening import PLAYING_TIMER_CACHE
from backend.config import MYSQL_CONFIG
from backend.utils.db import create_user_xp_log, ensure_users_xp_columns, get_album_table_name, get_db
from backend.utils.level import compute_level
from backend.utils.user import add_bonus_xp


@pytest.fixture(scope='module', autouse=True)
def _ensure_migration():
    """模块级自动执行：确保 users 等级经验四列已迁移 + user_xp_log 明细表已建（自足，不依赖后端已启动过）"""
    app = create_app()
    with app.app_context():
        ensure_users_xp_columns()
        create_user_xp_log()


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
            gained, _, _, _ = add_bonus_xp(user_id, 20, 'review')
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
        add_bonus_xp(user_id, 90, 'review')
        gained, new_xp, _, _ = add_bonus_xp(user_id, 20, 'review')
    assert gained == 10.0
    assert new_xp == 100.0


@pytest.mark.realdata
def test_user_info_returns_level_fields(client, test_user):
    """/api/user/info 返回 xp/level/next_level_xp/xp_progress/level_title，且与纯函数一致"""
    user_id = test_user['user_id']
    # 先加一点经验，再查 info
    with client.application.app_context():
        add_bonus_xp(user_id, 20, 'review')
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


@pytest.mark.realdata
def test_score_save_unchanged_no_xp(client, test_user):
    """评分保存接口：同分重存（离开板块/切子页面/退出专辑的自动保存）不再加经验"""
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    headers = test_user['headers']

    # 首次保存 [80,90]（实际评分）→ +5
    r1 = client.put(f'/api/album/score/save/{album_id}', json={'score_list': [80, 90]}, headers=headers).get_json()
    assert r1['code'] == 200, r1
    assert r1['data']['xp_gained'] == 5.0
    xp_after_first = _get_user_row(client, user_id)['xp']

    # 再存完全相同 [80,90]（自动保存触发）→ 不加经验
    r2 = client.put(f'/api/album/score/save/{album_id}', json={'score_list': [80, 90]}, headers=headers).get_json()
    assert r2['code'] == 200, r2
    assert r2['data']['xp_gained'] == 0.0
    assert _get_user_row(client, user_id)['xp'] == xp_after_first

    # 末尾未评分曲目数量不同、实际评分一致 → 也不算变化
    r3 = client.put(f'/api/album/score/save/{album_id}', json={'score_list': [80, 90, 0, 0]}, headers=headers).get_json()
    assert r3['data']['xp_gained'] == 0.0
    assert _get_user_row(client, user_id)['xp'] == xp_after_first


@pytest.mark.realdata
def test_score_save_changed_gives_xp(client, test_user):
    """评分保存接口：实际评分变化 → +5（真改分才给经验）"""
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)
    headers = test_user['headers']

    client.put(f'/api/album/score/save/{album_id}', json={'score_list': [80, 90]}, headers=headers).get_json()
    xp_before = _get_user_row(client, user_id)['xp']

    r = client.put(f'/api/album/score/save/{album_id}', json={'score_list': [85, 90]}, headers=headers).get_json()
    assert r['code'] == 200, r
    assert r['data']['xp_gained'] == 5.0
    assert _get_user_row(client, user_id)['xp'] == xp_before + 5.0


@pytest.mark.realdata
def test_bonus_xp_writes_log(client, test_user):
    """v0.7.2：add_bonus_xp 写 user_xp_log 明细——每次实际加分写一行；打满每日上限后 gained=0 不写新行；
    log 加分合计与 users.bonus_xp_today 严格一致（同事务写入）"""
    user_id = test_user['user_id']
    # 5 次听后感 +20 → 每次写一条 log
    for _ in range(5):
        with client.application.app_context():
            add_bonus_xp(user_id, 20, 'review')
    # 第 6 次打满上限 → gained=0，不写 log（防 +0 噪音）
    with client.application.app_context():
        gained, _, _, _ = add_bonus_xp(user_id, 20, 'review')
    assert gained == 0.0

    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT xp_type, amount FROM user_xp_log WHERE user_id = %s ORDER BY id', (user_id,))
        rows = cursor.fetchall()
        cursor.execute('SELECT bonus_xp_today FROM users WHERE user_id = %s', (user_id,))
        today_bonus = cursor.fetchone()['bonus_xp_today']
        cursor.execute(
            'SELECT COALESCE(SUM(amount), 0) AS s FROM user_xp_log WHERE user_id = %s AND xp_type != %s',
            (user_id, 'listening'))
        log_sum = cursor.fetchone()['s']
        cursor.close()

    assert len(rows) == 5  # 只有 5 次实际加分写了 log
    assert all(r['xp_type'] == 'review' for r in rows)
    assert [r['amount'] for r in rows] == [20.0] * 5
    assert log_sum == today_bonus == 100.0


@pytest.mark.realdata
def test_pause_writes_listening_log(client, test_user):
    """v0.7.2：pause 接口写 user_xp_log 收听明细——play_seconds>0 写一条（xp_type=listening）"""
    user_id = test_user['user_id']
    album_id = _insert_user_album(client, user_id)

    now = time.time()
    PLAYING_TIMER_CACHE[f'{user_id}_{album_id}'] = {'start_timestamp': now - 2, 'origin_duration': 0.0}
    r = client.post(
        f'/api/album/listening/pause/{album_id}',
        json={'progress_seconds': 1},
        headers=test_user['headers'],
    ).get_json()
    assert r['code'] == 200, r
    play_seconds = r['data']['this_play_seconds']

    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT xp_type, amount FROM user_xp_log WHERE user_id = %s', (user_id,))
        rows = cursor.fetchall()
        cursor.close()

    assert len(rows) == 1
    assert rows[0]['xp_type'] == 'listening'
    assert rows[0]['amount'] == pytest.approx(play_seconds, abs=0.1)
