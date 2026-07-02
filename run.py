"""
NI 43101 提取系统 - 主入口

提供 CLI 和 Python API 两种使用方式。
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click

from core.config import get_settings, settings
from core.logging_config import logger
from core.pdf_parser import extract_resources_from_pdf
from core.revise_loop import run_extraction, RevisionOutput
from core.evolution_log import get_evolution_log, EvolutionLog
from eval.metrics import load_ground_truth, evaluate_single, generate_report


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    NI 43-101 资源量提取系统

    基于双 Agent 协作的矿业报告数据提取系统，支持自进化改进。

    使用示例:

        # 提取单个 PDF
        python run.py extract data/pdfs/sample.pdf

        # 批量提取并评测
        python run.py evaluate

        # 查看进化统计
        python run.py stats
    """
    # 确保目录存在
    settings.ensure_dirs()


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "--few-shot",
    "-f",
    type=click.Path(exists=True),
    help="Few-shot 示例 JSON 文件路径"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="输出结果路径 (JSON)"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="详细输出"
)
def extract(pdf_path: str, few_shot: Optional[str], output: Optional[str], verbose: bool):
    """
    提取单个 PDF 的资源量数据

    PDF_PATH: PDF 文件路径
    """
    # 加载 few-shot 示例
    few_shot_examples = None
    if few_shot:
        import json
        with open(few_shot, "r", encoding="utf-8") as f:
            few_shot_examples = json.load(f)

    # 运行提取
    logger.info(f"开始提取：{pdf_path}")

    async def run():
        return await run_extraction(pdf_path, few_shot_examples)

    output_result: RevisionOutput = asyncio.run(run())

    # 输出结果
    if verbose:
        click.echo("\n" + "=" * 60)
        click.echo("提取结果")
        click.echo("=" * 60)
        click.echo(f"状态：{output_result.status}")
        click.echo(f"总轮次：{output_result.total_rounds}")
        click.echo(f"原因：{output_result.reason or 'N/A'}")

        if output_result.final_result:
            click.echo("\nIndicated Resources:")
            click.echo(f"  {output_result.final_result.indicated}")
            click.echo("\nInferred Resources:")
            click.echo(f"  {output_result.final_result.inferred}")

        click.echo("\n修订历史:")
        for r in output_result.rounds:
            click.echo(f"  轮次 {r.round_num}: 评分={r.score}/10, 成功={r.success}")

    # 保存结果
    if output:
        import json
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_result.to_dict(), f, indent=2, ensure_ascii=False)
        click.echo(f"\n结果已保存：{output_path}")

    # 记录进化日志
    evol_log = get_evolution_log()
    evol_log.log(pdf_path, output_result)

    # 返回状态码
    if output_result.status == "success":
        sys.exit(0)
    else:
        sys.exit(1)


@main.command()
@click.option(
    "--truth",
    "-t",
    type=click.Path(exists=True),
    default="eval/ground_truth.json",
    help="Ground truth JSON 路径"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="eval/report.txt",
    help="评测报告输出路径"
)
@click.option(
    "--tolerance",
    type=float,
    default=0.05,
    help="容差（默认 0.05 表示±5%）"
)
def evaluate(truth: str, output: str, tolerance: float):
    """
    批量提取并评测

    使用 ground truth 评估提取准确率。
    """
    # 加载 ground truth
    ground_truths = load_ground_truth(truth)

    # 获取 PDF 列表
    pdf_dir = settings.pdf_data_abs_path
    if not pdf_dir.exists():
        click.echo(f"PDF 目录不存在：{pdf_dir}")
        sys.exit(1)

    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        click.echo(f"PDF 目录中没有找到 PDF 文件：{pdf_dir}")
        sys.exit(1)

    click.echo(f"找到 {len(pdf_files)} 个 PDF 文件")

    # 运行提取并评估
    results = []

    async def run_all():
        for pdf_file in pdf_files:
            pdf_name = pdf_file.name
            click.echo(f"\n处理：{pdf_name}")

            if pdf_name not in ground_truths:
                click.echo(f"  跳过：没有 ground truth")
                continue

            try:
                output_result = await run_extraction(str(pdf_file))

                eval_result = evaluate_single(
                    output_result,
                    ground_truths[pdf_name],
                    pdf_name,
                    tolerance
                )
                results.append((pdf_name, output_result, eval_result))

                # 记录进化日志
                evol_log = get_evolution_log()
                evol_log.log(
                    pdf_name,
                    output_result,
                    ground_truths[pdf_name]
                )

            except Exception as e:
                click.echo(f"  错误：{e}")
                logger.error(f"处理 {pdf_name} 失败：{e}", exc_info=True)

    asyncio.run(run_all())

    # 生成报告
    from eval.metrics import EvalResult
    eval_results = [r[2] for r in results]
    report = generate_report(eval_results)

    # 保存报告
    save_report(report, output)
    click.echo(f"\n评测报告已保存：{output}")

    # 输出摘要
    click.echo("\n" + report)


@main.command()
def stats():
    """查看进化日志统计信息"""
    evol_log = get_evolution_log()
    stats = evol_log.get_statistics()

    if not stats:
        click.echo("进化日志为空")
        return

    click.echo("\n" + "=" * 60)
    click.echo("进化日志统计")
    click.echo("=" * 60)
    click.echo(f"总记录数：{stats.get('total', 0)}")
    click.echo(f"成功：{stats.get('success', 0)}")
    click.echo(f"失败：{stats.get('failure', 0)}")
    click.echo(f"Abstain: {stats.get('abstain', 0)}")
    click.echo(f"成功率：{stats.get('success_rate', 0)*100:.1f}%")
    click.echo(f"平均修订轮次：{stats.get('avg_rounds', 0):.1f}")
    click.echo(f"平均准确率：{stats.get('avg_accuracy', 0)*100:.1f}%")


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True))
def parse(pdf_path: str):
    """
    解析 PDF 表格（不调用 LLM）

    用于调试 PDF 解析功能。
    """
    tables = extract_resources_from_pdf(pdf_path)

    click.echo(f"\n解析结果：{len(tables)} 条记录\n")

    for i, table in enumerate(tables, 1):
        click.echo(f"[{i}] {table.resource_type}")
        click.echo(f"    矿石量：{table.ore_mt} Mt")
        click.echo(f"    品位：{table.grade_value} {table.grade_unit}")
        click.echo(f"    金属量：{table.metal_oz} oz / {table.metal_t} t")
        click.echo(f"    矿种：{table.commodity}")
        click.echo(f"    页码：{table.source_page}")
        click.echo(f"    置信度：{table.confidence}")
        click.echo("")


if __name__ == "__main__":
    main()
