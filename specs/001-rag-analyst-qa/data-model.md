# Data Model: 券商研报 RAG 智能问答系统

> Phase 1 — 数据模型设计 | Date: 2026-07-23

## 1. Report（研报）

```text
Report {
  id: str               # 唯一标识 (UUID, 自动生成)
  filename: str         # 原始文件名 "东吴证券-宁德时代-龙头份额再提升-260416.pdf"
  brokerage: str        # 券商名称 (从文件名提取: "东吴证券")
  pages: int            # 总页数
  size_bytes: int       # 文件大小
  chunks_count: int     # 分块数量
  status: enum          # "indexing" | "indexed" | "error"
  error_message: str?   # 失败原因 (status="error" 时有值)
  indexed_at: datetime  # 索引完成时间
}
```

**State transitions**:
```
upload → "indexing" → "indexed"
                    → "error"
```

**Validation**:
- `filename` 必须以 `.pdf` 结尾 (不区分大小写)
- `pages` > 0
- 同名文件上传 → 覆盖旧 Record (MVP 行为)

## 2. Chunk（分块）

```text
Chunk {
  id: str                # 唯一标识
  report_id: str         # → Report.id
  page_num: int          # 所在页码
  chunk_index: int       # 在页面内的序号
  text: str              # 分块文本内容 (约 300-400 汉字)
  embedding: float[]     # 向量表示 (BGE-large-zh: 1024 维)
  metadata: {            # 来源元数据 (用于引源标注)
    doc_name: str        # 研报文件名
    brokerage: str       # 券商名称
    page: int            # 页码
  }
}
```

**关系**:
- `Report` 1:N `Chunk` (一份研报包含多个分块)
- `Chunk` 是检索的最小单元
- `Chunk.embedding` 存入 FAISS 索引

## 3. QueryRecord（问答记录）

```text
QueryRecord {
  id: str                # 唯一标识
  question: str          # 用户自然语言问题
  answer: str            # 生成的回答
  sources: [Source]      # 引用的来源列表
  context_used: int      # 实际使用的分块数
  created_at: datetime   # 提问时间
  latency_ms: int        # 端到端延迟 (毫秒)
}

Source {
  doc: str               # 研报文件名
  page: int              # 页码
  text: str              # 引用的原文片段
  score: float           # 相似度分数 (0-1)
}
```

**关系**:
- `QueryRecord.sources[].doc` → `Report.filename`
- 每次提问创建一条新记录 (MVP 不做持久化存储，仅内存)

## 4. KnowledgeBase（知识库配置）

```text
KnowledgeBase {
  indexed_docs: int              # 已索引研报数量
  total_chunks: int              # 总分块数
  embedding_model: str           # "BGE-large-zh"
  chunk_size: int                # 512 (默认, v1.1 可调)
  chunk_overlap: int             # 50
  docs: [DocInfo]                # 已索引文档列表
}

DocInfo {
  filename: str
  pages: int
  chunks: int
  indexed_at: datetime
}
```

**来源**: `GET /status` 的响应体，实时从 FAISS 索引 + 元数据文件计算。

## 5. Entity Relationship

```
Report ──1:N──→ Chunk ──N:1──→ QueryRecord
  │                               │
  │                               │
  └──────→ KnowledgeBase ←────────┘
              (聚合视图)
```

## 6. Storage Layout

```
data/
├── reports/
│   ├── 东吴证券-宁德时代-技术迭代引领行业-260322.pdf   # 原始文件
│   └── ...
├── faiss_index/
│   ├── index.faiss                                      # FAISS 向量索引
│   └── index.pkl                                        # 元数据映射 (id → Chunk)
└── metadata.json                                        # KnowledgeBase 配置 + docs 列表
```
