"""
Extractor Agent - 强模型资源量提取 Agent

使用 DeepSeek 从 PDF 文本中提取结构化的资源量数据。
支持 few-shot 示例注入，提升提取准确率。
"""

import json

from openai import OpenAI
from pydantic import BaseModel, Field

from core.config import Settings, get_settings
from core.logging_config import logger
from core.pdf_parser import ResourceTable


class ExtractionRequest(BaseModel):
    """提取请求数据结构"""

    pdf_text: str = Field(..., description="PDF 提取的文本内容")
    few_shot_examples: list[dict] = Field(default_factory=list, description="Few-shot 示例")


class ExtractionResult(BaseModel):
    """
    提取结果数据结构

    Attributes:
        indicated: Indicated Resources 数据
        inferred: Inferred Resources 数据
        confidence: 整体置信度 (0-1)
        source_pages: 来源页码列表
        raw_extraction: 原始提取输出
        notes: 提取说明或不确定之处
    """

    indicated: dict | None = Field(None, description="Indicated Resources")
    inferred: dict | None = Field(None, description="Inferred Resources")
    confidence: float = Field(..., ge=0, le=1, description="提取置信度")
    source_pages: list[int] = Field(default_factory=list, description="来源页码")
    raw_extraction: str = Field(..., description="原始提取输出")
    notes: str | None = Field(None, description="提取说明")

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump()


class ExtractorAgent:
    """
    资源量提取 Agent

    使用 DeepSeek 模型从 NI 43-101 PDF 中提取结构化数据。
    """

    def __init__(self, config: Settings | None = None):
        """
        初始化 Extractor Agent

        Args:
            config: 配置对象，默认使用全局配置
        """
        self.config = config or get_settings()
        # DeepSeek API 使用 OpenAI 兼容接口
        self.client = OpenAI(
            api_key=self.config.deepseek_api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = self.config.deepseek_model

        logger.info(f"ExtractorAgent 已初始化，模型：{self.model}")

    def build_prompt(self, pdf_text: str, few_shot_examples: list[dict] | None = None) -> str:
        """
        构建提取 Prompt

        Args:
            pdf_text: PDF 提取的文本内容
            few_shot_examples: Few-shot 示例列表

        Returns:
            完整的 Prompt 文本
        """
        # 系统指令
        system_instruction = """你是一个专业的矿业数据提取专家，专门从 NI 43-101 格式的技术报告中提取资源量数据。

## 提取目标

从提供的 NI 43-101 报告文本中提取以下数据：

### Indicated Resources (指示资源量)
- 矿石量 (Ore Tonnes, 单位：百万吨 Mt)
- 品位 (Grade, 单位：g/t Au 或 % Cu)
- 金属量 (Metal Content, 单位：oz 或 t)

### Inferred Resources (推断资源量)
- 同上

## 输出格式

必须严格按照以下 JSON 格式输出：

```json
{
    "indicated": {
        "ore_mt": 数值或 null,
        "grade_value": 数值或 null,
        "grade_unit": "g/t Au" 或 "% Cu" 等，
        "metal_oz": 数值或 null (金/银),
        "metal_t": 数值或 null (铜/锌等)
    },
    "inferred": {
        "ore_mt": 数值或 null,
        "grade_value": 数值或 null,
        "grade_unit": "g/t Au" 或 "% Cu" 等，
        "metal_oz": 数值或 null,
        "metal_t": 数值或 null
    },
    "confidence": 0.0-1.0,
    "source_pages": [页码列表],
    "notes": "提取说明或不确定之处"
}
```

## 重要规则

1. **数值精确**：必须从原文中准确提取数值，不得估算或推测
2. **单位明确**：必须明确标注单位（Mt, g/t, %, oz, t 等）
3. **置信度评估**：
   - 0.9-1.0: 所有字段完整，原文明确
   - 0.7-0.8: 大部分字段完整，部分模糊
   - 0.5-0.6: 部分字段缺失或不确定
   - <0.5: 大部分字段缺失，建议人工复核
4. **不确定时 abstain**：如果原文模糊或无法确定，将对应字段设为 null，并在 notes 中说明
5. **不要硬编**：绝不编造原文中没有的数据

"""

        # Few-shot 示例
        few_shot_section = ""
        if few_shot_examples:
            few_shot_section = "\n## 示例\n\n"
            for i, example in enumerate(few_shot_examples[:3], 1):  # 最多 3 个示例
                few_shot_section += f"### 示例 {i}\n"
                few_shot_section += (
                    f"输入文本摘要：{example.get('input_summary', 'N/A')[:200]}...\n"
                )
                few_shot_section += (
                    f"输出：\n```json\n{json.dumps(example.get('output', {}), indent=2)}\n```\n\n"
                )

        # 用户指令
        user_instruction = f"""## 待提取的 PDF 文本

以下是从 NI 43-101 报告中提取的文本内容（可能包含表格、段落等）：

---
{pdf_text[:15000]}  # 限制长度，避免超出上下文
---

## 任务

请从上述文本中提取 Indicated Resources 和 Inferred Resources 数据，按照上述 JSON 格式输出。

**注意**：
- 如果文本中没有明确的资源量数据，请将 confidence 设为 0.1-0.3，并在 notes 中说明原因
- 如果只能找到 Indicated 或只能找到 Inferred，另一个设为 null
- 如果原文有多个矿体或区域，取总计（Total）数据
"""

        return system_instruction + few_shot_section + user_instruction

    async def extract(
        self,
        pdf_text: str,
        few_shot_examples: list[dict] | None = None,
        history: list[dict] | None = None,
    ) -> ExtractionResult:
        """
        执行提取

        Args:
            pdf_text: PDF 提取的文本内容
            few_shot_examples: Few-shot 示例
            history: 历史修订记录（用于多轮修订）

        Returns:
            ExtractionResult 提取结果
        """
        # 构建 Prompt
        prompt = self.build_prompt(pdf_text, few_shot_examples)

        # 添加历史修订信息
        if history:
            revision_context = "\n## 历史修订记录\n\n"
            for i, h in enumerate(history[-2:], 1):  # 最近 2 轮
                revision_context += f"### 第{i}轮\n"
                revision_context += f"评分：{h.get('score', 'N/A')}/10\n"
                revision_context += f"修改建议：{h.get('feedback', 'N/A')}\n\n"
            prompt += revision_context
            prompt += "请根据历史修订反馈，修正提取结果。"

        logger.info(f"调用 {self.model} 进行提取...")

        try:
            # 调用 DeepSeek API (OpenAI 兼容接口)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )

            raw_output = response.choices[0].message.content
            logger.info(f"提取完成，原始输出长度：{len(raw_output)}")

            # 解析 JSON 输出
            result = self._parse_extraction_output(raw_output)
            result.raw_extraction = raw_output

            return result

        except Exception as e:
            logger.error(f"提取失败：{e}", exc_info=True)
            return ExtractionResult(
                indicated=None,
                inferred=None,
                confidence=0.1,
                source_pages=[],
                raw_extraction="",
                notes=f"提取失败：{str(e)}",
            )

    def _parse_extraction_output(self, raw_output: str) -> ExtractionResult:
        """
        解析模型输出

        Args:
            raw_output: 模型原始输出

        Returns:
            ExtractionResult
        """
        # 尝试提取 JSON
        json_text = raw_output

        # 查找 JSON 代码块
        import re

        json_match = re.search(r"```json\s*(.+?)\s*```", raw_output, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # 尝试直接解析 - 使用更智能的括号匹配
            json_text = self._extract_json_braces(raw_output)

        try:
            data = json.loads(json_text)
            return ExtractionResult(
                indicated=data.get("indicated"),
                inferred=data.get("inferred"),
                confidence=data.get("confidence", 0.5),
                source_pages=data.get("source_pages", []),
                raw_extraction=raw_output,
                notes=data.get("notes"),
            )
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败：{e}，尝试降级处理")

            # 降级处理：尝试提取关键字段
            confidence = 0.3
            notes = f"JSON 解析失败，原始输出：{raw_output[:500]}"

            return ExtractionResult(
                indicated=None,
                inferred=None,
                confidence=confidence,
                source_pages=[],
                raw_extraction=raw_output,
                notes=notes,
            )

    def _extract_json_braces(self, text: str) -> str:
        """
        从文本中提取最外层的 JSON 对象（处理嵌套括号）

        Args:
            text: 包含 JSON 的文本

        Returns:
            JSON 字符串
        """
        # 找到第一个 {
        start = text.find("{")
        if start == -1:
            return text

        # 括号计数
        count = 0
        in_string = False
        escape = False

        for i, char in enumerate(text[start:], start):
            if escape:
                escape = False
                continue

            if char == "\\\\":
                escape = True
                continue

            if char == '"' and not escape:
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    count += 1
                elif char == "}":
                    count -= 1
                    if count == 0:
                        return text[start : i + 1]

        # 如果没有找到匹配的括号，返回整个文本
        return text

    def extract_from_resource_tables(
        self, tables: list[ResourceTable], few_shot_examples: list[dict] | None = None
    ) -> ExtractionResult:
        """
        从已解析的表格数据中提取结构化结果

        Args:
            tables: ResourceTable 列表
            few_shot_examples: Few-shot 示例

        Returns:
            ExtractionResult
        """
        # 将表格数据转换为文本
        pdf_text = self._tables_to_text(tables)
        return self.extract(pdf_text, few_shot_examples)

    def _tables_to_text(self, tables: list[ResourceTable]) -> str:
        """
        将表格数据转换为文本

        Args:
            tables: ResourceTable 列表

        Returns:
            文本表示
        """
        lines = []
        for table in tables:
            lines.append(f"页码：{table.source_page}")
            lines.append(f"类型：{table.resource_type}")
            lines.append(f"矿石量：{table.ore_mt} Mt")
            lines.append(f"品位：{table.grade_value} {table.grade_unit}")
            lines.append(f"金属量：{table.metal_oz} oz / {table.metal_t} t")
            lines.append(f"矿种：{table.commodity}")
            lines.append(f"置信度：{table.confidence}")
            lines.append(f"原始数据：{table.raw_text}")
            lines.append("---")

        return "\n".join(lines)


# 全局单例
_extractor_agent: ExtractorAgent | None = None


def get_extractor_agent() -> ExtractorAgent:
    """获取 ExtractorAgent 单例"""
    global _extractor_agent
    if _extractor_agent is None:
        _extractor_agent = ExtractorAgent()
    return _extractor_agent
