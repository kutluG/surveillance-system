import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

stub = types.ModuleType("stub")
sys.modules.setdefault("cv2", stub)
numpy_stub = types.ModuleType("numpy")
setattr(numpy_stub, "ndarray", object)
sys.modules.setdefault("numpy", numpy_stub)
pil_stub = types.ModuleType("PIL")
pil_image_stub = types.ModuleType("PIL.Image")
setattr(pil_stub, "Image", pil_image_stub)
sys.modules.setdefault("PIL", pil_stub)
sys.modules.setdefault("PIL.Image", pil_image_stub)
weaviate_stub = types.ModuleType("weaviate")
weaviate_stub.Client = lambda *a, **k: None
sys.modules.setdefault("weaviate", weaviate_stub)

openai_stub = types.ModuleType("openai")
openai_stub.AsyncOpenAI = lambda *a, **k: None
sys.modules.setdefault("openai", openai_stub)

redis_stub = types.ModuleType("redis.asyncio")
redis_stub.from_url = lambda *a, **k: None
redis_stub.Redis = object
sys.modules.setdefault("redis.asyncio", redis_stub)

from advanced_rag_service.main import app


class DummyResponse:
    def __init__(self, data):
        self.status_code = 200
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    async def fake_post(self, url, json=None, timeout=None):
        return DummyResponse(
            {
                "alert_text": "Analysis",
                "severity": "medium",
                "evidence_ids": ["e1", "e2"],
            }
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    async def fake_build(ids):
        return {"chain_id": "c1", "evidence_chain": {}, "confidence_level": "high"}

    monkeypatch.setattr("advanced_rag_service.main.build_evidence_chain", fake_build)


def test_multi_modal_analysis():
    client = TestClient(app)
    resp = client.post("/analyze/multi-modal", json={"query": "q"})
    assert resp.status_code == 200
    body = resp.json()
    assert "analysis" in body
    assert "evidence_chain" in body
