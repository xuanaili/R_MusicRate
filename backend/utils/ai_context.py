# MusicRate\backend\utils\ai_context.py AI 助手上下文组装纯函数（v0.8.1 P5，零 DB / 网络依赖）
# 作用：把专辑/歌手/评分/听后感/标签/BPM/当前歌歌词/平台评论/全网听后感组装成 system prompt，
#       供 backend/api/ai.py 的 chat 调用（镜像 BookRate _build_system_prompt 分层结构）。
# 设计（README v0.8.1）：
#   - 纯函数零 DB → 可单测（test_ai_context.py），DB 查询留在 ai.py
#   - 各段截断：专辑简介 600 / 歌手简介 400 / 标签 200 / 当前歌词 1200 / 评论每条 150 / 听后感每条 180
#   - 结尾强约束「优先依据以上上下文，信息不足如实告知，不编造」
#   - 复用 lrc.parse_any_to_items + lyric_recognizer.split_by_tracks_time 切当前曲目歌词
from backend.utils.lrc import parse_any_to_items
from backend.utils.lyric_recognizer import split_by_tracks_time

# 聚合限额（README v0.8.1）：评论 15 条；全网听后感每用户最新 3 条、总量 cap 20；对话历史最近 20 条
COMMENT_LIMIT = 15
REVIEW_TOTAL_CAP = 20
REVIEW_PER_USER = 3
HISTORY_LIMIT = 20

# 各段截断上限
_ALBUM_INTRO_CAP = 600
_SINGER_INTRO_CAP = 400
_TAGS_CAP = 200
_LYRIC_CAP = 1200
_COMMENT_LINE_CAP = 150
_REVIEW_LINE_CAP = 180


def _truncate(text, max_len):
    """截断长文本，保留开头，避免上下文过长；空/None → ''"""
    text = (text or '').strip()
    if not text:
        return ''
    if len(text) > max_len:
        return text[:max_len] + '…'
    return text


def format_score(my_score):
    """my_score 数组 → 你的评分文本（my_score[0] = 专辑整体评分，其余为单曲评分，0 = 未评分）
    - 空 / 无有效评分 → ''
    """
    if not my_score:
        return ''
    album_score = my_score[0] if len(my_score) > 0 else 0
    track_scores = my_score[1:]
    parts = []
    if album_score:
        parts.append(f'专辑整体评分：{album_score}分')
    if track_scores:
        parts.append('单曲评分：[' + ', '.join(str(s) for s in track_scores) + ']（0 表示未评分）')
    return '；'.join(parts)


def parse_feelings(review):
    """review 字段 → 听后感条目列表（兼容 dict {'feelings':[...]} 与旧数组两种格式）
    - dict → feelings 数组；list → 直接作为条目（过滤非 dict）
    - 空 → []
    """
    if not review:
        return []
    if isinstance(review, dict):
        return review.get('feelings') or []
    if isinstance(review, list):
        return [f for f in review if isinstance(f, dict)]
    return []


def format_own_feelings(feelings):
    """用户本专辑听后感 → 文本（编号 + 内容，附当时评分/时间）；空 → ''
    feeling 结构：{content, create_time, my_score}（review.py 落库格式）
    """
    if not feelings:
        return ''
    lines = []
    for i, f in enumerate(feelings, 1):
        content = (f.get('content') or '').strip()
        if not content:
            continue
        suffix = []
        if f.get('my_score'):
            suffix.append(f'当时评分 {f["my_score"]}')
        if f.get('create_time'):
            suffix.append(str(f['create_time']))
        lines.append(f'{i}. {content}' + (f'（{"，".join(suffix)}）' if suffix else ''))
    return '\n'.join(lines)


def format_tempo(tempo_dict, tracks=None):
    """album_tempo JSON → 单曲节奏文本（只列有效 BPM；0 = 无法测拍跳过）；空 → ''
    - tracks 与 track_tempos 等长时按曲目名列出，否则用「单曲N」
    - 附整专平均 / 区间
    """
    if not tempo_dict:
        return ''
    track_tempos = tempo_dict.get('track_tempos') or []
    tracks = tracks or []
    lines = []
    for i, bpm in enumerate(track_tempos):
        if not bpm:
            continue
        name = tracks[i] if i < len(tracks) and tracks[i] else f'单曲{i + 1}'
        lines.append(f'{name}：{bpm} BPM')
    avg = tempo_dict.get('avg_bpm')
    min_bpm = tempo_dict.get('min_bpm')
    max_bpm = tempo_dict.get('max_bpm')
    if avg:
        range_txt = f'（区间 {min_bpm}~{max_bpm} BPM）' if min_bpm and max_bpm else ''
        lines.append(f'整专平均：{avg} BPM{range_txt}')
    return '\n'.join(lines)


def extract_current_track_lyric(lyric_text, tracks_time, current_track_index):
    """整轨歌词 → 当前播放曲目的歌词切片（纯文字行，去时间戳）；空 → ''
    - tracks_time[i] 为第 i 首起始秒（与 split_by_tracks_time 口径一致）
    - tracks_time 为空 → 整轨视为一首（无论 index，归 track 0）
    - index 越界 / 无歌词 → ''（优雅降级，不阻断上下文）
    """
    if not lyric_text or current_track_index is None:
        return ''
    items = parse_any_to_items(lyric_text)
    if not items:
        return ''
    groups = split_by_tracks_time(items, tracks_time)
    idx = current_track_index if tracks_time else 0
    track_items = groups.get(idx) or []
    if not track_items:
        return ''
    return '\n'.join(it['text'] for it in track_items)


def format_comments(comments):
    """平台评论（[{username, content}, ...]）→ 文本；空 → ''
    - 每条「- username：content」，content 截断 150
    """
    if not comments:
        return ''
    lines = []
    for c in comments:
        content = (c.get('content') or '').strip()
        if not content:
            continue
        lines.append(f"- {c.get('username', '匿名')}：{_truncate(content, _COMMENT_LINE_CAP)}")
    return '\n'.join(lines)


def format_reviews(reviews):
    """全网听后感精选（[{username, rating, content}, ...]）→ 文本；空 → ''
    - 每条「- username（评分X）：content」，content 截断 180
    """
    if not reviews:
        return ''
    lines = []
    for r in reviews:
        content = (r.get('content') or '').strip()
        if not content:
            continue
        rating = f"，评分{r['rating']}" if r.get('rating') else ''
        lines.append(f"- {r.get('username', '匿名')}{rating}：{_truncate(content, _REVIEW_LINE_CAP)}")
    return '\n'.join(lines)


def build_system_prompt(
    album_name, singer, album_intro='', tracks=None, release_year=None, main_type='',
    own_tags=None, own_score=None, own_feelings=None, singer_intro='',
    tempo_text='', current_lyric_text='', comments_text='', other_reviews_text='',
):
    """组装 AI 助手 system prompt（分层结构，镜像 BookRate）
    - 数据有 → 含对应段落；数据空 → 该段落不出现（避免空占位）
    - 结尾强约束：优先依据上下文，信息不足如实告知，不编造
    """
    sections = [
        f'你是MusicRate的AI音乐助手，只围绕用户当前查看的专辑《{album_name}》（歌手：{singer}）展开回答，语气友好、简洁有条理。'
    ]

    # 【专辑信息】名称/歌手/年份/类型/曲目/简介
    info_parts = []
    if album_name:
        info_parts.append(f'专辑名：{album_name}')
    if singer:
        info_parts.append(f'歌手：{singer}')
    if release_year:
        info_parts.append(f'发行年份：{release_year}')
    if main_type:
        info_parts.append(f'类型：{main_type}')
    if tracks:
        info_parts.append(f'曲目（共{len(tracks)}首）：{" / ".join(str(t) for t in tracks)}')
    if album_intro:
        info_parts.append(f'专辑简介：{_truncate(album_intro, _ALBUM_INTRO_CAP)}')
    sections.append('【专辑信息】\n' + '\n'.join(info_parts))

    # 【歌手信息】album_singers.detail_intro best-effort
    if singer_intro:
        sections.append(f'【歌手信息】\n{_truncate(singer_intro, _SINGER_INTRO_CAP)}')

    # 【你的评分】
    if own_score:
        sections.append(f'【你的评分】\n{own_score}')

    # 【你的听后感】
    own_feelings_text = format_own_feelings(own_feelings or [])
    if own_feelings_text:
        sections.append(f'【你的听后感】\n{own_feelings_text}')

    # 【你的标签】
    if own_tags:
        sections.append(f'【你的标签】\n{_truncate("、".join(str(t) for t in own_tags), _TAGS_CAP)}')

    # 【单曲节奏 BPM】
    if tempo_text:
        sections.append(f'【单曲节奏 BPM】\n{tempo_text}')

    # 【当前播放歌曲歌词】
    if current_lyric_text:
        sections.append(f'【当前播放歌曲歌词】\n{_truncate(current_lyric_text, _LYRIC_CAP)}')

    # 【平台评论】
    if comments_text:
        sections.append(f'【平台评论】\n{comments_text}')

    # 【其他用户听后感精选】
    if other_reviews_text:
        sections.append(f'【其他用户听后感精选】\n{other_reviews_text}')

    sections.append('请优先依据以上上下文回答。若信息不足，请如实告知，不要编造专辑、歌手或歌词内容。')
    return '\n\n'.join(sections)
