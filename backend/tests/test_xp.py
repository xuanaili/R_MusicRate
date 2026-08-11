# MusicRate\backend\tests\test_xp.py 经验来源常量纯逻辑单测（v0.7.2，零 DB 依赖）
# 测试对象：backend/utils/xp.py
# 覆盖：来源枚举 / 加分来源集合（不含收听）/ 来源中文 label
import pytest

from backend.utils.xp import (
    BONUS_SOURCES,
    SOURCE_LABELS,
    XP_COMMENT,
    XP_LISTENING,
    XP_RATING,
    XP_REVIEW,
)


class TestXpConstants:
    """经验来源常量：listening 无上限，rating/review/comment 为加分来源（受每日上限 100 约束）"""

    def test_source_constants(self):
        assert XP_LISTENING == 'listening'
        assert XP_RATING == 'rating'
        assert XP_REVIEW == 'review'
        assert XP_COMMENT == 'comment'

    def test_bonus_sources_exclude_listening(self):
        # 加分来源仅评分/听后感/评论（收听无上限、不走 bonus 上限，必须排除）
        assert BONUS_SOURCES == (XP_RATING, XP_REVIEW, XP_COMMENT)
        assert XP_LISTENING not in BONUS_SOURCES

    def test_source_labels_complete(self):
        # 每个来源都有中文 label（前端弹窗展示用），且含全部四个来源
        for src in BONUS_SOURCES + (XP_LISTENING,):
            assert src in SOURCE_LABELS
        assert SOURCE_LABELS[XP_LISTENING] == '听歌'
        assert SOURCE_LABELS[XP_RATING] == '评分'
        assert SOURCE_LABELS[XP_REVIEW] == '听后感'
        assert SOURCE_LABELS[XP_COMMENT] == '评论'
