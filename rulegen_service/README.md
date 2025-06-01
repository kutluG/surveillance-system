```markdown
# Rule Generation Service

Manages security policy rules and evaluates camera events against them to trigger actions.

## Features

- Create rules from natural language descriptions using LLM
- Store and manage policy rules in PostgreSQL
- Evaluate events against active rules
- Support for complex conditions (time ranges, detection types, camera zones)
- JWT authentication for rule management

## Configuration

Copy and edit `.env`:

```bash
DATABASE_URL=postgresql://user:password@postgres:5432/events_db
OPENAI_API_KEY=<your-openai-key>
OPENAI_MODEL=gpt-4
JWT_SECRET_KEY=<your-jwt-secret>
```

## Build & Run

```bash
docker-compose up --build rulegen_service
```

## Endpoints

- POST `/rules` - Create new policy rule from natural language
- GET `/rules` - List all rules (optionally active only)
- PUT `/rules/{id}/toggle` - Activate/deactivate a rule
- DELETE `/rules/{id}` - Delete a rule
- POST `/evaluate` - Evaluate event against all active rules
- GET `/health` - Health check

## Example Usage

Create a rule:
```bash
curl -X POST http://localhost:8000/rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "After Hours Person Detection",
    "rule_text": "Alert security team when person detected in restricted area between 10 PM and 6 AM"
  }'
```

Evaluate an event:
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "camera_id": "restricted-area-01",
      "event_type": "detection",
      "detections": [{"label": "person", "confidence": 0.95}],
      "timestamp": "2025-05-31T02:30:00Z"
    }
  }'
```
```