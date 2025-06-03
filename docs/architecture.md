# Architecture & Design

This section explains the system architecture, service responsibilities, and data flow.

## System Architecture Diagram
```mermaid
graph TB
    subgraph "External Systems"
        A[Mobile Apps] --> B[API Gateway]
        C[Web Dashboard] --> B
        D[Third-party APIs] --> B
    end
    
    subgraph "Edge Layer"
        B --> E[Edge Service]
        E --> F[Camera Feeds]
    end
    
    subgraph "Processing Layer"
        E --> G[Ingest Service]
        G --> H[Message Queue (Kafka)]
        H --> I[RAG Service]
        H --> J[Prompt Service]
        H --> K[Rule Generation Service]
    end
    
    subgraph "Data Layer"
        I --> L[Weaviate Vector DB]
        G --> M[PostgreSQL]
        E --> N[Redis Cache]
    end
    
    subgraph "Notification Layer"
        K --> O[Notifier Service]
        O --> P[Email/SMS/Slack/Webhook]
        O --> Q[VMS Service]
    end
```

## Service Responsibilities

- **Edge Service** (Port 8001): Captures video, runs AI inference for object detection.
- **VMS Service** (Port 8008): Manages video clip storage and retrieval.
- **Ingest Service** (Port 8003): Data ingestion and processing into PostgreSQL and Kafka.
- **Prompt Service** (Port 8005): Manages prompt templates and context assembly.
- **RAG Service** (Port 8004): Retrieval-Augmented Generation using Weaviate embeddings.
- **Rule Generation Service** (Port 8006): Dynamically creates and tests alerting rules.
- **Notifier Service** (Port 8007): Sends alerts via various channels (email, SMS, Slack, webhooks).
- **MQTT-Kafka Bridge** (Port 8002): Bridges MQTT camera feeds into Kafka topics.

## Health & Monitoring

- Health endpoints: `/health` on each service.
- Metrics exposed at `/metrics` for Prometheus scraping.
- Dashboards in Grafana at `http://localhost:3000`.
