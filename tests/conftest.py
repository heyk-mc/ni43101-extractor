"""
Pytest 测试配置文件

定义共享 fixture 和测试配置。
"""

from unittest.mock import Mock

import pytest


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """创建测试数据目录"""
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture
def sample_pdf_path(test_data_dir):
    """
    创建模拟 PDF 文件路径

    注意：实际测试中需要创建真实的 PDF 文件
    或者使用 Mock 来绕过 PDF 解析
    """
    pdf_path = test_data_dir / "sample.pdf"
    # 这里可以创建一个简单的 PDF 用于测试
    # 或者返回 None 并在测试中使用 Mock
    return str(pdf_path)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock 环境变量"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("QWEN_MODEL", "qwen-test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MAX_REVISE_ROUNDS", "3")
    monkeypatch.setenv("SCORE_THRESHOLD", "8")


@pytest.fixture
def sample_resource_table():
    """创建示例 ResourceTable"""
    from core.pdf_parser import ResourceTable

    return ResourceTable(
        resource_type="Indicated",
        ore_mt=100.5,
        grade_value=2.5,
        grade_unit="g/t Au",
        metal_oz=8000.0,
        commodity="Au",
        source_page=5,
        raw_text="Sample table data",
        confidence=0.9,
    )


@pytest.fixture
def sample_extraction_result():
    """创建示例 ExtractionResult"""
    from agents.extractor_agent import ExtractionResult

    return ExtractionResult(
        indicated={"ore_mt": 100.5, "grade_value": 2.5, "grade_unit": "g/t Au", "metal_oz": 8000.0},
        inferred={"ore_mt": 50.2, "grade_value": 2.1, "grade_unit": "g/t Au", "metal_oz": 3500.0},
        confidence=0.9,
        source_pages=[5, 6],
        raw_extraction="Sample extraction output",
        notes="High quality extraction",
    )


@pytest.fixture
def sample_ground_truth():
    """创建示例 ground truth"""
    return {
        "indicated": {
            "ore_mt": 100.0,
            "grade_value": 2.5,
            "grade_unit": "g/t Au",
            "metal_oz": 8000.0,
        },
        "inferred": {
            "ore_mt": 50.0,
            "grade_value": 2.1,
            "grade_unit": "g/t Au",
            "metal_oz": 3500.0,
        },
    }


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic 客户端"""
    with pytest.importorskip("anthropic"):
        from unittest.mock import Mock, patch

        mock_client = Mock()
        mock_client.messages.create = Mock()

        with patch("anthropic.Anthropic", return_value=mock_client):
            yield mock_client


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX 客户端"""
    from unittest.mock import AsyncMock, patch

    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"score": 8, "feedback": "Good"}'}}]
    }
    mock_response.raise_for_status = Mock()

    mock_async_client = Mock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        yield mock_async_client
