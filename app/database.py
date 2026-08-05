"""
数据库模块：SQLAlchemy 引擎、会话工厂与 ORM 模型。

设计说明：
- 使用 SQLAlchemy 2.0 风格（DeclarativeBase + Mapped），类型提示更清晰。
- SQLite 设置 check_same_thread=False，允许 FastAPI 在不同工作线程/协程
  中复用连接池，避免 "SQLite objects created in a thread can only be used
  in that same thread" 错误。
- Session 通过依赖注入按需创建、用完即关，防止连接泄漏。
"""

from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings

settings = get_settings()

# ---------- 引擎与会话工厂 ----------

# connect_args 仅对 SQLite 生效；其他数据库（如 PostgreSQL）会忽略此参数
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # 允许多线程访问同一连接
    echo=settings.is_development,               # 开发环境打印 SQL，便于调试
)

# autocommit=False：由业务代码显式 commit，保证事务可控
# autoflush=False：避免在 query 前意外 flush，减少隐式写入
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------- ORM 基类 ----------


class Base(DeclarativeBase):
    """所有 ORM 模型的基类，便于 Alembic 迁移时统一扫描 metadata。"""


# ---------- Message 模型 ----------


class Message(Base):
    """
    对话消息表：记录多 Agent 协作过程中每条消息的完整上下文。

    字段设计理由：
    - session_id：同一会话内多条消息归属同一用户对话，便于按会话查询历史。
    - role：区分 user / assistant / system，对齐主流 LLM 消息格式。
    - agent_type：标识由哪个 Agent 产生（如 planner、coder、reviewer），
      支持后续按 Agent 维度统计与回放。
    - content：消息正文，使用 Text 类型以支持长文本（简历、代码块等）。
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),  # 统一使用 UTC，避免时区混乱
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} session_id={self.session_id!r} "
            f"role={self.role!r} agent_type={self.agent_type!r}>"
        )


# ---------- 数据库初始化 ----------


def init_db() -> None:
    """
    创建所有表（若不存在）。

    为什么不用 Alembic 做最简版本：
    - 当前只有一张表，create_all 足够；后续表结构变复杂时再引入迁移工具。
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖项：每个请求获取独立 Session，请求结束后自动关闭。

    使用 yield 模式是 FastAPI 官方推荐的数据库会话生命周期管理方式。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
