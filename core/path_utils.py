"""
路径工具模块

提供安全的路径处理，防止路径穿越攻击。
"""

from pathlib import Path


class PathSecurityError(ValueError):
    """路径安全检查失败时抛出的异常"""

    pass


def safe_path(user_path: str, base_dir: str | Path) -> Path:
    """
    安全检查用户传入的路径，防止路径穿越攻击

    Args:
        user_path: 用户传入的路径（可以是相对路径或文件名）
        base_dir: 允许的基准目录

    Returns:
        安全的绝对路径

    Raises:
        PathSecurityError: 路径超出允许范围

    Example:
        >>> safe_path("data.pdf", "/app/data")
        PosixPath('/app/data/data.pdf')

        >>> safe_path("../etc/passwd", "/app/data")
        PathSecurityError: 路径超出允许范围
    """
    base = Path(base_dir).resolve()

    # 处理用户路径
    user_path_obj = Path(user_path)

    # 如果是绝对路径，检查是否在 base 目录下
    if user_path_obj.is_absolute():
        target = user_path_obj.resolve()
    else:
        # 相对路径，拼接到 base 目录
        target = (base / user_path_obj).resolve()

    # 检查是否在 base 目录下
    try:
        target.relative_to(base)
    except ValueError:
        raise PathSecurityError(
            f"路径超出允许范围：{user_path} " f"(基准目录：{base}, 解析路径：{target})"
        )

    return target


def validate_pdf_path(pdf_filename: str, pdf_data_dir: Path) -> Path:
    """
    验证 PDF 文件路径

    Args:
        pdf_filename: PDF 文件名
        pdf_data_dir: PDF 数据目录

    Returns:
        PDF 文件绝对路径

    Raises:
        PathSecurityError: 路径不安全
        FileNotFoundError: 文件不存在
    """
    # 安全检查路径
    pdf_path = safe_path(pdf_filename, pdf_data_dir)

    # 检查文件是否存在
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

    # 检查文件扩展名
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"文件不是 PDF 格式：{pdf_path}")

    return pdf_path
