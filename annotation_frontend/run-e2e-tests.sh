#!/bin/bash

# E2E Test Runner Script
# This script sets up the test environment and runs Playwright E2E tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BROWSER="chromium"
HEADED="false"
CLEANUP="true"
USE_DOCKER="false"
DEBUG="false"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -b, --browser BROWSER    Browser to test with (chromium, firefox, webkit, all) [default: chromium]"
    echo "  -h, --headed             Run tests in headed mode"
    echo "  -d, --docker             Use Docker Compose for test environment"
    echo "  -n, --no-cleanup         Don't cleanup test environment after tests"
    echo "  -g, --debug              Run tests in debug mode"
    echo "  --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                       # Run chromium tests in headless mode"
    echo "  $0 -b firefox -h         # Run firefox tests in headed mode"
    echo "  $0 -b all -d             # Run all browsers using Docker"
    echo "  $0 -g                    # Run tests in debug mode"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--browser)
            BROWSER="$2"
            shift 2
            ;;
        -h|--headed)
            HEADED="true"
            shift
            ;;
        -d|--docker)
            USE_DOCKER="true"
            shift
            ;;
        -n|--no-cleanup)
            CLEANUP="false"
            shift
            ;;
        -g|--debug)
            DEBUG="true"
            HEADED="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate browser option
if [[ "$BROWSER" != "chromium" && "$BROWSER" != "firefox" && "$BROWSER" != "webkit" && "$BROWSER" != "all" ]]; then
    print_error "Invalid browser: $BROWSER"
    show_usage
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "package.json" ]] || [[ ! -f "playwright.config.ts" ]]; then
    print_error "This script must be run from the annotation_frontend directory"
    exit 1
fi

# Function to cleanup test environment
cleanup() {
    if [[ "$CLEANUP" == "true" ]]; then
        print_status "Cleaning up test environment..."
        
        if [[ "$USE_DOCKER" == "true" ]]; then
            print_status "Stopping Docker services..."
            docker-compose -f ../docker-compose.e2e.yml down -v --remove-orphans 2>/dev/null || true
        else
            # Kill local processes if they exist
            pkill -f "python main.py" 2>/dev/null || true
            pkill -f "redis-server" 2>/dev/null || true
        fi
        
        print_success "Cleanup completed"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-60}
    
    print_status "Waiting for $service_name to be ready..."
    
    local count=0
    while ! nc -z $host $port; do
        if [[ $count -gt $timeout ]]; then
            print_error "$service_name failed to start within $timeout seconds"
            return 1
        fi
        sleep 1
        ((count++))
    done
    
    print_success "$service_name is ready"
}

# Function to setup test environment using Docker
setup_docker_env() {
    print_status "Setting up Docker test environment..."
    
    # Start services
    docker-compose -f ../docker-compose.e2e.yml up -d
    
    # Wait for services
    wait_for_service localhost 5433 "PostgreSQL" 60
    wait_for_service localhost 6380 "Redis" 30
    wait_for_service localhost 9093 "Kafka" 120
    wait_for_service localhost 8001 "Annotation Backend" 60
    
    print_success "Docker environment is ready"
}

# Function to setup test environment locally
setup_local_env() {
    print_status "Setting up local test environment..."
    
    # Check if required services are running
    if ! nc -z localhost 5432; then
        print_error "PostgreSQL is not running on localhost:5432"
        print_status "Please start PostgreSQL or use --docker option"
        exit 1
    fi
    
    if ! nc -z localhost 6379; then
        print_error "Redis is not running on localhost:6379"
        print_status "Please start Redis or use --docker option"
        exit 1
    fi
    
    if ! nc -z localhost 9092; then
        print_error "Kafka is not running on localhost:9092"
        print_status "Please start Kafka or use --docker option"
        exit 1
    fi
    
    # Start the annotation backend
    print_status "Starting annotation backend..."
    export DATABASE_URL="postgresql://surveillance_user:surveillance_pass_5487@localhost:5432/events_db"
    export REDIS_URL="redis://localhost:6379"
    export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
    export PORT="8001"
    export ENV="test"
    
    python main.py &
    BACKEND_PID=$!
    
    # Wait for backend to start
    wait_for_service localhost 8001 "Annotation Backend" 30
    
    print_success "Local environment is ready"
}

# Main execution
print_status "Starting E2E test execution..."
print_status "Browser: $BROWSER"
print_status "Headed: $HEADED"
print_status "Docker: $USE_DOCKER"
print_status "Debug: $DEBUG"

# Install dependencies if needed
if [[ ! -d "node_modules" ]]; then
    print_status "Installing Node.js dependencies..."
    npm ci
fi

# Install Playwright browsers
print_status "Installing Playwright browsers..."
if [[ "$BROWSER" == "all" ]]; then
    npx playwright install --with-deps
else
    npx playwright install --with-deps $BROWSER
fi

# Setup test environment
if [[ "$USE_DOCKER" == "true" ]]; then
    setup_docker_env
else
    setup_local_env
fi

# Set environment variables for tests
export CI=false
if [[ "$USE_DOCKER" == "true" ]]; then
    export DATABASE_URL="postgresql://surveillance_user:surveillance_pass_5487@localhost:5433/events_db"
    export REDIS_URL="redis://localhost:6380"
    export KAFKA_BOOTSTRAP_SERVERS="localhost:9093"
else
    export DATABASE_URL="postgresql://surveillance_user:surveillance_pass_5487@localhost:5432/events_db"
    export REDIS_URL="redis://localhost:6379"
    export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
fi
export PORT="8001"
export ENV="test"

# Run tests
print_status "Running Playwright E2E tests..."

if [[ "$DEBUG" == "true" ]]; then
    print_status "Running in debug mode..."
    npx playwright test --project=$BROWSER --debug
elif [[ "$HEADED" == "true" ]]; then
    npx playwright test --project=$BROWSER --headed
else
    npx playwright test --project=$BROWSER
fi

# Check test results
if [[ $? -eq 0 ]]; then
    print_success "All E2E tests passed!"
    
    # Show report location
    if [[ -f "playwright-report/index.html" ]]; then
        print_status "Test report available at: playwright-report/index.html"
        print_status "Open with: npx playwright show-report"
    fi
else
    print_error "Some E2E tests failed"
    
    # Show artifacts location
    if [[ -d "test-results" ]]; then
        print_status "Test artifacts available in: test-results/"
    fi
    
    exit 1
fi
