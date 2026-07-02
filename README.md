# NI 43-101 资源量提取系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**基于双 Agent 协作的矿业报告数据提取系统，支持自进化改进。**

---

## 项目简介

本系统从 NI 43-101 格式的技术报告中自动提取资源量数据（Indicated Resources 和 Inferred Resources），采用双 Agent 协作架构：

- **Extractor Agent**: 使用强模型（Claude）进行数据提取
- **CriticMaster Agent**: 使用弱模型（Qwen）进行质量评分
- **Revise Loop**: 最多 3 轮修订，超过则返回 abstain
- **Evolution Log**: 失败案例自动积累为 few-shot 示例

### 核心特性

| 特性 | 说明 |
|------|------|
| **双模型校验** | 强模型提取 + 弱模型评分，成本与质量平衡 |
| **自进化机制** | 失败案例自动积累，持续改进提取质量 |
| **Abstain 机制** | 不确定时返回 abstain，而非硬编答案 |
| **工程化规范** | 类型注解、Lint 检查、单元测试、CI/CD |

---

## Docker 快速开始

### 前置准备

**在构建镜像之前**，需要完成以下准备：

```bash
# 1. 创建环境变量文件
cp .env.example .env
# 编辑 .env 填入 API Keys

# 2. 创建进化日志文件（避免 Docker 创建目录）
touch data/evolution.jsonl
```

### 1. 克隆项目并进入目录

```bash
git clone https://github.com/heyk-mc/ni43101-extractor.git
cd ni43101-extractor
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Keys
```

### 3. 准备 PDF 文件

```bash
mkdir -p data/pdfs
cp your-report.pdf data/pdfs/
```

### 4. 构建并运行

```bash
# 构建镜像
docker compose build

# 提取单个 PDF
docker compose run extractor python run.py extract data/pdfs/your-report.pdf -v

# 批量评测
docker compose --profile batch run batch-extractor
```

---

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 或从 pyproject.toml 安装
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 填入 API Keys
# - ANTHROPIC_API_KEY: Claude API 密钥
# - DASHSCOPE_API_KEY: Qwen API 密钥（可选）
```

### 3. 准备 PDF 文件

将 NI 43-101 PDF 文件放入 `data/pdfs/` 目录：

```bash
data/pdfs/
├── newmont_2024.pdf
├── barrick_2024.pdf
└── pilbara_2024.pdf
```

### 4. 运行提取

```bash
# 提取单个 PDF
python run.py extract data/pdfs/sample.pdf -v

# 使用 few-shot 示例
python run.py extract data/pdfs/sample.pdf -f data/evolution.jsonl -v

# 保存结果为 JSON
python run.py extract data/pdfs/sample.pdf -o output/result.json
```

### 5. 运行评测

```bash
# 批量提取并评测
python run.py evaluate

# 指定 ground truth 路径
python run.py evaluate -t eval/ground_truth.json -o eval/report.txt

# 查看进化统计
python run.py stats
```

---

## 项目结构

```
ni43101-extractor/
├── agents/                      # Agent 实现
│   ├── __init__.py
│   ├── extractor_agent.py       # 强模型提取 Agent (Claude)
│   └── critic_master.py         # 弱模型评分 Agent (Qwen)
├── core/                        # 核心逻辑
│   ├── __init__.py
│   ├── config.py                # 配置管理
│   ├── logging_config.py        # 日志配置
│   ├── path_utils.py            # 路径工具（安全校验）
│   ├── pdf_parser.py            # PDF 解析模块
│   ├── revise_loop.py           # 修订循环控制器
│   └── evolution_log.py         # 进化日志管理
├── eval/                        # 评测模块
│   ├── __init__.py
│   ├── metrics.py               # 准确率计算
│   └── ground_truth.json        # 标准答案
├── tests/                       # 单元测试
│   ├── __init__.py
│   ├── test_pdf_parser.py
│   ├── test_extractor.py
│   └── test_revise_loop.py
├── data/
│   ├── pdfs/                    # PDF 文件目录
│   └── evolution.jsonl          # 进化日志
├── logs/                        # 日志目录
├── .env.example                 # 环境变量示例
├── .gitignore
├── pyproject.toml               # 项目配置
├── requirements.txt             # 依赖列表
├── run.py                       # 主入口
└── README.md
```

---

## CLI 命令

```bash
# 查看帮助
python run.py --help

# 提取单个 PDF
python run.py extract <pdf_path> [-f few_shot] [-o output] [-v]

# 批量评测
python run.py evaluate [-t truth] [-o output] [--tolerance]

# 查看统计
python run.py stats

# 解析 PDF 表格（调试用）
python run.py parse <pdf_path>
```

---

## API 使用

```python
import asyncio
from core.revise_loop import run_extraction
from core.evolution_log import get_evolution_log

async def main():
    # 运行提取
    result = await run_extraction("data/pdfs/sample.pdf")

    print(f"状态：{result.status}")
    print(f"总轮次：{result.total_rounds}")

    if result.final_result:
        print(f"Indicated: {result.final_result.indicated}")
        print(f"Inferred: {result.final_result.inferred}")

    # 记录进化日志
    evol_log = get_evolution_log()
    evol_log.log("sample.pdf", result)

asyncio.run(main())
```

---

## 评测指标

| 指标 | 说明 |
|------|------|
| **Accuracy@5%** | 提取值与 ground truth 容差±5% 的准确率 |
| **Abstain Rate** | 不确定时 abstain 的比例（应高于硬编） |
| **Avg Rounds** | 平均修订轮次（越低越好） |
| **Success Rate** | 成功率（status=success 的比例） |

---

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | 必填 |
| `ANTHROPIC_MODEL` | Claude 模型 | `claude-sonnet-4-20250514` |
| `DASHSCOPE_API_KEY` | Qwen API 密钥 | 可选 |
| `QWEN_MODEL` | Qwen 模型 | `qwen-max` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MAX_REVISE_ROUNDS` | 最大修订轮次 | `3` |
| `SCORE_THRESHOLD` | 评分阈值 | `8` |
| `TOLERANCE_PERCENT` | 评测容差 | `0.05` |

---

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ -v --cov=agents --cov=core --cov-report=html

# 运行单个测试
pytest tests/test_pdf_parser.py -v
```

### 代码检查

```bash
# Ruff 检查
ruff check .

# Black 格式化检查
black --check .

# Mypy 类型检查
mypy agents/ core/ eval/
```

### Pre-commit Hooks

```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 手动运行
pre-commit run --all-files
```

---

## 技术亮点

### 1. 双 Agent 协作

```
Extractor Agent (Claude)
         ↓
    提取结果
         ↓
CriticMaster Agent (Qwen)
         ↓
      评分
         ↓
   评分 >= 8? ──→ 成功
         ↓ 否
   修订轮次 < 3? ──→ 继续修订
         ↓ 否
       Abstain
```

### 2. 自进化机制

每次提取的结果（特别是失败案例）自动记录到 `evolution.jsonl`：

```jsonl
{"timestamp": "2026-07-02T10:00:00", "pdf": "sample.pdf", "status": "abstain", "reason": "...", "is_failure": true}
{"timestamp": "2026-07-02T10:30:00", "pdf": "sample2.pdf", "status": "success", "accuracy": 0.95, "is_failure": false}
```

这些案例可用于后续 few-shot 学习，持续提升提取质量。

### 3. Abstain 机制

系统在以下情况返回 abstain：
- 达到最大修订轮次（3 轮）后评分仍未达标
- PDF 中未检测到资源量表格
- 模型多次提取失败

这确保系统不会硬编答案，提升可信度。

---

## 许可证

MIT License

---

## 联系方式

- 作者：Your Name
- 邮箱：your.email@example.com
