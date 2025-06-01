import pytest
from fastapi.testclient import TestClient
from rag_service.main import app
from rag_service import weaviate_client, llm_client
from shared.models import SeverityLevel

client = TestClient(app)

@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Stub the Weaviate semantic_search
    def fake_search(query, limit=5):
        return [
            {"event_id": "e1", "timestamp": "2025-05-29T10:00:00Z", "camera_id": "cam1", "event_type": "detection"},
            {"event_id": "e2", "timestamp": "2025-05-29T10:05:00Z", "camera_id": "cam1", "event_type": "activity"},
        ]
    monkeypatch.setattr(weaviate_client, "semantic_search", fake_search)
    # Stub the LLM generate_alert
    def fake_generate(query, contexts):
        return {
            "alert_text": "Test alert based on contexts",
            "severity": "medium",
            "evidence_ids": ["e1", "e2"]
        }
    monkeypatch.setattr(llm_client, "generate_alert", fake_generate)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_analysis_endpoint_success():
    payload = {"query": "Test query"}
    resp = client.post("/analysis", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["alert_text"] == "Test alert based on contexts"
    assert body["severity"] == SeverityLevel.MEDIUM.value
    assert set(body["evidence_ids"]) == {"e1", "e2"}

def test_analysis_invalid_llm_output(monkeypatch):
    # LLM returns invalid JSON
    def bad_generate(query, contexts):
        raise ValueError("JSON parse error")
    monkeypatch.setattr(llm_client, "generate_alert", bad_generate)
    resp = client.post("/analysis", json={"query": "q"})
    assert resp.status_code == 500
    assert "Alert generation error" in resp.json()["detail"]