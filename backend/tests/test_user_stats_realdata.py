# MusicRate\backend\tests\test_user_stats_realdata.py 音乐统计 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 覆盖：/api/user/stats 与 DB 聚合一致；listening pause 写入 user_listening_log 且 upsert 正确
import time
from datetime import date, timedelta

import pytest

from backend import create_app
from backend.api.listening import PLAYING_TIMER_CACHE
from backend.utils.db import get_album_table_name, get_db


@pytest.fixture(scope='module')
def client():
    # 注意：不要用 `with app.test_client()`（preserve_context=True 会跨请求复用 app context/g，
    # 导致 close_db 对已关闭连接二次 close 抛 "Already closed"）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_stats_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _insert_album(client, user_id, **fields):
    """向用户专辑表插入一行测试专辑，返回 id"""
    table = get_album_table_name(user_id)
    cols = {
        'album_name': '统计测试专辑',
        'singer': '测试歌手',
        'release_year': 2026,
        'my_score': '[8.0, 9.0]',
        'review': '[{"content":"好听"}]',
        'listening_duration': 300.0,
        'score': 85.0,
        'tags': '["Pop【流行】","Rock【摇滚】"]',
    }
    cols.update(fields)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'''
            INSERT INTO `{table}` (album_name, singer, release_year, my_score, review, listening_duration, score, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (cols['album_name'], cols['singer'], cols['release_year'], cols['my_score'],
              cols['review'], cols['listening_duration'], cols['score'], cols['tags']))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _insert_daily_log(client, user_id, album_id, date_str, seconds):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO user_listening_log (user_id, album_id, listen_date, duration_seconds)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE duration_seconds = duration_seconds + VALUES(duration_seconds)
        ''', (user_id, album_id, date_str, seconds))
        db.commit()
        cursor.close()


@pytest.mark.realdata
def test_stats_matches_db_aggregation(client, test_user):
    user_id = test_user['user_id']
    album_id = _insert_album(client, user_id)

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    old_day = (date.today() - timedelta(days=10)).isoformat()  # 7 天窗口外、30 天内记录（活跃度仍计数）
    _insert_daily_log(client, user_id, album_id, today, 100.0)
    _insert_daily_log(client, user_id, album_id, yesterday, 50.0)
    _insert_daily_log(client, user_id, album_id, old_day, 999.0)

    # v0.7.1 P1：总时长口径统一，读 users.listening_total（删专辑不掉），与 albums SUM / 按天记录无关
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE users SET listening_total = %s WHERE user_id = %s', (4200.0, user_id))
        db.commit()
        cursor.close()

    r = client.get('/api/user/stats', query_string={'days': 7}, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    data = r['data']

    # 与 DB 聚合一致
    assert data['album_count'] == 1
    assert data['scored_count'] == 1
    assert data['review_count'] == 1
    assert data['total_duration'] == 4200.0  # 读 users.listening_total，不再 SUM albums.listening_duration
    assert data['tag_distribution'] == [
        {'name': 'Pop【流行】', 'value': 1},
        {'name': 'Rock【摇滚】', 'value': 1},
    ]

    # 活跃度：今天/昨天/10 天前都听 → 连续 2 天（今天+昨天），近 30 天活跃 3 天
    assert data['current_streak'] == 2
    assert data['active_days_30'] == 3

    # 近N天序列：今天=100、昨天=50、其余补 0，窗口外不进序列
    daily = data['daily_listening']
    assert len(daily) == 7
    by_date = {item['date']: item['duration'] for item in daily}
    assert by_date[today] == 100.0
    assert by_date[yesterday] == 50.0
    assert old_day not in by_date
    assert sum(v for d, v in by_date.items() if d not in (today, yesterday)) == 0.0

    # 评分分布：由 my_score [8.0, 9.0] 计算总分 8.0*0.6+9.0*0.4=8.4 → 0-9 桶
    assert sum(b['count'] for b in data['score_distribution']) == 1
    assert data['score_distribution'][0] == {'bucket': '0-9', 'count': 1}


@pytest.mark.realdata
def test_listening_pause_upserts_daily_log(client, test_user):
    user_id = test_user['user_id']
    album_id = _insert_album(client, user_id, listening_duration=0.0)

    # 模拟播放 60 秒后暂停（直接种入内存计时缓存，避免真实等待）
    now = time.time()
    PLAYING_TIMER_CACHE[f'{user_id}_{album_id}'] = {'start_timestamp': now - 60, 'origin_duration': 0.0}
    r1 = client.post(f'/api/album/listening/pause/{album_id}', headers=test_user['headers']).get_json()
    assert r1['code'] == 200, r1
    assert r1['data']['this_play_seconds'] == 60.0

    # 再次播放 60 秒并暂停 → 同一天同一专辑 upsert 累加
    PLAYING_TIMER_CACHE[f'{user_id}_{album_id}'] = {'start_timestamp': now - 60, 'origin_duration': 60.0}
    r2 = client.post(f'/api/album/listening/pause/{album_id}', headers=test_user['headers']).get_json()
    assert r2['code'] == 200, r2

    # 按天记录累加为 120；专辑累计时长同步为 120
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT duration_seconds FROM user_listening_log
            WHERE user_id = %s AND album_id = %s
        ''', (user_id, album_id))
        log_row = cursor.fetchone()
        # 两次 60 秒累加≈120；因真实计时存在毫秒级漂移，用 ±2 秒容差
        assert log_row and log_row['duration_seconds'] == pytest.approx(120.0, abs=2), log_row

        table = get_album_table_name(user_id)
        cursor.execute(f'SELECT listening_duration FROM `{table}` WHERE id = %s', (album_id,))
        album_row = cursor.fetchone()
        assert album_row and album_row['listening_duration'] == pytest.approx(120.0, abs=2), album_row
        cursor.close()
