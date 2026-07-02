"""
CriticMaster Agent - 弱模型评分 Agent

使用较弱模型（Qwen/GLM）对 Extractor Agent 的提取结果进行评分，
提供修改建议，驱动修订循环。
"""

import json

import httpx
from pydantic import BaseModel, Field

from agents.extractor_agent import ExtractionResult
from core.config import Settings, get_settings
from core.logging_config import logger


class CriticismResult(BaseModel):
    """
    评分结果数据结构

    Attributes:
        score: 评分 (1-10)
        feedback: 修改建议
        issues: 发现的问题列表
        suggestion: 具体修改建议
    """

    score: int = Field(..., ge=1, le=10, description="评分 (1-10)")
    feedback: str = Field(..., description="修改建议")
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    suggestion: str | None = Field(None, description="具体修改建议")

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump()


class CriticMasterAgent:
    """
    评分 Agent

    使用较弱模型（Qwen/GLM）对提取结果进行评分，降低成本。
    """

    def __init__(self, config: Settings | None = None):
        """
        初始化 CriticMaster Agent

        Args:
            config: 配置对象
        """
        self.config = config or get_settings()
        self.model = self.config.qwen_model
        self.api_key = self.config.dashscope_api_key

        # DashScope API 端点
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

        logger.info(f"CriticMasterAgent 已初始化，模型：{self.model}")

    def build_prompt(
        self, extraction_result: ExtractionResult, history: list[dict] | None = None
    ) -> str:
        """
        构建评分 Prompt

        Args:
            extraction_result: 提取结果
            history: 历史修订记录

        Returns:
            完整的 Prompt 文本
        """
        system_instruction = """你是一个专业的矿业数据质量评审专家。你的任务是对 NI 43-101 报告资源量提取结果进行评分，并提供具体的修改建议。

## 评分标准

请严格按照以下标准评分（1-10 分）：

### 9-10 分：优秀
- 所有字段完整（ore_mt, grade_value, grade_unit）
- 数值精确，原文明确
- 单位正确标注
- 置信度自评合理

### 7-8 分：良好
- 大部分字段完整
- 数值有轻微模糊但可接受
- 单位基本正确
- 置信度自评基本合理

### 5-6 分：及格
- 部分字段缺失（缺少 1-2 个关键字段）
- 数值有较大不确定性
- 单位可能不明确
- 置信度自评可能偏高或偏低

### 3-4 分：较差
- 大部分字段缺失或明显错误
- 数值与原文明显不符
- 单位错误
- 置信度自评严重偏离

### 1-2 分：不可接受
- 完全无法提取或严重错误
- 编造原文中没有的数据
- 完全误解原文

## 输出格式

必须严格按照以下 JSON 格式输出：

```json
{
    "score": 7,
    "feedback": "整体提取质量良好，但..."
    "issues": ["问题 1", "问题 2"],
    "suggestion": "建议修改..."
}
```

"""

        # 构建提取结果文本
        result_text = f"""## 提取结果

### Indicated Resources
- 矿石量 (ore_mt): {extraction_result.indicated.get('ore_mt') if extraction_result.indicated else 'null'}
- 品位值 (grade_value): {extraction_result.indicated.get('grade_value') if extraction_result.indicated else 'null'}
- 品位单位 (grade_unit): {extraction_result.indicated.get('grade_unit') if extraction_result.indicated else 'null'}
- 金属量 (metal_oz): {extraction_result.indicated.get('metal_oz') if extraction_result.indicated else 'null'}
- 金属量 (metal_t): {extraction_result.indicated.get('metal_t') if extraction_result.indicated else 'null'}

### Inferred Resources
- 矿石量 (ore_mt): {extraction_result.inferred.get('ore_mt') if extraction_result.inferred else 'null'}
- 品位值 (grade_value): {extraction_result.inferred.get('grade_value') if extraction_result.inferred else 'null'}
- 品位单位 (grade_unit): {extraction_result.inferred.get('grade_unit') if extraction_result.inferred else 'null'}
- 金属量 (metal_oz): {extraction_result.inferred.get('metal_oz') if extraction_result.inferred else 'null'}
- 金属量 (metal_t): {extraction_result.inferred.get('metal_t') if extraction_result.inferred else 'null'}

### 自评置信度
confidence: {extraction_result.confidence}

### 来源页码
source_pages: {extraction_result.source_pages}

### 提取说明
notes: {extraction_result.notes or '无'}

### 原始提取输出
{extraction_result.raw_extraction[:1000] if extraction_result.raw_extraction else '无'}
"""

        # 历史记录
        history_section = ""
        if history:
            history_section = "\n## 历史修订记录\n\n"
            for i, h in enumerate(history[-2:], 1):
                history_section += f"### 第{i}轮修订\n"
                history_section += f"评分：{h.get('score', 'N/A')}/10\n"
                history_section += f"反馈：{h.get('feedback', 'N/A')}\n"
                history_section += f"建议：{h.get('suggestion', 'N/A')}\n\n"

        user_instruction = f"""{result_text}

{history_section}

## 任务

请对上述提取结果进行评分，并提供具体的修改建议。

**评审重点**：
1. 字段完整性：是否包含所有必需字段
2. 数值合理性：数值是否在合理范围内
3. 单位正确性：单位标注是否正确
4. 置信度评估：自评置信度是否与实际质量匹配
5. 历史修订：如果有历史修订，检查是否已修正之前的问题

请按照上述 JSON 格式输出评分结果。
"""

        return system_instruction + user_instruction

    async def score(
        self, extraction_result: ExtractionResult, history: list[dict] | None = None
    ) -> CriticismResult:
        """
        对提取结果进行评分

        Args:
            extraction_result: 提取结果
            history: 历史修订记录

        Returns:
            CriticismResult 评分结果
        """
        # 构建 Prompt
        prompt = self.build_prompt(extraction_result, history)

        logger.info(f"调用 {self.model} 进行评分...")

        try:
            # 检查 API Key
            if not self.api_key:
                logger.warning("DashScope API Key 未配置，使用模拟评分")
                return self._mock_score(extraction_result)

            # 调用 DashScope API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 500,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()

                data = response.json()
                raw_output = data["choices"][0]["message"]["content"]

                logger.info(f"评分完成，原始输出长度：{len(raw_output)}")

                # 解析评分输出
                result = self._parse_criticism_output(raw_output)
                return result

        except Exception as e:
            logger.error(f"评分失败：{e}", exc_info=True)
            # 降级处理：使用模拟评分
            return self._mock_score(extraction_result)

    def _parse_criticism_output(self, raw_output: str) -> CriticismResult:
        """
        解析模型输出

        Args:
            raw_output: 模型原始输出

        Returns:
            CriticismResult
        """
        # 尝试提取 JSON
        json_text = raw_output

        import re

        json_match = re.search(r"```json\s*(.+?)\s*```", raw_output, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            json_match = re.search(r"\{.+?\}", raw_output, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)

        try:
            data = json.loads(json_text)
            return CriticismResult(
                score=data.get("score", 5),
                feedback=data.get("feedback", ""),
                issues=data.get("issues", []),
                suggestion=data.get("suggestion"),
            )
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败：{e}，使用默认评分")

            # 尝试从文本中提取评分
            score_match = re.search(r"score[:\s]*(\d+)", raw_output.lower())
            score = int(score_match.group(1)) if score_match else 5

            return CriticismResult(
                score=score,
                feedback=raw_output[:500],
                issues=["JSON 解析失败"],
                suggestion="请手动检查提取结果",
            )

    def _mock_score(self, extraction_result: ExtractionResult) -> CriticismResult:
        """
        模拟评分（API 不可用时的降级处理）

        Args:
            extraction_result: 提取结果

        Returns:
            CriticismResult
        """
        score = 5
        issues = []
        feedback_parts = []

        # 检查字段完整性
        has_indicated = extraction_result.indicated is not None
        has_inferred = extraction_result.inferred is not None

        if not has_indicated and not has_inferred:
            score = 2
            issues.append("Indicated 和 Inferred 均为空")
            feedback_parts.append("提取结果完全缺失，需要重新提取")
        elif not has_indicated:
            score = 4
            issues.append("Indicated 为空")
            feedback_parts.append("缺少 Indicated Resources 数据")
        elif not has_inferred:
            score = 6
            issues.append("Inferred 为空")
            feedback_parts.append("缺少 Inferred Resources 数据")
        else:
            # 检查字段
            indicated = extraction_result.indicated
            if indicated and indicated.get("ore_mt") is None:
                score -= 1
                issues.append("Indicated 矿石量缺失")
            if indicated and indicated.get("grade_value") is None:
                score -= 1
                issues.append("Indicated 品位缺失")
            if indicated and indicated.get("grade_unit") is None:
                score -= 1
                issues.append("Indicated 单位缺失")

            inferred = extraction_result.inferred
            if inferred and inferred.get("ore_mt") is None:
                score -= 1
                issues.append("Inferred 矿石量缺失")
            if inferred and inferred.get("grade_value") is None:
                score -= 1
                issues.append("Inferred 品位缺失")

            # 置信度检查
            if extraction_result.confidence > 0.8 and len(issues) > 2:
                score -= 2
                feedback_parts.append("自评置信度过高，与实际质量不符")

            if score >= 7:
                feedback_parts.append("整体提取质量良好")
            elif score >= 5:
                feedback_parts.append("整体提取质量一般，部分字段缺失")
            else:
                feedback_parts.append("整体提取质量较差，需要大幅修改")

        # 确保分数在 1-10 范围内
        score = max(1, min(10, score))

        return CriticismResult(
            score=score,
            feedback="; ".join(feedback_parts),
            issues=issues,
            suggestion=f"建议检查：{', '.join(issues)}" if issues else "无明显问题",
        )


# 全局单例
_critic_master_agent: CriticMasterAgent | None = None


def get_critic_master_agent() -> CriticMasterAgent:
    """获取 CriticMasterAgent 单例"""
    global _critic_master_agent
    if _critic_master_agent is None:
        _critic_master_agent = CriticMasterAgent()
    return _critic_master_agent
