"""测试 FastAPI 接口。"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


class TestHealth:
    """/health 端点测试。"""

    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "role" in data
        assert len(data["role"]) > 0


class TestConfig:
    """/config 端点测试。"""

    def test_get_config(self):
        resp = client.get("/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "chunk_size" in data
        assert "similarity_threshold" in data
        assert "top_k" in data

    def test_update_threshold(self):
        resp = client.post("/config", json={"similarity_threshold": 0.50})
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        # 确认参数已更新
        resp2 = client.get("/config")
        assert resp2.json()["similarity_threshold"] == 0.50

        # 恢复默认值
        client.post("/config", json={"similarity_threshold": 0.35})

    def test_update_invalid_chunk_size(self):
        """无效 chunk_size 被 Pydantic 校验拦截。"""
        resp = client.post("/config", json={"chunk_size": 50})  # < 200
        assert resp.status_code == 422  # validation error


class TestQuery:
    """/query 端点测试。"""

    def test_query_returns_correct_format(self):
        """正常问答返回 answer + sources。"""
        resp = client.post("/query", json={"question": "宁德时代"})
        if resp.status_code == 503:
            pytest.skip("知识库未初始化")
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_query_empty_question(self):
        """空问题返回 422 验证错误。"""
        resp = client.post("/query", json={"question": ""})
        assert resp.status_code == 422

    def test_query_no_question_field(self):
        """缺少 question 字段返回 422。"""
        resp = client.post("/query", json={})
        assert resp.status_code == 422


class TestDocuments:
    """/documents 端点测试。"""

    def test_get_documents(self):
        resp = client.get("/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            d = data[0]
            assert "report_name" in d
            assert "chunks" in d
