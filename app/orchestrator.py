"""
会话编排器：串联 Triage → 保护机制 → Specialist 流式输出。

设计说明：
- 单一入口 handle_message()，上层（FastAPI SSE 路由）只需调用此方法
- 保护机制在 Specialist 调用前/后各执行一次，形成完整闭环
- 会话状态从 Message 表读取，保证重启后仍有效
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent import TriageAgent, TriageResult, get_triage_agent
from app.database import Message
from app.protection import (
    AgentProtection,
    LOOP_DETECTION_THRESHOLD,
    MaxTurnsExceededError,
    RouteDecision,
    SessionGuardState,
)
from app.specialists import ChatTurn, SpecialistRegistry, get_specialist_registry

logger = logging.getLogger(__name__)


def load_session_state(db: Session, session_id: str) -> SessionGuardState:
    """
    从数据库加载会话保护所需快照。

    turn_count：user 角色消息数 + 1（含即将处理的当前轮）
    recent_agents：最近 assistant 消息的 agent_type，用于循环检测
    """
    user_turn_count = db.scalar(
        select(func.count(Message.id)).where(
            Message.session_id == session_id,
            Message.role == "user",
        )
    ) or 0

    recent_rows = db.scalars(
        select(Message.agent_type)
        .where(
            Message.session_id == session_id,
            Message.role == "assistant",
            Message.agent_type.isnot(None),
        )
        .order_by(Message.created_at.desc())
        .limit(LOOP_DETECTION_THRESHOLD)
    ).all()

    # DB 查出来是倒序，翻转成时间正序供循环检测使用
    recent_agents = [row for row in reversed(recent_rows) if row]

    return SessionGuardState(
        session_id=session_id,
        turn_count=user_turn_count + 1,
        recent_agents=recent_agents,
    )


def load_chat_history(db: Session, session_id: str, limit: int = 20) -> list[ChatTurn]:
    """加载最近 N 条对话历史，供 Specialist 构建上下文。"""
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    history: list[ChatTurn] = []
    for msg in reversed(rows):
        if msg.role in ("user", "assistant"):
            history.append((msg.role, msg.content))
    return history


def save_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    agent_type: str | None = None,
) -> None:
    """持久化一条消息并提交。"""
    db.add(
        Message(
            session_id=session_id,
            role=role,
            content=content,
            agent_type=agent_type,
        )
    )
    db.commit()


def delete_session(db: Session, session_id: str) -> int:
    """删除指定 session 的全部消息，返回删除条数。"""
    messages = db.scalars(
        select(Message).where(Message.session_id == session_id)
    ).all()
    count = len(messages)
    for msg in messages:
        db.delete(msg)
    db.commit()
    return count


def get_session_history(db: Session, session_id: str) -> list[Message]:
    """按时间正序返回 session 全部对话消息。"""
    return list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        ).all()
    )


class AgentOrchestrator:
    """
    多 Agent 协作编排器。

    一次完整请求的处理流程：
      1. 加载 session 状态
      2. 保护 #1：检查最大轮次
      3. Triage 意图识别
      4. 保护 #2 #3：循环检测 + 错误降级 → 得到 RouteDecision
      5. Specialist 流式回答
      6. 保护 #4：异常时回退通用回答
      7. 持久化 user / assistant 消息
    """

    def __init__(
        self,
        triage: TriageAgent | None = None,
        registry: SpecialistRegistry | None = None,
        protection: AgentProtection | None = None,
    ) -> None:
        self._triage = triage or get_triage_agent()
        self._registry = registry or get_specialist_registry()
        self._protection = protection or AgentProtection()

    async def handle_message(
        self,
        db: Session,
        session_id: str,
        user_input: str,
    ) -> AsyncIterator[str | RouteDecision]:
        """
        处理单条用户消息，yield 路由决策（首包）与后续文本 chunk。

        首包 RouteDecision 供 SSE 层推送 meta 事件（agent_type、是否切换等）；
        后续 str chunk 为 Specialist 流式正文。
        """
        user_input = user_input.strip()
        if not user_input:
            yield self._protection.get_fallback_response()
            return

        state = load_session_state(db, session_id)

        # ----- 保护 #1：最大轮次 -----
        try:
            self._protection.check_max_turns(state)
        except MaxTurnsExceededError as exc:
            yield str(exc)
            return

        # ----- Triage 意图识别（保护 #3 在其后 resolve_route 中处理）-----
        triage: TriageResult | None = None
        try:
            triage = await self._triage.classify_async(user_input)
        except Exception as exc:
            logger.warning("Triage 异常，将降级至默认 Agent: %s", exc)

        decision = self._protection.resolve_route(triage, state)
        yield decision  # 首包：路由元信息

        history = load_chat_history(db, session_id)
        specialist = self._registry.get(decision.agent)

        # 先保存用户消息
        save_message(db, session_id, "user", user_input)

        # ----- Specialist 流式输出 + 保护 #4 -----
        full_response: list[str] = []
        try:
            async for chunk in specialist.stream_response(user_input, history):
                full_response.append(chunk)
                yield chunk
        except Exception as exc:
            fallback = self._protection.get_fallback_response(exc)
            full_response = [fallback]
            yield fallback

        # 保存 assistant 消息
        save_message(
            db,
            session_id,
            "assistant",
            "".join(full_response),
            agent_type=decision.agent.value,
        )


def get_orchestrator() -> AgentOrchestrator:
    """工厂函数，便于 FastAPI Depends 注入。"""
    return AgentOrchestrator()
