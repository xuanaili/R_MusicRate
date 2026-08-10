# MusicRate\backend\utils\user.py 用户相关纯逻辑工具函数（零 DB 依赖，可单测）
import re
from backend.utils.auth import verify_password


# http(s) URL 正则（含域名，排除 ftp/file/相对路径等）
_HTTP_URL_RE = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)


def validate_avatar_url(avatar_url: str):
    """头像地址校验（纯函数，不触碰数据库）

    返回：错误信息字符串；校验通过返回 None
    规则：非空 + 必须为 http/https 完整 URL（防止本地文件路径/协议注入）
    """
    url = (avatar_url or '').strip()
    if not url:
        return '头像地址不能为空'
    if not _HTTP_URL_RE.match(url):
        return '头像地址必须为 http(s) 完整链接'
    return None


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
