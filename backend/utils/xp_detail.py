# MusicRate\backend\utils\xp_detail.py 经验详情聚合纯函数（v0.7.2，零 DB 依赖，可单测）
# 供 /api/user/xp-detail 使用：近N天加分经验按天累加 + listening/bonus 合并为每日总经验
# 口径：1 秒 = 1 XP（收听）；加分来源（评分/听后感/评论）取 user_xp_log 加分行
import datetime


def _parse_created_date(value):
    """解析 user_xp_log.created_at 行为 date 对象；None / 非法 → None

    PyMySQL 对 DATETIME 返回 datetime.datetime、DATE 返回 datetime.date、字符串 'YYYY-MM-DD HH:MM:SS' 均兼容
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


def accumulate_bonus_daily(rows, days=7):
    """近 N 天加分经验按天累加 + 补零序列（经验详情弹窗 bonus 侧数据源）

    - rows: user_xp_log 加分行（xp_type in 评分/听后感/评论），元素含 created_at（datetime/date/'YYYY-MM-DD HH:MM:SS'）+ amount
    - days: 近N天窗口
    返回: [{'date': 'YYYY-MM-DD', 'bonus': float}, ...] 按日期升序共 days 项，无记录的天补 0
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)

    daily = {}
    for row in rows:
        d = _parse_created_date(row.get('created_at'))
        if d is None or not (start <= d <= today):
            continue
        daily[d] = daily.get(d, 0.0) + float(row.get('amount') or 0)

    result = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        result.append({'date': d.isoformat(), 'bonus': round(daily.get(d, 0.0), 1)})
    return result


def build_daily_xp(listening_daily, bonus_daily):
    """合并 listening + bonus 为每日总经验（经验详情弹窗 daily_xp）

    - listening_daily: accumulate_daily_logs 输出 [{'date','duration'}]（来自 user_listening_log，1秒=1XP）
    - bonus_daily: accumulate_bonus_daily 输出 [{'date','bonus'}]（来自 user_xp_log 加分行）
    两序列同窗口同升序，按 date 对齐合并。
    返回: [{'date','listening','bonus','total'}, ...]，total = listening + bonus（保留 1 位小数）
    """
    bonus_by_date = {item['date']: float(item['bonus'] or 0) for item in bonus_daily}
    result = []
    for item in listening_daily:
        d = item['date']
        listening = round(float(item['duration'] or 0), 1)
        bonus = round(bonus_by_date.get(d, 0.0), 1)
        result.append({
            'date': d,
            'listening': listening,
            'bonus': bonus,
            'total': round(listening + bonus, 1),
        })
    return result
