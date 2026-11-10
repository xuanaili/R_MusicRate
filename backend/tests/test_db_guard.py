# MusicRate\backend\tests\test_db_guard.py 测试数据回收守卫单测（纯逻辑，零 DB 依赖）
# 测试对象：backend/tests/_db_guard.py
# 背景：realdata 测试曾把 1193 个测试用户 / 557 条「XX测试专辑」留在生产库里，
#       搜索页出现「暂无封面 节奏分析测试专辑」。本守卫负责会话结束按水位线回收。
import os

from backend.tests import _db_guard


class TestShouldPurgePool:
    def test_system_created_is_test_data(self):
        assert _db_guard.should_purge_pool(0, []) is True

    def test_created_by_session_test_user(self):
        assert _db_guard.should_purge_pool(1205, [1201, 1202, 1205]) is True

    def test_created_by_real_user_is_kept(self):
        # 真实用户（会话开始前已存在）在会话期间手动添加的专辑不能被删
        assert _db_guard.should_purge_pool(2, [1205, 1206]) is False

    def test_none_create_user(self):
        assert _db_guard.should_purge_pool(None, []) is True

    def test_non_numeric_create_user(self):
        assert _db_guard.should_purge_pool('abc', []) is False

    def test_string_numeric(self):
        assert _db_guard.should_purge_pool('0', []) is True
        assert _db_guard.should_purge_pool('2', [1205]) is False


class TestDiffNewFiles:
    def test_returns_only_new(self):
        assert _db_guard.diff_new_files({'a.mp3', 'b.jpg'}, {'a.mp3', 'b.jpg', 'test_x.mp3'}) == ['test_x.mp3']

    def test_nothing_new(self):
        assert _db_guard.diff_new_files({'a.mp3'}, {'a.mp3'}) == []

    def test_empty_before(self):
        assert _db_guard.diff_new_files(set(), {'a', 'b'}) == ['a', 'b']


class TestBuildInClause:
    def test_placeholders(self):
        clause, params = _db_guard.build_in_clause([1, 2, 3])
        assert clause == '%s, %s, %s'
        assert params == [1, 2, 3]

    def test_empty_is_null(self):
        assert _db_guard.build_in_clause([]) == ('NULL', [])
        assert _db_guard.build_in_clause(None) == ('NULL', [])


class TestSnapshotFiles:
    def test_snapshot_missing_dirs(self, tmp_path):
        snapshot = _db_guard.snapshot_files(str(tmp_path))
        assert set(snapshot) == set(_db_guard.DATA_DIRS)
        assert all(value == set() for value in snapshot.values())

    def test_snapshot_lists_files(self, tmp_path):
        target = tmp_path / _db_guard.DATA_DIRS[0]
        target.mkdir(parents=True)
        (target / 'x.mp3').write_bytes(b'')
        snapshot = _db_guard.snapshot_files(str(tmp_path))
        assert snapshot[_db_guard.DATA_DIRS[0]] == {'x.mp3'}


class TestConnect:
    def test_connect_failure_returns_none(self):
        # 指向不存在的库 → 返回 None（不能让守卫拖挂测试）
        assert _db_guard.connect({'host': 'localhost', 'port': 1, 'user': 'x',
                                  'password': 'x', 'db': 'nope', 'charset': 'utf8mb4'}) is None


class TestDataDirsWiring:
    def test_data_dirs_are_relative(self):
        for path in _db_guard.DATA_DIRS:
            assert not os.path.isabs(path)

    def test_scoped_tables_cover_known_writers(self):
        # realdata 测试写过的表都要在回收名单里
        assert 'album_tempo' in {t for t, _ in _db_guard.POOL_SCOPED_TABLES}
        assert 'album_lyric' in {t for t, _ in _db_guard.POOL_SCOPED_TABLES}
        assert 'album_comments' in {t for t, _ in _db_guard.POOL_SCOPED_TABLES}
        assert 'ai_conversation' in set(_db_guard.USER_SCOPED_TABLES)
        assert 'user_xp_log' in set(_db_guard.USER_SCOPED_TABLES)
        assert ('album_pool', 'id') in _db_guard.MAX_ID_COLUMNS
        assert ('users', 'user_id') in _db_guard.MAX_ID_COLUMNS
