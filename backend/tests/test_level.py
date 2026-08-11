# MusicRate\backend\tests\test_level.py 等级经验纯逻辑单测（v0.7.1 P0，零 DB 依赖）
# 测试对象：backend/utils/level.py
# 规则（README v0.7.1 已定决策）：
# - level = floor(sqrt(xp / 3600))，Lv.N 约需 N² 小时（Lv.1=3600、Lv.2=14400、Lv.3=32400、Lv.5=90000、Lv.10=360000）
# - 每日加分（评分/听后感/评论合计）上限 100 XP，实际加分 = min(amount, 100 - today_bonus)，可为部分或 0
import pytest

from backend.utils.level import (
    DAILY_BONUS_LIMIT,
    compute_bonus_gain,
    compute_level,
    level_progress,
    level_title,
    xp_to_next_level,
)


class TestComputeLevel:
    """等级推导：floor(sqrt(xp/3600))，Lv.N 约需 N² 小时"""

    def test_zero_xp(self):
        assert compute_level(0) == 0

    def test_below_first_hour(self):
        assert compute_level(3599) == 0

    def test_first_hour_is_level_one(self):
        assert compute_level(3600) == 1

    def test_just_below_second_level(self):
        assert compute_level(14399) == 1

    def test_four_hours_is_level_two(self):
        assert compute_level(14400) == 2

    def test_nine_hours_is_level_three(self):
        assert compute_level(32400) == 3

    def test_25_hours_is_level_five(self):
        # README 示例：Lv.5=90000（25h）
        assert compute_level(90000) == 5

    def test_100_hours_is_level_ten(self):
        # README 示例：Lv.10=360000（100h）
        assert compute_level(360000) == 10

    def test_negative_treated_as_zero(self):
        assert compute_level(-100) == 0

    def test_none_treated_as_zero(self):
        assert compute_level(None) == 0

    def test_float_input(self):
        assert compute_level(3600.0) == 1


class TestXpToNextLevel:
    """距下一级所需经验：下一级边界 − 当前 xp，最少为 1"""

    def test_zero_needs_first_hour(self):
        assert xp_to_next_level(0) == 3600

    def test_one_xp_left_to_next(self):
        assert xp_to_next_level(3599) == 1

    def test_at_level_one_boundary(self):
        # 刚升到 Lv.1（3600），距 Lv.2（14400）还差 10800
        assert xp_to_next_level(3600) == 10800

    def test_just_below_level_two(self):
        assert xp_to_next_level(14399) == 1

    def test_at_level_two_boundary(self):
        assert xp_to_next_level(14400) == 18000

    def test_fractional_xp_ceil(self):
        # 0.5 距 3600 差 3599.5 → ceil = 3600
        assert xp_to_next_level(0.5) == 3600

    def test_higher_level_need(self):
        assert xp_to_next_level(90000) == (6 ** 2) * 3600 - 90000  # 129600-90000=39600


class TestLevelProgress:
    """当前级内进度 0~1：xp 在当前级 [base, next) 区间内的位置"""

    def test_zero_progress(self):
        assert level_progress(0) == 0.0

    def test_half_of_first_level(self):
        # Lv.0 区间 [0,3600)，1800 → 0.5
        assert level_progress(1800) == 0.5

    def test_start_of_level_two(self):
        # xp=3600 升到 Lv.1，区间 [3600,14400) 起点 → 0
        assert level_progress(3600) == 0.0

    def test_middle_of_level_two(self):
        # Lv.1 区间跨度 10800，9000 处进度 = 5400/10800 = 0.5
        assert level_progress(9000) == 0.5

    def test_exactly_at_next_boundary_resets(self):
        # xp=14400 已升到 Lv.2 → 进度归 0
        assert level_progress(14400) == 0.0

    def test_near_boundary_approaches_one(self):
        assert level_progress(14399.9) > 0.99

    def test_none_treated_as_zero(self):
        assert level_progress(None) == 0.0


class TestLevelTitle:
    """等级称号分段：Lv0-3 初听者 → Lv4-7 爱乐人 → Lv8-12 资深乐迷 → 更高段位"""

    def test_level_zero(self):
        assert level_title(0) == '初听者'

    def test_level_three(self):
        assert level_title(3) == '初听者'

    def test_level_four(self):
        assert level_title(4) == '爱乐人'

    def test_level_seven(self):
        assert level_title(7) == '爱乐人'

    def test_level_eight(self):
        assert level_title(8) == '资深乐迷'

    def test_level_twelve(self):
        assert level_title(12) == '资深乐迷'

    def test_level_thirteen(self):
        assert level_title(13) == '音乐行家'

    def test_level_twenty(self):
        assert level_title(20) == '乐评达人'

    def test_level_thirty_plus(self):
        assert level_title(30) == '传奇乐迷'
        assert level_title(99) == '传奇乐迷'


class TestBonusLimit:
    """每日加分上限：实际加分 = min(amount, 100 - today_bonus)，可为部分或 0"""

    def test_limit_is_100(self):
        assert DAILY_BONUS_LIMIT == 100

    def test_full_amount_within_limit(self):
        assert compute_bonus_gain(0, 20) == 20

    def test_partial_amount_at_limit(self):
        # 已加 90，再加 20 → 只能加 10
        assert compute_bonus_gain(90, 20) == 10

    def test_zero_remaining(self):
        assert compute_bonus_gain(100, 20) == 0

    def test_over_limit_today_clamped(self):
        # 防御：异常数据已超上限 → 不再加
        assert compute_bonus_gain(120, 20) == 0

    def test_small_bonus_always_full(self):
        assert compute_bonus_gain(50, 5) == 5

    def test_none_today_bonus(self):
        assert compute_bonus_gain(None, 20) == 20

    def test_zero_amount(self):
        assert compute_bonus_gain(0, 0) == 0
