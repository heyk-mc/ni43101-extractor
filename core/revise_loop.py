"""
修订循环模块

实现最多 3 轮修订逻辑，超过则返回 abstain。
驱动 Extractor Agent 和 CriticMaster Agent 的协作。
"""

import asyncio
from dataclasses import dataclass, field

from agents.critic_master import CriticMasterAgent, get_critic_master_agent
from agents.extractor_agent import ExtractionResult, ExtractorAgent, get_extractor_agent
from core.config import Settings, get_settings
from core.logging_config import logger
from core.pdf_parser import ResourceTable, extract_resources_from_pdf


@dataclass
class RevisionRound:
    """
    修订轮次数据

    Attributes:
        round_num: 轮次编号
        result: 提取结果
        score: 评分
        feedback: 反馈
        success: 是否成功
    """

    round_num: int
    result: ExtractionResult
    score: int
    feedback: str
    success: bool = False


@dataclass
class RevisionOutput:
    """
    修订循环输出

    Attributes:
        final_result: 最终提取结果
        status: 状态 (success/abstain/max_rounds)
        rounds: 修订轮次列表
        total_rounds: 总轮次数
        reason: 原因说明（abstain 时填写）
    """

    final_result: ExtractionResult | None
    status: str  # success, abstain, max_rounds
    rounds: list[RevisionRound] = field(default_factory=list)
    total_rounds: int = 0
    reason: str | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "final_result": self.final_result.to_dict() if self.final_result else None,
            "status": self.status,
            "rounds": [
                {
                    "round_num": r.round_num,
                    "score": r.score,
                    "feedback": r.feedback,
                    "success": r.success,
                }
                for r in self.rounds
            ],
            "total_rounds": self.total_rounds,
            "reason": self.reason,
        }


class ReviseLoop:
    """
    修订循环控制器

    管理 Extractor Agent 和 CriticMaster Agent 的协作，
    实现最多 3 轮修订逻辑。
    """

    def __init__(
        self,
        extractor: ExtractorAgent | None = None,
        critic: CriticMasterAgent | None = None,
        config: Settings | None = None,
    ):
        """
        初始化修订循环

        Args:
            extractor: Extractor Agent
            critic: CriticMaster Agent
            config: 配置对象
        """
        self.config = config or get_settings()
        self.extractor = extractor or get_extractor_agent()
        self.critic = critic or get_critic_master_agent()

        self.max_rounds = self.config.max_revise_rounds
        self.score_threshold = self.config.score_threshold

        logger.info(
            f"ReviseLoop 已初始化，"
            f"最大轮次：{self.max_rounds}, "
            f"评分阈值：{self.score_threshold}"
        )

    async def run(
        self, pdf_path: str, few_shot_examples: list[dict] | None = None
    ) -> RevisionOutput:
        """
        运行修订循环

        Args:
            pdf_path: PDF 文件路径
            few_shot_examples: Few-shot 示例

        Returns:
            RevisionOutput 修订输出
        """
        output = RevisionOutput(final_result=None, status="running", rounds=[])

        # 步骤 1: 解析 PDF 获取表格数据
        logger.info(f"步骤 1: 解析 PDF: {pdf_path}")
        tables = extract_resources_from_pdf(pdf_path)

        if not tables:
            logger.warning("PDF 中未提取到资源量表格")
            output.status = "abstain"
            output.reason = "PDF 中未检测到资源量表格"
            output.total_rounds = 0
            return output

        # 步骤 2: 将表格数据转换为文本
        pdf_text = self._tables_to_text(tables)

        # 步骤 3: 运行修订循环
        history: list[dict] = []
        current_few_shot = few_shot_examples

        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"步骤 {round_num + 1}: 第 {round_num} 轮修订")

            # 提取
            result = await self.extractor.extract(
                pdf_text=pdf_text, few_shot_examples=current_few_shot, history=history
            )

            # 评分
            criticism = await self.critic.score(result, history)

            logger.info(f"第{round_num}轮评分：{criticism.score}/10")

            # 记录轮次
            round_data = RevisionRound(
                round_num=round_num,
                result=result,
                score=criticism.score,
                feedback=criticism.feedback,
                success=criticism.score >= self.score_threshold,
            )
            output.rounds.append(round_data)
            output.total_rounds = round_num

            # 检查是否达到阈值
            if criticism.score >= self.score_threshold:
                logger.info(f"评分达到阈值 ({criticism.score} >= {self.score_threshold})，修订成功")
                output.final_result = result
                output.status = "success"
                return output

            # 准备下一轮
            history.append(
                {
                    "score": criticism.score,
                    "feedback": criticism.feedback,
                    "suggestion": criticism.suggestion,
                    "result": result.to_dict(),
                }
            )

        # 达到最大轮次，仍未达到阈值
        logger.warning(f"达到最大修订轮次 ({self.max_rounds})，返回 abstain")
        output.status = "abstain"
        output.reason = f"经过 {self.max_rounds} 轮修订后，最高评分为 {max(r.score for r in output.rounds)}/10，未达到阈值 {self.score_threshold}"
        output.final_result = output.rounds[-1].result  # 返回最后一轮结果

        return output

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


async def run_extraction(
    pdf_path: str, few_shot_examples: list[dict] | None = None
) -> RevisionOutput:
    """
    运行完整提取流程的便捷函数

    Args:
        pdf_path: PDF 文件路径
        few_shot_examples: Few-shot 示例

    Returns:
        RevisionOutput
    """
    loop = ReviseLoop()
    return await loop.run(pdf_path, few_shot_examples)


if __name__ == "__main__":
    # 本地测试
    import sys

    async def main():
        if len(sys.argv) > 1:
            pdf_file = sys.argv[1]
            result = await run_extraction(pdf_file)
            print(f"状态：{result.status}")
            print(f"总轮次：{result.total_rounds}")
            if result.final_result:
                print(f"Indicated: {result.final_result.indicated}")
                print(f"Inferred: {result.final_result.inferred}")
            if result.reason:
                print(f"原因：{result.reason}")
        else:
            print("用法：python core/revise_loop.py <pdf 文件名>")

    asyncio.run(main())
