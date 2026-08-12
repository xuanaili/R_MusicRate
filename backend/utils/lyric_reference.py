# MusicRate\backend\utils\lyric_reference.py 平台参考歌词拉取（v0.8.1 增补）
# 作用：DeepSeek 校正环节按曲目标题+歌手实时拉取网易云/酷狗/QQ 官方歌词作参考，
#       只用于消除中文同音字/错字/断句歧义——参考文本注入校正 prompt，不改草稿行文与时间戳。
# 决策（README v0.8.1）：
#   - 平台优先级：网易云 → 酷狗 → QQ（用户拍板）；每曲取第一个成功平台，失败自动降级
#   - 不缓存现拉现用（用户拍板，无新表）；每请求 5s 超时，网络失败/无参考不阻断校正
#   - 匹配策略：pick_best_match 要求「曲名 ≥1 + 歌手精确匹配」，防止翻唱/remix 的错歌词混入参考
#   - 实测（2026-08-12）：网易云受限歌手（周杰伦等）搜不到原始版→返回 None 兜底；酷狗歌词接口反爬→返回 None；
#     QQ 全链路可用，是可靠兜底层
# 纯逻辑部分（parse_lrc_text / pick_best_match / build_reference_text / fetch_one_track / fetch_all_references）
#   零网络可单测（test_lyric_reference.py）；fetch_netease/fetch_kugou/fetch_qq 属 realdata
import json
import re

import requests

from backend.utils.lrc import parse_any_to_items

# 平台优先级：网易云 → 酷狗 → QQ（README 拍板）；下方三个 fetch 函数定义后填充
PLATFORM_FETCHERS = []

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

# 歌手分隔符（专辑 singer 字段常含多歌手/feat）
_SINGER_SPLIT_RE = re.compile(r'[,、;/&（(]|feat\.?', re.IGNORECASE)


def parse_lrc_text(raw):
    """任意 LRC 文本 → 纯歌词文字行列表（去时间戳/元数据/空行，保留顺序）
    - 复用 lrc.parse_any_to_items（兼容方括号 LRC 与存储格式 mm:ss 两路径）
    - 同一行多时间标签产生的重复文本去重（保留首个，参考文本更紧凑）
    - 返回 [text, ...]；空/无有效行返回 []
    """
    if not raw:
        return []
    items = parse_any_to_items(raw)
    seen = set()
    out = []
    for it in items:
        if it['text'] not in seen:
            seen.add(it['text'])
            out.append(it['text'])
    return out


def _strip_brackets(text):
    """去掉括号及其内容（（女声版）(Live)(伴奏) 等标题后缀噪音）"""
    return re.sub(r'[（(][^（）()]*[）)]', '', text or '')


def pick_best_match(candidates, title, singer):
    """从候选歌曲中挑选与「曲名+歌手」最匹配的一条（纯函数，可单测）
    - candidates: [{name: str, artists: [str,...], ...}]，附加字段（如歌曲 id）透传不受影响
    - 曲名分：与目标曲名一致（含去括号后缀）→ 2；目标曲名是候选曲名子串 → 1
    - 歌手分：任一歌手名与目标歌手（按 ,、;/&feat 拆多歌手后）精确一致 → 2；子串包含 → 1
    - 只接受「曲名分 ≥ 1 且（歌手为空 或 歌手分 ≥ 2）」的候选——歌手不精确匹配的翻唱/remix 直接拒绝，
      防止其歌词与原始版不同而污染参考（网易云受限歌手场景常见）
    - 返回最高分候选；无匹配 → None
    """
    title_n = re.sub(r'\s+', '', title or '')
    singer_parts = [
        re.sub(r'\s+', '', p) for p in _SINGER_SPLIT_RE.split(singer or '') if p.strip()
    ]
    best = None
    best_score = 0
    for c in candidates:
        name = c.get('name') or ''
        name_n = re.sub(r'\s+', '', name)
        title_score = 0
        if name_n and title_n:
            if name_n == title_n or _strip_brackets(name_n) == _strip_brackets(title_n):
                title_score = 2
            elif title_n in name_n:
                title_score = 1
        artist_score = 0
        if singer_parts:
            artist_names = [re.sub(r'\s+', '', a or '') for a in c.get('artists') or []]
            if any(a_n in singer_parts for a_n in artist_names):
                artist_score = 2
            elif any(any(s_n in a_n or a_n in s_n for s_n in singer_parts) for a_n in artist_names):
                artist_score = 1
        if title_score < 1:
            continue
        if singer_parts and artist_score < 2:
            continue
        score = title_score + artist_score
        if score > best_score:
            best = c
            best_score = score
    return best


def build_reference_text(results):
    """逐曲参考结果 → 参考段落文本（注入校正 prompt 用）
    - results: [{index, title, text(纯歌词行列表), source}, ...]（只含成功拉到参考的曲目）
    - 格式：每曲一段，段首「【第N首《标题》- 来源：xxx】」，段间空行
    - 无有效结果 → ''
    """
    blocks = []
    for tr in results:
        lines = tr.get('text') or []
        title = tr.get('title') or ''
        source = tr.get('source') or ''
        if not lines:
            continue
        header = f'【第{tr["index"] + 1}首《{title}》- 来源：{source}】'
        blocks.append(header + '\n' + '\n'.join(lines))
    return '\n\n'.join(blocks)


def _http_get_json(url, params, referer=None, timeout=5):
    """GET + 解析 JSON（兼容 JSONP 包裹如 MusicJsonCallback(...)），失败返回 None
    - 带常见浏览器 UA，可选 Referer（QQ/网易云部分接口要求）
    - 返回 dict/list；请求失败/非 JSON/空响应 → None
    """
    headers = {'User-Agent': _UA}
    if referer:
        headers['Referer'] = referer
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        text = (r.text or '').strip()
        if not text:
            return None
        if not (text.startswith('{') or text.startswith('[')):
            start = text.find('(')
            end = text.rfind(')')
            if start != -1 and end > start:
                text = text[start + 1:end]
        return json.loads(text)
    except Exception:
        return None


def _keyword(title, singer):
    """搜索关键词：曲名+歌手拼接；空曲名回退歌手名，全空回退空串"""
    keyword = f'{title} {singer}'.strip()
    return keyword or (title or '')


def fetch_netease(title, singer, timeout=5):
    """网易云：搜索 → pick_best_match（防翻唱/remix）→ 拉 LRC。成功 {'text': [...], 'source': '网易云'}，失败 None"""
    keyword = _keyword(title, singer)
    data = _http_get_json(
        'https://music.163.com/api/search/get/web',
        {'s': keyword, 'type': 1, 'limit': 10},
        referer='https://music.163.com', timeout=timeout,
    )
    if not isinstance(data, dict):
        return None
    songs = (data.get('result') or {}).get('songs') or []
    candidates = [
        {
            'name': s.get('name', ''),
            'artists': [a.get('name', '') for a in s.get('artists') or []],
            '_id': s.get('id'),
        }
        for s in songs
    ]
    best = pick_best_match(candidates, title, singer)
    if not best or not best.get('_id'):
        return None
    lrc_data = _http_get_json(
        'https://music.163.com/api/song/lyric',
        {'id': best['_id'], 'lv': -1, 'kv': -1, 'tv': -1},
        referer='https://music.163.com', timeout=timeout,
    )
    if not isinstance(lrc_data, dict):
        return None
    lrc = (lrc_data.get('lrc') or {}).get('lyric') or ''
    lines = parse_lrc_text(lrc)
    if not lines:
        return None
    return {'text': lines, 'source': '网易云'}


def search_kugou(title, singer, timeout=5):
    """酷狗 songsearch_v2 搜索（公共：搜索层独立验证/调试用，返回候选列表）
    - 返回 [{name, artists, _hash, _album_id, _duration}, ...]；失败 → []
    """
    keyword = _keyword(title, singer)
    data = _http_get_json(
        'https://songsearch.kugou.com/song_search_v2',
        {'keyword': keyword, 'page': 1, 'pagesize': 10, 'platform': 'WebFilter'},
        timeout=timeout,
    )
    if not isinstance(data, dict):
        return []
    lists = (data.get('data') or {}).get('lists') or []
    candidates = []
    for it in lists:
        singer_names = [s.strip() for s in (it.get('SingerName') or '').split(',') if s.strip()]
        candidates.append({
            'name': it.get('SongName') or '',
            'artists': singer_names,
            '_hash': it.get('FileHash') or it.get('Hash'),
            '_album_id': it.get('AlbumID') or '',
            '_duration': it.get('Duration') or 0,
        })
    return candidates


def fetch_kugou(title, singer, timeout=5):
    """酷狗：search_kugou 搜索 → pick_best_match → krcs 拉 LRC。
    注意：酷狗歌词接口当前反爬（krcs 空响应），通常返回 None（兜底到 QQ）；保留搜索层，接口恢复即可用"""
    candidates = search_kugou(title, singer, timeout=timeout)
    best = pick_best_match(candidates, title, singer)
    if not best or not best.get('_hash'):
        return None
    lyric_data = _http_get_json(
        'https://krcs.kugou.com/api/v3/lyric/get',
        {'hash': best['_hash'], 'album_id': best['_album_id'],
         'timelength': (best.get('_duration') or 0) * 1000, 'format': 'json'},
        timeout=timeout,
    )
    if not isinstance(lyric_data, dict):
        return None
    lyrics = (lyric_data.get('data') or {}).get('lyrics') or ''
    lines = parse_lrc_text(lyrics)
    if not lines:
        return None
    return {'text': lines, 'source': '酷狗'}


def fetch_qq(title, singer, timeout=5):
    """QQ 音乐：搜索 → pick_best_match → 拉 LRC。成功 {'text': [...], 'source': 'QQ音乐'}，失败 None"""
    keyword = _keyword(title, singer)
    data = _http_get_json(
        'https://c.y.qq.com/soso/fcgi-bin/client_search_cp',
        {'w': keyword, 'format': 'json', 'n': 10, 'cr': 1, 'g_tk': 5381, 'loginUin': 0},
        referer='https://y.qq.com', timeout=timeout,
    )
    if not isinstance(data, dict):
        return None
    song_list = (data.get('data') or {}).get('song') or {}
    songs = song_list.get('list') or []
    candidates = [
        {
            'name': s.get('songname', ''),
            'artists': [a.get('name', '') for a in s.get('singer') or []],
            '_mid': s.get('songmid'),
        }
        for s in songs
    ]
    best = pick_best_match(candidates, title, singer)
    if not best or not best.get('_mid'):
        return None
    lyric_data = _http_get_json(
        'https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg',
        {'songmid': best['_mid'], 'format': 'json', 'nobase64': 1, 'g_tk': 5381, 'loginUin': 0},
        referer='https://y.qq.com', timeout=timeout,
    )
    # retcode != 0（如需要登录）视为无歌词
    if not isinstance(lyric_data, dict) or lyric_data.get('retcode', 0) != 0:
        return None
    lyric = lyric_data.get('lyric') or ''
    if not lyric:
        return None
    try:
        from urllib.parse import unquote
        lyric = unquote(lyric)  # 兼容 percent-encoded 返回
    except Exception:
        pass
    lines = parse_lrc_text(lyric)
    if not lines:
        return None
    return {'text': lines, 'source': 'QQ音乐'}


# 平台优先级（README 拍板）：网易云 → 酷狗 → QQ
PLATFORM_FETCHERS = [fetch_netease, fetch_kugou, fetch_qq]


def fetch_one_track(title, singer, fetchers=None, timeout=5):
    """单曲按平台优先级拉参考歌词（逐级兜底，取第一个成功平台）
    - fetchers: 平台拉取函数列表（默认 [fetch_netease, fetch_kugou, fetch_qq]；单测注入假函数）
    - 单个平台失败（返回 None / 抛异常）自动降级下一个；全部失败 → None
    - 成功 → {'text': [行...], 'source': str}
    """
    fetchers = fetchers if fetchers is not None else PLATFORM_FETCHERS
    for fetcher in fetchers:
        try:
            result = fetcher(title, singer, timeout=timeout)
        except Exception:
            result = None
        if result and result.get('text'):
            return result
    return None


def fetch_all_references(tracks, singer, fetchers=None, timeout=5):
    """逐曲拉参考歌词 → 参考段落文本（注入校正 prompt 用）
    - tracks: [title, ...]（album_pool.tracks 解析后的曲目列表）
    - 成功曲目按 build_reference_text 组装；全失败/无曲目 → ''
    - 返回 (reference_text, stats)：stats = {total, fetched, sources:{来源:数量}}
    """
    results = []
    stats = {'fetched': 0, 'total': len(tracks or []), 'sources': {}}
    for i, title in enumerate(tracks or []):
        title = (title or '').strip()
        if not title:
            continue
        res = fetch_one_track(title, singer, fetchers=fetchers, timeout=timeout)
        if res:
            results.append({'index': i, 'title': title, 'text': res['text'], 'source': res['source']})
            stats['fetched'] += 1
            stats['sources'][res['source']] = stats['sources'].get(res['source'], 0) + 1
    return build_reference_text(results), stats
