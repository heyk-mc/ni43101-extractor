"""
修订循环单元测试
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agents.critic_master import CriticismResult
from agents.extractor_agent import ExtractionResult
from core.revise_loop import (
    ReviseLoop,
    RevisionOutput,
    RevisionRound,
)


class TestRevisionRound:
    """测试修订轮次数据类"""

    def test_create_success(self):
        result = ExtractionResult(confidence=0.9, raw_extraction="test")
        round_data = RevisionRound(
            round_num=1, result=result, score=9, feedback="Excellent", success=True
        )

        assert round_data.round_num == 1
        assert round_data.success is True


class TestRevisionOutput:
    """测试修订输出数据类"""

    def test_create_running(self):
        output = RevisionOutput(final_result=None, status="running")

        assert output.status == "running"
        assert output.final_result is None

    def test_to_dict(self):
        result = ExtractionResult(confidence=0.9, raw_extraction="test")
        output = RevisionOutput(
            final_result=result,
            status="success",
            rounds=[
                RevisionRound(round_num=1, result=result, score=9, feedback="Good", success=True)
            ],
            total_rounds=1,
        )

        d = output.to_dict()
        assert d["status"] == "success"
        assert d["total_rounds"] == 1
        assert len(d["rounds"]) == 1


class TestReviseLoop:
    """测试修订循环控制器"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract = AsyncMock()
        return extractor

    @pytest.fixture
    def mock_critic(self):
        critic = Mock()
        critic.score = AsyncMock()
        return critic

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.max_revise_rounds = 3
        config.score_threshold = 8.0
        config.pdf_data_abs_path = "/tmp/pdfs"
        return config

    @pytest.fixture
    def revise_loop(self, mock_extractor, mock_critic, mock_config):
        return ReviseLoop(extractor=mock_extractor, critic=mock_critic, config=mock_config)

    @pytest.mark.asyncio
    async def test_run_success_first_round(self, revise_loop, mock_extractor, mock_critic):
        # 配置第一轮就达到阈值
        mock_extractor.extract.return_value = ExtractionResult(
            indicated={"ore_mt": 100.0},
            inferred={"ore_mt": 50.0},
            confidence=0.9,
            raw_extraction="test",
        )
        mock_critic.score.return_value = CriticismResult(score=9, feedback="Excellent extraction")

        with patch("core.revise_loop.extract_resources_from_pdf") as mock_parse:
            mock_parse.return_value = [
                Mock(resource_type="Indicated", ore_mt=100.0, grade_value=2.5, grade_unit="g/t Au")
            ]

            result = await revise_loop.run("test.pdf")

        assert result.status == "success"
        assert result.total_rounds == 1
        assert mock_extractor.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_run_success_after_revision(self, revise_loop, mock_extractor, mock_critic):
        # 配置前两轮失败，第三轮成功
        mock_critic.score.side_effect = [
            CriticismResult(score=5, feedback="Missing fields"),
            CriticismResult(score=6, feedback="Better but still incomplete"),
            CriticismResult(score=9, feedback="Good now"),
        ]

        mock_extractor.extract.return_value = ExtractionResult(
            indicated={"ore_mt": 100.0}, confidence=0.8, raw_extraction="test"
        )

        with patch("core.revise_loop.extract_resources_from_pdf") as mock_parse:
            mock_parse.return_value = [Mock()]
            result = await revise_loop.run("test.pdf")

        assert result.status == "success"
        assert result.total_rounds == 3
        assert mock_extractor.extract.call_count == 3

    @pytest.mark.asyncio
    async def test_run_abstain_max_rounds(self, revise_loop, mock_extractor, mock_critic):
        # 配置所有轮次都失败
        mock_critic.score.side_effect = [
            CriticismResult(score=4, feedback="Poor"),
            CriticismResult(score=5, feedback="Still poor"),
            CriticismResult(score=5, feedback="Still not good enough"),
        ]

        mock_extractor.extract.return_value = ExtractionResult(
            confidence=0.3, raw_extraction="test"
        )

        with patch("core.revise_loop.extract_resources_from_pdf") as mock_parse:
            mock_parse.return_value = [Mock()]
            result = await revise_loop.run("test.pdf")

        assert result.status == "abstain"
        assert result.total_rounds == 3
        # 检查是否包含"修订"或"阈值"关键词
        assert (
            "修订" in result.reason
            or "阈值" in result.reason
            or "max_rounds" in result.reason.lower()
        )

    @pytest.mark.asyncio
    async def test_run_no_tables_in_pdf(self, revise_loop, mock_extractor, mock_critic):
        # 配置 PDF 中没有表格
        with patch("core.revise_loop.extract_resources_from_pdf") as mock_parse:
            mock_parse.return_value = []
            result = await revise_loop.run("test.pdf")

        assert result.status == "abstain"
        assert "未检测到资源量表格" in result.reason
        mock_extractor.extract.assert_not_called()


class TestRunExtraction:
    """测试便捷提取函数"""

    @pytest.mark.asyncio
    async def test_run_extraction(self):
        # 这是一个集成测试的骨架
        # 实际需要配置 Mock 或使用测试 PDF
        pytest.skip("需要完整的 Mock 配置")

        with patch("core.revise_loop.ReviseLoop") as mock_loop_class:
            mock_loop = Mock()
            mock_loop.run = AsyncMock()
            mock_loop_class.return_value = mock_loop

            from core.revise_loop import run_extraction

            result = await run_extraction("test.pdf")

            mock_loop.run.assert_called_once()
