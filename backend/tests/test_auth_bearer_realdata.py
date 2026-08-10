# MusicRate\backend\tests\test_auth_bearer_realdata.py 认证兼容性 realdata 集成测试（依赖真实 MySQL）
# 运行：portable\python\python.exe -m pytest -m realdata
# 背景：前端重构后部分请求带 'Bearer <token>' 前缀，后端 login_required 只认裸 token，
# 导致今日推荐（封面取色）等请求 401。修复：login_required 剥掉 Bearer 前缀统一匹配。
import time

import pytest

from backend import create_app


@pytest.fixture(scope='module')
def client():
    # 不用 `with app.test_client()`（preserve_context=True 会跨请求复用 app context/g，
    # 导致 close_db 对已关闭连接二次 close 抛 "Already closed"）
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def token(client):
    """注册并登录一个测试用户，返回裸 token"""
    username = f'test_auth_{int(time.time() * 1000)}'
    r = client.post('/api/register', json={'username': username, 'password': 'test123'})
    assert r.get_json()['code'] == 200, r.get_json()
    login = client.post('/api/login', json={'username': username, 'password': 'test123'}).get_json()
    assert login['code'] == 200, login
    return login['data']['token']


@pytest.mark.realdata
def test_bearer_prefix_accepted(client, token):
    """Bearer 前缀（前端部分请求写法）必须通过认证"""
    r = client.get('/api/user/info', headers={'Authorization': f'Bearer {token}'})
    assert r.get_json()['code'] == 200, r.get_json()


@pytest.mark.realdata
def test_raw_token_still_works(client, token):
    """裸 token（axios 拦截器默认写法）必须保持可用"""
    r = client.get('/api/user/info', headers={'Authorization': token})
    assert r.get_json()['code'] == 200, r.get_json()


@pytest.mark.realdata
def test_bearer_case_insensitive(client, token):
    """大小写不敏感：'bearer ' 前缀同样放行"""
    r = client.get('/api/user/info', headers={'Authorization': f'bearer {token}'})
    assert r.get_json()['code'] == 200, r.get_json()


@pytest.mark.realdata
def test_no_token_rejected(client):
    r = client.get('/api/user/info')
    assert r.get_json()['code'] == 401, r.get_json()


@pytest.mark.realdata
def test_wrong_bearer_token_rejected(client):
    r = client.get('/api/user/info', headers={'Authorization': 'Bearer wrong-token'})
    assert r.get_json()['code'] == 401, r.get_json()
