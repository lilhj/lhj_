# 券商研报 RAG 问答系统 — 头脑风暴要点总结

> 日期：2026-07-23 | 状态：已澄清

---

## 一、项目目标

构建一个**基于券商研报知识库的 RAG 智能问答系统**，作为券商首席分析师助理（🎩），
帮助分析师、基金经理和投研团队快速从 3-5 份研报中检索信息并生成专业回答。

**核心流程**: 上传研报 → 自动解析 → 向量化存储 → 自然语言提问 → 基于研报内容
给出专业回答 + 标注来源研报名称和 PDF 文件页码（从 1 开始）。

---

## 二、虚拟身份定义

| 属性 | 定义 |
|---|---|
| **身份** | 🎩 某券商首席分析师助理 |
| **口吻** | 专业严谨，符合券商研究行文风格 |
| **核心行为** | 所有回答 MUST 标注信息来源：`"根据XX证券《XX研报》第X页指出..."`（页码 = PDF 文件页码，从 1 开始） |
| **目标受众** | 券商分析师、基金经理、内部投研团队 |

---

## 三、核心功能

| # | 功能 | 优先级 | 描述 |
|---|---|---|---|
| ① | 多份 PDF 研报上传与解析 | MVP | Web 界面上传 PDF，后端 PyMuPDF 提取文本 + PDF 文件页码 |
| ② | 文本向量化存储 | MVP | LlamaIndex SentenceSplitter 分块 → BGE-large-zh 向量化 → FAISS 本地索引 |
| ③ | 自然语言问答 | MVP | 输入问题 → 向量检索 → Claude API 生成回答（不重试，失败即返回 502） |
| ④ | 显示引用来源 | MVP | 回答附带来源（研报名称 + PDF 文件页码），LlamaIndex CitationQueryEngine |
| ⑤ | 多文档跨文档检索 | MVP | 知识库 3-5 份研报，跨文档搜索 |
| ⑥ | 多轮对话 | MVP | 保留最近 3 轮 Q&A 作为上下文，滑动窗口截断 |
| ⭐ | chunk_size / 相似度阈值可调 | v1.1 | UI 滑块：chunk_size (200/400/600/800)，阈值 (0.3/0.5/0.7) |

---

## 四、技术约束

| 维度 | 选择 |
|---|---|
| **后端框架** | FastAPI（REST API，供 Web + CLI 共用） |
| **RAG 编排** | LlamaIndex（CitationQueryEngine 来源追踪） |
| **PDF 解析** | PyMuPDF |
| **嵌入模型** | BGE-large-zh（本地部署，1024 维） |
| **向量存储** | FAISS（本地持久化，data/faiss_index/） |
| **LLM** | Claude API (Anthropic) |
| **前端** | React + Vite（轻量 SPA） |
| **CLI** | Click/Typer（v1.1，调 REST API） |
| **目录** | backend/ + frontend/ |
| **部署** | 本地运行，研报数据不出公司 |

---

## 五、架构概览

```
frontend/ (React SPA) ──REST API──▶ backend/ (FastAPI)
                                      ├── RAG Pipeline (LlamaIndex)
                                      │   Loader → Splitter → Embedder → FAISS
                                      │   Question → Retriever → Claude API → Answer
                                      └── CLI (v1.1)
```

**两条数据流**：
- **索引链路**: PDF → PyMuPDF 提取(文本 + 页码) → SentenceSplitter 分块 → BGE 向量化 → FAISS 持久化
- **问答链路**: 问题 → BGE 向量化 → FAISS Top-K 检索(默认 3) → 组装 Prompt(🎩 身份 + 最近 3 轮对话 + Context) → Claude 生成（失败不重试） → 带来源的回答

---

## 六、用户故事

### US1 — 上传研报并建立知识库 (P1, MVP)
- 选择 3-5 份 PDF 上传，批量处理
- 部分失败不阻塞有效文件
- 索引本地持久化，重启自动恢复

### US2 — 自然语言提问获取专业回答 (P1, MVP)
- 自然语言提问，🎩 分析师口吻回答
- 来源标注：研报名称 + PDF 文件页码
- 多轮对话：保留最近 3 轮上下文
- 研报未覆盖时明确告知，不编造

### US3 — CLI 命令行问答 (P2, v1.1)
- `python -m backend.cli query "问题"` 终端输出带来源的回答

### US4 — 检索参数可调实验对比 (P3, v1.1)
- 滑块调 chunk_size (200/400/600/800) + 相似度阈值 (0.3/0.5/0.7)
- 对比不同参数下的回答质量

---

## 七、澄清记录 (2026-07-23)

| # | 问题 | 结论 |
|---|---|---|
| Q1 | PDF 页码定义 | PDF 文件页码，从 1 开始，与 PDF 阅读器一致 |
| Q2 | Claude API 失败是否重试 | 不重试，立即返回 502，由用户手动重试 |
| Q3 | 多轮对话上下文溢出 | 滑动窗口，保留最近 3 轮 Q&A |

---

## 八、对应文件索引

| 文件 | 路径 |
|---|---|
| Constitution | `.speckit/constitution.md` |
| Spec | `.speckit/spec.md` |
| Plan | `.speckit/plan.md` |
| Tasks | `.speckit/tasks.md` |
| Brainstorm | `docs/brainstorm.md` |
