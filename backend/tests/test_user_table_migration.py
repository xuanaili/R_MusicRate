# MusicRate\backend\tests\test_user_table_migration.py users表幂等迁移纯逻辑单测（零 DB 依赖）
# 测试对象：backend/utils/db.py 的 needs_avatar_column() / needs_xp_columns()（缺列→需要迁移；已存在→跳过）
from backend.utils.db import needs_avatar_column, needs_xp_columns


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


class TestNeedsXpColumns:
    """v0.7.1 P0 等级经验四列幂等迁移判断：缺任一列 → 需要迁移"""

    def test_missing_all_xp_columns(self):
        # 老库（仅 avatar 迁移后）：无任何等级经验列 → 需要迁移
        cols = ['user_id', 'username', 'password', 'level', 'avatar', 'token']
        assert needs_xp_columns(cols) is True

    def test_missing_one_of_four(self):
        # 只有 xp 列，缺 listening_total → 仍需迁移
        cols = ['user_id', 'xp', 'bonus_date', 'bonus_xp_today']
        assert needs_xp_columns(cols) is True

    def test_all_four_present(self):
        # 四列齐全 → 幂等跳过
        cols = ['user_id', 'xp', 'listening_total', 'bonus_date', 'bonus_xp_today']
        assert needs_xp_columns(cols) is False

    def test_empty_columns_returns_true(self):
        assert needs_xp_columns([]) is True

    def test_case_insensitive(self):
        # information_schema 列名大小写不敏感
        cols = ['XP', 'LISTENING_TOTAL', 'BONUS_DATE', 'BONUS_XP_TODAY']
        assert needs_xp_columns(cols) is False

    def test_full_users_schema_with_xp(self):
        # 完整 users 表结构（含 xp 四列 + avatar）→ 跳过迁移
        cols = [
            'user_id', 'username', 'password', 'level', 'create_time',
            'last_login', 'is_vip', 'is_admin', 'donate_amount',
            'album_count', 'token', 'avatar', 'xp', 'listening_total',
            'bonus_date', 'bonus_xp_today'
        ]
        assert needs_xp_columns(cols) is False
