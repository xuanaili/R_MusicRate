# MusicRate\backend\tests\test_deepseek_correct.py DeepSeek 歌词校正纯函数单测（v0.8.1 P2，零网络）
# 测试对象：backend/utils/deepseek_correct.py 的纯逻辑部分
#   （_call_chat 真实 API 属 realdata，此处用 monkeypatch 模拟返回，验证校正管线与回退）
# 覆盖：prompt 构造 / 返回解析（时间戳前缀、代码块）/ difflib 保时间戳对齐（equal/replace/delete/insert）/
#       correct_lyric 无 key 跳过、异常回退、成功校正（时间戳保留）
import pytest

from backend.utils.deepseek_correct import (
    align_back_timestamps,
    build_correct_prompt,
    correct_lyric,
    parse_corrected_lines,
)


class TestBuildCorrectPrompt:
    def test_prompt_contains_lyric_and_constraints(self):
        prompt = build_correct_prompt('00:00 某夜你离开\n00:10 某天你走来')
        assert '00:00 某夜你离开' in prompt
        assert '00:10 某天你走来' in prompt
        # 强约束：不改时间戳、不增删行、逐行对应
        assert '时间戳' in prompt
        assert '不增删行' in prompt or '不要增加或删除行' in prompt


class TestParseCorrectedLines:
    def test_lines_with_timestamp_prefix(self):
        # 模型遵守格式：每行带时间戳 → 只取文本
        raw = '00:00 某夜你离开\n00:10 某天你走来'
        assert parse_corrected_lines(raw) == ['某夜你离开', '某天你走来']

    def test_lines_without_timestamp(self):
        # 模型只输出文本 → 整行作为文本
        raw = '某夜你离开\n某天你走来'
        assert parse_corrected_lines(raw) == ['某夜你离开', '某天你走来']

    def test_code_block_wrapped(self):
        raw = '```\n00:00 第一句\n00:05 第二句\n```'
        assert parse_corrected_lines(raw) == ['第一句', '第二句']

    def test_blank_lines_and_markdown_stripped(self):
        raw = '00:00 第一句\n\n好的，以下是校对结果：\n00:05 第二句'
        # 「好的，以下是校对结果：」无时间戳 → 仍作为一行（交由对齐处理；此场景少见）
        assert parse_corrected_lines(raw) == ['第一句', '好的，以下是校对结果：', '第二句']

    def test_empty_input(self):
        assert parse_corrected_lines('') == []
        assert parse_corrected_lines(None) == []


class TestAlignBackTimestamps:
    """difflib 保时间戳对齐：校正行映射回 anchor 时间戳"""

    def _anchor(self, times, texts):
        return [{'time': t, 'time_str': f'00:{int(t):02d}', 'text': s} for t, s in zip(times, texts)]

    def test_equal_lines(self):
        anchor = self._anchor([0.0, 10.0, 20.0], ['某夜你離開', '某天你走來', '我們都在'])
        corr = ['某夜你离开', '某天你走来', '我们都在']
        out = align_back_timestamps(anchor, corr)
        assert out == [
            {'time': 0.0, 'text': '某夜你离开'},
            {'time': 10.0, 'text': '某天你走来'},
            {'time': 20.0, 'text': '我们都在'},
        ]

    def test_replace_same_count_keeps_timestamps(self):
        # 同音错字替换，行数不变 → 时间戳原样保留
        anchor = self._anchor([0.0, 10.0], ['同音錯字', '另一句'])
        corr = ['同音错字', '另一句']
        out = align_back_timestamps(anchor, corr)
        assert [x['time'] for x in out] == [0.0, 10.0]
        assert [x['text'] for x in out] == corr

    def test_replace_fewer_corrected_lines(self):
        # 校正后行数变少（删行）：剩余行对齐到前 N 个 anchor 时间戳
        anchor = self._anchor([0.0, 10.0, 20.0], ['甲', '乙', '丙'])
        corr = ['甲', '丙']
        out = align_back_timestamps(anchor, corr)
        # 甲=0.0 丙=20.0（difflib 匹配到的）
        assert [x['time'] for x in out] == [0.0, 20.0]

    def test_replace_more_corrected_lines(self):
        # 校正后行数变多（增行）：多出的行沿用最后一个 anchor 时间戳
        anchor = self._anchor([0.0, 10.0], ['甲', '乙'])
        corr = ['甲', '乙', '新增一行']
        out = align_back_timestamps(anchor, corr)
        assert len(out) == 3
        assert out[0] == {'time': 0.0, 'text': '甲'}
        assert out[1] == {'time': 10.0, 'text': '乙'}
        # 新增行沿用前一行 anchor 时间戳
        assert out[2] == {'time': 10.0, 'text': '新增一行'}

    def test_delete_dropped(self):
        # 校正删除了行 → 该 anchor 行不再输出
        anchor = self._anchor([0.0, 10.0, 20.0], ['甲', '乙', '丙'])
        corr = ['甲', '乙']  # 丙被删
        out = align_back_timestamps(anchor, corr)
        assert [x['text'] for x in out] == ['甲', '乙']

    def test_insert_at_start(self):
        # 开头新增行 → 沿用第一行 anchor 时间戳
        anchor = self._anchor([0.0, 10.0], ['甲', '乙'])
        corr = ['开场白', '甲', '乙']
        out = align_back_timestamps(anchor, corr)
        assert out[0] == {'time': 0.0, 'text': '开场白'}
        assert out[1] == {'time': 0.0, 'text': '甲'}

    def test_empty_corrected_returns_empty(self):
        assert align_back_timestamps(self._anchor([0.0], ['甲']), []) == []


class TestCorrectLyric:
    """correct_lyric 总入口：无 key 跳过 / 异常回退 / 成功校正"""

    def _monkey_call(self, monkeypatch, response_text):
        """把 _call_chat 替换为固定返回（或抛异常），并捕获调用参数"""
        import backend.utils.deepseek_correct as mod
        captured = {}

        def fake(api_key, prompt, timeout=60):
            captured['api_key'] = api_key
            captured['prompt'] = prompt
            if callable(response_text):
                return response_text()
            return response_text

        monkeypatch.setattr(mod, '_call_chat', fake)
        return captured

    def test_no_key_skips(self, monkeypatch):
        monkeypatch.delattr('backend.utils.deepseek_correct._call_chat', raising=False)
        text, meta = correct_lyric('00:00 某夜你離開', api_key=None)
        assert text == '00:00 某夜你離開'
        assert meta['corrected'] is False
        assert '未配置' in meta['reason']

    def test_empty_lyric_skips(self, monkeypatch):
        text, meta = correct_lyric('', api_key='key')
        assert text == ''
        assert meta['corrected'] is False

    def test_api_error_falls_back(self, monkeypatch):
        self._monkey_call(monkeypatch, response_text=lambda: (_ for _ in ()).throw(RuntimeError('网络错误')))
        text, meta = correct_lyric('00:00 某夜你離開', api_key='key')
        assert text == '00:00 某夜你離開'  # 回退原稿
        assert meta['corrected'] is False
        assert 'DeepSeek 调用失败' in meta['reason']

    def test_success_keeps_timestamps(self, monkeypatch):
        captured = self._monkey_call(
            monkeypatch,
            response_text='00:00 某夜你离开\n00:10 我们终会相遇',
        )
        text, meta = correct_lyric('00:00 某夜你離開\n00:10 我們終會相遇', api_key='key')
        assert meta['corrected'] is True
        assert text == '00:00 某夜你离开\n00:10 我们终会相遇'
        assert meta['anchor_lines'] == 2
        assert meta['corrected_lines'] == 2
        # 校正 prompt 已带歌词草稿
        assert '某夜你離開' in captured['prompt']

    def test_success_with_code_block_wrap(self, monkeypatch):
        # 模型返回包 ``` 代码块 → 解析后仍成功
        self._monkey_call(monkeypatch, response_text='```\n00:00 第一句\n```')
        text, meta = correct_lyric('00:00 第一句', api_key='key')
        assert meta['corrected'] is True
        assert text == '00:00 第一句'

    def test_success_with_inserted_line(self, monkeypatch):
        # 模型增行 → difflib 对齐回锚定时间戳，仍落库
        self._monkey_call(monkeypatch, response_text='00:00 甲\n00:10 乙\n00:10 新增')
        text, meta = correct_lyric('00:00 甲\n00:10 乙', api_key='key')
        assert meta['corrected'] is True
        # 增行沿用前一行时间戳
        assert text == '00:00 甲\n00:10 乙\n00:10 新增'
