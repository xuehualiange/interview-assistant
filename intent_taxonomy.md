# Triage Agent 意图分类表（基于生产代码）

> **数据来源**：`app/agent.py`（`Intent` 枚举、`TRIAGE_SYSTEM_PROMPT`、`_KEYWORD_RULES`）、`app/specialists.py`（Specialist 映射）、`app/protection.py`（默认路由）。
>
> **重要说明**：设计文档（`docs/BLUEPRINT.md`、`SKILL.md`）中描述了 10+ 种意图（如 `job_search`、`salary_negotiate`），但**当前 MVP 代码仅实现并路由 3 个 intent**。本表以代码为准。

---

## 一、生产环境 Intent 一览

| intent（JSON 字段值） | 对应 Specialist | 代码定义位置 |
|---|---|---|
| `interview_prep` | 面试准备专家 | `Intent.INTERVIEW_PREP` |
| `mock_interview` | 模拟面试官 | `Intent.MOCK_INTERVIEW` |
| `resume_opt` | 简历优化专家 | `Intent.RESUME_OPT` |

**LLM 输出格式**（`TRIAGE_SYSTEM_PROMPT`）：

```json
{"intent": "interview_prep|mock_interview|resume_opt", "confidence": 0.0~1.0, "reason": "简短中文理由"}
```

**关键词兜底顺序**（`_KEYWORD_RULES`，先匹配先生效）：

1. 含 `简历` / `cv` / `履历` / `resume` → `resume_opt`
2. 含 `模拟面试` / `mock` / `演练` / **`面试`** → `mock_interview`
3. 其余 → `interview_prep`（默认）

---

## 二、各 Intent 详细定义

### 1. `interview_prep`

| 字段 | 内容 |
|---|---|
| **判定标准** | 用户在咨询**如何准备求职/面试**（计划、策略、知识点、行业了解、八股/算法要不要刷），但**不是在请求当场模拟问答**。含**自言自语式陈述/碎碎念**（无完整请求句式，但话题是求职方向、背景短板、焦虑等）——与真实日志一致，归本类。 |
| **典型信号词** | 准备、计划、怎么学、该看什么、求职策略、八股、算法题、掌握程度、通过率、岗位方向、内推、薪资谈判**准备**、想找…岗、实习…学得不好 |
| **正例** | 见下方 |
| **易混淆点** | 「帮我**准备**面试」含「面试」二字 → 关键词兜底会判为 `mock_interview`；**语义上属 `interview_prep`，但 fallback 会错路由**。微调数据应教会模型区分「准备咨询」vs「模拟演练」。 |

**正例（≥5）**

1. 我想转 AI 应用开发，接下来三个月该怎么规划？
2. 字节 AI 应用岗一般考什么，我要不要刷 LeetCode？
3. 我是双非本科，投中小厂还是创业公司更现实？
4. 明天有一轮技术面，今晚最后 2 小时复习什么性价比最高？
5. 内推和海投哪个更有效，一般怎么组合？
6. 高频八股我还搞不搞，AI 岗是不是不太考？
7. 有了这版简历，整体面试该怎么准备？

---

### 2. `mock_interview`

| 字段 | 内容 |
|---|---|
| **判定标准** | 用户希望**进入面试演练/问答模拟**（技术面、HR 面、项目深挖、当场作答、点评回答），或正在**回答面试官抛出的问题**。 |
| **典型信号词** | 模拟面试、mock、演练、开始面、问我、你问、我来答、点评我的回答、技术面、HR 面、自我介绍、连环追问 |
| **正例** | 见下方 |
| **易混淆点** | 「帮我**看看**这份 CV 有没有问题」→ 表面像诊断，但 prompt 示例明确归 **`resume_opt`**（修改润色），不是 mock。 |

**正例（≥5）**

1. 开始一场 30 分钟的技术模拟面试吧
2. 你是面试官，问我两个 FastAPI 相关的问题
3. 我答完了，你点评一下刚才那段项目介绍
4. 继续，再追问一下我简历里 Agent 架构那块
5. 来个 HR 面，问离职原因和职业规划
6. 不清楚，返回格式不对会422自动报错。（用户在**作答**技术面问题）
7. 你要不先看看我的掌握程度（要求对方**出题/摸底**）

---

### 3. `resume_opt`

| 字段 | 内容 |
|---|---|
| **判定标准** | 用户要**修改、润色、诊断、重写简历/CV**，或讨论**简历某一节怎么写**（项目描述、技能栈排版、ATS、量化表达）。 |
| **典型信号词** | 简历、CV、履历、润色、优化、改写、诊断、ATS、项目描述、一版完整简历、还要改吗 |
| **正例** | 见下方 |
| **易混淆点** | 「我的简历应该**掌握到什么程度**才能通过面试」→ 含「简历」但核心是**准备深度**，应归 **`interview_prep`**，不是改简历。 |

**正例（≥5）**

1. 帮我优化简历里的项目描述，尤其是 Agent 那段
2. 这份 CV 太长了，怎么压到一页？
3. 技术栈这块写得乱七八糟，帮我重新组织
4. 给我一版完整简历，按 AI 应用开发岗来改
5. 我的简历还要改么？
6. 我这个简历怎么样？
7. 个人总结和项目经历重复了，怎么改不显得凑字数？

---

## 三、特殊类别

### 3.1 `out_of_scope`（微调扩展标签，**当前代码未实现**）

| 字段 | 内容 |
|---|---|
| **判定标准** | 与求职/面试/简历**完全无关**的输入：闲聊、系统能力问询、让 AI 写无关内容等。**求职相关的陈述/碎碎念按话题归类**（如「想找 AI 应用开发岗」「学到的东西都用不上，急」→ `interview_prep`）；**只有与求职完全无关的内容**才进 `out_of_scope`。 |
| **典型信号词** | 天气、笑话、你是谁、写首诗、记得上次吗、帮我订餐、翻译 unrelated 内容（均与求职无关） |
| **正例** | 见下方 |
| **当前系统行为** | `Intent` 枚举无此项；LLM 只能输出 3 值之一。兜底默认 → **`interview_prep`**。微调数据集建议保留此标签，便于将来拒答或固定回复。 |

**正例（≥5）**

1. 今天北京天气怎么样？
2. 你是谁，用的什么模型？
3. 新的对话还记得上次讲了什么么？
4. 帮我写一首关于夏天的诗
5. 我心情很差，陪我聊聊天（与求职无关的纯情感倾诉）
6. 把下面这段英文翻译成法语（与求职无关的翻译任务）

**易混淆点**

- 「介绍一下我的项目」→ 若上下文是**面试演练**，归 `mock_interview`；若是**写简历项目段**，归 `resume_opt`。**看用户在要「讲出来」还是「写出来」**。
- 求职相关的自言自语、半截陈述、带情绪的碎碎念（无完整请求句式）→ **按话题归类，不归** `out_of_scope`。例：「想找 AI 应用开发岗」「学到的东西都用不上，急」→ `interview_prep`（与 SQLite 真实标注一致）。

---

### 3.2 多意图输入处理规则

| 层级 | 规则 |
|---|---|
| **LLM Prompt（当前 `TRIAGE_SYSTEM_PROMPT`）** | 仅允许输出**单个** `intent`，**未定义**多意图拆分规则。 |
| **设计文档（`docs/BLUEPRINT.md`，未落地）** | 多任务按用户提及**顺序依次**处理；若可并行则并行（当前代码不支持）。 |
| **关键词兜底（实际生效）** | **先匹配先生效**：`resume` 关键词 > `mock/面试` 关键词 > 默认 `interview_prep`。 |
| **微调数据集建议规则** | ① **主意图优先**：用户明确动作词（「改简历」「模拟面试」「制定计划」）胜出；② **并列时按求职链路**：`resume_opt` → `interview_prep` → `mock_interview`（先材料、再策略、再演练）；③ **无法裁决** → 标 `interview_prep` 并降 `confidence`，或单独标 `needs_clarification`（扩展标签）。 |

**多意图示例**

| 用户输入 | 推荐主 intent | 理由 |
|---|---|---|
| 先帮我把简历改一下，然后开始模拟面试 | `resume_opt` | 用户明确「先…改简历」 |
| 我想准备面试，顺便优化一下项目描述 | `interview_prep` | 主干是准备；「优化项目描述」可后续 handoff |
| 模拟一下 HR 面，然后告诉我简历哪里要改 | `mock_interview` | 用户先要求模拟 |
| 帮我准备面试（仅含「面试」关键词） | **冲突** | 语义 `interview_prep`，fallback 可能 → `mock_interview` |

---

## 四、SQLite 真实用户输入标注（30 条）

> 来源：`app.db` → `messages` 表，`role='user'`，共 36 条，取 30 条（按 `id` 升序，跳过 2 条重复快捷按钮文案）。

| # | id | 用户输入（摘要/原文） | 标注 intent | 备注 |
|---|---|---|---|---|
| 1 | 1 | 帮我准备面试 | `interview_prep` | ⚠ fallback 会因「面试」→ `mock_interview` |
| 2 | 3 | 帮我优化简历中的项目描述 | `resume_opt` | 快捷按钮原文 |
| 3 | 5 | 帮我制定一份前端工程师的面试准备计划 | `interview_prep` | 快捷按钮原文 |
| 4 | 11 | 我想从事ai应用开发相关工作 | `interview_prep` | 职业方向咨询 |
| 5 | 13 | 我想从事ai应用工程师，该准备什么 | `interview_prep` | |
| 6 | 15 | 介绍一下我的项目 | `mock_interview` | 上传简历后，面试式介绍；亦可能 `interview_prep` |
| 7 | 17 | 我这个简历怎么样 | `resume_opt` | |
| 8 | 19 | 现在都是八月了，滑坡项目是我毕设，ai求职助手是我毕业以后做的 | `interview_prep` | 时间线/叙事澄清 |
| 9 | 21 | 我想找ai应用开发工程师 | `interview_prep` | |
| 10 | 23 | 我的实习都是学校里的生产实习，学的不好 | `interview_prep` | 背景短板咨询 |
| 11 | 25 | （长文）AI多Agent求职助手项目总结…让ai总结了一下 | `interview_prep` | 项目表述/面试话术整理 |
| 12 | 27 | https://… 这是我做的项目链接…也就是你这个系统 | `interview_prep` | 作品集展示策略 |
| 13 | 29 | 我的简历还要改么 | `resume_opt` | |
| 14 | 31 | （长文）四六级要不要写简历…kimi的说法 | `resume_opt` | 简历字段取舍 |
| 15 | 33 | （长文）技术栈/生产可用/总结重复等硬伤改法 | `resume_opt` | |
| 16 | 35 | 20+模拟面试太假了…面试官会不会怀疑 | `resume_opt` | 简历表述真实性 |
| 17 | 37 | 给我一版完整简历 | `resume_opt` | |
| 18 | 39 | 我这个简历应该掌握到什么程度才能通过面试 | `interview_prep` | ⚠ 含「简历」但非改简历 |
| 19 | 41 | 我这个话术手册掌握了通过面试的几率多大 | `interview_prep` | |
| 20 | 43 | 现在ai应用开发不怎么考八股吧 | `interview_prep` | |
| 21 | 45 | 那我高频八股还搞么 | `interview_prep` | |
| 22 | 47 | 你要不先看看我的掌握程度 | `mock_interview` | 请求摸底/出题 |
| 23 | 49 | （长文）Triage/混合检索/SSE 等技术面作答 | `mock_interview` | 模拟面试中答题 |
| 24 | 51 | 4.不清楚 5.因为nano是最轻量… | `mock_interview` | 继续答题 |
| 25 | 53 | 我怎么能吃透我这个简历和我做过的部分呢 | `interview_prep` | |
| 26 | 55 | 算法部分呢，我要不要准备几道算法题 | `interview_prep` | |
| 27 | 57 | 新的对话还记得上次讲了什么么 | `out_of_scope` | 会话/meta 问询 |
| 28 | 61 | 这是我的简历，我要把简历掌握到什么程度，才能通过面试 | `interview_prep` | |
| 29 | 69 | 我有了这个简历该怎么准备面试 | `interview_prep` | ⚠ 含「面试」；语义为准备 |
| 30 | 71 | 我这个话术能解决多少 | `interview_prep` | 面试准备效果评估 |

---

## 五、代码 vs 设计文档：模糊与重叠（需裁决）

| # | 问题 | 现状 | 建议 |
|---|---|---|---|
| 1 | **`面试` 关键词过宽** | `_KEYWORD_RULES` 中单独「面试」→ `mock_interview`，导致「帮我准备面试」fallback 错路由 | 缩小为「模拟面试」「mock」「演练」；或增加「准备面试」例外 |
| 2 | **`interview_prep` vs `mock_interview` 边界** | Prompt 写「通用面试准备」vs「模拟演练」，但「面试技巧咨询」与「开始模拟」口语重叠 | 以**用户是否要当场问答**为硬规则写进 prompt |
| 3 | **`resume_opt` vs `interview_prep` 含「简历」** | 「简历掌握程度」「简历怎么讲」vs「简历怎么改」 | 区分 **改文档** vs **准备/掌握** |
| 4 | **`out_of_scope` 未实现** | 闲聊/meta 问题会进 `interview_prep` | 微调加第 4 类，或 Triage 前加拒答层 |
| 5 | **设计文档 10+ intent 未实现** | `job_search`、`salary_negotiate` 等只在 BLUEPRINT | 微调阶段勿引入未实现标签，或同步扩展 Specialist |
| 6 | **多意图无代码支持** | 只能路由 1 个 Specialist | 微调可先标主 intent；产品层需 sequential handoff |
| 7 | **空输入默认** | `classify` 空字符串 → `interview_prep`, confidence=0 | 微调可标 `out_of_scope` 或拒答 |
| 8 | **「介绍一下我的项目」** | 依赖是否在上传简历/模拟上下文中 | 需 session 上下文特征，单句难判 |

---

## 六、Specialist 与 Intent 映射（代码确认）

```
interview_prep  → InterviewPrepSpecialist  （INTERVIEW_PREP_PROMPT）
mock_interview  → MockInterviewSpecialist  （MOCK_INTERVIEW_PROMPT）
resume_opt      → ResumeOptSpecialist      （RESUME_OPT_PROMPT）
```

默认降级 Agent（Triage 失败）：`interview_prep`（`protection.py` → `DEFAULT_AGENT`）
