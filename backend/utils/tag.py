# MusicRate\backend\utils\tag.py 标签聚合统计（搜索页 / 专辑详情气泡图共用）
#
# 性能背景（2026-11 修复「搜索一直卡在搜索中」）：
#   老实现每次调用都 `SELECT tags FROM albums_N WHERE source_pool_id = %s` 把**所有**用户表
#   扫一遍。用户表数量 = 用户数量（线上有 1199 张），所以单张专辑的标签统计要 ~1.0s，
#   而搜索接口一页 10 张专辑 = 10 次调用 ≈ 11s，超过前端 axios 10s 超时 → 页面永远“搜索中”。
#
# 现实现：
#   1) 一次调用把【整页需要的 pool_id】合并成一条批量查询（UNION ALL，按块拼接）→ 一次扫描
#   2) 扫描结果按 pool_id 聚合后进进程内缓存（默认 120s），翻页/重复搜索直接命中
#   3) 对外 API 不变：get_album_tag_stats(album_pool_id, cursor) → 气泡图用的统计数组
import json
import random
import time

# 缓存有效期（秒）：用户改标签后最多延迟这么久才反映到聚合气泡图，换取搜索/详情页的响应速度
CACHE_TTL_SECONDS = 120
# UNION ALL 每块拼接的表数量（避免单条 SQL 过长）
UNION_CHUNK_SIZE = 200

# {pool_id: {'counts': {tag: count}, 'total': int}} —— 进程内聚合缓存
_COUNTS_CACHE = {'at': 0.0, 'data': {}}


# ================= 纯逻辑（便于单测） =================

def parse_tags(raw):
    """把 tags 字段（JSON 数组字符串）解析成标签列表；非法/空值返回 []

    兼容：JSON 数组、单个字符串、非列表 JSON。
    """
    if not raw:
        return []
    try:
        value = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
    except (ValueError, TypeError):
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result = []
    for tag in value:
        if isinstance(tag, str) and tag.strip():
            result.append(tag.strip())
    return result


def build_tag_stats(tag_count, total_tags):
    """统计数组生成：占比 <10% 的标签过滤掉；size = 占比×2+40；颜色随机

    入参 tag_count: {tag: count}；total_tags: 标签出现总次数
    """
    result = []
    if not total_tags or total_tags <= 0:
        return result
    for tag, count in tag_count.items():
        percent = (count / total_tags) * 100
        if percent < 10:
            continue
        result.append({
            "tag": tag,
            "count": count,
            "percent": round(percent, 1),
            "size": int(percent * 2 + 40),
            "color": f"#{random.randint(0, 0xFFFFFF):06x}",
        })
    return result


def merge_tag_counts(target, source):
    """把 source 的 {tag: count} 合并进 target（原地累加），返回累加的总次数"""
    added = 0
    for tag, count in source.items():
        target[tag] = target.get(tag, 0) + count
        added += count
    return added


def chunked(seq, size):
    """把列表切成 size 大小的块"""
    return [seq[i:i + size] for i in range(0, len(seq), size)] if size > 0 else [list(seq)]


# ================= 缓存 =================

def invalidate_cache():
    """清空聚合缓存（标签/专辑被修改后可主动调用）"""
    _COUNTS_CACHE['at'] = 0.0
    _COUNTS_CACHE['data'] = {}


def _cache_valid():
    return (time.time() - _COUNTS_CACHE['at']) < CACHE_TTL_SECONDS


# ================= 数据库扫描 =================

def list_user_tables(cursor):
    """所有用户专辑表名（albums_1、albums_2 …）"""
    cursor.execute(
        'SELECT table_name AS t FROM information_schema.tables '
        "WHERE table_schema = DATABASE() AND table_name LIKE 'albums\\_%'"
    )
    names = []
    for row in cursor.fetchall():
        name = row.get('t') if isinstance(row, dict) else row[0]
        if name:
            names.append(name)
    return names


def _accumulate(counts, rows):
    """把 (source_pool_id, tags) 行累加进 counts（原地修改）"""
    for row in rows:
        pool_id = row.get('source_pool_id') if isinstance(row, dict) else row[1]
        tags_raw = row.get('tags') if isinstance(row, dict) else row[2]
        if pool_id is None:
            continue
        bucket = counts.setdefault(pool_id, {})
        for tag in parse_tags(tags_raw):
            bucket[tag] = bucket.get(tag, 0) + 1


def scan_user_tags(cursor, pool_ids=None):
    """批量扫描所有用户专辑表 → {pool_id: {tag: count}}

    pool_ids 为 None 表示统计所有专辑；否则只取这些 pool_id。
    实现：把表按 UNION_CHUNK_SIZE 分块拼成一条 SQL，避免 1000+ 次往返；
    某一块失败（异构老表缺列等）时回退成逐表查询，不让一张坏表拖累整块统计。
    """
    tables = list_user_tables(cursor)
    if not tables:
        return {}

    counts = {}
    id_filter_sql = ''
    id_filter_params = []
    if pool_ids:
        id_filter_sql = f" AND source_pool_id IN ({', '.join(['%s'] * len(pool_ids))})"
        id_filter_params = list(pool_ids)

    for chunk in chunked(tables, UNION_CHUNK_SIZE):
        parts = []
        params = []
        for index, table_name in enumerate(chunk):
            parts.append(
                f"SELECT {index} AS src, source_pool_id, tags FROM `{table_name}` "
                f"WHERE tags IS NOT NULL AND tags <> ''{id_filter_sql}"
            )
            params.extend(id_filter_params)
        try:
            cursor.execute(' UNION ALL '.join(parts), params)
            _accumulate(counts, cursor.fetchall())
            continue
        except Exception as e:  # noqa: BLE001 - 单块失败回退逐表，仍要尽量统计完整
            print(f"⚠️ 批量统计用户标签失败，回退逐表（{len(chunk)} 张表）：{e}")

        for table_name in chunk:
            try:
                cursor.execute(
                    f"SELECT source_pool_id, tags FROM `{table_name}` "
                    f"WHERE tags IS NOT NULL AND tags <> ''{id_filter_sql}",
                    id_filter_params
                )
                _accumulate(counts, cursor.fetchall())
            except Exception as table_error:  # noqa: BLE001 - 跳过坏表
                print(f"⚠️ 统计用户表 {table_name} 失败（跳过）：{table_error}")
    return counts


def _fetch_pool_tags(cursor, pool_ids=None):
    """公共专辑池自身的标签 → {pool_id: {tag: count}}（pool_ids=None 表示全量）"""
    if pool_ids is None:
        cursor.execute('SELECT id, tags FROM album_pool')
    else:
        if not pool_ids:
            return {}
        cursor.execute(
            f"SELECT id, tags FROM album_pool WHERE id IN ({', '.join(['%s'] * len(pool_ids))})",
            list(pool_ids)
        )
    counts = {}
    for row in cursor.fetchall():
        pool_id = row.get('id') if isinstance(row, dict) else row[0]
        tags_raw = row.get('tags') if isinstance(row, dict) else row[1]
        tags = parse_tags(tags_raw)
        if tags:
            bucket = {}
            for tag in tags:
                bucket[tag] = bucket.get(tag, 0) + 1
            counts[pool_id] = bucket
    return counts


def load_full_snapshot(cursor):
    """全量重建缓存：一次扫描所有用户表 + album_pool → 写满缓存

    单条 UNION ALL 扫描的成本与「只查 10 个 pool_id」几乎相同（表数量决定开销），
    因此干脆全量统计并缓存，后续任意专辑命中缓存，不再出现「换一张专辑就重扫一遍」。
    注：album_pool 里没有标签的专辑也会写入空桶，保证全量快照对每个 pool_id 都有答案，
    否则「无标签专辑」每次查询都会判定未命中而反复重扫。
    """
    combined = {}
    cursor.execute('SELECT id FROM album_pool')
    for row in cursor.fetchall():
        pid = row.get('id') if isinstance(row, dict) else row[0]
        if pid is not None:
            combined.setdefault(pid, {})
    for pid, bucket in _fetch_pool_tags(cursor, None).items():
        combined.setdefault(pid, {}).update(bucket)
    for pid, bucket in scan_user_tags(cursor, None).items():
        target = combined.setdefault(pid, {})
        merge_tag_counts(target, bucket)

    snapshot = {}
    for pid, counts in combined.items():
        snapshot[pid] = {'counts': counts, 'total': sum(counts.values())}
    _COUNTS_CACHE['data'] = snapshot
    _COUNTS_CACHE['at'] = time.time()
    return snapshot


def collect_tag_counts(cursor, pool_ids):
    """取若干专辑的标签计数 → {pool_id: {'counts': {...}, 'total': n}}

    公共池标签 + 所有用户副本标签合并（与老实现口径一致）。
    缓存是「全量快照」，有效期内任何 pool_id 都直接查表返回，不再打库。
    """
    pool_ids = [int(pid) for pid in (pool_ids or [])]
    if not pool_ids:
        return {}

    snapshot = _COUNTS_CACHE['data'] if _cache_valid() else load_full_snapshot(cursor)

    result = {}
    for pid in pool_ids:
        data = snapshot.get(pid)
        result[pid] = data if data else {'counts': {}, 'total': 0}
    return result


def get_album_tag_stats(album_pool_id, cursor):
    """单个专辑的标签气泡统计（对外 API，保持老签名不变）

    :param album_pool_id: album_pool.id
    :param cursor: 调用方的游标（同一连接，保证事务内一致）
    :return: [{'tag','count','percent','size','color'}, ...]
    """
    data = collect_tag_counts(cursor, [album_pool_id]).get(album_pool_id, {'counts': {}, 'total': 0})
    return build_tag_stats(data['counts'], data['total'])


def get_album_tag_stats_map(cursor, pool_ids):
    """批量版：列表页一次取到 {pool_id: 统计数组}，只触发一次扫描"""
    counts_map = collect_tag_counts(cursor, pool_ids)
    return {
        pid: build_tag_stats(data['counts'], data['total'])
        for pid, data in counts_map.items()
    }
