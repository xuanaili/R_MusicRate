# MusicRate\backend\tests\test_lyric_recognizer.py 歌词识别器纯函数单测（v0.8 P1 spike + v0.8.1 P0，零 DB / 零模型依赖）
# 测试对象：backend/utils/lyric_recognizer.py 的纯逻辑部分
#   （模型加载/转写属 realdata：依赖 faster-whisper + 音频文件，由 lyric_spike.py CLI 实测，不进单测）
# 覆盖（P1）：文本清洗 / segment→items（1位小数去重升序）/ 按 tracks_time 边界切分 / 单曲相对时间存储文本
# 覆盖（P0 识别器升级）：is_hallucination 噪音模式 / filter_segments no_speech_prob 阈值 /
#   to_simplified OpenCC 繁转简（含 opencc 缺失回退）/ segments_to_items 接入过滤+转简
import pytest

from backend.utils.lyric_recognizer import (
    clean_segment_text,
    filter_segments,
    is_hallucination,
    segments_to_items,
    split_by_tracks_time,
    to_simplified,
    track_items_to_storage,
)


class TestCleanSegmentText:
    """whisper 噪音 token 清洗：方括号噪音 / 音符符 / 多空格归一"""

    def test_bracket_noise_removed(self):
        assert clean_segment_text('[Music] 在无风的午后') == '在无风的午后'

    def test_blank_audio_removed(self):
        assert clean_segment_text('[BLANK_AUDIO]') == ''

    def test_music_note_removed(self):
        assert clean_segment_text('♪ 旋律 ♫ 还在') == '旋律 还在'

    def test_multiple_spaces_collapsed(self):
        assert clean_segment_text('  飞向   远方的  天空  ') == '飞向 远方的 天空'

    def test_empty_and_none(self):
        assert clean_segment_text('') == ''
        assert clean_segment_text('   ') == ''
        assert clean_segment_text(None) == ''


class TestSegmentsToItems:
    """segment 列表 → [{time, text}]：时间 1 位小数、升序、同时间去重保留首个"""

    def test_basic_round_and_sort(self):
        segs = [
            {'start': 12.346, 'end': 15.0, 'text': '后来'},
            {'start': 5.003, 'end': 8.0, 'text': '一开始'},
        ]
        items = segments_to_items(segs)
        assert items == [
            {'time': 5.0, 'text': '一开始'},
            {'time': 12.3, 'text': '后来'},
        ]

    def test_dedupe_same_rounded_time_keeps_first(self):
        segs = [
            {'start': 10.04, 'end': 12.0, 'text': '第一句'},
            {'start': 10.03, 'end': 12.5, 'text': '第二句同时间'},
        ]
        items = segments_to_items(segs)
        # 10.04 与 10.03 四舍五入到 1 位小数都是 10.0 → 保留首个
        assert [it['text'] for it in items] == ['第一句']

    def test_empty_text_skipped(self):
        segs = [
            {'start': 0.0, 'end': 2.0, 'text': '[BLANK_AUDIO]'},
            {'start': 2.5, 'end': 5.0, 'text': '真实歌词'},
        ]
        items = segments_to_items(segs)
        assert items == [{'time': 2.5, 'text': '真实歌词'}]

    def test_whitespace_text_skipped(self):
        segs = [{'start': 1.0, 'end': 2.0, 'text': '   '}]
        assert segments_to_items(segs) == []

    def test_half_up_rounding_matches_lrc(self):
        # 与 lrc._round_tenths 一致：.x5 半进位（Python round 是银行家舍入，不能用）
        segs = [{'start': 1.25, 'end': 2.0, 'text': 'a'}]
        assert segments_to_items(segs)[0]['time'] == 1.3

    # ---------- v0.8.1 P0 识别器升级接入 ----------

    def test_traditional_converted_to_simplified(self):
        # whisper 中文输出繁体 → 落库统一简体（OpenCC t2s）
        segs = [{'start': 10.0, 'end': 12.0, 'text': '某夜你離開'}]
        assert segments_to_items(segs) == [{'time': 10.0, 'text': '某夜你离开'}]

    def test_high_no_speech_prob_segment_dropped(self):
        # no_speech_prob > 0.6 → 器乐/静音段幻觉，丢弃
        segs = [
            {'start': 0.0, 'end': 3.0, 'text': '正常歌词', 'no_speech_prob': 0.05},
            {'start': 5.0, 'end': 8.0, 'text': '幻觉输出', 'no_speech_prob': 0.91},
        ]
        assert [it['text'] for it in segments_to_items(segs)] == ['正常歌词']

    def test_missing_no_speech_prob_kept(self):
        # 无 no_speech_prob 字段（旧数据/旧测试）→ 视为 0，不过滤
        segs = [{'start': 1.0, 'end': 2.0, 'text': '旧数据'}]
        assert [it['text'] for it in segments_to_items(segs)] == ['旧数据']

    def test_hallucination_credit_line_dropped(self):
        # 制作信息幻觉（spike 确认「詞曲 李宗盛」）→ 丢弃
        segs = [
            {'start': 0.0, 'end': 2.0, 'text': '詞曲 李宗盛', 'no_speech_prob': 0.1},
            {'start': 3.0, 'end': 5.0, 'text': '真實歌詞', 'no_speech_prob': 0.1},
        ]
        assert [it['text'] for it in segments_to_items(segs)] == ['真实歌词']


class TestSplitByTracksTime:
    """按 tracks_time 边界把整轨绝对时间条目分到各单曲
    归属规则（与前端 initTrackLyricsMap 一致）：st <= t < 下一首 st；tracks_time[i] 是第 i 首起始秒
    """

    def test_middle_item_to_correct_track(self):
        items = [
            {'time': 100.0, 'text': '第一首里'},
            {'time': 300.0, 'text': '第二首里'},
            {'time': 500.0, 'text': '第三首里'},
        ]
        groups = split_by_tracks_time(items, [0, 254, 334, 516])
        assert [it['text'] for it in groups[0]] == ['第一首里']
        assert [it['text'] for it in groups[1]] == ['第二首里']
        assert [it['text'] for it in groups[2]] == ['第三首里']

    def test_exact_boundary_belongs_to_later_track(self):
        items = [{'time': 254.0, 'text': '恰好在边界'}]
        groups = split_by_tracks_time(items, [0, 254, 334])
        # 254 是第 1 首（index 1）的起点 → 归属第 1 首
        assert 1 in groups and groups[1][0]['text'] == '恰好在边界'

    def test_item_before_first_boundary(self):
        items = [{'time': 0.0, 'text': '起点'}]
        groups = split_by_tracks_time(items, [10, 100])
        assert groups[0][0]['text'] == '起点'

    def test_item_after_last_boundary_goes_to_last_track(self):
        items = [{'time': 2000.0, 'text': '末曲'}]
        groups = split_by_tracks_time(items, [0, 100, 500])
        assert groups[2][0]['text'] == '末曲'

    def test_no_boundaries_all_to_track_zero(self):
        items = [{'time': 5.0, 'text': 'a'}, {'time': 9.0, 'text': 'b'}]
        groups = split_by_tracks_time(items, [])
        assert set(groups.keys()) == {0}
        assert len(groups[0]) == 2

    def test_empty_items_returns_empty_groups(self):
        groups = split_by_tracks_time([], [0, 100])
        assert groups == {}


class TestTrackItemsToStorage:
    """单曲条目 → 相对时间存储文本（减 track_start，格式复用 lrc.items_to_storage）"""

    def test_relative_time_output(self):
        items = [
            {'time': 260.0, 'text': '第二首第一句'},
            {'time': 275.5, 'text': '第二首第二句'},
        ]
        out = track_items_to_storage(items, 254)
        assert out == '00:06 第二首第一句\n00:21.5 第二首第二句'

    def test_relative_dedupe(self):
        # 两个绝对时间减起点后落到同一相对秒（254.03/254.04 四舍五入都 254.0）→ 保留最早出现者
        # （先按绝对时间排序，绝对更早的 254.03 胜出——与 segments_to_items「保留首个」语义一致）
        items = [
            {'time': 254.04, 'text': '较晚一条'},
            {'time': 254.03, 'text': '最早一条'},
        ]
        out = track_items_to_storage(items, 0)
        assert '最早一条' in out
        assert '较晚一条' not in out

    def test_empty_items(self):
        assert track_items_to_storage([], 100) == ''


class TestIsHallucination:
    """v0.8.1 P0：幻觉噪音文本判定（制作信息 / 字幕 / 器乐名）"""

    def test_credit_line_detected(self):
        # spike 确认的「詞曲 李宗盛」制作信息幻觉
        assert is_hallucination('詞曲 李宗盛') is True
        assert is_hallucination('作詞 方文山') is True
        assert is_hallucination('作曲 林俊傑') is True
        assert is_hallucination('编曲 陈伟') is True

    def test_subtitle_detected(self):
        # spike 确认的「字幕by索兰娅」字幕幻觉
        assert is_hallucination('字幕by索兰娅') is True

    def test_instrument_label_detected(self):
        # spike 确认的「Zither Harp」器乐名幻觉 + 常见器乐英文名
        assert is_hallucination('Zither Harp') is True
        assert is_hallucination('instrumental') is True
        assert is_hallucination('Guitar') is True

    def test_normal_lyric_not_detected(self):
        assert is_hallucination('某夜你离开') is False
        assert is_hallucination('在无风的午后') is False
        assert is_hallucination('将甘苦注入汤') is False

    def test_empty_text_is_hallucination(self):
        assert is_hallucination('') is True
        assert is_hallucination('   ') is True
        assert is_hallucination(None) is True


class TestFilterSegments:
    """v0.8.1 P0：segment 级幻觉过滤（no_speech_prob 阈值 + 噪音模式）"""

    def test_drops_high_no_speech_prob(self):
        segs = [
            {'start': 0.0, 'end': 2.0, 'text': '正常', 'no_speech_prob': 0.1},
            {'start': 3.0, 'end': 5.0, 'text': '幻觉', 'no_speech_prob': 0.85},
        ]
        out = filter_segments(segs)
        assert len(out) == 1 and out[0]['text'] == '正常'

    def test_threshold_is_strict_greater(self):
        # no_speech_prob 恰等于阈值 0.6 → 保留（> 严格大于才丢弃）
        segs = [{'start': 0.0, 'end': 2.0, 'text': '边界', 'no_speech_prob': 0.6}]
        assert len(filter_segments(segs)) == 1

    def test_missing_no_speech_prob_kept(self):
        segs = [{'start': 0.0, 'end': 2.0, 'text': '旧数据'}]
        assert len(filter_segments(segs)) == 1
        # None 也安全（视为 0）
        segs = [{'start': 0.0, 'end': 2.0, 'text': '旧数据', 'no_speech_prob': None}]
        assert len(filter_segments(segs)) == 1

    def test_credit_and_instrument_dropped(self):
        segs = [
            {'start': 0.0, 'end': 2.0, 'text': '詞曲 李宗盛', 'no_speech_prob': 0.1},
            {'start': 2.5, 'end': 4.0, 'text': 'Zither Harp', 'no_speech_prob': 0.1},
            {'start': 5.0, 'end': 7.0, 'text': '真实歌词', 'no_speech_prob': 0.1},
        ]
        out = filter_segments(segs)
        assert [s['text'] for s in out] == ['真实歌词']

    def test_bracket_noise_cleaned_to_empty_dropped(self):
        # [BLANK_AUDIO]/[Music] 纯噪音：clean 后为空 → 丢弃
        segs = [
            {'start': 0.0, 'end': 2.0, 'text': '[BLANK_AUDIO]'},
            {'start': 3.0, 'end': 5.0, 'text': '旋律 还在'},
        ]
        out = filter_segments(segs)
        assert [s['text'] for s in out] == ['旋律 还在']

    def test_keeps_segment_structure(self):
        # 保留原 segment 结构（含 no_speech_prob 等字段），供下游 segments_to_items 使用
        segs = [{'start': 1.0, 'end': 2.0, 'text': '保留', 'no_speech_prob': 0.05, 'extra': 1}]
        out = filter_segments(segs)
        assert out[0] == segs[0]


class TestToSimplified:
    """v0.8.1 P0：OpenCC t2s 繁转简（全站统一简体）"""

    def test_traditional_to_simplified(self):
        assert to_simplified('某夜你離開') == '某夜你离开'
        assert to_simplified('將甘苦注入湯') == '将甘苦注入汤'
        assert to_simplified('後來 我總算學會了如何去愛') == '后来 我总算学会了如何去爱'

    def test_simplified_unchanged(self):
        assert to_simplified('在无风的午后') == '在无风的午后'

    def test_empty_and_none(self):
        assert to_simplified('') == ''
        assert to_simplified(None) is None

    def test_fallback_when_opencc_fails(self, monkeypatch):
        # opencc 不可用 / 初始化失败 → 回退原文本，不阻断识别管线
        import backend.utils.lyric_recognizer as mod
        monkeypatch.setattr(mod, '_simplifier', False)
        assert to_simplified('繁體測試') == '繁體測試'
