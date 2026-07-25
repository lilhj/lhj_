# API Contract: POST /upload

## Request

```
POST /upload
Content-Type: multipart/form-data

files: File[]           # PDF 文件数组，最多 5 个
```

## Success Response: 201 Created

```json
{
  "uploaded": [
    {
      "id": "uuid-string",
      "filename": "东吴证券-宁德时代-技术迭代引领行业-260322.pdf",
      "brokerage": "东吴证券",
      "pages": 32,
      "chunks": 210,
      "status": "indexed"
    }
  ],
  "errors": [
    {
      "file": "broken.pdf",
      "error": "文件已损坏，无法解析"
    }
  ]
}
```

## Error Responses

| Code | Body | Condition |
|---|---|---|
| 200 | `{"uploaded":[], "errors":[...]}` | 部分文件失败（有效文件正常索引） |
| 400 | `{"detail":"所有上传文件均无效，请检查文件格式和完整性"}` | 全部文件无效 |
| 400 | `{"detail":"单次最多上传 5 份文件，当前已索引 {n} 份，还可上传 {m} 份"}` | 超过 5 份上限 |
| 413 | `{"detail":"文件总大小超过 100MB 限制"}` | 总大小超限 |

## Error Detail Format (per file)

```json
{
  "file": "filename.docx",
  "error": "不支持的文件类型，仅接受 PDF"
}
```

Possible error messages:
- `"不支持的文件类型，仅接受 PDF"`
- `"文件已损坏，无法解析"`
- `"无可提取的文本内容，请提供文字型 PDF"`

## Notes

- 同名文件覆盖旧索引 (MVP 行为)
- 上传过程为异步索引：先返回 202 确认接收，后台建索引，通过 `GET /status` 查询完成状态
- `brokerage` 字段从文件名前缀自动提取
