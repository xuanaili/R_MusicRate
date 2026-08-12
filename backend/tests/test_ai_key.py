# MusicRate\backend\tests\test_ai_key.py AI key 配置参数校验单测（纯逻辑，零 DB 依赖，v0.8.1 P3）
# 测试对象：backend/api/ai.py 的 validate_ai_key_params()（provider 规范化 + api_key 非空/长度校验）
from backend.api.ai import MAX_API_KEY_LENGTH, DEFAULT_PROVIDER, PROVIDER_CONFIG, validate_ai_key_params


class TestValidateAiKeyParams:
    def test_default_provider_when_empty(self):
        # provider 缺省 → 回退默认服务商（deepseek），key 原样返回，无错误
        p, k, err = validate_ai_key_params('', 'sk-abc')
        assert err == ''
        assert p == DEFAULT_PROVIDER
        assert k == 'sk-abc'

    def test_provider_normalized_lowercase(self):
        # provider 大小写/空格容错：'DeepSeek ' → 'deepseek'
        p, k, err = validate_ai_key_params('DeepSeek ', 'sk-abc')
        assert err == ''
        assert p == 'deepseek'

    def test_provider_openai_supported(self):
        p, k, err = validate_ai_key_params('openai', 'sk-abc')
        assert err == ''
        assert p == 'openai'
        assert p in PROVIDER_CONFIG

    def test_unsupported_provider_rejected(self):
        # 不支持的 service provider（如 claude）→ 返回错误信息
        p, k, err = validate_ai_key_params('claude', 'sk-abc')
        assert err != ''
        assert 'claude' in err

    def test_empty_api_key_rejected(self):
        # api_key 为空白 → 返回错误信息，提示不能为空
        p, k, err = validate_ai_key_params('deepseek', '   ')
        assert err != ''
        assert '不能为空' in err

    def test_none_api_key_rejected(self):
        p, k, err = validate_ai_key_params('deepseek', None)
        assert err != ''
        assert '不能为空' in err

    def test_api_key_trimmed(self):
        # api_key 首尾空白被去掉
        p, k, err = validate_ai_key_params('deepseek', '  sk-abc  ')
        assert err == ''
        assert k == 'sk-abc'

    def test_api_key_too_long_rejected(self):
        # 超 MAX_API_KEY_LENGTH（防误粘贴大文本）→ 返回友好错误（而非 DB 1406）
        p, k, err = validate_ai_key_params('deepseek', 'x' * (MAX_API_KEY_LENGTH + 1))
        assert err != ''
        assert '过长' in err

    def test_api_key_at_max_length_allowed(self):
        # 恰好 MAX_API_KEY_LENGTH 字符 → 通过（列已是 TEXT，长度足够）
        p, k, err = validate_ai_key_params('deepseek', 'x' * MAX_API_KEY_LENGTH)
        assert err == ''
        assert len(k) == MAX_API_KEY_LENGTH

    def test_non_ascii_api_key_rejected(self):
        # 误粘贴中文文本当密钥 → 拒绝并提示（请求头 latin-1 编码会炸，见 ai.py 实测坑）
        p, k, err = validate_ai_key_params('deepseek', 'sk-今日计划abc')
        assert err != ''
        assert '非ASCII' in err

    def test_control_char_api_key_rejected(self):
        # 含控制字符（如换行）的密钥 → 拒绝（latin-1 头不允许控制字符）
        p, k, err = validate_ai_key_params('deepseek', 'sk-abc\x01def')
        assert err != ''
        assert '非ASCII' in err

    def test_ascii_with_inner_space_allowed(self):
        # 可打印 ASCII（含空格）→ 通过（strip 只去首尾空白，内部空格合法）
        p, k, err = validate_ai_key_params('deepseek', 'sk ab c')
        assert err == ''
        assert k == 'sk ab c'

    def test_both_invalid_returns_provider_error_first(self):
        # 非法 provider + 空 key → provider 错误优先（先校验 provider）
        p, k, err = validate_ai_key_params('unknown', '')
        assert err != ''
        assert 'unknown' in err

    def test_all_providers_have_base_url_and_model(self):
        # PROVIDER_CONFIG 每个服务商都有 OpenAI 兼容的 base_url + model 配置
        for name, cfg in PROVIDER_CONFIG.items():
            assert cfg.get('base_url'), name
            assert cfg.get('model'), name
