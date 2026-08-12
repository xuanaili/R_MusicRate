# MusicRate\backend\tests\test_lyric_reference_realdata.py 平台参考歌词拉取 realdata 测试（需真实网络）
# 真实请求网易云/酷狗/QQ 非官方接口，验证「搜索 → 匹配 → 拉取 → 解析」链路
# 实测现状（2026-08-12）：
#   - 网易云：非受限歌手（王菲/陈奕迅）可拉到原始版；受限歌手（周杰伦等）搜不到原始版 → 返回 None
#   - 酷狗：songsearch_v2 搜索可用；歌词接口（krcs）反爬空响应 → fetch_kugou 返回 None（此处只验证搜索层）
#   - QQ：搜索 + 歌词全链路可用（可靠兜底层）
# 运行：portable\python\python.exe -m pytest -m realdata backend/tests/test_lyric_reference_realdata.py
import pytest

from backend.utils.lyric_reference import (
    fetch_all_references,
    fetch_netease,
    fetch_qq,
    pick_best_match,
    search_kugou,
)

pytestmark = pytest.mark.realdata


class TestFetchPlatform:
    def test_netease_known_song(self):
        # 非受限歌手：王菲《红豆》网易云可搜到原始版
        res = fetch_netease('红豆', '王菲')
        assert res is not None, '网易云拉取失败（搜索无结果/接口变动/网络）'
        assert res['source'] == '网易云'
        assert len(res['text']) > 5
        assert '好好的感受' in ' '.join(res['text'])

    def test_qq_known_song(self):
        # QQ 全链路：周杰伦《七里香》（网易云受限场景的可靠兜底）
        res = fetch_qq('七里香', '周杰伦')
        assert res is not None, 'QQ 拉取失败（搜索无结果/需登录/接口变动/网络）'
        assert res['source'] == 'QQ音乐'
        assert len(res['text']) > 5
        assert '窗外的麻雀' in ' '.join(res['text'])

    def test_kugou_search_layer(self):
        # 酷狗歌词接口反爬，但搜索层可用：songsearch_v2 能找到周杰伦《七里香》
        cands = search_kugou('七里香', '周杰伦')
        assert len(cands) > 0, '酷狗搜索失败（接口变动/网络）'
        best = pick_best_match(cands, '七里香', '周杰伦')
        assert best is not None, '酷狗搜索结果未匹配到《七里香》'
        assert best['name'] == '七里香'
        assert best['artists'] == ['周杰伦']


class TestFetchAll:
    """整专逐曲编排：至少拉到 1 首，命中知名单曲文本"""

    def test_known_album_tracks(self):
        text, stats = fetch_all_references(['红豆', '容易受伤的女人'], '王菲')
        assert stats['total'] == 2
        assert stats['fetched'] >= 1, f'两曲全失败，stats={stats}'
        assert '红豆' in text
        assert stats['sources'], f'sources 不应为空，stats={stats}'
