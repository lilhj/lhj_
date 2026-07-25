"""RAG 核心链 — 检索 + 生成。

使用极简 Prompt 模板适配 Qwen 0.5B 等小模型的指令跟随能力。
LLM 调用使用 httpx 直连 Ollama /api/generate，避免 Windows 防火墙问题。
"""

from typing import List, Optional

import httpx
from langchain_core.documents import Document

from config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    OLLAMA_HOST,
    SIMILARITY_THRESHOLD,
    SYSTEM_ROLE,
    TOP_K,
)
from vector_store import OllamaEmbeddings, load_local, search

# ── Prompt 模板 ────────────────────────────────────────────
PROMPT_TEMPLATE = """你是{role}。根据以下研报内容回答问题。如果资料中没有答案，就说'根据已有研报，未找到相关信息'。
参考研报：
{context}
问题：{question}
分析师助理回答："""


def _build_context(docs: List[Document]) -> str:
    """将检索到的文档组装为 Prompt 上下文。

    格式：【券商名《研报名》第X页】: 原文段落内容...
    """
    parts = []
    for doc in docs:
        meta = doc.metadata
        # 元数据中 report_name 已包含券商信息，提取纯研报名用于显示
        report = meta.get("report_name", "未知研报")
        page = meta.get("page_number", "?")
        text = doc.page_content.strip()
        parts.append(f"【{report}第{page}页】: {text}")
    return "\n\n".join(parts)


def _extract_sources(docs: List[Document]) -> List[dict]:
    """从检索到的 Document 列表提取来源信息。"""
    return [
        {
            "report_name": doc.metadata.get("report_name", "未知研报"),
            "page_number": doc.metadata.get("page_number", 0),
            "snippet": doc.page_content[:100].replace("\n", " "),
        }
        for doc in docs
    ]


class RAGChain:
    """RAG 问答链。

    封装检索 + 生成流程，支持参数调优实验。

    Usage:
        chain = RAGChain("data/faiss_index")
        result = chain.query("宁德时代2025年产能规划？")
        print(result["answer"])
        for s in result["sources"]:
            print(f"  - {s['report_name']} p.{s['page_number']}")
    """

    def __init__(
        self,
        index_path: str = "data/faiss_index",
        top_k: int = TOP_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        embedding_model: str = EMBEDDING_MODEL,
        llm_model: str = LLM_MODEL,
        system_role: str = SYSTEM_ROLE,
        ollama_host: str = OLLAMA_HOST,
    ):
        self.index_path = index_path
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.system_role = system_role
        self.ollama_host = ollama_host
        self._generate_url = f"{ollama_host}/api/generate"

        # 加载向量存储
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vector_store = load_local(index_path, embedding_model)
        if self.vector_store is None:
            raise FileNotFoundError(
                f"未找到 FAISS 索引 ({index_path}/index.faiss)。请先上传研报创建知识库。"
            )

    def query(self, question: str) -> dict:
        """执行 RAG 问答。

        Args:
            question: 用户的自然语言问题

        Returns:
            {"answer": str, "sources": [{"report_name", "page_number", "snippet"}]}
        """
        # 1. 检索
        docs = search(
            self.vector_store,
            question,
            k=self.top_k,
            threshold=self.similarity_threshold,
        )

        if not docs:
            return {
                "answer": "根据已有研报，未找到相关信息。",
                "sources": [],
            }

        # 2. 组装 Prompt
        context = _build_context(docs)
        prompt = PROMPT_TEMPLATE.format(
            role=self.system_role,
            context=context,
            question=question,
        )

        # 3. 调用 LLM 生成
        answer = self._call_llm(prompt)

        # 4. 组装返回结果
        sources = _extract_sources(docs)
        return {"answer": answer, "sources": sources}

    def _call_llm(self, prompt: str) -> str:
        """通过 httpx 直连 Ollama /api/generate 调用 LLM。"""
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                self._generate_url,
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()

    def update_params(
        self,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ):
        """动态更新检索参数（用于 v1.1 调优实验）。"""
        if top_k is not None:
            self.top_k = top_k
        if similarity_threshold is not None:
            self.similarity_threshold = similarity_threshold
