# MusicRate\backend\utils\level.py 等级-经验纯逻辑工具函数（v0.7.1 P0，零 DB 依赖，可单测）
# 规则（README v0.7.1 已定决策）：
# - 经验来源：听取时长为主（1 秒 = 1 XP，无上限）+ 评分/听后感/评论小额加分（每日合计上限 100）
# - 升级曲线：level = floor(sqrt(xp / 3600))，Lv.N 约需 N² 小时
#   （Lv.1=3600（1h）、Lv.2=14400（4h）、Lv.3=32400（9h）、Lv.5=90000（25h）、Lv.10=360000（100h））
# - 前端用 frontend/src/utils/level.js，与后端逻辑必须一致（复用 scoreCalc「前后端一致」模式）
import math

# 升级曲线参数：1 小时 = 3600 秒（经验），Lv.N 需 N² 小时 → N²*3600 XP
HOURS_TO_XP = 3600

# 每日加分（评分 / 听后感 / 评论合计）上限
DAILY_BONUS_LIMIT = 100

# 等级称号分段：Lv0-3 初听者 → Lv4-7 爱乐人 → Lv8-12 资深乐迷 → Lv13-19 音乐行家 → Lv20-29 乐评达人 → Lv30+ 传奇乐迷
_LEVEL_TITLES = [
    (30, '传奇乐迷'),
    (20, '乐评达人'),
    (13, '音乐行家'),
    (8, '资深乐迷'),
    (4, '爱乐人'),
    (0, '初听者'),
]


def _to_xp(xp):
    """经验值归一化：None/非法 → 0，负数 → 0"""
    try:
        val = float(xp if xp is not None else 0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, val)


def compute_level(xp):
    """等级推导：level = floor(sqrt(xp / 3600))，Lv.N 约需 N² 小时"""
    xp = _to_xp(xp)
    return int(math.floor(math.sqrt(xp / HOURS_TO_XP)))


def xp_to_next_level(xp):
    """距下一级还需经验：下一级边界 (level+1)²*3600 − 当前 xp，最少为 1"""
    xp = _to_xp(xp)
    level = compute_level(xp)
    next_boundary = (level + 1) ** 2 * HOURS_TO_XP
    return int(math.ceil(next_boundary - xp))


def level_progress(xp):
    """当前级内进度 0~1：xp 在当前级 [base, next) 区间内的位置，保留 4 位小数"""
    xp = _to_xp(xp)
    level = compute_level(xp)
    base = level ** 2 * HOURS_TO_XP
    next_boundary = (level + 1) ** 2 * HOURS_TO_XP
    span = next_boundary - base
    if span <= 0:
        return 0.0
    progress = (xp - base) / span
    return round(max(0.0, min(progress, 1.0)), 4)


def level_title(level):
    """等级称号：按段位返回（Lv0-3 初听者 → Lv4-7 爱乐人 → Lv8-12 资深乐迷 → …）"""
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = 0
    for threshold, title in _LEVEL_TITLES:
        if level >= threshold:
            return title
    return '初听者'


def compute_bonus_gain(today_bonus, amount):
    """每日加分上限计算（纯函数）：实际加分 = min(amount, 100 - today_bonus)，可为部分或 0

    - today_bonus: 今日已累计加分（跨天重置由调用方保证）
    - amount: 本次申请加分（评分 +5 / 听后感 +20 / 评论 +10）
    返回: 本次实际可加分（≥0）
    """
    today_bonus = float(today_bonus or 0)
    try:
        amount = float(amount or 0)
    except (TypeError, ValueError):
        return 0.0
    if amount <= 0:
        return 0.0
    remaining = max(0.0, DAILY_BONUS_LIMIT - today_bonus)
    return min(amount, remaining)
