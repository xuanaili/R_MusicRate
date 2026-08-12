# MusicRate\backend\tests\test_ai_key_realdata.py 个人 AI key 配置 realdata 集成测试（v0.8.1 P3，依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_ai_key_realdata.py
# 覆盖：
#   - 保存 key：成功 + 响应绝不返回明文 + has_key/provider 正确
#   - 状态查询：未配置（has_key=false + 默认 provider + 今日用量 0）与已配置
#   - upsert 幂等：重复保存只一行，更新走 UPDATE（provider 变更生效）
#   - 校验：非法 provider 400 / 空 key 400 / 未登录 401
#   - is_enabled=0 → has_key=false
import json
import time

import pytest

from backend import create_app
from backend.utils.db import get_db


@pytest.fixture(scope='module')
def client():
    # 与 test_user_stats_realdata 同款：不用 `with app.test_client()`（preserve_context 跨请求复用 g 会二次 close）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture(scope='module', autouse=True)
def ensure_ai_key_table(client):
    """create_app() 不跑 init_base_tables（仅 run.py 启动时跑）→ 模块级确保 ai_key 表存在（幂等 CREATE）"""
    from backend.utils.db import create_ai_key
    with client.application.app_context():
        create_ai_key()


@pytest.fixture()
def test_user(client):
    """每个测试独立注册一个测试用户并登录（避免用例间数据耦合）"""
    username = f'test_ai_key_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return {
        'user_id': login['data']['user_id'],
        'headers': {'Authorization': login['data']['token']}
    }


def _save_key(client, headers, provider='deepseek', api_key='sk-test-1234567890abcdef', is_enabled=True):
    """发送保存 key 请求，返回响应 json"""
    return client.post('/api/ai/key', json={
        'provider': provider,
        'api_key': api_key,
        'is_enabled': is_enabled
    }, headers=headers).get_json()


def _get_status(client, headers):
    return client.get('/api/ai/status', headers=headers).get_json()


def _count_key_rows(client, user_id):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT COUNT(*) AS c FROM ai_key WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return row['c']


def _get_key_row(client, user_id):
    app = client.application
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT provider, api_key, is_enabled FROM ai_key WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return row


# ==================== 保存 key ====================

@pytest.mark.realdata
def test_save_key_success_no_plaintext(client, test_user):
    api_key = 'sk-test-1234567890abcdef'
    r = _save_key(client, test_user['headers'], api_key=api_key)
    assert r['code'] == 200, r
    assert r['data']['has_key'] is True
    assert r['data']['provider'] == 'deepseek'

    # 安全铁律：响应 JSON 字符串里绝不能出现明文 key
    assert api_key not in json.dumps(r, ensure_ascii=False), '响应泄露了明文 API key！'

    # 明文只存后端 DB
    row = _get_key_row(client, test_user['user_id'])
    assert row['api_key'] == api_key
    assert row['is_enabled'] == 1


@pytest.mark.realdata
def test_save_key_provider_openai(client, test_user):
    r = _save_key(client, test_user['headers'], provider='OpenAI ')
    assert r['code'] == 200, r
    # provider 规范化小写
    assert r['data']['provider'] == 'openai'
    assert _get_key_row(client, test_user['user_id'])['provider'] == 'openai'


@pytest.mark.realdata
def test_save_long_api_key(client, test_user):
    # 回归：api_key 列原为 varchar(200)，超长 key 触发 MySQL 1406「Data too long」→ 500；
    # 已扩为 TEXT，300 字符 key 应保存成功（bug：个人中心保存密钥失败）
    api_key = 'sk-long-' + 'x' * 300
    assert len(api_key) > 200  # 确保真的超旧列宽
    r = _save_key(client, test_user['headers'], api_key=api_key)
    assert r['code'] == 200, r
    assert r['data']['has_key'] is True
    # 明文完整落库（TEXT 列不截断）
    row = _get_key_row(client, test_user['user_id'])
    assert row['api_key'] == api_key


# ==================== 状态查询 ====================

@pytest.mark.realdata
def test_status_without_key(client, test_user):
    r = _get_status(client, test_user['headers'])
    assert r['code'] == 200, r
    data = r['data']
    assert data['has_key'] is False
    assert data['provider'] == 'deepseek'  # 未配置回退默认
    assert data['today_requests'] == 0
    assert data['today_chars'] == 0


@pytest.mark.realdata
def test_status_with_key(client, test_user):
    _save_key(client, test_user['headers'], provider='openai')
    r = _get_status(client, test_user['headers'])
    assert r['code'] == 200, r
    data = r['data']
    assert data['has_key'] is True
    assert data['provider'] == 'openai'
    # P3 阶段 ai_quota 未落表计数 → 今日用量为 0（P5 后才有实际值）
    assert data['today_requests'] == 0
    assert data['today_chars'] == 0


@pytest.mark.realdata
def test_status_disabled_key_has_key_false(client, test_user):
    _save_key(client, test_user['headers'], is_enabled=False)
    r = _get_status(client, test_user['headers'])
    assert r['code'] == 200, r
    assert r['data']['has_key'] is False


# ==================== upsert 幂等 ====================

@pytest.mark.realdata
def test_save_key_upsert_single_row(client, test_user):
    user_id = test_user['user_id']
    # 首次保存
    assert _save_key(client, test_user['headers'], provider='deepseek')['code'] == 200
    # 更新：换 provider + key
    assert _save_key(client, test_user['headers'], provider='openai', api_key='sk-new-key')['code'] == 200

    # user_id 唯一 → 始终只有一行；第二次走 UPDATE（provider 已变，key 已更新）
    assert _count_key_rows(client, user_id) == 1
    row = _get_key_row(client, user_id)
    assert row['provider'] == 'openai'
    assert row['api_key'] == 'sk-new-key'


# ==================== 校验 / 权限 ====================

@pytest.mark.realdata
def test_save_key_invalid_provider_rejected(client, test_user):
    r = _save_key(client, test_user['headers'], provider='claude')
    assert r['code'] == 400, r
    assert 'claude' in r['msg']


@pytest.mark.realdata
def test_save_key_empty_api_key_rejected(client, test_user):
    r = _save_key(client, test_user['headers'], api_key='   ')
    assert r['code'] == 400, r
    assert '不能为空' in r['msg']


@pytest.mark.realdata
def test_save_key_requires_login(client):
    r = client.post('/api/ai/key', json={'provider': 'deepseek', 'api_key': 'sk-xxx'}).get_json()
    assert r['code'] == 401, r


@pytest.mark.realdata
def test_status_requires_login(client):
    r = client.get('/api/ai/status').get_json()
    assert r['code'] == 401, r
