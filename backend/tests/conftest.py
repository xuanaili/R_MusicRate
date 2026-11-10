# MusicRate\backend\tests\conftest.py pytest 全局配置
# 自动把项目根加入 sys.path，测试内可直接 `from backend.utils.xxx import ...`
# 同时挂一个「真实库测试数据回收」守卫：会话结束自动清理测试污染（详见 _db_guard.py）
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope='session', autouse=True)
def db_pollution_guard():
    """会话级兜底：记录水位线 → 跑测试 → 回收会话期间新建的测试数据

    铁律见 CLAUDE.md「禁止测试污染数据库」。
    连不上 MySQL（纯单测环境）时静默跳过，不影响测试结果。
    """
    from backend.config import MYSQL_CONFIG
    from backend.tests import _db_guard

    conn = _db_guard.connect(MYSQL_CONFIG)
    debug = bool(os.environ.get('MUSICRATE_DEBUG_GUARD'))
    if conn is None:
        if debug:
            print('[guard] 无法连接数据库，跳过回收')
        yield
        return

    cursor = conn.cursor()
    try:
        max_ids = _db_guard.snapshot_max_ids(cursor)
    finally:
        cursor.close()
    file_snapshot = _db_guard.snapshot_files(PROJECT_ROOT)
    if debug:
        print('[guard] 水位线快照:', max_ids.get('users.user_id'), max_ids.get('album_pool.id'))

    try:
        yield
    finally:
        if debug:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) AS c FROM users')
            print('[guard] teardown 时 users 数量:', cursor.fetchone()['c'])
            cursor.close()
        try:
            _db_guard.purge(conn, max_ids, file_snapshot, PROJECT_ROOT)
        finally:
            conn.close()
