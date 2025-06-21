#!/bin/bash
# CI/CD Dependency Validation Script
# This script is designed to run in CI/CD pipelines to ensure
# all dependencies are properly pinned and secure.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REQUIREMENTS_FILE="requirements.txt"
STRICT_MODE=false
CHECK_SECURITY=false
GENERATE_LOCK=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strict)
            STRICT_MODE=true
            shift
            ;;
        --check-security)
            CHECK_SECURITY=true
            shift
            ;;
        --generate-lock)
            GENERATE_LOCK=true
            shift
            ;;
        --requirements)
            REQUIREMENTS_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--strict] [--check-security] [--generate-lock] [--requirements FILE]"
            echo ""
            echo "Options:"
            echo "  --strict          Treat warnings as errors"
            echo "  --check-security  Check for known security vulnerabilities"
            echo "  --generate-lock   Generate requirements.lock file"
            echo "  --requirements    Path to requirements file (default: requirements.txt)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🔍 CI/CD Dependency Validation${NC}"
echo "============================================"
echo "Requirements file: $REQUIREMENTS_FILE"
echo "Strict mode: $STRICT_MODE"
echo "Security check: $CHECK_SECURITY"
echo "Generate lock: $GENERATE_LOCK"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not available${NC}"
    exit 1
fi

# Check if requirements file exists
if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo -e "${RED}❌ Requirements file '$REQUIREMENTS_FILE' not found${NC}"
    exit 1
fi

# Run the Python validation script
VALIDATION_ARGS=""
if [[ "$STRICT_MODE" == "true" ]]; then
    VALIDATION_ARGS="$VALIDATION_ARGS --strict"
fi

if [[ "$CHECK_SECURITY" == "true" ]]; then
    VALIDATION_ARGS="$VALIDATION_ARGS --check-security"
fi

if [[ "$GENERATE_LOCK" == "true" ]]; then
    VALIDATION_ARGS="$VALIDATION_ARGS --generate-lock"
fi

# Run validation
if python validate_dependencies.py --requirements "$REQUIREMENTS_FILE" $VALIDATION_ARGS; then
    echo -e "${GREEN}✅ Dependency validation passed${NC}"
    exit 0
else
    echo -e "${RED}❌ Dependency validation failed${NC}"
    exit 1
fi
