"""
日志配置模块

提供结构化日志配置，支持控制台和文件双输出。
"""

import logging
import sys
from datetime import datetime

from core.config import settings


def setup_logging() -> logging.Logger:
    """
    配置结构化日志

    Returns:
        配置好的 logger 实例
    """
    # 创建日志目录
    log_dir = settings.log_abs_path
    log_dir.mkdir(parents=True, exist_ok=True)

    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"extractor_{timestamp}.log"

    # 日志格式
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 创建 logger
    logger = logging.getLogger("ni43101_extractor")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 清除已有 handler
    logger.handlers.clear()

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)

    # 文件 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)

    # 抑制第三方库的冗余日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    logging.getLogger("pypdf").setLevel(logging.WARNING)

    logger.info(f"日志系统已初始化，日志文件：{log_file}")

    return logger


# 全局 logger 实例
logger = setup_logging()


def get_logger(name: str = "ni43101_extractor") -> logging.Logger:
    """
    获取命名 logger

    Args:
        name: logger 名称

    Returns:
        logger 实例
    """
    return logging.getLogger(name)
