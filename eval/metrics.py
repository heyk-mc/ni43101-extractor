"""
评测模块

计算提取准确率，检测 abstain 机制，生成评测报告。
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from core.config import get_settings
from core.logging_config import logger
from core.revise_loop import RevisionOutput
from agents.extractor_agent import ExtractionResult


@dataclass
class EvalResult:
    """评测结果"""
    pdf_name: str
    status: str  # success, abstain
    accuracy: float  # 0-1
    total_rounds: int
    max_score: int
    abstained: bool

    def to_dict(self) -> dict:
        return {
            "pdf_name": self.pdf_name,
            "status": self.status,
            "accuracy": self.accuracy,
            "total_rounds": self.total_rounds,
            "max_score": self.max_score,
            "abstained": self.abstained
        }


def load_ground_truth(truth_path: str) -> dict:
    """
    加载 ground truth

    Args:
        truth_path: ground truth JSON 路径

    Returns:
        ground truth 字典
    """
    with open(truth_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_accuracy(
    result: ExtractionResult,
    ground_truth: dict,
    tolerance: float = 0.05
) -> float:
    """
    计算提取准确率

    Args:
        result: 提取结果
        ground_truth: 标准答案
        tolerance: 容差（0.05 表示±5%）

    Returns:
        准确率 (0-1)
    """
    if not result:
        return 0.0

    correct = 0
    total = 0

    # 检查 Indicated
    if ground_truth.get("indicated") and result.indicated:
        for key in ["ore_mt", "grade_value", "metal_oz", "metal_t"]:
            gt_val = ground_truth["indicated"].get(key)
            res_val = result.indicated.get(key)

            if gt_val is not None and res_val is not None:
                total += 1
                if _within_tolerance(res_val, gt_val, tolerance):
                    correct += 1

    # 检查 Inferred
    if ground_truth.get("inferred") and result.inferred:
        for key in ["ore_mt", "grade_value", "metal_oz", "metal_t"]:
            gt_val = ground_truth["inferred"].get(key)
            res_val = result.inferred.get(key)

            if gt_val is not None and res_val is not None:
                total += 1
                if _within_tolerance(res_val, gt_val, tolerance):
                    correct += 1

    return correct / total if total > 0 else 0.0


def _within_tolerance(predicted: float, expected: float, tolerance: float) -> bool:
    """检查是否在容差范围内"""
    if expected == 0:
        return abs(predicted - expected) < tolerance * 100

    relative_error = abs(predicted - expected) / abs(expected)
    return relative_error <= tolerance


def evaluate_single(
    output: RevisionOutput,
    ground_truth: dict,
    pdf_name: str,
    tolerance: float = 0.05
) -> EvalResult:
    """
    评估单次提取

    Args:
        output: 修订循环输出
        ground_truth: 标准答案
        pdf_name: PDF 名称
        tolerance: 容差

    Returns:
        EvalResult
    """
    accuracy = 0.0
    if output.final_result:
        accuracy = calculate_accuracy(output.final_result, ground_truth, tolerance)

    max_score = max((r.score for r in output.rounds), default=0)

    return EvalResult(
        pdf_name=pdf_name,
        status=output.status,
        accuracy=accuracy,
        total_rounds=output.total_rounds,
        max_score=max_score,
        abstained=output.status == "abstain"
    )


def run_evaluation(
    results: list[tuple[str, RevisionOutput]],
    ground_truths: dict[str, dict],
    tolerance: float = 0.05
) -> list[EvalResult]:
    """
    批量评估

    Args:
        results: [(pdf_name, output), ...]
        ground_truths: {pdf_name: ground_truth}
        tolerance: 容差

    Returns:
        EvalResult 列表
    """
    eval_results = []

    for pdf_name, output in results:
        if pdf_name not in ground_truths:
            logger.warning(f"未找到 {pdf_name} 的 ground truth，跳过")
            continue

        eval_result = evaluate_single(
            output,
            ground_truths[pdf_name],
            pdf_name,
            tolerance
        )
        eval_results.append(eval_result)

    return eval_results


def generate_report(eval_results: list[EvalResult]) -> str:
    """
    生成评测报告

    Args:
        eval_results: 评测结果列表

    Returns:
        评测报告文本
    """
    if not eval_results:
        return "没有评测结果"

    lines = []
    lines.append("=" * 60)
    lines.append("NI 43-101 提取系统评测报告")
    lines.append("=" * 60)
    lines.append("")

    # 汇总统计
    total = len(eval_results)
    success = sum(1 for r in eval_results if r.status == "success")
    abstain = sum(1 for r in eval_results if r.abstained)
    avg_accuracy = sum(r.accuracy for r in eval_results) / total
    avg_rounds = sum(r.total_rounds for r in eval_results) / total

    lines.append(f"总样本数：{total}")
    lines.append(f"成功：{success} ({success/total*100:.1f}%)")
    lines.append(f"Abstain: {abstain} ({abstain/total*100:.1f}%)")
    lines.append(f"平均准确率：{avg_accuracy*100:.1f}%")
    lines.append(f"平均修订轮次：{avg_rounds:.1f}")
    lines.append("")

    # 详细结果
    lines.append("-" * 60)
    lines.append("详细结果")
    lines.append("-" * 60)

    for r in eval_results:
        lines.append(f"\nPDF: {r.pdf_name}")
        lines.append(f"  状态：{r.status}")
        lines.append(f"  准确率：{r.accuracy*100:.1f}%")
        lines.append(f"  修订轮次：{r.total_rounds}")
        lines.append(f"  最高评分：{r.max_score}/10")
        lines.append(f"  Abstain: {r.abstained}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def save_report(report: str, output_path: str) -> None:
    """
    保存评测报告

    Args:
        report: 评测报告文本
        output_path: 输出路径
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"评测报告已保存：{output_path}")


if __name__ == "__main__":
    # 本地测试
    print("评测模块 - 运行评测需要完整的提取结果")
    print("用法：python eval/metrics.py")
