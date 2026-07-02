"""
进化日志模块

负责记录失败/困难案例，积累 few-shot 示例，支持自进化改进。
"""

import json
from datetime import datetime
from typing import Any

from core.config import Settings, get_settings
from core.logging_config import logger
from core.revise_loop import RevisionOutput


class EvolutionLog:
    """
    进化日志管理器

    记录每次提取的结果，特别是失败案例，用于后续 few-shot 学习。
    """

    def __init__(self, config: Settings | None = None):
        """
        初始化进化日志

        Args:
            config: 配置对象
        """
        self.config = config or get_settings()
        self.log_path = self.config.evolution_log_abs_path

        # 确保目录存在
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"EvolutionLog 已初始化，日志路径：{self.log_path}")

    def log(
        self,
        pdf_path: str,
        output: RevisionOutput,
        ground_truth: dict | None = None,
        extra_info: dict | None = None,
    ) -> None:
        """
        记录一次提取结果

        Args:
            pdf_path: PDF 文件路径
            output: 修订循环输出
            ground_truth: 标准答案（可选）
            extra_info: 额外信息（可选）
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "pdf_path": pdf_path,
            "status": output.status,
            "total_rounds": output.total_rounds,
            "reason": output.reason,
            "final_result": output.final_result.to_dict() if output.final_result else None,
            "rounds": [
                {
                    "round_num": r.round_num,
                    "score": r.score,
                    "feedback": r.feedback,
                    "success": r.success,
                }
                for r in output.rounds
            ],
        }

        # 如果有 ground truth，计算 accuracy
        if ground_truth and output.final_result:
            accuracy = self._calculate_accuracy(
                output.final_result, ground_truth, self.config.tolerance_percent
            )
            entry["accuracy"] = accuracy

        # 添加额外信息
        if extra_info:
            entry.update(extra_info)

        # 标记是否为失败案例
        entry["is_failure"] = self._is_failure(output, ground_truth)

        # 写入日志
        self._append_entry(entry)

        logger.info(f"已记录进化日志：{pdf_path}, 状态：{output.status}")

    def _append_entry(self, entry: dict) -> None:
        """
        追加条目到日志文件

        Args:
            entry: 日志条目
        """
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _is_failure(self, output: RevisionOutput, ground_truth: dict | None = None) -> bool:
        """
        判断是否为失败案例

        Args:
            output: 修订循环输出
            ground_truth: 标准答案

        Returns:
            是否失败
        """
        # 状态为 abstain 或 max_rounds
        if output.status in ["abstain", "max_rounds"]:
            return True

        # 如果有 ground truth，检查 accuracy
        if ground_truth and output.final_result:
            accuracy = self._calculate_accuracy(
                output.final_result, ground_truth, self.config.tolerance_percent
            )
            if accuracy < 0.5:  # 准确率低于 50% 视为失败
                return True

        # 评分过低
        if output.rounds:
            max_score = max(r.score for r in output.rounds)
            if max_score < 5:
                return True

        return False

    def _calculate_accuracy(self, result: Any, ground_truth: dict, tolerance: float) -> float:
        """
        计算提取准确率

        Args:
            result: 提取结果
            ground_truth: 标准答案
            tolerance: 容差（如 0.05 表示±5%）

        Returns:
            准确率 (0-1)
        """
        if not result.indicated and not result.inferred:
            return 0.0

        correct_count = 0
        total_count = 0

        # 检查 Indicated
        if ground_truth.get("indicated") and result.indicated:
            for key in ["ore_mt", "grade_value", "metal_oz", "metal_t"]:
                gt_val = ground_truth["indicated"].get(key)
                res_val = result.indicated.get(key)

                if gt_val is not None:
                    total_count += 1
                    if res_val is not None and self._within_tolerance(res_val, gt_val, tolerance):
                        correct_count += 1

        # 检查 Inferred
        if ground_truth.get("inferred") and result.inferred:
            for key in ["ore_mt", "grade_value", "metal_oz", "metal_t"]:
                gt_val = ground_truth["inferred"].get(key)
                res_val = result.inferred.get(key)

                if gt_val is not None:
                    total_count += 1
                    if res_val is not None and self._within_tolerance(res_val, gt_val, tolerance):
                        correct_count += 1

        if total_count == 0:
            return 0.0

        return correct_count / total_count

    def _within_tolerance(self, predicted: float, expected: float, tolerance: float) -> bool:
        """
        检查预测值是否在容差范围内

        Args:
            predicted: 预测值
            expected: 期望值
            tolerance: 相对容差（如 0.05 表示±5%）

        Returns:
            是否在容差范围内
        """
        if expected == 0:
            return abs(predicted - expected) < tolerance

        relative_error = abs(predicted - expected) / abs(expected)
        return relative_error <= tolerance

    def get_few_shot_examples(self, limit: int = 5, success_only: bool = True) -> list[dict]:
        """
        获取 few-shot 示例

        Args:
            limit: 最大返回数量
            success_only: 是否只返回成功案例

        Returns:
            few-shot 示例列表
        """
        if not self.log_path.exists():
            logger.warning(f"进化日志文件不存在：{self.log_path}")
            return []

        examples = []

        try:
            with open(self.log_path, encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())

                    if success_only and entry.get("is_failure", False):
                        continue

                    # 构建 few-shot 示例
                    example = {
                        "input_summary": f"PDF: {entry['pdf_path']}, 状态：{entry['status']}",
                        "output": entry.get("final_result"),
                    }
                    examples.append(example)

                    if len(examples) >= limit:
                        break

        except Exception as e:
            logger.error(f"读取进化日志失败：{e}")

        return examples

    def get_statistics(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        if not self.log_path.exists():
            return {}

        total = 0
        success = 0
        failure = 0
        abstain = 0
        total_rounds = 0
        accuracies = []

        try:
            with open(self.log_path, encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    total += 1

                    if entry.get("status") == "success":
                        success += 1
                    elif entry.get("status") == "abstain":
                        abstain += 1
                    else:
                        failure += 1

                    total_rounds += entry.get("total_rounds", 0)

                    if entry.get("accuracy") is not None:
                        accuracies.append(entry["accuracy"])

        except Exception as e:
            logger.error(f"读取进化日志失败：{e}")

        return {
            "total": total,
            "success": success,
            "failure": failure,
            "abstain": abstain,
            "success_rate": success / total if total > 0 else 0,
            "avg_rounds": total_rounds / total if total > 0 else 0,
            "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
        }


# 全局单例
_evolution_log: EvolutionLog | None = None


def get_evolution_log() -> EvolutionLog:
    """获取 EvolutionLog 单例"""
    global _evolution_log
    if _evolution_log is None:
        _evolution_log = EvolutionLog()
    return _evolution_log
