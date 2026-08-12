# MusicRate\backend\tests\test_lyric_reference.py 平台参考歌词纯函数单测（v0.8.1 增补，零网络）
# 测试对象：backend/utils/lyric_reference.py
#   parse_lrc_text（各平台 LRC → 纯歌词文字）/ build_reference_text（参考段落格式）
#   / fetch_one_track（平台优先级逐级兜底，注入假 fetcher）/ fetch_all_references（逐曲编排 + 统计）
# 网络拉取函数（fetch_netease/fetch_kugou/fetch_qq）属 realdata，见 test_lyric_reference_realdata.py
import pytest

from backend.utils.lyric_reference import (
    build_reference_text,
    fetch_all_references,
    fetch_one_track,
    parse_lrc_text,
    pick_best_match,
)


class TestParseLrcText:
    def test_netease_lrc(self):
        raw = '[00:12.34]窗外的麻雀\n[00:16.70]在电线杆上多嘴\n[00:20.90]你说这一句很有夏天的感觉'
        assert parse_lrc_text(raw) == ['窗外的麻雀', '在电线杆上多嘴', '你说这一句很有夏天的感觉']

    def test_metadata_and_empty_lines_filtered(self):
        raw = '[ti:七里香]\n[ar:周杰伦]\n[00:12.34]窗外的麻雀\n\n[00:16.70]在电线杆上多嘴\n[by:somebody]'
        lines = parse_lrc_text(raw)
        assert lines == ['窗外的麻雀', '在电线杆上多嘴']
        assert '七里香' not in lines

    def test_storage_format_lines(self):
        # 平台返回偶有存储格式（无方括号）→ 同样可解析
        raw = '00:12.3 窗外的麻雀\n00:16.7 在电线杆上多嘴'
        assert parse_lrc_text(raw) == ['窗外的麻雀', '在电线杆上多嘴']

    def test_empty_and_none(self):
        assert parse_lrc_text('') == []
        assert parse_lrc_text(None) == []

    def test_pure_text_no_timestamps(self):
        # 无时间戳的纯文本 → 无有效歌词行 → []
        assert parse_lrc_text('窗外的麻雀\n在电线杆上多嘴') == []


class TestPickBestMatch:
    """候选歌曲匹配：曲名+歌手双重约束，防翻唱/remix 的错歌词混入参考"""

    @staticmethod
    def _c(name, artists, **kw):
        d = {'name': name, 'artists': artists}
        d.update(kw)
        return d

    def test_exact_title_and_artist_wins(self):
        cands = [
            self._c('红豆', ['王菲']),
            self._c('红豆 (Live)', ['王菲']),
            self._c('红豆', ['某翻唱']),
        ]
        best = pick_best_match(cands, '红豆', '王菲')
        assert best['name'] == '红豆' and best['artists'] == ['王菲']

    def test_remix_with_similar_artist_rejected(self):
        # 歌手名含目标子串但非精确（周杰伦- 等 remix）→ 拒绝，防止歌词错误
        cands = [self._c('晴天', ['周杰伦-', 'A-LNK'])]
        assert pick_best_match(cands, '晴天', '周杰伦') is None

    def test_cover_rejected_when_singer_provided(self):
        cands = [self._c('七里香', ['Xai小爱'])]
        assert pick_best_match(cands, '七里香', '周杰伦') is None

    def test_title_only_when_no_singer(self):
        cands = [self._c('七里香', [])]
        best = pick_best_match(cands, '七里香', '')
        assert best['name'] == '七里香'

    def test_bracket_suffix_title_match(self):
        cands = [self._c('红豆(现场版)', ['王菲'])]
        best = pick_best_match(cands, '红豆', '王菲')
        assert best['name'] == '红豆(现场版)'

    def test_multi_singer_split(self):
        cands = [self._c('屋顶', ['周杰伦'])]
        best = pick_best_match(cands, '屋顶', '周杰伦,温岚')
        assert best['name'] == '屋顶'

    def test_no_title_match_returns_none(self):
        cands = [self._c('惊鸿一面', ['许嵩'])]
        assert pick_best_match(cands, '七里香', '周杰伦') is None

    def test_empty_candidates(self):
        assert pick_best_match([], '七里香', '周杰伦') is None


class TestBuildReferenceText:
    def test_single_track(self):
        results = [{'index': 0, 'title': '七里香', 'text': ['窗外的麻雀', '在电线杆上多嘴'], 'source': '网易云'}]
        text = build_reference_text(results)
        assert '【第1首《七里香》- 来源：网易云】' in text
        assert '窗外的麻雀' in text
        assert '在电线杆上多嘴' in text

    def test_multi_track(self):
        results = [
            {'index': 0, 'title': '七里香', 'text': ['甲'], 'source': '网易云'},
            {'index': 1, 'title': '借口', 'text': ['乙'], 'source': '酷狗'},
        ]
        text = build_reference_text(results)
        assert '【第1首《七里香》' in text and '【第2首《借口》' in text
        assert '甲' in text and '乙' in text

    def test_empty_text_skipped(self):
        results = [{'index': 0, 'title': '七里香', 'text': [], 'source': '网易云'}]
        assert build_reference_text(results) == ''

    def test_empty_results(self):
        assert build_reference_text([]) == ''


class TestFetchOneTrack:
    """平台优先级逐级兜底：一个失败自动降级下一个，全失败返回 None"""

    @staticmethod
    def _fake(name, text=None, raise_exc=False):
        def fetcher(title, singer, timeout=5):
            if raise_exc:
                raise RuntimeError('network error')
            return {'text': text, 'source': name} if text else None
        return fetcher

    def test_first_success(self):
        n = self._fake('网易云', ['甲'])
        k = self._fake('酷狗', ['乙'])
        res = fetch_one_track('七里香', '周杰伦', fetchers=[n, k])
        assert res == {'text': ['甲'], 'source': '网易云'}

    def test_first_fails_falls_back(self):
        n = self._fake('网易云', None)  # 搜索无结果
        k = self._fake('酷狗', ['乙'])
        res = fetch_one_track('七里香', '周杰伦', fetchers=[n, k])
        assert res == {'text': ['乙'], 'source': '酷狗'}

    def test_first_raises_falls_back(self):
        n = self._fake('网易云', raise_exc=True)
        k = self._fake('酷狗', ['乙'])
        res = fetch_one_track('七里香', '周杰伦', fetchers=[n, k])
        assert res == {'text': ['乙'], 'source': '酷狗'}

    def test_all_fail_returns_none(self):
        res = fetch_one_track('七里香', '周杰伦', fetchers=[
            self._fake('网易云', None), self._fake('酷狗', None), self._fake('QQ音乐', None),
        ])
        assert res is None

    def test_default_fetchers_used_when_omitted(self, monkeypatch):
        # 未传 fetchers → 用默认平台顺序（网易云→酷狗→QQ）；替换 PLATFORM_FETCHERS 列表验证顺序（零网络）
        import backend.utils.lyric_reference as mod
        calls = []

        def make(name):
            def f(title, singer, timeout=5):
                calls.append(name)
                return None
            return f

        monkeypatch.setattr(mod, 'PLATFORM_FETCHERS', [make('netease'), make('kugou'), make('qq')])
        assert fetch_one_track('七里香', '周杰伦') is None
        assert calls == ['netease', 'kugou', 'qq']


class TestFetchAllReferences:
    def test_stats_and_text(self):
        def n(title, singer, timeout=5):
            return {'text': ['甲'], 'source': '网易云'}

        def k(title, singer, timeout=5):
            return None

        text, stats = fetch_all_references(['七里香', '借口'], '周杰伦', fetchers=[n, k])
        assert '甲' in text
        assert stats['total'] == 2
        assert stats['fetched'] == 2
        assert stats['sources']['网易云'] == 2

    def test_empty_tracks(self):
        text, stats = fetch_all_references([], '周杰伦')
        assert text == ''
        assert stats['total'] == 0 and stats['fetched'] == 0
