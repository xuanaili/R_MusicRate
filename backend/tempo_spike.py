# MusicRate\backend\tempo_spike.py v0.8.1 P4 spike CLI：librosa BPM 节奏分析可行性验证
# 用途：对已有整轨 mp3 的池专辑做 BPM 节奏分析，按 tracks_time 切分得每曲 BPM + 整专节奏结构，
#       产出评估报告（整轨耗时 / 每曲 BPM / 与音乐常识比对），供拍板正式管线（album_tempo 缓存 + 异步任务）。
# 用法：
#   portable\python\python.exe backend/tempo_spike.py --pool-id 31 [--tracks-time "[0,254,334]"] [--report-out report.md]
# 说明：spike 阶段纯 CLI，不接 Flask 路由；只读 album_pool，不写库（正式管线由异步任务缓存 album_tempo）。
import argparse
import json
import os
import sys
import time

# 便携 Python cwd 不在 sys.path：脚本目录上一级 = 项目根，手动加入（与 run.py / lyric_spike.py 一致）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 终端 UTF-8 输出，防 emoji/中文 GBK 报错（与 run.py 一致）
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pymysql
from backend.config import MYSQL_CONFIG, AUDIO_UPLOAD_FOLDER
from backend.utils.json import safe_json_loads
from backend.utils.tempo_analyzer import analyze_tempo, get_track_boundaries, SAMPLE_RATE


def db_connect():
    """MySQL 连接（DictCursor）"""
    return pymysql.connect(**MYSQL_CONFIG)


def load_pool_album(pool_id):
    """读 album_pool 单行：专辑名 / 歌手 / mp3_url / mp3_duration / tracks_time"""
    db = db_connect()
    try:
        cur = db.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            'SELECT id, album_name, singer, mp3_url, mp3_duration, tracks_time FROM album_pool WHERE id = %s',
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


def seconds_to_mmss(secs):
    """秒 → mm:ss（报告展示用）"""
    secs = int(secs)
    return f'{secs // 60:02d}:{secs % 60:02d}'


def build_report(pool, audio_path, tracks_time, elapsed, result):
    """组装 markdown 评估报告（整轨耗时 / 每曲 BPM / 结构）"""
    lines = []
    add = lines.append
    add(f'# BPM 节奏分析 spike 报告（{pool["album_name"]} · {pool["singer"]}）')
    add('')
    add('| 项 | 值 |')
    add('|----|----|')
    add(f'| album_pool_id | {pool["id"]} |')
    add(f'| 音频 | `{audio_path}` |')
    add(f'| 采样率 | {SAMPLE_RATE} Hz（mono，节拍检测够用） |')
    add(f'| 分析耗时 | {elapsed:.1f}s |')
    add(f'| 切分段数 | {len(result["track_tempos"])} |')
    add(f'| **整专平均 BPM** | **{result["avg_bpm"]}** |')
    add(f'| BPM 范围 | {result["min_bpm"]} – {result["max_bpm"]} |')
    add('')
    add('### 每曲 BPM（按 tracks_time 切分）')
    add('')
    add('| 段 | 时长 | BPM |')
    add('|----|------|-----|')
    for i, (bpm, dur) in enumerate(zip(result['track_tempos'], result['track_durations'])):
        add(f'| {i + 1} | {seconds_to_mmss(dur)} | {bpm} |')
    add('')
    if tracks_time:
        add(f'> 边界（tracks_time）：`{json.dumps(tracks_time, ensure_ascii=False)}`')
    else:
        add('> 无 tracks_time，整轨作为一个切片（只给整专 BPM）')
    return '\n'.join(lines)


def run_spike(pool_id, tracks_time, report_out):
    """执行一次 spike：加载 → 逐段测拍 → 报告"""
    pool = load_pool_album(pool_id)
    if not pool:
        print(f'❌ album_pool 无 id={pool_id}')
        return 1
    audio_path = resolve_audio_path(pool['mp3_url'])
    if not audio_path or not os.path.exists(audio_path):
        print(f'❌ 音频文件不存在：{audio_path}')
        return 1
    # 单曲边界：优先 CLI 参数；否则池专辑 tracks_time；否则空（整轨一段）
    if tracks_time is None:
        tracks_time = safe_json_loads(pool.get('tracks_time')) or []

    print(f'📀 {pool["album_name"]}（{pool["singer"]}） id={pool_id}')
    print(f'🎧 {audio_path}')

    t0 = time.time()
    result = analyze_tempo(audio_path, tracks_time)
    elapsed = time.time() - t0

    print(f'⏱️  分析耗时 {elapsed:.1f}s（{len(result["track_tempos"])} 段）')
    print(f'📈 整专 BPM：avg {result["avg_bpm"]} / min {result["min_bpm"]} / max {result["max_bpm"]}')
    for i, (bpm, dur) in enumerate(zip(result['track_tempos'], result['track_durations'])):
        print(f'   [{i + 1}] {seconds_to_mmss(dur)}  {bpm} BPM')

    report = build_report(pool, audio_path, tracks_time, elapsed, result)
    print()
    print(report)

    if report_out:
        with open(report_out, 'w', encoding='utf-8') as f:
            f.write(report + '\n')
        print(f'📄 报告 → {report_out}')
    return 0


def main():
    parser = argparse.ArgumentParser(description='librosa BPM 节奏分析 spike')
    parser.add_argument('--pool-id', type=int, required=True, help='album_pool 专辑 id')
    parser.add_argument('--tracks-time', default=None,
                        help='单曲边界数组 JSON 如 "[0,254,334]"（默认读池专辑 tracks_time，无则整轨一段）')
    parser.add_argument('--report-out', default=None, help='评估报告 markdown 输出路径')
    args = parser.parse_args()
    tracks_time = json.loads(args.tracks_time) if args.tracks_time else None
    sys.exit(run_spike(args.pool_id, tracks_time, args.report_out))


if __name__ == '__main__':
    main()
