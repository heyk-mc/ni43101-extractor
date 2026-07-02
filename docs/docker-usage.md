# Docker 使用指南

## 前置要求

- Docker Desktop for Windows (已安装并运行)
- Docker Compose v2+（已包含在 Docker Desktop 中）

**启动 Docker Desktop:**
1. 打开 Docker Desktop 应用程序
2. 等待状态显示 "Engine running"
3. 在终端运行 `docker info` 验证

## 快速开始

### 前置准备

**在构建镜像之前**，需要完成以下准备：

```bash
# 1. 创建环境变量文件
cp .env.example .env
# 编辑 .env 填入 API Keys

# 2. 创建进化日志文件（避免 Docker 创建目录）
touch data/evolution.jsonl

# 3. 准备 PDF 文件目录
mkdir -p data/pdfs
cp your-report.pdf data/pdfs/
```

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
