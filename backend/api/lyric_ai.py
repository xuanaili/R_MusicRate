# MusicRate\backend\api\lyric_ai.py 歌词 AI 识别异步任务接口（v0.8.1 P1）
# faster-whisper 整轨识别耗 CPU 数分钟（small int8 RTF≈0.18，44min 专辑 ≈ 8min）→ 后台线程 + 内存任务表，
# 前端「AI 识别歌词」按钮触发后轮询状态，完成后自动落 album_lyric。
# 决策（README v0.8.1）：
#   - 内存任务表不持久化（后端重启任务状态丢失，接口幂等：重复触发视为新任务）
#   - 识别串行化（tasks.serial_lock）：同一时间只跑一个识别任务，避免 CPU 100% 抢占，并发请求排队
#   - 产物整轨绝对时间存储文本落 album_lyric（复用 lyric.upsert_album_lyric），前端按 tracks_time 切分
#   - 识别器走 v0.8.1 P0：vad_filter=False（音乐场景 VAD 会整首丢失）+ 幻觉过滤 + OpenCC 繁转简
import os
import threading
import traceback
from datetime import datetime

import pymysql
from flask import jsonify, request

from backend import config
from backend.config import AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_current_user_id, get_db
from backend.utils.decorators import is_admin_user, login_required
from backend.utils.task_table import tasks, format_dt
from backend.utils.deepseek_correct import correct_lyric
from backend.utils.lyric_recognizer import build_full_storage_text, segments_to_items, transcribe
from backend.api.lyric import upsert_album_lyric

# 后台任务内存任务表（v0.8.1 P4 抽取共享：歌词识别 + BPM 分析共用同一实例，serial_lock 全局唯一保证 CPU 串行）
_app = None


def _resolve_audio_path(mp3_url):
    """mp3_url（http://localhost:5000/tracks/<filename>）→ 磁盘绝对路径
    backend/data/album_track/<filename>（与 audio_resource.py 存储/读取一致）
    """
    if not mp3_url:
        return None
    filename = mp3_url.split('/')[-1]
    return os.path.join(AUDIO_UPLOAD_FOLDER, filename)


def _do_recognize(app, album_pool_id, user_id, task_id):
    """后台执行识别：查池专辑 → 校验 mp3 → 转写（VAD 关）→ 幻觉过滤/繁转简 → 整轨绝对时间文本落库
    - 失败抛异常，由 _run_recognize 捕获标记 failed
    - 需 app.app_context：get_db 走 Flask g（线程独立连接），teardown_appcontext 自动 close
    - 产物整轨绝对时间存储格式（build_full_storage_text），前端按 tracks_time 切分，与 save/upload 落库等价
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT id, album_name, singer, mp3_url FROM album_pool WHERE id = %s', (album_pool_id,))
        pool = cursor.fetchone()
        cursor.close()
        if not pool:
            raise ValueError(f'公共专辑ID[{album_pool_id}]不存在')
        mp3_url = pool.get('mp3_url') or ''
        if not mp3_url:
            raise ValueError('该专辑无整轨 MP3，无法识别')
        audio_path = _resolve_audio_path(mp3_url)
        if not audio_path or not os.path.exists(audio_path):
            raise ValueError(f'整轨 MP3 文件不存在：{audio_path}')

        tasks.update(task_id, progress=10, message='模型转写中（VAD 关）…')
        # P0 管线：vad_filter=False + no_speech_prob 幻觉过滤 + 噪音模式滤除 + OpenCC 繁转简（segments_to_items 内置）
        segments, info, metrics = transcribe(audio_path)
        items = segments_to_items(segments)

        audio_seconds = metrics.get('audio_seconds') or 0
        result = {
            'segment_count': len(segments),
            'item_count': len(items),
            'elapsed': round(metrics.get('elapsed') or 0, 1),
            'audio_seconds': round(audio_seconds, 1),
            'rtf': round(metrics.get('rtf') or 0, 3),
        }
        if not items:
            result['progress'] = 100
            result['saved'] = False
            result['message'] = '识别完成但未产出有效歌词（音频可能是纯音乐/器乐，或识别异常）'
            return result

        tasks.update(task_id, progress=90, message='写入歌词…')
        # whisper 草稿（整轨绝对时间存储文本）
        lyric_text = build_full_storage_text(items)
        corrected = False
        correct_reason = None
        # v0.8.1 P2：若配置服务器端 DEEPSEEK_API_KEY → DeepSeek 校正（difflib 保时间戳只改文字）
        # 校正失败/未配置 → 回退 whisper 草稿（deepseek_correct.correct_lyric 内置回退），不阻断落库
        if config.DEEPSEEK_API_KEY:
            tasks.update(task_id, progress=93, message='DeepSeek 校正歌词中…')
            corrected_text, meta = correct_lyric(lyric_text, api_key=config.DEEPSEEK_API_KEY)
            corrected = meta.get('corrected') is True
            correct_reason = meta.get('reason') if not corrected else None
            if corrected:
                lyric_text = corrected_text
                result['anchor_lines'] = meta.get('anchor_lines')
                result['corrected_lines'] = meta.get('corrected_lines')

        # 整轨绝对时间存储文本落库（复用 save/upload 的 upsert 幂等路径，识别产物为草稿可再手动覆盖）
        upsert_album_lyric(db, album_pool_id, lyric_text, '{}', str(user_id))
        result['corrected'] = corrected
        if correct_reason:
            result['correct_reason'] = correct_reason
        result['progress'] = 100
        result['saved'] = True
        result['lyric_lines'] = len(lyric_text.splitlines()) if lyric_text else 0
        result['message'] = (
            f'识别完成，{"已 DeepSeek 校正" if corrected else "草稿歌词"}已落库（{result["lyric_lines"]} 行）'
        )
        return result


def _run_recognize(app, task_id, album_pool_id, user_id):
    """后台线程入口：串行锁排队 → 识别 → 更新任务状态"""
    # 排队等待（README：识别/分析串行化；同一时间只跑一个识别任务）
    tasks.serial_lock.acquire()
    try:
        if not tasks.get(task_id):
            return
        tasks.update(task_id, status='running', started_at=datetime.now())
        try:
            result = _do_recognize(app, album_pool_id, user_id, task_id)
            message = result.pop('message', '识别完成')
            tasks.update(task_id, status='done', message=message, **result)
        except Exception as e:
            print(f"❌ AI 识别任务[{task_id}]失败：{e}")
            traceback.print_exc()
            tasks.update(task_id, status='failed', progress=100, message=f'识别失败：{e}')
        tasks.update(task_id, finished_at=datetime.now())
    finally:
        tasks.serial_lock.release()


def format_dt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None


def register_lyric_ai_routes(app):
    """注册歌词 AI 识别异步任务路由（recognize 触发 + status 轮询），仅管理员可触发"""
    global _app
    _app = app

    # 1. 触发 AI 歌词识别（仅管理员）：校验池专辑存在 + 有整轨 mp3 → 启动后台线程 → 返回 task_id
    @app.route('/api/album/lyric/recognize/<int:album_pool_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def recognize_lyric(album_pool_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            if not is_admin_user(current_user_id):
                return jsonify({"code": 403, "msg": "只有管理员才能触发 AI 识别歌词！"}), 403

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT id, album_name, singer, mp3_url FROM album_pool WHERE id = %s', (album_pool_id,))
            pool = cursor.fetchone()
            cursor.close()
            if not pool:
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404
            mp3_url = pool.get('mp3_url') or ''
            if not mp3_url:
                return jsonify({"code": 400, "msg": "该专辑无整轨 MP3，无法识别！"}), 400
            audio_path = _resolve_audio_path(mp3_url)
            if not audio_path or not os.path.exists(audio_path):
                return jsonify({"code": 400, "msg": "整轨 MP3 文件不存在，请先上传音频！"}), 400

            # 幂等：重复触发视为新任务（README：内存任务表不持久化，接口幂等）
            task_id = tasks.new_task_id()
            tasks.create(
                task_id=task_id,
                album_pool_id=album_pool_id,
                album_name=pool['album_name'],
                user_id=current_user_id,
                status='queued',
                message='任务已创建，排队等待识别',
                progress=0,
                created_at=datetime.now(),
            )

            t = threading.Thread(
                target=_run_recognize, args=(app, task_id, album_pool_id, current_user_id), daemon=True,
            )
            t.start()

            return jsonify({
                "code": 200,
                "msg": "AI 识别已开始（后台生成中，44 分钟专辑约需 8 分钟）",
                "data": {
                    "task_id": task_id,
                    "album_pool_id": album_pool_id,
                    "album_name": pool['album_name'],
                    "status": "queued",
                }
            })
        except Exception as e:
            print(f"❌ 触发 AI 识别出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"触发 AI 识别失败：{str(e)}"}), 500

    # 2. 查询识别任务状态（轮询）：running/done/failed + 进度 + 统计
    @app.route('/api/album/lyric/recognize/status/<task_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def recognize_status(task_id):
        try:
            task = tasks.get(task_id)
            if not task:
                return jsonify({"code": 404, "msg": f"任务[{task_id}]不存在（后端重启会丢失内存任务）"}), 404
            return jsonify({
                "code": 200,
                "msg": "查询成功",
                "data": {
                    "task_id": task['task_id'],
                    "album_pool_id": task.get('album_pool_id'),
                    "album_name": task.get('album_name'),
                    "status": task.get('status'),
                    "message": task.get('message'),
                    "progress": task.get('progress'),
                    "segment_count": task.get('segment_count'),
                    "item_count": task.get('item_count'),
                    "lyric_lines": task.get('lyric_lines'),
                    "saved": task.get('saved'),
                    "corrected": task.get('corrected'),
                    "correct_reason": task.get('correct_reason'),
                    "anchor_lines": task.get('anchor_lines'),
                    "corrected_lines": task.get('corrected_lines'),
                    "elapsed": task.get('elapsed'),
                    "rtf": task.get('rtf'),
                    "created_at": format_dt(task.get('created_at')),
                    "started_at": format_dt(task.get('started_at')),
                    "finished_at": format_dt(task.get('finished_at')),
                }
            })
        except Exception as e:
            print(f"❌ 查询识别任务状态出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"查询任务状态失败：{str(e)}"}), 500

    return app


# 导出注册函数
__all__ = ['register_lyric_ai_routes']
