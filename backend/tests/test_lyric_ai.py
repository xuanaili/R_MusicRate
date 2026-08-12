# MusicRate\backend\tests\test_lyric_ai.py 歌词 AI 识别任务纯逻辑单测（零 DB 依赖，v0.8.1 增补：进度条）
# 测试对象：lyric_ai.py 的 _map_transcribe_progress（转写比例 → 任务进度 10~90 映射）
from backend.api.lyric_ai import _map_transcribe_progress


class TestMapTranscribeProgress:
    def test_zero_ratio_maps_to_start(self):
        # 刚开转写 → 进度 10
        assert _map_transcribe_progress(0.0) == 10

    def test_full_ratio_maps_to_90(self):
        # 转写完成 → 进度 90（剩余 90 写入歌词 / 93 校正 / 100 完成）
        assert _map_transcribe_progress(1.0) == 90

    def test_half_ratio_maps_to_middle(self):
        # 转写一半 → 进度 50
        assert _map_transcribe_progress(0.5) == 50

    def test_quarter_ratio(self):
        assert _map_transcribe_progress(0.25) == 30

    def test_three_quarters_ratio(self):
        assert _map_transcribe_progress(0.75) == 70

    def test_monotonic_increasing(self):
        # 进度随 ratio 单调不减（进度条不倒退）
        prev = -1
        for i in range(0, 101):
            p = _map_transcribe_progress(i / 100)
            assert p >= prev, f'ratio={i/100} 进度倒退 {prev}→{p}'
            prev = p

    def test_out_of_range_clamped(self):
        # 越界 ratio 收敛到边界（防转写尾段 end 略超 duration）
        assert _map_transcribe_progress(-0.5) == 10
        assert _map_transcribe_progress(2.0) == 90
