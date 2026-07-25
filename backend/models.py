"""SQLAlchemy ORM 模型 + Pydantic 请求/响应结构体。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base

# ═══════════════════════════════════════════
# SQLAlchemy ORM 模型
# ═══════════════════════════════════════════


class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    chunks = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class ConversationORM(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("MessageORM", back_populates="conversation", order_by="MessageORM.id")


class MessageORM(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(16), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("ConversationORM", back_populates="messages")


# ═══════════════════════════════════════════
# Pydantic 请求/响应结构体
# ═══════════════════════════════════════════


class SourceItem(BaseModel):
    report_name: str
    page_number: int
    snippet: str


# ── 文档管理 ──
class UploadResponse(BaseModel):
    filename: str
    chunks: int
    message: str = "研报已成功加入知识库"


class DocumentItem(BaseModel):
    id: int
    report_name: str
    chunks: int
    uploaded_at: str


# ── 问答 ──
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = []


# ── 配置调优 ──
class ConfigRequest(BaseModel):
    chunk_size: Optional[int] = Field(None, ge=200, le=800)
    similarity_threshold: Optional[float] = Field(None, ge=0.1, le=0.9)
    top_k: Optional[int] = Field(None, ge=1, le=10)


class ConfigResponse(BaseModel):
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float
    embedding_model: str
    llm_model: str


# ── 对话管理 ──
class ConversationCreate(BaseModel):
    title: str = "新对话"


class ConversationItem(BaseModel):
    id: int
    title: str
    created_at: str
    message_count: int


class MessageItem(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[List[SourceItem]] = None
    created_at: str
