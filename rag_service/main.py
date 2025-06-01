"""
RAG Service: handles /analysis endpoint to produce semantic alerts.
"""
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.models import Alert, SeverityLevel

from weaviate_client import semantic_search
from llm_client import generate_alert

LOGGER = get_logger("rag_service")
app = FastAPI(title="RAG Service")
instrument_app(app, service_name="rag_service")


class AnalysisRequest(BaseModel):
    query: str
    context_ids: Optional[List[str]] = None


@app.post("/analysis", response_model=Alert)
async def analyze(req: AnalysisRequest):
    """
    Analyze a natural language query against camera events, return an Alert.
    """
    LOGGER.info("Analysis request received", query=req.query, context_ids=req.context_ids)
    # Step 1: Retrieve context from Weaviate
    try:
        contexts = semantic_search(req.query, limit=5)
    except Exception as e:
        LOGGER.error("Weaviate search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Context retrieval error")
    # Step 2: Call LLM to generate alert JSON
    try:
        alert_json = generate_alert(req.query, contexts)
    except Exception as e:
        LOGGER.error("LLM generation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Alert generation error")
    # Step 3: Validate and build Alert model
    try:
        alert = Alert(
            alert_text=alert_json["alert_text"],
            severity=SeverityLevel(alert_json["severity"]),
            evidence_ids=alert_json["evidence_ids"],
        )
    except Exception as e:
        LOGGER.error("Alert model validation failed", error=str(e), payload=alert_json)
        raise HTTPException(status_code=500, detail="Invalid alert format")
    LOGGER.info("Generated alert", alert_id=str(alert.id), severity=alert.severity.value)
    return alert


@app.get("/health")
async def health():
    return {"status": "ok"}