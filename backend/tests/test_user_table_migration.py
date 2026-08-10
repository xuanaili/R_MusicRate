# MusicRate\backend\tests\test_user_table_migration.py users表avatar列幂等迁移纯逻辑单测（零 DB 依赖）
# 测试对象：backend/utils/db.py 的 needs_avatar_column()（缺列→需要迁移；已存在→跳过）
from backend.utils.db import needs_avatar_column


class TestNeedsAvatarColumn:
    def test_missing_avatar_returns_true(self):
        # 旧库：无 avatar 列 → 需要执行 ALTER 迁移
        cols = ['user_id', 'username', 'password', 'token', 'is_admin']
        assert needs_avatar_column(cols) is True

    def test_avatar_present_returns_false(self):
        # 已迁移过：含 avatar 列 → 幂等跳过
        cols = ['user_id', 'username', 'password', 'avatar']
        assert needs_avatar_column(cols) is False

    def test_empty_columns_returns_true(self):
        # 极端情况：查不到任何列也视为需要迁移（缺列即建）
        assert needs_avatar_column([]) is True

    def test_avatar_case_insensitive(self):
        # information_schema 列名大小写不敏感，迁移判断需容错
        assert needs_avatar_column(['user_id', 'AVATAR']) is False

    def test_avatar_in_full_users_schema(self):
        # 模拟完整 users 表结构（含 avatar）→ 跳过迁移
        cols = [
            'user_id', 'username', 'password', 'level', 'create_time',
            'last_login', 'is_vip', 'is_admin', 'donate_amount',
            'album_count', 'token', 'avatar'
        ]
        assert needs_avatar_column(cols) is False
