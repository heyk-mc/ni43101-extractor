"""
PDF 解析模块

负责从 NI 43-101 格式 PDF 中提取资源量表格数据。
支持多种解析策略：pdfplumber（优先）和 pypdf（兜底）。
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from core.config import settings
from core.logging_config import logger
from core.path_utils import validate_pdf_path


@dataclass
class ResourceTable:
    """
    资源量表格数据结构

    Attributes:
        resource_type: 资源类型 (Indicated/Inferred)
        ore_mt: 矿石量 (百万吨 Mt)
        grade_value: 品位数值
        grade_unit: 品位单位 (g/t Au 或 % Cu)
        metal_oz: 金属量 (盎司 oz，针对金)
        metal_t: 金属量 (吨 t，针对铜等)
        commodity: 主要矿产品种 (Au/Cu 等)
        source_page: 来源页码
        raw_text: 原始表格文本
        confidence: 提取置信度 (0-1)
    """

    resource_type: str
    ore_mt: float | None = None
    grade_value: float | None = None
    grade_unit: str | None = None
    metal_oz: float | None = None
    metal_t: float | None = None
    commodity: str | None = None
    source_page: int | None = None
    raw_text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "resource_type": self.resource_type,
            "ore_mt": self.ore_mt,
            "grade_value": self.grade_value,
            "grade_unit": self.grade_unit,
            "metal_oz": self.metal_oz,
            "metal_t": self.metal_t,
            "commodity": self.commodity,
            "source_page": self.source_page,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
        }


def extract_tables_pdfplumber(pdf_path: Path) -> list[tuple[int, list[list[str | None]]]]:
    """
    使用 pdfplumber 提取 PDF 中的表格

    Args:
        pdf_path: PDF 文件路径

    Returns:
        列表，每项为 (页码，表格数据) 元组
    """
    tables_with_pages: list[tuple[int, list[list[str | None]]]] = []

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                if page_tables:
                    for table in page_tables:
                        if table and len(table) > 1:  # 至少要有表头 + 数据行
                            tables_with_pages.append((i + 1, table))  # 页码从 1 开始
    except Exception as e:
        logger.warning(f"pdfplumber 解析失败：{e}，尝试使用 pypdf 兜底")
        return extract_tables_pypdf(pdf_path)

    return tables_with_pages


def extract_tables_pypdf(pdf_path: Path) -> list[tuple[int, list[list[str | None]]]]:
    """
    使用 pypdf 提取 PDF 中的表格（兜底方案）

    Args:
        pdf_path: PDF 文件路径

    Returns:
        列表，每项为 (页码，表格数据) 元组
    """
    tables_with_pages: list[tuple[int, list[list[str | None]]]] = []

    try:
        reader = PdfReader(str(pdf_path))

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue

            # 简单的表格检测：查找包含制表符或多空格的行
            lines = text.split("\n")
            table_lines: list[list[str | None]] = []
            in_table = False

            for line in lines:
                # 检测表格行特征
                if "\t" in line or (line.count("  ") >= 2):
                    if not in_table:
                        in_table = True
                        table_lines = []
                    # 分割表格单元格
                    cells = re.split(r"\t|\s{2,}", line.strip())
                    table_lines.append([c.strip() for c in cells if c.strip()])
                else:
                    if in_table and table_lines:
                        tables_with_pages.append((i + 1, table_lines))
                        in_table = False
                        table_lines = []

            # 处理页面末尾的表格
            if in_table and table_lines:
                tables_with_pages.append((i + 1, table_lines))

    except Exception as e:
        logger.error(f"pypdf 解析失败：{e}")

    return tables_with_pages


def is_resource_table(table: list[list[str | None]]) -> bool:
    """
    判断表格是否为资源量表格

    检测关键词：Indicated, Inferred, Resources, Tonnes, Grade 等

    Args:
        table: 表格数据

    Returns:
        是否为资源量表格
    """
    # 资源量表格关键词
    keywords = [
        "indicated",
        "inferred",
        "measured",
        "resources",
        "reserves",
        "tonnes",
        "million tonnes",
        "mt",
        "grade",
        "g/t",
        "oz",
        "au",
        "cu",
        "gold",
        "copper",
        "ni 43-101",
        "ni43101",
    ]

    # 检查表头（通常是第一行）
    header = " ".join(str(cell) for cell in table[0] if cell).lower() if table else ""

    # 检查前几行
    first_rows = " ".join(" ".join(str(cell) for cell in row if cell) for row in table[:3]).lower()

    # 统计关键词匹配
    match_count = sum(1 for kw in keywords if kw in header or kw in first_rows)

    # 至少匹配 2 个关键词才认为是资源量表格
    return match_count >= 2


def parse_number(text: str) -> float | None:
    """
    从文本中解析数字

    支持格式：1,000.50 / 1.000,50 / 100M / 1.5B 等

    Args:
        text: 包含数字的文本

    Returns:
        解析后的数字，失败返回 None
    """
    if not text:
        return None

    # 清理文本
    text = text.strip()

    # 移除常见单位
    text = re.sub(r"[Mm]illion|[Bb]illion|%", "", text)

    # 处理千分位分隔符（英式：1,000.50）
    text = text.replace(",", "")

    # 尝试解析
    try:
        return float(text)
    except ValueError:
        pass

    # 尝试提取数字部分
    match = re.search(r"[\d.]+", text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            pass

    return None


def parse_table(table: list[list[str | None]], page: int) -> list[ResourceTable]:
    """
    解析资源量表格

    Args:
        table: 表格数据
        page: 页码

    Returns:
        ResourceTable 列表
    """
    results = []

    # 构建列名映射
    header = table[0] if table else []
    col_mapping = {}

    for i, col_name in enumerate(header):
        col_lower = col_name.lower() if col_name else ""

        if any(kw in col_lower for kw in ["tonnes", "million", "mt", "quantity"]):
            col_mapping["ore_mt"] = i
        elif any(kw in col_lower for kw in ["grade", "g/t", "%"]):
            col_mapping["grade"] = i
        elif any(kw in col_lower for kw in ["oz", "ounce", "gold content"]):
            col_mapping["metal_oz"] = i
        elif any(kw in col_lower for kw in ["metal", "contained"]):
            col_mapping["metal_t"] = i

    # 检测矿产品种
    commodity = detect_commodity(table)

    # 解析每一行数据
    for row in table[1:]:
        if len(row) < len(header):
            continue

        # 检测资源类型
        resource_type = detect_resource_type(row)
        if not resource_type:
            continue

        resource_table = ResourceTable(
            resource_type=resource_type,
            commodity=commodity,
            source_page=page,
            raw_text=" | ".join(str(cell) for cell in row if cell),
        )

        # 提取数值
        if "ore_mt" in col_mapping and col_mapping["ore_mt"] < len(row):
            ore_text = row[col_mapping["ore_mt"]]
            resource_table.ore_mt = parse_number(ore_text) if ore_text else None

        if "grade" in col_mapping and col_mapping["grade"] < len(row):
            grade_text = row[col_mapping["grade"]]
            resource_table.grade_value = parse_number(grade_text) if grade_text else None
            resource_table.grade_unit = extract_grade_unit(grade_text) if grade_text else None

        if "metal_oz" in col_mapping and col_mapping["metal_oz"] < len(row):
            metal_oz_text = row[col_mapping["metal_oz"]]
            resource_table.metal_oz = parse_number(metal_oz_text) if metal_oz_text else None

        if "metal_t" in col_mapping and col_mapping["metal_t"] < len(row):
            metal_t_text = row[col_mapping["metal_t"]]
            resource_table.metal_t = parse_number(metal_t_text) if metal_t_text else None

        # 计算置信度
        resource_table.confidence = calculate_confidence(resource_table)

        if resource_table.confidence > 0.3:  # 只保留置信度>0.3 的结果
            results.append(resource_table)

    return results


def detect_resource_type(row: list[str | None]) -> str | None:
    """
    从行数据中检测资源类型

    Args:
        row: 表格行数据

    Returns:
        资源类型 (Indicated/Inferred) 或 None
    """
    row_text = " ".join(str(cell) for cell in row).lower()

    if "indicated" in row_text:
        return "Indicated"
    elif "inferred" in row_text:
        return "Inferred"
    elif "measured" in row_text:
        return "Measured"
    elif "proven" in row_text:
        return "Proven"
    elif "probable" in row_text:
        return "Probable"

    return None


def detect_commodity(table: list[list[str | None]]) -> str | None:
    """
    检测矿产品种

    Args:
        table: 表格数据

    Returns:
        矿产品种 (Au/Cu 等)
    """
    table_text = " ".join(" ".join(str(cell) for cell in row if cell) for row in table).lower()

    if any(kw in table_text for kw in ["gold", "au ", "au,", "(au)"]):
        return "Au"
    elif any(kw in table_text for kw in ["copper", "cu ", "cu,", "(cu)"]):
        return "Cu"
    elif any(kw in table_text for kw in ["silver", "ag ", "ag,", "(ag)"]):
        return "Ag"
    elif any(kw in table_text for kw in ["zinc", "zn ", "zn,", "(zn)"]):
        return "Zn"
    elif any(kw in table_text for kw in ["lead", "pb ", "pb,", "(pb)"]):
        return "Pb"
    elif any(kw in table_text for kw in ["lithium", "li ", "li,", "(li)"]):
        return "Li"

    return None


def extract_grade_unit(grade_text: str) -> str:
    """
    从品位文本中提取单位

    Args:
        grade_text: 品位文本

    Returns:
        单位 (g/t Au, % Cu 等)
    """
    grade_text_lower = grade_text.lower()

    if "g/t" in grade_text_lower:
        if "au" in grade_text_lower or "gold" in grade_text_lower:
            return "g/t Au"
        elif "ag" in grade_text_lower or "silver" in grade_text_lower:
            return "g/t Ag"
        else:
            return "g/t"
    elif "%" in grade_text:
        if "cu" in grade_text_lower or "copper" in grade_text_lower:
            return "% Cu"
        elif "zn" in grade_text_lower or "zinc" in grade_text_lower:
            return "% Zn"
        elif "pb" in grade_text_lower or "lead" in grade_text_lower:
            return "% Pb"
        else:
            return "%"
    elif "oz" in grade_text_lower:
        return "oz/t"

    return ""


def calculate_confidence(resource: ResourceTable) -> float:
    """
    计算提取结果的置信度

    Args:
        resource: 资源量数据

    Returns:
        置信度 (0-1)
    """
    score = 0.0
    max_score = 5.0

    # 资源类型明确 +1
    if resource.resource_type in ["Indicated", "Inferred", "Measured"]:
        score += 1.0

    # 矿石量存在 +1
    if resource.ore_mt is not None:
        score += 1.0

    # 品位存在 +1
    if resource.grade_value is not None and resource.grade_unit:
        score += 1.0

    # 金属量存在 +1
    if resource.metal_oz is not None or resource.metal_t is not None:
        score += 1.0

    # 矿产品种明确 +1
    if resource.commodity:
        score += 1.0

    return score / max_score


def extract_resources_from_pdf(pdf_path: str | Path) -> list[ResourceTable]:
    """
    从 PDF 中提取资源量数据的主函数

    Args:
        pdf_path: PDF 文件路径

    Returns:
        ResourceTable 列表
    """
    pdf_path = Path(pdf_path)

    # 如果是绝对路径，直接使用；否则使用 validate_pdf_path 检查
    if pdf_path.is_absolute():
        validated_path = pdf_path.resolve()
        if not validated_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在：{validated_path}")
    else:
        # 相对路径：如果包含路径分隔符，只取文件名部分传给 validate_pdf_path
        # 因为 validate_pdf_path 会自动拼接到 pdf_data_dir 后面
        path_str = pdf_path.name if pdf_path.parent != Path(".") else str(pdf_path)
        validated_path = validate_pdf_path(path_str, settings.pdf_data_abs_path)

    logger.info(f"开始解析 PDF: {validated_path}")

    # 提取表格
    tables_with_pages = extract_tables_pdfplumber(validated_path)

    if not tables_with_pages:
        logger.warning(f"PDF 中未检测到表格：{validated_path}")
        return []

    logger.info(f"检测到 {len(tables_with_pages)} 个表格")

    # 解析资源量表格
    results = []
    for page_num, table in tables_with_pages:
        if is_resource_table(table):
            logger.info(f"第{page_num}页检测到资源量表格")
            parsed = parse_table(table, page_num)
            results.extend(parsed)

    logger.info(f"共提取 {len(results)} 条资源量记录")

    return results


if __name__ == "__main__":
    # 本地测试入口
    import sys

    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        results = extract_resources_from_pdf(pdf_file)
        for r in results:
            print(f"{r.resource_type}: {r.ore_mt} Mt, {r.grade_value} {r.grade_unit}")
    else:
        print("用法：python core/pdf_parser.py <pdf 文件名>")
