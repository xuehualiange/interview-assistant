"""
FastAPI 应用入口：健康检查 + 对话 SSE + 历史/会话管理。

接口：
  POST   /chat                    SSE 流式对话
  POST   /upload-resume             上传会话简历
  GET    /history/{session_id}    查询对话历史
  DELETE /session/{session_id}    清除会话
  GET    /health                  健康检查

为什么用 SSE 而不是 WebSocket（见模块末尾 SSE 说明注释）：
- 本场景是「客户端发一条、服务端流式回一条」的单向推送，SSE 语义完全匹配
- SSE 基于 HTTP，无需额外协议升级，穿透 Nginx / CDN / 企业防火墙更可靠
- FastAPI + 浏览器 EventSource 原生支持，实现与调试成本更低
- WebSocket 适合双向高频通信（如协同编辑）；聊天流式输出无需客户端持续推送
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import io
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import PyPDF2
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db, get_resume, init_db, save_resume
from app.orchestrator import (
    AgentOrchestrator,
    delete_session,
    get_orchestrator,
    get_session_history,
)
from app.protection import RouteDecision

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------- 请求 / 响应模型 ----------


class ChatRequest(BaseModel):
    """POST /chat 请求体。"""

    message: str = Field(..., min_length=1, description="用户输入")
    session_id: str = Field(..., min_length=1, max_length=64, description="会话 ID")


class HistoryMessage(BaseModel):
    """单条历史消息。"""

    id: int
    role: str
    content: str
    agent_type: str | None
    created_at: datetime


class HistoryResponse(BaseModel):
    """GET /history/{session_id} 响应。"""

    session_id: str
    messages: list[HistoryMessage]
    total: int


class DeleteSessionResponse(BaseModel):
    """DELETE /session/{session_id} 响应。"""

    session_id: str
    deleted_count: int
    message: str


# ---------- SSE 工具 ----------


def _format_sse_event(event_type: str, content: str) -> str:
    """
    格式化为 SSE 标准行：data: {...}\n\n

    为什么 content 统一为字符串：
    - SSE 规范中 data 字段是文本；复杂结构（如 triage 路由信息）先 json.dumps
      再放入 content，前端 JSON.parse 即可，保持事件格式一致。
    """
    payload = json.dumps({"type": event_type, "content": content}, ensure_ascii=False)
    return f"data: {payload}\n\n"


def _route_decision_to_content(decision: RouteDecision) -> str:
    """将 RouteDecision 序列化为 JSON 字符串，作为 triage 事件的 content。"""
    return json.dumps(
        {
            "agent": decision.agent.value,
            "loop_switched": decision.loop_switched,
            "used_default_agent": decision.used_default_agent,
            "switch_reason": decision.switch_reason,
        },
        ensure_ascii=False,
    )


async def _chat_sse_generator(
    session_id: str,
    message: str,
    orchestrator: AgentOrchestrator,
    resume_text: str | None = None,
) -> Any:
    """
    SSE 异步生成器。

    为什么在生成器内部创建 DB Session 而非 Depends(get_db)：
    - StreamingResponse 在路由函数返回后才持续 yield
    - Depends 的 Session 在路由函数返回时即关闭，会导致流式写入中途断连
    - 在生成器内手动管理 Session 生命周期，保证整条流式链路 DB 可用
    """
    db = SessionLocal()
    try:
        async for item in orchestrator.handle_message(
            db,
            session_id,
            message,
            resume_text=resume_text,
        ):
            if isinstance(item, RouteDecision):
                # 首包：Triage 路由结果
                yield _format_sse_event("triage", _route_decision_to_content(item))
            elif isinstance(item, str):
                # 正文片段（含保护机制回退文本、轮次超限提示等）
                yield _format_sse_event("chunk", item)

        # 结束标记，前端据此关闭 loading 状态
        yield _format_sse_event("end", "")
    except Exception as exc:
        logger.exception("SSE 流式对话异常: session_id=%s", session_id)
        yield _format_sse_event("chunk", f"服务异常：{exc}")
        yield _format_sse_event("end", "")
    finally:
        db.close()


# ---------- 应用生命周期 ----------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化 SQLite 表结构。"""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# 跨域：本地前端 + Vercel 部署域名（credentials 模式下不可使用 allow_origins=["*"]）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://interview-assistant-drab.vercel.app",
        "https://xuehualiange.github.io",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 路由 ----------


@app.get("/health", tags=["系统"])
async def health_check() -> dict[str, Any]:
    """健康检查，供 Docker / 负载均衡探针使用。"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@app.post("/chat", tags=["对话"])
async def chat_stream(
    body: ChatRequest,
    db: Session = Depends(get_db),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    """
    SSE 流式对话接口。

    请求体：{"message": "...", "session_id": "..."}

    SSE 事件格式（每条以空行分隔）：
      data: {"type": "triage", "content": "{\\"agent\\":\\"resume_opt\\",...}"}
      data: {"type": "chunk",  "content": "你好，..."}
      data: {"type": "end",    "content": ""}

    对话 user/assistant 消息由 Orchestrator 自动持久化到 SQLite。
    """
    resume_text = get_resume(db, body.session_id)
    return StreamingResponse(
        _chat_sse_generator(body.session_id, body.message, orchestrator, resume_text),
        media_type="text/event-stream",
        headers={
            # 禁止缓冲，确保 nginx / 代理立即转发每个 chunk
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/upload-resume", tags=["对话"])
async def upload_resume(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """上传简历文件（PDF / TXT / MD），提取文本后存入数据库。"""
    content = await file.read()
    filename = file.filename or ""

    if filename.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
    else:
        text = content.decode("utf-8")

    save_resume(db, session_id, text)
    return {"status": "ok", "message": f"已上传: {filename}"}


@app.get("/history/{session_id}", response_model=HistoryResponse, tags=["对话"])
async def get_history(
    session_id: str,
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """
    返回指定 session 的全部对话历史（按时间正序）。

    数据来源：SQLite messages 表，服务重启后仍可恢复。
    """
    rows = get_session_history(db, session_id)
    messages = [
        HistoryMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            agent_type=msg.agent_type,
            created_at=msg.created_at,
        )
        for msg in rows
    ]
    return HistoryResponse(session_id=session_id, messages=messages, total=len(messages))


@app.delete("/session/{session_id}", response_model=DeleteSessionResponse, tags=["对话"])
async def clear_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> DeleteSessionResponse:
    """清除指定 session 的全部消息，用于「新对话」或 GDPR 删除请求。"""
    deleted = delete_session(db, session_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已为空")

    return DeleteSessionResponse(
        session_id=session_id,
        deleted_count=deleted,
        message=f"已清除 {deleted} 条消息",
    )


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
