# MusicRate\backend\tests\test_tempo_analyzer.py BPM 节奏分析纯函数单测（v0.8.1 P4）
# 测试对象：backend/utils/tempo_analyzer.py
#   - get_track_boundaries（纯逻辑，零依赖）
#   - build_tempo_result（纯聚合）
#   - extract_tempo / analyze_tempo（librosa 测拍；用合成节拍音 + 临时 wav，零 DB）
import os
import tempfile

import numpy as np
import pytest

from backend.utils.tempo_analyzer import (
    SAMPLE_RATE,
    analyze_tempo,
    build_tempo_result,
    extract_tempo,
    get_track_boundaries,
)


def _click_track(bpm, seconds=30.0, sr=SAMPLE_RATE):
    """合成一段固定 BPM 的节拍音（周期性冲激），用于测拍验证"""
    y = np.zeros(int(sr * seconds))
    interval = 60.0 / bpm
    t = 0.0
    while t < seconds:
        idx = int(t * sr)
        if idx < len(y):
            y[idx] = 1.0
        t += interval
    return y


# ==================== get_track_boundaries ====================

class TestGetTrackBoundaries:
    def test_no_tracks_time_single_segment(self):
        assert get_track_boundaries([], 600.0) == [(0.0, 600.0)]

    def test_none_tracks_time_single_segment(self):
        assert get_track_boundaries(None, 600.0) == [(0.0, 600.0)]

    def test_with_leading_zero(self):
        # [0,254,334,516] + 总长 600 → 4 首
        assert get_track_boundaries([0, 254, 334, 516], 600.0) == [
            (0.0, 254.0), (254.0, 334.0), (334.0, 516.0), (516.0, 600.0),
        ]

    def test_no_leading_zero_prepends_zero(self):
        # 无 0 起点 → 第一首仍从 0 开始（与 split_by_tracks_time 口径一致）
        assert get_track_boundaries([254, 334], 600.0) == [
            (0.0, 254.0), (254.0, 334.0), (334.0, 600.0),
        ]

    def test_none_and_duplicates_filtered(self):
        # None/重复边界被过滤
        assert get_track_boundaries([0, None, 254, 254, 516], 600.0) == [
            (0.0, 254.0), (254.0, 516.0), (516.0, 600.0),
        ]

    def test_boundary_beyond_total_filtered(self):
        assert get_track_boundaries([0, 254, 700], 600.0) == [(0.0, 254.0), (254.0, 600.0)]

    def test_zero_or_negative_total_returns_empty(self):
        assert get_track_boundaries([0, 254], 0) == []
        assert get_track_boundaries([0, 254], -1) == []

    def test_boundaries_unsorted_are_sorted(self):
        assert get_track_boundaries([334, 0, 254], 600.0) == [
            (0.0, 254.0), (254.0, 334.0), (334.0, 600.0),
        ]


# ==================== build_tempo_result ====================

class TestBuildTempoResult:
    def test_valid_tempos(self):
        r = build_tempo_result([120.0, 90.0, 150.0], [60.0, 40.0, 50.0])
        assert r['track_tempos'] == [120.0, 90.0, 150.0]
        assert r['track_durations'] == [60.0, 40.0, 50.0]
        assert r['avg_bpm'] == 120.0
        assert r['min_bpm'] == 90.0
        assert r['max_bpm'] == 150.0

    def test_avg_rounded_one_decimal(self):
        r = build_tempo_result([120.0, 90.1], [60.0, 40.0])
        assert r['avg_bpm'] == 105.1  # (120.0+90.1)/2=105.05 → 105.1（四舍五入）

    def test_all_zero_returns_zero_aggregates(self):
        r = build_tempo_result([0.0, 0.0], [30.0, 30.0])
        assert r['avg_bpm'] == 0.0
        assert r['min_bpm'] == 0.0
        assert r['max_bpm'] == 0.0
        assert r['track_tempos'] == [0.0, 0.0]

    def test_mixed_zero_only_valid_counted(self):
        # 0 表示该段无法测拍（过短/静音），聚合只计有效值
        r = build_tempo_result([120.0, 0.0, 80.0], [60.0, 10.0, 30.0])
        assert r['avg_bpm'] == 100.0  # (120+80)/2
        assert r['min_bpm'] == 80.0
        assert r['max_bpm'] == 120.0


# ==================== extract_tempo ====================

class TestExtractTempo:
    def test_empty_audio_returns_zero(self):
        assert extract_tempo(np.array([])) == 0.0

    def test_too_short_audio_returns_zero(self):
        y = np.zeros(SAMPLE_RATE * 2)  # 2s < MIN_TEMPO_SEGMENT_SECS
        assert extract_tempo(y) == 0.0

    def test_known_bpm_click_track(self):
        # 120 BPM 节拍音 → 测回 ≈120（容差 ±8，DP 估计可能略偏）
        y = _click_track(120)
        bpm = extract_tempo(y)
        assert bpm == pytest.approx(120, abs=8), bpm

    def test_slower_bpm_click_track(self):
        y = _click_track(90)
        bpm = extract_tempo(y)
        assert bpm == pytest.approx(90, abs=8), bpm


# ==================== analyze_tempo（临时 wav 端到端） ====================

class TestAnalyzeTempo:
    def test_whole_track_single_segment(self):
        # 临时 wav：30s 120BPM 节拍音 → 无边界 → 单段，track_tempos=[~120]
        import soundfile as sf
        y = _click_track(120)
        fd, path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        try:
            sf.write(path, y, SAMPLE_RATE)
            r = analyze_tempo(path, [])
            assert len(r['track_tempos']) == 1
            assert r['track_tempos'][0] == pytest.approx(120, abs=8)
            assert r['track_durations'] == [pytest.approx(30.0, abs=0.5)]
            assert r['avg_bpm'] == r['track_tempos'][0]
            assert r['min_bpm'] == r['max_bpm'] == r['track_tempos'][0]
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_split_by_boundaries(self):
        # 30s wav，边界 [0, 15] → 两段各 15s，每段 120BPM
        import soundfile as sf
        y = _click_track(120, seconds=30)
        fd, path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        try:
            sf.write(path, y, SAMPLE_RATE)
            r = analyze_tempo(path, [0, 15])
            assert len(r['track_tempos']) == 2
            assert r['track_durations'] == [pytest.approx(15.0, abs=0.5), pytest.approx(15.0, abs=0.5)]
            for bpm in r['track_tempos']:
                assert bpm == pytest.approx(120, abs=8), r
        finally:
            if os.path.exists(path):
                os.remove(path)
