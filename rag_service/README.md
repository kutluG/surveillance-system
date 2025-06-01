```markdown
# RAG Service

Retrieval-Augmented Generation (RAG) service that analyzes user queries
against stored camera events and generates contextual alerts.

## Configuration

Copy and edit `.env`:

```bash
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=<optional>
OPENAI_API_KEY=<your-openai-key>
OPENAI_MODEL=gpt-4
```

## Build & Run

```bash
docker-compose up --build rag_service
```

## Endpoints

- POST `/analysis`  
  Request Body:
  ```json
  {
    "query": "Describe suspicious movement near door at 3 AM",
    "context_ids": ["...optional event IDs..."]
  }
  ```
  Response Body (Alert):
  ```json
  {
    "id": "...",
    "timestamp": "...",
    "alert_text": "Multiple figures loitered by the rear entrance around 03:15.",
    "severity": "high",
    "evidence_ids": ["..."]
  }
  ```
- GET `/health` – returns `{"status":"ok"}`.
```