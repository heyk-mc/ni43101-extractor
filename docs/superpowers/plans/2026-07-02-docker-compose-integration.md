# Docker Compose 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ni43101-extractor 项目集成到 Docker Compose 环境，支持多阶段构建和多种运行模式

**Architecture:** 采用多阶段 Docker 构建，分离构建时和运行时依赖；使用 docker-compose 编排服务，挂载数据卷实现 PDF 输入、日志输出和进化日志持久化

**Tech Stack:** Docker (多阶段构建), Docker Compose, Python 3.10+, poetry/pip

---

## 文件结构

### 创建文件
- `docker/Dockerfile` - 多阶段构建配置
- `docker-compose.yml` - 服务编排配置
- `.dockerignore` - Docker 忽略文件
- `docs/superpowers/plans/docker-usage.md` - 使用文档

### 修改文件
- `README.md` - 添加 Docker 使用说明

---

## Task 1: 创建 .dockerignore 文件

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: 创建 .dockerignore 文件**

```dockerignore
# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# 测试和覆盖率
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# 构建产物
*.egg-info/
*.egg
dist/
build/

# 日志和数据
logs/
*.log
data/evolution.jsonl
data/pdfs/

# 环境配置
.env
.env.local

# 文档
docs/
*.md
!README.md

# Docker 配置
docker-compose.override.yml
```

- [ ] **Step 2: 验证 .dockerignore 语法**

```bash
# 检查文件是否存在且格式正确
cat .dockerignore
```

Expected: 显示上述内容

- [ ] **Step 3: 提交**

```bash
git add .dockerignore
git commit -m "feat: add .dockerignore for Docker build optimization"
```

---

## Task 2: 创建多阶段 Dockerfile

**Files:**
- Create: `docker/Dockerfile`

- [ ] **Step 1: 创建多阶段 Dockerfile**

```dockerfile
# ========================================
# Stage 1: 构建阶段
# ========================================
FROM python:3.10-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ========================================
# Stage 2: 运行阶段
# ========================================
FROM python:3.10-slim as runtime

# 设置工作目录
WORKDIR /app

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装运行时依赖（pdfplumber 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

# 创建数据目录
RUN mkdir -p /app/data/pdfs /app/logs && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 复制应用代码
COPY --chown=appuser:appuser \
    agents/ /app/agents/
COPY --chown=appuser:appuser \
    core/ /app/core/
COPY --chown=appuser:appuser \
    eval/ /app/eval/
COPY --chown=appuser:appuser \
    run.py /app/
COPY --chown=appuser:appuser \
    pyproject.toml /app/
COPY --chown=appuser:appuser \
    __init__.py /app/

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 挂载点声明
VOLUME ["/app/data/pdfs", "/app/logs", "/app/data"]

# 健康检查（检查 Python 环境是否正常）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 默认命令
CMD ["python", "run.py", "--help"]
```

- [ ] **Step 2: 验证 Dockerfile 语法**

```bash
# 检查 Dockerfile 语法（需要 Docker）
docker build -f docker/Dockerfile --check .
```

Expected: 语法检查通过

- [ ] **Step 3: 提交**

```bash
git add docker/Dockerfile
git commit -m "feat: add multi-stage Dockerfile for optimized image size"
```

---

## Task 3: 创建 docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 docker-compose.yml 文件**

```yaml
version: "3.8"

services:
  extractor:
    build:
      context: .
      dockerfile: docker/Dockerfile
      target: runtime
    image: ni43101-extractor:latest
    container_name: ni43101-extractor
    restart: "no"

    # 环境变量
    env_file:
      - .env

    # 环境变量覆盖（可选）
    environment:
      - LOG_LEVEL=INFO

    # 数据卷挂载
    volumes:
      # PDF 输入目录（只读）
      - ./data/pdfs:/app/data/pdfs:ro
      # 进化日志（读写）
      - ./data/evolution.jsonl:/app/data/evolution.jsonl
      # 日志输出目录（读写）
      - ./logs:/app/logs
      # 环境变量文件（只读）
      - ./.env:/app/.env:ro

    # 工作目录
    working_dir: /app

    # 覆盖默认命令
    # command: ["python", "run.py", "extract", "data/pdfs/sample.pdf", "-v"]

    # 网络配置
    networks:
      - extractor-network

  # 批量处理服务（可选）
  batch-extractor:
    extends:
      service: extractor
    container_name: ni43101-extractor-batch
    command: ["python", "run.py", "evaluate"]
    profiles:
      - batch

  # 统计服务（可选）
  stats:
    extends:
      service: extractor
    container_name: ni43101-extractor-stats
    command: ["python", "run.py", "stats"]
    profiles:
      - stats

# 网络配置
networks:
  extractor-network:
    driver: bridge

# 卷声明（可选，用于持久化）
volumes:
  pdf-data:
  logs:
```

- [ ] **Step 2: 验证 docker-compose.yml 语法**

```bash
# 检查 docker-compose.yml 语法
docker compose config
```

Expected: 显示解析后的配置，无错误

- [ ] **Step 3: 提交**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml for service orchestration"
```

---

## Task 4: 创建 Docker 使用文档

**Files:**
- Create: `docs/docker-usage.md`

- [ ] **Step 1: 创建 Docker 使用文档**

```markdown
# Docker 使用指南

## 快速开始

### 1. 构建镜像

```bash
# 构建镜像
docker compose build

# 或单独构建
docker build -f docker/Dockerfile -t ni43101-extractor:latest .
```

### 2. 配置环境变量

```bash
# 复制环境变量示例
cp .env.example .env

# 编辑 .env 文件，填入 API Keys
# - DEEPSEEK_API_KEY=sk-xxx
# - DASHSCOPE_API_KEY=sk-xxx
```

### 3. 准备 PDF 文件

将 NI 43-101 PDF 文件放入 `data/pdfs/` 目录：

```bash
mkdir -p data/pdfs
cp your-report.pdf data/pdfs/
```

### 4. 运行提取

```bash
# 查看帮助
docker compose run extractor

# 提取单个 PDF
docker compose run extractor python run.py extract data/pdfs/your-report.pdf -v

# 保存结果为 JSON
docker compose run extractor python run.py extract data/pdfs/your-report.pdf -o output/result.json

# 使用 few-shot 示例
docker compose run extractor python run.py extract data/pdfs/your-report.pdf -f data/evolution.jsonl -v
```

### 5. 批量处理

```bash
# 运行批量提取和评测
docker compose --profile batch run batch-extractor

# 查看统计信息
docker compose --profile stats run stats
```

### 6. 查看日志

```bash
# 查看提取日志
tail -f logs/extractor_*.log
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 必填 |
| `DEEPSEEK_MODEL` | DeepSeek 模型 | `deepseek-v4-pro` |
| `DASHSCOPE_API_KEY` | DashScope API 密钥 | 必填 |
| `QWEN_MODEL` | Qwen 模型 | `qwen3.5-plus` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MAX_REVISE_ROUNDS` | 最大修订轮次 | `3` |
| `SCORE_THRESHOLD` | 评分阈值 | `8.0` |

## 数据卷

| 挂载点 | 说明 | 模式 |
|--------|------|------|
| `./data/pdfs:/app/data/pdfs` | PDF 输入目录 | 只读 |
| `./data/evolution.jsonl:/app/data/evolution.jsonl` | 进化日志 | 读写 |
| `./logs:/app/logs` | 日志输出目录 | 读写 |
| `./.env:/app/.env` | 环境变量文件 | 只读 |

## 常见问题

### 镜像大小

使用多阶段构建后，运行时镜像约 500MB。如需进一步减小：
- 使用 Alpine 基础镜像（需要处理兼容性问题）
- 移除不需要的依赖

### 权限问题

容器内使用非 root 用户（`appuser`, UID 1000）。如遇到权限问题：
```bash
# 确保本地目录权限匹配
chown -R 1000:1000 data/ logs/
```

### 网络超时

API 调用超时可能是网络问题。可尝试：
```bash
# 增加超时时间（需要修改代码）
# 或使用代理
docker compose run --env HTTP_PROXY=http://proxy:port extractor ...
```
```

- [ ] **Step 2: 提交**

```bash
git add docs/docker-usage.md
git commit -m "docs: add Docker usage guide"
```

---

## Task 5: 更新 README.md 添加 Docker 说明

**Files:**
- Modify: `README.md:31-95`（快速开始部分）

- [ ] **Step 1: 在 README.md 中添加 Docker 快速开始**

在原有"快速开始"章节前添加新的"Docker 快速开始"章节：

```markdown
## Docker 快速开始

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

## 传统安装方式
```

- [ ] **Step 2: 验证 README.md 格式**

```bash
# 检查 Markdown 语法（可选）
cat README.md | head -150
```

Expected: 显示更新后的 README，包含 Docker 和传统安装两种说明

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: add Docker quick start to README"
```

---

## Task 6: 测试 Docker 构建和运行

**Files:**
- Test: 手动测试 Docker 功能

- [ ] **Step 1: 构建 Docker 镜像**

```bash
docker compose build
```

Expected: 构建成功，输出类似：
```
=> [internal] load build definition from Dockerfile
=> => transferring dockerfile: 2.34kB
=> [builder 3/4] RUN pip install --no-cache-dir -r requirements.txt
=> [runtime 5/7] COPY --from=builder /opt/venv /opt/venv
Successfully built ni43101-extractor:latest
```

- [ ] **Step 2: 查看镜像大小**

```bash
docker images ni43101-extractor
```

Expected: 显示镜像信息，大小约 500-700MB

- [ ] **Step 3: 测试帮助命令**

```bash
docker compose run extractor
```

Expected: 显示 CLI 帮助信息

- [ ] **Step 4: 测试 PDF 解析命令**

```bash
docker compose run extractor python run.py parse data/pdfs/test_ni43101.pdf
```

Expected: 显示 PDF 表格内容

- [ ] **Step 5: 验证数据卷挂载**

```bash
# 运行后检查日志目录
ls -la logs/

# 检查 evolution.jsonl
cat data/evolution.jsonl
```

Expected: 日志文件和进化日志正确生成

- [ ] **Step 6: 清理测试容器**

```bash
docker compose down --remove-orphans
```

---

## 验收标准

- [ ] `.dockerignore` 正确排除不必要的文件
- [ ] `docker/Dockerfile` 使用多阶段构建
- [ ] `docker-compose.yml` 正确配置服务和数据卷
- [ ] 镜像大小 < 700MB
- [ ] 能够成功运行 `docker compose run extractor`
- [ ] PDF 解析功能正常工作
- [ ] 日志和进化日志正确写入挂载目录
- [ ] README.md 包含 Docker 使用说明

---

## 备注

- Python 版本：3.10-slim
- 镜像大小目标：500-700MB
- 构建时间目标：< 5 分钟（有缓存时 < 1 分钟）
- 运行模式：CLI 命令（非 Web 服务）
