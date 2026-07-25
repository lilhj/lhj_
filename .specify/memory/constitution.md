<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 1.1.0
  Bump rationale: MINOR — 3 new principles added (来源引用、安全配置、测试覆盖),
  Technical Constraints and Development Workflow materially expanded with
  directory structure, dependency management, multi-document support, persona,
  and code style requirements.

  Modified principles:
    - (unchanged) I. 数据本地化与隐私优先
    - (unchanged) II. 模块化管道架构
    - (unchanged) III. 检索质量可度量
    - (unchanged) IV. 可观测性
    - (unchanged) V. 简洁优先

  Added sections:
    - VI. 来源引用强制规范 (Mandatory Source Attribution)
    - VII. 安全配置管理 (Secure Configuration Management)
    - VIII. 核心模块测试覆盖 (Core Module Test Coverage)

  Expanded sections:
    - Technical Constraints: 目录结构、依赖管理、多文档支持、虚拟身份
    - Development Workflow: 代码风格规范、测试要求

  Removed sections: None

  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ no changes needed
    - .specify/templates/spec-template.md ✅ no changes needed
    - .specify/templates/tasks-template.md ✅ no changes needed
    - .specify/templates/checklist-template.md ✅ no changes needed

  Follow-up TODOs: None — all placeholders resolved.
-->

# 券商研报 RAG 问答系统 Constitution

## Core Principles

### I. 数据本地化与隐私优先 (Data Locality & Privacy First)

所有券商研报 PDF 文档的处理 MUST 在本地环境中完成。MUST NOT 将原始研报内容
上传至任何外部 API 或云服务。文本提取、分块（chunking）、嵌入向量生成
（embedding）等预处理步骤 MUST 全部离线执行。仅检索到的、最小必要的上下文
片段可以发送给 LLM 进行答案生成。

**Rationale**: 券商研报属于付费商业数据，具有版权和合规约束。本地处理确保
数据主权，避免合规风险和知识产权争议。

### II. 模块化管道架构 (Modular Pipeline Architecture)

RAG 管道 MUST 由独立、可替换的模块组成：

- **文档摄入** (Ingestion): PDF 加载与解析
- **文本分块** (Chunking): 语义感知的文本切分
- **嵌入向量化** (Embedding): 文本转向量表示
- **向量索引** (Indexing): 向量存储与相似性搜索
- **检索** (Retrieval): 查询-文档相关性匹配
- **生成** (Generation): 基于检索上下文的答案生成

每个模块 MUST 有明确的输入/输出契约，可独立测试和替换。MUST NOT 出现模块间
的隐式耦合。

**Rationale**: RAG 系统需要频繁实验和优化各环节（换用不同分块策略、嵌入
模型、向量数据库等）。模块化架构使对比实验和渐进式演进成为可能。

### III. 检索质量可度量 (Measurable Retrieval Quality)

任何检索策略变更 MUST 通过量化评估验证。MUST 建立基准数据集（ground truth）
并计算标准指标：Recall@K、MRR（Mean Reciprocal Rank）、NDCG。生成质量 MUST
通过人工评审或 LLM-as-judge 进行评估。评估结果 MUST 记录在案，用于回归测试。

**Rationale**: RAG 系统的核心价值在于检索质量。没有量化基准，任何改动都
无法判断是改进还是退化。数据驱动决策是系统演进的基础。

### IV. 可观测性 (Observability)

所有管道阶段 MUST 输出结构化日志，包含：阶段名称、输入/输出摘要、耗时、
资源使用（token 数、内存）。LLM 调用 MUST 记录：模型名称、提示词 token 数、
生成 token 数、延迟。检索步骤 MUST 记录：查询文本、返回文档 ID 及相似度分数。

**Rationale**: RAG 管道涉及多个异步阶段，排查问题需要端到端追踪能力。
结构化日志是性能优化、成本管控和质量诊断的前提。

### V. 简洁优先 (Simplicity First, YAGNI)

MUST 优先选择最简单的可行方案。在基准数据证明有必要之前，MUST NOT 引入复杂
架构（如 multi-hop retrieval、agentic RAG、混合检索等）。过早优化 MUST NOT
阻塞核心功能交付。复杂性的引入 MUST 有明确的量化收益支撑。

**Rationale**: RAG 领域技术迭代极快，容易陷入过度工程化。保持简洁有利于
快速交付、降低维护负担、适应需求变化。

### VI. 来源引用强制规范 (Mandatory Source Attribution)

系统生成的每一份回答 MUST 标注信息来源，包含：
- **研报名称**: 完整的研报标题
- **页码**: 信息来源所在的页码（如 PDF 页码）

MUST NOT 生成无法追溯到具体文档和页码的回答。检索到的上下文片段 MUST 携带
来源元数据（文档名、页码、段落位置），并随生成结果一起透出。引用格式示例：

> 根据《东吴证券-宁德时代-龙头份额再提升-260416》第 3 页的分析……

**Rationale**: 券商分析师对信息来源有严格的可溯性要求。标注来源不仅是专业
规范的体现，也使用户能够验证信息准确性、追溯原始分析逻辑。

### VII. 安全配置管理 (Secure Configuration Management)

所有密钥、密码、API Token、数据库连接串等敏感配置 MUST 从环境变量读取。
MUST NOT 在源代码、配置文件或文档中硬编码任何凭据。环境变量命名 MUST 使用
大写蛇形（UPPER_SNAKE_CASE）格式，如 `ANTHROPIC_API_KEY`、`DATABASE_URL`。

项目 MUST 提供 `.env.example` 模板文件列出所需变量（不包含真实值），并确保
`.env` 已加入 `.gitignore`。

**Rationale**: 凭据硬编码是最高频的安全漏洞之一。环境变量隔离敏感配置是
行业标准实践，也是 CI/CD 和容器化部署的基础要求。

### VIII. 核心模块测试覆盖 (Core Module Test Coverage)

管道核心模块 MUST 有对应的单元测试。至少覆盖以下模块：

- PDF 解析与文本提取
- 文本分块（chunking）逻辑
- 嵌入向量生成
- 检索查询构建

测试 MUST 在 CI 流程中自动执行。新增核心模块 MUST 同时交付测试用例。测试
框架使用 pytest。

**Rationale**: RAG 管道各模块独立演进，测试是防止回归的唯一可靠保障。
核心模块出问题会级联影响最终回答质量。

## Technical Constraints

- **语言与运行时**: Python 3.11+；前端使用 Node.js 18+
- **依赖管理**: Python 使用 `requirements.txt`（`pip install -r requirements.txt`）；
  前端使用 `package.json`（`npm install`）。虚拟环境使用 venv
- **目录结构**: 后端代码统一放置 `backend/` 目录；前端代码统一放置 `frontend/`
  目录。项目根目录仅存放全局配置和文档
  ```
  backend/
  ├── src/
  │   ├── ingestion/    # PDF 加载与解析
  │   ├── chunking/     # 文本分块
  │   ├── embedding/    # 嵌入向量化
  │   ├── indexing/     # 向量索引
  │   ├── retrieval/    # 检索逻辑
  │   └── generation/   # LLM 答案生成
  └── tests/
  frontend/
  ├── src/
  └── public/
  data/
  └── reports/          # 原始 PDF 研报文件
  ```
- **向量数据库**: FAISS（本地文件索引）或 Chroma（嵌入式向量库），禁止引入
  需要独立部署的外部向量数据库服务（如 Pinecone、Weaviate、Milvus）
- **嵌入模型**: 优先使用本地可部署的中文语义模型（如 BGE-large-zh、
  text2vec-large-chinese）。如需实验对比，可备选云端嵌入 API，但 MUST NOT
  传输原始研报文本
- **LLM**: Claude API (Anthropic) 用于答案生成，理由：中文能力强、上下文窗口
  大（适合长研报上下文）
- **编排框架**: LangChain 或 LlamaIndex 作为管道编排层，但 MUST NOT 被框架
  锁定——核心逻辑 MUST 可脱离框架独立运行
- **存储**: 暂不引入关系数据库。文档元数据、分块信息使用 JSON/Parquet 文件
  存储；向量索引使用 FAISS 文件持久化
- **多文档支持**: 知识库 MUST 同时支持 3-5 份研报的并行索引。检索时 MUST
  跨所有已索引文档执行搜索，不限定单一文档
- **虚拟身份**: 系统交互身份为 🎩 **某券商首席分析师助理**，所有回答 MUST
  以专业分析师口吻呈现，风格专业严谨
- **平台**: 本地开发/运行（Windows/Linux/macOS），暂不涉及服务端部署

## Development Workflow

- **规格驱动开发**: 所有功能 MUST 先编写 spec.md 定义用户场景、需求和验收标准，
  再进入 plan.md 技术方案设计，最后拆解为 tasks.md 任务列表。遵循 Speckit
  workflow: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`
- **代码风格**: Python 代码 MUST 遵循 PEP 8 规范；前端代码 MUST 使用 ESLint
  进行检查。代码风格检查建议在提交前自动执行
- **分支策略**: 每个功能在独立分支上开发，分支名格式 `###-feature-name`，
  完成后合并至 `master`（主分支）
- **Code Review**: 合并前 MUST 通过代码审查。审查重点：管道模块契约是否符合
  定义、日志是否完整、是否有合规风险（数据泄露）、安全凭据是否有硬编码风险
- **Constitution 检查**: 每个 feature plan 的 Phase 0 研究阶段 MUST 做
  Constitution Check，Phase 1 设计完成后 MUST 复查一次
- **测试要求**: 核心模块 MUST 有单元测试（参见 Principle VIII）。推荐遵循 TDD：
  先写测试 → 测试失败 → 实现功能 → 测试通过
- **提交规范**: 提交信息使用中文，简明描述改动。格式：`<类型>: <简述>`
  （如 `feat: PDF 解析模块`、`fix: chunking 边界处理`）

## Governance

本 Constitution 是本项目的最高治理文件，其权威高于其他任何开发实践和惯例。

**修订流程**:
- 修订提案 MUST 通过 PR 提交，说明修订理由和影响范围
- 重大修订（原则增删或重新定义）MUST 经过讨论和明确批准
- 修订后 MUST 更新 `LAST_AMENDED_DATE` 并按语义化版本规则递增
  `CONSTITUTION_VERSION`
- 修订后 MUST 检查并更新所有依赖模板（plan、spec、tasks、checklist）以确保
  一致性

**版本策略**:
- MAJOR: 原则删除、重新定义，或向后不兼容的治理变更
- MINOR: 新增原则或章节，或现有原则的实质性扩充
- PATCH: 措辞澄清、错字修复、非语义性调整

**合规审查**:
- 每个 feature plan 的 Phase 0 MUST 包含 Constitution Check，确认设计方案与
  Constitution 原则一致
- 发现的违规项 MUST 在 `plan.md` 的 Complexity Tracking 表格中记录并说明合理性
- 无法合理说明的违规 MUST 在设计阶段解决后方可进入实现阶段

**Version**: 1.1.0 | **Ratified**: 2026-07-23 | **Last Amended**: 2026-07-23
