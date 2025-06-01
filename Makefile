# Surveillance System Makefile
# Provides convenient commands for development and deployment

.PHONY: help setup build up down restart logs health clean test lint format

# Default target
help: ## Show this help message
	@echo "Surveillance System - Available Commands:"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and Installation
setup: ## Run initial setup for development environment
	@echo "🚀 Setting up development environment..."
	./scripts/setup-dev.sh

env: ## Create .env file from template
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env file from template"; \
		echo "⚠️  Please edit .env with your configuration"; \
	else \
		echo "✅ .env file already exists"; \
	fi

# Build and Deployment
build: ## Build all Docker images
	@echo "🏗️  Building all services..."
	docker-compose build --parallel

build-service: ## Build specific service (usage: make build-service SERVICE=edge_service)
	@echo "🏗️  Building $(SERVICE)..."
	docker-compose build $(SERVICE)

# Service Management
up: ## Start all services
	@echo "🚀 Starting all services..."
	docker-compose up -d

up-infra: ## Start only infrastructure services
	@echo "📦 Starting infrastructure services..."
	docker-compose up -d postgres redis zookeeper kafka weaviate prometheus grafana

up-apps: ## Start only application services
	@echo "🚀 Starting application services..."
	docker-compose up -d edge_service mqtt_kafka_bridge ingest_service rag_service prompt_service rulegen_service notifier vms_service

down: ## Stop all services
	@echo "🛑 Stopping all services..."
	docker-compose down

restart: ## Restart all services
	@echo "🔄 Restarting all services..."
	docker-compose restart

restart-service: ## Restart specific service (usage: make restart-service SERVICE=edge_service)
	@echo "🔄 Restarting $(SERVICE)..."
	docker-compose restart $(SERVICE)

# Monitoring and Debugging
logs: ## Show logs for all services
	docker-compose logs -f

logs-service: ## Show logs for specific service (usage: make logs-service SERVICE=edge_service)
	docker-compose logs -f $(SERVICE)

health: ## Check health status of all services
	@echo "🔍 Checking service health..."
	@echo "Infrastructure Services:"
	@echo "======================="
	@docker-compose ps postgres redis kafka weaviate prometheus grafana
	@echo ""
	@echo "Application Services:"
	@echo "===================="
	@docker-compose ps edge_service mqtt_kafka_bridge ingest_service rag_service prompt_service rulegen_service notifier vms_service
	@echo ""
	@echo "Health Check Endpoints:"
	@echo "======================"
	@echo "Edge Service:       http://localhost:8001/health"
	@echo "MQTT Bridge:        http://localhost:8002/health"
	@echo "Ingest Service:     http://localhost:8003/health"
	@echo "RAG Service:        http://localhost:8004/health"
	@echo "Prompt Service:     http://localhost:8005/health"
	@echo "RuleGen Service:    http://localhost:8006/health"
	@echo "Notifier:           http://localhost:8007/health"
	@echo "VMS Service:        http://localhost:8008/health"

status: ## Show quick service status
	@docker-compose ps

# Development and Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

test-service: ## Run tests for specific service (usage: make test-service SERVICE=edge_service)
	@echo "🧪 Running tests for $(SERVICE)..."
	cd $(SERVICE) && python -m pytest tests/ -v

test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	python -m pytest integration_tests/ -v

lint: ## Run linting on all services
	@echo "🔍 Running linting..."
	@for service in edge_service mqtt_kafka_bridge ingest_service rag_service prompt_service rulegen_service notifier vms_service; do \
		echo "Linting $$service..."; \
		cd $$service && python -m flake8 . && cd ..; \
	done

format: ## Format code with black
	@echo "🎨 Formatting code..."
	@for service in edge_service mqtt_kafka_bridge ingest_service rag_service prompt_service rulegen_service notifier vms_service; do \
		echo "Formatting $$service..."; \
		cd $$service && python -m black . && cd ..; \
	done

# Utility Commands
clean: ## Clean up Docker resources
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

clean-data: ## Clean up all persistent data (WARNING: This will delete all data!)
	@echo "⚠️  WARNING: This will delete ALL persistent data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v
	docker volume rm $$(docker volume ls -q | grep surveillance) 2>/dev/null || true

reset: clean clean-data build up ## Complete reset: clean, rebuild, and start

# Database Management
db-shell: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U user -d events_db

db-backup: ## Backup database
	@echo "💾 Creating database backup..."
	mkdir -p backups
	docker-compose exec -T postgres pg_dump -U user events_db > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql

db-restore: ## Restore database (usage: make db-restore BACKUP=backup_file.sql)
	@echo "📥 Restoring database from $(BACKUP)..."
	docker-compose exec -T postgres psql -U user -d events_db < $(BACKUP)

# Monitoring and Dashboards
dashboard: ## Open monitoring dashboards
	@echo "📊 Opening monitoring dashboards..."
	@echo "Grafana:    http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "APIs:       http://localhost:800X/docs (X=1-8)"

metrics: ## Show system metrics
	@echo "📈 System Metrics:"
	@echo "=================="
	docker stats --no-stream

# Development Helpers
shell: ## Access shell in specific service (usage: make shell SERVICE=edge_service)
	docker-compose exec $(SERVICE) /bin/bash

python-shell: ## Access Python shell with service environment (usage: make python-shell SERVICE=edge_service)
	docker-compose exec $(SERVICE) python

# Production Deployment
deploy: ## Deploy to production
	@echo "🚀 Deploying to production..."
	./scripts/deployment/deploy.sh production

deploy-staging: ## Deploy to staging
	@echo "🚀 Deploying to staging..."
	./scripts/deployment/deploy.sh staging

# Quick Start
quick-start: env up-infra ## Quick start for development (setup env and infrastructure)
	@echo "⏳ Waiting for infrastructure to be ready..."
	@sleep 30
	@make up-apps
	@echo ""
	@echo "🎉 Surveillance system is starting up!"
	@echo "📊 Monitor progress: make logs"
	@echo "🔍 Check health: make health"
	@echo "📈 Open dashboards: make dashboard"

# Security
cert-gen: ## Generate SSL certificates for development
	@echo "🔐 Generating SSL certificates..."
	mkdir -p certs
	openssl genrsa -out certs/ca.key 4096
	openssl req -new -x509 -days 365 -key certs/ca.key -out certs/ca.crt -subj "/C=US/ST=CA/L=San Francisco/O=Surveillance System/CN=ca"
	openssl genrsa -out certs/client.key 4096
	openssl req -new -key certs/client.key -out certs/client.csr -subj "/C=US/ST=CA/L=San Francisco/O=Surveillance System/CN=client"
	openssl x509 -req -days 365 -in certs/client.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial -out certs/client.crt
	rm certs/client.csr

# Information
info: ## Show system information
	@echo "Surveillance System Information"
	@echo "==============================="
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker-compose --version)"
	@echo "Available services:"
	@docker-compose config --services
	@echo ""
	@echo "Service URLs:"
	@echo "============="
	@echo "Edge Service:       http://localhost:8001"
	@echo "MQTT Bridge:        http://localhost:8002" 
	@echo "Ingest Service:     http://localhost:8003"
	@echo "RAG Service:        http://localhost:8004"
	@echo "Prompt Service:     http://localhost:8005"
	@echo "RuleGen Service:    http://localhost:8006"
	@echo "Notifier:           http://localhost:8007"
	@echo "VMS Service:        http://localhost:8008"
