# 🏦 券商研报 RAG 问答系统

基于 **RAG（检索增强生成）** 的券商研报智能问答系统，支持上传 PDF 研报，通过自然语言提问，AI 自动检索相关段落并生成带来源引用的专业回答。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       🖥️  前端 (React + Vite)                    │
│                        http://localhost:5173                     │
│                                                                 │
│   ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│   │ 📄 上传研报   │  │  💬 问答对话   │  │ ⚙️ 参数调优面板  │   │
│   │  Drag & Drop │  │  SSE 打字机流  │  │ chunk_size / 阈值 │   │
│   └──────┬───────┘  └───────┬────────┘  └────────┬─────────┘   │
└──────────┼──────────────────┼─────────────────────┼─────────────┘
           │                  │                     │
      Vite Proxy ─────────────┼─────────────────────┘
           │                  │
┌──────────▼──────────────────▼──────────────────────────────────┐
│                   ⚡ 后端 (FastAPI :8000)                        │
│                                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ /upload   │ │ /query    │ │ /config   │ │ /conversations│  │
│  │ /documents│ │ /stream   │ │           │ │ /health       │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └───────────────┘  │
│        │             │             │                            │
│        ▼             ▼             │                            │
│  ┌─────────────────────────────────┼────────────────────────┐  │
│  │           🔗 RAGChain                                   │  │
│  │                                                          │  │
│  │  ① 检索                         ② 生成                   │  │
│  │  question → Embedding            System: 🎩 分析师助理     │  │
│  │     ↓                           Context: 【研报片段】     │  │
│  │  FAISS 相似度搜索                 Question: 用户问题       │  │
│  │     ↓                           → Ollama /api/generate   │  │
│  │  Top-3 片段 (含 metadata)         → 答案 + 来源引用        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 数据流程

```
上传 PDF 研报 → 文本解析 + 分块 → 向量化 → FAISS 索引
                                           ↓
用户自然语言提问 → 向量检索 Top-3 → Prompt 组装 → LLM 生成 → 带来源引用回答
```

## 🛠️ 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| **前端** | React + Ant Design + Vite | 组件库成熟，Vite 代理解决跨域 |
| **后端** | FastAPI | 异步高性能，自动 OpenAPI 文档 |
| **RAG 编排** | LangChain | PyPDFLoader / FAISS / TextSplitter 组件齐全 |
| **向量模型** | BGE-large-zh (324M) | 中文检索 MTEB 榜首，本地运行 |
| **向量库** | FAISS (CPU) | Meta 开源，无外部依赖，文件持久化 |
| **LLM** | Ollama + Qwen2.5 | 完全本地、免费、中文能力好 |
| **存储** | SQLite + JSON | 零配置，适合单机本地部署 |
| **测试** | pytest + FastAPI TestClient | 21 条测试，100% 通过 |

## 🚀 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+
- [Ollama](https://ollama.com/) 已安装并启动

```bash
# 拉取模型
ollama pull quentinz/bge-large-zh-v1.5:latest
ollama pull qwen2.5:0.5b
```

### 后端启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
# FastAPI 运行在 http://localhost:8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
# Vite 运行在 http://localhost:5173
```

## 📁 项目结构

```
rag-project/
├── backend/                          # FastAPI Python 后端
│   ├── main.py                       # 🚀 API 入口：10 个 REST 路由 + SSE 流式
│   ├── config.py                     # ⚙️ 全局配置
│   ├── document_loader.py            # 📄 PDF 解析 + 分块
│   ├── vector_store.py               # 📇 向量化 + FAISS 索引
│   ├── rag_chain.py                  # 🔗 RAG 核心链路
│   ├── database.py                   # 🗄️ SQLite 数据库
│   ├── models.py                     # 📊 ORM + Pydantic 模型
│   ├── requirements.txt              # 📦 Python 依赖
│   └── tests/                        # 🧪 pytest 测试 (21 条)
├── frontend/                         # 🖥️ React + Vite 前端
│   ├── src/
│   │   ├── App.jsx                   # 💬 主组件（问答 + 上传 + 调优）
│   │   └── main.jsx                  # 🚀 React 入口
│   ├── package.json
│   └── vite.config.js                # 🔀 Vite 代理配置
├── data/
│   ├── reports/                      # 📊 上传的券商研报 PDF
│   └── faiss_index/                  # 📇 FAISS 向量索引
├── docs/                             # 📚 项目文档
│   ├── architecture.md               # 系统架构图
│   ├── file-tree.md                  # 文件结构树
│   └── presentation.md               # 项目讲解（流程 + 踩坑记录）
└── specs/                            # 📋 设计规格
```

## ✨ 核心功能

- **📄 研报上传** — 支持 PDF 拖拽上传，自动解析、分块、向量化
- **💬 智能问答** — 自然语言提问，AI 检索相关段落并生成专业回答
- **🎩 分析师风格** — 内置券商分析师角色 Prompt，回答专业且有据可查
- **📌 来源追溯** — 每个回答附带来源引用（研报名称 + 页码），支持高亮定位
- **⚡ SSE 流式输出** — 打字机效果实时展示生成过程
- **⚙️ 调优实验面板** — 可视化调节 chunk_size / 相似度阈值，记录对比实验

## 📊 项目数据

| 指标 | 值 |
|---|---|
| 后端代码 | 6 个模块，~550 行 |
| 前端代码 | 1 个主组件，~350 行 |
| API 端点 | 10 个 |
| 测试用例 | 21 条，100% 通过 |
| 检索速度 | < 2s（embedding + FAISS + LLM 生成） |

## 📝 踩坑记录

| 问题 | 解决方案 |
|---|---|
| Windows 防火墙拦截 Ollama 子进程 | 改用 `httpx` 直连 `POST /api/embed` |
| 模型名不匹配 404 | `ollama list` 查看实际模型名 |
| `OLLAMA_HOST` 缺少协议头 | config.py 自动补全 `http://` |
| Qwen 0.5B 指令跟随弱 | 极简 Prompt + 降低相似度阈值 |
| Git `.gitignore` 编码问题 | 使用 UTF-8 编码，不用 Windows 记事本 |
| FastAPI `Depends` 注入时机 | 用 `Depends(get_db)` 替代直接调用 |

---

*Built with FastAPI + LangChain + FAISS + Ollama + React*
