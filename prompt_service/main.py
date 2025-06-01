"""
Prompt Service: handles natural-language queries to retrieve event summaries and clip links.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from shared.logging import get_logger
from shared.metrics import instrument_app
from shared.models import QueryResult

from prompt_service.weaviate_client import semantic_search
from prompt_service.clip_store import get_clip_url

LOGGER = get_logger("prompt_service")
app = FastAPI(title="Prompt Service")
instrument_app(app, service_name="prompt_service")

class QueryRequest(BaseModel):
    query: str
    limit: int = 5

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResult)
async def query_endpoint(req: QueryRequest):
    LOGGER.info("Query received", query=req.query, limit=req.limit)
    # Step 1: semantic retrieval
    try:
        contexts = semantic_search(req.query, limit=req.limit)
    except Exception as e:
        LOGGER.error("Weaviate search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Context retrieval error")
    # Step 2: build a human-readable answer
    lines = [
        f"{idx+1}. event {ctx['event_id']} at {ctx['timestamp']} on camera {ctx['camera_id']}"
        for idx, ctx in enumerate(contexts)
    ]
    answer_text = "Here are the relevant events:\n" + "\n".join(lines) if lines else "No relevant events found."
    # Step 3: generate clip links
    clip_links = [get_clip_url(ctx["event_id"]) for ctx in contexts]
    return QueryResult(answer_text=answer_text, clip_links=clip_links)