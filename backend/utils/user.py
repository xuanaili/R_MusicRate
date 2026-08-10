# MusicRate\backend\utils\user.py 用户相关纯逻辑工具函数（零 DB 依赖，可单测）
from backend.utils.auth import verify_password


def validate_password_change(old_password: str, new_password: str, current_hashed: str):
    """改密码入参校验（纯函数，不触碰数据库）

    返回：错误信息字符串；校验通过返回 None
    分支：旧密码为空 / 新密码为空 / 新密码长度<6 / 新旧相同 / 旧密码错误
    """
    if not old_password:
        return '旧密码不能为空'
    if not new_password:
        return '新密码不能为空'
    if len(new_password) < 6:
        return '新密码长度不能少于6位'
    if old_password == new_password:
        return '新旧密码不能相同'
    if not verify_password(old_password, current_hashed):
        return '旧密码错误'
    return None
