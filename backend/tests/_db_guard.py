# -*- coding: utf-8 -*-
"""真实库（realdata）测试数据回收：水位线机制

为什么需要：
    `pytest -m realdata` 会往**生产用的 MySQL** 里注册测试用户、插入测试专辑
    （历史上留下 1193 个 test_* 用户、1193 张 albums_N 空表、557 条「XX测试专辑」），
    搜索页就出现一堆「暂无封面 / 节奏分析测试专辑」的脏数据。

做法：
    测试会话开始前记录各表自增 id 水位线 + 素材目录文件快照；
    会话结束后把「水位线以上」新建的数据删掉、把新注册用户的分表 DROP、
    把测试新建的音频/封面文件删掉。真实用户（会话开始前就存在）的数据一律不动。

约束（配合 CLAUDE.md 铁律）：
    - 兜底不等于许可：写 realdata 测试仍应尽量自己清理
    - 测试插入的池专辑用 `create_user = 0` 或测试用户 id；用真实用户 id 插入的数据不会被回收
"""
import os

# 会话结束要按水位线回收的表 → (表名, 自增列)
MAX_ID_COLUMNS = [
    ('users', 'user_id'),
    ('album_pool', 'id'),
    ('album_lyric', 'id'),
    ('album_tempo', 'id'),
    ('album_comments', 'id'),
    ('album_share', 'id'),
    ('album_singers', 'id'),
    ('album_tags', 'id'),
    ('ai_key', 'id'),
    ('ai_conversation', 'id'),
    ('ai_quota', 'id'),
    ('user_playlist', 'id'),
    ('user_recommend', 'id'),
    ('user_listening_log', 'id'),
    ('user_xp_log', 'id'),
    ('user_album_style', 'id'),
    ('user_album_intro', 'id'),
    ('user_album_relation', 'id'),
]

# 按 user_id 回收的表
USER_SCOPED_TABLES = [
    'user_playlist', 'user_recommend', 'user_listening_log', 'user_xp_log',
    'user_album_style', 'user_album_intro', 'user_album_relation',
    'ai_key', 'ai_conversation', 'ai_quota', 'album_comments',
]

# 按池专辑 id 回收的表 → (表名, 外键列)
POOL_SCOPED_TABLES = [
    ('album_lyric', 'album_pool_id'),
    ('album_tempo', 'album_pool_id'),
    ('album_share', 'album_pool_id'),
    ('album_comments', 'album_id'),
    ('user_album_intro', 'album_id'),
    ('user_album_relation', 'album_pool_id'),
    ('ai_conversation', 'album_pool_id'),
]

# 测试素材目录（测试会往里塞空 mp3 / 假封面）
DATA_DIRS = [
    os.path.join('backend', 'data', 'album_track'),
    os.path.join('backend', 'data', 'album_covers'),
    os.path.join('backend', 'data', 'album_covers_thumb'),
]


# ================= 纯逻辑（便于单测） =================

def should_purge_pool(create_user, new_user_ids):
    """新建的池专辑是否属于测试数据

    create_user == 0 → 测试脚本常用（真实用户 id 从 1 开始）
    create_user 在会话内新建用户集合里 → 测试用户创建的
    其它（真实用户在会话期间手工加的专辑）→ 不动
    """
    if create_user is None:
        return True
    try:
        create_user = int(create_user)
    except (TypeError, ValueError):
        return False
    return create_user == 0 or create_user in set(new_user_ids or ())


def diff_new_files(before, after):
    """快照差集：新增的文件（before/after 为 set）"""
    return sorted(set(after) - set(before))


def build_in_clause(values):
    """构造 SQL IN 子句的占位符与参数"""
    values = list(values or [])
    if not values:
        return 'NULL', []
    return ', '.join(['%s'] * len(values)), values


# ================= DB 操作 =================

def connect(mysql_config):
    """独立连接（不依赖 Flask 上下文）；失败返回 None

    必须 autocommit=True：否则首个 SELECT 就开了 REPEATABLE READ 快照，
    会话结束时用同一个连接查「水位线以上的新数据」会看不见测试刚插的行，回收直接失效。
    """
    import pymysql
    config = {k: v for k, v in mysql_config.items() if k != 'db'}
    config['database'] = mysql_config.get('db')
    try:
        return pymysql.connect(**config, connect_timeout=5, read_timeout=60, autocommit=True)
    except Exception:  # noqa: BLE001 - 没装 MySQL / 没启动时跳过回收，不影响纯单测
        return None


def snapshot_max_ids(cursor):
    """记录各表自增列水位线 → {(表, 列): 最大值}"""
    snapshot = {}
    for table, column in MAX_ID_COLUMNS:
        try:
            cursor.execute(f'SELECT COALESCE(MAX(`{column}`), 0) AS v FROM `{table}`')
            snapshot[f'{table}.{column}'] = int(cursor.fetchone()['v'])
        except Exception:  # noqa: BLE001 - 表不存在（旧库/精简库）跳过
            continue
    return snapshot


def snapshot_files(root_dir):
    """记录素材目录下的文件名集合 → {目录: set(文件名)}"""
    snapshot = {}
    for relative in DATA_DIRS:
        directory = os.path.join(root_dir, relative)
        try:
            snapshot[relative] = set(os.listdir(directory)) if os.path.isdir(directory) else set()
        except OSError:
            snapshot[relative] = set()
    return snapshot


def purge(conn, max_ids, file_snapshot=None, root_dir=None, verbose=True):
    """按水位线清理会话期间新建的测试数据，返回统计字典"""
    cursor = conn.cursor()
    report = {'rows': 0, 'dropped_tables': 0, 'files': 0}

    def _exec(sql, params=None):
        affected = cursor.execute(sql, params or [])
        report['rows'] += affected
        return affected

    try:
        # 1) 会话内新建的用户
        new_user_ids = []
        user_watermark = max_ids.get('users.user_id', 0)
        try:
            cursor.execute('SELECT user_id FROM users WHERE user_id > %s', (user_watermark,))
            new_user_ids = [row['user_id'] for row in cursor.fetchall()]
        except Exception:  # noqa: BLE001
            pass

        # 2) 会话内新建的池专辑：仅回收测试创建的那些（create_user=0 或新建用户）
        new_pool_ids = []
        pool_watermark = max_ids.get('album_pool.id', 0)
        try:
            cursor.execute('SELECT id, create_user FROM album_pool WHERE id > %s', (pool_watermark,))
            new_pool_ids = [row['id'] for row in cursor.fetchall()
                            if should_purge_pool(row['create_user'], new_user_ids)]
        except Exception:  # noqa: BLE001
            pass

        pool_clause, pool_params = build_in_clause(new_pool_ids)
        user_clause, user_params = build_in_clause(new_user_ids)

        # 3) 现有用户表里指向测试池专辑的副本
        if new_pool_ids:
            cursor.execute("SELECT table_name AS t FROM information_schema.tables "
                           "WHERE table_schema = DATABASE() AND table_name LIKE 'albums\\_%'")
            for row in cursor.fetchall():
                table = row['t']
                if table in {f'albums_{uid}' for uid in new_user_ids}:
                    continue  # 这些表整体要 DROP，不用删行
                try:
                    _exec(f'DELETE FROM `{table}` WHERE source_pool_id IN ({pool_clause})', pool_params)
                except Exception:  # noqa: BLE001
                    continue

        # 4) 池专辑关联数据
        if new_pool_ids:
            for table, column in POOL_SCOPED_TABLES:
                try:
                    _exec(f'DELETE FROM `{table}` WHERE `{column}` IN ({pool_clause})', pool_params)
                except Exception:  # noqa: BLE001
                    continue
            try:
                _exec(f'DELETE FROM album_pool WHERE id IN ({pool_clause})', pool_params)
            except Exception:  # noqa: BLE001
                pass

        # 5) 用户维度数据
        if new_user_ids:
            for table in USER_SCOPED_TABLES:
                try:
                    _exec(f'DELETE FROM `{table}` WHERE user_id IN ({user_clause})', user_params)
                except Exception:  # noqa: BLE001
                    continue
            try:
                _exec(f'DELETE FROM album_lyric WHERE create_user_id IN ({user_clause})', user_params)
            except Exception:  # noqa: BLE001
                pass
            try:
                _exec(f'DELETE FROM album_share WHERE create_user_id IN ({user_clause})', user_params)
            except Exception:  # noqa: BLE001
                pass
            try:
                _exec(f'DELETE FROM album_pool WHERE create_user IN ({user_clause})', user_params)
            except Exception:  # noqa: BLE001
                pass
        conn.commit()

        # 6) 测试新增的歌手/标签（只回收名字含「测试」的，避免误删真实新增）
        for table, column in (('album_singers', 'singer_name'), ('album_tags', 'tags_name')):
            try:
                _exec(f"DELETE FROM `{table}` WHERE `{column}` LIKE '%%测试%%' "
                      f"AND id > %s", (max_ids.get(f'{table}.id', 0),))
            except Exception:  # noqa: BLE001
                continue
        conn.commit()

        # 7) DROP 测试用户的 albums_ 分表 + 删除用户行
        if new_user_ids:
            for user_id in new_user_ids:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS `albums_{int(user_id)}`')
                    report['dropped_tables'] += 1
                except Exception:  # noqa: BLE001
                    continue
            _exec(f'DELETE FROM users WHERE user_id IN ({user_clause})', user_params)
            conn.commit()

        # 8) 清理测试新建的素材文件
        if file_snapshot is not None and root_dir:
            for relative, before in file_snapshot.items():
                directory = os.path.join(root_dir, relative)
                try:
                    current = set(os.listdir(directory)) if os.path.isdir(directory) else set()
                except OSError:
                    continue
                for name in diff_new_files(before, current):
                    path = os.path.join(directory, name)
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                            report['files'] += 1
                    except OSError:
                        continue
    finally:
        cursor.close()

    if verbose and (report['rows'] or report['dropped_tables'] or report['files']):
        print(f"\n🧹 测试数据回收：删除 {report['rows']} 行 / "
              f"DROP {report['dropped_tables']} 张用户表 / 清理 {report['files']} 个素材文件")
    return report
