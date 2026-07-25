# API Contract: POST /query

## Request

```
POST /query
Content-Type: application/json

{
  "question": "宁德时代2025年产能规划是多少？",
  "top_k": 3                    # 可选，默认 3，范围 [1, 10]
}
```

## Validation

| Field | Type | Required | Constraints |
|---|---|---|---|
| `question` | string | Yes | 1-2000 chars, 不能纯空白 |
| `top_k` | int | No (default 3) | 1-10 |

## Success Response: 200 OK

```json
{
  "answer": "根据《东吴证券-宁德时代-龙头份额再提升-260416》第3页的分析，公司2025年规划产能达到800GWh，其中储能电池占比提升至30%...",
  "sources": [
    {
      "doc": "东吴证券-宁德时代-龙头份额再提升-260416.pdf",
      "page": 3,
      "text": "公司2025年规划产能达800GWh，储能电池占比提升至30%",
      "score": 0.87
    },
    {
      "doc": "国信证券-宁德时代-盈利能力表现稳健-260417.pdf",
      "page": 5,
      "text": "产能扩张节奏保持稳定，2025年全球市占率预计维持在35%以上",
      "score": 0.82
    }
  ],
  "context_used": 3
}
```

## 知识库无结果: 200 OK

```json
{
  "answer": "当前知识库中未找到与该问题相关的信息。建议尝试：1) 换用不同关键词 2) 扩大问题范围 3) 确认相关研报已上传。",
  "sources": [],
  "context_used": 0
}
```

## Error Responses

| Code | Body | Condition |
|---|---|---|
| 400 | `{"detail":"问题不能为空"}` | `question` 为空
| 400 | `{"detail":"问题长度超过 2000 字符限制"}` | `question` > 2000 chars
| 503 | `{"detail":"知识库尚未初始化，请先上传研报"}` | 无已索引文档
| 502 | `{"detail":"LLM 服务响应超时，请稍后重试"}` | Claude API > 30s
| 502 | `{"detail":"LLM 服务配置错误，请联系管理员"}` | API key 无效/余额不足（通用提示，不泄露细节）
