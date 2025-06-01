import pytest
from fastapi.testclient import TestClient
from prompt_service.main import app
import prompt_service.weaviate_client as wc
from prompt_service.clip_store import get_clip_url

client = TestClient(app)

@pytest.fixture(autouse=True)
def patch_weaviate(monkeypatch):
    def fake_search(query, limit=5):
        return [
            {"event_id": "e1", "timestamp": "2025-05-29T10:00:00Z", "camera_id": "cam1"},
            {"event_id": "e2", "timestamp": "2025-05-29T10:05:00Z", "camera_id": "cam2"},
        ]
    monkeypatch.setattr(wc, "semantic_search", fake_search)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_query_success():
    resp = client.post("/query", json={"query": "test", "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert "Here are the relevant events" in data["answer_text"]
    assert len(data["clip_links"]) == 2
    for link in data["clip_links"]:
        assert link.endswith(".mp4")

def test_query_default_limit():
    # default limit=5, but fake_search returns 2
    resp = client.post("/query", json={"query": "another test"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["clip_links"]) == 2