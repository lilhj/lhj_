"""向量存储模块 — httpx 直连 Ollama + FAISS 持久化。

Windows 上 Ollama Python 库的 embed 子进程会被防火墙拦截，因此使用 httpx
直接调用 /api/embed 端点，避免子进程问题。
"""

from pathlib import Path
from typing import List, Optional

import httpx
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    LLM_MODEL,
    OLLAMA_HOST,
    SIMILARITY_THRESHOLD,
    TOP_K,
)

BATCH_SIZE = 20  # 每批嵌入 20 条文本


def _check_ollama() -> None:
    """检查 Ollama 服务是否在运行。"""
    try:
        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        resp.raise_for_status()
    except httpx.ConnectError:
        raise RuntimeError(
            f"无法连接到 Ollama ({OLLAMA_HOST})。请确认 Ollama 已启动。\n"
            "启动命令: ollama serve"
        )
    except httpx.HTTPError as e:
        raise RuntimeError(f"Ollama 服务异常: {e}")


def _check_model(model: str) -> None:
    """检查指定模型是否已 pull。"""
    try:
        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        # 模型名可能有 :latest 后缀
        model_base = model.split(":")[0]
        if not any(model_base in m or m.startswith(model) for m in models):
            print(f"警告: 未找到模型 '{model}'，将自动 pull...")
    except Exception:
        pass  # /api/tags 失败时跳过检查，到 embed 调用时自然会报错


class OllamaEmbeddings(Embeddings):
    """通过 httpx 直连 Ollama /api/embed 的 Embedding 实现。

    继承 LangChain BaseEmbeddings，可直接传入 FAISS.from_documents()。
    """

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        host: str = OLLAMA_HOST,
        batch_size: int = BATCH_SIZE,
    ):
        self.model = model
        self.host = host
        self.batch_size = batch_size
        self._embed_url = f"{host}/api/embed"

    def _call_embed(self, texts: List[str]) -> List[List[float]]:
        """调用 Ollama /api/embed，自动分批。"""
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    self._embed_url,
                    json={"model": self.model, "input": batch},
                )
                resp.raise_for_status()
                result = resp.json()
                all_embeddings.extend(result["embeddings"])
        return all_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表。"""
        return self._call_embed(texts)

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询。"""
        embeddings = self._call_embed([text])
        return embeddings[0]


def create_vector_store(
    docs: List[Document],
    embedding_model: Optional[str] = None,
) -> FAISS:
    """从文档列表创建 FAISS 向量存储。

    Args:
        docs: 分块后的 Document 列表（必须带有 metadata）
        embedding_model: 嵌入模型名，默认从 config 读取

    Returns:
        包含所有文档向量的 FAISS vector store
    """
    _check_ollama()
    model = embedding_model or EMBEDDING_MODEL
    _check_model(model)

    embeddings = OllamaEmbeddings(model=model)
    vector_store = FAISS.from_documents(docs, embeddings)
    return vector_store


def save_local(vector_store: FAISS, path: str) -> None:
    """将 FAISS 索引持久化到磁盘。

    Args:
        vector_store: FAISS vector store 实例
        path: 保存目录路径（如 data/faiss_index/）
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    vector_store.save_local(path)


def load_local(
    path: str,
    embedding_model: Optional[str] = None,
) -> Optional[FAISS]:
    """从磁盘加载 FAISS 索引。

    Args:
        path: 索引目录路径
        embedding_model: 嵌入模型名，默认从 config 读取

    Returns:
        FAISS vector store，索引不存在时返回 None
    """
    index_file = Path(path) / "index.faiss"
    if not index_file.exists():
        return None

    model = embedding_model or EMBEDDING_MODEL
    embeddings = OllamaEmbeddings(model=model)
    vector_store = FAISS.load_local(
        path,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    return vector_store


def search(
    vector_store: FAISS,
    query: str,
    k: Optional[int] = None,
    threshold: Optional[float] = None,
) -> List[Document]:
    """相似度搜索，返回带 metadata 的 Document 列表。

    Args:
        vector_store: FAISS vector store 实例
        query: 查询文本
        k: 返回结果数，默认从 config 读取
        threshold: 相似度阈值，低于此分数的结果被过滤，默认从 config 读取

    Returns:
        匹配的 Document 列表（按分数降序），每个包含完整 metadata
    """
    k = k or TOP_K
    threshold = threshold or SIMILARITY_THRESHOLD

    docs_with_scores = vector_store.similarity_search_with_score(query, k=k)
    filtered = [
        doc for doc, score in docs_with_scores if score >= threshold
    ]
    return filtered
