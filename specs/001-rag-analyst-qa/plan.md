# Implementation Plan: 券商研报 RAG 智能问答系统

**Branch**: `001-rag-analyst-qa` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-rag-analyst-qa/spec.md`

## Summary

构建一个基于 LlamaIndex 编排的 RAG 问答系统，核心链路：上传 PDF 研报 → PyMuPDF 解析文本+页码
→ SentenceSplitter 语义分块 → BGE-large-zh 文本向量化 → FAISS 索引持久化 → 用户自然语言提问
→ 向量检索 Top-K 片段 → Claude API 生成 🎩 分析师口吻回答 → 标注来源（研报名+页码）。

技术方案已通过头脑风暴完整确认：FastAPI 后端 + LlamaIndex RAG 管道 + 轻量前端 SPA + CLI 消费者，
前后端分离，CLI 与 Web 共用同一套 REST API。

## Technical Context

**Language/Version**: Python 3.11+, Node.js 18+ (前端)
**Primary Dependencies**: FastAPI, LlamaIndex, llama-index-vector-stores-faiss,
  llama-index-embeddings-huggingface, faiss-cpu, sentence-transformers (BGE-large-zh),
  PyMuPDF, anthropic SDK, python-dotenv
**Storage**: FAISS 本地文件索引 (`data/faiss_index/`) + JSON 元数据文件
**Testing**: pytest
**Target Platform**: 本地开发/运行（Windows/Linux/macOS）
**Project Type**: Web 服务（FastAPI）+ CLI（Click）+ 前端 SPA
**Performance Goals**: 单份 30 页研报索引 < 60s，问答 < 30s，重启恢复 < 10s
**Constraints**: 研报数据不离开本地，仅最小检索片段发送 Claude API；3-5 份研报；单用户
**Scale/Scope**: MVP 覆盖 US1(上传索引) + US2(问答溯源)，v1.1 加入 US3(CLI) + US4(参数调节)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. 数据本地化与隐私优先 | ✅ PASS | PDF 解析/分块/嵌入全部本地执行；仅 Top-K 检索片段发送 Claude API；FR-012 硬编码禁止 |
| II. 模块化管道架构 | ✅ PASS | 6 阶段管道独立目录：ingestion/chunking/embedding/indexing/retrieval/generation，每模块独立函数接口 |
| III. 检索质量可度量 | ✅ PASS | SC-004(90%引用准确率)、SC-005(100%拒答覆盖)；评估集将在 research.md 中定义 |
| IV. 可观测性 | ✅ PASS | 每个管道阶段记录输入/输出摘要、耗时、token 数；LLM 调记录模型+延迟 |
| V. 简洁优先 | ✅ PASS | MVP 单轮检索+生成，不引入 multi-hop/agentic RAG；FAISS 本地文件索引无需独立服务 |
| VI. 来源引用强制规范 | ✅ PASS | FR-007 要求回答标注研报名+页码；FR-003 分块携带元数据；LlamaIndex CitationQueryEngine 支持 |
| VII. 安全配置管理 | ✅ PASS | FR-011 环境变量读取密钥；.env.example 模板 + .gitignore；Claude API key 走 ANTHROPIC_API_KEY |
| VIII. 核心模块测试覆盖 | ✅ PASS | tests/ 覆盖 loader、splitter、embedder、retriever；pytest 自动执行 |

**Gate Result**: ALL PASS — 无违规项，无需 Complexity Tracking。

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-analyst-qa/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
│   ├── upload.md
│   ├── query.md
│   └── status.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── ingestion/
│   │   └── loader.py          # PyMuPDF PDF 加载 (via LlamaIndex SimpleDirectoryReader)
│   ├── chunking/
│   │   └── splitter.py         # SentenceSplitter 分块 (chunk_size=512, overlap=50)
│   ├── embedding/
│   │   └── embedder.py         # BGE-large-zh 向量化
│   ├── indexing/
│   │   └── indexer.py          # FAISS 索引构建与持久化
│   ├── retrieval/
│   │   └── retriever.py        # FAISS 相似度搜索 + CitationQueryEngine
│   ├── generation/
│   │   └── generator.py        # Claude API 答案生成 (源引标注)
│   ├── api/
│   │   ├── upload.py            # POST /upload 路由
│   │   ├── query.py             # POST /query 路由
│   │   └── status.py            # GET /status 路由
│   ├── config.py               # 环境变量加载 + 全局配置
│   └── cli/
│       └── main.py              # CLI (v1.1)
├── tests/
│   ├── test_loader.py
│   ├── test_splitter.py
│   ├── test_embedder.py
│   ├── test_retriever.py
│   └── test_api.py
├── main.py                      # FastAPI 入口 + uvicorn
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── components/
│   │   ├── FileUploader.jsx    # 拖拽/点击上传 PDF
│   │   ├── ChatArea.jsx        # 问答对话区
│   │   ├── SourceCard.jsx      # 来源引用折叠卡片
│   │   └── StatusBar.jsx       # 顶栏知识库状态
│   ├── App.jsx
│   └── main.jsx
├── public/
├── package.json
├── vite.config.js
└── index.html

data/
├── reports/                     # 原始 PDF 研报
└── faiss_index/                 # FAISS 持久化索引文件
```

**Structure Decision**: 单项目前后端分离。`backend/` 承载全部 Python RAG 逻辑和 API，
`frontend/` 承载 SPA UI。CLI 作为 backend 的子模块，与前端共享同一套 REST API。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

无违规项 — 本表留空。
