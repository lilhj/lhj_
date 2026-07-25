"""券商研报 RAG 问答系统 — FastAPI 入口（13 路由）。"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import config as cfg
from config import SYSTEM_ROLE
from database import get_db, init_db
from document_loader import load_and_split_pdf, load_multiple_pdfs
from models import (
    ConfigRequest,
    ConfigResponse,
    ConversationCreate,
    ConversationItem,
    ConversationORM,
    DocumentItem,
    DocumentORM,
    MessageItem,
    MessageORM,
    QueryRequest,
    QueryResponse,
    SourceItem,
    UploadResponse,
)
from rag_chain import RAGChain
from vector_store import (
    OllamaEmbeddings,
    create_vector_store,
    load_local,
    save_local,
    search,
)

# ═══════════════════════════════════════════
# 全局状态
# ═══════════════════════════════════════════

UPLOAD_DIR = Path("../data/reports")
INDEX_DIR = Path("../data/faiss_index")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

rag_chain: Optional["RAGChain"] = None
_uploaded_pdf_paths: List[str] = []  # 已上传 PDF 路径（用于重建索引）


def _get_rag_chain() -> RAGChain:
    """获取全局 RAGChain 实例（延迟初始化）。"""
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain(str(INDEX_DIR), top_k=cfg.TOP_K,
                             similarity_threshold=cfg.SIMILARITY_THRESHOLD)
    return rag_chain


def _rebuild_index():
    """使用当前已上传的 PDF 重建索引。"""
    global rag_chain
    if not _uploaded_pdf_paths:
        return
    all_docs = load_multiple_pdfs(_uploaded_pdf_paths,
                                  chunk_size=cfg.CHUNK_SIZE,
                                  chunk_overlap=cfg.CHUNK_OVERLAP)
    vs = create_vector_store(all_docs, embedding_model=cfg.EMBEDDING_MODEL)
    save_local(vs, str(INDEX_DIR))
    rag_chain = RAGChain(str(INDEX_DIR), top_k=cfg.TOP_K,
                         similarity_threshold=cfg.SIMILARITY_THRESHOLD)


# ═══════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════

app = FastAPI(
    title="券商研报 RAG 问答系统",
    description="基于 LangChain + Ollama + FAISS 的本地 RAG 问答系统",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    # 尝试加载已有索引
    global rag_chain
    try:
        rag_chain = RAGChain(str(INDEX_DIR), top_k=cfg.TOP_K,
                             similarity_threshold=cfg.SIMILARITY_THRESHOLD)
        print(f"知识库已加载: {len(rag_chain.vector_store.index_to_docstore_id)} 个向量")
    except Exception:
        print("知识库为空，等待上传研报")


# ═══════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "role": SYSTEM_ROLE}


# ═══════════════════════════════════════════
# 文档管理
# ═══════════════════════════════════════════

@app.post("/upload", response_model=UploadResponse)
def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传单份 PDF 研报，解析并加入向量库。"""
    try:
        # 校验文件类型
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "仅支持 PDF 文件")

        # 保存文件
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 解析 PDF
        docs = load_and_split_pdf(str(file_path))
        if not docs:
            raise HTTPException(400, "PDF 无可提取的文本内容")

        # 加入向量库
        try:
            vs = _get_rag_chain().vector_store
            embeddings = OllamaEmbeddings(model=cfg.EMBEDDING_MODEL)
            from langchain_community.vectorstores import FAISS
            if isinstance(vs, FAISS):
                new_vs = FAISS.from_documents(docs, embeddings)
                vs.merge_from(new_vs)
                save_local(vs, str(INDEX_DIR))
        except FileNotFoundError:
            create_vector_store(docs)
            save_local(create_vector_store(docs), str(INDEX_DIR))

        _uploaded_pdf_paths.append(str(file_path))

        # 记录到数据库
        report_name = docs[0].metadata.get("report_name", file.filename)
        doc_orm = DocumentORM(
            report_name=report_name,
            file_path=str(file_path),
            chunks=len(docs),
        )
        db.add(doc_orm)
        db.commit()

        return UploadResponse(filename=file.filename, chunks=len(docs))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"上传失败: {str(e)}")


@app.get("/documents", response_model=List[DocumentItem])
def list_documents(db: Session = Depends(get_db)):
    """列出已上传的研报列表。"""
    try:
        docs = db.query(DocumentORM).order_by(DocumentORM.uploaded_at.desc()).all()
        return [
            DocumentItem(
                id=d.id,
                report_name=d.report_name,
                chunks=d.chunks,
                uploaded_at=d.uploaded_at.strftime("%Y-%m-%d %H:%M") if d.uploaded_at else "",
            )
            for d in docs
        ]
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


# ═══════════════════════════════════════════
# 问答接口
# ═══════════════════════════════════════════

@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """标准问答。"""
    try:
        chain = _get_rag_chain()
        result = chain.query(req.question)
        sources = [
            SourceItem(report_name=s["report_name"], page_number=s["page_number"], snippet=s["snippet"])
            for s in result.get("sources", [])
        ]
        return QueryResponse(answer=result["answer"], sources=sources)
    except FileNotFoundError:
        raise HTTPException(503, "知识库尚未初始化，请先上传研报")
    except Exception as e:
        raise HTTPException(500, f"问答失败: {str(e)}")


@app.post("/query/stream")
def query_stream(req: QueryRequest):
    """SSE 流式问答。"""
    try:
        chain = _get_rag_chain()
    except FileNotFoundError:
        raise HTTPException(503, "知识库尚未初始化")

    # 检索
    docs = search(chain.vector_store, req.question, k=chain.top_k, threshold=chain.similarity_threshold)
    if not docs:
        return StreamingResponse(
            _sse_generator("根据已有研报，未找到相关信息。"),
            media_type="text/event-stream",
        )

    # 组装 prompt
    from rag_chain import _build_context, PROMPT_TEMPLATE
    context = _build_context(docs)
    prompt = PROMPT_TEMPLATE.format(role=SYSTEM_ROLE, context=context, question=req.question)

    # 流式调用 Ollama
    return StreamingResponse(
        _ollama_stream_generator(prompt),
        media_type="text/event-stream",
    )


async def _sse_generator(text: str) -> Generator[str, None, None]:
    """将固定文本转为 SSE 流。"""
    for char in text:
        yield f"data: {json.dumps({'chunk': char})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


async def _ollama_stream_generator(prompt: str) -> Generator[str, None, None]:
    """Ollama 流式生成 → SSE。"""
    import httpx
    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{cfg.OLLAMA_HOST}/api/generate",
                json={"model": cfg.LLM_MODEL, "prompt": prompt, "stream": True},
            ) as resp:
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                        except json.JSONDecodeError:
                            continue
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# ═══════════════════════════════════════════
# 调优实验
# ═══════════════════════════════════════════

@app.get("/config", response_model=ConfigResponse)
def get_config():
    """获取当前 RAG 参数。"""
    return ConfigResponse(
        chunk_size=cfg.CHUNK_SIZE,
        chunk_overlap=cfg.CHUNK_OVERLAP,
        top_k=cfg.TOP_K,
        similarity_threshold=cfg.SIMILARITY_THRESHOLD,
        embedding_model=cfg.EMBEDDING_MODEL,
        llm_model=cfg.LLM_MODEL,
    )


@app.post("/config")
def update_config(req: ConfigRequest):
    """更新 RAG 参数，如果 chunk_size 变化则重建索引。"""
    old_chunk = cfg.CHUNK_SIZE
    message_parts = []

    if req.chunk_size is not None and req.chunk_size != cfg.CHUNK_SIZE:
        cfg.CHUNK_SIZE = req.chunk_size
        message_parts.append(f"chunk_size 已更新为 {req.chunk_size}")
    if req.similarity_threshold is not None:
        cfg.SIMILARITY_THRESHOLD = req.similarity_threshold
        message_parts.append(f"similarity_threshold 已更新为 {req.similarity_threshold}")
    if req.top_k is not None:
        cfg.TOP_K = req.top_k
        message_parts.append(f"top_k 已更新为 {req.top_k}")

    # chunk_size 变化 → 重建索引
    if req.chunk_size is not None and req.chunk_size != old_chunk:
        message_parts.append("正在重建索引...")
        try:
            _rebuild_index()
            message_parts.append("索引重建完成")
        except Exception as e:
            raise HTTPException(500, f"索引重建失败: {str(e)}")
    else:
        # 更新运行中的 chain 参数
        try:
            chain = _get_rag_chain()
            chain.update_params(
                top_k=req.top_k,
                similarity_threshold=req.similarity_threshold,
            )
        except FileNotFoundError:
            pass

    return {
        "message": "；".join(message_parts) if message_parts else "参数无变化",
        "chunk_size": cfg.CHUNK_SIZE,
        "similarity_threshold": cfg.SIMILARITY_THRESHOLD,
        "top_k": cfg.TOP_K,
    }


# ═══════════════════════════════════════════
# 对话管理
# ═══════════════════════════════════════════

@app.post("/conversations", response_model=ConversationItem)
def create_conversation(req: ConversationCreate, db: Session = Depends(get_db)):
    """创建新对话。"""
    try:
        conv = ConversationORM(title=req.title)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return ConversationItem(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at.strftime("%Y-%m-%d %H:%M") if conv.created_at else "",
            message_count=0,
        )
    except Exception as e:
        raise HTTPException(500, f"创建对话失败: {str(e)}")


@app.get("/conversations", response_model=List[ConversationItem])
def list_conversations(db: Session = Depends(get_db)):
    """列出所有对话。"""
    try:
        convs = db.query(ConversationORM).order_by(ConversationORM.created_at.desc()).all()
        return [
            ConversationItem(
                id=c.id,
                title=c.title,
                created_at=c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
                message_count=len(c.messages),
            )
            for c in convs
        ]
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


@app.get("/conversations/{conv_id}/messages", response_model=List[MessageItem])
def get_messages(conv_id: int, db: Session = Depends(get_db)):
    """获取对话中的消息列表。"""
    try:
        messages = (
            db.query(MessageORM)
            .filter(MessageORM.conversation_id == conv_id)
            .order_by(MessageORM.id)
            .all()
        )
        result = []
        for m in messages:
            sources = None
            if m.sources:
                try:
                    raw = json.loads(m.sources)
                    sources = [SourceItem(**s) for s in raw]
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=sources,
                created_at=m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else "",
            ))
        return result
    except Exception as e:
        raise HTTPException(500, f"查询失败: {str(e)}")


# ═══════════════════════════════════════════
# 全局错误处理
# ═══════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误: {str(exc)}"})


# ═══════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
