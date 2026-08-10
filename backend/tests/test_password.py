# MusicRate\backend\tests\test_password.py 改密码校验纯逻辑单测（零 DB 依赖）
# 测试对象：backend/utils/user.py 的 validate_password_change()
# 分支：空值 / 长度<6 / 新旧相同 / 旧密码错误 / 合法修改
from backend.utils.auth import encrypt_password
from backend.utils.user import validate_password_change


class TestValidatePasswordChange:
    def test_old_password_empty(self):
        hashed = encrypt_password('abc123')
        assert validate_password_change('', 'newpass1', hashed) == '旧密码不能为空'

    def test_new_password_empty(self):
        hashed = encrypt_password('abc123')
        assert validate_password_change('abc123', '', hashed) == '新密码不能为空'

    def test_new_password_too_short(self):
        hashed = encrypt_password('abc123')
        assert validate_password_change('abc123', '12345', hashed) == '新密码长度不能少于6位'

    def test_old_new_same(self):
        hashed = encrypt_password('abc123')
        assert validate_password_change('abc123', 'abc123', hashed) == '新旧密码不能相同'

    def test_old_password_wrong(self):
        hashed = encrypt_password('abc123')
        assert validate_password_change('wrong12', 'newpass1', hashed) == '旧密码错误'

    def test_valid_change_returns_none(self):
        hashed = encrypt_password('abc123')
        assert validate_password_change('abc123', 'newpass1', hashed) is None
