# Interview-Assistant SKILL 开发计划（大树模型多智能体协作）

## 目标
将 interview-assistant-skill-v2.md 设计文档转化为符合 skill-creator-swarm 规范的正式 SKILL 包。

## 最终交付物
1. **完整MD提示词模板** — 保留全部细节，人类可读的总蓝图
2. **精简SKILL包** — SKILL.md + references/，符合规范，已打包为 .skill 文件

---

## Stage 1: 技能初始化（Infrastructure Agent）
- 运行 init_skill.py 创建目录结构
- 建立 references/ 目录骨架
- 产出：skill 目录框架

## Stage 2: 参考文档并行编写（Content Agents — 3路并行）
**大树模型第一层：3片叶子并行**

- **Agent_JobSpecialist**: 编写 references/job-specialist.md
- **Agent_InterviewSpecialist**: 编写 references/interview-specialist.md
- **Agent_CareerSpecialist**: 编写 references/career-specialist.md

每个 agent 接收对应模块的详细设计作为输入。

## Stage 3: SKILL.md 主文件编写（Core Agent）
- 基于 Stage 2 的 reference 文件索引，编写精简的 SKILL.md
- 确保 < 500 行，YAML frontmatter 正确，路由规则完整

## Stage 4: 审查梯队（Review Swarm — 多层交叉检查）
**第一层审查（结构审）：StructureReviewer**
- 检查目录结构、YAML frontmatter、文件引用路径
- 检查行数限制（SKILL.md < 500 行，每个 reference < 500 行）

**第二层审查（功能审）：FunctionReviewer**
- 检查 4 个角色定义完整性
- 检查 Handoff 保护机制
- 检查路由规则覆盖度

**第三层审查（内容审）：ContentReviewer**
- 检查每个 reference 文件内容质量
- 检查指令是否采用祈使/不定式形式
- 检查是否有冗余或遗漏

**审查结果汇总 → 生成修复清单**

## Stage 5: 修复与优化（Fix Agents — 按需并行）
- 根据审查结果，并行派发修复任务
- 合并冗余、抽离公共片段
- 控制 SKILL.md 主文件体量

## Stage 6: 双文件交付（Delivery Agent）
- 生成完整版 MD 提示词模板（人类可读总蓝图）
- 生成精简版 SKILL.md + references/
- 运行 package_skill.py 打包
- 验证打包结果

## Stage 7: Swarm 评估验证（Eval Swarm）
- 设计 3-5 个评估用例
- with_skill vs without_skill 对比执行
- Grader + Comparator 评估
- 如有问题，返回 Stage 5 修复

---

## 技能加载点
- Stage 1-3: 加载 skill-creator-swarm（init + edit）
- Stage 4-5: 加载 skill-creator-swarm（eval + iterate）
- Stage 6: 加载 skill-creator-swarm（packaging）
- Stage 7: 加载 skill-creator-swarm（swarm eval）
