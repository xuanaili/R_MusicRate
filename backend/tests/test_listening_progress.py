# MusicRate\backend\tests\test_listening_progress.py 听取进度规范化纯逻辑单测（零 DB 依赖）
# 测试对象：backend/api/listening.py 的 normalize_progress()
# 规则：非法/负数→0；超过音频时长→clamp 到时长；保留 1 位小数（与听取时长口径一致）
from backend.api.listening import normalize_progress


class TestNormalizeProgress:
    def test_none_to_zero(self):
        assert normalize_progress(None) == 0.0

    def test_zero_to_zero(self):
        assert normalize_progress(0) == 0.0

    def test_empty_string_to_zero(self):
        assert normalize_progress('') == 0.0

    def test_negative_to_zero(self):
        assert normalize_progress(-5) == 0.0

    def test_non_numeric_to_zero(self):
        assert normalize_progress('abc') == 0.0

    def test_round_to_one_decimal(self):
        # 与 listening_duration 的 round(...,1) 口径一致
        assert normalize_progress(123.456) == 123.5

    def test_numeric_string_parsed(self):
        assert normalize_progress('42.5') == 42.5

    def test_exceeds_duration_clamped(self):
        # 进度超过整轨时长 → 收敛到时长（防续播越界）
        assert normalize_progress(400, duration=300) == 300.0

    def test_within_duration_unchanged(self):
        assert normalize_progress(120.5, duration=300) == 120.5

    def test_negative_ignores_duration_clamp(self):
        # 负数仍收敛到 0，而不是被 duration 抬高
        assert normalize_progress(-1, duration=300) == 0.0
