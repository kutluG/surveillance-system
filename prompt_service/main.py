"""
Prompt Service: handles natural-language queries to retrieve event summaries and clip links.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from shared.logging_config import configure_logging, get_logger, log_context
from shared.audit_middleware import add_audit_middleware
from shared.metrics import instrument_app
from shared.models import QueryResult
from shared.middleware import add_rate_limiting

from .weaviate_client import semantic_search
from clip_store import get_clip_url

# Configure logging first
logger = configure_logging("prompt_service")

app = FastAPI(
    title="Prompt Service",
    openapi_prefix="/api/v1"
)

# Add audit middleware
add_audit_middleware(app, service_name="prompt_service")
instrument_app(app, service_name="prompt_service")

# Add rate limiting middleware
add_rate_limiting(app, service_name="prompt_service")

class QueryRequest(BaseModel):
    query: str
    limit: int = 5

@app.get("/health")
async def health():
    logger.info("Health check performed", extra={'action': 'health_check'})
    return {"status": "ok"}

@app.post("/api/v1/query", response_model=QueryResult)
async def query_endpoint(req: QueryRequest):
    with log_context(action="prompt_query", query=req.query[:100]):  # Truncate query for logging
        logger.info("Query received", extra={
            'action': 'prompt_query',
            'query': req.query[:100],  # Truncate for logging
            'limit': req.limit
        })
        # Step 1: semantic retrieval
        try:
            contexts = semantic_search(req.query, limit=req.limit)
            logger.info("Context retrieved from Weaviate", extra={
                'action': 'weaviate_search',
                'context_count': len(contexts)
            })
        except Exception as e:
            logger.error("Weaviate search failed", extra={
                'action': 'weaviate_search_error',
                'error': str(e)
            })
            raise HTTPException(status_code=500, detail="Context retrieval error")        # Step 2: build a human-readable answer
        lines = [
            f"{idx+1}. event {ctx['event_id']} at {ctx['timestamp']} on camera {ctx['camera_id']}"
            for idx, ctx in enumerate(contexts)
        ]
        answer_text = "Here are the relevant events:\n" + "\n".join(lines) if lines else "No relevant events found."
        
        # Step 3: generate clip links
        clip_links = [get_clip_url(ctx["event_id"]) for ctx in contexts]
        
        logger.info("Query processed successfully", extra={
            'action': 'query_complete',
            'result_count': len(contexts),
            'clip_links_count': len(clip_links)
        })
        
        return QueryResult(answer_text=answer_text, clip_links=clip_links)