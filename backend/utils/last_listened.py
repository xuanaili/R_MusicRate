# MusicRate\backend\utils\last_listened.py 最近收听排序纯逻辑（零 DB 依赖，可单测）
# 规则：降序(默认)最新收听在前；升序最早收听在前；从未收听（缺字段/None）固定排最后
import datetime


def last_listened_sort_key(album, sort_order='desc'):
    """最近收听排序 key：从未收听的专辑固定排最后，不受升降序影响。

    - album: 专辑 dict，可能含 last_listened 字段（DATETIME 对象），也可能缺失/为 None
    - sort_order: 'asc' / 'desc'
    降序(默认)时用 datetime.min 兜底（配合 reverse=True 排最后）；
    升序时用 datetime.max 兜底（正常序排最后）。
    """
    listened_time = album.get('last_listened')
    if not listened_time:
        return datetime.datetime.min if sort_order == 'desc' else datetime.datetime.max
    return listened_time
