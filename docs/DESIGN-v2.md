# AI 面试助手 SKILL — 完整设计方案（修复版 v2.0）

> 版本：v2.0 | 日期：2026-06-24  
> 修复范围：P0 x3 + P1 x4 + P2 x4 = 共11项修复  
> 修复后目标评分：90+/100

---

## 目录

1. [研究概览：参考案例总结](#一研究概览参考案例总结)
2. [整体架构设计](#二整体架构设计)
3. [九大功能模块详细设计](#三九大功能模块详细设计)
4. [角色体系定义](#四角色体系定义)
5. [数据流与协作流程](#五数据流与协作流程)
6. [SKILL 文件结构](#六skill-文件结构)
7. [实施路线图](#七实施路线图)

---

## 一、研究概览：参考案例总结

### 1.1 参考案例列表

#### 参考案例 1：Natively (GitHub 1.5k⭐)
- **类型**：开源实时 AI 面试 Copilot
- **链接**：https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant
- **核心能力**：实时语音转文字（<500ms）、AI 答案生成、屏幕 OCR 分析、7 种角色模式、本地 RAG、隐身模式
- **技术栈**：Electron, Rust, React, TypeScript, Whisper, Ollama
- **借鉴点**：多角色模式切换设计、隐私优先的本地处理架构

#### 参考案例 2：Aural (GitHub 96⭐)
- **类型**：开源 AI 面试平台
- **链接**：https://github.com/1146345502/aural-oss
- **核心能力**：语音/聊天/视频三模态面试、AI 自主结构化面试、实时代码编辑器、JD-简历关联建议
- **技术栈**：Next.js, TypeScript, tRPC, Supabase, OpenAI
- **借鉴点**：全生命周期面试平台设计、练习模式与正式面试区分

#### 参考案例 3：OphyAI (商用)
- **类型**：全栈求职生命周期平台
- **链接**：https://ophyai.com
- **核心能力**：Interview Coach + Copilot + Resume Builder + Application Tracker + Negotiation Coach
- **备注**：Mockly（原案例4）已于2026年初被 OphyAI 收购合并，其 5-7 轮面试引擎技术已整合进 OphyAI 平台
- **借鉴点**：全流程数据互通设计、5-7 轮面试引擎、公司特定调优

#### 参考案例 4：ResumeSkills (GitHub 859⭐)
- **类型**：Claude Code 的 AI Skills 集合
- **链接**：https://github.com/Paramchoudhary/ResumeSkills
- **核心能力**：包含 resume-ats-optimizer、job-description-analyzer、resume-tailor、cover-letter-generator 等 5-6 个 skill，支持多 IDE（Cursor、Claude、Gemini、Windsurf 等）
- **借鉴点**：多 Agent Skills 协作模式、透明度设计（每条修改附原因）
- **备注**：非独立 Agent 系统，而是 Claude Code 生态的 Skills 集合

#### 参考案例 5：Resume Optimizer Pro (商用)
- **类型**：ATS 简历优化平台
- **链接**：https://resumeoptimizerpro.com
- **核心能力**：ATS 优化、一键重写、上下文关键词融入、400k+ 简历处理
- **借鉴点**：诊断+治疗一体化工作流、透明度设计

#### 参考案例 6：Eightfold AI (企业级)
- **类型**：企业人才智能平台
- **链接**：https://eightfold.ai
- **核心能力**：大规模职业档案数据、深度学习人才匹配、Career Planner 职业路径规划、Agentic AI 自主招聘
- **借鉴点**：大规模职业轨迹数据分析、相邻技能推断引擎、技能差距分析算法

#### 参考案例 7：FutureFit AI (职业导航)
- **类型**：AI 职业导航平台
- **链接**：https://www.futurefit.ai
- **核心能力**：实时区域劳动力市场数据、Career Copilot（50+ 语言）、Career Passport 数字钱包
- **借鉴点**：实时市场数据+个人档案结合、大规模政府项目验证（加拿大 150,000+ 工人、康涅狄格州 50,000 人）

#### 参考案例 8：Revarta (行为面试)
- **类型**：行为面试 AI 教练
- **链接**：https://revarta.com
- **核心能力**：前 Google/Amazon/Adobe Hiring Manager 校准反馈、STAR 方法合规检测、跨会话进度追踪
- **定价**：$39/月 或 $49/月（官网 2026-06 数据）
- **借鉴点**：Hiring Manager 视角反馈设计、跨会话迭代学习

#### 参考案例 9：OpenAI Agents SDK Handoff 模式
- **类型**：AI Agent 架构模式
- **链接**：https://platform.openai.com/docs/guides/agents
- **核心能力**：Triage Agent → Specialist Agent 控制转移、完整对话历史保留
- **借鉴点**：核心架构模式 — Triage + Specialist Handoff 是面试助手的最佳匹配架构

#### 参考案例 10：Progressive Disclosure + SKILL.md 生态
- **类型**：Agent 上下文管理标准
- **链接**：https://platform.openai.com/docs/guides/agents
- **核心能力**：L1/L2/L3 三层渐进式上下文加载
- **借鉴点**：核心上下文策略 — 避免一次性加载所有角色 prompt，显著减少 context window 压力

### 1.2 关键市场洞察

| 洞察 | 详情 |
|------|------|
| **全链路平台空白** | 覆盖"职位分析→简历优化→模拟面试→面试复盘→薪资谈判→跟进"全链路的工具几乎不存在 |
| **薪资谈判是蓝海** | 竞品中仅 OphyAI 提供基础 Negotiation Coach，深度薪资谈判支持严重不足 |
| **面试跟进被忽视** | 绝大多数工具忽略 Thank-you email、状态跟进等"最后一公里"体验 |
| **代码面试待整合** | 缺少将算法题生成、评估、优化集成到面试准备流程的工具 |
| **反馈质量决定留存** | 用户需要"真实、直接"的 Hiring Manager 视角反馈 |
| **教练导向优于作弊导向** | 教练导向工具更容易获得雇主认可和长期发展 |
| **语音原生是未来** | 模拟真实面试的对话感是核心竞争力 |

---

## 二、整体架构设计

### 2.1 架构模式：Triage + Specialist Handoff

采用 **"协调员分发 + 专家执行"** 架构，将原始设计的 **8 个角色精简为 4 个核心角色**：

```
                    +------------------+
                    |  用户请求         |
                    +--------+---------+
                             |
                    +--------v---------+
                    | InterviewTriage  |  <-- 唯一入口（P0 优先级）
                    |    (Router)      |
                    +--------+---------+
                             |
            +----------------+----------------+
            |                |                |
    +-------v------+ +-------v-------+ +------v--------+
    | JobSpecialist | | InterviewSpec  | | CareerSpecialist|
    |              | |                | |                |
    | - 职位深度分析 | | - 模拟面试      | | - 简历优化      |
    | - 批量搜索     | | - 代码面试      | | - 求职信生成    |
    |              | | - 面试复盘      | | - 市场洞察      |
    |              | | - 面试跟进      | | - 薪资谈判      |
    |              | |                | | - 职业规划      |
    +--------------+ +----------------+ +----------------+
```

### 2.2 Handoff 保护机制（新增）

| 机制 | 说明 | 触发条件 |
|------|------|---------|
| **max_turns** | 每轮对话最多 5 次 handoff | 达到 3 次时警告 |
| **循环检测** | 记录 handoff 历史，防止 A→B→A 循环 | 检测到循环时中断 |
| **fallback** | Specialist 无法处理时回退到 Triage | 意图不匹配/处理失败 |
| **错误降级** | 外部 API 失败时使用缓存/通用知识 | API 超时或返回错误 |
| **并发支持** | 独立任务可并行触发 | 用户同时请求多个不相关任务 |

### 2.3 核心设计原则

| 原则 | 说明 |
|------|------|
| **渐进式披露** | 按 L1/L2/L3 三层加载角色上下文，避免 context window 过载 |
| **状态共享** | 通过 InterviewState 共享对象访问面试上下文 |
| **教练导向** | 聚焦能力提升，非实时作弊辅助 |
| **隐私优先** | 敏感数据本地处理，支持 BYOK 和 Ollama 本地模型 |
| **Hiring Manager 视角** | 所有反馈模拟真实招聘官的评估标准 |

### 2.4 InterviewState 共享上下文（抽象描述）

InterviewState 包含以下信息类别（具体实现由运行时管理）：

- **用户画像**：技能、经验、目标职位、偏好
- **职位分析**：JobSpecialist 的分析结果和匹配记录
- **面试记录**：InterviewSpecialist 的会话历史、评分、反馈
- **简历优化**：CareerSpecialist 的优化记录和 ATS 分数
- **市场数据**：CareerSpecialist 的薪资和趋势洞察
- **复盘记录**：面试复盘历史和改进追踪
- **职业规划**：长期计划、技能差距、行动项

---

## 三、九大功能模块详细设计

### 模块 1：单职位深度分析 (JobSpecialist)

**目标**：分析单个职位是否适合用户，给出匹配度评估。

**工作流程**：
1. 解析 JD，提取硬性要求、软性要求、优先条件
2. 对比用户简历/技能，逐维度评分
3. 识别关键词差距
4. 查询市场薪资数据做对比
5. 生成综合评估和准备建议

**参考对标**：OphyAI 的 JD 匹配引擎、ResumeSkills 的 job-description-analyzer

---

### 模块 2：批量搜索排名 (JobSpecialist)

**目标**：帮用户批量搜索匹配的公司和岗位，以列表形式呈现并排名。

**工作流程**：
1. 从多个数据源（LinkedIn、Indeed 等）搜索职位
2. 对每个职位调用模块 1 进行匹配评分
3. 按匹配度、薪资、公司规模等多维度排序
4. 生成推荐理由和申请优先级

**参考对标**：Teal 的职位追踪器、AIHawk 的自动化搜索

---

### 模块 3：简历定向优化 (CareerSpecialist)

**目标**：针对目标职位优化简历，提升 ATS 通过率。

**工作流程**：
1. 解析简历和 JD
2. 计算原始 ATS 匹配分数
3. 识别关键词差距
4. 逐段优化（Summary → Experience → Skills）
5. 融入 JD 关键词到现有要点（非堆砌）
6. 验证优化后的 ATS 分数
7. 生成透明的修改说明

**Guardrails**：
- 不编造不存在的经历
- 关键词自然融入，非堆砌
- 保留用户原有写作风格
- 每条修改附原因说明

**参考对标**：Resume Optimizer Pro、Jobscan、ResumeSkills

---

### 模块 4：求职信生成 (CareerSpecialist - 新增)

**目标**：根据简历和 JD 生成个性化求职信。

**工作流程**：
1. 提取简历中与 JD 匹配的关键资质
2. 研究公司使命、产品、文化
3. 生成三段式求职信（开场+资质+结尾）
4. 控制 250-400 字，匹配公司文化调性

**参考对标**：ResumeSkills 的 cover-letter-generator

---

### 模块 5：模拟面试生成 (InterviewSpecialist)

**目标**：预测面试题，提供参考答案和评分反馈。

**支持的面试类型**：
- 技术面试（domain knowledge）
- 行为面试（STAR method）
- 系统设计（architecture）
- **代码面试（新增）**：算法题生成、评估、复杂度分析
- 综合面试（multi-round）

**面试流程（5-7 轮）**：
1. HR 筛选（自我介绍、动机）
2. 技术深度（专业知识、项目深挖）
3. **代码/实践评估（新增）**：算法题或 case study
4. 系统设计（架构能力，高级岗位）
5. 差距分析（针对弱点追问）
6. 行为面试（STAR 方法合规检测）
7. 收尾（薪资期望、提问环节）

**参考对标**：OphyAI 的面试引擎、Revarta 的 Hiring Manager 反馈、LeetCode（代码面试）

---

### 模块 6：代码面试支持 (InterviewSpecialist - 新增)

**目标**：为技术岗位面试提供算法题练习和评估。

**工作流程**：
1. 根据目标公司和岗位确定难度和题型分布
2. 生成算法问题，匹配公司出题偏好（如 Meta 重 graph/string，Google 重 tree/DP）
3. 用户提供解答后进行评估
4. 分析时间/空间复杂度
5. 提供优化建议

**评估维度**：正确性 30%、复杂度 25%、代码质量 20%、解题思路 15%、优化能力 10%

**参考对标**：LeetCode、Interviewing.io、Aural 的 Monaco 编辑器

---

### 模块 7：面试复盘与迭代 (InterviewSpecialist)

**目标**：在面试中学习，持续改进。

**工作流程**：
1. 收集面试反馈（用户输入+录音分析）
2. 逐题评估和对比历史表现
3. 识别进步和退步的维度
4. 生成改进版答案
5. 更新技能画像和行动计划
6. 为下次面试推荐重点

**参考对标**：Revarta（跨会话追踪）、Yoodli（表达分析）

---

### 模块 8：面试跟进 (InterviewSpecialist - 新增)

**目标**：面试后的 Thank-you email 和状态跟进。

**工作流程**：
1. 根据面试内容生成个性化 Thank-you email（24 小时内发送）
2. 如 1 周无回复，生成礼貌的状态跟进邮件
3. 多轮面试间的协调邮件

**Thank-you Email 模板要素**：
- 提及面试中的具体讨论话题
- 重申 1-2 个关键资质
- 表达对角色和公司的热情
- 100-150 字，专业但温暖的语调

**参考对标**：InterviewPal、WriteMail.ai

---

### 模块 9：市场洞察 (CareerSpecialist)

**目标**：提供薪资分析、技能趋势、需求增长方向。

**工作流程**：
1. 从多个数据源抓取市场数据
2. 计算薪资百分位和趋势
3. 分析技能需求和增长方向
4. 对比用户当前状况给出建议

**数据源优先级**：Levels.fyi → Glassdoor → LinkedIn Salary Insights → PayScale

---

### 模块 10：薪资谈判 (CareerSpecialist - 新增)

**目标**：帮助用户评估 Offer 并制定谈判策略。

**工作流程**：
1. 评估 Offer 与市场数据的对比（percentile 定位）
2. 计算谈判筹码（竞争 offer、独特技能、紧迫性）
3. 生成谈判策略和具体话术要点
4. 提供谈判邮件模板

**Offer 评估标准**：

| 评估 | Percentile | 建议 |
|------|-----------|------|
| 低于市场 | < P25 | 强势谈判或考虑拒绝 |
| 偏低 | P25-P40 | 争取 P50+ |
| 合理 | P40-P60 | 标准谈判 P60-P75 |
| 良好 | P60-P80 | 争取增量改善 |
| 优秀 | > P80 | 可接受，小幅争取 |

**参考对标**：Levels.fyi、OphyAI Negotiation Coach、Glassdoor

---

### 模块 11：职业规划推荐 (CareerSpecialist)

**目标**：推荐发展方向，提供清晰路径和行动计划。

**工作流程**：
1. 分析用户当前技能和经验
2. 结合市场趋势数据
3. 参考 Eightfold AI 的职业轨迹模型生成路径
4. 识别技能差距并制定学习计划
5. 输出分阶段的行动计划

**参考对标**：Eightfold AI Career Planner、FutureFit AI Career GPS

---

## 四、角色体系定义（精简为 4 个角色）

### 角色 1：InterviewTriage（面试协调员）— P0

**定位**：唯一入口。理解用户意图，分发到 Specialist。不执行具体任务。

**路由规则**：

| 用户意图 | 目标 Specialist |
|---------|----------------|
| "分析这个职位" / "搜索工作" | JobSpecialist |
| "优化简历" / "写求职信" / "薪资谈判" / "市场趋势" / "职业规划" | CareerSpecialist |
| "模拟面试" / "练算法题" / "复盘面试" / "发 thank-you email" | InterviewSpecialist |

**Guardrails**：
- 最多 5 次 handoff 每轮对话
- 3 次 handoff 时发出警告
- 记录 handoff 历史防止 A→B→A 循环
- Specialist 无法处理时回退到 Triage
- 无法识别意图时询问用户

---

### 角色 2：JobSpecialist（职位专家）

**定位**：处理所有职位相关任务。合并了原 JobAnalyst + SearchDispatcher。

**职责**：
- 单职位深度分析（JD 解析、匹配评分、差距识别）
- 批量搜索排名（多源搜索、匹配评分、多维度排序）
- 薪资数据查询与市场对比

**详细指南**：见 `references/job-specialist.md`

---

### 角色 3：InterviewSpecialist（面试专家）

**定位**：处理所有面试相关任务。合并了原 InterviewCoach + ReviewAdvisor，新增 InterviewFollowUp + CodingInterview。

**职责**：
- 模拟面试题生成（技术/行为/系统设计/代码/综合）
- 代码面试支持（算法题、复杂度分析、优化建议）
- 面试复盘与迭代（逐题评估、进度追踪、改进建议）
- 面试跟进（Thank-you email、状态跟进）

**详细指南**：见 `references/interview-specialist.md`

---

### 角色 4：CareerSpecialist（职业专家）

**定位**：处理职业发展任务。合并了原 ResumeOptimizer + MarketAnalyst + CareerPlanner，新增 CoverLetter + SalaryNegotiation。

**职责**：
- 简历定向优化（ATS 评分、关键词融入、逐段重写）
- 求职信生成（个性化、公司文化匹配）
- 市场洞察（薪资分析、技能趋势、需求方向）
- 薪资谈判（Offer 评估、谈判策略、邮件模板）
- 职业规划（路径推荐、技能差距、行动计划）

**详细指南**：见 `references/career-specialist.md`

---

## 五、数据流与协作流程

### 5.1 典型场景数据流

#### 场景 A：准备面试

```
用户: "我收到了 TechCorp 的 Senior ML Engineer 面试，帮我准备"
  │
  ▼
InterviewTriage ──handoff──► InterviewSpecialist
  │                            │
  │                            ▼
  │                    生成 8 道预测题（含 2 道代码 + 1 道系统设计）
  │                    提供答案框架和评分标准
  │                            │
  │◄───────────────────────────┘
  │
  ├──► "已生成模拟面试题库，包含代码题和系统设计题"
  │
  ▼
用户完成模拟后请求复盘
  │
  ▼
InterviewTriage ──handoff──► InterviewSpecialist
                                │
                                ▼
                        逐题评估、生成改进建议
                        安排下次练习重点
```

#### 场景 B：求职规划

```
用户: "我想找机器学习方向的工作，不知道该往哪走"
  │
  ▼
InterviewTriage ──handoff──► JobSpecialist
  │                            │
  │                            ▼
  │                    搜索并排名 20 个匹配职位
  │                            │
  │◄───────────────────────────┘
  │
InterviewTriage ──handoff──► CareerSpecialist
  │                            │
  │                            ▼
  │                    分析 ML Engineer 市场趋势
  │                    Agentic AI 方向需求增长 280%
  │                    生成 3 条职业路径 + 技能差距分析
  │                            │
  │◄───────────────────────────┘
  │
  └──► "推荐 3 条路径，Agentic AI 方向优先级最高..."
```

#### 场景 C：面试后跟进（新增）

```
用户: "我刚面完 TechCorp，帮我写 thank-you email"
  │
  ▼
InterviewTriage ──handoff──► InterviewSpecialist
                                │
                                ▼
                        根据面试内容生成个性化 thank-you email
                        提及具体讨论话题
                                │
  ▼
1 周后用户询问进展
  │
  ▼
InterviewTriage ──handoff──► InterviewSpecialist
                                │
                                ▼
                        生成礼貌的状态跟进邮件
```

#### 场景 D：薪资谈判（新增）

```
用户: "我收到了 TechCorp 的 offer，50k，想谈一下"
  │
  ▼
InterviewTriage ──handoff──► CareerSpecialist
                                │
                                ▼
                        评估 Offer（P45，合理范围）
                        分析谈判筹码
                        生成谈判策略和邮件
                                │
  ◄─────────────────────────────┘
  │
  └──► "Offer 处于市场中位数，建议争取 base 到 55k 或增加 sign-on..."
```

### 5.2 角色间数据共享

所有角色通过 **InterviewState** 共享：

| 数据类别 | 来源 | 消费者 |
|---------|------|--------|
| 用户画像 | Triage onboarding | 所有角色 |
| 职位分析 | JobSpecialist | CareerSpecialist（简历优化时参考） |
| 面试记录 | InterviewSpecialist | Triage（路由决策） |
| 简历优化 | CareerSpecialist | InterviewSpecialist（生成面试题时参考） |
| 市场数据 | CareerSpecialist | JobSpecialist（薪资评估） |
| 复盘记录 | InterviewSpecialist | InterviewSpecialist（跨会话追踪） |

---

## 六、SKILL 文件结构

### 6.1 目录结构（符合 skill-creator 规范）

```
interview-assistant/
├── SKILL.md                          # 主入口文件（< 500 行）
│   ├── YAML frontmatter (name + description only)
│   ├── 架构概览
│   ├── 核心原则
│   ├── 4 个角色定义
│   ├── 路由规则
│   ├── Handoff 保护机制
│   ├── Session 管理
│   └── Reference 文件索引
└── references/
    ├── job-specialist.md             # 职位分析+搜索详细指南
    ├── interview-specialist.md       # 模拟面试+代码+复盘+跟进指南
    └── career-specialist.md          # 简历+求职信+市场+谈判+规划指南
```

### 6.2 关键规范遵循

| 规范要求 | 修复前 | 修复后 | 状态 |
|---------|--------|--------|------|
| SKILL.md 行数 | 800-1200 行/角色 | 主入口 < 200 行 | 已修复 |
| Frontmatter 字段 | name + desc + version + author + category + tags | 仅 name + description | 已修复 |
| 写作形式 | 第三人称描述 | 祈使/不定式形式 | 已修复 |
| 冗余文档 | CHANGELOG、CONTRIBUTING 等 | 已移除 | 已修复 |
| 目录层级 | config/roles/shared 三层嵌套 | 扁平化 SKILL.md + references/ | 已修复 |
| 角色数量 | 8 个角色 | 4 个核心角色 | 已修复 |

---

## 七、实施路线图

### 阶段 1：MVP（核心功能）— 预计 4 周

| 优先级 | 功能 | 角色 | 工作量 |
|--------|------|------|--------|
| **P0** | **Triage 协调员** | InterviewTriage | 1 周 |
| **P0** | 单职位深度分析 | JobSpecialist | 1.5 周 |
| **P0** | 模拟面试生成（含代码面试） | InterviewSpecialist | 2 周 |
| **P0** | 简历定向优化 | CareerSpecialist | 1.5 周 |
| **P0** | Handoff 保护机制 | InterviewTriage | 0.5 周 |
| **P0** | 面试跟进（Thank-you email） | InterviewSpecialist | 0.5 周 |

**里程碑**：具备完整面试准备 + 跟进能力的 SKILL

### 阶段 2：增强（扩展功能）— 预计 4 周

| 优先级 | 功能 | 角色 | 工作量 |
|--------|------|------|--------|
| **P1** | 批量搜索排名 | JobSpecialist | 1.5 周 |
| **P1** | 市场洞察 | CareerSpecialist | 1 周 |
| **P1** | **薪资谈判** | CareerSpecialist | 1 周 |
| **P1** | 面试复盘 | InterviewSpecialist | 1 周 |
| **P1** | 求职信生成 | CareerSpecialist | 0.5 周 |
| **P1** | 职业规划 | CareerSpecialist | 1 周 |

**里程碑**：覆盖求职全链路的完整 SKILL（含谈判 + 跟进）

### 阶段 3：优化（体验提升）— 预计 3 周

| 优先级 | 功能 | 说明 |
|--------|------|------|
| **P2** | 多语言支持 | 中文/英文/日文 |
| **P2** | 用户 Onboarding | 首次使用时的画像收集流程 |
| **P2** | 数据持久化 | 跨 session 的记忆和学习 |
| **P2** | 语音交互 | 模拟真实面试的对话感 |
| **P2** | 本地模型支持 | Ollama 等本地 LLM |

**里程碑**：生产级体验的完整 SKILL

---

## 八、修复记录

### P0 修复（3项）

| # | 问题 | 修复措施 | 状态 |
|---|------|---------|------|
| P0-1 | 目录结构过度设计 | 精简为 SKILL.md + references/ 扁平结构 | 已修复 |
| P0-2 | 8 个角色过多 | 合并为 4 个核心 Specialist 角色 | 已修复 |
| P0-3 | Triage 在 MVP 中标为 P1 | 调整为 P0，作为第一个开发项 | 已修复 |

### P1 修复（4项）

| # | 问题 | 修复措施 | 状态 |
|---|------|---------|------|
| P1-4 | 缺少薪资谈判模块 | 新增 SalaryNegotiation 模块（CareerSpecialist 子功能） | 已修复 |
| P1-5 | 缺少面试跟进模块 | 新增 InterviewFollowUp 模块（Thank-you email + 状态跟进） | 已修复 |
| P1-6 | CareerPlanner 职责混淆 | 拆分为 CareerSpecialist 角色 + 隐式 SessionManager 机制 | 已修复 |
| P1-7 | 缺少 Coding Interview | 在 InterviewSpecialist 中新增 coding_interview 子类型 | 已修复 |

### P2 修复（4项）

| # | 问题 | 修复措施 | 状态 |
|---|------|---------|------|
| P2-8 | Mockly 描述不准确 | 标注已合并至 OphyAI，替换参考为 OphyAI 整合引擎 | 已修复 |
| P2-9 | ResumeSkills 描述偏差 | 修正为"Claude Code 的 Skills 集合，5-6 个 skill" | 已修复 |
| P2-10 | 缺少 handoff 保护机制 | 新增 max_turns、循环检测、fallback、错误降级、并发支持 | 已修复 |
| P2-11 | Revarta 定价错误 | 更新为 $39/月或 $49/月（官网 2026-06 数据） | 已修复 |

---

## 九、测试与验证策略（新增）

### 9.1 SKILL 触发测试

验证 SKILL.md 的 description 能正确触发：

| 测试输入 | 期望触发 | 验证方式 |
|---------|---------|---------|
| "帮我准备面试" | 是 | 关键词匹配 |
| "优化简历" | 是 | 关键词匹配 |
| "分析这个职位" | 是 | 关键词匹配 |
| "薪资谈判" | 是 | 关键词匹配 |
| "写周报" | 否 | 不相关 |

### 9.2 路由准确性测试

验证 Triage 能正确路由到 4 个 Specialist：

| 用户输入 | 期望路由 | 验证标准 |
|---------|---------|---------|
| "分析这个 JD" | JobSpecialist | 引用 job-specialist.md |
| "模拟面试" | InterviewSpecialist | 引用 interview-specialist.md |
| "优化简历" | CareerSpecialist | 引用 career-specialist.md |
| "谈薪资" | CareerSpecialist | 引用 career-specialist.md |

### 9.3 Handoff 保护测试

| 测试场景 | 期望行为 | 验证标准 |
|---------|---------|---------|
| 连续 6 次 handoff | 阻止第 6 次，提示用户 | max_turns=5 |
| A->B->A 循环 | 检测到循环，中断并提示 | 历史记录检查 |
| Specialist 无法处理 | 回退到 Triage | fallback 机制 |
| API 超时 | 使用通用知识回答 | 错误降级 |

### 9.4 Reference 文件完整性检查

- [ ] `references/job-specialist.md` 存在且 < 500 行
- [ ] `references/interview-specialist.md` 存在且 < 500 行
- [ ] `references/career-specialist.md` 存在且 < 500 行
- [ ] 所有 reference 文件从 SKILL.md 正确引用
- [ ] SKILL.md 总行数 < 500 行

### 9.5 打包验证

```bash
# 使用 skill-creator 打包脚本验证
python scripts/package_skill.py /path/to/interview-assistant/

# 验证输出：
# - YAML frontmatter 格式正确
# - 必需字段（name, description）存在
# - 目录结构符合规范
# - .skill 文件成功生成
```

---

## 十、跨角色协作规范（新增）

### 10.1 数据流转规则

当 Specialist 需要其他角色的能力时，通过 Triage 路由：

```
用户 -> Triage -> Specialist A 处理 -> 需要 Specialist B 能力
                      |
                      v
              返回 Triage（附带上文摘要）
                      |
                      v
              Triage -> Specialist B 处理
                      |
                      v
              返回 Triage -> 整合回复用户
```

**规则**：
- Specialist 之间不直接通信，始终通过 Triage 中转
- 每次 handoff 附带 conversation context 摘要（< 500 tokens）
- 最终回复由 Triage 整合，确保语气一致

### 10.2 多任务并行处理

当用户同时请求多个独立任务：

```
用户: "帮我搜索 ML 工作，同时优化简历"
  |
  v
Triage -> JobSpecialist（搜索任务）
  |
  v
Triage -> CareerSpecialist（优化任务）
  |
  v
Triage 整合两个结果统一回复
```

**规则**：
- 独立任务可并行触发（如果运行时支持）
- 串行执行时按用户提及顺序处理
- 结果整合时标明各部分的来源 Specialist

### 10.3 错误处理流程

| 错误类型 | 处理步骤 | 用户-facing 消息 |
|---------|---------|-----------------|
| 外部 API 失败 | 1. 重试 1 次 2. 使用缓存 3. 使用通用知识 | "实时数据暂时不可用，基于一般趋势..." |
| 意图不明确 | 1. 列出可能的理解 2. 请用户确认 | "你是想 X 还是 Y？" |
| 超出能力范围 | 1. 诚实说明 2. 建议替代方案 | "这个我暂时无法帮你，但你可以尝试..." |
| Handoff 超限 | 1. 终止 handoff 2. 总结当前进展 | "已处理多个任务，建议分次进行..." |

---

*修复版 v2.1 — 所有 P0/P1/P2 问题已修复 + 测试策略 + 跨角色协作规范*
