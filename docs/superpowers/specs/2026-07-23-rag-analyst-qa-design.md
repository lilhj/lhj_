# 券商研报 RAG 问答系统 — 设计规格

> 日期：2026-07-23 | 版本：v1.0 | 状态：Draft

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [数据流](#3-数据流)
4. [API 设计](#4-api-设计)
5. [前端 UI 布局](#5-前端-ui-布局)
6. [错误处理](#6-错误处理)
7. [用户故事](#7-用户故事)
8. [技术约束](#8-技术约束)
9. [版本规划](#9-版本规划)
10. [附录](#10-附录)

---

## 1. 项目概述

### 1.1 项目目标

构建一个**基于券商研报知识库的 RAG 智能问答系统**，作为券商首席分析师助理（🎩），
帮助分析师、基金经理和投研团队快速从 3-5 份研报中检索信息并生成专业回答。

### 1.2 核心流程

```
上传 PDF 研报 → 自动解析与索引 → 自然语言提问 → 基于研报内容生成回答 + 标注来源
```

### 1.3 虚拟身份

| 属性 | 定义 |
|---|---|
| **身份** | 🎩 某券商首席分析师助理 |
| **口吻** | 专业严谨，符合券商研究行文风格 |
| **引源规范** | 所有回答 MUST 标注：`"根据XX证券《XX研报》第X页..."` |
| **目标受众** | 券商分析师、基金经理、内部投研团队 |

### 1.4 交互通道

- **Web 应用**（主要）：浏览器中完成文件上传、提问、查看回答
- **CLI 命令行**（次要）：终端调用同一套后端 API

---

## 2. 架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────┐
│                    frontend/                      │
│              (轻量 SPA — 文件上传 + 对话 UI)        │
└──────────────────────┬───────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────▼───────────────────────────┐
│                   backend/                        │
│                  (FastAPI)                        │
│                                                   │
│  POST /upload   POST /query   GET /status         │
│       │              │            │               │
│  ┌────▼──────────────▼────────────▼─────┐         │
│  │           RAG Pipeline                │         │
│  │        (LlamaIndex 编排)              │         │
│  │                                       │         │
│  │  PDF Loader  →  Splitter  →  Embed    │         │
│  │       (PyMuPDF)   (Sentence)  (BGE)   │         │
│  │                          │             │         │
│  │                   ┌──────▼──────┐      │         │
│  │                   │  FAISS 索引  │      │         │
│  │                   └──────┬──────┘      │         │
│  │                          │             │         │
│  │  Question  →  Retriever  →  LLM        │         │
│  │                          (Claude API)  │         │
│  └───────────────────────────────────────┘         │
│                                                   │
│  ┌──────────────────────┐                         │
│  │  CLI (Click/Typer)   │  ← REST API 消费者      │
│  └──────────────────────┘                         │
└──────────────────────────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 技术 | 职责 |
|---|---|---|
| **PDF Loader** | PyMuPDF (via LlamaIndex `SimpleDirectoryReader`) | 提取文本 + 页码，返回 `Document` 对象 |
| **Splitter** | LlamaIndex `SentenceSplitter` | 语义分块，chunk_size=512, overlap=50 |
| **Embedding** | BGE-large-zh (via `HuggingFaceEmbedding`) | 文本转向量，维度 1024 |
| **Index** | FAISS (via `FaissVectorStore`) | 向量相似度搜索，持久化到 `data/faiss_index/` |
| **Retriever** | LlamaIndex `VectorIndexRetriever` | Top-K 相似片段检索 |
| **Generator** | Claude API (via `anthropic` SDK) | 基于上下文生成专业回答 |
| **API Layer** | FastAPI | 暴露 REST 端点，处理文件上传和 JSON 请求 |

### 2.3 设计原则

- **LlamaIndex 仅为编排层**，核心逻辑（加载、分块、嵌入、检索）均暴露为独立函数，可脱离框架替换
- **CLI 与 Web 共享 API**，CLI 是 API 的薄封装层
- **索引持久化到本地磁盘**，重启无需重建

---

## 3. 数据流

### 3.1 索引链路（低频，上传时触发）

```
1. 上传 PDF 文件
       │
2. PyMuPDF 提取文本 + 页码
       │
3. SentenceSplitter 语义分块
   chunk_size=512, chunk_overlap=50
   每块携带元数据: {doc_name, page_num, chunk_id}
       │
4. BGE-large-zh 转向量 (1024 维)
       │
5. FAISS 写入索引并持久化到 data/faiss_index/
       │
6. 返回索引结果: {filename, pages, chunks_count, status}
```

### 3.2 问答链路（高频，每次提问触发）

```
1. 用户输入自然语言问题
       │
2. BGE-large-zh 将问题转向量
       │
3. FAISS 相似度搜索 → Top-K 片段 (K=3)
       │
4. 组装 Prompt:
   ┌─────────────────────────────┐
   │ System: 你是某券商首席分析师   │
   │         助理，回答基于研报内容  │
   │         必须标注来源...        │
   │ Context:                     │
   │   [片段1] 东吴-龙头份额 p.3   │
   │   [片段2] 国信-盈利稳健 p.5   │
   │   [片段3] 东吴-技术迭代 p.12  │
   │ Question: 宁德时代2025年...   │
   └─────────────────────────────┘
       │
5. Claude API 生成回答 (stream=False)
       │
6. 返回: {answer, sources[{doc, page, text, score}]}
```

---

## 4. API 设计

### 4.1 `POST /upload` — 上传研报

**Request**: `multipart/form-data`
```
files: [pdf, pdf, ...]   最多 5 个 PDF 文件
```

**Response**: `201 Created`
```json
{
  "uploaded": [
    {
      "filename": "东吴证券-宁德时代-技术迭代引领行业-260322.pdf",
      "pages": 32,
      "chunks": 210,
      "status": "indexed"
    }
  ],
  "errors": []
}
```

**错误码**:

| 状态码 | 场景 |
|---|---|
| 200 | 部分文件失败（失败项在 `errors` 数组中，成功项正常索引） |
| 400 | 全部文件无效 |
| 413 | 文件总大小超过 100MB |

### 4.2 `POST /query` — 自然语言提问

**Request**: `application/json`
```json
{
  "question": "宁德时代2025年产能规划是多少？",
  "top_k": 3
}
```

**Response**: `200 OK`
```json
{
  "answer": "根据《东吴证券-宁德时代-龙头份额再提升-260416》第3页的分析，公司2025年规划产能...",
  "sources": [
    {
      "doc": "东吴证券-宁德时代-龙头份额再提升-260416.pdf",
      "page": 3,
      "text": "公司2025年规划产能达...",
      "score": 0.87
    }
  ],
  "context_used": 3
}
```

**错误码**:

| 状态码 | 场景 |
|---|---|
| 200 | 检索无结果：`answer` 提示未找到，`sources` 为空 |
| 400 | `question` 为空或超过 2000 字符 |
| 503 | 知识库未初始化 |
| 502 | Claude API 调用失败 / 超时 (30s) / 鉴权失败 |

### 4.3 `GET /status` — 知识库状态

**Response**: `200 OK`
```json
{
  "indexed_docs": 4,
  "total_chunks": 856,
  "docs": [
    {
      "filename": "东吴证券-宁德时代-技术迭代引领行业-260322.pdf",
      "pages": 32,
      "chunks": 210,
      "indexed_at": "2026-07-23T15:30:00"
    }
  ],
  "embedding_model": "BGE-large-zh",
  "chunk_size": 512,
  "chunk_overlap": 50
}
```

---

## 5. 前端 UI 布局

```
┌─────────────────────────────────────────────────────┐
│  🎩 券商研报 RAG 问答系统            [已索引: 4份]  │  顶栏
├──────────────────────┬──────────────────────────────┤
│                      │                              │
│   📄 研报管理         │   💬 问答区                  │
│                      │                              │
│  ┌─────────────────┐ │  ┌──────────────────────────┐│
│  │ 拖拽或点击上传   │ │  │                          ││
│  │ PDF 文件 (≤5份)  │ │  │  您：宁德时代2025年       ││
│  │                 │ │  │  产能规划是多少？          ││
│  │ 已上传：        │ │  │                          ││
│  │ ✅ 东吴-技术迭代 │ │  │  🎩：根据《东吴证券-     ││
│  │ ✅ 东吴-龙头份额 │ │  │  宁德时代-龙头份额再提升》 ││
│  │ ✅ 国信-盈利稳健 │ │  │  第3页的分析，公司2025年  ││
│  │ ✅ 宁德时代.pdf  │ │  │  规划产能...              ││
│  └─────────────────┘ │  │                          ││
│                      │  │  ┌─ 📄 来源引用 ─────────┐││
│                      │  │  │ 东吴-龙头份额 p.3     │││
│                      │  │  │ 国信-盈利稳健 p.5     │││
│                      │  │  └──────────────────────┘││
│                      │  └──────────────────────────┘│
│                      │  ┌──────────────────────────┐│
│                      │  │ 输入问题...      [发送]   ││
│                      │  └──────────────────────────┘│
├──────────────────────┴──────────────────────────────┤
│  ⚙️ 参数 (v1.1): chunk_size [200|400|600|800]       │  底部 (v1.1)
│                  阈值 [0.3|0.5|0.7]                  │
└─────────────────────────────────────────────────────┘
```

| 区域 | 位置 | MVP | v1.1 |
|---|---|---|---|
| 顶栏 | 顶部 | 标题 + 虚拟身份 🎩 + 知识库状态 | 同 |
| 研报管理 | 左侧 30% | 上传区 + 已上传列表 | 增加删除按钮 |
| 问答区 | 右侧 70% | 对话历史 + 来源卡片 + 输入框 | 同 |
| 参数设置 | 底部 | 无 | 滑块：chunk_size + 阈值 |

---

## 6. 错误处理

### 6.1 上传阶段

| 场景 | 状态码 | 行为 |
|---|---|---|
| 文件不是 PDF | 200 (部分成功) | `errors[]`: `{"file":"xxx.docx", "error":"不支持的文件类型，仅接受 PDF"}` |
| PDF 损坏/无法解析 | 200 (部分成功) | `errors[]`: `{"file":"broken.pdf", "error":"文件已损坏，无法解析"}` |
| PDF 纯图片无文字 | 200 (部分成功) | `errors[]`: `{"file":"scan.pdf", "error":"无可提取的文本内容"}` |
| 全部文件无效 | 400 | `{"detail":"所有上传文件均无效"}` |
| 超过 5 份限制 | 400 | `{"detail":"单次最多 5 份，当前还可上传 {n} 份"}` |
| 总大小超 100MB | 413 | `{"detail":"文件总大小超过 100MB"}` |

### 6.2 问答阶段

| 场景 | 状态码 | 行为 |
|---|---|---|
| 问题为空 | 400 | `{"detail":"问题不能为空"}` |
| 问题超过 2000 字 | 400 | `{"detail":"问题长度超过限制"}` |
| 知识库未初始化 | 503 | `{"detail":"请先上传研报"}` |
| 检索无相关结果 | 200 | `{"answer":"当前知识库中未找到相关信息。","sources":[], "context_used":0}` |
| Claude API 超时 (30s) | 502 | `{"detail":"LLM 服务超时，请稍后重试"}` |
| Claude API 鉴权失败 | 502 | 返回通用错误，详情记录后端日志 |
| 网络中断 | — | 前端 Toast: "请求超时，请检查后端服务" |

### 6.3 前端统一策略

```
API 4xx/5xx 错误 → Toast 通知，3 秒自动消失，不阻断操作
网络超时         → "请求超时，请检查后端服务是否运行"
500 未知错误     → "服务异常，请稍后重试"
```

---

## 7. 用户故事

### US1 — 上传研报并建立知识库 (P1, MVP)

> 作为投研团队成员，我希望上传 3-5 份 PDF 研报，系统自动解析并建立可检索的知识库。

**验收场景**:

1. 用户在 Web 界面选择 PDF 文件（拖拽或点击），点击上传
2. 系统显示上传进度，完成后展示已索引的研报列表（名称、页数、状态）
3. 同时上传多个文件时，成功和失败独立处理——有效文件正常索引，无效文件返回错误说明
4. 索引持久化到本地 `data/faiss_index/`，重启后无需重新上传
5. 上传已存在的同名文件时，提示是否覆盖旧索引

### US2 — 自然语言提问获取专业回答 (P1, MVP)

> 作为分析师，我希望用自然语言提问，系统基于研报内容给出专业回答，并标注信息来源。

**验收场景**:

1. 用户输入问题，系统检索 Top-3 片段并生成回答
2. 回答以 🎩 分析师助理口吻呈现，专业严谨
3. 回答中标注引用来源：`"根据《XX证券-XX研报》第X页..."`
4. 每个回答下方展示可展开的来源卡片（研报名 + 页码 + 原文片段 + 相似度分数）
5. 当研报中无相关信息时，明确告知 "当前知识库未覆盖该问题"
6. 支持追问（多轮对话上下文延续）

### US3 — CLI 命令行问答 (P2, v1.1)

> 作为偏好终端的分析师，我希望在命令行中直接提问。

**验收场景**:

1. `python -m backend.cli query "问题"` 返回带来源标注的回答
2. `python -m backend.cli status` 显示已索引研报列表
3. CLI 与 Web 共享后端 API，行为一致

### US4 — 参数可调实验对比 (P3, v1.1)

> 作为投研人员，我希望调整检索参数，对比不同配置下的回答质量。

**验收场景**:

1. UI 底部滑块调整 chunk_size (200/400/600/800) 和相似度阈值 (0.3/0.5/0.7)
2. 切换参数后重新提问，可观察回答差异
3. 显示当前参数下检索到的片段数量和相似度分数

---

## 8. 技术约束

| 维度 | 选择 |
|---|---|
| **后端语言** | Python 3.11+ |
| **后端框架** | FastAPI |
| **RAG 编排** | LlamaIndex（`SimpleDirectoryReader` + `VectorStoreIndex` + `CitationQueryEngine`） |
| **PDF 解析** | PyMuPDF |
| **文本分块** | `SentenceSplitter`, chunk_size=512, overlap=50 |
| **嵌入模型** | BGE-large-zh (本地部署) |
| **向量存储** | FAISS (faiss-cpu), 持久化到 `data/faiss_index/` |
| **LLM** | Claude API (Anthropic SDK) |
| **前端** | 轻量 SPA（具体框架由 plan 阶段确定） |
| **CLI** | Click 或 Typer |
| **依赖管理** | `requirements.txt` + `package.json` |
| **目录结构** | `backend/` + `frontend/` |
| **多文档** | 3-5 份研报，跨文档检索 |
| **部署** | 本地运行，数据不出公司 |

---

## 9. 版本规划

### MVP (v1.0)

- [x] PDF 上传与解析（多文件，批量处理）
- [x] 文本向量化存储（FAISS 本地持久化）
- [x] 自然语言问答（Claude API 生成）
- [x] 来源引用标注（研报名称 + 页码）
- [x] 跨文档检索（3-5 份研报并行搜索）
- [x] 知识库状态查询

### v1.1

- [ ] chunk_size 可调滑块 (200/400/600/800)
- [ ] 相似度阈值可调滑块 (0.3/0.5/0.7)
- [ ] CLI 命令行问答
- [ ] 参数对比展示

---

## 10. 附录

### 10.1 目标目录结构

```
backend/
├── src/
│   ├── ingestion/          PDF 加载与解析
│   │   ├── __init__.py
│   │   └── loader.py
│   ├── chunking/           文本分块
│   │   ├── __init__.py
│   │   └── splitter.py
│   ├── embedding/          嵌入向量化
│   │   ├── __init__.py
│   │   └── embedder.py
│   ├── indexing/           向量索引
│   │   ├── __init__.py
│   │   └── indexer.py
│   ├── retrieval/          检索逻辑
│   │   ├── __init__.py
│   │   └── retriever.py
│   ├── generation/         答案生成
│   │   ├── __init__.py
│   │   └── generator.py
│   ├── api/                FastAPI 路由
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── query.py
│   │   └── status.py
│   └── cli/                CLI 命令
│       ├── __init__.py
│       └── main.py
├── tests/
│   ├── test_loader.py
│   ├── test_splitter.py
│   ├── test_embedder.py
│   ├── test_retriever.py
│   └── test_api.py
├── requirements.txt
└── main.py                 FastAPI 入口

frontend/
├── src/
│   ├── components/
│   │   ├── ChatArea.jsx
│   │   ├── FileUploader.jsx
│   │   ├── SourceCard.jsx
│   │   └── StatusBar.jsx
│   ├── App.jsx
│   └── main.jsx
├── public/
├── package.json
└── index.html

data/
├── reports/                原始 PDF 研报
└── faiss_index/            持久化向量索引

docs/
├── brainstorm.md
└── superpowers/
    └── specs/
        └── 2026-07-23-rag-analyst-qa-design.md
```

### 10.2 关键依赖

**Python (backend/requirements.txt)**:
```
fastapi
uvicorn
python-multipart
llama-index
llama-index-vector-stores-faiss
llama-index-embeddings-huggingface
faiss-cpu
sentence-transformers
pymupdf
anthropic
click          # v1.1 CLI
python-dotenv
```

**Node.js (frontend/package.json)**:
```
react          # 或其他轻量框架，plan 阶段确定
vite
```
