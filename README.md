# Interview Assistant · 多 Agent 协作求职助手

<p align="center">
  <img src="./docs/demo.gif" alt="AI求职助手演示" width="800"/>
</p>

<p align="center">
  <a href="https://xuehualiange.github.io/interview-assistant/">🌐 在线体验</a> •
  <a href="#快速开始">⚡ 本地运行</a>
</p>

> **从架构设计到工程落地的完整闭环** — 先写 SKILL 设计文档，再实现可运行的 FastAPI 后端、SSE 前端与 Docker 部署。

[![GitHub](https://img.shields.io/badge/GitHub-interview--assistant-181717?logo=github)](https://github.com/xuehualiange/interview-assistant)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-DeepSeek-1C3C3C)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)

[English](#english) | [中文](#chinese)

---

## 中文

AI 驱动的求职全链路助手，采用 **Triage + Specialist Handoff** 多 Agent 架构。本项目包含两层交付：

| 层级 | 内容 | 说明 |
|------|------|------|
| **设计层** | [`SKILL.md`](./SKILL.md) + [`references/`](./references/) | Cursor/Claude Skill 规范，三位专家完整 Prompt |
| **工程层** | `app/` + [`index.html`](./index.html) + Docker | 可运行的 FastAPI 后端 + SSE 可视化前端 |

用户输入自然语言 → **Triage Agent** 识别意图 → 路由至专家 Agent → **SSE 流式**返回 → **SQLite** 持久化。

### 为什么这个项目？

| 阶段 | 产出 | 说明 |
|------|------|------|
| **① 架构设计** | [`SKILL.md`](./SKILL.md) + [`references/`](./references/) + [`docs/DESIGN-v2.md`](./docs/DESIGN-v2.md) | Triage 路由、三位专家 Prompt、9 模块设计方案 |
| **② 后端工程** | `app/` | FastAPI + LangChain + DeepSeek，四重保护机制 |
| **③ 前端交互** | `index.html` | GitHub Dark 对话 UI，fetch + ReadableStream |
| **④ 容器化部署** | `Dockerfile` + `docker-compose.yml` | 一键启动，SQLite 数据持久化 |

### 核心能力

| 模块 | 设计文档（SKILL） | 工程实现（MVP） |
|------|------------------|----------------|
| 意图路由 | InterviewTriage | `TriageAgent` — JSON 结构化 + 关键词兜底 |
| 模拟面试 | InterviewSpecialist | `MockInterviewSpecialist` |
| 简历优化 | CareerSpecialist | `ResumeOptSpecialist` |
| 面试准备 | CareerSpecialist / InterviewSpecialist | `InterviewPrepSpecialist` |
| 职位分析 | JobSpecialist | 📋 Phase 2（见 DESIGN-v2 路线图） |
| Handoff 保护 | 4 重机制 | `AgentProtection` — 轮次/循环/降级/回退 |

### 架构概览

```
┌─────────────┐     POST /chat (SSE)     ┌──────────────────────────────────────┐
│  index.html │ ───────────────────────▶ │           FastAPI (main.py)          │
└─────────────┘ ◀── triage/chunk/end ── │  Triage → Protection → Specialist    │
                                         │       ↓                              │
                                         │  SQLite (messages)                   │
                                         └──────────────────────────────────────┘
         设计层：SKILL.md + references/          工程层：app/
```

**设计文档**：[SKILL.md](./SKILL.md) · [DESIGN-v2.md](./docs/DESIGN-v2.md) · [BLUEPRINT.md](./docs/BLUEPRINT.md)

### 项目结构

```
interview-assistant/
├── SKILL.md                      # 架构设计入口（Skill 规范 + 设计→工程映射）
├── references/                   # 三位专家详细 Prompt（Skill 参考文档）
│   ├── job-specialist.md
│   ├── interview-specialist.md
│   └── career-specialist.md
├── docs/
│   ├── DESIGN-v2.md              # 完整设计方案（60+ 工具研究、路线图）
│   ├── BLUEPRINT.md              # 提示词总蓝图
│   └── PLAN.md                   # SKILL 包开发计划
├── app/                          # FastAPI 后端
│   ├── main.py                   # SSE / 历史 / 会话 API
│   ├── agent.py                  # Triage Agent
│   ├── specialists.py            # 三位 Specialist
│   ├── protection.py             # 四重保护机制
│   ├── orchestrator.py           # 编排器
│   ├── database.py               # SQLite ORM
│   └── config.py                 # 环境变量
├── index.html                    # 可视化前端
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### 快速开始

```bash
git clone https://github.com/xuehualiange/interview-assistant.git
cd interview-assistant

cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# Docker（推荐）
docker compose up -d --build

# 或本地开发
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端：浏览器打开 index.html 或 python -m http.server 5500
```

验证：`curl http://localhost:8000/health`

### 技术栈

FastAPI · LangChain · DeepSeek · SQLite · SSE · Docker

### 设计亮点（面试向）

1. **先设计后编码** — SKILL.md 定义架构，代码一一对应
2. **渐进式披露** — 主入口精简，references/ 按需加载
3. **LLM 结构化输出** — Triage JSON + Pydantic 校验 + 关键词兜底
4. **SSE 流式** — 单向推送，HTTP 语义，穿透代理更简单
5. **四重保护收敛** — `AgentProtection` 单类管理全部边界

---

## English

AI-powered job search assistant with **Triage + Specialist Handoff** multi-Agent architecture. Two delivery layers:

| Layer | Contents | Description |
|-------|----------|-------------|
| **Design** | [`SKILL.md`](./SKILL.md) + [`references/`](./references/) | Skill spec with specialist prompts |
| **Engineering** | `app/` + [`index.html`](./index.html) + Docker | Runnable FastAPI backend + SSE frontend |

### Quick Start

```bash
git clone https://github.com/xuehualiange/interview-assistant.git
cd interview-assistant
cp .env.example .env  # set DEEPSEEK_API_KEY
docker compose up -d --build
```

### Tech Stack

FastAPI · LangChain · DeepSeek · SQLite · SSE · Docker

---

## License

MIT License · Copyright (c) 2026 Wu Yu

---

## 本地微调意图路由（LoRA + Ollama）

### 动机

项目原意图路由依赖 DeepSeek API，存在三个痛点：

- **在线依赖**：断网或 API 波动时路由不可用
- **延迟**：p50 约 930ms，对话首 token 被拖慢
- **成本与隐私**：每次请求计费，用户输入需出网

因此用 LoRA 微调 Qwen3-1.7B-Base，把意图路由（Triage，四分类 JSON 输出）下沉到本机。

### 效果对比（冻结真实测试集 100 条，同集对比）

| 指标 | 本地微调模型（Q4_K_M） | DeepSeek API（四分类完整 prompt） |
|------|------------------------|-----------------------------------|
| 准确率 | **93%** | 88% |
| p50 延迟 | **393ms** | 932ms |
| p95 延迟 | **414ms** | 1248ms |
| 单次成本（100 条） | **¥0** | ¥0.1067 |
| 离线可用 | ✅ | ❌ |

> 测试集为人工整理的真实用户输入，训练/测试严格隔离，测试集冻结不再改动。基线采用 DeepSeek 的最强形态（补齐第四类定义的完整 prompt），而非极简 prompt。

### 技术要点

- **微调**：Qwen3-1.7B-Base + LoRA，仅 0.5% 参数可训练；AutoDL 单卡训练
- **数据**：合成数据 + 真实样本，错例分桶后定向补数，两轮迭代（84% → 95%，bf16 测试口径）
- **量化部署**：合并 LoRA 权重 → llama.cpp 转 GGUF（F16）→ `ollama create --quantize q4_K_M`，模型体积 3.4GB → 1.1GB，6GB 显存本机可跑；量化代价约 -2pp（95% → 93%）
- **输出契约**：ChatML 模板，模型直接输出 `{"intent": "..."}`；调用方对首个 `{...}` 做正则提取，温度 0、num_predict 32
- **双后端热切换**：`ROUTER_BACKEND=local|api` 环境变量切换；本地链路为 Ollama → DeepSeek → 关键词兜底三级降级，本地服务宕机自动回退 API，已做故障注入验证

### 快速开始

```bash
# 1. 安装并启动 Ollama，创建模型（仓库内提供 Modelfile，GGUF 需自行转换）
ollama create --quantize q4_K_M triage-router -f finetune/Modelfile

# 2. 切换到本地路由（.env）
ROUTER_BACKEND=local
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=triage-router

# 3. 正常启动项目即可，路由自动走本地模型
```

### 复现评测

```bash
python finetune/eval_ollama.py     # 本地模型评测（需 Ollama 已启动）
python finetune/eval_deepseek.py   # DeepSeek 基线评测（需 DEEPSEEK_API_KEY）
```

评测使用同一份冻结测试集 `finetune/data/test.jsonl`，prompt 与线上生产一致。

### 已知局限

- 小模型对输入格式敏感：必须带训练时的 INSTR 指令前缀，裸用户文本会 OOD 输出乱码（生产路由恒前置 INSTR，不受影响）
- `out_of_scope` 错例集中在「真实文本碎片」边界样本，已记录于 `finetune/dataset_card.md`
- Q4_K_M 量化后输出偶发垃圾 token（位于 JSON 前缀），因 JSON 提取鲁棒，不影响线上指标

