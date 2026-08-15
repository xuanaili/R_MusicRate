# MusicRate\backend\tests\test_album_style.py —— v0.9 P0：专辑样式配置规范化纯函数单测（零 DB 依赖）
# 测试对象：backend/api/album.py 的 normalize_style_config
# 作用：POST /api/album/style 边界校验——style_type/auto_manual 枚举收敛、rhy_config a-e 与
#       meteor_config 四参数数字收敛 0-100（非法回 0），保证落库数据安全、前端不脏写。
from backend.api.album import normalize_style_config


class TestNormalizeStyleConfig:
    """样式配置规范化：枚举收敛 + 数值 clamp + 非法兜底"""

    def test_empty_defaults(self):
        # 空提交 → 全部回默认（close / auto / 全 0）
        result = normalize_style_config({})
        assert result == {
            'style_type': 'close',
            'rhy_config': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0},
            'meteor_config': {'angle': 0, 'size': 0, 'tailLength': 0, 'speed': 0},
            'auto_manual': 'auto',
        }

    def test_none_input(self):
        result = normalize_style_config(None)
        assert result['style_type'] == 'close'

    def test_full_valid_passthrough(self):
        data = {
            'style_type': 'ball',
            'auto_manual': 'manual',
            'rhy_config': {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11},
            'meteor_config': {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45},
        }
        result = normalize_style_config(data)
        assert result['style_type'] == 'ball'
        assert result['auto_manual'] == 'manual'
        assert result['rhy_config'] == {'a': 58, 'b': 100, 'c': 0, 'd': 3, 'e': 11}
        assert result['meteor_config'] == {'angle': 45, 'size': 22, 'tailLength': 54, 'speed': 45}

    def test_invalid_enums_fallback(self):
        # 非法枚举 → 默认（close / auto）
        result = normalize_style_config({'style_type': 'explode', 'auto_manual': 'sometimes'})
        assert result['style_type'] == 'close'
        assert result['auto_manual'] == 'auto'

    def test_all_valid_enums(self):
        for st in ('close', 'ball', 'meteor'):
            assert normalize_style_config({'style_type': st})['style_type'] == st
        for am in ('auto', 'manual'):
            assert normalize_style_config({'auto_manual': am})['auto_manual'] == am

    def test_numeric_clamp_and_cast(self):
        # 越界收敛 0-100；浮点取整；非法字符串 → 0
        data = {
            'rhy_config': {'a': 150, 'b': -5, 'c': 'abc', 'd': 88.6, 'e': 0},
            'meteor_config': {'angle': 120, 'size': -1, 'tailLength': 45.4, 'speed': 'x'},
        }
        result = normalize_style_config(data)
        assert result['rhy_config']['a'] == 100
        assert result['rhy_config']['b'] == 0
        assert result['rhy_config']['c'] == 0
        assert result['rhy_config']['d'] == 89
        assert result['rhy_config']['e'] == 0
        assert result['meteor_config']['angle'] == 100
        assert result['meteor_config']['size'] == 0
        assert result['meteor_config']['tailLength'] == 45
        assert result['meteor_config']['speed'] == 0

    def test_extra_keys_dropped(self):
        # 未知 key（如 tail 拼写错误）不进入落库对象，只保留约定的 a-e / 四参数
        data = {'rhy_config': {'a': 10, 'f': 99, 'tail': 77}, 'meteor_config': {'angle': 30, 'foo': 1}}
        result = normalize_style_config(data)
        assert set(result['rhy_config'].keys()) == {'a', 'b', 'c', 'd', 'e'}
        assert set(result['meteor_config'].keys()) == {'angle', 'size', 'tailLength', 'speed'}
        assert result['meteor_config']['speed'] == 0
