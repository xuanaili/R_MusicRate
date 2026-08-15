# MusicRate\backend\tests\test_style_auto.py —— v0.9 P0：动画样式自动生成纯函数契约单测
# 测试对象：前端 frontend/src/utils/styleAuto.js 的 presetFromTags / applyBpmAdjustment / buildAutoConfig
#   golden 由 node 跑前端真实文件生成（_gen_style_auto 临时 .mjs，跑完即删；见文件尾注释）。
# 背景：打开专辑时按「类型(tags) + BPM」自动生成初始动画样式与参数：
#   tags 决定风格预设（ball 小球 / meteor 流星 / close 关闭 + 基础参数档位，从 config 反推），
#   BPM 相对 100 基准微调能量参数（速度 / 密度 / 生成频率）。本测试锁定三函数契约防回归；
#   组件集成（AlbumDetail 落库 / RhythmBall initial props）靠 P1 手动回归。
# 注意：JS Math.round 半进位 vs Python round 银行家舍入 → 参考实现用 _round_half_up 复刻（镜像 v0.8 已知坑）。
import math

# ========== 相关风格的小球基础参数（摘自 frontend/src/config/index.js tagBallConfigList，测试用子集）==========
# (minSize, maxSize, minRate, maxRate, numWeight)
BALL_CONFIG = {
    'Rock【摇滚音乐】': (60, 120, 100, 250, 2.0),
    'Ambient【氛围音乐】': (25, 65, 300, 500, 0.8),
    'Techno【科技舞曲】': (50, 105, 140, 290, 1.6),
    'Death Metal【死亡金属】': (85, 150, 50, 160, 3.2),
    'Classical Music【古典音乐】': (20, 60, 330, 530, 0.7),
    'Doom Metal【厄运金属】': (80, 145, 55, 175, 3.0),
    'Pop【流行音乐】': (40, 90, 200, 400, 1.1),
    'K Pop【韩国流行】': (55, 110, 120, 270, 1.8),
    'default': (40, 80, 200, 400, 1.0),
}
# 风格预设覆盖表（config stylePresetOverrides 子集）：(style_type, bpm_scale)
STYLE_OVERRIDES = {
    'Ambient【氛围音乐】': ('close', 0.4),
    'Techno【科技舞曲】': ('meteor', 0.6),
    'Death Metal【死亡金属】': ('meteor', 0.6),
    'Classical Music【古典音乐】': ('close', 0.4),
    'Doom Metal【厄运金属】': ('ball', 0.4),
}
DEFAULT_STYLE_TYPE = 'ball'
DEFAULT_BPM_SCALE = 0.5
REF_BPM = 100

# ========== presetFromTags golden（node 跑前端真实文件生成）==========
# 每个用例：tags 输入 → 完整预设（style_type + rhy_config + meteor_config + bpm_scale）
PRESET_GOLDEN = [
    # 精确全名：高能量摇滚 → ball（启发式）
    (['Rock【摇滚音乐】'], {'style_type': 'ball', 'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
                           'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}, 'bpm_scale': 0.5}),
    # 覆盖表：安静氛围 → close（bpm_scale 0.4）
    (['Ambient【氛围音乐】'], {'style_type': 'close', 'rhy_config': {'a': 21, 'b': 61, 'c': 7, 'd': 8, 'e': 0},
                              'meteor_config': {'angle': 45, 'size': 11, 'tailLength': 33, 'speed': 20}, 'bpm_scale': 0.4}),
    # 覆盖表：高能量舞曲 → meteor（bpm_scale 0.6）
    (['Techno【科技舞曲】'], {'style_type': 'meteor', 'rhy_config': {'a': 47, 'b': 100, 'c': 1, 'd': 4, 'e': 7},
                             'meteor_config': {'angle': 45, 'size': 19, 'tailLength': 44, 'speed': 32}, 'bpm_scale': 0.6}),
    # 覆盖表：极端金属 → meteor（能量启发式本也会判 meteor）
    (['Death Metal【死亡金属】'], {'style_type': 'meteor', 'rhy_config': {'a': 84, 'b': 100, 'c': 0, 'd': 1, 'e': 24},
                                  'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 70, 'speed': 70}, 'bpm_scale': 0.6}),
    # 覆盖表：古典 → close（能量启发式 <2.5 本也判 close）
    (['Classical Music【古典音乐】'], {'style_type': 'close', 'rhy_config': {'a': 16, 'b': 56, 'c': 8, 'd': 9, 'e': 0},
                                      'meteor_config': {'angle': 45, 'size': 10, 'tailLength': 33, 'speed': 20}, 'bpm_scale': 0.4}),
    # 覆盖表：慢速金属能量启发式误判 meteor → 显式压回 ball
    (['Doom Metal【厄运金属】'], {'style_type': 'ball', 'rhy_config': {'a': 79, 'b': 100, 'c': 0, 'd': 2, 'e': 22},
                                 'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 70, 'speed': 70}, 'bpm_scale': 0.4}),
    # 【中文】匹配：'摇滚音乐' → Rock 预设
    (['摇滚音乐'], {'style_type': 'ball', 'rhy_config': {'a': 37, 'b': 78, 'c': 3, 'd': 6, 'e': 0},
                   'meteor_config': {'angle': 45, 'size': 15, 'tailLength': 36, 'speed': 23}, 'bpm_scale': 0.5}),
    # English 大小写不敏感匹配：'rock' → Rock 预设（与精确全名一致）
    (['rock'], {'style_type': 'ball', 'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
                'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}, 'bpm_scale': 0.5}),
    # 未知标签 → 默认预设
    (['不存在的风格'], {'style_type': 'ball', 'rhy_config': {'a': 37, 'b': 78, 'c': 3, 'd': 6, 'e': 0},
                       'meteor_config': {'angle': 45, 'size': 15, 'tailLength': 36, 'speed': 23}, 'bpm_scale': 0.5}),
    # 空数组 / null → 默认预设
    ([], {'style_type': 'ball', 'rhy_config': {'a': 37, 'b': 78, 'c': 3, 'd': 6, 'e': 0},
          'meteor_config': {'angle': 45, 'size': 15, 'tailLength': 36, 'speed': 23}, 'bpm_scale': 0.5}),
    (None, {'style_type': 'ball', 'rhy_config': {'a': 37, 'b': 78, 'c': 3, 'd': 6, 'e': 0},
            'meteor_config': {'angle': 45, 'size': 15, 'tailLength': 36, 'speed': 23}, 'bpm_scale': 0.5}),
    # 单字符串标签（非数组）
    ('Pop【流行音乐】', {'style_type': 'ball', 'rhy_config': {'a': 37, 'b': 89, 'c': 3, 'd': 6, 'e': 1},
                        'meteor_config': {'angle': 45, 'size': 16, 'tailLength': 37, 'speed': 23}, 'bpm_scale': 0.5}),
    # 多标签：首个命中决定（Pop 命中，Ambient 不参与）
    (['Pop【流行音乐】', 'Ambient【氛围音乐】'], {'style_type': 'ball', 'rhy_config': {'a': 37, 'b': 89, 'c': 3, 'd': 6, 'e': 1},
                                               'meteor_config': {'angle': 45, 'size': 16, 'tailLength': 37, 'speed': 23}, 'bpm_scale': 0.5}),
    # 中等能量 → ball（启发式，无覆盖）
    (['K Pop【韩国流行】'], {'style_type': 'ball', 'rhy_config': {'a': 53, 'b': 100, 'c': 1, 'd': 3, 'e': 9},
                            'meteor_config': {'angle': 45, 'size': 21, 'tailLength': 48, 'speed': 38}, 'bpm_scale': 0.5}),
]

# ========== applyBpmAdjustment golden（基准 = 对应标签的 presetFromTags 输出，再调 BPM）==========
# 每个用例：(标签, avg_bpm) → 调整后的 {rhy_config, meteor_config}
APPLY_GOLDEN = [
    (('Rock【摇滚音乐】', 120), {'rhy_config': {'a': 64, 'b': 100, 'c': 0, 'd': 3, 'e': 12},
                                'meteor_config': {'angle': 45, 'size': 24, 'tailLength': 59, 'speed': 49}}),
    (('Rock【摇滚音乐】', 80), {'rhy_config': {'a': 52, 'b': 89, 'c': 0, 'd': 3, 'e': 10},
                               'meteor_config': {'angle': 45, 'size': 20, 'tailLength': 48, 'speed': 40}}),
    (('Rock【摇滚音乐】', 100), {'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
                                'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}}),
    (('Rock【摇滚音乐】', None), {'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
                                 'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}}),
    (('Rock【摇滚音乐】', 0), {'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
                              'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}}),
    # bpm_scale 0.6 的舞曲（BPM 影响更强）
    (('Techno【科技舞曲】', 128), {'rhy_config': {'a': 55, 'b': 100, 'c': 1, 'd': 3, 'e': 8},
                                  'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 51, 'speed': 37}}),
]

# ========== buildAutoConfig golden（tags + tempo JSON → 最终落库配置）==========
BUILD_GOLDEN = [
    (['Rock【摇滚音乐】'], {'avg_bpm': 120}, {'style_type': 'ball', 'rhy_config': {'a': 64, 'b': 100, 'c': 0, 'd': 3, 'e': 12},
                                             'meteor_config': {'angle': 45, 'size': 24, 'tailLength': 59, 'speed': 49}}),
    (['Techno【科技舞曲】'], {'avg_bpm': 128}, {'style_type': 'meteor', 'rhy_config': {'a': 55, 'b': 100, 'c': 1, 'd': 3, 'e': 8},
                                               'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 51, 'speed': 37}}),
    (['Ambient【氛围音乐】'], None, {'style_type': 'close', 'rhy_config': {'a': 21, 'b': 61, 'c': 7, 'd': 8, 'e': 0},
                                    'meteor_config': {'angle': 45, 'size': 11, 'tailLength': 33, 'speed': 20}}),
    ([], {'avg_bpm': 90}, {'style_type': 'ball', 'rhy_config': {'a': 35, 'b': 74, 'c': 3, 'd': 6, 'e': 0},
                           'meteor_config': {'angle': 45, 'size': 14, 'tailLength': 34, 'speed': 22}}),
]


class TestPresetFromTags:
    """tags → 风格预设：标签匹配（精确/中文/英文）+ 覆盖表 + 能量启发式 + 默认兜底"""

    def test_golden(self):
        for tags, expected in PRESET_GOLDEN:
            assert _preset_from_tags(tags) == expected, tags


class TestApplyBpmAdjustment:
    """BPM 相对 100 基准微调：高 BPM → 间隔 c/d 更小、密度 e/尺寸 a,b/流星参数更大；低 BPM 反向"""

    def test_golden(self):
        for (tag, avg_bpm), expected in APPLY_GOLDEN:
            preset = _preset_from_tags([tag] if not isinstance(tag, list) else tag)
            assert _apply_bpm(preset, avg_bpm) == expected, (tag, avg_bpm)

    def test_invalid_bpm_returns_clone(self):
        # avgBpm 非法/缺失 → 原样克隆（不抛错、不 NaN）
        preset = _preset_from_tags(['Rock【摇滚音乐】'])
        for bad in (None, 0, -5, 'abc'):
            result = _apply_bpm(preset, bad)
            assert result['rhy_config'] == preset['rhy_config']
            assert result['meteor_config'] == preset['meteor_config']

    def test_immutability(self):
        # 返回新对象，不污染原 preset
        preset = _preset_from_tags(['Rock【摇滚音乐】'])
        result = _apply_bpm(preset, 120)
        assert result is not preset
        assert result['rhy_config'] is not preset['rhy_config']
        result['rhy_config']['a'] = 999
        assert preset['rhy_config']['a'] != 999


class TestBuildAutoConfig:
    """一键生成：tags 定风格预设 + BPM 就绪则微调 → {style_type, rhy_config, meteor_config}"""

    def test_golden(self):
        for tags, tempo_dict, expected in BUILD_GOLDEN:
            assert _build_auto(tags, tempo_dict) == expected, (tags, tempo_dict)

    def test_bpm_absent_keeps_base(self):
        # tempo 缺失（null/空）→ 基础档位原样，style_type 由 tags 决定
        base = _build_auto(['Rock【摇滚音乐】'], None)
        assert base['style_type'] == 'ball'
        assert base['rhy_config']['a'] == 58

    def test_no_tempo_ready_flag_shape(self):
        # tempo_dict 存在但 avg_bpm 缺失 → 同样不缩放（与 None 等价）
        no_bpm = _build_auto(['Rock【摇滚音乐】'], {})
        assert no_bpm == _build_auto(['Rock【摇滚音乐】'], None)

    def test_immutability(self):
        # buildAutoConfig 每次返回全新对象（AlbumDetail 连续调用不串）
        a = _build_auto(['Rock【摇滚音乐】'], {'avg_bpm': 120})
        b = _build_auto(['Rock【摇滚音乐】'], {'avg_bpm': 120})
        assert a == b and a is not b


# ========== 参考实现（镜像前端 frontend/src/utils/styleAuto.js + config/index.js，node golden 验证一致）==========
# 注：golden 表本身由 node 跑前端真实文件生成（跑完即删）；此处仅做参考实现，让测试在无 node 环境下可读。
#     真实行为以上方 golden 为准。

def _round_half_up(v):
    """复刻 JS Math.round（半进位）：Python round 是银行家舍入，必须显式 +0.5 取整（镜像 v0.8 已知坑）"""
    return math.floor(v + 0.5)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _round_clamp(v, lo, hi):
    return _round_half_up(_clamp(v, lo, hi))


def _extract_zh(tag):
    s = str(tag)
    start = s.find('【')
    end = s.find('】', start + 1) if start >= 0 else -1
    return s[start + 1:end] if start >= 0 and end > start else ''


def _extract_en(tag):
    s = str(tag)
    idx = s.find('【')
    return (s[:idx] if idx >= 0 else s).strip()


def _resolve_ball_params(tag):
    if tag is None:
        return BALL_CONFIG['default']
    t = str(tag).strip()
    if not t:
        return BALL_CONFIG['default']
    if t in BALL_CONFIG:
        return BALL_CONFIG[t]
    zh = _extract_zh(t)
    en = _extract_en(t).lower()
    for option, params in BALL_CONFIG.items():
        o_zh = _extract_zh(option)
        o_en = _extract_en(option).lower()
        if zh and o_zh == zh:
            return params
        if en and o_en == en:
            return params
    return BALL_CONFIG['default']


def _energy_of(params):
    min_size, max_size, min_rate, max_rate, num_weight = params
    return num_weight * (1000 / max(1, min_rate))


def _derive_rhy(params):
    min_size, max_size, min_rate, max_rate, num_weight = params
    return {
        'a': _round_clamp((min_size - 5) / 0.95, 0, 100),
        'b': _round_clamp((max_size - 10) / 0.9, 0, 100),
        'c': _round_clamp((min_rate - 100) / 29, 0, 100),
        'd': _round_clamp((max_rate - 100) / 49, 0, 100),
        'e': _round_clamp((num_weight - 1) / 0.09, 0, 100),
    }


def _derive_meteor(params, energy):
    min_size, max_size, min_rate, max_rate, num_weight = params
    avg_size = (min_size + max_size) / 2
    return {
        'angle': 45,
        'size': _round_clamp(avg_size * 0.25, 8, 22),
        'tailLength': _round_clamp(30 + energy * 1.2, 30, 70),
        'speed': _round_clamp(15 + energy * 1.5, 20, 70),
    }


def _pick_style_type(energy):
    if energy < 2.5:
        return 'close'
    if energy >= 30:
        return 'meteor'
    return 'ball'


def _resolve_override(tag):
    if tag is None:
        return None
    t = str(tag).strip()
    if not t:
        return None
    if t in STYLE_OVERRIDES:
        return STYLE_OVERRIDES[t]
    zh = _extract_zh(t)
    en = _extract_en(t).lower()
    for option, override in STYLE_OVERRIDES.items():
        o_zh = _extract_zh(option)
        o_en = _extract_en(option).lower()
        if zh and o_zh == zh:
            return override
        if en and o_en == en:
            return override
    return None


def _preset_from_tags(tags):
    lst = list(tags) if isinstance(tags, list) else ([tags] if tags is not None else [])
    for tag in lst:
        if tag is None:
            continue
        params = _resolve_ball_params(tag)
        override = _resolve_override(tag)
        energy = _energy_of(params)
        style_type = override[0] if override else _pick_style_type(energy)
        bpm_scale = override[1] if override else DEFAULT_BPM_SCALE
        return {
            'style_type': style_type,
            'rhy_config': _derive_rhy(params),
            'meteor_config': _derive_meteor(params, energy),
            'bpm_scale': bpm_scale,
        }
    params = BALL_CONFIG['default']
    energy = _energy_of(params)
    return {
        'style_type': DEFAULT_STYLE_TYPE,
        'rhy_config': _derive_rhy(params),
        'meteor_config': _derive_meteor(params, energy),
        'bpm_scale': DEFAULT_BPM_SCALE,
    }


def _apply_bpm(preset, avg_bpm):
    rc = preset.get('rhy_config') or {}
    mc = preset.get('meteor_config') or {}
    if avg_bpm is None:
        bpm = float('nan')
    else:
        try:
            bpm = float(avg_bpm)
        except (TypeError, ValueError):
            bpm = float('nan')
    if not math.isfinite(bpm) or bpm <= 0:  # NaN/∞ / ≤0 → 原样克隆（镜像 JS isFinite）
        return {'rhy_config': dict(rc), 'meteor_config': dict(mc)}
    scale = preset.get('bpm_scale') if preset.get('bpm_scale') is not None else DEFAULT_BPM_SCALE
    factor = (bpm / REF_BPM) ** scale
    return {
        'rhy_config': {
            'a': _round_clamp((rc.get('a') or 0) * factor, 0, 100),
            'b': _round_clamp((rc.get('b') or 0) * factor, 0, 100),
            'c': _round_clamp((rc.get('c') or 0) / factor, 0, 100),
            'd': _round_clamp((rc.get('d') or 0) / factor, 0, 100),
            'e': _round_clamp((rc.get('e') or 0) * factor, 0, 100),
        },
        'meteor_config': {
            'angle': mc.get('angle') if mc.get('angle') is not None else 45,
            'size': _round_clamp((mc.get('size') or 0) * factor, 0, 100),
            'tailLength': _round_clamp((mc.get('tailLength') or 0) * factor, 0, 100),
            'speed': _round_clamp((mc.get('speed') or 0) * factor, 0, 100),
        },
    }


def _build_auto(tags, tempo_dict):
    preset = _preset_from_tags(tags)
    avg_bpm = tempo_dict.get('avg_bpm') if isinstance(tempo_dict, dict) else None
    adjusted = _apply_bpm(preset, avg_bpm)
    return {
        'style_type': preset['style_type'],
        'rhy_config': adjusted['rhy_config'],
        'meteor_config': adjusted['meteor_config'],
    }
