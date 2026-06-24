# Interview Assistant

[English](#english) | [中文](#chinese)

<a name="chinese"></a>
## 中文

AI 驱动的求职全链路助手 Skill，采用多 Agent 协作架构，覆盖职位分析、模拟面试、简历优化、薪资谈判与职业规划。

### 核心能力

| 模块 | 功能 | 负责 Agent |
|------|------|-----------|
| 职位深度分析 | JD 解析、匹配评分、关键词差距识别、薪资对比 | JobSpecialist |
| 模拟面试 | 技术/行为/系统设计/代码/综合面试（5-7 轮） | InterviewSpecialist |
| 简历优化 | ATS 评分、关键词融入、逐段重写、修改透明说明 | CareerSpecialist |
| 求职信生成 | 个性化 Cover Letter，250-400 字，匹配公司调性 | CareerSpecialist |
| 面试复盘 | 逐题评估、改进建议、跨会话进度追踪 | InterviewSpecialist |
| 面试跟进 | Thank-you Email、状态跟进邮件 | InterviewSpecialist |
| 薪资谈判 | Offer 评估、谈判策略、邮件模板、话术要点 | CareerSpecialist |
| 市场洞察 | 薪资基准、技能需求趋势、增长方向分析 | CareerSpecialist |
| 职业规划 | 多路径推荐、技能差距分析、分阶段行动计划 | CareerSpecialist |

### 架构设计

```
用户请求 -> InterviewTriage (协调员) -> 3 个 Specialist 专家
              |                    |-- JobSpecialist (职位)
              |                    |-- InterviewSpecialist (面试)
              |                    |-- CareerSpecialist (职业)
              |
          InterviewState (共享状态)
```

**设计亮点**：
- **Triage + Specialist Handoff**：参考 OpenAI Agents SDK 的 Handoff 模式，InterviewTriage 作为唯一入口进行意图识别与任务分发
- **渐进式上下文加载**：L1/L2/L3 三层加载，主入口 SKILL.md 仅 160 行，按需加载参考文档，避免上下文窗口过载
- **4 重 Handoff 保护**：最大轮次限制(5)、循环检测、错误降级、回退机制
- **InterviewState 状态共享**：全链路数据互通，面试记录反哺简历优化，市场数据支撑薪资谈判

### 技术栈

- **核心框架**：LangChain · DeepSeek API · Prompt Engineering
- **架构模式**：Multi-Agent Collaboration · Triage Router · Progressive Disclosure
- **规范标准**：兼容 skill-creator 打包规范，支持 `.skill` 分发

### 安装使用

```bash
# 下载 skill 包
# 在支持 skill-creator 规范的环境中加载 interview-assistant.skill 即可激活

# 或直接引用源码目录
├── SKILL.md              # 主入口（触发器 + 架构 + 路由）
└── references/
    ├── job-specialist.md       # 职位分析操作指南
    ├── interview-specialist.md # 模拟面试操作指南
    └── career-specialist.md    # 职业发展操作指南
```

### 竞品调研基础

系统性分析 10 个国内外竞品（Natively、Aural、OphyAI、ResumeSkills、Resume Optimizer Pro、Eightfold AI、FutureFit AI、Revarta 等），提炼以下市场洞察：
- 全链路求职平台存在市场空白
- 薪资谈判支持严重不足（蓝海）
- 面试跟进环节被绝大多数工具忽视
- 教练导向优于作弊导向，更易获得雇主认可

---

<a name="english"></a>
## English

AI-powered full-lifecycle job search assistant built with a multi-Agent collaboration architecture. Covers JD analysis, mock interviews, resume optimization, salary negotiation, and career planning.

### Capabilities

| Module | Function | Agent |
|--------|----------|-------|
| JD Deep Analysis | Parse JD, match scoring, keyword gap analysis, salary comparison | JobSpecialist |
| Mock Interview | Technical/Behavioral/System Design/Coding/Comprehensive (5-7 rounds) | InterviewSpecialist |
| Resume Optimization | ATS scoring, keyword integration, section-by-section rewrite | CareerSpecialist |
| Cover Letter | Personalized, 250-400 words, culture-matched | CareerSpecialist |
| Interview Debrief | Per-question evaluation, improvement suggestions, cross-session tracking | InterviewSpecialist |
| Interview Follow-up | Thank-you email, status check | InterviewSpecialist |
| Salary Negotiation | Offer evaluation, negotiation strategy, email templates | CareerSpecialist |
| Market Insights | Salary benchmarks, skill demand trends, growth analysis | CareerSpecialist |
| Career Planning | Multi-path recommendations, skill gap analysis, phased action plans | CareerSpecialist |

### Architecture

```
User Request -> InterviewTriage (Router) -> 3 Specialist Agents
                   |                       |-- JobSpecialist
                   |                       |-- InterviewSpecialist
                   |                       |-- CareerSpecialist
                   |
               InterviewState (Shared Context)
```

**Design Highlights**:
- **Triage + Specialist Handoff**: Inspired by OpenAI Agents SDK; InterviewTriage serves as the single entry point for intent recognition and task dispatch
- **Progressive Disclosure**: L1/L2/L3 context loading; main SKILL.md is only 160 lines; reference docs loaded on-demand
- **4-Layer Handoff Protection**: Max turn limit (5), loop detection, error degradation, fallback
- **InterviewState**: Full-lifecycle data sharing; interview feedback informs resume optimization; market data supports negotiation

### Tech Stack

- **Core**: LangChain · DeepSeek API · Prompt Engineering
- **Architecture**: Multi-Agent Collaboration · Triage Router · Progressive Disclosure
- **Standard**: Compatible with skill-creator packaging spec, `.skill` distribution ready

### Installation

```bash
# Load interview-assistant.skill in any skill-creator compatible environment

# Or reference source directly
├── SKILL.md              # Entry point (triggers + architecture + routing)
└── references/
    ├── job-specialist.md       # Job analysis guide
    ├── interview-specialist.md # Mock interview guide
    └── career-specialist.md    # Career development guide
```

### Competitive Research

Systematic analysis of 10 domestic and international competitors (Natively, Aural, OphyAI, ResumeSkills, Resume Optimizer Pro, Eightfold AI, FutureFit AI, Revarta, etc.) yielded the following insights:
- Full-lifecycle job search platforms represent a market gap
- Salary negotiation support is significantly underserved (blue ocean)
- Interview follow-up is neglected by most tools
- Coaching-oriented tools gain better employer trust than copilot-oriented ones

---

## License

MIT License · Copyright (c) 2026 Wu Yu
