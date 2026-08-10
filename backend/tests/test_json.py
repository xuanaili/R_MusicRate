# MusicRate\backend\tests\test_json.py 安全JSON解析函数单测（纯逻辑，零 DB 依赖）
# 测试对象：backend/utils/json.py 的 safe_json_loads()
from backend.utils.json import safe_json_loads


class TestSafeJsonLoads:
    def test_none_returns_none(self):
        assert safe_json_loads(None) is None

    def test_empty_string_returns_none(self):
        assert safe_json_loads('') is None

    def test_valid_json_array_returns_parsed(self):
        assert safe_json_loads('[1, 2, 3]') == [1, 2, 3]

    def test_valid_json_object_returns_parsed(self):
        assert safe_json_loads('{"a": 1}') == {'a': 1}

    def test_invalid_json_returns_none(self):
        assert safe_json_loads('{bad json') is None

    def test_non_string_input_returns_none(self):
        # json.loads(123) 抛 TypeError → 捕获返回 None
        assert safe_json_loads(123) is None
