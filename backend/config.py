"""应用配置 — 所有配置从环境变量读取，提供合理默认值。"""

import os


OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# 确保 OLLAMA_HOST 包含协议前缀（环境变量可能只给了 host:port）
if not OLLAMA_HOST.startswith(("http://", "https://")):
    OLLAMA_HOST = f"http://{OLLAMA_HOST}"
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "quentinz/bge-large-zh-v1.5:latest")
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:0.5b")
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K: int = int(os.getenv("TOP_K", "3"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
SYSTEM_ROLE: str = os.getenv("SYSTEM_ROLE", "某券商首席分析师助理")
