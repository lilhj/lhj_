# 券商研报 RAG 问答系统 — 项目讲解

## 一、项目流程

```
上传 PDF 研报 → 文本解析 + 分块 → 向量化 → FAISS 索引
                                           ↓
用户自然语言提问 → 向量检索 Top-3 → Prompt 组装 → LLM 生成 → 带来源引用回答
```

| 步骤 | 做什么 | 产出 |
|---|---|---|
| 1 | 上传 3-5 份券商 PDF 研报 | 原始文件存入 `data/reports/` |
| 2 | PyMuPDF 逐页提取文本 + 页码 | 每页带 `page_number` 元数据 |
| 3 | RecursiveCharacterTextSplitter 语义分块 | chunk_size=400, overlap=50 |
| 4 | BGE-large-zh 模型转向量 (1024 维) | FAISS 本地索引持久化 |
| 5 | 用户输入问题 → 同模型转向量 → FAISS 相似度搜索 | Top-3 最相关片段 |
| 6 | 组装 Prompt（🎩 分析师身份 + 上下文 + 问题） | 发给 Ollama 生成 |
| 7 | 返回答案 + 来源标注（研报名 + 页码） | 前端展示 + 引用高亮 |

## 二、技术栈

| 层 | 技术 | 为什么选它 |
|---|---|---|
| **前端** | React + Ant Design + Vite | 组件库成熟，Layout/Sider/Collapse 开箱即用；Vite 代理解决跨域 |
| **后端** | FastAPI | 异步高性能，自动 OpenAPI 文档，原生文件上传支持 |
| **RAG 编排** | LangChain | 社区最大，PyPDFLoader/FAISS/TextSplitter 组件齐全 |
| **向量模型** | BGE-large-zh (324M) | 中文检索 MTEB 榜首，本地运行不传数据外网 |
| **向量库** | FAISS (CPU) | Meta 开源，无外部依赖，文件持久化即插即用 |
| **LLM** | Ollama + Qwen2.5 (0.5B) | 完全本地、免费、低配可跑；Qwen 中文能力好 |
| **存储** | SQLite + JSON | 零配置，适合单机本地部署 |
| **测试** | pytest + FastAPI TestClient | 无需启动服务即可测试全部 API |

## 三、选型原因

| 决策 | 理由 |
|---|---|
| **本地全栈 vs 云端 API** | 券商研报有版权/合规约束，数据不能出公司，必须本地 |
| **Ollama vs Claude API** | 免费、无网络依赖、数据不出本机；Qwen2.5 中文能力满足教学需求 |
| **FAISS vs Chroma/Milvus** | 零部署，`pip install` 即用；大厂的 Chroma/Milvus 需 Docker |
| **LangChain vs LlamaIndex** | LangChain 社区更大，中文教程多；PyPDFLoader + FAISS 组合成熟 |
| **FastAPI vs Flask** | FastAPI 原生 async，RAG 管道 IO 密集，异步收益明显 |
| **httpx 直连 vs Ollama Python 库** | 见下文踩坑记录 |

## 四、踩坑记录

### 坑 1: Windows 防火墙拦截 Ollama 子进程

**现象**: 调用 `ollama.embed()` 时连接超时，没有任何响应。

**原因**: Ollama Python 库内部 `subprocess.Popen` 启动子进程，Windows 防火墙弹出拦截
对话框——但在无 GUI 环境或被用户忽略时，子进程静默卡死。

**解决**: 放弃 Ollama Python 库，用 `httpx` 直连 `POST /api/embed`。代码更简洁，
请求完全可控，不经过子进程。

```python
# ❌ Ollama 库（Windows 上卡死）
import ollama
ollama.embed(model="bge-large-zh", input=texts)

# ✅ httpx 直连
resp = httpx.post("http://localhost:11434/api/embed",
                   json={"model": "bge-large-zh", "input": texts})
```

### 坑 2: 模型名不匹配

**现象**: `/api/embed` 返回 404 "model not found"。

**原因**: `ollama pull bge-large-zh-v1.5` 拉下来的实际名称是
`quentinz/bge-large-zh-v1.5:latest`（Ollama 自动加了发布者前缀）。

**解决**: 先 `ollama list` 查看实际模型名，config 默认值改成完整名。

### 坑 3: OLLAMA_HOST 缺少 http:// 前缀

**现象**: `httpx.ConnectError: missing protocol`。

**原因**: 环境变量 `OLLAMA_HOST=127.0.0.1:11434` 没带协议头，httpx 拒绝连接。

**解决**: config.py 里加一行自动补全：
```python
if not OLLAMA_HOST.startswith(("http://", "https://")):
    OLLAMA_HOST = f"http://{OLLAMA_HOST}"
```

### 坑 4: Qwen 0.5B 指令跟随弱

**现象**: 同样的 Prompt，有时回答很好，有时反复输出 "根据已有研报，未找到相关信息"。

**原因**: 0.5B 参数模型严格遵循 Prompt 指令的能力不稳定。

**应对**: ① 使用极简 Prompt 模板（67 字符）减少歧义；② 相似度阈值放低到 0.35 ；
③ 如教学需要更好效果，建议换 `qwen2:7b`；④ 这是教学中有价值的对比素材。

### 坑 5: Git .gitignore 编码问题

**现象**: `.gitignore` 写了 `.venv/` 但 `git add -A` 仍然提交了整个虚拟环境。

**原因**: 文件编码是 UTF-16 LE（Windows 记事本默认），Git 只识别 UTF-8 的 gitignore。

**解决**: 用编辑器重写 `.gitignore`，确保 UTF-8 编码，添加 `__pycache__/`、`*.db` 等规则。

### 坑 6: FastAPI 依赖注入的求值时机

**现象**: `def upload(file, db: Session = next(get_db()))` 在导入模块时立即执行
`next(get_db())`，导致 FastAPI 报 "Invalid args for response field"。

**解决**: 改用 FastAPI 的 `Depends`：
```python
# ❌ 模块导入时求值
def upload(db: Session = next(get_db())):

# ✅ FastAPI 请求时才注入
def upload(db: Session = Depends(get_db)):
```

## 五、项目数据

| 指标 | 值 |
|---|---|
| 后端代码 | 6 个模块，~550 行 |
| 前端代码 | 1 个组件 (App.jsx)，~350 行 |
| API 端点 | 10 个 |
| 测试 | 21 条，100% 通过 |
| 支持研报 | 3-5 份，跨文档检索 |
| 检索速度 | < 2s（含 embedding + FAISS + LLM 生成） |
