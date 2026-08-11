# MusicRate\backend\tests\test_xp_detail_realdata.py 经验详情接口 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 覆盖：/api/user/xp-detail 聚合与 DB 一致（today / daily_xp / source_totals / recent_logs）
import time
from datetime import date, datetime, timedelta

import pytest

from backend import create_app
from backend.utils.db import create_user_xp_log, get_album_table_name, get_db
from backend.utils.xp import XP_COMMENT, XP_LISTENING, XP_RATING, XP_REVIEW


@pytest.fixture(scope='module', autouse=True)
def _ensure_table():
    """模块级自动执行：确保 user_xp_log 表已建（自足，不依赖后端已启动过）"""
    app = create_app()
    with app.app_context():
        create_user_xp_log()


@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_xpd_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {'user_id': login['data']['user_id'], 'headers': {'Authorization': login['data']['token']}}


def _insert_album(client, user_id):
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'''
            INSERT INTO `{table}` (album_name, singer, release_year)
            VALUES (%s, %s, %s)
        ''', ('xp详情测试专辑', '测试歌手', 2026))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


@pytest.mark.realdata
def test_xp_detail_aggregation(client, test_user):
    user_id = test_user['user_id']
    album_id = _insert_album(client, user_id)

    today = date.today()
    yesterday = today - timedelta(days=1)

    # 种数据：收听（今天120/昨天30，1秒=1XP）+ 加分明细（今天 听后感20+评论10；昨天 评分5）+ users 累计值
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO user_listening_log (user_id, album_id, listen_date, duration_seconds)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE duration_seconds = duration_seconds + VALUES(duration_seconds)
        ''', (user_id, album_id, today.isoformat(), 120.0))
        cursor.execute('''
            INSERT INTO user_listening_log (user_id, album_id, listen_date, duration_seconds)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE duration_seconds = duration_seconds + VALUES(duration_seconds)
        ''', (user_id, album_id, yesterday.isoformat(), 30.0))
        cursor.execute(
            'INSERT INTO user_xp_log (user_id, xp_type, amount, created_at) VALUES (%s,%s,%s,%s)',
            (user_id, XP_REVIEW, 20.0, datetime.combine(today, datetime.min.time())))
        cursor.execute(
            'INSERT INTO user_xp_log (user_id, xp_type, amount, created_at) VALUES (%s,%s,%s,%s)',
            (user_id, XP_COMMENT, 10.0, datetime.combine(today, datetime.min.time())))
        cursor.execute(
            'INSERT INTO user_xp_log (user_id, xp_type, amount, created_at) VALUES (%s,%s,%s,%s)',
            (user_id, XP_RATING, 5.0, datetime.combine(yesterday, datetime.min.time())))
        cursor.execute(
            'UPDATE users SET xp = 155.0, listening_total = 150.0, bonus_date = %s, bonus_xp_today = 30.0 WHERE user_id = %s',
            (today.isoformat(), user_id))
        db.commit()
        cursor.close()

    r = client.get('/api/user/xp-detail', headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    data = r['data']

    # 累计 / 今日
    assert data['total_xp'] == 155.0
    assert data['total_listening_xp'] == 150.0
    assert data['today_listening'] == 120.0
    assert data['today_bonus'] == 30.0
    assert data['today_xp'] == 150.0  # 120 收听 + 30 加分

    # 近 7 天：今天 listening=120/bonus=30/total=150；昨天 listening=30/bonus=5/total=35
    daily = data['daily_xp']
    assert len(daily) == 7
    by_date = {item['date']: item for item in daily}
    t_item = by_date[today.isoformat()]
    assert t_item['listening'] == 120.0 and t_item['bonus'] == 30.0 and t_item['total'] == 150.0
    y_item = by_date[yesterday.isoformat()]
    assert y_item['listening'] == 30.0 and y_item['bonus'] == 5.0 and y_item['total'] == 35.0

    # 按来源累计（自 v0.7.2 起，来自 user_xp_log；本测试未写 listening 明细）
    assert data['source_totals'] == {
        XP_LISTENING: 0.0, XP_RATING: 5.0, XP_REVIEW: 20.0, XP_COMMENT: 10.0,
    }

    # 最近明细流：倒序（created_at DESC, id DESC → 今天 comment→review，昨天 rating）
    logs = data['recent_logs']
    assert [log['xp_type'] for log in logs] == [XP_COMMENT, XP_REVIEW, XP_RATING]
    assert logs[0]['amount'] == 10.0
