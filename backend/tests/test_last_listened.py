# MusicRate\backend\tests\test_last_listened.py 最近收听排序纯逻辑单测（零 DB 依赖）
# 测试对象：backend/utils/last_listened.py 的 last_listened_sort_key()
# 规则：降序(默认)最新收听在前；升序最早收听在前；从未收听（缺字段/None）固定排最后
import datetime

from backend.utils.last_listened import last_listened_sort_key


class TestLastListenedSortKey:
    def test_missing_key_desc_uses_min_sentinel(self):
        # 从未收听（缺字段）：降序 → datetime.min（reverse 后排最后）
        assert last_listened_sort_key({}, 'desc') == datetime.datetime.min

    def test_missing_key_asc_uses_max_sentinel(self):
        # 从未收听（缺字段）：升序 → datetime.max（排最后）
        assert last_listened_sort_key({}, 'asc') == datetime.datetime.max

    def test_none_value_desc_uses_min_sentinel(self):
        assert last_listened_sort_key({'last_listened': None}, 'desc') == datetime.datetime.min

    def test_none_value_asc_uses_max_sentinel(self):
        assert last_listened_sort_key({'last_listened': None}, 'asc') == datetime.datetime.max

    def test_returns_listened_time(self):
        t = datetime.datetime(2026, 8, 10, 12, 0, 0)
        assert last_listened_sort_key({'last_listened': t}, 'desc') == t

    def test_desc_sort_newest_first_never_listened_last(self):
        t1 = datetime.datetime(2026, 8, 10, 12, 0, 0)
        t2 = datetime.datetime(2026, 8, 9, 12, 0, 0)
        albums = [
            {'id': 1, 'last_listened': None},
            {'id': 2, 'last_listened': t2},
            {'id': 3, 'last_listened': t1},
            {'id': 4},  # 缺字段
        ]
        result = sorted(albums, key=lambda a: last_listened_sort_key(a, 'desc'), reverse=True)
        # 最新收听在前，从未收听（含缺字段）固定排最后
        assert [a['id'] for a in result[:2]] == [3, 2]
        assert set(a['id'] for a in result[2:]) == {1, 4}

    def test_asc_sort_oldest_first_never_listened_last(self):
        t1 = datetime.datetime(2026, 8, 10, 12, 0, 0)
        t2 = datetime.datetime(2026, 8, 9, 12, 0, 0)
        albums = [
            {'id': 1, 'last_listened': None},
            {'id': 2, 'last_listened': t2},
            {'id': 3, 'last_listened': t1},
            {'id': 4},  # 缺字段
        ]
        result = sorted(albums, key=lambda a: last_listened_sort_key(a, 'asc'), reverse=False)
        # 有收听的最早在前，从未收听（含缺字段）仍固定排最后
        assert [a['id'] for a in result[:2]] == [2, 3]
        assert set(a['id'] for a in result[2:]) == {1, 4}
