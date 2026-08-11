# MusicRate\backend\utils\lyric_recognizer.py AI 歌词识别器（v0.8 P1 spike）
# faster-whisper 本地 ASR（CTranslate2），用于「整轨 mp3 → 歌词 + 时间戳」的可行性验证
# spike 阶段只被 CLI（lyric_spike.py）调用，不接 Flask 路由，避免拖慢后端启动
# 管线（README v0.8 架构设计）：
#   懒加载模型单例 → transcribe(word_timestamps=True, vad_filter=True)
#   → segment 级时间戳 1 位小数去重升序 → 按 tracks_time 边界切分到单曲
#   → 复用 lrc.py 产出整轨绝对时间存储文本（可直接落 album_lyric）
# 纯逻辑部分（clean_segment_text / segments_to_items / split_by_tracks_time / track_items_to_storage）
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

# 模型单例缓存：{model_size: WhisperModel}
_model_cache = {}


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


def segments_to_items(segments):
    """whisper segments（[{start, end, text}, ...]）→ 歌词条目 [{time, text}, ...]
    - 文本先 clean_segment_text，空 / 纯噪音跳过
    - 时间按 start 四舍五入到 1 位小数（复用 lrc._round_tenths，与全站存储格式一致）
    - 同时间去重保留首个（与 lrc 前端同构的取首规则）
    - 按 time 升序
    """
    items = []
    seen = set()
    for seg in segments:
        text = clean_segment_text(seg.get('text', ''))
        if not text:
            continue
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


def transcribe(audio_path, model_size='small', limit_secs=None, language=None, vad_filter=True):
    """转写音频文件 → (segments, info, metrics)
    - word_timestamps=True + vad_filter（README P1 管线默认 True；spike 对比实验可关）
    - limit_secs 用 clip_timestamps 限制（只转写前 N 秒，spike 首跑拿 RTF 用）
    - 返回 faster-whisper segment 列表（含 start/end/text）与模型 info（语言 / 时长）
    """
    model = get_model(model_size)
    kwargs = dict(word_timestamps=True, vad_filter=vad_filter)
    if language:
        kwargs['language'] = language
    if limit_secs:
        kwargs['clip_timestamps'] = (0.0, float(limit_secs))

    t0 = time.time()
    segments_iter, info = model.transcribe(audio_path, **kwargs)
    segments = [{'start': s.start, 'end': s.end, 'text': s.text} for s in segments_iter]
    elapsed = time.time() - t0

    audio_seconds = limit_secs if limit_secs else (getattr(info, 'duration', None) or 0)
    rtf = (elapsed / audio_seconds) if audio_seconds else 0.0
    return segments, info, {'elapsed': elapsed, 'audio_seconds': audio_seconds, 'rtf': rtf}
