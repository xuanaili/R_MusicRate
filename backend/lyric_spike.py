# MusicRate\backend\lyric_spike.py v0.8 P1 spike CLI：faster-whisper 歌词识别可行性验证
# 用途：对已有整轨 mp3 的专辑做 AI 歌词识别（含时间戳），按 tracks_time 切分到单曲，产出评估报告
#       （文本准确度 / 时间戳对齐 / CPU 耗时 RTF），供拍板正式管线是否落地。
# 用法：
#   portable\python\python.exe backend/lyric_spike.py --pool-id 31 [--user-id 1] [--model small] \
#       [--limit-secs 300] [--language zh] [--out full.lrc] [--per-track-dir dir] [--report-out report.md]
# 说明：spike 阶段纯 CLI，不接 Flask 路由；模型懒加载，首次运行需下载（走 HF 镜像）。
import argparse
import difflib
import json
import os
import sys
import time

# 便携 Python cwd 不在 sys.path：脚本目录上一级 = 项目根，手动加入（与 run.py 一致）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 终端 UTF-8 输出，防 emoji/中文 GBK 报错（与 run.py 一致）
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pymysql
from backend.config import MYSQL_CONFIG, AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER
from backend.utils.lyric_recognizer import (
    build_full_storage_text,
    segments_to_items,
    split_by_tracks_time,
    track_items_to_storage,
    transcribe,
)
from backend.utils.lrc import parse_any_to_items, seconds_to_str


def db_connect():
    """MySQL 连接（DictCursor）"""
    return pymysql.connect(**MYSQL_CONFIG)


def load_pool_album(pool_id):
    """读 album_pool 单行：专辑名 / 歌手 / mp3_url / mp3_duration"""
    db = db_connect()
    try:
        cur = db.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            'SELECT id, album_name, singer, mp3_url, mp3_duration FROM album_pool WHERE id = %s',
            (pool_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        db.close()


def resolve_audio_path(mp3_url):
    """mp3_url（http://localhost:5000/tracks/<filename>）→ 磁盘绝对路径
    backend/data/album_track/<filename>（与 audio_resource.py 的存储/读取一致）
    """
    if not mp3_url:
        return None
    filename = mp3_url.split('/')[-1]
    return os.path.join(AUDIO_UPLOAD_FOLDER, filename)


def load_user_album(user_id, pool_id):
    """从 albums_{user_id} 读某公共池专辑的用户副本：tracks / tracks_time
    （README：P1 spike 从用户专辑表读 tracks_time；无副本则返回空，不做切分）
    """
    db = db_connect()
    try:
        cur = db.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            f'SELECT album_name, tracks, tracks_time FROM albums_{int(user_id)} WHERE source_pool_id = %s LIMIT 1',
            (pool_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        tracks = json.loads(row['tracks']) if row['tracks'] else []
        tracks_time = json.loads(row['tracks_time']) if row['tracks_time'] else []
        return {'tracks': tracks, 'tracks_time': tracks_time}
    finally:
        db.close()


def load_reference_lyric(pool_id):
    """读 album_lyric 现成歌词作对照（有则算文本相似度 / 时间戳对齐；无则报告注明人工目测）"""
    db = db_connect()
    try:
        cur = db.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            'SELECT lyric_text FROM album_lyric WHERE album_pool_id = %s ORDER BY update_time DESC LIMIT 1',
            (pool_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row['lyric_text'] if row else None
    finally:
        db.close()


def compute_ref_metrics(rec_items, ref_text):
    """识别条目 vs 现成歌词（ref_text 任意格式）→ (文本相似度, 时间戳对齐统计)
    - 时间戳对齐：每条识别条目的时间找参考歌词中时间最近的一条，落在 ±3s 且文本相似>0.3 记为对齐
    - 文本相似度：difflib SequenceMatcher 按行取近邻最高 ratio 的平均
    """
    if not ref_text:
        return None
    ref_items = [it for it in parse_any_to_items(ref_text) if it['text']]
    if not ref_items:
        return None
    text_ratios = []
    aligned = 0
    offsets = []
    for it in rec_items:
        nearest = min(ref_items, key=lambda r: abs(r['time'] - it['time']))
        ratio = difflib.SequenceMatcher(None, it['text'], nearest['text']).ratio()
        text_ratios.append(ratio)
        offset = it['time'] - nearest['time']
        offsets.append(abs(offset))
        if abs(offset) <= 3.0 and ratio > 0.3:
            aligned += 1
    total = len(rec_items) or 1
    mean_text = sum(text_ratios) / total
    offsets_sorted = sorted(offsets)
    median_offset = offsets_sorted[len(offsets_sorted) // 2] if offsets_sorted else 0
    return {
        'ref_lines': len(ref_items),
        'rec_lines': len(rec_items),
        'text_similarity': round(mean_text * 100, 1),
        'align_rate': round(aligned / total * 100, 1),
        'median_offset': round(median_offset, 1),
    }


def build_report(pool, audio_path, user_album, seg_count, items, groups, metrics, info_meta):
    """组装 markdown 评估报告（文本准确度 / 时间戳对齐 / RTF）"""
    lines = []
    add = lines.append
    add(f'# AI 歌词识别 spike 报告（{pool["album_name"]} · {pool["singer"]}）')
    add('')
    add('| 项 | 值 |')
    add('|----|----|')
    add(f'| album_pool_id | {pool["id"]} |')
    add(f'| 音频 | `{audio_path}` |')
    add(f'| 模型 | {info_meta["model"]} (CPU int8) |')
    add(f'| VAD 过滤 | {"开" if info_meta["vad_filter"] else "关（对比实验）"} |')
    add(f'| 语言 | {info_meta["language"] or "自动检测"} |')
    add(f'| 音频时长 | {info_meta["duration"]:.1f}s |')
    add(f'| 实际转写 | {info_meta["audio_seconds"]:.1f}s{"（limit-secs 截断）" if info_meta.get("truncated") else ""} |')
    add(f'| 转写耗时 | {metrics["elapsed"]:.1f}s |')
    add(f'| **RTF** | **{metrics["rtf"]:.2f}**（1 秒音频需 {metrics["rtf"]:.2f} 秒 CPU） |')
    add(f'| segment 数 | {seg_count} |')
    add(f'| 清洗后条目数 | {len(items)} |')
    add('')
    if metrics.get('ref'):
        r = metrics['ref']
        add('### 对照评估（对照现成歌词）')
        add('')
        add(f'- 现成歌词行数：{r["ref_lines"]}，识别行数：{r["rec_lines"]}')
        add(f'- **文本相似度**（difflib 近邻平均）：{r["text_similarity"]}%')
        add(f'- **时间戳对齐率**（±3s 且文本相似>0.3）：{r["align_rate"]}%')
        add(f'- **时间偏移中位数**：±{r["median_offset"]}s')
        add('')
    else:
        add('> ⚠️ 无现成歌词对照，**文本准确度 / 时间戳对齐需人工目测**下方样例。')
        add('')
    add('### 单曲切分分布')
    add('')
    if groups:
        for idx in sorted(groups):
            name = (user_album['tracks'][idx] if user_album and idx < len(user_album['tracks']) else f'未知曲目{idx+1}')
            add(f'- `[{idx+1}]` {name}：{len(groups[idx])} 条')
    else:
        add('- 无 tracks_time，未切分（全部归第 0 组）')
    add('')
    add('### 单曲样例（每首前 2 条）')
    add('')
    for idx in sorted(groups):
        name = (user_album['tracks'][idx] if user_album and idx < len(user_album['tracks']) else f'未知曲目{idx+1}')
        st = user_album['tracks_time'][idx] if user_album and idx < len(user_album['tracks_time']) else 0
        add(f'**{name}**（起点 {seconds_to_str(st)}，共 {len(groups[idx])} 条）')
        for it in groups[idx][:2]:
            rel = max(it['time'] - st, 0)
            add(f'- `{seconds_to_str(rel)}` {it["text"]}')
        add('')
    add('### 整轨文本样例（前 15 行，绝对时间存储格式）')
    add('')
    for it in items[:15]:
        add(f'- `{seconds_to_str(it["time"])}` {it["text"]}')
    return '\n'.join(lines)


def run_spike(pool_id, user_id, model, limit_secs, language, vad_filter, out_path, per_track_dir, report_out):
    """执行一次 spike：加载 → 转写 → 切分 → 报告"""
    pool = load_pool_album(pool_id)
    if not pool:
        print(f'❌ album_pool 无 id={pool_id}')
        return 1
    audio_path = resolve_audio_path(pool['mp3_url'])
    if not audio_path or not os.path.exists(audio_path):
        print(f'❌ 音频文件不存在：{audio_path}')
        return 1
    user_album = load_user_album(user_id, pool_id)

    print(f'📀 {pool["album_name"]}（{pool["singer"]}） id={pool_id}')
    print(f'🎧 {audio_path}')

    t0 = time.time()
    segments, info, metrics = transcribe(
        audio_path, model_size=model, limit_secs=limit_secs, language=language, vad_filter=vad_filter,
    )
    items = segments_to_items(segments)
    groups = split_by_tracks_time(items, user_album['tracks_time'] if user_album else [])
    ref_text = load_reference_lyric(pool_id)
    ref_metrics = compute_ref_metrics(items, ref_text) if ref_text else None
    metrics['ref'] = ref_metrics
    info_meta = {
        'model': model,
        'language': getattr(info, 'language', None),
        'vad_filter': vad_filter,
        'duration': getattr(info, 'duration', 0) or pool.get('mp3_duration') or 0,
        'audio_seconds': metrics['audio_seconds'],
        'truncated': bool(limit_secs and limit_secs < (getattr(info, 'duration', 0) or 0)),
    }

    print(f'⏱️  转写耗时 {metrics["elapsed"]:.1f}s，RTF = {metrics["rtf"]:.2f}（{info_meta["audio_seconds"]:.1f}s 音频）')
    print(f'📝 segment {len(segments)} → 条目 {len(items)}，切分 {len(groups)} 组')

    # 写整轨存储文本（可直接落 album_lyric.lyric_text）
    if out_path:
        full_text = build_full_storage_text(items)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(full_text + '\n')
        print(f'💾 整轨存储文本 → {out_path}（{len(items)} 行）')

    # 写各单曲相对时间文本（目录）
    if per_track_dir:
        os.makedirs(per_track_dir, exist_ok=True)
        for idx in sorted(groups):
            name = (user_album['tracks'][idx] if user_album and idx < len(user_album['tracks']) else f'track_{idx+1}')
            st = user_album['tracks_time'][idx] if user_album and idx < len(user_album['tracks_time']) else 0
            content = track_items_to_storage(groups[idx], st)
            fname = os.path.join(per_track_dir, f'{idx+1:02d}_{name}.lrc')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(content + '\n' if content else '')
        print(f'💾 单曲 LRC → {per_track_dir}/（{len(groups)} 首）')

    report = build_report(pool, audio_path, user_album, len(segments), items, groups, metrics, info_meta)
    print()
    print(report)

    if report_out:
        with open(report_out, 'w', encoding='utf-8') as f:
            f.write(report + '\n')
        print(f'📄 报告 → {report_out}')
    return 0


def main():
    parser = argparse.ArgumentParser(description='faster-whisper 歌词识别 spike')
    parser.add_argument('--pool-id', type=int, required=True, help='album_pool 专辑 id')
    parser.add_argument('--user-id', type=int, default=1, help='读 tracks_time 的用户（默认 admin=1）')
    parser.add_argument('--model', default='small', help='whisper 模型：tiny/base/small/medium/large-v3（默认 small）')
    parser.add_argument('--limit-secs', type=float, default=None, help='只转写前 N 秒（先拿 RTF 再整轨）')
    parser.add_argument('--language', default=None, help='强制语言，如 zh / en（默认自动检测）')
    parser.add_argument('--no-vad', action='store_true', help='关闭 VAD 过滤（音乐场景对比实验用，默认 VAD 开）')
    parser.add_argument('--out', default=None, help='整轨存储文本输出文件路径')
    parser.add_argument('--per-track-dir', default=None, help='输出目录：各单曲相对时间 LRC')
    parser.add_argument('--report-out', default=None, help='评估报告 markdown 输出路径')
    args = parser.parse_args()
    sys.exit(run_spike(args.pool_id, args.user_id, args.model, args.limit_secs,
                       args.language, not args.no_vad, args.out, args.per_track_dir, args.report_out))


if __name__ == '__main__':
    main()
