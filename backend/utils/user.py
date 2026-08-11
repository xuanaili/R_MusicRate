# MusicRate\backend\utils\user.py 用户相关工具函数（校验纯函数零 DB 依赖可单测；add_bonus_xp 依赖 DB 由接口层调用）
import datetime
import re

import pymysql

from backend.utils.auth import verify_password
from backend.utils.db import get_db
from backend.utils.level import compute_bonus_gain, compute_level
from backend.utils.xp import BONUS_SOURCES


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


def add_bonus_xp(user_id, amount, source):
    """加分并返回本次实际加分（受每日上限 100 约束），供评分/听后感/评论接口成功后一行调用

    v0.7.2 新增：source 必填经验来源（XP_RATING/XP_REVIEW/XP_COMMENT，来自 backend/utils/xp.py），
    实际加分 > 0 时【与 users 累计列同事务】写一条 user_xp_log 明细（保证 SUM(log) 与 bonus_xp_today 严格一致）。
    source 校验枚举，非法抛 ValueError——防止漏传 source 导致明细静默丢失。

    逻辑（README v0.7.1/v0.7.2 已定决策）：
    - 先查 bonus_date / bonus_xp_today，跨天（含多天未登录）则重置当日计数，无需定时任务
    - remaining = 100 - bonus_xp_today；实际加分 = min(amount, remaining)（可为部分或 0）
    - 更新 users.xp += 实际加分、level = compute_level(xp)、bonus_date、bonus_xp_today
    - gained > 0 时 INSERT user_xp_log(user_id, xp_type=source, amount=gained)

    返回: (xp_gained, new_xp, new_level, level_up)
    - xp_gained: 本次实际加分（0 ~ amount，受每日上限约束）
    - new_xp: 加分后的总经验（保留 1 位小数）
    - new_level: 加分后的等级（由 xp 推导）
    - level_up: 是否本次升级
    """
    if source not in BONUS_SOURCES:
        raise ValueError(f'非法经验来源：{source}，应为 {BONUS_SOURCES} 之一')
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('SELECT xp, bonus_date, bonus_xp_today FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        if not user:
            return 0, 0, 0, False

        xp = float(user.get('xp') or 0)
        today = datetime.date.today()
        bonus_date = user.get('bonus_date')
        if bonus_date is None or str(bonus_date) != today.isoformat():
            today_bonus = 0.0
        else:
            today_bonus = float(user.get('bonus_xp_today') or 0)

        gained = compute_bonus_gain(today_bonus, amount)
        new_xp = round(xp + gained, 1)
        old_level = compute_level(xp)
        new_level = compute_level(new_xp)
        cursor.execute('''
            UPDATE users SET xp = %s, level = %s, bonus_date = %s, bonus_xp_today = %s
            WHERE user_id = %s
        ''', (new_xp, new_level, today.isoformat(), round(today_bonus + gained, 1), user_id))
        # v0.7.2：仅实际加分 > 0 时写明细（防 +0 噪音），与 users 累计同事务同 commit
        if gained > 0:
            cursor.execute('''
                INSERT INTO user_xp_log (user_id, xp_type, amount)
                VALUES (%s, %s, %s)
            ''', (user_id, source, gained))
        db.commit()
        return gained, new_xp, new_level, new_level > old_level
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
