"""
PDF 解析模块单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from core.pdf_parser import (
    extract_tables_pdfplumber,
    extract_tables_pypdf,
    is_resource_table,
    parse_number,
    parse_table,
    detect_resource_type,
    detect_commodity,
    extract_grade_unit,
    calculate_confidence,
    ResourceTable,
)


class TestIsResourceTable:
    """测试资源量表格检测"""

    def test_detects_indicated_table(self):
        table = [
            ["Resource Category", "Tonnes", "Grade (g/t Au)", "Metal (oz)"],
            ["Indicated", "100", "2.5", "8000"],
        ]
        assert is_resource_table(table) is True

    def test_detects_inferred_table(self):
        table = [
            ["Category", "Million Tonnes", "Grade"],
            ["Inferred Resources", "50", "1.8"],
        ]
        assert is_resource_table(table) is True

    def test_rejects_non_resource_table(self):
        table = [
            ["Name", "Age", "City"],
            ["Alice", "30", "New York"],
        ]
        assert is_resource_table(table) is False

    def test_empty_table(self):
        assert is_resource_table([]) is False


class TestParseNumber:
    """测试数字解析"""

    def test_parse_simple_number(self):
        assert parse_number("123.45") == 123.45

    def test_parse_thousands_separator(self):
        assert parse_number("1,234.56") == 1234.56

    def test_parse_with_million(self):
        assert parse_number("100 Million") == 100.0

    def test_parse_percentage(self):
        assert parse_number("2.5%") == 2.5

    def test_parse_none(self):
        assert parse_number("") is None
        assert parse_number("N/A") is None


class TestDetectResourceType:
    """测试资源类型检测"""

    def test_detect_indicated(self):
        assert detect_resource_type(["Indicated Resources", "100", "2.5"]) == "Indicated"

    def test_detect_inferred(self):
        assert detect_resource_type(["Inferred", "50", "1.8"]) == "Inferred"

    def test_detect_measured(self):
        assert detect_resource_type(["Measured Resources", "80", "3.0"]) == "Measured"

    def test_no_match(self):
        assert detect_resource_type(["Some Data", "100", "2.5"]) is None


class TestDetectCommodity:
    """测试矿产品种检测"""

    def test_detect_gold_au(self):
        table = [["Grade", "g/t Au"], ["2.5", "3.0"]]
        assert detect_commodity(table) == "Au"

    def test_detect_copper_cu(self):
        table = [["Grade", "% Cu"], ["1.5", "2.0"]]
        assert detect_commodity(table) == "Cu"

    def test_detect_silver_ag(self):
        table = [["Metal", "Ag content"]]
        assert detect_commodity(table) == "Ag"

    def test_no_match(self):
        assert detect_commodity([["Name", "Value"]]) is None


class TestExtractGradeUnit:
    """测试品位单位提取"""

    def test_extract_g_t_au(self):
        assert extract_grade_unit("2.5 g/t Au") == "g/t Au"

    def test_extract_percent_cu(self):
        assert extract_grade_unit("1.5% Cu") == "% Cu"

    def test_extract_oz(self):
        assert extract_grade_unit("0.5 oz/t") == "oz/t"

    def test_unknown_unit(self):
        assert extract_grade_unit("some value") == ""


class TestResourceTable:
    """测试 ResourceTable 数据类"""

    def test_create_default(self):
        table = ResourceTable(resource_type="Indicated")
        assert table.ore_mt is None
        assert table.confidence == 0.0

    def test_to_dict(self):
        table = ResourceTable(
            resource_type="Indicated",
            ore_mt=100.5,
            grade_value=2.5,
            grade_unit="g/t Au"
        )
        d = table.to_dict()
        assert d["resource_type"] == "Indicated"
        assert d["ore_mt"] == 100.5


class TestCalculateConfidence:
    """测试置信度计算"""

    def test_full_fields_high_confidence(self):
        table = ResourceTable(
            resource_type="Indicated",
            ore_mt=100.0,
            grade_value=2.5,
            grade_unit="g/t Au",
            metal_oz=8000.0,
            commodity="Au"
        )
        assert calculate_confidence(table) == 1.0

    def test_partial_fields_medium_confidence(self):
        table = ResourceTable(
            resource_type="Indicated",
            ore_mt=100.0,
            grade_value=None,
            grade_unit=None,
        )
        conf = calculate_confidence(table)
        assert 0.3 < conf < 0.7


# 集成测试（需要实际 PDF 文件）
class TestExtractTablesPdfplumber:
    """测试 PDF 表格提取（集成测试）"""

    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """创建测试 PDF 文件（需要实际实现）"""
        # 这里需要创建一个真实的测试 PDF
        # 或者跳过此测试
        pytest.skip("需要真实 PDF 文件")
        return tmp_path / "test.pdf"

    def test_extract_tables(self, sample_pdf_path):
        tables = extract_tables_pdfplumber(sample_pdf_path)
        assert len(tables) > 0
