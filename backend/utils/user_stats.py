# MusicRate\backend\utils\user_stats.py 音乐统计口径纯函数（v0.7 P2，零 DB 依赖，可单测）
# 统计口径（防重复计数，参考 README v0.7 P2 统计口径表）：
# - 听取总时长：仅 SUM(albums.listening_duration) 累计；同一秒数也会写入 user_listening_log，两者【不相加】（相加=重复计数）
# - 近N天听取时长：仅用 user_listening_log 按 listen_date 分组累加（柱状图专用）
# - 已评分 / 听后感：my_score / review 非空且非 "[]"
# - 标签分布：albums.tags 逐行解析前 top_n 个高频标签（气泡图）
# - 评分分布：按总分分桶（0 分未评分不计入）
import datetime
import json

from backend.utils.json import safe_json_loads

# 近N天窗口白名单
VALID_DAYS = (7, 14, 30)


def is_scored(my_score):
    """已评分判断：my_score 非空且非空数组（"[]"）。None/""/"[]" → False"""
    parsed = safe_json_loads(my_score)
    return isinstance(parsed, list) and len(parsed) > 0


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
        d = row.get('listen_date')
        if isinstance(d, str):
            try:
                d = datetime.date.fromisoformat(str(d)[:10])
            except ValueError:
                continue
        if not isinstance(d, datetime.date):
            continue
        daily[d] = daily.get(d, 0.0) + float(row.get('duration_seconds') or 0)

    # 近N天补零序列
    result = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        result.append({'date': d.isoformat(), 'duration': round(daily.get(d, 0.0), 1)})
    return result


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
    """评分分布：按总分分桶（0 分未评分不计入）

    - albums: 专辑行，元素含 'score'（0-100，0 表示未评分）
    返回: [{'bucket': '0-9', 'count': n}, ...] 共 10 个桶
    """
    buckets = {}
    for i in range(0, 100, bucket_size):
        end = 100 if i + bucket_size >= 100 else i + bucket_size - 1
        buckets[i] = {'bucket': f'{i}-{end}', 'count': 0}
    for album in albums:
        score = album.get('score')
        if not score:
            continue
        s = float(score)
        if s <= 0:
            continue
        idx = int(s) // bucket_size
        if idx >= 100 // bucket_size:
            idx = (100 // bucket_size) - 1
        buckets[idx * bucket_size]['count'] += 1
    return [v for _, v in sorted(buckets.items())]


def aggregate_stats(album_rows, daily_rows, days):
    """统计聚合（纯函数）：由 albums 行 + user_listening_log 行计算全部口径，防重复计数

    - album_rows: albums_{user_id} 行，元素含 my_score/review/listening_duration/score/tags
    - daily_rows: user_listening_log 行
    - days: 近N天窗口（7/14/30）
    返回:
        {
            'album_count': int, 'scored_count': int, 'review_count': int,
            'total_duration': float,  # 仅 SUM(albums.listening_duration)，不与 daily 相加
            'daily_listening': [{'date', 'duration'}...],  # 仅来自 user_listening_log
            'tag_distribution': [{'name', 'value'}...],
            'score_distribution': [{'bucket', 'count'}...],
        }
    """
    return {
        'album_count': len(album_rows),
        'scored_count': sum(1 for a in album_rows if is_scored(a.get('my_score'))),
        'review_count': sum(1 for a in album_rows if has_review(a.get('review'))),
        'total_duration': round(sum(float(a.get('listening_duration') or 0) for a in album_rows), 1),
        'daily_listening': accumulate_daily_logs(daily_rows, days),
        'tag_distribution': build_tag_distribution(album_rows),
        'score_distribution': build_score_distribution(album_rows),
    }
