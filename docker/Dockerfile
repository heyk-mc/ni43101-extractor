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
