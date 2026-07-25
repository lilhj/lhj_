"""PDF 研报加载与分块模块 — 保留页码元数据用于来源追溯。"""

from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP


def _enrich_metadata(doc: Document, file_path: str) -> Document:
    """为每页 Document 补充来源元数据。"""
    report_name = Path(file_path).stem  # 不含路径和扩展名
    page_number = doc.metadata.get("page", 0) + 1  # PyPDFLoader 是 0-based，转为 1-based

    doc.metadata.update({
        "report_name": report_name,
        "page_number": page_number,
        "source": str(Path(file_path).resolve()),
    })
    return doc


def load_and_split_pdf(
    file_path: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """加载单个 PDF 并分块，保留页码元数据。

    Args:
        file_path: PDF 文件路径
        chunk_size: 分块大小，默认从 config 读取
        chunk_overlap: 分块重叠量，默认从 config 读取

    Returns:
        分块后的 Document 列表，每个 metadata 包含:
        {"report_name", "page_number", "source"}
    """
    chunk_size = chunk_size or CHUNK_SIZE
    chunk_overlap = chunk_overlap or CHUNK_OVERLAP

    # 逐页加载 PDF
    loader = PyPDFLoader(file_path)
    raw_docs = loader.load()

    # 为每页补充来源元数据
    enriched_docs = [_enrich_metadata(doc, file_path) for doc in raw_docs]

    # 分块，保留原始 metadata
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    )
    split_docs = splitter.split_documents(enriched_docs)

    return split_docs


def load_multiple_pdfs(
    file_paths: List[str],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """批量加载多份 PDF 研报并分块。

    Args:
        file_paths: PDF 文件路径列表
        chunk_size: 分块大小，默认从 config 读取
        chunk_overlap: 分块重叠量，默认从 config 读取

    Returns:
        所有 PDF 分块后的 Document 列表，按加载顺序拼接
    """
    all_docs: List[Document] = []
    for path in file_paths:
        docs = load_and_split_pdf(path, chunk_size, chunk_overlap)
        all_docs.extend(docs)
    return all_docs
