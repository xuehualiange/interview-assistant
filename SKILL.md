---
name: interview-assistant
description: >
  Activate when the user needs help with job search, interview preparation, or career development.
  Trigger scenarios include: interview preparation (technical/behavioral/mock), resume optimization,
  ATS improvement, mock interviews, and general career coaching.
---

# Interview Assistant — 架构设计文档

> **SKILL.md** 是本项目的架构设计入口。完整设计方案见 [`docs/DESIGN-v2.md`](./docs/DESIGN-v2.md)，提示词总蓝图见 [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md)。

## 设计 → 工程映射

本项目实现了 **「先设计、后编码」** 的完整闭环：

| 设计阶段（文档） | 工程阶段（代码） |
|----------------|----------------|
| Triage + Specialist Handoff 架构 | `app/agent.py` + `app/orchestrator.py` |
| 四重 Handoff 保护机制 | `app/protection.py` → `AgentProtection` |
| 三位领域专家 Prompt | `app/specialists.py` |
| InterviewState / 会话持久化 | `app/database.py` → SQLite `messages` 表 |
| SSE 流式输出 | `app/main.py` → `POST /chat` |
| 可视化对话界面 | `index.html` |

---

## Architecture

```
User Request → InterviewTriage (Router) → One of 3 Specialists
```

| 设计角色（SKILL 规范） | 工程实现（FastAPI） | 职责 |
|----------------------|-------------------|------|
| **InterviewTriage** | `TriageAgent` (`agent.py`) | 意图识别，JSON 结构化路由 |
| **InterviewSpecialist** | `MockInterviewSpecialist` | 模拟面试、问答演练 |
| **CareerSpecialist（简历）** | `ResumeOptSpecialist` | 简历诊断与优化 |
| **CareerSpecialist（准备）** | `InterviewPrepSpecialist` | 面试准备、求职策略 |

> MVP 阶段将原设计 4 角色（Job / Interview / Career + Triage）精简为 **3 个 Specialist + 1 个 Triage**，聚焦最高频场景。完整 9 模块扩展路线图见 [`docs/DESIGN-v2.md` §七](./docs/DESIGN-v2.md)。

---

## Core Principles

1. **Progressive Disclosure** — Triage 先加载，Specialist Prompt 按需激活
2. **State Sharing** — 会话状态通过 SQLite 持久化，跨轮次保留上下文
3. **Coaching Orientation** — 聚焦能力提升，非实时作弊辅助
4. **Specialist Isolation** — 专家之间不直接通信，统一由 Orchestrator 编排

---

## Routing Rules

| 用户意图 | 路由目标 | 实现 Intent 枚举 |
|---------|---------|-----------------|
| 面试准备、求职策略、技巧咨询 | InterviewPrepSpecialist | `interview_prep` |
| 模拟面试、问答演练、技术面 | MockInterviewSpecialist | `mock_interview` |
| 简历优化、CV 润色、ATS | ResumeOptSpecialist | `resume_opt` |

**Triage 实现要点**（`agent.py`）：
- 优先 DeepSeek LLM + JSON 结构化输出（`json_mode` + Pydantic 校验）
- LLM 失败时关键词兜底（简历→`resume_opt`，面试→`mock_interview`，其他→`interview_prep`）

---

## Handoff Protection（四重保护）

设计文档定义于 [`docs/DESIGN-v2.md` §2.2](./docs/DESIGN-v2.md)，工程实现于 `app/protection.py`：

| 机制 | 设计规则 | 工程实现 |
|------|---------|---------|
| **最大轮次** | 控制 session 长度与成本 | 单 session 超 **20 轮**报错（`MaxTurnsExceededError`） |
| **循环检测** | 防止 A→B→A 路由死循环 | 同一 Agent **连续 3 次**强制切换 |
| **错误降级** | Triage 失败时的兜底 | 路由至默认 Agent（`interview_prep`） |
| **异常回退** | LLM 异常保证可用性 | 返回通用回答，不暴露 500 |

---

## Session & State

**设计态**（InterviewState 共享对象）→ 见 [`docs/BLUEPRINT.md` §InterviewState](./docs/BLUEPRINT.md)

**工程态**（SQLite `messages` 表）：

```sql
messages (id, session_id, role, content, agent_type, created_at)
```

- `session_id`：会话隔离
- `agent_type`：记录响应来自哪个 Specialist，供循环检测与历史回放

---

## API Contract

| 端点 | 说明 |
|------|------|
| `POST /chat` | SSE 流式对话，`type`: triage / chunk / end |
| `GET /history/{session_id}` | 查询对话历史 |
| `DELETE /session/{session_id}` | 清除会话 |
| `GET /health` | 健康检查 |

---

## Reference Documents

| 文件 | 说明 |
|------|------|
| [`references/job-specialist.md`](./references/job-specialist.md) | JobSpecialist 职位分析操作指南 |
| [`references/interview-specialist.md`](./references/interview-specialist.md) | InterviewSpecialist 模拟面试操作指南 |
| [`references/career-specialist.md`](./references/career-specialist.md) | CareerSpecialist 简历/职业操作指南 |
| [`docs/DESIGN-v2.md`](./docs/DESIGN-v2.md) | 完整设计方案 v2.0 — 60+ 工具研究、9 模块、实施路线图 |
| [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md) | 提示词总蓝图 |
| [`docs/PLAN.md`](./docs/PLAN.md) | SKILL 包开发计划 |
| [`README.md`](./README.md) | 面向面试官的项目说明与快速开始 |

---

## Implementation Roadmap Status

| 阶段 | 设计范围 | 工程状态 |
|------|---------|---------|
| **MVP** | Triage + 模拟面试 + 简历优化 + 保护机制 | ✅ 已实现 |
| **Phase 2** | 批量搜岗、薪资谈判、面试复盘、求职信 | 📋 见 DESIGN-v2 §七 |
| **Phase 3** | 多语言、语音交互、本地模型 | 📋 规划中 |
