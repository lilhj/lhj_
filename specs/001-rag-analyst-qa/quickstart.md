# Quickstart: 券商研报 RAG 智能问答系统

> 从零到首次问答的完整验证指南 | Date: 2026-07-23

## 前置条件

- Python 3.11+
- Node.js 18+
- Git
- Claude API Key ([获取地址](https://console.anthropic.com/))

## 1. 环境搭建

```bash
# 克隆并进入项目
git checkout master  # 或 feature 分支
cd rag-project

# 后端虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# 前端依赖
cd frontend
npm install
cd ..

# 配置 API Key
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 ANTHROPIC_API_KEY=sk-ant-...
```

## 2. 启动服务

```bash
# 终端 1: 启动后端 (端口 8000)
cd backend
python main.py

# 终端 2: 启动前端 (端口 5173)
cd frontend
npm run dev
```

## 3. 端到端验证

### 3.1 上传研报 (US1)

```bash
# CLI 方式
curl -X POST http://localhost:8000/upload \
  -F "files=@data/reports/【东吴证券】宁德时代-龙头份额再提升-260416.pdf" \
  -F "files=@data/reports/【国信证券】宁德时代-盈利能力表现稳健-260417.pdf"

# 预期响应: 201
# {"uploaded":[{"filename":"...","pages":28,"chunks":195,"status":"indexed"},...],"errors":[]}
```

### 3.2 检查知识库状态

```bash
curl http://localhost:8000/status

# 预期响应: 200
# {"indexed_docs":2,"total_chunks":...,"docs":[...]}
```

### 3.3 提问 (US2)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"宁德时代2025年产能规划是多少？"}'

# 预期响应: 200
# {"answer":"根据《东吴证券-宁德时代-龙头份额再提升》第3页...",
#  "sources":[{"doc":"...","page":3,"text":"...","score":0.87}],
#  "context_used":3}
```

### 3.4 边界条件验证

```bash
# 空知识库提问 → 503
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"测试"}'  # (在上传研报之前执行)

# 无相关性提问 → 200, sources=[]
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"苹果公司股价走势如何？"}'

# 非 PDF 上传 → 200, errors 数组有内容
curl -X POST http://localhost:8000/upload \
  -F "files=@test.txt"

# 重启恢复 → 重新启动后端后
curl http://localhost:8000/status
# 预期: indexed_docs > 0 (索引自动加载)
```

## 4. 运行测试

```bash
cd backend
pytest tests/ -v

# 预期: 5 个测试文件全部通过
# test_loader.py: 3 passed
# test_splitter.py: 2 passed
# test_embedder.py: 2 passed
# test_retriever.py: 3 passed
# test_api.py: 5 passed
```

## 5. 成功标准对照

| SC | 指标 | 目标 | 验证方式 |
|---|---|---|---|
| SC-001 | 首次上传 3 份研报 < 5min | < 300s | 计时三次上传操作 |
| SC-002 | 单份 30 页索引 < 60s | < 60s | 后端日志输出耗时 |
| SC-003 | 问答 < 30s | < 30s | `QueryRecord.latency_ms` |
| SC-004 | 90% 回答含准确来源 | ≥ 90% | 人工评审 10 个测试问题 |
| SC-005 | 无信息时 100% 拒答 | 100% | 20 个跨主题无关问题 |
| SC-006 | 重启恢复 < 10s | < 10s | 重启后端后计时 `GET /status` |
| SC-007 | 新手独立完成 | 通过 | 找一位分析师同事试操作 |
