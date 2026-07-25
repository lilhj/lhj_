"""测试 PDF 加载和分块。"""
import re
import sys
from pathlib import Path

import pytest

# 确保 backend/ 在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from document_loader import load_and_split_pdf, load_multiple_pdfs

REPORTS_DIR = Path(__file__).parent.parent.parent / "data" / "reports"


def _first_pdf():
    pdfs = sorted(REPORTS_DIR.glob("*.pdf"))
    if not pdfs:
        pytest.skip("data/reports/ 中没有 PDF 文件")
    return str(pdfs[0])


def test_load_single_pdf():
    """单文件加载：返回非空列表，分块数 > 0。"""
    docs = load_and_split_pdf(_first_pdf())
    assert len(docs) > 0, "分块数量不应为 0"


def test_metadata_contains_report_name():
    """每个分块的 metadata 必须包含 report_name。"""
    docs = load_and_split_pdf(_first_pdf())
    for doc in docs:
        assert "report_name" in doc.metadata, f"缺少 report_name: {doc.metadata}"
        assert len(doc.metadata["report_name"]) > 0, "report_name 不应为空"


def test_metadata_contains_page_number():
    """每个分块的 metadata 必须包含 page_number（1-based）。"""
    docs = load_and_split_pdf(_first_pdf())
    for doc in docs:
        assert "page_number" in doc.metadata, f"缺少 page_number: {doc.metadata}"
        page = doc.metadata["page_number"]
        assert isinstance(page, int), f"page_number 应为 int，实际: {type(page)}"
        assert page >= 1, f"page_number 应为 1-based，实际: {page}"


def test_page_number_range():
    """页码范围必须在合理范围内。"""
    docs = load_and_split_pdf(_first_pdf())
    pages = {d.metadata["page_number"] for d in docs}
    assert min(pages) >= 1
    assert max(pages) <= 100, f"最大页码 {max(pages)} 异常"


def test_chunk_count_reasonable():
    """分块数量在合理范围（不为 0，不超过几千）。"""
    docs = load_and_split_pdf(_first_pdf())
    assert 1 <= len(docs) <= 5000, f"分块数 {len(docs)} 异常"


def test_load_multiple_pdfs():
    """批量加载多份 PDF 返回合并结果。"""
    pdfs = [str(p) for p in sorted(REPORTS_DIR.glob("*.pdf"))[:2]]
    if len(pdfs) < 2:
        pytest.skip("需要至少 2 份 PDF")
    docs = load_multiple_pdfs(pdfs)
    assert len(docs) > 0

    # 应包含两份不同 report_name
    names = {d.metadata["report_name"] for d in docs}
    assert len(names) >= 2, f"应包含至少 2 份不同研报，实际: {names}"
