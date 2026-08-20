"""
Triage Agent：意图识别路由模块。

职责：接收用户自然语言输入，判断应路由到哪个下游 Agent：
  - interview_prep  面试准备（通用求职/面试技巧咨询）
  - mock_interview  模拟面试（实战演练、问答模拟）
  - resume_opt      简历优化（简历修改、润色、ATS 优化）

设计说明：
- ROUTER_BACKEND=api（默认）时走 DeepSeek；local 时优先 Ollama triage-router，失败自动降级 DeepSeek。
- DeepSeek 亦不可用时自动降级到关键词规则，保证服务可用性。
- 返回结构化 Pydantic 对象而非裸字符串，便于后续路由与日志记录。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from enum import Enum
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ---------- 意图枚举 ----------


class Intent(str, Enum):
    """用户意图枚举，值与下游 Agent 路由键一一对应。"""

    INTERVIEW_PREP = "interview_prep"
    MOCK_INTERVIEW = "mock_interview"
    RESUME_OPT = "resume_opt"


# ---------- 结构化输出模型 ----------


class TriageResult(BaseModel):
    """
    Triage Agent 的最终输出。

    source 字段标记结果来源，便于监控 LLM 解析成功率与兜底触发频率。
    """

    intent: Intent
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度 0~1")
    reason: str = Field(default="", description="分类理由，便于调试与审计")
    source: Literal["llm", "fallback"] = Field(default="llm", description="结果来源")


class _LLMIntentResponse(BaseModel):
    """
    LLM 必须返回的 JSON 结构（用于 with_structured_output 约束）。

    为什么用 JSON 格式而不是自由文本：
    1. 机器可解析：下游路由逻辑需要明确的 intent 字段，JSON 键值对可直接
       映射到 Pydantic 模型，避免从"我认为用户想要..."中再抽取意图。
    2. 契约稳定：JSON Schema 是 LLM 与后端之间的"接口文档"，换模型或
       换 Prompt 时输出格式不变，降低集成成本。
    3. 可校验：Pydantic 可对 JSON 做类型校验（intent 必须是三个枚举值之一），
       非法输出在解析阶段即被拦截，触发兜底而非静默错误路由。
    """

    intent: Intent
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    reason: str = Field(default="")


# ---------- 系统 Prompt ----------

TRIAGE_SYSTEM_PROMPT = """你是一个求职助手系统的意图分类器（Triage Agent）。
根据用户输入，判断其意图并返回 JSON。

可选意图（intent 字段必须严格使用以下三个值之一）：
- interview_prep：通用面试准备、求职策略、行业了解、面试技巧咨询
- mock_interview：模拟面试、面试演练、问答练习、技术面/HR面模拟
- resume_opt：简历优化、简历修改、CV润色、简历诊断、ATS优化

请分析用户真实需求，输出 JSON 格式：
{"intent": "...", "confidence": 0.0~1.0, "reason": "简短中文理由"}
"""

# ---------- 本地 Ollama 路由（微调 triage-router）----------

LOCAL_ROUTER_INSTR = '判断用户输入的意图类别,只输出JSON:{"intent": "类别名"}'
_IM_END = "<|" + "im_end" + "|>"
_VALID_INTENT_VALUES = frozenset(i.value for i in Intent) | {"out_of_scope"}


def _build_ollama_prompt(user_input: str) -> str:
    return (
        f"<|im_start|>user\n{LOCAL_ROUTER_INSTR}\n{user_input}{_IM_END}\n"
        f"<|im_start|>assistant\n"
    )


def _extract_first_json_intent(text: str) -> str | None:
    """从模型输出中提取第一个 JSON 块并校验 intent 合法性。"""
    match = re.search(r"\{[^{}]*\}", text)
    if not match:
        return None
    try:
        intent = json.loads(match.group(0)).get("intent")
    except json.JSONDecodeError:
        return None
    if intent not in _VALID_INTENT_VALUES:
        return None
    return intent


# ---------- 关键词兜底规则 ----------

# 为什么需要兜底：
# 1. LLM 偶发超时/限流/网络错误，不能让整个请求失败
# 2. LLM 有时返回非 JSON 或字段缺失，结构化解析会失败
# 3. 关键词规则零延迟、零成本，在 LLM 不可用时保证基本可用
# 4. 常见高频词（"简历""面试"）规则覆盖率高，兜底结果通常可接受

_KEYWORD_RULES: list[tuple[list[str], Intent]] = [
    # 顺序 matters：先匹配更具体的意图
    (["简历", "cv", "履历", "resume"], Intent.RESUME_OPT),
    (["模拟面试", "mock", "演练", "面试"], Intent.MOCK_INTERVIEW),
]


def _keyword_fallback(user_input: str) -> TriageResult:
    """
    关键词兜底分类。

    规则（按用户要求）：
    - 含"简历"相关词 → resume_opt
    - 含"面试"相关词 → mock_interview
    - 其他 → interview_prep
    """
    text = user_input.lower()

    for keywords, intent in _KEYWORD_RULES:
        for kw in keywords:
            if kw.lower() in text:
                return TriageResult(
                    intent=intent,
                    confidence=0.6,  # 兜底置信度低于 LLM，便于监控
                    reason=f"关键词兜底：检测到「{kw}」",
                    source="fallback",
                )

    return TriageResult(
        intent=Intent.INTERVIEW_PREP,
        confidence=0.5,
        reason="关键词兜底：未匹配特定关键词，默认路由至面试准备",
        source="fallback",
    )


def _extract_json_from_text(text: str) -> dict | None:
    """
    从 LLM 原始回复中提取 JSON 对象（应对模型在 JSON 外包裹 markdown 的情况）。

    例如模型可能返回：
    ```json
    {"intent": "resume_opt", ...}
    ```
    """
    # 先尝试直接解析整段文本
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 再尝试提取 ```json ... ``` 或 { ... } 块
    patterns = [
        r"```(?:json)?\s*(\{.*?\})\s*```",
        r"(\{[^{}]*\"intent\"[^{}]*\})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


def _parse_structured_llm_result(raw_result: object) -> TriageResult | None:
    """将 with_structured_output(include_raw=True) 的返回值统一解析为 TriageResult。"""
    if isinstance(raw_result, dict):
        parsing_error = raw_result.get("parsing_error")
        parsed = raw_result.get("parsed")

        if parsing_error is not None or parsed is None:
            raw_msg = raw_result.get("raw")
            raw_text = getattr(raw_msg, "content", "") if raw_msg else ""
            logger.warning(
                "Triage JSON 解析失败，尝试手动提取。error=%s, raw=%s",
                parsing_error,
                raw_text[:200],
            )
            manual = _extract_json_from_text(raw_text)
            if manual:
                try:
                    parsed = _LLMIntentResponse.model_validate(manual)
                except ValidationError as ve:
                    logger.warning("手动提取的 JSON 校验失败: %s", ve)
                    return None
            else:
                return None

        if isinstance(parsed, _LLMIntentResponse):
            return TriageResult(
                intent=parsed.intent,
                confidence=parsed.confidence,
                reason=parsed.reason or "LLM 意图识别",
                source="llm",
            )
        return None

    if isinstance(raw_result, _LLMIntentResponse):
        return TriageResult(
            intent=raw_result.intent,
            confidence=raw_result.confidence,
            reason=raw_result.reason or "LLM 意图识别",
            source="llm",
        )
    return None


# ---------- Triage Agent 主体 ----------


class TriageAgent:
    """
    意图识别 Agent：LLM 优先，失败则关键词兜底。

    用法：
        agent = TriageAgent()
        result = await agent.classify("帮我优化一下简历")
        print(result.intent)  # Intent.RESUME_OPT
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._llm = self._build_llm()

    def _build_llm(self) -> ChatDeepSeek:
        """构建 DeepSeek 聊天模型实例。"""
        return ChatDeepSeek(
            model=self._settings.deepseek_model,
            api_key=self._settings.deepseek_api_key,
            api_base=self._settings.deepseek_base_url,
            temperature=0,       # 分类任务需要确定性输出，temperature=0 减少随机性
            max_retries=2,         # 网络抖动时自动重试，减少无谓降级
        )

    def _classify_with_ollama(self, user_input: str) -> TriageResult | None:
        """调用本地 Ollama triage-router；失败返回 None，由调用方降级 DeepSeek。"""
        prompt = _build_ollama_prompt(user_input)
        body = json.dumps({
            "model": self._settings.ollama_model,
            "raw": True,
            "stream": False,
            "prompt": prompt,
            "options": {"temperature": 0, "num_predict": 32},
        }).encode("utf-8")
        req = urllib.request.Request(
            self._settings.ollama_url,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Triage Ollama 调用失败: %s", exc)
            return None

        intent_value = _extract_first_json_intent(data.get("response", ""))
        if intent_value is None:
            logger.warning(
                "Triage Ollama 输出无法解析或 intent 非法: %s",
                data.get("response", "")[:200],
            )
            return None

        routed_intent = (
            Intent.INTERVIEW_PREP
            if intent_value == "out_of_scope"
            else Intent(intent_value)
        )
        reason = (
            "本地 Ollama 路由（out_of_scope → interview_prep）"
            if intent_value == "out_of_scope"
            else "本地 Ollama 路由"
        )
        return TriageResult(
            intent=routed_intent,
            confidence=0.9,
            reason=reason,
            source="llm",
        )

    async def _classify_with_ollama_async(self, user_input: str) -> TriageResult | None:
        return await asyncio.to_thread(self._classify_with_ollama, user_input)

    def _classify_with_llm(self, user_input: str) -> TriageResult | None:
        """
        调用 DeepSeek 做意图识别。

        返回 None 表示 LLM 路径失败，由调用方触发兜底。
        使用 include_raw=True 以便在解析失败时记录原始响应，方便排查。
        """
        structured_llm = self._llm.with_structured_output(
            _LLMIntentResponse,
            method="json_mode",    # 强制 JSON 模式，与 Prompt 中的格式要求一致
            include_raw=True,      # 解析失败时不抛异常，返回 parsing_error 供降级判断
        )

        messages = [
            SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ]

        try:
            raw_result = structured_llm.invoke(messages)
        except Exception as exc:
            # API 超时、鉴权失败、限流等网络/服务层错误
            logger.warning("Triage LLM 调用失败，将启用关键词兜底: %s", exc)
            return None

        return _parse_structured_llm_result(raw_result)

    async def _classify_with_llm_async(self, user_input: str) -> TriageResult | None:
        """异步版 LLM 分类，供 FastAPI 异步路由直接 await。"""
        structured_llm = self._llm.with_structured_output(
            _LLMIntentResponse,
            method="json_mode",
            include_raw=True,
        )
        messages = [
            SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ]
        try:
            raw_result = await structured_llm.ainvoke(messages)
        except Exception as exc:
            logger.warning("Triage LLM 异步调用失败，将启用关键词兜底: %s", exc)
            return None

        return _parse_structured_llm_result(raw_result)

    def _classify_primary(self, user_input: str) -> TriageResult | None:
        """按 router_backend 选择主路由；local 失败时自动降级 DeepSeek。"""
        if self._settings.router_backend == "local":
            local_result = self._classify_with_ollama(user_input)
            if local_result is not None:
                logger.info(
                    "Triage Ollama 成功: intent=%s confidence=%.2f",
                    local_result.intent.value,
                    local_result.confidence,
                )
                return local_result
            logger.warning("Triage Ollama 失败，降级 DeepSeek API")

        result = self._classify_with_llm(user_input)
        if result is not None:
            logger.info(
                "Triage DeepSeek 成功: intent=%s confidence=%.2f",
                result.intent.value,
                result.confidence,
            )
        return result

    async def _classify_primary_async(self, user_input: str) -> TriageResult | None:
        if self._settings.router_backend == "local":
            local_result = await self._classify_with_ollama_async(user_input)
            if local_result is not None:
                logger.info(
                    "Triage Ollama 成功: intent=%s confidence=%.2f",
                    local_result.intent.value,
                    local_result.confidence,
                )
                return local_result
            logger.warning("Triage Ollama 失败，降级 DeepSeek API")

        result = await self._classify_with_llm_async(user_input)
        if result is not None:
            logger.info(
                "Triage DeepSeek 成功: intent=%s confidence=%.2f",
                result.intent.value,
                result.confidence,
            )
        return result

    def classify(self, user_input: str) -> TriageResult:
        """
        同步意图分类入口：LLM → 关键词兜底。

        为什么两层而非只用 LLM：
        - LLM 是"最佳努力"（best-effort），兜底是"保证可用"（guaranteed）；
          生产环境必须假设 LLM 会失败，路由不能因为一次 API 超时就 500。
        """
        user_input = user_input.strip()
        if not user_input:
            return TriageResult(
                intent=Intent.INTERVIEW_PREP,
                confidence=0.0,
                reason="空输入，默认路由至面试准备",
                source="fallback",
            )

        llm_result = self._classify_primary(user_input)
        if llm_result is not None:
            return llm_result

        fallback_result = _keyword_fallback(user_input)
        logger.info(
            "Triage 降级至关键词兜底: intent=%s reason=%s",
            fallback_result.intent.value,
            fallback_result.reason,
        )
        return fallback_result

    async def classify_async(self, user_input: str) -> TriageResult:
        """异步意图分类入口，逻辑与 classify 相同。"""
        user_input = user_input.strip()
        if not user_input:
            return TriageResult(
                intent=Intent.INTERVIEW_PREP,
                confidence=0.0,
                reason="空输入，默认路由至面试准备",
                source="fallback",
            )

        llm_result = await self._classify_primary_async(user_input)
        if llm_result is not None:
            return llm_result

        fallback_result = _keyword_fallback(user_input)
        logger.info(
            "Triage 降级至关键词兜底: intent=%s reason=%s",
            fallback_result.intent.value,
            fallback_result.reason,
        )
        return fallback_result


def get_triage_agent(settings: Settings | None = None) -> TriageAgent:
    """工厂函数，便于 FastAPI Depends 注入。"""
    return TriageAgent(settings=settings)
