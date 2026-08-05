"""
Agent 保护机制：集中管控多 Agent 协作的安全边界。

四类保护（按执行顺序）：
  1. 最大轮次   — 单 session 超过 20 轮拒绝继续
  2. 循环检测   — 同一 Agent 连续 3 次强制切换
  3. 错误降级   — Triage 识别失败路由至默认 Agent
  4. 异常回退   — 任意未捕获异常返回通用回答

设计说明：
- 全部逻辑收敛到一个类，便于在 Orchestrator 入口单点调用，
  也便于单元测试时 mock 整个保护层。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.agent import Intent, TriageResult

logger = logging.getLogger(__name__)


# ---------- 常量 ----------

# 为什么最大轮次是 20：
# 1. 成本控制：每轮都调用 DeepSeek，20 轮 ≈ 10 组问答，单次会话 API 费用有上限
# 2. 上下文窗口：历史消息随轮次线性增长，超过 20 轮后 token 消耗陡增且回答质量下降
# 3. 防滥用：公开 API 若无轮次上限，易被脚本刷量
# 4. 产品体验：求职咨询单次聚焦一个主题，20 轮足够深度交流；超出应开新 session 保持清晰
MAX_TURNS_PER_SESSION = 20

# 连续同一 Agent 多少次后强制切换
LOOP_DETECTION_THRESHOLD = 3

# Triage 失败时的默认 Agent（最通用的求职咨询入口）
DEFAULT_AGENT = Intent.INTERVIEW_PREP

# 所有 Specialist 列表，用于循环检测时选择替代 Agent
_ALL_SPECIALISTS: list[Intent] = [
    Intent.INTERVIEW_PREP,
    Intent.MOCK_INTERVIEW,
    Intent.RESUME_OPT,
]

# 异常回退时的通用回答（保护机制 #4）
GENERIC_FALLBACK_RESPONSE = (
    "抱歉，我暂时无法完整处理您的问题。"
    "您可以尝试：\n"
    "1. 重新描述您的需求（如「帮我优化简历」「模拟一场技术面」）\n"
    "2. 开启新的对话会话\n"
    "3. 稍后再试\n\n"
    "如需面试准备、模拟面试或简历优化方面的帮助，请随时告诉我。"
)


# ---------- 异常 ----------


class MaxTurnsExceededError(Exception):
    """单 session 轮次超限。"""

    def __init__(self, session_id: str, turn_count: int) -> None:
        self.session_id = session_id
        self.turn_count = turn_count
        super().__init__(
            f"会话 {session_id} 已达最大轮次限制（{turn_count}/{MAX_TURNS_PER_SESSION}），"
            "请开启新会话继续。"
        )

# ---------- 路由决策结果 ----------


@dataclass
class RouteDecision:
    """保护层处理后的最终路由决策。"""

    agent: Intent
    loop_switched: bool = False          # 是否因循环检测被强制切换
    used_default_agent: bool = False     # 是否因 Triage 失败使用默认 Agent
    switch_reason: str = ""              # 切换/降级原因，便于日志与前端展示


@dataclass
class SessionGuardState:
    """单次请求前从 DB 或缓存加载的会话快照。"""

    session_id: str
    turn_count: int = 0                  # 当前 session 用户消息数（即将 +1）
    recent_agents: list[str] = field(default_factory=list)  # 最近若干轮 assistant 的 agent_type


# ---------- 保护机制主体 ----------


class AgentProtection:
    """
    多 Agent 系统四重保护机制。

    典型调用链（在 Orchestrator 中）：
        state = load_session_state(session_id)
        protection.check_max_turns(state)           # #1 超限则抛异常
        triage = await triage_agent.classify_async(input)
        decision = protection.resolve_route(triage, state)  # #2 #3
        try:
            async for chunk in specialist.stream(...):
                yield chunk
        except Exception as exc:
            yield protection.get_fallback_response(exc)       # #4
    """

    def __init__(
        self,
        max_turns: int = MAX_TURNS_PER_SESSION,
        loop_threshold: int = LOOP_DETECTION_THRESHOLD,
        default_agent: Intent = DEFAULT_AGENT,
    ) -> None:
        self.max_turns = max_turns
        self.loop_threshold = loop_threshold
        self.default_agent = default_agent

    # ----- 保护 #1：最大轮次 -----

    def check_max_turns(self, state: SessionGuardState) -> None:
        """
        检查 session 轮次是否超限。

        turn_count 应为「即将处理的本轮」计数（含当前用户消息）。
        超过 max_turns 时抛出 MaxTurnsExceededError，由上层返回 429 或友好提示。
        """
        if state.turn_count > self.max_turns:
            logger.warning(
                "Session %s 超出最大轮次: %d > %d",
                state.session_id,
                state.turn_count,
                self.max_turns,
            )
            raise MaxTurnsExceededError(state.session_id, state.turn_count)

    # ----- 保护 #2：循环检测 -----

    def detect_loop_and_switch(
        self,
        proposed_agent: Intent,
        recent_agents: list[str],
    ) -> tuple[Intent, bool, str]:
        """
        检测同一 Agent 是否连续出现达到阈值，若是则强制切换。

        为什么需要循环检测：
        1. Triage 误判稳定复现：用户说「还有呢」「继续」，Triage 可能反复路由到同一 Agent，
           导致用户 stuck 在错误专家（如想改简历却一直做模拟面试）
        2. 对话死循环：LLM 专家回答相似、用户重复提问，形成「同一 Agent 来回答同一类问题」
           的无效循环，浪费 token 且体验差
        3. 强制切换 = 主动打破僵局，让用户获得不同视角的帮助

        规则：若 recent_agents 末尾已有 (threshold-1) 个与 proposed 相同，
        则本次 proposed 将是第 threshold 次连续 → 强制切换到其他 Agent。
        """
        needed = self.loop_threshold - 1
        if len(recent_agents) >= needed:
            tail = recent_agents[-needed:]
            if all(agent == proposed_agent.value for agent in tail):
                alternate = self._pick_alternate_agent(proposed_agent)
                reason = (
                    f"循环检测：Agent「{proposed_agent.value}」已连续出现 "
                    f"{self.loop_threshold} 次，强制切换至「{alternate.value}」"
                )
                logger.warning(reason)
                return alternate, True, reason

        return proposed_agent, False, ""

    def _pick_alternate_agent(self, current: Intent) -> Intent:
        """选择与 current 不同的下一个 Specialist（轮询顺序）。"""
        try:
            idx = _ALL_SPECIALISTS.index(current)
            return _ALL_SPECIALISTS[(idx + 1) % len(_ALL_SPECIALISTS)]
        except ValueError:
            return self.default_agent

    # ----- 保护 #3：Triage 错误降级 -----

    def resolve_agent_from_triage(
        self,
        triage: TriageResult | None,
    ) -> tuple[Intent, bool, str]:
        """
        Triage 识别失败时降级到默认 Agent。

        失败判定：
        - triage 为 None（classify 抛异常等）
        - triage.source == "fallback" 且 confidence 极低（空输入等边缘情况）

        为什么默认是 interview_prep：
        三类意图中最通用，可覆盖大部分未分类的求职咨询，误路由代价最小。
        """
        if triage is None:
            reason = "Triage 失败：无分类结果，降级至默认 Agent"
            logger.warning(reason)
            return self.default_agent, True, reason

        if triage.source == "fallback" and triage.confidence <= 0.0:
            reason = "Triage 失败：空输入或无效分类，降级至默认 Agent"
            logger.warning(reason)
            return self.default_agent, True, reason

        return triage.intent, False, ""

    # ----- 保护 #4：异常回退 -----

    def get_fallback_response(self, error: Exception | None = None) -> str:
        """
        任意环节异常时返回通用回答，保证用户始终得到文本响应而非 500 空白页。

        为什么不用静默失败或重试：
        - 用户侧需要的是可操作的下一步指引，而非技术错误码
        - 通用回答维持产品可用性，同时日志中保留 error 供排查
        """
        if error is not None:
            logger.exception("Agent  pipeline 异常，启用回退回答: %s", error)
        return GENERIC_FALLBACK_RESPONSE

    # ----- 统一路由入口 -----

    def resolve_route(
        self,
        triage: TriageResult | None,
        state: SessionGuardState,
    ) -> RouteDecision:
        """
        合并保护 #2 与 #3，输出最终应使用的 Specialist Agent。

        调用前须已通过 check_max_turns（保护 #1）。
        """
        agent, used_default, degrade_reason = self.resolve_agent_from_triage(triage)

        agent, loop_switched, loop_reason = self.detect_loop_and_switch(
            agent,
            state.recent_agents,
        )

        reasons = [r for r in (degrade_reason, loop_reason) if r]
        return RouteDecision(
            agent=agent,
            loop_switched=loop_switched,
            used_default_agent=used_default,
            switch_reason="; ".join(reasons),
        )
