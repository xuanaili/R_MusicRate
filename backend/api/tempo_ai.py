# MusicRate\backend\api\tempo_ai.py BPM 节奏分析异步任务接口（v0.8.1 P4）
# 对池专辑整轨 mp3 做节奏分析：librosa 测拍按单曲边界逐段分析（每段 <0.5s），后台线程执行避免阻塞请求，
# 完成后缓存到 album_tempo（album_pool_id 唯一，upsert），供 AI 助手上下文读取。
# 决策（README v0.8.1）：
#   - 与歌词识别共用同一内存任务表 tasks（task_table 模块级单例）→ serial_lock 全局唯一，CPU 密集任务严格串行
#   - 触发管理员专属（同歌词识别）；重复触发视为新任务（内存任务表不持久化，接口幂等）
#   - 单曲边界优先读 album_pool.tracks_time，为空则回退触发用户的私有副本（albums_{user_id}.source_pool_id）
#   - 产物仅缓存 album_tempo，不改 mp3 / tracks_time / 歌词
# v0.8.3 P1 BPM 预触发：
#   - 新增 ensure_tempo get-or-trigger（album_tempo 缓存短路 + tasks.find_active 防重复）+ 任意登录用户可用的
#     POST /api/ai/tempo/ensure/<album_pool_id>，供前端专辑详情页打开 / AI 助手 tab 打开两个时机幂等预触发，
#     消除「首次提问才开始分析 BPM」的滞后；chat 不再返回「节奏分析中」占位（见 ai.py）
import json
import os
import threading
import traceback
from datetime import datetime

import pymysql
from flask import jsonify, request

from backend.config import AUDIO_UPLOAD_FOLDER
from backend.utils.db import get_album_table_name, get_current_user_id, get_db
from backend.utils.decorators import is_admin_user, login_required
from backend.utils.task_table import tasks, format_dt
from backend.utils.json import safe_json_loads
from backend.utils.tempo_analyzer import analyze_tempo

# 后台任务线程用的 Flask app 引用（register 时注入）
_app = None


def _resolve_audio_path(mp3_url):
    """mp3_url（http://localhost:5000/tracks/<filename>）→ 磁盘绝对路径
    与 lyric_ai._resolve_audio_path / audio_resource.py 存储读取一致
    """
    if not mp3_url:
        return None
    filename = mp3_url.split('/')[-1]
    return os.path.join(AUDIO_UPLOAD_FOLDER, filename)


def upsert_album_tempo(db, album_pool_id, tempo_dict):
    """缓存/更新 album_tempo（album_pool_id 唯一，upsert）
    tempo TEXT 存 build_tempo_result 的 JSON：{track_tempos, avg_bpm, min_bpm, max_bpm, track_durations}
    """
    tempo_json = json.dumps(tempo_dict, ensure_ascii=False)
    cursor = db.cursor()
    cursor.execute(
        '''INSERT INTO album_tempo (album_pool_id, tempo)
           VALUES (%s, %s)
           ON DUPLICATE KEY UPDATE tempo = %s''',
        (album_pool_id, tempo_json, tempo_json),
    )
    db.commit()
    cursor.close()


def _do_tempo(app, album_pool_id, user_id, task_id):
    """后台执行分析：查池专辑 → 校验 mp3 → 取单曲边界 → 逐段测拍 → 聚合 → 缓存 album_tempo
    - 失败抛异常，由 _run_tempo 捕获标记 failed
    - 需 app.app_context：get_db 走 Flask g（线程独立连接），teardown_appcontext 自动 close
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('SELECT id, album_name, singer, mp3_url, tracks_time FROM album_pool WHERE id = %s', (album_pool_id,))
        pool = cursor.fetchone()
        cursor.close()
        if not pool:
            raise ValueError(f'公共专辑ID[{album_pool_id}]不存在')
        mp3_url = pool.get('mp3_url') or ''
        if not mp3_url:
            raise ValueError('该专辑无整轨 MP3，无法分析')
        audio_path = _resolve_audio_path(mp3_url)
        if not audio_path or not os.path.exists(audio_path):
            raise ValueError(f'整轨 MP3 文件不存在：{audio_path}')

        # 单曲边界：优先池专辑 tracks_time（[每首起始秒,...]），为空则回退触发用户的私有副本（可能编辑过时间戳）
        tracks_time = safe_json_loads(pool.get('tracks_time')) or []
        if not tracks_time:
            user_table = get_album_table_name(user_id)
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute(f'SELECT tracks_time FROM `{user_table}` WHERE source_pool_id = %s', (album_pool_id,))
            user_album = cursor.fetchone()
            cursor.close()
            if user_album:
                tracks_time = safe_json_loads(user_album.get('tracks_time')) or []

        tasks.update(task_id, progress=30, message='逐段测拍中…')
        result = analyze_tempo(audio_path, tracks_time)

        tasks.update(task_id, progress=90, message='写入节奏缓存…')
        upsert_album_tempo(db, album_pool_id, result)
        result['segments'] = len(result['track_tempos'])
        result['progress'] = 100
        result['saved'] = True
        result['message'] = f'节奏分析完成（{result["segments"]} 段）'
        return result


def _run_tempo(app, task_id, album_pool_id, user_id):
    """后台线程入口：串行锁排队 → 分析 → 更新任务状态"""
    tasks.serial_lock.acquire()
    try:
        if not tasks.get(task_id):
            return
        tasks.update(task_id, status='running', started_at=datetime.now())
        try:
            result = _do_tempo(app, album_pool_id, user_id, task_id)
            message = result.pop('message', '节奏分析完成')
            tasks.update(task_id, status='done', message=message, **result)
        except Exception as e:
            print(f"❌ BPM 分析任务[{task_id}]失败：{e}")
            traceback.print_exc()
            tasks.update(task_id, status='failed', progress=100, message=f'节奏分析失败：{e}')
        tasks.update(task_id, finished_at=datetime.now())
    finally:
        tasks.serial_lock.release()


def start_tempo_task(app, album_pool_id, album_name, user_id):
    """创建并启动 BPM 分析后台任务（tempo/analyze 路由 与 AI chat 懒分析共用）
    - 复用全局任务表单例 tasks（kind='tempo'，find_active 区分歌词识别任务）；CPU 串行由 _run_tempo 的 serial_lock 保证
    - 调用方负责前置校验（池存在 / 有整轨 mp3 / 管理员）；返回 task_id
    """
    task_id = tasks.new_task_id()
    tasks.create(
        task_id=task_id,
        kind='tempo',
        album_pool_id=album_pool_id,
        album_name=album_name,
        user_id=user_id,
        status='queued',
        message='任务已创建，排队等待分析',
        progress=0,
        created_at=datetime.now(),
    )
    t = threading.Thread(
        target=_run_tempo, args=(app, task_id, album_pool_id, user_id), daemon=True,
    )
    t.start()
    return task_id


def ensure_tempo(app, album_pool_id, user_id):
    """get-or-trigger：确保该专辑节奏 BPM 分析已触发（幂等，v0.8.3 P1）
    - 池不存在 / 无整轨 mp3（或磁盘文件缺失）→ {ready:false, has_mp3:false}（not_found 供路由 404）
    - album_tempo 已有缓存 → {ready:true}
    - 有活跃 tempo 任务（queued/running）→ {ready:false, analyzing:true, task_id}（find_active 防重复启动）
    - 否则 start_tempo_task 启动 → {ready:false, analyzing:true, task_id}
    供前端专辑详情页 / AI 助手 tab 双时机预触发 + ai_chat 懒分析共用；任意登录用户可调用（无 is_admin 校验）
    """
    db = get_db()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('SELECT id, album_name, mp3_url FROM album_pool WHERE id = %s', (album_pool_id,))
        pool = cursor.fetchone()
        if not pool:
            return {'ready': False, 'has_mp3': False, 'not_found': True}

        mp3_url = pool.get('mp3_url') or ''
        if not mp3_url:
            return {'ready': False, 'has_mp3': False}
        audio_path = _resolve_audio_path(mp3_url)
        if not audio_path or not os.path.exists(audio_path):
            return {'ready': False, 'has_mp3': False}

        # ① 已有缓存 → ready（短路，不再分析）
        cursor.execute('SELECT 1 FROM album_tempo WHERE album_pool_id = %s LIMIT 1', (album_pool_id,))
        if cursor.fetchone():
            return {'ready': True, 'has_mp3': True}

        # ② 有活跃 tempo 任务 → 复用任务 id，不重复启动
        active = tasks.find_active(kind='tempo', album_pool_id=album_pool_id)
        if active:
            return {'ready': False, 'has_mp3': True, 'analyzing': True, 'task_id': active[0].get('task_id')}

        # ③ 启动后台分析任务
        task_id = start_tempo_task(app, album_pool_id, pool['album_name'], user_id)
        return {'ready': False, 'has_mp3': True, 'analyzing': True, 'task_id': task_id}
    finally:
        cursor.close()


def register_tempo_ai_routes(app):
    """注册 BPM 节奏分析异步任务路由（analyze 管理员触发 + ensure 任意用户预触发 + status 轮询）"""
    global _app
    _app = app

    # 0. BPM 预触发 get-or-trigger（v0.8.3 P1，任意登录用户）：album_tempo 已有 → ready；有活跃任务 → 复用；
    #    否则启动后台线程。池不存在 404 / 无 mp3 → has_mp3:false（前端忽略）
    @app.route('/api/ai/tempo/ensure/<int:album_pool_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def tempo_ensure(album_pool_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            result = ensure_tempo(app, album_pool_id, current_user_id)
            if result.get('not_found'):
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404
            return jsonify({
                "code": 200,
                "msg": "节奏状态查询成功",
                "data": result,
            })
        except Exception as e:
            print(f"❌ BPM 预触发 ensure 出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"预触发节奏分析失败：{str(e)}"}), 500

    # 1. 触发 BPM 节奏分析（仅管理员）：校验池专辑存在 + 有整轨 mp3 → 启动后台线程 → 返回 task_id
    @app.route('/api/ai/tempo/analyze/<int:album_pool_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def tempo_analyze(album_pool_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            if not is_admin_user(current_user_id):
                return jsonify({"code": 403, "msg": "只有管理员才能触发节奏分析！"}), 403

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT id, album_name, mp3_url FROM album_pool WHERE id = %s', (album_pool_id,))
            pool = cursor.fetchone()
            cursor.close()
            if not pool:
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404
            mp3_url = pool.get('mp3_url') or ''
            if not mp3_url:
                return jsonify({"code": 400, "msg": "该专辑无整轨 MP3，无法分析！"}), 400
            audio_path = _resolve_audio_path(mp3_url)
            if not audio_path or not os.path.exists(audio_path):
                return jsonify({"code": 400, "msg": "整轨 MP3 文件不存在，请先上传音频！"}), 400

            # 幂等：重复触发视为新任务（README：内存任务表不持久化，接口幂等）
            # 与 AI chat 懒分析共用 start_tempo_task（kind='tempo'，find_active 区分任务类型）
            task_id = start_tempo_task(app, album_pool_id, pool['album_name'], current_user_id)

            return jsonify({
                "code": 200,
                "msg": "节奏分析已开始（后台逐段测拍，通常几十秒内完成）",
                "data": {
                    "task_id": task_id,
                    "album_pool_id": album_pool_id,
                    "album_name": pool['album_name'],
                    "status": "queued",
                }
            })
        except Exception as e:
            print(f"❌ 触发节奏分析出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"触发节奏分析失败：{str(e)}"}), 500

    # 2. 查询节奏分析任务状态（轮询）：running/done/failed + 进度 + BPM 结果
    @app.route('/api/ai/tempo/status/<task_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def tempo_status(task_id):
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
                    "saved": task.get('saved'),
                    "segments": task.get('segments'),
                    "track_tempos": task.get('track_tempos'),
                    "track_durations": task.get('track_durations'),
                    "avg_bpm": task.get('avg_bpm'),
                    "min_bpm": task.get('min_bpm'),
                    "max_bpm": task.get('max_bpm'),
                    "created_at": format_dt(task.get('created_at')),
                    "started_at": format_dt(task.get('started_at')),
                    "finished_at": format_dt(task.get('finished_at')),
                }
            })
        except Exception as e:
            print(f"❌ 查询节奏分析任务状态出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"查询任务状态失败：{str(e)}"}), 500

    # 3. 直读 album_tempo 缓存（v0.9 P0）：前端自动样式按 BPM 微调用，只读不改动 ensure/analyze/status
    #    有缓存 → {ready:true, tempo:{track_tempos, avg_bpm, ...}}；无缓存 → {ready:false}（等待 ensure/analyze 补齐）
    @app.route('/api/ai/tempo/get/<int:album_pool_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def tempo_get(album_pool_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            try:
                cursor.execute('SELECT 1 FROM album_pool WHERE id = %s', (album_pool_id,))
                if not cursor.fetchone():
                    return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404
                cursor.execute('SELECT tempo FROM album_tempo WHERE album_pool_id = %s', (album_pool_id,))
                row = cursor.fetchone()
            finally:
                cursor.close()

            if not row:
                return jsonify({"code": 200, "msg": "该专辑尚无 BPM 缓存（未分析或分析中）", "data": {"ready": False}})
            tempo = safe_json_loads(row.get('tempo')) or {}
            return jsonify({
                "code": 200,
                "msg": "获取 BPM 缓存成功",
                "data": {"ready": True, "tempo": tempo},
            })
        except Exception as e:
            print(f"❌ 直读 BPM 缓存出错：{str(e)}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": f"读取 BPM 缓存失败：{str(e)}"}), 500

    return app


# 导出注册函数
__all__ = ['register_tempo_ai_routes']
