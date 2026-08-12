# MusicRate\backend\tests\test_tempo_ensure.py ensure_tempo get-or-trigger 决策单测（v0.8.3 P1，零 DB 依赖）
# 用 fake DB cursor 模拟 ensure_tempo 的 SELECT 分支，锁定 get-or-trigger 五条决策路径：
#   池不存在 → not_found / 无整轨 mp3（URL 空或文件缺失）→ has_mp3:false /
#   已缓存 → ready:true / 有活跃任务 → 复用 task_id / 否则 → start_tempo_task 启动新任务
from backend.api.tempo_ai import ensure_tempo


class _FakeCursor:
    """按顺序返回预设 fetchone 结果的伪 cursor（execute 无副作用）"""
    def __init__(self, fetchone_results):
        self._results = list(fetchone_results)
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(sql)

    def fetchone(self):
        return self._results.pop(0) if self._results else None

    def close(self):
        pass


class _FakeDB:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, *args, **kwargs):
        return self._cursor


def _patch(monkeypatch, cursor, audio_exists=True, active_tasks=()):
    """装配 ensure_tempo 的全部依赖（DB / 文件存在 / 活跃任务 / start_tempo_task），返回 start 调用记录"""
    import backend.api.tempo_ai as mod
    monkeypatch.setattr(mod, 'get_db', lambda: _FakeDB(cursor))
    monkeypatch.setattr(mod.os.path, 'exists', lambda p: audio_exists)
    monkeypatch.setattr(mod.tasks, 'find_active', lambda **kw: list(active_tasks))

    calls = []

    def _start(app, album_pool_id, album_name, user_id):
        calls.append({'album_pool_id': album_pool_id, 'album_name': album_name, 'user_id': user_id})
        return 'new-task'

    monkeypatch.setattr(mod, 'start_tempo_task', _start)
    return calls


def test_ensure_pool_not_found(monkeypatch):
    cursor = _FakeCursor([None])
    _patch(monkeypatch, cursor)
    r = ensure_tempo(None, 1, 1)
    assert r == {'ready': False, 'has_mp3': False, 'not_found': True}


def test_ensure_no_mp3_url(monkeypatch):
    cursor = _FakeCursor([{'id': 1, 'album_name': 'A', 'mp3_url': ''}])
    _patch(monkeypatch, cursor)
    r = ensure_tempo(None, 1, 1)
    assert r == {'ready': False, 'has_mp3': False}


def test_ensure_mp3_file_missing(monkeypatch):
    cursor = _FakeCursor([{'id': 1, 'album_name': 'A', 'mp3_url': 'http://x/t.mp3'}])
    _patch(monkeypatch, cursor, audio_exists=False)
    r = ensure_tempo(None, 1, 1)
    assert r == {'ready': False, 'has_mp3': False}


def test_ensure_cached_ready(monkeypatch):
    # 第一条 SELECT 命中 pool，第二条命中 album_tempo 缓存 → ready
    cursor = _FakeCursor([
        {'id': 1, 'album_name': 'A', 'mp3_url': 'http://x/t.mp3'},
        {'1': 1},
    ])
    calls = _patch(monkeypatch, cursor)
    r = ensure_tempo(None, 1, 1)
    assert r == {'ready': True, 'has_mp3': True}
    assert calls == []


def test_ensure_active_task_reused(monkeypatch):
    # pool 命中、缓存未命中、find_active 返回活跃任务 → 复用其 task_id，不启动新任务
    cursor = _FakeCursor([
        {'id': 1, 'album_name': 'A', 'mp3_url': 'http://x/t.mp3'},
        None,
    ])
    active = [{'task_id': 'running-task', 'kind': 'tempo', 'status': 'running'}]
    calls = _patch(monkeypatch, cursor, active_tasks=active)
    r = ensure_tempo(None, 1, 1)
    assert r == {'ready': False, 'has_mp3': True, 'analyzing': True, 'task_id': 'running-task'}
    assert calls == []


def test_ensure_starts_new_task(monkeypatch):
    # pool 命中、缓存未命中、无活跃任务 → start_tempo_task 启动，返回新 task_id
    cursor = _FakeCursor([
        {'id': 1, 'album_name': 'A', 'mp3_url': 'http://x/t.mp3'},
        None,
    ])
    calls = _patch(monkeypatch, cursor, active_tasks=[])
    r = ensure_tempo(None, 1, 1)
    assert r == {'ready': False, 'has_mp3': True, 'analyzing': True, 'task_id': 'new-task'}
    assert calls == [{'album_pool_id': 1, 'album_name': 'A', 'user_id': 1}]
