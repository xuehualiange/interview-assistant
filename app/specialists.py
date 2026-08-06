"""
Specialist Agent 模块：三位领域专家，各自独立 System Prompt + LLM 流式输出。

Specialist 列表：
  - interview_prep  面试准备专家
  - mock_interview  模拟面试官
  - resume_opt      简历优化专家

设计说明：
- 每个 Specialist 只负责一个垂直领域，Prompt 更聚焦、回答更专业
- 统一继承 BaseSpecialist，共享 LLM 构建与流式输出逻辑，避免重复代码
- 流式输出（astream）为后续 SSE 端点直接对接做准备
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek

from app.agent import Intent
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ---------- 各 Specialist 的 System Prompt ----------

INTERVIEW_PREP_PROMPT = """你是一位资深的「面试准备专家」，拥有 10 年以上 HR 与技术面辅导经验。

你的职责：
- 帮助用户制定面试准备计划（时间线、复习重点、资料推荐）
- 讲解常见面试题型与答题框架（STAR 法则、行为面、案例面）
- 提供行业/公司/岗位的面试情报与准备建议
- 解答求职策略问题（投简历节奏、内推、薪资谈判准备等）

回答风格：
- 结构化、可执行，给出具体步骤而非空泛鼓励
- 使用中文，语气专业且友好
- 适当追问用户的目标岗位与背景，以便给出个性化建议
"""

MOCK_INTERVIEW_PROMPT = """你是一位严格的「模拟面试官」，负责进行真实的面试演练。

你的职责：
- 根据用户目标岗位发起模拟面试（技术面 / HR 面 / 综合面）
- 每次只问 1~2 个问题，等待用户回答后再追问或进入下一题
- 在用户回答后给出简短点评（优点 + 改进建议 + 参考回答思路）
- 模拟真实面试节奏：先自我介绍 → 项目深挖 → 场景题 → 反问环节

回答风格：
- 扮演面试官角色，不要一次性给出所有题目
- 问题要有深度，结合用户提到的经历追问细节
- 点评要具体，指出哪里好、哪里需要加强
- 使用中文，语气专业、略带压迫感以模拟真实场景
"""

RESUME_OPT_PROMPT = """你是一位「简历优化专家」，精通 ATS 系统与国内互联网/外企简历规范。

你的职责：
- 诊断用户简历的问题（结构、措辞、量化、关键词）
- 给出逐段修改建议与优化后的示例表述
- 指导 STAR 法则在简历项目描述中的应用
- 针对目标岗位调整简历重点与关键词匹配

回答风格：
- 先总览问题，再逐条给出「原文 → 优化建议 → 示例」
- 强调量化成果（数字、百分比、规模）
- 使用中文，语气专业、细致
- 若用户未提供简历内容，引导其粘贴或描述主要经历
"""

# Intent → System Prompt 映射表
SPECIALIST_PROMPTS: dict[Intent, str] = {
    Intent.INTERVIEW_PREP: INTERVIEW_PREP_PROMPT,
    Intent.MOCK_INTERVIEW: MOCK_INTERVIEW_PROMPT,
    Intent.RESUME_OPT: RESUME_OPT_PROMPT,
}


# ---------- 聊天历史类型 ----------

ChatTurn = tuple[str, str]  # (role, content)，role 为 "user" | "assistant"


def _build_messages(
    system_prompt: str,
    user_input: str,
    history: Sequence[ChatTurn],
    resume_text: str | None = None,
) -> list[BaseMessage]:
    """将 system prompt + 历史 + 当前用户输入组装为 LangChain 消息列表。"""
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
    if resume_text:
        messages.append(
            SystemMessage(
                content=(
                    f"【用户简历】\n{resume_text}\n\n"
                    "请基于以上简历内容回答用户问题。"
                )
            )
        )
    for role, content in history:
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_input))
    return messages


# ---------- Specialist 协议与基类 ----------


class SpecialistProtocol(Protocol):
    """Specialist 统一接口，便于 Registry 多态调用。"""

    intent: Intent

    async def stream_response(
        self,
        user_input: str,
        history: Sequence[ChatTurn] | None = None,
        resume_text: str | None = None,
    ) -> AsyncIterator[str]: ...


class BaseSpecialist:
    """
    Specialist 基类：封装 DeepSeek LLM 与流式输出。

    为什么 Specialist 用 temperature=0.7 而 Triage 用 0：
    - Triage 是分类任务，需要确定性；Specialist 是生成任务，适度随机性让回答更自然。
    """

    intent: Intent
    system_prompt: str

    def __init__(self, intent: Intent, system_prompt: str, settings: Settings | None = None) -> None:
        self.intent = intent
        self.system_prompt = system_prompt
        self._settings = settings or get_settings()
        self._llm = ChatDeepSeek(
            model=self._settings.deepseek_model,
            api_key=self._settings.deepseek_api_key,
            api_base=self._settings.deepseek_base_url,
            temperature=0.7,
            max_retries=2,
        )

    async def stream_response(
        self,
        user_input: str,
        history: Sequence[ChatTurn] | None = None,
        resume_text: str | None = None,
    ) -> AsyncIterator[str]:
        """
        流式生成 Specialist 回答，逐 chunk yield 文本片段。

        为什么用 astream 而非 ainvoke：
        - 前端 SSE 需要逐 token 推送，降低首字延迟（TTFT）
        - 长回答（如简历诊断）不必等全文生成完毕才展示
        """
        messages = _build_messages(
            self.system_prompt,
            user_input.strip(),
            history or [],
            resume_text=resume_text,
        )
        async for chunk in self._llm.astream(messages):
            # ChatDeepSeek chunk 可能是 str 或带 .content 的消息块
            text = chunk.content if hasattr(chunk, "content") else str(chunk)
            if text:
                yield text


# ---------- 三个具体 Specialist ----------


class InterviewPrepSpecialist(BaseSpecialist):
    """面试准备专家。"""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(Intent.INTERVIEW_PREP, INTERVIEW_PREP_PROMPT, settings)


class MockInterviewSpecialist(BaseSpecialist):
    """模拟面试官。"""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(Intent.MOCK_INTERVIEW, MOCK_INTERVIEW_PROMPT, settings)


class ResumeOptSpecialist(BaseSpecialist):
    """简历优化专家。"""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(Intent.RESUME_OPT, RESUME_OPT_PROMPT, settings)


# ---------- Specialist 注册表 ----------


class SpecialistRegistry:
    """
    按 Intent 查找对应 Specialist 实例。

    为什么用 Registry 而非 if/else：
    - Orchestrator 路由时一行 registry.get(intent) 即可，新增 Specialist 只改注册表
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._specialists: dict[Intent, BaseSpecialist] = {
            Intent.INTERVIEW_PREP: InterviewPrepSpecialist(settings),
            Intent.MOCK_INTERVIEW: MockInterviewSpecialist(settings),
            Intent.RESUME_OPT: ResumeOptSpecialist(settings),
        }

    def get(self, intent: Intent) -> BaseSpecialist:
        """获取 Specialist；未知 intent 时降级到面试准备专家。"""
        specialist = self._specialists.get(intent)
        if specialist is None:
            logger.warning("未知 intent %s，降级至 interview_prep", intent)
            return self._specialists[Intent.INTERVIEW_PREP]
        return specialist


def get_specialist_registry(settings: Settings | None = None) -> SpecialistRegistry:
    """工厂函数，便于 FastAPI Depends 注入。"""
    return SpecialistRegistry(settings=settings)
