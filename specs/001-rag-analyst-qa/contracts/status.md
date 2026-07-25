# API Contract: GET /status

## Request

```
GET /status
```

No parameters required.

## Success Response: 200 OK

```json
{
  "indexed_docs": 4,
  "total_chunks": 856,
  "embedding_model": "BGE-large-zh",
  "chunk_size": 512,
  "chunk_overlap": 50,
  "docs": [
    {
      "id": "uuid-1",
      "filename": "东吴证券-宁德时代-技术迭代引领行业-260322.pdf",
      "brokerage": "东吴证券",
      "pages": 32,
      "chunks": 210,
      "indexed_at": "2026-07-23T15:30:00"
    },
    {
      "id": "uuid-2",
      "filename": "东吴证券-宁德时代-龙头份额再提升-260416.pdf",
      "brokerage": "东吴证券",
      "pages": 28,
      "chunks": 195,
      "indexed_at": "2026-07-23T15:32:00"
    }
  ]
}
```

## Empty Knowledge Base: 200 OK

```json
{
  "indexed_docs": 0,
  "total_chunks": 0,
  "embedding_model": "BGE-large-zh",
  "chunk_size": 512,
  "chunk_overlap": 50,
  "docs": []
}
```

## Notes

- 此接口始终返回 200 — 知识库为空是正常状态，不是错误
- `docs` 数组按 `indexed_at` 降序排列
- 数据来源：`data/metadata.json` (元数据) + FAISS 索引文件统计
