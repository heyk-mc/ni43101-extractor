"""
配置管理模块

从环境变量读取配置，提供类型安全的配置访问。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    系统配置类

    所有配置项从环境变量读取，支持 .env 文件加载。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------
    # DeepSeek API 配置 (Extractor Agent)
    # -----------------------------
    deepseek_api_key: str
    deepseek_model: str = "deepseek-v4-pro"

    # -----------------------------
    # DashScope API 配置 (CriticMaster Agent - Qwen)
    # -----------------------------
    dashscope_api_key: str | None = None
    qwen_model: str = "qwen3.5-plus"

    # -----------------------------
    # 日志配置
    # -----------------------------
    log_level: str = "INFO"

    # -----------------------------
    # 系统配置
    # -----------------------------
    max_revise_rounds: int = 3
    score_threshold: float = 8.0
    tolerance_percent: float = 0.05

    # -----------------------------
    # 路径配置
    # -----------------------------
    pdf_data_dir: str = "data/pdfs"
    evolution_log_path: str = "data/evolution.jsonl"
    log_dir: str = "logs"

    # -----------------------------
    # 派生属性
    # -----------------------------
    @property
    def project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).resolve().parents[1]

    @property
    def pdf_data_abs_path(self) -> Path:
        """获取 PDF 数据目录绝对路径"""
        return self.project_root / self.pdf_data_dir

    @property
    def evolution_log_abs_path(self) -> Path:
        """获取进化日志绝对路径"""
        return self.project_root / self.evolution_log_path

    @property
    def log_abs_path(self) -> Path:
        """获取日志目录绝对路径"""
        return self.project_root / self.log_dir

    def ensure_dirs(self) -> None:
        """确保所有配置的目录存在"""
        self.pdf_data_abs_path.mkdir(parents=True, exist_ok=True)
        self.evolution_log_abs_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_abs_path.mkdir(parents=True, exist_ok=True)


# 全局单例配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取全局配置实例"""
    return settings
