"""测试 RAG 检索和生成。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_chain import RAGChain, _build_context, _extract_sources
from vector_store import (
    OllamaEmbeddings,
    load_local,
    search,
)
from langchain_core.documents import Document

INDEX_DIR = Path(__file__).parent.parent.parent / "data" / "faiss_index"


@pytest.fixture(scope="module")
def vector_store():
    """加载已存在的 FAISS 索引。"""
    idx = load_local(str(INDEX_DIR))
    if idx is None:
        pytest.skip("FAISS 索引不存在，请先上传研报")
    return idx


@pytest.fixture(scope="module")
def rag_chain():
    """加载 RAGChain。"""
    try:
        return RAGChain(str(INDEX_DIR))
    except FileNotFoundError:
        pytest.skip("FAISS 索引不存在")


class TestRetrieval:
    """检索测试。"""

    def test_search_returns_correct_top_k(self, vector_store):
        """search 返回结果数量不超过 k。"""
        results = search(vector_store, "宁德时代产能", k=3)
        assert len(results) <= 3

    def test_search_results_have_metadata(self, vector_store):
        """检索结果的 metadata 包含 report_name 和 page_number。"""
        results = search(vector_store, "产能规划", k=3)
        if len(results) == 0:
            pytest.skip("无匹配结果")
        for doc in results:
            assert "report_name" in doc.metadata
            assert "page_number" in doc.metadata

    def test_threshold_filters_low_scores(self, vector_store):
        """高阈值应减少或清空结果。"""
        results_low = search(vector_store, "宁德时代", k=5, threshold=0.01)
        results_high = search(vector_store, "宁德时代", k=5, threshold=0.95)
        # 高阈值结果数不应超过低阈值
        assert len(results_high) <= len(results_low)


class TestSources:
    """来源提取测试。"""

    def test_extract_sources_format(self):
        """_extract_sources 返回正确的字典结构。"""
        docs = [
            Document(
                page_content="测试内容...",
                metadata={"report_name": "测试报告", "page_number": 3},
            )
        ]
        sources = _extract_sources(docs)
        assert len(sources) == 1
        assert sources[0]["report_name"] == "测试报告"
        assert sources[0]["page_number"] == 3
        assert "snippet" in sources[0]
        assert len(sources[0]["snippet"]) > 0

    def test_build_context_format(self):
        """_build_context 应包含 report_name 和页码。"""
        docs = [
            Document(
                page_content="产能规划分析...",
                metadata={"report_name": "测试研报", "page_number": 5},
            )
        ]
        ctx = _build_context(docs)
        assert "测试研报" in ctx
        assert "第5页" in ctx


class TestRAGChain:
    """RAGChain 集成测试。"""

    def test_query_returns_dict(self, rag_chain):
        """query 返回包含 answer + sources 的 dict。"""
        result = rag_chain.query("宁德时代")
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    def test_query_sources_have_required_fields(self, rag_chain):
        """返回的 sources 中每项包含 report_name 和 page_number。"""
        result = rag_chain.query("宁德时代产能")
        for s in result["sources"]:
            assert "report_name" in s
            assert "page_number" in s
