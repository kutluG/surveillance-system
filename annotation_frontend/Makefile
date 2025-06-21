# Makefile for Annotation Frontend Service
# Dependency management and validation commands

.PHONY: help install install-dev validate-deps validate-deps-strict check-security generate-lock clean test

# Default target
help:
	@echo "🎯 Annotation Frontend Service - Dependency Management"
	@echo "======================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install            Install production dependencies"
	@echo "  install-dev        Install development dependencies (includes pip-audit)"
	@echo "  validate-deps      Validate dependency pinning"
	@echo "  validate-strict    Validate dependencies in strict mode"
	@echo "  check-security     Check for security vulnerabilities"
	@echo "  generate-lock      Generate requirements.lock file"
	@echo "  test               Run tests"
	@echo "  clean              Clean generated files"
	@echo "  pre-commit-setup   Set up pre-commit hooks"
	@echo ""

# Install production dependencies
install:
	@echo "📦 Installing production dependencies..."
	pip install -r requirements.txt

# Install development dependencies including security tools
install-dev: install
	@echo "🔧 Installing development dependencies..."
	pip install pip-audit safety bandit pre-commit

# Validate dependencies
validate-deps:
	@echo "🔍 Validating dependencies..."
	python validate_dependencies.py

# Validate dependencies in strict mode
validate-strict:
	@echo "🔍 Validating dependencies (strict mode)..."
	python validate_dependencies.py --strict

# Check for security vulnerabilities
check-security: install-dev
	@echo "🔒 Checking for security vulnerabilities..."
	python validate_dependencies.py --check-security

# Generate lock file
generate-lock:
	@echo "🔒 Generating requirements.lock file..."
	python validate_dependencies.py --generate-lock

# Run all validations (for CI)
validate-all: validate-strict check-security generate-lock
	@echo "✅ All validations completed successfully!"

# Run tests
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	rm -f requirements.lock
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

# Set up pre-commit hooks
pre-commit-setup:
	@echo "🪝 Setting up pre-commit hooks..."
	@if [ ! -d ".git" ]; then \
		echo "❌ Not in a git repository"; \
		exit 1; \
	fi
	@if [ ! -f ".git/hooks/pre-commit" ]; then \
		cp pre-commit-hook.py .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "✅ Pre-commit hook installed"; \
	else \
		echo "⚠️ Pre-commit hook already exists"; \
	fi

# Quick dependency check (for development)
dep-check: validate-deps
	@echo "✅ Quick dependency check completed"

# Full CI validation
ci-validate: install-dev validate-all test
	@echo "🚀 CI validation pipeline completed successfully!"

# Show dependency information
dep-info:
	@echo "📊 Dependency Information"
	@echo "========================"
	@echo "Requirements file: requirements.txt"
	@if [ -f "requirements.txt" ]; then \
		echo "Total dependencies: $$(grep -v '^#' requirements.txt | grep -v '^$$' | wc -l)"; \
		echo "Pinned dependencies: $$(grep '==' requirements.txt | wc -l)"; \
		echo "Version ranges: $$(grep -E '[><=!~]' requirements.txt | grep -v '==' | wc -l)"; \
	fi
	@if [ -f "requirements.lock" ]; then \
		echo "Lock file: requirements.lock (exists)"; \
	else \
		echo "Lock file: requirements.lock (not generated)"; \
	fi

# Check for outdated dependencies
check-outdated: install-dev
	@echo "📅 Checking for outdated dependencies..."
	pip list --outdated

# Update dependency validation script
update-validator:
	@echo "⬇️ Updating dependency validation script..."
	@if [ -f "../annotation_frontend/validate_dependencies.py" ]; then \
		cp ../annotation_frontend/validate_dependencies.py .; \
		echo "✅ Updated validate_dependencies.py"; \
	else \
		echo "❌ Source validation script not found"; \
	fi
