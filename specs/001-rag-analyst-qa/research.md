# Research: 券商研报 RAG 智能问答系统

> Phase 0 — 技术调研与决策记录 | Date: 2026-07-23

## 1. RAG 编排框架

**Decision**: LlamaIndex

**Rationale**:
- 对文档管理和来源引用（citation）有原生支持，`CitationQueryEngine` 开箱即用
- 概念模型清晰（Document → Node → VectorStoreIndex），适合多文档场景
- 每个组件（Loader/Splitter/Embedding/Retriever）可独立替换，满足 Constitution 原则 II
- 比 LangChain 更轻量，API 更直观，符合原则 V (简洁优先)

**Alternatives considered**:
- LangChain: 社区更大但抽象层过厚，框架锁定风险高
- 完全自建: 灵活度最高但模板代码多，收益不足以抵消开发成本

## 2. PDF 文本提取

**Decision**: PyMuPDF (fitz)

**Rationale**:
- 速度优于 pdfplumber（C 实现 vs 纯 Python）
- 原生页码感知，直接返回 `(page_num, text)` 对
- LlamaIndex `SimpleDirectoryReader` 默认支持 PyMuPDF
- 内存占用低，适合 100+ 页研报

**Alternatives considered**:
- pdfplumber: 提取质量好但速度慢 3-5x
- pdfminer.six: 功能完备但 API 繁琐

## 3. 文本分块策略

**Decision**: LlamaIndex `SentenceSplitter`, chunk_size=512, chunk_overlap=50

**Rationale**:
- 中文研报段落较长，512 tokens ≈ 300-400 汉字，保持语义完整性
- 50-token overlap 确保跨 chunk 边界的信息不丢失
- 预留 v1.1 参数调节（200/400/600/800）用于对比实验

**Alternatives considered**:
- `TokenTextSplitter`: 按 token 硬切，中文断句不准
- 固定字符数切分: 忽略语义边界

## 4. 嵌入模型

**Decision**: BGE-large-zh (BAAI/bge-large-zh-v1.5)

**Rationale**:
- 中文语义检索领域 MTEB 基准最优之一
- 1024 维向量，FAISS 索引体积可控
- 通过 `sentence-transformers` + `HuggingFaceEmbedding` 加载，本地运行无需 API 调用
- 满足 Constitution 原则 I (数据不离开本地)

**Alternatives considered**:
- text2vec-large-chinese: 性能接近，BGE 在金融文本场景略优
- OpenAI text-embedding-3: 需要上传文本 → 违反原则 I
- m3e-base: 维度更低 (768) 但检索精度略逊

## 5. 向量存储

**Decision**: FAISS (faiss-cpu) via `FaissVectorStore`

**Rationale**:
- Meta 维护，成熟稳定，CPU 版本安装简单
- 支持 L2/IP 距离度量，IndexFlatIP (内积) 模式适合 `sentence-transformers` 归一化向量
- 文件持久化到 `data/faiss_index/`，重启 < 10s 加载
- 无需独立服务进程，满足原则 V

**Alternatives considered**:
- Chroma: 嵌入式向量库，Python 原生，但索引格式与 FAISS 不通用
- Qdrant/Milvus: 需要 Docker/独立服务 → 违反原则 V

## 6. LLM 选择

**Decision**: Claude API (Anthropic), 模型默认 claude-sonnet-5

**Rationale**:
- 中文能力业界领先，长篇回答流畅自然
- 200K 上下文窗口 → 可容纳更多检索片段
- 原生支持 System Prompt → 注入 🎩 分析师助理身份
- Constitution 指定使用 Claude API

## 7. 来源引用实现

**Decision**: LlamaIndex `CitationQueryEngine` + 自定义元数据注入

**Rationale**:
- 分块时在 `Document.metadata` 中注入 `{doc_name, page_num, chunk_id}`
- `CitationQueryEngine` 检索时自动返回来源 `NodeWithScore`
- 生成 prompt 中格式化来源引用要求，Claude 按规范输出
- 满足 Constitution 原则 VI (来源引用强制规范)

## 8. API 框架

**Decision**: FastAPI

**Rationale**:
- Python 生态性能最优的异步 Web 框架
- 自动 OpenAPI 文档生成 — 前端和 CLI 开发可以参考
- 原生支持文件上传 (`UploadFile`) 和 JSON 请求
- 类型安全 (Pydantic models)

**Alternatives considered**:
- Flask: 缺少原生 async 支持，不适合 IO 密集型 RAG 管道
- Streamlit: 无法前后端分离

## 9. 前端技术

**Decision**: React + Vite (MVP 可降级为纯 HTML+JS)

**Rationale**:
- 组件化适配双栏布局 (FileUploader / ChatArea / SourceCard)
- Vite 构建快，开发体验好
- 在 plan 阶段标注为 "React 优先"，`/speckit-tasks` 阶段可根据开发者偏好调整

## 10. 并发与部署

**Decision**: 单进程 uvicorn，MVP 不引入 Gunicorn

**Rationale**:
- MVP 为单用户本地部署，无需多 worker
- PDF 索引为 CPU 密集型操作 → 放在后台线程执行，不阻塞 API 响应
- 索引写入操作天然串行（FAISS 不支持并发写），符合当前场景
