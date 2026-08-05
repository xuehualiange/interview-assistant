"""
应用配置模块：集中管理环境变量与运行时参数。

设计说明：
- 使用 pydantic-settings 而非手写 os.getenv，可在启动时自动校验类型、
  提供默认值，并在缺少必填项时给出清晰的错误提示。
- 将 DeepSeek 相关配置单独分组，后续接入多个 LLM 提供商时只需扩展此类。
- 通过 lru_cache 单例化 Settings，避免每次请求重复读取 .env 文件。
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量 / .env 文件加载的应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",           # 本地开发时自动读取 .env
        env_file_encoding="utf-8",
        case_sensitive=False,      # 环境变量名大小写不敏感，降低部署出错概率
        extra="ignore",            # 忽略未声明的变量，避免无关 env 导致启动失败
    )

    # ---------- 应用基础配置 ----------
    app_env: Literal["development", "production"] = "development"
    app_name: str = "Multi-Agent Backend"
    debug: bool = Field(default=True, description="开发模式是否开启调试")

    # ---------- DeepSeek API 配置 ----------
    # 必填：没有 API Key 则 Agent 无法调用大模型，启动时应尽早暴露此问题
    deepseek_api_key: str = Field(..., description="DeepSeek API 密钥")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API 基础地址，便于切换代理或私有部署",
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="默认使用的模型名称",
    )

    # ---------- 数据库配置 ----------
    database_url: str = Field(
        default="sqlite:///./app.db",
        description="SQLAlchemy 数据库连接 URL",
    )

    @property
    def is_development(self) -> bool:
        """是否为开发环境，便于在 main.py 中条件性开启文档页等。"""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """
    获取全局唯一的 Settings 实例（依赖注入时使用）。

    为什么用 lru_cache：
    - FastAPI 的 Depends(get_settings) 会在每个请求中调用此函数，
      缓存后可保证配置只解析一次，性能更好且行为一致。
    """
    return Settings()
