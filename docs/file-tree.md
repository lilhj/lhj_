# 项目文件结构树

```
rag-project/                              # 📦 券商研报 RAG 问答系统
│
├── .gitignore                            # 🔧 Git 忽略规则 (venv/node_modules/__pycache__/*.db)
│
├── .speckit/                             # 📋 Speckit 工作流快照
│   ├── constitution.md                   #   项目宪法：8 条核心原则 + 技术约束
│   ├── spec.md                           #   功能规格：4 条用户故事 + 15 条功能需求
│   ├── plan.md                           #   实施计划：架构设计 + Constitution Check
│   └── tasks.md                          #   任务清单：49 个任务，7 个阶段
│
├── backend/                              # ⚡ 后端 — FastAPI Python 服务
│   ├── main.py                           #   🚀 FastAPI 入口：10 个 REST 路由 + CORS + SSE 流式
│   ├── config.py                         #   ⚙️ 全局配置：8 个环境变量 (OLLAMA_HOST/LLM_MODEL...)
│   ├── requirements.txt                  #   📦 Python 依赖清单
│   ├── document_loader.py                #   📄 PDF 加载：PyPDFLoader 解析 + RecursiveCharacterTextSplitter 分块
│   ├── vector_store.py                   #   📇 向量存储：httpx→Ollama /api/embed + FAISS 索引持久化
│   ├── rag_chain.py                      #   🔗 RAG 核心链：检索 → Prompt 组装 → Ollama 生成 → 来源提取
│   ├── database.py                       #   🗄️ SQLite 数据库：SQLAlchemy 引擎 + Session 管理
│   ├── models.py                         #   📊 数据模型：ORM (Document/Conversation/Message) + Pydantic Schema
│   ├── rag_system.db                     #   💾 运行时数据库文件 (SQLite)
│   │
│   ├── src/                              #   📁 管道模块目录 (预留给后续扩展)
│   │   ├── ingestion/                    #     PDF 加载模块占位
│   │   ├── chunking/                     #     文本分块模块占位
│   │   ├── embedding/                    #     向量化模块占位
│   │   ├── indexing/                     #     索引模块占位
│   │   ├── retrieval/                    #     检索模块占位
│   │   ├── generation/                   #     生成模块占位
│   │   ├── api/                          #     REST 路由模块占位
│   │   └── cli/                          #     CLI 命令占位 (v1.1)
│   │
│   └── tests/                            #   🧪 测试
│       ├── __init__.py                   #     测试包初始化
│       ├── test_document_loader.py       #     测试 PDF 加载 + 分块 (6 条)
│       ├── test_rag_chain.py             #     测试检索 + 生成 (7 条)
│       └── test_api.py                   #     测试 FastAPI 接口 (8 条)
│
├── frontend/                             # 🖥️ 前端 — React + Ant Design + Vite
│   ├── index.html                        #   🌐 HTML 入口
│   ├── package.json                      #   📦 Node 依赖 (antd/react/vite/axios)
│   ├── vite.config.js                    #   🔀 Vite 配置：代理 6 个路由到 :8000 后端
│   ├── eslint.config.js                  #   ✨ ESLint 代码规范
│   └── src/
│       ├── main.jsx                      #   🚀 React 入口：挂载 App 到 #root
│       ├── App.jsx                       #   💬 主组件：问答界面 + 上传 + 调优面板 (~350 行)
│       ├── App.css                       #   🎨 App 样式占位
│       ├── index.css                     #   🎨 全局样式重置
│       └── assets/                       #   🖼️ 静态资源 (logo/icon)
│
├── data/                                 # 📊 数据目录
│   ├── reports/                          #   📄 原始 PDF 研报 (4 份宁德时代研报)
│   └── faiss_index/                      #   📇 FAISS 向量索引持久化文件
│       ├── index.faiss                   #     向量二进制文件
│       └── index.pkl                     #     文档元数据映射
│
├── docs/                                 # 📚 项目文档
│   ├── architecture.md                   #   🏗️ ASCII 架构图
│   ├── brainstorm.md                     #   💡 头脑风暴要点
│   ├── presentation.md                   #   🎤 项目讲解 (流程+技术栈+踩坑)
│   ├── file-tree.md                      #   🌲 本文件
│   └── superpowers/specs/
│       └── 2026-07-23-rag-analyst-qa-design.md  # 📐 完整设计规格
│
├── specs/                                # 📋 Speckit 规格目录
│   └── 001-rag-analyst-qa/               #   001 号功能：RAG 分析师问答
│       ├── spec.md                       #     功能规格说明书
│       ├── plan.md                       #     技术实施计划
│       ├── tasks.md                      #     任务拆解 (49 tasks)
│       ├── research.md                   #     技术调研：10 项决策记录
│       ├── data-model.md                 #     数据模型：4 实体 + ER 图
│       ├── quickstart.md                 #     启动验证指南
│       ├── contracts/                    #     API 契约
│       │   ├── upload.md                 #       POST /upload
│       │   ├── query.md                  #       POST /query
│       │   └── status.md                 #       GET /status
│       └── checklists/
│           └── requirements.md           #     规格质量清单 (16/16 pass)
│
├── .specify/                             # 🔧 Speckit 框架配置
├── .claude/                              # 🤖 Claude Code 技能/Agent 定义
└── .venv/                                # 🐍 Python 虚拟环境 (不提交)
```

## 核心文件速查

### 后端 (改代码从这里找)

| 文件 | 改什么 |
|---|---|
| `backend/config.py` | 调默认参数、切换模型 |
| `backend/document_loader.py` | 改分块策略、切分大小 |
| `backend/vector_store.py` | 换向量库、换嵌入模型 |
| `backend/rag_chain.py` | 改 Prompt 模板、调检索参数 |
| `backend/main.py` | 加新 API、改错误处理 |

### 前端

| 文件 | 改什么 |
|---|---|
| `frontend/src/App.jsx` | 所有 UI：布局、消息、上传、调优面板 |
| `frontend/vite.config.js` | 代理配置、端口 |

### 测试

| 文件 | 覆盖 |
|---|---|
| `tests/test_document_loader.py` | PDF 加载、分块、元数据 |
| `tests/test_rag_chain.py` | 检索、生成、来源、阈值 |
| `tests/test_api.py` | /health /query /config /documents |
