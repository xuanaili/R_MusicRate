# MusicRate\backend\tests\test_ai_context.py AI 助手上下文组装纯函数单测（v0.8.1 P5，零 DB / 网络依赖）
# 测试对象：backend/utils/ai_context.py
#   - _truncate：截断长文本
#   - format_score：my_score 数组 → 你的评分文本
#   - parse_feelings：review（dict feelings / 旧数组）→ 听后感列表
#   - format_own_feelings：听后感 → 文本
#   - format_tempo：album_tempo JSON → 单曲节奏文本
#   - format_album_lyric：整轨歌词 → 整张专辑歌词文本（按 tracks_time 分曲标注）
#   - format_comments / format_reviews：平台评论 / 全网听后感 → 文本
#   - build_system_prompt：分层组装 system prompt（数据有→含段落，无→不出现空段落）
from backend.utils.ai_context import (
    COMMENT_LIMIT,
    HISTORY_LIMIT,
    REVIEW_PER_USER,
    REVIEW_TOTAL_CAP,
    _truncate,
    build_system_prompt,
    format_album_lyric,
    format_comments,
    format_own_feelings,
    format_reviews,
    format_score,
    format_tempo,
    parse_feelings,
)


# ==================== _truncate ====================

class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate('你好世界', 100) == '你好世界'

    def test_empty_text_unchanged(self):
        assert _truncate('', 100) == ''
        assert _truncate(None, 100) == ''
        assert _truncate('   ', 100) == ''

    def test_long_text_truncated_with_ellipsis(self):
        assert _truncate('A' * 10, 5) == 'AAAAA…'


# ==================== format_score ====================

class TestFormatScore:
    def test_empty_returns_empty(self):
        assert format_score(None) == ''
        assert format_score([]) == ''

    def test_album_score_and_tracks(self):
        # my_score[0] = 专辑整体评分，其余为单曲评分
        assert format_score([85, 88, 90, 0]) == '专辑整体评分：85分；单曲评分：[88, 90, 0]（0 表示未评分）'

    def test_only_album_score(self):
        assert format_score([80]) == '专辑整体评分：80分'

    def test_only_tracks_no_album_score(self):
        assert format_score([0, 70, 75]) == '单曲评分：[70, 75]（0 表示未评分）'


# ==================== parse_feelings ====================

class TestParseFeelings:
    def test_dict_with_feelings(self):
        feelings = [{'content': '好', 'create_time': '2026-08-12'}]
        assert parse_feelings({'feelings': feelings}) == feelings

    def test_legacy_array(self):
        feelings = [{'content': '旧格式'}]
        assert parse_feelings(feelings) == feelings

    def test_none_empty(self):
        assert parse_feelings(None) == []
        assert parse_feelings({}) == []
        assert parse_feelings([]) == []

    def test_ignore_non_dict_entries(self):
        assert parse_feelings([{'content': 'a'}, 'x', 1]) == [{'content': 'a'}]


# ==================== format_own_feelings ====================

class TestFormatOwnFeelings:
    def test_empty_returns_empty(self):
        assert format_own_feelings([]) == ''
        assert format_own_feelings(None) == ''

    def test_numbered_lines(self):
        feelings = [{'content': '第一感受'}, {'content': '第二感受'}]
        assert format_own_feelings(feelings) == '1. 第一感受\n2. 第二感受'

    def test_with_time_and_rating(self):
        feelings = [{'content': '好听', 'create_time': '2026-08-12 10:00', 'my_score': 90}]
        assert format_own_feelings(feelings) == '1. 好听（当时评分 90，2026-08-12 10:00）'

    def test_blank_content_skipped(self):
        assert format_own_feelings([{'content': '  '}]) == ''


# ==================== format_tempo ====================

class TestFormatTempo:
    def test_empty_returns_empty(self):
        assert format_tempo(None) == ''
        assert format_tempo({}) == ''

    def test_with_track_names(self):
        tempo = {
            'track_tempos': [120.0, 0.0, 90.0],
            'avg_bpm': 105.0, 'min_bpm': 90.0, 'max_bpm': 120.0,
        }
        out = format_tempo(tempo, ['春日光', '无边界', '花与树'])
        assert '春日光：120.0 BPM' in out
        assert '无边界' not in out  # 0 BPM（无法测拍）不列出
        assert '花与树：90.0 BPM' in out
        assert '整专平均：105.0 BPM（区间 90.0~120.0 BPM）' in out

    def test_without_track_names_uses_number(self):
        tempo = {'track_tempos': [120.0], 'avg_bpm': 120.0, 'min_bpm': 120.0, 'max_bpm': 120.0}
        out = format_tempo(tempo)
        assert '单曲1：120.0 BPM' in out

    def test_all_zero_returns_empty(self):
        assert format_tempo({'track_tempos': [0.0, 0.0], 'avg_bpm': 0.0}) == ''


# ==================== format_album_lyric ====================

class TestFormatAlbumLyric:
    def test_empty_returns_empty(self):
        assert format_album_lyric('') == ''
        assert format_album_lyric(None) == ''

    def test_no_tracks_time_continuous_text(self):
        # 无单曲边界 → 整轨连续文本（去时间戳），不标曲目
        lyric = '00:00.5 第一首歌词\n00:02.0 第一首续\n00:06.0 第二首歌词'
        assert format_album_lyric(lyric) == '第一首歌词\n第一首续\n第二首歌词'

    def test_group_by_tracks_time_with_names(self):
        # 整轨歌词：0-5s 第一首、5-10s 第二首 → 按曲名分块
        lyric = '00:00.5 第一首歌词\n00:02.0 第一首续\n00:06.0 第二首歌词\n00:08.0 第二首续'
        out = format_album_lyric(lyric, tracks=['春日光', '花与树'], tracks_time=[0, 5])
        assert '《春日光》\n第一首歌词\n第一首续' in out
        assert '《花与树》\n第二首歌词\n第二首续' in out

    def test_group_without_names_uses_number(self):
        lyric = '00:01.0 词A\n00:06.0 词B'
        out = format_album_lyric(lyric, tracks=[], tracks_time=[0, 5])
        assert '《单曲1》\n词A' in out
        assert '《单曲2》\n词B' in out

    def test_invalid_text_returns_empty(self):
        # 无时间戳纯文本无法解析 → ''
        assert format_album_lyric('随便写的文字，没有时间戳') == ''

    def test_long_lyric_truncated_to_cap(self):
        # 超长整轨 → 截断保留开头（防上下文爆炸）；时间戳用 mm:ss 分/秒生成（避免超过 99 秒格式失配）
        lyric = '\n'.join(f'{i // 60:02d}:{i % 60:02d}.0 第{i}句歌词' for i in range(800))
        out = format_album_lyric(lyric, tracks_time=[])
        assert len(out) <= 4001
        assert '…' in out
        assert out.startswith('第0句歌词')


# ==================== format_comments / format_reviews ====================

class TestFormatComments:
    def test_empty_returns_empty(self):
        assert format_comments([]) == ''
        assert format_comments(None) == ''

    def test_lines_with_username(self):
        out = format_comments([{'username': '小明', 'content': '太好听了'}])
        assert out == '- 小明：太好听了'

    def test_long_content_truncated(self):
        out = format_comments([{'username': '小明', 'content': 'A' * 200}])
        assert out == f'- 小明：{"A" * 150}…'


class TestFormatReviews:
    def test_empty_returns_empty(self):
        assert format_reviews([]) == ''

    def test_lines_with_username(self):
        out = format_reviews([{'username': '阿飞', 'content': '神专'}])
        assert out == '- 阿飞：神专'


# ==================== build_system_prompt ====================

class TestBuildSystemPrompt:
    def test_present_sections(self):
        prompt = build_system_prompt(
            album_name='春日光', singer='苏打绿',
            album_intro='一首关于春天的专辑', tracks=['春日光', '花与树'],
            release_year=2009, main_type='Pop【流行】',
            own_tags=['Spring【春天】'], own_score='专辑整体评分：85分',
            own_feelings=[{'content': '适合春天听'}],
            singer_intro='台湾乐团', tempo_text='春日光：120.0 BPM',
            album_lyric_text='《春日光》\n第一首歌词', comments_text='- 小明：好听',
            other_reviews_text='- 阿飞：神专',
        )
        assert '你是MusicRate的AI音乐助手' in prompt
        for section in ['【专辑信息】', '【歌手信息】', '【你的评分】', '【你的听后感】',
                        '【你的标签】', '【单曲节奏 BPM】', '【专辑歌词】',
                        '【平台评论】', '【其他用户听后感精选】']:
            assert section in prompt, section
        assert '不要编造' in prompt  # 结尾强约束

    def test_empty_data_omits_sections(self):
        prompt = build_system_prompt(album_name='春日光', singer='苏打绿')
        for section in ['【歌手信息】', '【你的评分】', '【你的听后感】', '【你的标签】',
                        '【单曲节奏 BPM】', '【专辑歌词】', '【平台评论】', '【其他用户听后感精选】']:
            assert section not in prompt, section
        # 专辑信息即使只有名称也存在
        assert '【专辑信息】' in prompt


# ==================== 常量对齐 ====================

class TestConstants:
    def test_limits_match_readme(self):
        assert COMMENT_LIMIT == 15
        assert REVIEW_TOTAL_CAP == 20
        assert REVIEW_PER_USER == 3
        assert HISTORY_LIMIT == 20
