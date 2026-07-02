"""
Extractor Agent 单元测试
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from agents.extractor_agent import (
    ExtractorAgent,
    ExtractionResult,
)


class TestExtractionResult:
    """测试 ExtractionResult 数据类"""

    def test_create_default(self):
        result = ExtractionResult(
            confidence=0.8,
            raw_extraction="test"
        )
        assert result.indicated is None
        assert result.inferred is None
        assert result.confidence == 0.8

    def test_to_dict(self):
        result = ExtractionResult(
            indicated={"ore_mt": 100.0},
            inferred={"ore_mt": 50.0},
            confidence=0.9,
            source_pages=[1, 2],
            raw_extraction="test output"
        )
        d = result.to_dict()
        assert d["indicated"]["ore_mt"] == 100.0
        assert d["inferred"]["ore_mt"] == 50.0
        assert d["confidence"] == 0.9


class TestExtractorAgent:
    """测试 ExtractorAgent"""

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.anthropic_api_key = "test-key"
        config.anthropic_model = "claude-test"
        return config

    @pytest.fixture
    def extractor(self, mock_config):
        with patch('agents.extractor_agent.Anthropic'):
            return ExtractorAgent(config=mock_config)

    def test_init(self, mock_config):
        with patch('agents.extractor_agent.Anthropic') as mock_anthropic:
            agent = ExtractorAgent(config=mock_config)
            assert agent.model == mock_config.anthropic_model
            mock_anthropic.assert_called_once_with(api_key=mock_config.anthropic_api_key)

    def test_build_prompt(self, extractor):
        pdf_text = "Test PDF content with Indicated Resources 100 Mt"
        prompt = extractor.build_prompt(pdf_text)

        assert "Indicated Resources" in prompt
        assert "Inferred Resources" in prompt
        assert "JSON" in prompt
        assert pdf_text in prompt

    def test_build_prompt_with_few_shot(self, extractor):
        few_shot = [
            {
                "input_summary": "Example PDF",
                "output": {"indicated": {"ore_mt": 50.0}}
            }
        ]
        prompt = extractor.build_prompt("Test content", few_shot)

        assert "示例" in prompt or "Example" in prompt

    def test_parse_extraction_output_json(self, extractor):
        raw_output = '''```json
{
    "indicated": {"ore_mt": 100.0, "grade_value": 2.5},
    "inferred": {"ore_mt": 50.0},
    "confidence": 0.9,
    "source_pages": [1, 2]
}
```'''
        result = extractor._parse_extraction_output(raw_output)

        assert result.indicated is not None
        assert result.indicated["ore_mt"] == 100.0
        assert result.confidence == 0.9

    def test_parse_extraction_output_no_code_block(self, extractor):
        raw_output = '{"indicated": {"ore_mt": 100.0}, "confidence": 0.8}'
        result = extractor._parse_extraction_output(raw_output)

        assert result.indicated is not None
        assert result.confidence == 0.8

    def test_parse_extraction_output_invalid_json(self, extractor):
        raw_output = "Invalid JSON output"
        result = extractor._parse_extraction_output(raw_output)

        assert result.confidence == 0.3
        assert "JSON 解析失败" in result.notes

    @pytest.mark.asyncio
    async def test_extract_success(self, extractor):
        with patch.object(extractor.client.messages, 'create') as mock_create:
            mock_create.return_value = Mock(
                content=[Mock(text='{"indicated": {"ore_mt": 100.0}, "confidence": 0.9}')]
            )

            result = await extractor.extract("Test PDF content")

            assert result.indicated is not None
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_with_history(self, extractor):
        history = [
            {"score": 5, "feedback": "Missing grade value"}
        ]

        with patch.object(extractor.client.messages, 'create') as mock_create:
            mock_create.return_value = Mock(
                content=[Mock(text='{"indicated": {"ore_mt": 100.0}, "confidence": 0.8}')]
            )

            result = await extractor.extract("Test content", history=history)

            assert result is not None
            # 验证 history 被加入 prompt
            call_args = mock_create.call_args
            assert "历史修订" in call_args[1]["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_extract_api_error(self, extractor):
        with patch.object(extractor.client.messages, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")

            result = await extractor.extract("Test content")

            assert result.confidence == 0.1
            assert "提取失败" in result.notes


class TestTablesToText:
    """测试表格转文本"""

    @pytest.fixture
    def extractor(self):
        with patch('agents.extractor_agent.Anthropic'):
            return ExtractorAgent()

    def test_tables_to_text(self, extractor):
        from core.pdf_parser import ResourceTable

        tables = [
            ResourceTable(
                resource_type="Indicated",
                ore_mt=100.5,
                grade_value=2.5,
                grade_unit="g/t Au",
                source_page=5
            )
        ]

        text = extractor._tables_to_text(tables)

        assert "Indicated" in text
        assert "100.5" in text
        assert "2.5" in text
        assert "页码：5" in text
