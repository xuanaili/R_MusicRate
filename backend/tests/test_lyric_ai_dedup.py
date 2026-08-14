# MusicRate\backend\tests\test_lyric_ai_dedup.py 歌词识别任务去重 + active 查询单测（v0.8.6，零 DB 零模型）
# 背景（v0.8.6 修复）：新专辑添加时后端自动触发 AI 识别，但前端从不轮询自动触发的任务 → 页面进度永远 0%；
#   且手动再点按钮会无条件新建任务，排到正在跑的长任务（BPM/识别，共享 serial_lock 串行）后面 → 又是 0% 排队。
# 修复：
#   - start_recognize_task 用 tasks.find_active(kind='lyric', album_pool_id) 去重——已有活跃任务则复用其 task_id
#   - 新增 GET /api/album/lyric/recognize/active/<pool_id> 返回该专辑当前活跃任务，供前端挂载时恢复轮询
# 本文件测纯逻辑部分（find_active 去重 / 无活跃则新建 / 路由 active 查询响应组装）；路由 HTTP 链路走 realdata
import pytest


class TestStartRecognizeTaskDedup:
    """start_recognize_task：已有活跃 lyric 任务 → 复用 task_id，不新建（防重复排队）"""

    def test_active_task_reused(self, monkeypatch):
        import backend.api.lyric_ai as mod
        existing = {'task_id': 'abc123', 'kind': 'lyric', 'album_pool_id': 99, 'status': 'running'}
        monkeypatch.setattr(mod.tasks, 'find_active', lambda kind=None, **kw: [existing])
        calls = []
        monkeypatch.setattr(mod.tasks, 'new_task_id', lambda: calls.append('new_task_id') or 'xyz789')
        monkeypatch.setattr(mod.tasks, 'create', lambda **kw: calls.append('create'))
        monkeypatch.setattr(mod.threading, 'Thread', lambda *a, **k: calls.append('Thread'))

        tid = mod.start_recognize_task(object(), 99, '某专辑', 1)

        assert tid == 'abc123'
        assert calls == []  # 未 new_task_id / 未 create / 未启动线程

    def test_active_filter_kind_lyric(self, monkeypatch):
        # find_active 必须以 kind='lyric' 过滤——不能复用 tempo（BPM）任务，只复用同专辑的歌词识别任务
        import backend.api.lyric_ai as mod
        seen = {}

        def _find_active(kind=None, **kw):
            seen['kind'] = kind
            seen['album_pool_id'] = kw.get('album_pool_id')
            return []

        monkeypatch.setattr(mod.tasks, 'find_active', _find_active)
        monkeypatch.setattr(mod.tasks, 'new_task_id', lambda: 'n1')
        monkeypatch.setattr(mod.tasks, 'create', lambda **kw: None)
        monkeypatch.setattr(mod.threading, 'Thread', lambda *a, **k: type('T', (), {'start': lambda self: None})())

        mod.start_recognize_task(object(), 42, 'A', 1)
        assert seen == {'kind': 'lyric', 'album_pool_id': 42}

    def test_no_active_creates_new_task(self, monkeypatch):
        import backend.api.lyric_ai as mod
        monkeypatch.setattr(mod.tasks, 'find_active', lambda kind=None, **kw: [])
        monkeypatch.setattr(mod.tasks, 'new_task_id', lambda: 'new1')
        created = {}
        monkeypatch.setattr(mod.tasks, 'create', lambda **kw: created.update(kw))
        monkeypatch.setattr(mod.threading, 'Thread', lambda *a, **k: type('T', (), {'start': lambda self: None})())

        tid = mod.start_recognize_task(object(), 77, '新专辑', 3)

        assert tid == 'new1'
        assert created['album_pool_id'] == 77
        assert created['kind'] == 'lyric'
        assert created['status'] == 'queued'
        assert created['progress'] == 0


class TestRecognizeActiveResponse:
    """GET /api/album/lyric/recognize/active/<pool_id> 响应组装（纯函数化路由内部查询，可单测）"""

    def test_no_active_response(self):
        import backend.api.lyric_ai as mod
        assert mod._build_active_response([]) == {'active': False}

    def test_active_response_fields(self):
        import backend.api.lyric_ai as mod
        task = {
            'task_id': 't1', 'status': 'running', 'progress': 68,
            'message': '模型转写中（VAD 关）… 68%', 'album_name': '某专辑',
        }
        data = mod._build_active_response([task])
        assert data['active'] is True
        assert data['task_id'] == 't1'
        assert data['status'] == 'running'
        assert data['progress'] == 68
        assert data['message'] == '模型转写中（VAD 关）… 68%'
        assert data['album_name'] == '某专辑'
