"""
CriticMaster Agent 单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from agents.critic_master import (
    CriticMasterAgent,
    CriticismResult,
)
from agents.extractor_agent import ExtractionResult


class TestCriticismResult:
    """测试 CriticismResult 数据类"""

    def test_create_default(self):
        result = CriticismResult(
            score=7,
            feedback="Good extraction"
        )

        assert result.score == 7
        assert result.issues == []

    def test_to_dict(self):
        result = CriticismResult(
            score=8,
            feedback="Good",
            issues=["Missing unit"],
            suggestion="Add unit"
        )

        d = result.to_dict()
        assert d["score"] == 8
        assert d["issues"] == ["Missing unit"]


class TestCriticMasterAgent:
    """测试 CriticMasterAgent"""

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.dashscope_api_key = "test-key"
        config.qwen_model = "qwen-test"
        return config

    @pytest.fixture
    def critic(self, mock_config):
        return CriticMasterAgent(config=mock_config)

    def test_init(self, mock_config):
        agent = CriticMasterAgent(config=mock_config)
        assert agent.model == mock_config.qwen_model
        assert agent.api_key == mock_config.dashscope_api_key

    def test_build_prompt(self, critic):
        extraction_result = ExtractionResult(
            indicated={"ore_mt": 100.0, "grade_value": 2.5},
            inferred={"ore_mt": 50.0},
            confidence=0.8,
            raw_extraction="Test extraction output"
        )

        prompt = critic.build_prompt(extraction_result)

        assert "Indicated Resources" in prompt
        assert "评分标准" in prompt or "评分" in prompt
        assert "100.0" in prompt
        assert "50.0" in prompt

    def test_build_prompt_with_history(self, critic):
        extraction_result = ExtractionResult(
            confidence=0.7,
            raw_extraction="test"
        )
        history = [
            {"score": 5, "feedback": "Missing grade", "suggestion": "Add grade value"}
        ]

        prompt = critic.build_prompt(extraction_result, history)

        assert "历史修订" in prompt
        assert "Missing grade" in prompt

    def test_parse_criticism_output_json(self, critic):
        raw_output = '''```json
{
    "score": 8,
    "feedback": "Good extraction",
    "issues": ["Minor formatting"],
    "suggestion": "Improve formatting"
}
```'''

        result = critic._parse_criticism_output(raw_output)

        assert result.score == 8
        assert "Good" in result.feedback

    def test_parse_criticism_output_no_code_block(self, critic):
        raw_output = '{"score": 7, "feedback": "Good"}'

        result = critic._parse_criticism_output(raw_output)

        assert result.score == 7

    def test_parse_criticism_output_invalid_json(self, critic):
        raw_output = "Invalid JSON output with score: 6"

        result = critic._parse_criticism_output(raw_output)

        assert result.score == 6  # 从文本中提取的分数

    def test_mock_score_both_missing(self, critic):
        extraction_result = ExtractionResult(
            indicated=None,
            inferred=None,
            confidence=0.5,
            raw_extraction="test"
        )

        result = critic._mock_score(extraction_result)

        assert result.score <= 3
        assert "Indicated 和 Inferred 均为空" in result.issues

    def test_mock_score_indicated_missing(self, critic):
        extraction_result = ExtractionResult(
            indicated=None,
            inferred={"ore_mt": 50.0},
            confidence=0.7,
            raw_extraction="test"
        )

        result = critic._mock_score(extraction_result)

        assert result.score <= 5
        assert "Indicated 为空" in result.issues

    def test_mock_score_inferred_missing(self, critic):
        extraction_result = ExtractionResult(
            indicated={"ore_mt": 100.0},
            inferred=None,
            confidence=0.7,
            raw_extraction="test"
        )

        result = critic._mock_score(extraction_result)

        assert result.score <= 7
        assert "Inferred 为空" in result.issues

    def test_mock_score_fields_missing(self, critic):
        extraction_result = ExtractionResult(
            indicated={"ore_mt": 100.0},  # 只有 ore_mt
            inferred={"ore_mt": 50.0},
            confidence=0.9,
            raw_extraction="test"
        )

        result = critic._mock_score(extraction_result)

        assert result.score <= 7
        assert any("缺失" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_score_api_error(self, critic):
        extraction_result = ExtractionResult(
            confidence=0.5,
            raw_extraction="test"
        )

        # 模拟 API 调用失败
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = Exception("Connection error")

            result = await critic.score(extraction_result)

            # 应该降级到 mock_score
            assert result.score <= 5

    @pytest.mark.asyncio
    async def test_score_no_api_key(self, critic):
        critic.api_key = None

        extraction_result = ExtractionResult(
            indicated={"ore_mt": 100.0},
            confidence=0.8,
            raw_extraction="test"
        )

        result = await critic.score(extraction_result)

        # 应该使用 mock_score
        assert result.score is not None


class TestGetCriticMasterAgent:
    """测试单例获取函数"""

    def test_get_critic_master_agent_singleton(self):
        from agents.critic_master import (
            get_critic_master_agent,
            _critic_master_agent
        )

        # 重置单例
        import agents.critic_master as cm
        cm._critic_master_agent = None

        agent1 = get_critic_master_agent()
        agent2 = get_critic_master_agent()

        assert agent1 is agent2
