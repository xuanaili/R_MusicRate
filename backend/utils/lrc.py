# MusicRate\backend\utils\lrc.py LRC 歌词纯函数（v0.8 P0-A，零 DB / 网络依赖）
# 与前端 AlbumLyricViewer.vue 的 parseLrcToStandardFormat 双端同构：
#   normalize_to_storage() 输出与前端「逐字符一致」（含 .5 当百分秒等历史怪癖，见下方注释）
# 存储格式（全站唯一）：每行 `mm:ss 歌词` 或 `mm:ss.x 歌词`（1 位小数，无方括号），时间按升序、去重保留首个
import math
import re

# 元数据行过滤正则（与前端 /作词|作曲|编曲|演唱|专辑|by:/i 逐字符一致）
METADATA_RE = re.compile(r'作词|作曲|编曲|演唱|专辑|by:', re.IGNORECASE)

# 标准 LRC 方括号时间标签：2 位分钟 + 2 位秒 + 可选 1~3 位小数（与前端正则逐字符一致）
LRC_TAG_RE = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{1,3}))?\]')

# 存储格式行：mm:ss(.x) 歌词（无方括号，分钟 1~3 位容忍 100+ 分钟）
STORAGE_LINE_RE = re.compile(r'^(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\s+(.*)$')


def _round_half_up(x):
    """复制前端 Math.round 语义（正数四舍五入，.5 进位；Python round 是银行家舍入，不能直接用）"""
    return math.floor(x + 0.5)


def _round_tenths(seconds):
    """四舍五入到 1 位小数：等价前端 `Math.round(t * 10) / 10`"""
    return _round_half_up(seconds * 10) / 10.0


def str_to_seconds(time_str):
    """时间字符串 'mm:ss' / 'mm:ss.xx' → 秒数（浮点）
    小数按真实位数归一：'.5'=0.5、'.05'=0.05、'.123'=0.123（存储格式语义，非前端 parseTimeStr 的 /1000 bug）
    """
    if not time_str:
        return 0
    try:
        minutes_part, _, rest = time_str.partition(':')
        minutes = int(minutes_part)
        if '.' in rest:
            seconds_part, _, ms_part = rest.partition('.')
            seconds = int(seconds_part)
            fraction = float('0.' + ms_part) if ms_part else 0
            return minutes * 60 + seconds + fraction
        return minutes * 60 + int(rest)
    except (ValueError, TypeError):
        return 0


def seconds_to_str(seconds):
    """秒数 → 存储格式 'mm:ss' 或 'mm:ss.x'（1 位小数，为 0 时省略；与前端逐字符一致）
    内部先四舍五入到 1 位小数，再取 分:秒 + 十分位，避免 float 噪声（如 10.1 实为 10.100000000000001）
    """
    if seconds is None or seconds < 0:
        return '00:00'
    t = _round_tenths(seconds)
    minutes = int(t // 60)
    sec = int(t % 60)
    tenth = _round_half_up((t % 1) * 10)
    if tenth > 0:
        return f'{minutes:02d}:{sec:02d}.{tenth}'
    return f'{minutes:02d}:{sec:02d}'


def parse_any_to_items(text):
    """解析任意歌词文本为条目列表 [{time: float, text: str}, ...]，按时间升序
    双路径：
    1. 标准 LRC 方括号 [mm:ss.xx] —— 与前端 parseLrcToStandardFormat 逐字符一致：
       · 元数据行（作词/作曲/编曲/演唱/专辑/by:）与空文本行过滤
       · 一行多时间标签 → 每个时间一条（文本合并为去标签后的剩余）
       · 小数按「3 位 /1000，1~2 位 /100」解释（历史怪癖：'.5' 当 0.05 秒）
       · 四舍五入到 1 位小数，同时间去重保留首个
    2. 存储格式 mm:ss(.x) —— 无方括号路径，时间按真实小数位解析
    """
    if not text:
        return []
    items = []
    seen = set()
    for raw_line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        # ---------- 1) 标准 LRC 方括号路径 ----------
        if LRC_TAG_RE.search(line):
            times = []
            rest = line
            for tag in LRC_TAG_RE.finditer(line):
                minute = int(tag.group(1))
                second = int(tag.group(2))
                ms_str = tag.group(3)
                ms = (int(ms_str) / (1000 if len(ms_str) == 3 else 100)) if ms_str else 0
                times.append(minute * 60 + second + ms)
                rest = rest.replace(tag.group(0), '', 1)
            text_part = rest.strip()
            if not text_part or METADATA_RE.search(text_part):
                continue
            for t in times:
                t_rounded = _round_tenths(t)
                if t_rounded in seen:
                    continue
                seen.add(t_rounded)
                items.append({'time': t_rounded, 'text': text_part})
            continue

        # ---------- 2) 存储格式路径 ----------
        match = STORAGE_LINE_RE.match(line)
        if match:
            t = (int(match.group(1)) * 60 + int(match.group(2))
                 + (float('0.' + match.group(3)) if match.group(3) else 0))
            text_part = match.group(4).strip()
            if not text_part:
                continue
            t_rounded = _round_tenths(t)
            if t_rounded in seen:
                continue
            seen.add(t_rounded)
            items.append({'time': t_rounded, 'text': text_part})

    items.sort(key=lambda x: x['time'])
    return items


def items_to_storage(items):
    """条目列表 → 存储格式文本（每行 'mm:ss(.x) 歌词'，按时间升序）
    入参无序也先按 time 升序（parse_any_to_items 已排序，此处防御性再排）
    """
    if not items:
        return ''
    ordered = sorted(items, key=lambda x: x['time'])
    return '\n'.join(seconds_to_str(item['time']) + ' ' + item['text'] for item in ordered)


def normalize_to_storage(text):
    """任意歌词文本 → 规范化存储格式（与前端 parseLrcToStandardFormat 输出逐字符一致）"""
    return items_to_storage(parse_any_to_items(text))


def validate_lyric_text(lyric_text):
    """校验歌词文本合法性，返回 (is_valid: bool, error_msg: str)
    - 空 / 全空白 → 拒绝「不能为空」
    - 无法解析出任何有效歌词行（如纯文本无时间戳） → 拒绝「无效」
    - 合法 → 通过（后续再由 normalize_to_storage 规范化落库）
    """
    if not lyric_text or not lyric_text.strip():
        return False, '歌词内容不能为空'
    if not parse_any_to_items(lyric_text):
        return False, '未解析到有效的歌词行（每行应为：mm:ss 歌词 或 [mm:ss]歌词）'
    return True, ''
