# MusicRate\backend\tests\test_user_stats.py 音乐统计口径纯逻辑单测（v0.7 P2，零 DB 依赖）
# 测试对象：backend/utils/user_stats.py
# 口径：按天累加 / 近N天补零序列 / 标签分布 top8 / 已评分判断 / 防重复计数
import datetime

import pytest

from backend.utils.user_stats import (
    accumulate_daily_logs,
    aggregate_stats,
    build_score_distribution,
    build_tag_distribution,
    compute_active_days,
    compute_current_streak,
    has_review,
    is_scored,
    parse_days_param,
)


class TestScoredReview:
    """已评分 / 听后感判断：my_score / review 非空且非 "[]" """

    def test_is_scored_none(self):
        assert is_scored(None) is False

    def test_is_scored_empty_string(self):
        assert is_scored("") is False

    def test_is_scored_empty_array(self):
        # "[]" 表示存了数组但未打分 → 不算已评分
        assert is_scored("[]") is False

    def test_is_scored_zero_scores(self):
        # 数组全 0 = 未打分（评分格式 0=未评分）→ 不算已评分
        assert is_scored("[0, 0, 0]") is False

    def test_is_scored_partial_zero(self):
        # 数组含非 0 即算已评分（如只打了专辑分/部分单曲）
        assert is_scored("[0, 8.5, 0]") is True

    def test_is_scored_valid(self):
        assert is_scored("[8.5, 9.0]") is True

    def test_is_scored_invalid_json(self):
        assert is_scored("not-json") is False

    def test_has_review_none(self):
        assert has_review(None) is False

    def test_has_review_empty_array(self):
        assert has_review("[]") is False

    def test_has_review_valid(self):
        assert has_review('[{"content": "好听"}]') is True


class TestAccumulateDailyLogs:
    """按天累加 + 近N天补零序列（柱状图数据源）"""

    def _iso(self, d):
        return d.isoformat()

    def test_zero_fill_full_window(self):
        # 无任何记录 → 近N天全补 0，天数=N，含今天
        today = datetime.date.today()
        result = accumulate_daily_logs([], 7)
        assert len(result) == 7
        assert result[-1]['date'] == today.isoformat()
        assert result[0]['date'] == (today - datetime.timedelta(days=6)).isoformat()
        assert all(item['duration'] == 0.0 for item in result)

    def test_accumulate_same_day_multiple_rows(self):
        # 同一天多张专辑 → 按天累加
        today = datetime.date.today()
        rows = [
            {'listen_date': today, 'duration_seconds': 100.0},
            {'listen_date': today, 'duration_seconds': 50.5},
        ]
        result = accumulate_daily_logs(rows, 7)
        last = result[-1]
        assert last['duration'] == 150.5
        # 其他天补 0
        assert sum(item['duration'] for item in result[:-1]) == 0.0

    def test_accumulate_string_date(self):
        # DB 返回字符串日期 'YYYY-MM-DD' 也能解析
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        rows = [{'listen_date': yesterday.isoformat(), 'duration_seconds': 30.0}]
        result = accumulate_daily_logs(rows, 7)
        assert result[-2]['date'] == yesterday.isoformat()
        assert result[-2]['duration'] == 30.0

    def test_out_of_window_ignored(self):
        # 早于窗口起点的记录不参与近N天序列
        today = datetime.date.today()
        old = today - datetime.timedelta(days=10)
        rows = [{'listen_date': old, 'duration_seconds': 999.0}]
        result = accumulate_daily_logs(rows, 7)
        assert all(item['duration'] == 0.0 for item in result)

    def test_invalid_date_skipped(self):
        today = datetime.date.today()
        rows = [
            {'listen_date': 'not-a-date', 'duration_seconds': 10.0},
            {'listen_date': today, 'duration_seconds': 5.0},
        ]
        result = accumulate_daily_logs(rows, 7)
        assert result[-1]['duration'] == 5.0


class TestTagDistribution:
    """标签分布：逐行解析 tags 取前 top_n 个高频标签"""

    def test_top8_desc(self):
        albums = [{'tags': '["Pop【流行】","Rock【摇滚】"]'}] * 4
        albums.append({'tags': '["Jazz【爵士】"]'})
        result = build_tag_distribution(albums)
        # 3 个不同标签：频次降序 Pop(4)、Rock(4)、Jazz(1)，同频按名称排
        assert len(result) == 3
        assert result[0] == {'name': 'Pop【流行】', 'value': 4}
        assert result[1] == {'name': 'Rock【摇滚】', 'value': 4}
        assert result[2] == {'name': 'Jazz【爵士】', 'value': 1}

    def test_respects_top_n(self):
        albums = [
            {'tags': json_str(t)} for t in [
                ['a'], ['b'], ['c'], ['d'], ['e'], ['f'], ['g'], ['h'], ['i'], ['j'],
            ]
        ]
        result = build_tag_distribution(albums)
        # 10 个不同标签 → 只取前 8
        assert len(result) == 8

    def test_empty_and_none_tags(self):
        albums = [
            {'tags': ''},
            {'tags': None},
            {'tags': '[]'},
            {'tags': '["a"]'},
        ]
        result = build_tag_distribution(albums)
        assert result == [{'name': 'a', 'value': 1}]


class TestScoreDistribution:
    """评分分布：按 my_score 计算综合总分分桶，0 分未评分不计入"""

    def test_bucket_count(self):
        albums = [
            {'my_score': '[0]'},            # 全 0 未评分 → 不计入
            {'my_score': '[5, 60]'},        # 5*0.6 + 60*0.4 = 27 → 20-29
            {'my_score': '[42]'},           # 42 → 40-49
            {'my_score': '[100]'},          # 100 → 90-100
            {'my_score': '[95]'},           # 95 → 90-100
            {'my_score': None},             # 缺失 → 不计入
            {'my_score': 'not-json'},       # 解析失败 → 不计入
        ]
        result = build_score_distribution(albums)
        assert len(result) == 10  # 10 个桶
        assert result[0] == {'bucket': '0-9', 'count': 0}
        assert result[2] == {'bucket': '20-29', 'count': 1}
        assert result[4] == {'bucket': '40-49', 'count': 1}
        assert result[9] == {'bucket': '90-100', 'count': 2}

    def test_score_column_ignored(self):
        # 口径：评分分布只认 my_score 计算的总分，绝不用 albums.score 列（那是评论均分，未评论会漏）
        albums = [
            {'my_score': '[80]', 'score': 0.0},    # 已评分但未评论 → 必须计入 80-89
            {'my_score': '[0]', 'score': 85.0},    # 未评分但被评论刷分 → 必须不计入
        ]
        result = build_score_distribution(albums)
        assert result[8] == {'bucket': '80-89', 'count': 1}
        assert sum(b['count'] for b in result) == 1


class TestParseDays:
    def test_valid_days(self):
        assert parse_days_param(7) == 7
        assert parse_days_param(14) == 14
        assert parse_days_param(30) == 30
        assert parse_days_param('7') == 7

    def test_invalid_falls_back(self):
        assert parse_days_param(None) == 7
        assert parse_days_param('abc') == 7
        assert parse_days_param(3) == 7
        assert parse_days_param(100) == 7


class TestCurrentStreak:
    """连续收听天数：从最近有收听日期往回连续非 0；今天尚未收听不算断签（标准断签语义）"""

    def test_no_listening(self):
        assert compute_current_streak([]) == 0

    def test_today_and_yesterday(self):
        today = datetime.date.today()
        rows = [
            {'listen_date': today, 'duration_seconds': 60.0},
            {'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 30.0},
        ]
        assert compute_current_streak(rows) == 2

    def test_yesterday_only_not_today(self):
        # 今天还没听不算断签（今天还没结束）→ 昨天听 = 连续 1 天
        today = datetime.date.today()
        rows = [{'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 60.0}]
        assert compute_current_streak(rows) == 1

    def test_streak_counts_from_last_listened_day(self):
        # 昨天、前天连听，今天没听 → 锚点昨天往回连续 2 天
        today = datetime.date.today()
        rows = [
            {'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 60.0},
            {'listen_date': today - datetime.timedelta(days=2), 'duration_seconds': 60.0},
        ]
        assert compute_current_streak(rows) == 2

    def test_gap_breaks_streak(self):
        # 今天 + 前天有听，但昨天没听 → 中间断签，只算今天 1 天
        today = datetime.date.today()
        rows = [
            {'listen_date': today, 'duration_seconds': 60.0},
            {'listen_date': today - datetime.timedelta(days=2), 'duration_seconds': 30.0},
        ]
        assert compute_current_streak(rows) == 1

    def test_streak_broken_after_full_silent_day(self):
        # 前天有听，昨天（完整一天）+ 今天都没听 → 断签 0
        today = datetime.date.today()
        rows = [{'listen_date': today - datetime.timedelta(days=2), 'duration_seconds': 60.0}]
        assert compute_current_streak(rows) == 0

    def test_zero_duration_not_counted(self):
        # duration_seconds=0 的记录不计入活跃
        today = datetime.date.today()
        rows = [
            {'listen_date': today, 'duration_seconds': 0.0},
            {'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 60.0},
        ]
        assert compute_current_streak(rows) == 1

    def test_string_and_invalid_dates(self):
        today = datetime.date.today()
        rows = [
            {'listen_date': today.isoformat(), 'duration_seconds': 60.0},
            {'listen_date': 'not-a-date', 'duration_seconds': 99.0},
            {'listen_date': None, 'duration_seconds': 99.0},
        ]
        assert compute_current_streak(rows) == 1


class TestActiveDays:
    """近 N 天活跃天数：最近 days 天内（含今天）有收听（时长>0）的不同日期数"""

    def test_no_listening(self):
        assert compute_active_days([]) == 0

    def test_count_distinct_active_days(self):
        today = datetime.date.today()
        rows = [
            {'listen_date': today, 'duration_seconds': 60.0},
            {'listen_date': today, 'duration_seconds': 30.0},   # 同一天多条只算 1 天
            {'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 10.0},
            {'listen_date': today - datetime.timedelta(days=29), 'duration_seconds': 5.0},
        ]
        assert compute_active_days(rows) == 3  # 今天 / 昨天 / 29 天前

    def test_out_of_window_excluded(self):
        today = datetime.date.today()
        rows = [{'listen_date': today - datetime.timedelta(days=31), 'duration_seconds': 60.0}]
        assert compute_active_days(rows) == 0

    def test_zero_duration_not_active(self):
        today = datetime.date.today()
        rows = [
            {'listen_date': today, 'duration_seconds': 0.0},
            {'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 60.0},
        ]
        assert compute_active_days(rows) == 1

    def test_custom_days_window(self):
        today = datetime.date.today()
        rows = [{'listen_date': today - datetime.timedelta(days=7), 'duration_seconds': 60.0}]
        assert compute_active_days(rows, days=7) == 0   # 第 8 天前，不在 7 天窗内
        assert compute_active_days(rows, days=30) == 1


class TestAggregateStats:
    """统计聚合纯函数：v0.7.1 P1 口径（总时长读 users.listening_total，活跃度由 user_listening_log 计算）"""

    def test_total_duration_reads_listening_total(self):
        # P1 口径：总时长来自 users.listening_total（删专辑不掉），与 albums.listening_duration / 按天记录无关
        today = datetime.date.today()
        album_rows = [
            {'my_score': '[8.0]', 'review': '[]', 'listening_duration': 150.0, 'score': 80, 'tags': '["Pop【流行】"]'},
            {'my_score': '[]', 'review': '[]', 'listening_duration': 100.0, 'score': 0, 'tags': '[]'},
        ]
        daily_rows = [
            {'listen_date': today, 'duration_seconds': 150.0},
            {'listen_date': today, 'duration_seconds': 100.0},
            {'listen_date': today - datetime.timedelta(days=1), 'duration_seconds': 50.0},
        ]
        stats = aggregate_stats(album_rows, daily_rows, 7, total_duration=8888.5)
        assert stats['album_count'] == 2
        assert stats['scored_count'] == 1          # 第二张 my_score=[] 不算
        assert stats['review_count'] == 0
        assert stats['total_duration'] == 8888.5   # 读 listening_total，不再取 albums SUM
        # 按天序列只反映 user_listening_log（窗口内）
        assert stats['daily_listening'][-1]['duration'] == 250.0
        assert stats['daily_listening'][-2]['duration'] == 50.0
        # 标签分布 top8
        assert stats['tag_distribution'] == [{'name': 'Pop【流行】', 'value': 1}]
        # 评分分布：只有 80 分计入
        assert sum(b['count'] for b in stats['score_distribution']) == 1
        # 活跃度：今天 + 昨天 → 连续 2 天；近 30 天活跃 2 天
        assert stats['current_streak'] == 2
        assert stats['active_days_30'] == 2

    def test_total_duration_fallback_to_albums(self):
        # total_duration 未传时回退 SUM(albums.listening_duration)（兼容旧调用 / 默认值）
        album_rows = [
            {'my_score': '[]', 'review': '[]', 'listening_duration': 150.0, 'score': 0, 'tags': '[]'},
            {'my_score': '[]', 'review': '[]', 'listening_duration': 100.0, 'score': 0, 'tags': '[]'},
        ]
        stats = aggregate_stats(album_rows, [], 7)
        assert stats['total_duration'] == 250.0
        assert stats['current_streak'] == 0
        assert stats['active_days_30'] == 0

    def test_empty_rows(self):
        stats = aggregate_stats([], [], 7)
        assert stats['album_count'] == 0
        assert stats['scored_count'] == 0
        assert stats['review_count'] == 0
        assert stats['total_duration'] == 0.0
        assert len(stats['daily_listening']) == 7
        assert stats['tag_distribution'] == []
        assert stats['current_streak'] == 0
        assert stats['active_days_30'] == 0


def json_str(tags):
    import json
    return json.dumps(tags, ensure_ascii=False)
