# MusicRate\backend\utils\deepseek_correct.py DeepSeek 歌词校正（v0.8.1 P2）
# 作用：对 faster-whisper 识别的歌词草稿做文字校正——识别产物是「草稿 + 时间戳」，
#       同音错字/诗意句需 DeepSeek 修正；whisper 时间戳为锚，只改文字不改时间、不增删行。
# 决策（README v0.8.1）：
#   - key 用服务器端 config.DEEPSEEK_API_KEY（管理员识别专属，与个人用户 AI key 分离两套）
#   - 若行数变化（模型未遵守约束）→ difflib.SequenceMatcher 对齐回锚定时间戳
#   - 校正失败（网络/解析异常/无 key）→ 回退 whisper 原稿，不阻断识别管线
# 纯逻辑部分（build_correct_prompt / parse_corrected_lines / align_back_timestamps）零网络可单测；
# _call_chat（真实 API 请求）属 realdata，由 lyric_ai.py 后台任务调用。
import difflib

import requests

from backend.utils.lrc import STORAGE_LINE_RE, items_to_storage, parse_any_to_items, seconds_to_str

# DeepSeek OpenAI 兼容接口（官方）
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
DEEPSEEK_MODEL = 'deepseek-chat'

# 校正 prompt 模板：逐行锚定时间戳，强约束「只改文字、不改时间戳、不增删行」
_CORRECT_PROMPT_TPL = """你是专业的歌词校对专家。下面是 AI 语音识别产出的歌词草稿，每行格式为「时间戳 歌词文本」。

请逐行校对歌词文本，要求：
1. 只修正歌词文字（同音错字、断句、语义不通），保留歌词原意与风格
2. 必须保留每行的时间戳原样不变（不改动数字，不增删行）
3. 保持行数与顺序与原文完全一致，逐行对应输出
4. 仅输出校对后的歌词（每行「时间戳 歌词文本」），不要输出任何解释、引号或额外内容

歌词草稿：
{lyric_text}
"""


def build_correct_prompt(lyric_text):
    """构造校正 prompt（纯函数，可单测）
    - lyric_text 为整轨绝对时间存储格式（每行 mm:ss(.x) 文本）
    """
    return _CORRECT_PROMPT_TPL.format(lyric_text=lyric_text.strip())


def parse_corrected_lines(raw):
    """解析 DeepSeek 返回为校正文本行列表（纯文本，剥离时间戳前缀）
    - 容忍 ``` 代码块包裹、行尾空白、行首时间戳
    - 若行带时间戳（模型遵守格式）→ 只取文本；无时间戳 → 整行作为文本（交由对齐处理）
    - 返回 [text, ...]；空输入返回 []
    """
    if not raw:
        return []
    lines = []
    for line in raw.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        line = line.strip()
        if not line or line.startswith('```'):
            continue
        m = STORAGE_LINE_RE.match(line)
        if m:
            lines.append(m.group(4).strip())
        else:
            lines.append(line)
    return lines


def align_back_timestamps(anchor_lines, corrected_lines):
    """把校正后文本行对齐回 anchor 时间戳（difflib 保时间戳核心，纯函数可单测）
    - anchor_lines: [{time: float, text: str}, ...]（whisper 原文，时间戳为锚）
    - corrected_lines: [text, ...]（DeepSeek 校正后纯文本行，可能增删/乱序行）
    - 用 difflib.SequenceMatcher.get_opcodes 对齐：
      · equal    —— 逐行对应，anchor 时间戳
      · replace  —— 校正行映射回 anchor 行（行数不等则按最大行数对齐，缺失 anchor 行沿用最近前一行时间戳）
      · delete   —— 校正后删除的行丢弃
      · insert   —— 校正新增行无 anchor 时间戳，沿用前一行时间戳（开头则用第一行时间戳）
    - 返回 [{time: float, text: str}, ...]，可直接 items_to_storage
    """
    if not corrected_lines:
        return []
    anchor_texts = [a['text'] for a in anchor_lines]
    sm = difflib.SequenceMatcher(None, anchor_texts, corrected_lines)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                out.append({'time': anchor_lines[i1 + k]['time'], 'text': corrected_lines[j1 + k]})
        elif tag == 'replace':
            n_anchor = i2 - i1
            n_corr = j2 - j1
            for k in range(n_corr):
                a_idx = i1 + min(k, n_anchor - 1)  # 校正行多于 anchor 行 → 最后一行沿用最后一个 anchor 时间戳
                out.append({'time': anchor_lines[a_idx]['time'], 'text': corrected_lines[j1 + k]})
        elif tag == 'delete':
            pass  # 校正删除的行丢弃（时间戳不再出现）
        elif tag == 'insert':
            # 新增行：沿用前一行 anchor 时间戳；开头则用第一行 anchor 时间戳
            if i1 > 0:
                t = anchor_lines[i1 - 1]['time']
            elif anchor_lines:
                t = anchor_lines[0]['time']
            else:
                t = 0.0
            for k in range(j2 - j1):
                out.append({'time': t, 'text': corrected_lines[j1 + k]})
    return out


def _call_chat(api_key, prompt, timeout=60):
    """调用 DeepSeek chat/completions（OpenAI 兼容），返回助手消息文本
    - 属 realdata：真实网络请求，仅后台识别任务调用
    """
    resp = requests.post(
        f'{DEEPSEEK_BASE_URL}/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        json={
            'model': DEEPSEEK_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.2,  # 低温度：校正任务确定性优先
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


def correct_lyric(lyric_text, api_key=None, timeout=60):
    """DeepSeek 校正整轨歌词草稿（总入口，供 lyric_ai 后台任务调用）
    - api_key 为空 → 未配置跳过校正，返回 (原稿, {corrected: False, reason: 未配置})
    - 调用失败（网络/HTTP/解析/无可校正行）→ 回退 whisper 原稿（README：校正失败回退原稿）
    - 成功 → (校正文本, {corrected: True, anchor_lines, corrected_lines, lyric_lines})
    """
    if not api_key:
        return lyric_text, {'corrected': False, 'reason': '未配置 DEEPSEEK_API_KEY，跳过校正'}

    items = parse_any_to_items(lyric_text)
    if not items:
        return lyric_text, {'corrected': False, 'reason': '无可校正歌词行'}

    # anchor 时间戳：保留原始时间戳字符串与浮点值（对齐后 items_to_storage 用 float）
    anchor_lines = [{'time': it['time'], 'time_str': seconds_to_str(it['time']), 'text': it['text']} for it in items]

    try:
        raw = _call_chat(api_key, build_correct_prompt(lyric_text), timeout=timeout)
    except Exception as e:
        return lyric_text, {'corrected': False, 'reason': f'DeepSeek 调用失败：{e}'}

    corrected_lines = parse_corrected_lines(raw)
    if not corrected_lines:
        return lyric_text, {'corrected': False, 'reason': 'DeepSeek 返回内容无法解析'}

    aligned = align_back_timestamps(anchor_lines, corrected_lines)
    corrected_text = items_to_storage(aligned)

    # 校正后为空（理论不会：align 至少保留 equal/replace）→ 防御回退
    if not corrected_text:
        return lyric_text, {'corrected': False, 'reason': '校正结果为空，回退原稿'}

    return corrected_text, {
        'corrected': True,
        'anchor_lines': len(anchor_lines),
        'corrected_lines': len(corrected_lines),
        'lyric_lines': len(corrected_text.splitlines()),
    }
