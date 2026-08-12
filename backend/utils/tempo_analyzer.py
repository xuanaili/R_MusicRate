# MusicRate\backend\utils\tempo_analyzer.py BPM 节奏分析纯函数（v0.8.1 P4）
# 对整轨 mp3 做 tempo 分析，按 tracks_time 边界切分得每曲 BPM + 整专节奏结构，供 AI 助手上下文使用。
# 设计（README v0.8.1）：
#   - extract_tempo / get_track_boundaries / build_tempo_result 为纯函数，可单测
#   - analyze_tempo 加载整轨一次（mono 22050，~6ms/s），按边界切片逐曲测拍（每段 <0.5s），总耗时 ≈ 加载 + 各段测拍之和
#   - 不调用 librosa.get_duration（整轨解码取时长很慢 ~15s/30min，改由 album_pool.mp3_duration 或 len(y)/sr 提供）
#   - 采样率 22050 单声道节拍检测够用且省内存（44min 峰值 ~230MB）；无 librosa 时降级 aubio 见 README（本实现走 librosa）
import math

import numpy as np
import librosa

# 整轨加载采样率（mono 单声道，节拍检测够用）
SAMPLE_RATE = 22050
# 测拍有效段最小秒数（过短拍子数不足，测拍不可靠 → 记为 0）
MIN_TEMPO_SEGMENT_SECS = 5.0


def _round_half_up(x):
    """复制前端 Math.round 语义（.5 进位；Python round 是银行家舍入，不能直接用，见 v0.8 教训）"""
    return math.floor(x + 0.5)


def _round_tenths(x):
    """x 四舍五入到 1 位小数（半进位）"""
    return _round_half_up(x * 10) / 10.0


def extract_tempo(y, sr=SAMPLE_RATE):
    """纯函数：对一段音频 y（1D numpy 单声道数组）测 BPM
    - 空 / 过短（< MIN_TEMPO_SEGMENT_SECS）→ 0.0（无法测拍）
    - librosa.beat.beat_track 全局节拍估计；返回 1 位小数；非有限/非正 → 0.0
    """
    if y is None or len(y) == 0:
        return 0.0
    if len(y) / sr < MIN_TEMPO_SEGMENT_SECS:
        return 0.0
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # librosa 0.11 tempo 可能是标量或 np 数组，统一取首值
    tempo_val = float(np.atleast_1d(tempo)[0])
    if not np.isfinite(tempo_val) or tempo_val <= 0:
        return 0.0
    return _round_tenths(tempo_val)


def get_track_boundaries(tracks_time, total_duration):
    """纯函数：按 tracks_time 边界得到每曲的绝对时间切片 [(start, end), ...]
    - tracks_time[i] 是第 i 首的起始秒（与 lyric.split_by_tracks_time 口径一致）；
      第一首恒从 0 开始（无 0 起点则补 0）；末首到 total_duration
    - tracks_time 为空 / 全空 → 整轨一个切片 (0, total_duration)
    - 过滤 None / 重复 / 乱序（排序去重）/ 越界（>= total）边界
    """
    if total_duration is None or total_duration <= 0:
        return []
    boundaries = sorted({
        float(b) for b in (tracks_time or []) if b is not None and float(b) > 0 and float(b) < total_duration
    })
    if not boundaries:
        return [(0.0, float(total_duration))]
    starts = [0.0] + boundaries
    segments = []
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else float(total_duration)
        if end > st:
            segments.append((st, end))
    return segments


def build_tempo_result(track_tempos, track_durations):
    """纯函数：聚合每曲 BPM 为整专节奏结构
    - 0 表示该段无法测拍（过短/静音），聚合 avg/min/max 只计有效值
    - avg_bpm 保留 1 位小数
    """
    valid = [b for b in track_tempos if b > 0]
    return {
        'track_tempos': track_tempos,
        'avg_bpm': _round_tenths(sum(valid) / len(valid)) if valid else 0.0,
        'min_bpm': min(valid) if valid else 0.0,
        'max_bpm': max(valid) if valid else 0.0,
        'track_durations': track_durations,
    }


def analyze_tempo(audio_path, tracks_time=None):
    """对整轨 mp3 做节奏分析：加载一次 → 按边界切片 → 逐曲测拍 → 聚合
    返回 build_tempo_result 的字典（track_tempos / avg_bpm / min_bpm / max_bpm / track_durations）
    - tracks_time 为空 → 整轨作为一个切片（只给整专 BPM，不给单曲）
    - 文件不存在 / 加载失败抛异常，由调用方（异步任务）标记失败
    """
    y, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    total_duration = len(y) / sr
    segments = get_track_boundaries(tracks_time, total_duration)
    track_tempos = []
    track_durations = []
    for st, end in segments:
        start_sample = int(st * sr)
        end_sample = min(int(end * sr), len(y))
        seg = y[start_sample:end_sample] if end_sample > start_sample else np.array([])
        track_tempos.append(extract_tempo(seg, sr))
        track_durations.append(round(end - st, 1))
    return build_tempo_result(track_tempos, track_durations)
