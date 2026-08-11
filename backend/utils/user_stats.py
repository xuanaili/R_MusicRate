# MusicRate\backend\utils\user_stats.py 音乐统计口径纯函数（v0.7 P2 + v0.7.1 P1，零 DB 依赖，可单测）
# 统计口径（防重复计数，参考 README v0.7 P2 统计口径表 + v0.7.1 P1 口径统一）：
# - 听取总时长：v0.7.1 P1 起改读 users.listening_total（持久化列，删专辑不掉）；不再 SUM albums.listening_duration
# - 近N天听取时长：仅用 user_listening_log 按 listen_date 分组累加（柱状图专用）
# - 活跃度：连续收听天数 / 近 30 天活跃天数，由 user_listening_log 计算（compute_current_streak / compute_active_days）
# - 已评分 / 听后感：my_score / review 非空且非 "[]"
# - 标签分布：albums.tags 逐行解析前 top_n 个高频标签（气泡图）
# - 评分分布：按总分分桶（0 分未评分不计入）
import datetime
import json

from backend.utils.json import safe_json_loads
from backend.utils.score import calculate_album_total_score

# 近N天窗口白名单
VALID_DAYS = (7, 14, 30)


def is_scored(my_score):
    """已评分判断：my_score 数组含至少一个非 0 评分（评分格式 0=未评分）。
    None/""/"[]"/全0数组 → False；如 [0, 8.5, 0] → True"""
    parsed = safe_json_loads(my_score)
    if not isinstance(parsed, list) or len(parsed) == 0:
        return False
    return any(isinstance(s, (int, float)) and s > 0 for s in parsed)


def has_review(review):
    """听后感判断：review 非空且非空数组（"[]"）。None/""/"[]" → False"""
    parsed = safe_json_loads(review)
    return isinstance(parsed, list) and len(parsed) > 0


def parse_days_param(days, default=7):
    """days 参数归一化：仅接受 7/14/30，其他值（含 None/非数字/越界）回退默认 7"""
    try:
        days = int(days)
    except (TypeError, ValueError):
        return default
    return days if days in VALID_DAYS else default


def _parse_log_date(value):
    """解析 user_listening_log.listen_date 行为 date 对象；None / 非法 → None

    PyMySQL 对 DATE 列返回 datetime.date、DATETIME 返回 datetime.datetime，代码层统一转 date
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return None


def accumulate_daily_logs(rows, days):
    """按天累加 + 近N天补零序列（柱状图数据源，含今天）

    - rows: user_listening_log 行，元素为 {'listen_date': date或'YYYY-MM-DD', 'duration_seconds': float}
    - days: 近N天窗口
    返回: [{'date': 'YYYY-MM-DD', 'duration': float}, ...]，按日期升序共 days 项，无记录的天补 0
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)

    # 按天累加（同一天多张专辑 → 求和）
    daily = {}
    for row in rows:
        d = _parse_log_date(row.get('listen_date'))
        if d is None:
            continue
        daily[d] = daily.get(d, 0.0) + float(row.get('duration_seconds') or 0)

    # 近N天补零序列
    result = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        result.append({'date': d.isoformat(), 'duration': round(daily.get(d, 0.0), 1)})
    return result


def compute_current_streak(rows):
    """连续收听天数：从最近一个有收听的日期往回连续非 0 的天数（v0.7.1 P1）

    断签语义（标准）：只要「昨天及更早」存在一个整天没有任何收听（且该天晚于最近收听日），连续即中断；
    今天尚未收听【不算断签】（今天还没结束，锚点 = 最近有收听那天）
    - rows: user_listening_log 行，元素含 listen_date / duration_seconds
    返回: int，无任何收听 → 0
    """
    listened = set()
    for row in rows:
        d = _parse_log_date(row.get('listen_date'))
        if d is not None and float(row.get('duration_seconds') or 0) > 0:
            listened.add(d)
    if not listened:
        return 0

    last = max(listened)
    today = datetime.date.today()
    # 最近收听日早于昨天（今天、昨天都无收听）→ 已过完整无收听日，断签
    if last < today - datetime.timedelta(days=1):
        return 0

    streak = 0
    day = last
    while day in listened:
        streak += 1
        day -= datetime.timedelta(days=1)
    return streak


def compute_active_days(rows, days=30):
    """近 N 天活跃天数：最近 days 天内（含今天）有收听（时长>0）的不同日期数（v0.7.1 P1）

    - rows: user_listening_log 行，元素含 listen_date / duration_seconds
    - days: 窗口天数（默认 30）
    返回: int
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    active = set()
    for row in rows:
        d = _parse_log_date(row.get('listen_date'))
        if d is None or not (start <= d <= today):
            continue
        if float(row.get('duration_seconds') or 0) > 0:
            active.add(d)
    return len(active)


def build_tag_distribution(albums, top_n=8):
    """标签分布：逐行解析 tags JSON，统计前 top_n 个高频标签（气泡图数据源）

    - albums: 专辑行，元素含 'tags'（JSON 字符串数组）
    返回: [{'name': 'Pop【流行】', 'value': 3}, ...] 按频次降序取前 top_n
    """
    counter = {}
    for album in albums:
        tags = safe_json_loads(album.get('tags'))
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if tag:
                counter[tag] = counter.get(tag, 0) + 1
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    return [{'name': name, 'value': cnt} for name, cnt in items]


def build_score_distribution(albums, bucket_size=10):
    """评分分布：按【综合总分】分桶（0 分未评分不计入）

    ⚠️ 总分来源是 my_score 经 calculate_album_total_score 计算，而非 albums.score 列
    （score 列是评论均分，只在评论时更新，未评论的已评分专辑会是 0 → 用它会漏掉已评分专辑）
    - albums: 专辑行，元素含 'my_score'（评分数组 JSON）
    返回: [{'bucket': '0-9', 'count': n}, ...] 共 10 个桶
    """
    buckets = {}
    for i in range(0, 100, bucket_size):
        end = 100 if i + bucket_size >= 100 else i + bucket_size - 1
        buckets[i] = {'bucket': f'{i}-{end}', 'count': 0}
    for album in albums:
        score = calculate_album_total_score(safe_json_loads(album.get('my_score')))
        if score <= 0:
            continue
        idx = int(score) // bucket_size
        if idx >= 100 // bucket_size:
            idx = (100 // bucket_size) - 1
        buckets[idx * bucket_size]['count'] += 1
    return [v for _, v in sorted(buckets.items())]


def aggregate_stats(album_rows, daily_rows, days, total_duration=None):
    """统计聚合（纯函数）：由 albums 行 + user_listening_log 行计算全部口径，防重复计数

    - album_rows: albums_{user_id} 行，元素含 my_score/review/listening_duration/tags（score 列不用，评分分布由 my_score 计算总分）
    - daily_rows: user_listening_log 行（建议传近 30 天窗口，供活跃度计算；窗口外行会被 accumulate 忽略）
    - days: 近N天窗口（7/14/30）
    - total_duration: 持久化听取总秒数（users.listening_total，删专辑不掉）；为 None 时回退 SUM(albums.listening_duration)
    返回:
        {
            'album_count': int, 'scored_count': int, 'review_count': int,
            'total_duration': float,       # v0.7.1 P1 起读 users.listening_total（口径统一，删专辑不掉）
            'current_streak': int,         # 连续收听天数
            'active_days_30': int,         # 近 30 天活跃天数
            'daily_listening': [{'date', 'duration'}...],  # 仅来自 user_listening_log
            'tag_distribution': [{'name', 'value'}...],
            'score_distribution': [{'bucket', 'count'}...],
        }
    """
    if total_duration is None:
        total_duration = round(sum(float(a.get('listening_duration') or 0) for a in album_rows), 1)
    return {
        'album_count': len(album_rows),
        'scored_count': sum(1 for a in album_rows if is_scored(a.get('my_score'))),
        'review_count': sum(1 for a in album_rows if has_review(a.get('review'))),
        'total_duration': round(float(total_duration or 0), 1),
        'current_streak': compute_current_streak(daily_rows),
        'active_days_30': compute_active_days(daily_rows, 30),
        'daily_listening': accumulate_daily_logs(daily_rows, days),
        'tag_distribution': build_tag_distribution(album_rows),
        'score_distribution': build_score_distribution(album_rows),
    }
