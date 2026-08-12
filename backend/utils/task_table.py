# MusicRate\backend\utils\task_table.py 后台任务内存任务表（v0.8.1 P4 从 lyric_ai.py 抽取共享）
# 歌词识别 / BPM 分析等 CPU 密集后台任务共用：
#   - 内存任务表不持久化（后端重启任务状态丢失 → 接口幂等：重复触发视为新任务）
#   - 任务串行化（serial_lock：同一时间只跑一个，避免 CPU 100% 抢占，并发请求排队）
#   - 容量控制：超限清理最早完成/失败的任务（运行/排队中的不删）
import threading
import uuid

# 内存任务表最大保留数（防止无限增长）
MAX_TASKS = 100


class TaskTable:
    """线程安全的后台任务表（单机内存版，不引 Redis）
    - create(**fields)：插入任务（须含 task_id），自动容量清理
    - get(task_id) / update(task_id, **fields)
    - serial_lock：串行执行锁（acquire/release 由调用方管理，见 lyric_ai._run_recognize）
    """

    def __init__(self):
        self._tasks = {}
        self._lock = threading.RLock()      # 嵌套访问安全（创建 + 容量清理同一临界区）
        self.serial_lock = threading.Lock()  # 串行执行锁：同一时间只跑一个后台任务

    def new_task_id(self):
        """生成任务 id（短随机，内存表足够）"""
        return uuid.uuid4().hex[:12]

    def create(self, **fields):
        """插入一个任务（须含 task_id），超限时清理最早完成/失败的任务"""
        with self._lock:
            self._tasks[fields['task_id']] = fields
            if len(self._tasks) > MAX_TASKS:
                completed_ids = sorted(
                    [tid for tid, t in self._tasks.items() if t.get('status') in ('done', 'failed')],
                    key=lambda tid: self._tasks[tid]['created_at'],
                )
                while len(self._tasks) > MAX_TASKS and completed_ids:
                    self._tasks.pop(completed_ids.pop(0), None)

    def get(self, task_id):
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task_id, **fields):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.update(fields)


def format_dt(dt):
    """datetime → 字符串（任务表时间字段展示用），None → None"""
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None
