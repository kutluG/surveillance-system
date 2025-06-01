```markdown
# Prompt Service

Handles user natural-language queries for retrieving event summaries and video clip URLs.

## Configuration

Copy and edit `.env`:

```bash
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=<optional>
CLIP_BASE_URL=https://cdn.example.com/clips
```

## Build & Run

```bash
docker-compose up --build prompt_service
```

## Endpoints

- GET `/health`  
  Returns `{"status":"ok"}`

- POST `/query`  
  Request Body:
  ```json
  {
    "query": "Find person detections near entrance",
    "limit": 3
  }
  ```
  Response Body:
  ```json
  {
    "answer_text": "Here are the relevant events:\n1. event e1 at 2025-05-29T10:00:00Z on camera cam1\n2. event e2 at 2025-05-29T10:05:00Z on camera cam2",
    "clip_links": [
      "https://cdn.example.com/clips/e1.mp4",
      "https://cdn.example.com/clips/e2.mp4"
    ]
  }
  ```
```