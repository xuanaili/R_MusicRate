# MusicRate\backend\tests\test_lrc.py LRC 纯函数单测（v0.8 P0-A，零 DB 依赖）
# 测试对象：backend/utils/lrc.py
# 验收基准：与前端 AlbumLyricViewer.vue parseLrcToStandardFormat 输出「逐字符一致」
# （基准由 node 跑前端原样函数生成，见 _gen_frontend_lrc_samples.js，跑完即删）
import pytest

from backend.utils.lrc import (
    items_to_storage,
    normalize_to_storage,
    parse_any_to_items,
    seconds_to_str,
    str_to_seconds,
    validate_lyric_text,
)


class TestStrToSeconds:
    """时间字符串 'mm:ss' / 'mm:ss.xx' → 秒数（浮点，小数按真实位数）"""

    def test_zero(self):
        assert str_to_seconds('00:00') == 0

    def test_plain_seconds(self):
        assert str_to_seconds('00:05') == 5

    def test_with_minutes(self):
        assert str_to_seconds('01:30') == 90

    def test_one_decimal(self):
        # '.5' = 0.5 秒（存储格式 1 位小数语义）
        assert str_to_seconds('00:05.5') == 5.5

    def test_two_decimal(self):
        assert str_to_seconds('00:05.50') == 5.5

    def test_two_decimal_tenths(self):
        assert str_to_seconds('00:05.05') == pytest.approx(5.05)

    def test_three_decimal(self):
        assert str_to_seconds('00:15.123') == pytest.approx(15.123)

    def test_over_minute_decimal(self):
        assert str_to_seconds('10:30.25') == pytest.approx(630.25)

    def test_none_and_empty(self):
        assert str_to_seconds(None) == 0
        assert str_to_seconds('') == 0

    def test_invalid_falls_back_zero(self):
        assert str_to_seconds('abc') == 0


class TestSecondsToStr:
    """秒数 → 存储格式 'mm:ss' 或 'mm:ss.x'（1 位小数，为 0 省略；与前端逐字符一致）"""

    def test_zero(self):
        assert seconds_to_str(0) == '00:00'

    def test_whole_seconds_no_decimal(self):
        assert seconds_to_str(5) == '00:05'

    def test_with_minutes_padded(self):
        assert seconds_to_str(305.5) == '05:05.5'

    def test_tenth_second_shown(self):
        assert seconds_to_str(10.1) == '00:10.1'

    def test_half_second(self):
        assert seconds_to_str(5.5) == '00:05.5'

    def test_rounding_to_tenths(self):
        # 15.123 → 15.1（四舍五入到 1 位小数）
        assert seconds_to_str(15.123) == '00:15.1'

    def test_round_half_up(self):
        # 半值进位（复制前端 Math.round 语义）：10.05 → 10.1
        assert seconds_to_str(10.05) == '00:10.1'

    def test_over_hour(self):
        assert seconds_to_str(3600) == '60:00'

    def test_negative_treated_as_zero(self):
        assert seconds_to_str(-1) == '00:00'

    def test_none_treated_as_zero(self):
        assert seconds_to_str(None) == '00:00'


class TestParseAnyToItems:
    """任意歌词文本 → 条目 [{time, text}, ...]：LRC 方括号 或 存储格式 双路径"""

    def test_lrc_bracket_single(self):
        items = parse_any_to_items('[00:05.00]第一句')
        assert items == [{'time': 5.0, 'text': '第一句'}]

    def test_lrc_multi_tags_merge_text(self):
        items = parse_any_to_items('[00:05.00]第二句[00:08.50]第三句')
        assert items == [
            {'time': 5.0, 'text': '第二句第三句'},
            {'time': 8.5, 'text': '第二句第三句'},
        ]

    def test_lrc_metadata_filtered(self):
        items = parse_any_to_items('[00:00.00]作词：方文山\n[00:01.00]正文')
        assert items == [{'time': 1.0, 'text': '正文'}]

    def test_lrc_empty_text_skipped(self):
        assert parse_any_to_items('[00:05.00]\n[00:06.00]有文字') == [{'time': 6.0, 'text': '有文字'}]

    def test_lrc_no_time_tags_skipped(self):
        assert parse_any_to_items('[ti:标题]\n普通行') == []

    def test_storage_format_parsed(self):
        items = parse_any_to_items('00:05.5 歌词一\n00:10 歌词二')
        assert items == [{'time': 5.5, 'text': '歌词一'}, {'time': 10.0, 'text': '歌词二'}]

    def test_storage_sorted(self):
        items = parse_any_to_items('00:05 后出现\n00:01 先出现')
        assert items == [{'time': 1.0, 'text': '先出现'}, {'time': 5.0, 'text': '后出现'}]

    def test_dedup_keeps_first(self):
        items = parse_any_to_items('[00:03.00]重复A\n[00:03.00]重复B')
        assert items == [{'time': 3.0, 'text': '重复A'}]

    def test_crlf_normalized(self):
        assert parse_any_to_items('[00:01.00]a\r\n[00:02.00]b') == [
            {'time': 1.0, 'text': 'a'},
            {'time': 2.0, 'text': 'b'},
        ]

    def test_none_returns_empty(self):
        assert parse_any_to_items(None) == []
        assert parse_any_to_items('') == []


class TestNormalizeToStorage:
    """任意歌词 → 存储格式文本（与前端 parseLrcToStandardFormat 输出逐字符一致）"""

    def test_basic_metadata(self):
        src = '[ti:七里香]\n[ar:周杰伦]\n[offset:500]\n[00:00.00]intro\n[00:05.00]第一句\n' \
              '[00:10.50]第二句\n[00:15.123]第三句\n[00:20]第四句无小数\n[00:30]作词：方文山'
        assert normalize_to_storage(src) == '00:00 intro\n00:05 第一句\n00:10.5 第二句\n00:15.1 第三句\n00:20 第四句无小数'

    def test_multi_tags(self):
        src = '[00:01.00]开始\n[00:05.00]第二句[00:08.50]第三句'
        assert normalize_to_storage(src) == '00:01 开始\n00:05 第二句第三句\n00:08.5 第二句第三句'

    def test_dedup_same_time(self):
        assert normalize_to_storage('[00:03.00]重复A\n[00:03.00]重复B') == '00:03 重复A'

    def test_half_second_quirk(self):
        # [00:10.5] 被前端当百分秒 0.05 → 10.05 → 四舍五入 10.1；[00:10.50] 才是 0.5 秒
        src = '[00:10.5]半秒当百分秒\n[00:10.50]点五零\n[00:10.500]点五零零'
        assert normalize_to_storage(src) == '00:10.1 半秒当百分秒\n00:10.5 点五零'

    def test_empty_text_skipped(self):
        assert normalize_to_storage('[00:05.00]\n[00:06.00]有文字') == '00:06 有文字'

    def test_plain_decimal(self):
        src = '[00:00.00]开头\n[01:02.3]一分零二点三'
        assert normalize_to_storage(src) == '00:00 开头\n01:02 一分零二点三'

    def test_sorted_reorder(self):
        assert normalize_to_storage('[00:05.00]后出现\n[00:01.00]先出现') == '00:01 先出现\n00:05 后出现'

    def test_storage_input_idempotent(self):
        canonical = '00:05.5 歌词一\n00:10 歌词二'
        assert normalize_to_storage(canonical) == canonical

    def test_none_returns_empty(self):
        assert normalize_to_storage(None) == ''
        assert normalize_to_storage('') == ''


class TestItemsToStorage:
    """条目列表 → 存储文本：按时间升序、每行 'mm:ss(.x) 歌词'"""

    def test_sorted_output(self):
        items = [{'time': 8.5, 'text': 'b'}, {'time': 1.0, 'text': 'a'}]
        assert items_to_storage(items) == '00:01 a\n00:08.5 b'

    def test_empty(self):
        assert items_to_storage([]) == ''


class TestValidateLyricText:
    """歌词文本合法性校验：空 → 拒绝；无法解析出有效行 → 拒绝；合法 → 通过"""

    def test_empty_rejected(self):
        ok, msg = validate_lyric_text('')
        assert ok is False and '不能为空' in msg

    def test_whitespace_rejected(self):
        ok, msg = validate_lyric_text('   \n  ')
        assert ok is False

    def test_no_valid_line_rejected(self):
        ok, msg = validate_lyric_text('随便一段没有时间的文字')
        assert ok is False and '有效' in msg

    def test_lrc_valid(self):
        ok, _ = validate_lyric_text('[00:00.00]歌词')
        assert ok is True

    def test_storage_valid(self):
        ok, _ = validate_lyric_text('00:05 歌词\n00:10 歌词二')
        assert ok is True

    def test_metadata_only_rejected(self):
        ok, msg = validate_lyric_text('[00:00.00]作词：方文山')
        assert ok is False
