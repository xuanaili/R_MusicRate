# MusicRate\backend\tests\test_xp_detail.py 经验详情聚合纯逻辑单测（v0.7.2，零 DB 依赖）
# 测试对象：backend/utils/xp_detail.py
# 覆盖：近N天加分经验按天累加补零 / listening+bonus 合并为每日总经验
import datetime

from backend.utils.xp_detail import accumulate_bonus_daily, build_daily_xp


class TestAccumulateBonusDaily:
    """近 N 天加分经验按天累加 + 补零序列（经验详情弹窗 bonus 侧数据源）"""

    def test_zero_fill_full_window(self):
        today = datetime.date.today()
        result = accumulate_bonus_daily([], 7)
        assert len(result) == 7
        assert result[-1]['date'] == today.isoformat()
        assert result[0]['date'] == (today - datetime.timedelta(days=6)).isoformat()
        assert all(item['bonus'] == 0.0 for item in result)

    def test_accumulate_same_day_multiple(self):
        # 同一天多条加分 → 按天累加
        today = datetime.date.today()
        rows = [
            {'created_at': datetime.datetime.combine(today, datetime.time(10, 0)), 'amount': 20.0},
            {'created_at': datetime.datetime.combine(today, datetime.time(11, 0)), 'amount': 10.0},
        ]
        result = accumulate_bonus_daily(rows, 7)
        assert result[-1]['bonus'] == 30.0
        assert sum(item['bonus'] for item in result[:-1]) == 0.0

    def test_string_created_at(self):
        # DB 返回字符串 'YYYY-MM-DD HH:MM:SS' 也能解析
        today = datetime.date.today()
        rows = [{'created_at': f'{today.isoformat()} 20:15:33', 'amount': 20.0}]
        result = accumulate_bonus_daily(rows, 7)
        assert result[-1]['bonus'] == 20.0

    def test_out_of_window_ignored(self):
        today = datetime.date.today()
        old = today - datetime.timedelta(days=10)
        rows = [{'created_at': old, 'amount': 999.0}]
        result = accumulate_bonus_daily(rows, 7)
        assert all(item['bonus'] == 0.0 for item in result)

    def test_invalid_date_skipped(self):
        today = datetime.date.today()
        rows = [
            {'created_at': 'not-a-date', 'amount': 10.0},
            {'created_at': datetime.datetime.combine(today, datetime.time(8, 0)), 'amount': 5.0},
        ]
        result = accumulate_bonus_daily(rows, 7)
        assert result[-1]['bonus'] == 5.0


class TestBuildDailyXp:
    """listening + bonus 合并为每日总经验（7 天升序，total = listening + bonus）"""

    def _listening(self, dates, durations):
        return [{'date': d.isoformat(), 'duration': v} for d, v in zip(dates, durations)]

    def _bonus(self, dates, bonuses):
        return [{'date': d.isoformat(), 'bonus': v} for d, v in zip(dates, bonuses)]

    def test_merge_with_total(self):
        today = datetime.date.today()
        dates = [today - datetime.timedelta(days=6) + datetime.timedelta(days=i) for i in range(7)]
        listening = self._listening(dates, [100.0, 50.0, 0.0, 0.0, 0.0, 0.0, 30.0])
        bonus = self._bonus(dates, [0.0, 20.0, 0.0, 0.0, 0.0, 0.0, 10.0])
        result = build_daily_xp(listening, bonus)
        assert len(result) == 7
        assert result[0] == {'date': dates[0].isoformat(), 'listening': 100.0, 'bonus': 0.0, 'total': 100.0}
        assert result[1]['bonus'] == 20.0 and result[1]['total'] == 70.0
        assert result[6]['total'] == 40.0
        # 升序日期
        assert [item['date'] for item in result] == [d.isoformat() for d in dates]
