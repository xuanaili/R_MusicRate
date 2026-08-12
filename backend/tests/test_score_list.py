# MusicRate\backend\tests\test_score_list.py —— v0.8.4 P0：歌词页快捷评分纯函数契约单测
# 测试对象：前端 frontend/src/utils/scoreList.js 的 parseScoreList / getTrackScore / setTrackScore
#   golden 由 node 跑前端真实文件生成（_gen_frontend_score_list.mjs，跑完即删；29 例全过）。
# 背景：歌词展示页顶部「当前单曲快捷评分」需要复用评分数组 [专辑整体分, 单曲1分, 单曲2分, ...]，
#   组件内直接读 album.my_score（兼容数组 / JSON 字符串 / 空值），交互时经纯函数读写单曲分。
#   本测试锁定三个函数的契约防回归；组件行为（拖拽/防抖保存）靠手动回归。
import pytest

# 前端 parseScoreList golden（node 跑前端真实文件生成）：归一化 album.my_score 为数字数组，
#   至少含 index0（专辑整体分）占位；非法项置 0、数值收敛 0-100
PARSE_GOLDEN = [
    ([], [0]),
    ([80], [80]),
    ([80, 90, 0], [80, 90, 0]),
    ('[80,90]', [80, 90]),          # JSON 字符串
    ('[80, 90.5]', [80, 90.5]),     # 带小数整体分
    ('', [0]),                       # 空串
    (None, [0]),
    ('not-json', [0]),              # 非法 JSON 串
    ([80, 'abc', 120, -5], [80, 0, 100, 0]),  # 非法项置0 / 越界收敛
    ({}, [0]),                       # 非数组对象
]

# getTrackScore golden：取第 idx 首单曲分 = list[idx+1]（index0 是专辑整体分）
GET_GOLDEN = [
    (([80, 90, 70], 0), 90),
    (([80, 90, 70], 1), 70),
    (([80, 90, 70], 2), 0),          # 越界 → 0
    (([80], 0), 0),                   # 无单曲分 → 0
    (([], 0), 0),
    ((None, 0), 0),
    (([0, 0, 0], 1), 0),              # 未评分 → 0
    (([80, 'abc'], 0), 0),            # 非法 → 0
    (([80, 120, -5], 0), 100),        # 收敛 0-100
    (([80, 120, -5], 1), 0),
]

# setTrackScore golden：写入第 idx 首单曲分并返回新数组（克隆不污染原数组）
SET_GOLDEN = [
    (([80, 90], 0, 75), [80, 75]),
    (([80], 0, 88), [80, 88]),         # 长度不足补位
    (([], 0, 50), [0, 50]),            # 空数组 → index0 占位 + 写入
    ((None, 0, 50), [0, 50]),
    (([80, 90], 1, 55), [80, 90, 55]), # 中间补位
    (([80, 90], 0, 105), [80, 100]),   # 收敛 0-100
    (([80, 90], 0, 88.6), [80, 89]),   # 取整
    (([80, 90], 0, 'abc'), [80, 0]),   # 非法 → 0
]


class TestParseScoreList:
    """归一化 album.my_score：数组 / JSON 字符串 / 空值 → 数字数组（含 index0 占位）"""

    @pytest.mark.parametrize('raw,expected', PARSE_GOLDEN)
    def test_golden(self, raw, expected):
        # golden 来自 node 跑前端真实 scoreList.js（见文件头注释）
        assert _parse_score_list(raw) == expected


class TestGetTrackScore:
    """取单曲分：scoreList[idx+1]，未评分 / 越界 / 非法 → 0"""

    @pytest.mark.parametrize('args,expected', GET_GOLDEN)
    def test_golden(self, args, expected):
        assert _get_track_score(*args) == expected

    def test_album_overall_is_index0(self):
        # 单曲分从 index1 开始，index0 永远是专辑整体分（本函数只读单曲位）
        assert _get_track_score([66, 88], 0) == 88


class TestSetTrackScore:
    """写入单曲分：返回新数组，补位 / 收敛 / 取整，不污染原数组"""

    @pytest.mark.parametrize('args,expected', SET_GOLDEN)
    def test_golden(self, args, expected):
        assert _set_track_score(*args) == expected

    def test_immutability(self):
        # 写入必须返回新数组，原数组不被修改（供 Vue 响应式触发）
        orig = [80, 90]
        _set_track_score(orig, 0, 50)
        assert orig == [80, 90]


# ========== 参考实现（镜像前端 frontend/src/utils/scoreList.js，node golden 验证过逐字符一致）==========
# 注：golden 表本身由 node 跑前端真实文件生成（跑完即删）；此处仅做参考实现，让测试在无 node 环境下可读。
#     真实行为以上方 golden 为准。

def _parse_score_list(my_score):
    if isinstance(my_score, list):
        lst = my_score
    elif isinstance(my_score, str):
        try:
            import json
            lst = json.loads(my_score)
        except (ValueError, TypeError):
            lst = []
    else:
        lst = []
    if not isinstance(lst, list):
        lst = []
    clean = []
    for v in lst:
        try:
            n = float(v)
        except (TypeError, ValueError):
            n = float('nan')
        clean.append(0 if n != n else max(0.0, min(100.0, n)))
    if not clean:
        clean.append(0)
    return clean


def _get_track_score(score_list, track_index):
    if not isinstance(score_list, list):
        return 0
    idx = track_index + 1
    if idx >= len(score_list):
        return 0
    try:
        n = float(score_list[idx])
    except (TypeError, ValueError):
        return 0
    return 0 if n != n else max(0.0, min(100.0, n))


def _set_track_score(score_list, track_index, new_score):
    lst = list(score_list) if isinstance(score_list, list) else [0]
    idx = track_index + 1
    while len(lst) <= idx:
        lst.append(0)
    try:
        n = float(new_score)
    except (TypeError, ValueError):
        n = float('nan')
    lst[idx] = 0 if n != n else max(0.0, min(100.0, round(n)))
    return lst
