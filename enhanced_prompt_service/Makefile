# Enhanced Prompt Service - Dependency Management
# ==================================================

.PHONY: help install install-dev validate audit test clean setup-dev check-deps

# Default target
help:
	@echo "🎯 Enhanced Prompt Service - Dependency Management"
	@echo "=================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install           Install production dependencies"
	@echo "  install-dev       Install development dependencies"
	@echo "  validate          Validate dependency pinning"
	@echo "  audit             Check for security vulnerabilities"
	@echo "  test              Run all tests"
	@echo "  check-deps        Validate dependencies and run security audit"
	@echo "  setup-dev         Complete development environment setup"
	@echo "  clean             Clean Python cache and build artifacts"
	@echo "  update-deps       Interactive dependency update helper"
	@echo ""
	@echo "Examples:"
	@echo "  make check-deps   # Validate and audit dependencies"
	@echo "  make setup-dev    # Set up development environment"
	@echo "  make install      # Install production dependencies"

# Install production dependencies
install:
	@echo "📦 Installing production dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ Dependencies installed successfully"

# Install development dependencies
install-dev: install
	@echo "🔧 Installing development dependencies..."
	pip install pytest pytest-asyncio pytest-cov httpx
	pip install bandit safety pipdeptree
	@echo "✅ Development dependencies installed"

# Validate dependency pinning
validate:
	@echo "🔍 Validating dependency pinning..."
	python scripts/validate_requirements.py

# Run security audit
audit:
	@echo "🔐 Running security audit..."
	python scripts/audit_dependencies.py

# Run tests
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Check dependencies (validate + audit)
check-deps: validate audit
	@echo "✅ All dependency checks passed!"

# Set up development environment
setup-dev:
	@echo "🚀 Setting up development environment..."
	@echo "Creating virtual environment..."
	python -m venv venv
	@echo "Installing dependencies..."
	@make install-dev
	@echo "Validating setup..."
	@make check-deps
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "To activate the virtual environment:"
	@echo "  source venv/bin/activate  # On Linux/Mac"
	@echo "  venv\\Scripts\\activate     # On Windows"

# Clean Python cache and build artifacts
clean:
	@echo "🧹 Cleaning cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/
	@echo "✅ Cleanup completed"

# Interactive dependency update helper
update-deps:
	@echo "🔄 Dependency Update Helper"
	@echo "=========================="
	@echo ""
	@echo "Current dependencies:"
	@pip list --format=freeze | grep -E "(fastapi|uvicorn|pydantic|redis|openai|weaviate-client|requests|PyJWT|python-jose)"
	@echo ""
	@echo "Checking for outdated packages..."
	@pip list --outdated
	@echo ""
	@echo "⚠️  Manual steps required:"
	@echo "1. Research new versions for security and compatibility"
	@echo "2. Update requirements.txt with new pinned versions"
	@echo "3. Run 'make check-deps' to validate changes"
	@echo "4. Run 'make test' to ensure compatibility"
	@echo "5. Commit changes after thorough testing"

# CI/CD simulation
ci-check:
	@echo "🤖 Simulating CI/CD pipeline..."
	@make validate
	@make install
	@make audit
	@make test
	@echo "✅ CI/CD simulation completed successfully!"
