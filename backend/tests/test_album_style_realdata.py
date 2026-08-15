# MusicRate\backend\tests\test_album_style_realdata.py v0.9 P0：专辑样式配置读写接口 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_album_style_realdata.py
# 覆盖：
#   - GET 无记录 → data:null（「从未配置」等价首次自动生成）
#   - GET 归属校验：专辑不存在 / 非本人 → 404
#   - POST 保存 → 返回规范化配置；GET 读回一致（切 tab / 刷新 / 换设备持久化）
#   - POST upsert 幂等：重复保存同一行更新，不重复插行（user_id + album_id 唯一）
#   - POST 边界校验：非法 style_type/auto_manual 收敛默认、数值 clamp 0-100
#   - 越权：他人不可读写本人专辑的样式配置
import time

import pytest

from backend import create_app
from backend.utils.db import get_album_table_name, get_db


@pytest.fixture(scope='module')
def client():
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture(scope='module', autouse=True)
def ensure_user_album_style_table(client):
    """create_app() 不跑 init_base_tables（仅 run.py 启动时跑）→ 模块级确保 user_album_style 表存在（幂等 CREATE）"""
    from backend.utils.db import create_user_album_style
    with client.application.app_context():
        create_user_album_style()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_style_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _insert_user_album(client, user_id):
    """在 albums_{user_id} 插入一条私有副本，返回 album_id（login_required 已确保用户表存在）"""
    table = get_album_table_name(user_id)
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            f'INSERT INTO `{table}` (album_name, singer, release_year, source_pool_id) '
            'VALUES (%s, %s, %s, %s)',
            ('样式测试专辑', '测试歌手', 2026, 0),
        )
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id


def _get_style_rows(client, user_id, album_id):
    """直接查 user_album_style 行（校验持久化落库），返回行 dict 列表"""
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'SELECT id, user_id, album_id, style_type, rhy_config, meteor_config, auto_manual FROM user_album_style '
            'WHERE user_id = %s AND album_id = %s',
            (user_id, album_id),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows


# ==================== GET 读取 ====================

@pytest.mark.realdata
def test_get_no_record_returns_null(client, test_user):
    album_id = _insert_user_album(client, test_user['user_id'])
    r = client.get(f'/api/album/style/{album_id}', headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data'] is None  # 从未配置


@pytest.mark.realdata
def test_get_album_not_owned_404(client, test_user):
    # 专辑不存在于本人 albums_{user_id}（ID 不存在）
    r = client.get('/api/album/style/999999', headers=test_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_get_other_user_album_404(client, test_user):
    # 别人的专辑（在他人 albums 表，不在本人表）→ 归属校验 404
    user_a = _insert_user_album(client, test_user['user_id'])
    # 用另一个用户登录，尝试读 user_a
    username = f'test_style_b_{int(time.time() * 1000)}'
    client.post('/api/register', json={'username': username, 'password': 'test123'})
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    r = client.get(f'/api/album/style/{user_a}', headers={'Authorization': login['data']['token']}).get_json()
    assert r['code'] == 404, r


# ==================== POST 保存 / upsert / 读回 ====================

@pytest.mark.realdata
def test_post_save_then_get(client, test_user):
    album_id = _insert_user_album(client, test_user['user_id'])
    body = {
        'style_type': 'ball',
        'auto_manual': 'auto',
        'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
        'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45},
    }
    r = client.post(f'/api/album/style/{album_id}', json=body, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    assert r['data']['style_type'] == 'ball'
    assert r['data']['rhy_config']['a'] == 58

    # GET 读回一致（持久化生效）
    g = client.get(f'/api/album/style/{album_id}', headers=test_user['headers']).get_json()
    assert g['code'] == 200, g
    assert g['data']['style_type'] == 'ball'
    assert g['data']['rhy_config'] == {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11}
    assert g['data']['meteor_config'] == {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}
    assert g['data']['auto_manual'] == 'auto'
    assert g['data']['update_time'] is not None

    # 落库校验（rhy_config 为 JSON 文本）
    rows = _get_style_rows(client, test_user['user_id'], album_id)
    assert len(rows) == 1
    assert rows[0]['style_type'] == 'ball'


@pytest.mark.realdata
def test_post_upsert_idempotent(client, test_user):
    """重复保存同一专辑 → 同一行更新（user_id+album_id 唯一键），不重复插行"""
    album_id = _insert_user_album(client, test_user['user_id'])
    for i in range(2):
        r = client.post(f'/api/album/style/{album_id}', json={
            'style_type': 'meteor',
            'auto_manual': 'manual',
            'rhy_config': {'a': 47, 'b': 100, 'c': 1, 'd': 4, 'e': 7},
            'meteor_config': {'angle': 45, 'size': 19, 'tailLength': 44, 'speed': 32},
        }, headers=test_user['headers']).get_json()
        assert r['code'] == 200, r
    rows = _get_style_rows(client, test_user['user_id'], album_id)
    assert len(rows) == 1, 'upsert 后应只有一行'
    assert rows[0]['auto_manual'] == 'manual'


@pytest.mark.realdata
def test_post_invalid_values_normalized(client, test_user):
    """POST 非法 style_type/auto_manual 收敛默认；数值越界 clamp 0-100"""
    album_id = _insert_user_album(client, test_user['user_id'])
    r = client.post(f'/api/album/style/{album_id}', json={
        'style_type': 'explode',
        'auto_manual': 'sometimes',
        'rhy_config': {'a': 150, 'b': -5, 'c': 'abc', 'd': 88, 'e': 0},
        'meteor_config': {'angle': 45, 'size': 500, 'tailLength': -1, 'speed': 60},
    }, headers=test_user['headers']).get_json()
    assert r['code'] == 200, r
    data = r['data']
    assert data['style_type'] == 'close'
    assert data['auto_manual'] == 'auto'
    assert data['rhy_config']['a'] == 100
    assert data['rhy_config']['b'] == 0
    assert data['rhy_config']['c'] == 0
    assert data['meteor_config']['size'] == 100
    assert data['meteor_config']['tailLength'] == 0


@pytest.mark.realdata
def test_post_album_not_owned_404(client, test_user):
    r = client.post('/api/album/style/999999', json={}, headers=test_user['headers']).get_json()
    assert r['code'] == 404, r


@pytest.mark.realdata
def test_post_other_user_album_404(client, test_user):
    album_id = _insert_user_album(client, test_user['user_id'])
    username = f'test_style_c_{int(time.time() * 1000)}'
    client.post('/api/register', json={'username': username, 'password': 'test123'})
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    r = client.post(f'/api/album/style/{album_id}', json={'style_type': 'ball'}, headers={'Authorization': login['data']['token']}).get_json()
    assert r['code'] == 404, r
