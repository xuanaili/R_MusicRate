# MusicRate\backend\tests\test_user_avatar.py 头像URL校验纯逻辑单测（零 DB 依赖）
# 测试对象：backend/utils/user.py 的 validate_avatar_url()
# 分支：空值 / 非http(s)协议 / 缺少域名 / 合法 http / 合法 https
from backend.utils.user import validate_avatar_url


class TestValidateAvatarUrl:
    def test_empty_url(self):
        # 空串：不允许，返回错误信息
        assert validate_avatar_url('') == '头像地址不能为空'

    def test_whitespace_url(self):
        # 纯空白：视为空值
        assert validate_avatar_url('   ') == '头像地址不能为空'

    def test_non_url(self):
        # 非 URL（无协议前缀）：不允许
        assert validate_avatar_url('abc.png') is not None

    def test_ftp_protocol(self):
        # 非 http(s) 协议：不允许（防止本地文件路径等注入）
        assert validate_avatar_url('ftp://x/y.png') is not None

    def test_http_missing_host(self):
        # 有协议但无域名：不允许
        assert validate_avatar_url('http://') is not None

    def test_valid_http(self):
        # 合法 http URL：返回 None
        assert validate_avatar_url('http://localhost:5000/covers/abc.jpg') is None

    def test_valid_https(self):
        # 合法 https URL：返回 None
        assert validate_avatar_url('https://cdn.example.com/avatar/1.png') is None

    def test_valid_url_with_query(self):
        # 带路径/查询参数的合法 URL：允许
        assert validate_avatar_url('http://localhost:5000/covers/abc.jpg?v=1') is None
