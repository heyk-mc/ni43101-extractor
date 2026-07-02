# 快速安装指南

## 系统要求

- Python 3.10+
- pip 或 uv
- Git

## 方法一：使用 pip（推荐）

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd ni43101-extractor
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，填入你的 API Keys
# - ANTHROPIC_API_KEY: https://console.anthropic.com/settings/keys
# - DASHSCOPE_API_KEY: https://dashscope.console.aliyun.com/apiKey (可选)
```

### 5. 验证安装

```bash
# 查看帮助
python run.py --help

# 查看版本
python run.py --version
```

---

## 方法二：使用 uv（更快）

[uv](https://github.com/astral-sh/uv) 是一个超快的 Python 包管理器。

### 1. 安装 uv

```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 创建虚拟环境并安装

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 3. 验证安装

```bash
python run.py --help
```

---

## 方法三：从 PyPI 安装（发布后）

```bash
pip install ni43101-extractor
```

---

## 安装 pre-commit Hooks（可选）

pre-commit 可以在每次提交前自动运行代码检查。

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 hooks
pre-commit install

# 手动运行
pre-commit run --all-files
```

---

## 安装开发依赖（可选）

如果你需要开发或贡献代码：

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 或
pip install pytest pytest-asyncio pytest-cov ruff black mypy pre-commit
```

---

## 常见问题

### Q: 安装时出现 "No module named 'xxx'" 错误

A: 确保虚拟环境已激活：
- Windows: `.venv\Scripts\activate`
- Linux/Mac: `source .venv/bin/activate`

### Q: API Key 配置后仍然报错

A: 检查 `.env` 文件格式：
- 不要有多余的空格
- API Key 必须完整
- 重启 Python 进程

### Q: PDF 解析失败

A: 确保安装了所有依赖：
```bash
pip install pdfplumber pypdf
```

### Q: 内存不足

A: 大型 PDF 可能需要更多内存：
- 关闭其他应用
- 增加虚拟内存
- 考虑分割 PDF

---

## 下一步

安装完成后，查看 [README.md](README.md) 了解如何使用：

```bash
# 提取单个 PDF
python run.py extract data/pdfs/sample.pdf -v

# 批量评测
python run.py evaluate
```
