# MusicRate\backend\utils\lyric_recognizer.py AI 歌词识别器（v0.8 P1 spike → v0.8.1 P0 正式管线识别器升级）
# faster-whisper 本地 ASR（CTranslate2），用于「整轨 mp3 → 歌词 + 时间戳」的正式管线
# 管线（README v0.8.1 架构设计）：
#   懒加载模型单例 → transcribe(word_timestamps=True, vad_filter=False 音乐场景必须关)
#   → 幻觉过滤（no_speech_prob 阈值丢弃 + 噪音模式/器乐标签滤除）→ OpenCC 繁转简
#   → segment 级时间戳 1 位小数去重升序 → 按 tracks_time 边界切分到单曲
#   → 复用 lrc.py 产出整轨绝对时间存储文本（可直接落 album_lyric）
# 纯逻辑部分（clean_segment_text / is_hallucination / filter_segments / to_simplified
#   / segments_to_items / split_by_tracks_time / track_items_to_storage）
# 零依赖可单测（test_lyric_recognizer.py）；模型加载 / 转写属 realdata，由 CLI 实测
import os
import re
import time

from backend.utils.lrc import _round_tenths, items_to_storage

# 国内直连 HuggingFace 不可达 → 走镜像（模型下载时生效；Downloading... 也走 HF_ENDPOINT）
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
# 新版 huggingface-hub 默认启用 hf-xet（Xet 后端），hf-mirror 不支持会 401 → 禁用回退经典 HTTP
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')

# 模型下载根目录：portable/models/faster-whisper（README 决策固定，避免散落在用户目录）
MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'portable', 'models', 'faster-whisper',
)

# whisper 噪音 token 清洗正则（方括号标签 / 音符符）
_BRACKET_NOISE_RE = re.compile(r'\[[^\]]*\]')
_MUSIC_NOTES_RE = re.compile(r'[♪♫🎵🎶]')
_SPACES_RE = re.compile(r'\s+')

# 幻觉噪音模式（spike 报告确认 + README 难点对策）：制作信息 / 字幕 / 器乐名
# - 制作信息：「詞曲 李宗盛」「作詞 方文山」「編曲」等
# - 字幕：「字幕by索兰娅」「字幕：...」等
# - 器乐标签：spike 验证的「Zither Harp」类纯器乐幻觉 + 常见乐器英文名
_HALLUCINATION_RE = re.compile(
    r'(詞曲|词曲|作詞|作词|作曲|編曲|编曲|監製|监制|字幕by|字幕|製作者|制作人|Zither|Harp|Guitar|Piano|Violin|Viola|Cello|Flute|Saxophone|Trumpet|Trombone|Bass|Drums|Percussion|Tambourine|Gong|instrumental|Instrumental)'
)

# 模型单例缓存：{model_size: WhisperModel}
_model_cache = {}

# OpenCC 繁→简单例：懒加载（None 未初始化 / False 初始化失败回退 / 实例可用）
_simplifier = None


def is_hallucination(text):
    """判断文本是否为幻觉噪音（制作信息 / 字幕 / 器乐名）→ 丢弃该 segment
    - 入参应为 clean_segment_text 之后的文本（方括号噪音已去除）
    - 空 / 全空白 → True（无可唱内容，当作幻觉）
    - 命中 _HALLUCINATION_RE（词曲/作词/字幕by/器乐英文名等）→ True
    """
    if not text or not text.strip():
        return True
    return bool(_HALLUCINATION_RE.search(text))


def filter_segments(segments, no_speech_threshold=0.6):
    """幻觉过滤：丢弃 no_speech_prob 超过阈值 + 噪音模式（制作信息/字幕/器乐名）的 segment
    - no_speech_prob > no_speech_threshold（默认 0.6，README 拍板）→ 器乐/静音段幻觉，丢弃
    - 缺失 / None 的 no_speech_prob 视为 0（不过滤，兼容旧测试与旧转写数据）
    - 文本经 clean_segment_text 后为空（[Music]/[BLANK_AUDIO]/空白）或 is_hallucination → 丢弃
    - 返回过滤后的 segment 列表（保留原 segment 结构，时间/文本字段不变）
    """
    out = []
    for seg in segments:
        nsp = seg.get('no_speech_prob')
        if nsp is not None and nsp > no_speech_threshold:
            continue
        text = clean_segment_text(seg.get('text', ''))
        if not text:
            continue
        if is_hallucination(text):
            continue
        out.append(seg)
    return out


def to_simplified(text):
    """繁体 → 简体（OpenCC t2s，全站存储/显示统一简体，spike 确认 whisper 中文输出为繁体）
    - 懒加载单例，仅首次调用初始化；opencc 缺失 / 初始化失败回退原文本（不阻断识别管线）
    - 对已为简体的文本无副作用（原样返回）
    """
    if not text:
        return text
    global _simplifier
    if _simplifier is None:
        try:
            import opencc
            _simplifier = opencc.OpenCC('t2s')
        except Exception:
            _simplifier = False
    if not _simplifier:
        return text
    try:
        return _simplifier.convert(text)
    except Exception:
        return text


def clean_segment_text(text):
    """清洗 whisper segment 文本：去掉 [Music]/[BLANK_AUDIO] 等方括号噪音、音符符，归一空白
    - 清洗后为空串的 segment 视为纯噪音（转写时跳过，不入歌词）
    """
    if not text:
        return ''
    t = _BRACKET_NOISE_RE.sub(' ', text)
    t = _MUSIC_NOTES_RE.sub(' ', t)
    t = _SPACES_RE.sub(' ', t).strip()
    return t


def get_model(model_size='small', device='cpu', compute_type='int8'):
    """懒加载 faster-whisper 模型单例：首次调用才下载 / 加载，之后复用
    - 模型下载到 MODELS_DIR（download_root 固定，配合 HF_ENDPOINT 镜像）
    - CPU + int8：本机无 GPU，int8 量化显著提速且中文识别损失可接受（spike 定位「草稿」非成品）
    """
    if model_size not in _model_cache:
        from faster_whisper import WhisperModel
        os.makedirs(MODELS_DIR, exist_ok=True)
        _model_cache[model_size] = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=MODELS_DIR,
        )
    return _model_cache[model_size]


def segments_to_items(segments, no_speech_threshold=0.6):
    """whisper segments（[{start, end, text, no_speech_prob?}, ...]）→ 歌词条目 [{time, text}, ...]
    - 先 filter_segments 幻觉过滤（no_speech_prob 阈值 + 噪音模式/器乐标签，缺失字段视为 0）
    - 文本 clean_segment_text → 空 / 纯噪音跳过 → OpenCC 繁转简（全站统一简体）
    - 时间按 start 四舍五入到 1 位小数（复用 lrc._round_tenths，与全站存储格式一致）
    - 同时间去重保留首个（与 lrc 前端同构的取首规则）；按 time 升序
    """
    items = []
    seen = set()
    for seg in filter_segments(segments, no_speech_threshold=no_speech_threshold):
        text = clean_segment_text(seg.get('text', ''))
        if not text:
            continue
        text = to_simplified(text)
        t = _round_tenths(seg['start'])
        if t in seen:
            continue
        seen.add(t)
        items.append({'time': t, 'text': text})
    items.sort(key=lambda x: x['time'])
    return items


def split_by_tracks_time(items, tracks_time):
    """按单曲边界把整轨绝对时间条目分到各单曲（与前端 initTrackLyricsMap 口径一致）
    tracks_time[i] 是第 i 首的起始秒；条目归属第 i 首当 tracks_time[i] <= t < tracks_time[i+1]
    - 恰在边界 → 归属该边界开头的单曲（如 254 归属第 1 首）
    - 最后一首到音频末尾（Infinity）
    - tracks_time 为空 / 全空 → 全部归第 0 组（不做切分）
    返回 {track_index: [items]}（只有非空组）
    """
    boundaries = [b for b in (tracks_time or []) if b is not None]
    if not boundaries:
        return {0: list(items)}
    groups = {}
    for it in items:
        t = it['time']
        idx = 0
        for i, st in enumerate(boundaries):
            if t < st:
                idx = i - 1
                break
            idx = i
        if idx < 0:
            idx = 0
        groups.setdefault(idx, []).append(it)
    return groups


def track_items_to_storage(items, track_start):
    """单曲条目 → 相对时间存储文本（每行 'mm:ss(.x) 歌词'，减 track_start）
    相对时间同样四舍五入到 1 位小数 + 去重保留首个，再复用 lrc.items_to_storage 格式化
    """
    if not items:
        return ''
    rel = []
    seen = set()
    for it in sorted(items, key=lambda x: x['time']):
        t = _round_tenths(it['time'] - track_start)
        if t in seen:
            continue
        seen.add(t)
        rel.append({'time': t, 'text': it['text']})
    return items_to_storage(rel)


def build_full_storage_text(items):
    """整轨绝对时间存储文本（不切分，供落 album_lyric.lyric_text）"""
    return items_to_storage(items)


def transcribe(audio_path, model_size='small', limit_secs=None, language=None, vad_filter=False,
               progress_callback=None):
    """转写音频文件 → (segments, info, metrics)
    - word_timestamps=True + vad_filter 默认 False（v0.8.1 P0 拍板：音乐场景 VAD 会整首丢失曲目）
    - word_timestamps=True 时 segment 带 no_speech_prob（幻觉过滤的数据源，保留到返回 dict）
    - limit_secs 用 clip_timestamps 限制（只转写前 N 秒，spike 首跑拿 RTF 用）
    - progress_callback：可选回调，每产出一个 segment 调用 progress_callback(ratio)（0.0~1.0），
      ratio = 已转写音频比例（segment.end / 总时长 估算；无总时长信息则不回调），前端进度条用
    - 返回 faster-whisper segment 列表（含 start/end/text/no_speech_prob）与模型 info（语言 / 时长）
    """
    model = get_model(model_size)
    kwargs = dict(word_timestamps=True, vad_filter=vad_filter)
    if language:
        kwargs['language'] = language
    if limit_secs:
        kwargs['clip_timestamps'] = (0.0, float(limit_secs))

    t0 = time.time()
    segments_iter, info = model.transcribe(audio_path, **kwargs)
    audio_seconds = limit_secs if limit_secs else (getattr(info, 'duration', None) or 0)
    segments = []
    for s in segments_iter:
        segments.append({
            'start': s.start,
            'end': s.end,
            'text': s.text,
            'no_speech_prob': getattr(s, 'no_speech_prob', 0.0) or 0.0,
        })
        if progress_callback and audio_seconds:
            progress_callback(min(1.0, (s.end or 0.0) / audio_seconds))
    elapsed = time.time() - t0

    rtf = (elapsed / audio_seconds) if audio_seconds else 0.0
    return segments, info, {'elapsed': elapsed, 'audio_seconds': audio_seconds, 'rtf': rtf}
