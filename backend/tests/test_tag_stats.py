# MusicRate\backend\tests\test_tag_stats.py 标签聚合统计单测（纯逻辑 + 假游标，零 DB 依赖）
# 测试对象：backend/utils/tag.py
# 背景：老实现每张专辑都要扫一遍全部用户表（1199 张 ≈ 1.0s/张），搜索一页 10 张 ≈ 11s 直接超时。
# 现实现 = 一次 UNION ALL 批量扫描 + 全量快照缓存；本文件锁住「统计口径不变 + 只扫一次」。
import re

import pytest

from backend.utils import tag as tag_module
from backend.utils.tag import (
    parse_tags,
    build_tag_stats,
    merge_tag_counts,
    chunked,
    scan_user_tags,
    collect_tag_counts,
    get_album_tag_stats,
    get_album_tag_stats_map,
    load_full_snapshot,
    invalidate_cache,
)


class FakeCursor:
    """模拟 pymysql DictCursor：只认识本文件用到的几条 SQL"""

    def __init__(self, tables=None, rows_by_table=None, pool_rows=None, fail_tables=None):
        self.tables = tables or []
        self.rows_by_table = rows_by_table or {}
        self.pool_rows = pool_rows or []
        self.fail_tables = set(fail_tables or [])
        self.execute_count = 0
        self.statements = []
        self._rows = []

    def execute(self, sql, params=None):
        self.execute_count += 1
        self.statements.append((sql, params))
        if 'information_schema.tables' in sql:
            self._rows = [{'t': name} for name in self.tables]
            return
        if 'FROM album_pool' in sql and 'UNION' not in sql:
            if 'WHERE id IN' in sql:
                wanted = set(params or [])
                self._rows = [row for row in self.pool_rows if row['id'] in wanted]
            else:
                self._rows = list(self.pool_rows)
            return
        # UNION ALL 批量扫描：按 SQL 里出现的表名还原结果
        names = re.findall(r'FROM `([^`]+)`', sql)
        pool_ids = None
        if params and 'source_pool_id IN' in sql:
            pool_ids = set(params)
        rows = []
        for name in names:
            if name in self.fail_tables:
                raise RuntimeError(f'模拟表 {name} 查询失败')
            for row in self.rows_by_table.get(name, []):
                if pool_ids is not None and row['source_pool_id'] not in pool_ids:
                    continue
                rows.append(row)
        self._rows = rows

    def fetchall(self):
        return self._rows


@pytest.fixture(autouse=True)
def _clear_cache():
    invalidate_cache()
    yield
    invalidate_cache()


class TestParseTags:
    def test_json_array(self):
        assert parse_tags('["Rock", "Pop"]') == ['Rock', 'Pop']

    def test_trims_whitespace_and_drops_empty(self):
        assert parse_tags('[" Rock ", "", "  "]') == ['Rock']

    def test_single_string_json(self):
        assert parse_tags('"Jazz"') == ['Jazz']

    def test_non_list_json(self):
        assert parse_tags('{"a": 1}') == []
        assert parse_tags('123') == []

    def test_invalid_json(self):
        assert parse_tags('not-json') == []

    def test_empty_values(self):
        assert parse_tags(None) == []
        assert parse_tags('') == []
        assert parse_tags('[]') == []

    def test_list_input(self):
        assert parse_tags(['Rock', None, '']) == ['Rock']

    def test_non_string_elements_dropped(self):
        assert parse_tags('["Rock", 1, true, null]') == ['Rock']


class TestBuildTagStats:
    def test_filters_tags_below_ten_percent(self):
        # 20 次里 major=18(90%)、minor=2(10%)、tiny=1(<10%)
        stats = build_tag_stats({'major': 18, 'minor': 2, 'tiny': 1}, 21)
        tags = [item['tag'] for item in stats]
        assert 'tiny' not in tags
        assert 'major' in tags

    def test_percent_and_size(self):
        stats = build_tag_stats({'Rock': 5}, 10)
        assert stats[0]['percent'] == 50.0
        assert stats[0]['size'] == 140  # int(50 * 2 + 40)
        assert stats[0]['count'] == 5

    def test_color_format(self):
        stats = build_tag_stats({'Rock': 10}, 10)
        assert re.fullmatch(r'#[0-9a-f]{6}', stats[0]['color'])

    def test_empty_total(self):
        assert build_tag_stats({'Rock': 1}, 0) == []
        assert build_tag_stats({}, 0) == []


class TestHelpers:
    def test_merge_tag_counts(self):
        target = {'Rock': 1}
        added = merge_tag_counts(target, {'Rock': 2, 'Pop': 3})
        assert target == {'Rock': 3, 'Pop': 3}
        assert added == 5

    def test_chunked(self):
        assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
        assert chunked([], 2) == []
        assert chunked([1, 2], 0) == [[1, 2]]


class TestScanUserTags:
    def test_batches_tables_into_union(self, monkeypatch):
        monkeypatch.setattr(tag_module, 'UNION_CHUNK_SIZE', 2)
        cursor = FakeCursor(
            tables=['albums_1', 'albums_2', 'albums_3'],
            rows_by_table={
                'albums_1': [{'source_pool_id': 10, 'tags': '["Rock"]'}],
                'albums_2': [{'source_pool_id': 10, 'tags': '["Rock","Pop"]'}],
                'albums_3': [{'source_pool_id': 11, 'tags': '["Jazz"]'}],
            },
        )
        counts = scan_user_tags(cursor, None)
        assert counts[10] == {'Rock': 2, 'Pop': 1}
        assert counts[11] == {'Jazz': 1}
        # 3 张表 / 每块 2 张 = 2 条扫描 SQL（不是 3 条单表 SQL）
        scan_sqls = [sql for sql, _ in cursor.statements if 'source_pool_id' in sql]
        assert len(scan_sqls) == 2
        assert 'UNION ALL' in scan_sqls[0]  # 第一块拼了两张表
        assert 'UNION ALL' not in scan_sqls[1]  # 第二块只剩一张表

    def test_filters_by_pool_ids(self):
        cursor = FakeCursor(
            tables=['albums_1'],
            rows_by_table={'albums_1': [
                {'source_pool_id': 10, 'tags': '["Rock"]'},
                {'source_pool_id': 11, 'tags': '["Jazz"]'},
            ]},
        )
        counts = scan_user_tags(cursor, [10])
        assert set(counts) == {10}

    def test_failed_chunk_falls_back_to_per_table(self):
        # 一张坏表（异构老表缺列）不应该让同块其它表的数据丢失
        cursor = FakeCursor(
            tables=['albums_1', 'albums_broken', 'albums_2'],
            rows_by_table={
                'albums_1': [{'source_pool_id': 10, 'tags': '["Rock"]'}],
                'albums_2': [{'source_pool_id': 10, 'tags': '["Pop"]'}],
            },
            fail_tables={'albums_broken'},
        )
        counts = scan_user_tags(cursor, None)
        assert counts[10] == {'Rock': 1, 'Pop': 1}

    def test_all_tables_broken_returns_empty(self):
        cursor = FakeCursor(
            tables=['albums_broken'],
            rows_by_table={},
            fail_tables={'albums_broken'},
        )
        assert scan_user_tags(cursor, None) == {}

    def test_no_tables(self):
        cursor = FakeCursor(tables=[])
        assert scan_user_tags(cursor, None) == {}


class TestCollectTagCounts:
    def _cursor(self):
        return FakeCursor(
            tables=['albums_1'],
            rows_by_table={'albums_1': [{'source_pool_id': 10, 'tags': '["Rock","Pop"]'}]},
            pool_rows=[
                {'id': 10, 'tags': '["Rock"]'},
                {'id': 11, 'tags': '[]'},
            ],
        )

    def test_merges_pool_and_user_tags(self):
        cursor = self._cursor()
        data = collect_tag_counts(cursor, [10])[10]
        # 公共池 Rock 1 次 + 用户副本 Rock 1 次 / Pop 1 次
        assert data['counts'] == {'Rock': 2, 'Pop': 1}
        assert data['total'] == 3

    def test_second_call_hits_cache(self):
        cursor = self._cursor()
        collect_tag_counts(cursor, [10])
        first = cursor.execute_count
        collect_tag_counts(cursor, [10])
        collect_tag_counts(cursor, [11])
        assert cursor.execute_count == first  # 没有新增任何 SQL

    def test_unknown_pool_id_returns_empty_without_rescan(self):
        cursor = self._cursor()
        collect_tag_counts(cursor, [10])
        first = cursor.execute_count
        assert collect_tag_counts(cursor, [999])[999] == {'counts': {}, 'total': 0}
        assert cursor.execute_count == first

    def test_pool_album_without_tags_is_in_snapshot(self):
        cursor = self._cursor()
        snapshot = load_full_snapshot(cursor)
        assert 11 in snapshot
        assert snapshot[11]['total'] == 0

    def test_empty_ids(self):
        cursor = self._cursor()
        assert collect_tag_counts(cursor, []) == {}
        assert cursor.execute_count == 0


class TestPublicApi:
    def test_get_album_tag_stats(self):
        cursor = FakeCursor(
            tables=['albums_1'],
            rows_by_table={'albums_1': [{'source_pool_id': 10, 'tags': '["Rock"]'}]},
            pool_rows=[{'id': 10, 'tags': '["Rock"]'}],
        )
        stats = get_album_tag_stats(10, cursor)
        assert stats[0]['tag'] == 'Rock'
        assert stats[0]['percent'] == 100.0

    def test_get_album_tag_stats_map_batch(self):
        cursor = FakeCursor(
            tables=['albums_1'],
            rows_by_table={'albums_1': [{'source_pool_id': 10, 'tags': '["Rock"]'}]},
            pool_rows=[{'id': 10, 'tags': '["Rock"]'}, {'id': 20, 'tags': '["Jazz"]'}],
        )
        result = get_album_tag_stats_map(cursor, [10, 20])
        assert result[10][0]['tag'] == 'Rock'
        assert result[20][0]['tag'] == 'Jazz'

    def test_invalidate_cache_forces_rescan(self):
        cursor = FakeCursor(
            tables=['albums_1'],
            rows_by_table={'albums_1': []},
            pool_rows=[{'id': 10, 'tags': '["Rock"]'}],
        )
        collect_tag_counts(cursor, [10])
        first = cursor.execute_count
        invalidate_cache()
        collect_tag_counts(cursor, [10])
        assert cursor.execute_count > first
