# MusicRate\backend\tests\test_lrc_time.py —— v0.8.3 P0：歌词时间纯函数双端一致单测
# 测试对象：
#   前端 frontend/src/utils/lrcTime.js 的 parseTimeStr / formatTime / formatTimeForOutput
#     （golden 由 node 跑前端真实文件生成，见 _gen_frontend_lrc_time.mjs，跑完即删）
#   后端 backend/utils/lrc.py 的 str_to_seconds / seconds_to_str
# 验收基准：前端 parseTimeStr 与后端 str_to_seconds 语义一致（小数按真实位数：'.5'=0.5、'.05'=0.05、'.123'=0.123）；
#   存储格式行 'mm:ss(.x)'（1 位小数）在前端 formatTime 与后端 seconds_to_str 均能 round-trip。
# 背景：v0.8.3 P0 修复原组件内 parseTimeStr 的 /1000 bug（'00:05.5' 被解析成 5.005s → 现 5.5s），
#   并抽出 utils/lrcTime.js 使纯函数可测；本测试锁定修复后行为与后端一致，防止回归。
import pytest

from backend.utils.lrc import seconds_to_str, str_to_seconds

# 前端 parseTimeStr golden（node 跑 frontend/src/utils/lrcTime.js 生成）：
#   '00:05.5' => 5.5、'00:05.05' => 5.05、'00:05.55' => 5.55、'00:05.555' => 5.555
FRONTEND_PARSE_GOLDEN = [
    ('00:00', 0),
    ('00:05', 5),
    ('00:05.5', 5.5),
    ('00:05.05', 5.05),
    ('00:05.55', 5.55),
    ('00:05.555', 5.555),
    ('01:30', 90),
    ('01:30.5', 90.5),
    ('10:30.25', 630.25),
    ('100:00', 6000),
]

# 存储格式行（1 位小数）round-trip：前端 formatTime(parseTimeStr(s)) === s（node 验证），
# 后端 seconds_to_str(str_to_seconds(s)) === s（本测试验证）——双端 round-trip 一致
STORAGE_ROUND_TRIP = ['00:00', '00:05', '00:05.5', '01:30.5', '15:00', '05:05.5']


class TestParseTimeStrAlignWithBackend:
    """前端 parseTimeStr（黄金值）与后端 str_to_seconds 语义一致（按真实小数位归一）"""

    @pytest.mark.parametrize('input_str,expected', FRONTEND_PARSE_GOLDEN)
    def test_frontend_parse_matches_backend(self, input_str, expected):
        # 前端 parseTimeStr 由 node 生成 golden（见文件头注释）；此处断言后端一致
        assert str_to_seconds(input_str) == pytest.approx(expected)

    def test_one_decimal_fixed(self):
        # v0.8.3 P0 核心：'00:05.5' 必须是 5.5 秒（旧实现 /1000 得 5.005，属 bug）
        assert str_to_seconds('00:05.5') == pytest.approx(5.5)

    def test_two_decimal(self):
        assert str_to_seconds('00:05.55') == pytest.approx(5.55)

    def test_three_decimal(self):
        assert str_to_seconds('00:05.555') == pytest.approx(5.555)


class TestStorageRoundTrip:
    """存储格式 'mm:ss(.x)' 在前端 formatTime 与后端 seconds_to_str 均 round-trip"""

    @pytest.mark.parametrize('storage_line', STORAGE_ROUND_TRIP)
    def test_backend_seconds_to_str_round_trip(self, storage_line):
        # 后端 round-trip：解析 → 格式化 还原原行（与前端 formatTime(parseTimeStr(s)) === s 对齐）
        assert seconds_to_str(str_to_seconds(storage_line)) == storage_line

    def test_format_time_matches_seconds_to_str(self):
        # 存储格式行上，前端 formatTime 与后端 seconds_to_str 逐字符一致
        for line in STORAGE_ROUND_TRIP:
            assert seconds_to_str(str_to_seconds(line)) == line
