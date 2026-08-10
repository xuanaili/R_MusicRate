# MusicRate\backend\tests\test_score.py 专辑综合评分计算函数单测（纯逻辑，零 DB 依赖）
# 测试对象：backend/utils/score.py 的 calculate_album_total_score()
# 评分规则：专辑总分 = 专辑整体评分 × 0.6 + 单曲均分 × 0.4（0 分单曲不计入）
from backend.utils.score import calculate_album_total_score


class TestCalculateAlbumTotalScore:
    def test_empty_list_returns_zero(self):
        assert calculate_album_total_score([]) == 0.0

    def test_non_list_returns_zero(self):
        assert calculate_album_total_score('abc') == 0.0
        assert calculate_album_total_score(None) == 0.0

    def test_only_album_score(self):
        # 无单曲评分，直接返回专辑整体评分
        assert calculate_album_total_score([50]) == 50

    def test_none_album_score_returns_zero(self):
        # 专辑整体评分为 None 且无单曲 → 0
        assert calculate_album_total_score([None]) == 0.0

    def test_standard_weighted_score(self):
        # 专辑50*0.6 + 单曲均分(100,20,30 → 50)*0.4 = 30 + 20 = 50
        assert calculate_album_total_score([50, 100, 20, 30, 0, 0]) == 50

    def test_all_zero_tracks_fall_back_to_album_score(self):
        # 单曲全为0 → 直接返回专辑整体评分
        assert calculate_album_total_score([50, 0, 0]) == 50

    def test_score_clamped_to_100(self):
        # 专辑120*0.6 + 单曲均分100*0.4 = 112 → 超上限截断为100
        assert calculate_album_total_score([120, 100, 100]) == 100

    def test_negative_clamped_to_0(self):
        # 负数被截断到下限0
        assert calculate_album_total_score([-50, 0, 0]) == 0.0

    def test_rounding_to_one_decimal(self):
        # 专辑50*0.6 + 单曲均分(33+33)/2=33*0.4 = 30+13.2 = 43.2
        assert calculate_album_total_score([50, 33, 33]) == 43.2
