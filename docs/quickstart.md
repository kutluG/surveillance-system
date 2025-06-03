# Quick Start Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.8+
- Git

## Clone & Setup

```bash
git clone https://github.com/kutluG/surveillance-system.git
cd surveillance-system
env  # or make env
cp .env.example .env  # edit .env with your API keys and settings
```

## Start Services

```bash
make quick-start  # spins up infra + app services
```

## Verify

```bash
make health      # check service health
docker-compose logs -f
```

## Access APIs & Dashboards

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Edge Service API: http://localhost:8001/docs
- RAG Service API: http://localhost:8004/docs
- Notifier API: http://localhost:8007/docs
- VMS Service API: http://localhost:8008/docs

Refer to [CONTRIBUTING.md](/CONTRIBUTING.md) for development workflows.
