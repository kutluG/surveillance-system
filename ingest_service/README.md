````markdown
# Event Ingest Service

Consumes camera events from Kafka, validates and transforms them, then persists to PostgreSQL and upserts embeddings into Weaviate.

## Prerequisites

- PostgreSQL database at `DATABASE_URL`
- Kafka broker at `KAFKA_BROKER`
- Weaviate instance at `WEAVIATE_URL`

## Configuration

Populate `.env` with:

```bash
DATABASE_URL=postgresql://user:password@postgres:5432/events_db
KAFKA_BROKER=kafka:9092
KAFKA_TOPIC=camera.events
GROUP_ID=ingest-service-group
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=<your-api-key-if-any>