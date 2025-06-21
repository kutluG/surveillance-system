#!/bin/bash
# Performance Testing Script for Annotation Backend
# This script provides convenient commands for running various load test scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOCUST_FILE="locustfile.py"
HOST="${HOST:-http://localhost:8001}"
REPORTS_DIR="reports"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
Performance Testing Script for Annotation Backend

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    install             Install performance testing dependencies
    check               Check if backend is available
    light               Run light load test (10 users, 2m)
    standard            Run standard load test (50 users, 5m)
    heavy               Run heavy load test (100 users, 10m)
    stress              Run stress test (200 users, 15m)
    custom              Run custom test with specified parameters
    web                 Start Locust web UI for interactive testing
    ci                  Run CI-optimized test (standard test in headless mode)
    clean               Clean up generated reports and logs

Options for custom command:
    -u, --users N       Number of concurrent users (default: 50)
    -r, --spawn-rate N  User spawn rate per second (default: 5)
    -t, --time DURATION Test duration (e.g., 5m, 300s) (default: 5m)
    -H, --host URL      Target host URL (default: http://localhost:8001)

Examples:
    $0 install                                    # Install dependencies
    $0 check                                      # Check backend availability
    $0 standard                                   # Run standard load test
    $0 custom -u 100 -r 10 -t 10m               # Custom test: 100 users, 10/s spawn rate, 10 minutes
    $0 web                                        # Start web UI for interactive testing
    $0 ci                                         # Run CI test

Environment Variables:
    HOST                Target host URL (default: http://localhost:8001)
    LOCUST_LOGLEVEL     Log level (default: INFO)
EOF
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        return 1
    fi
    
    if ! python3 -c "import locust" 2>/dev/null; then
        log_error "Locust is not installed. Run '$0 install' first."
        return 1
    fi
    
    log_success "All dependencies are available"
    return 0
}

check_backend() {
    log_info "Checking backend availability at $HOST..."
    
    if curl -f -s "$HOST/health" > /dev/null 2>&1; then
        log_success "Backend is available at $HOST"
        return 0
    else
        log_error "Backend is not available at $HOST"
        log_warning "Make sure the annotation backend is running"
        return 1
    fi
}

install_dependencies() {
    log_info "Installing performance testing dependencies..."
    
    if [ -f "requirements-performance.txt" ]; then
        pip3 install -r requirements-performance.txt
        log_success "Dependencies installed successfully"
    else
        log_warning "requirements-performance.txt not found, installing Locust only"
        pip3 install locust
    fi
}

setup_reports_dir() {
    if [ ! -d "$REPORTS_DIR" ]; then
        mkdir -p "$REPORTS_DIR"
        log_info "Created reports directory: $REPORTS_DIR"
    fi
}

run_load_test() {
    local users=$1
    local spawn_rate=$2
    local duration=$3
    local test_name=$4
    local additional_args=${5:-""}
    
    log_info "Starting $test_name load test..."
    log_info "Configuration: $users users, spawn rate $spawn_rate/s, duration $duration"
    log_info "Target: $HOST"
    
    setup_reports_dir
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="$REPORTS_DIR/${test_name}_${timestamp}.html"
    local csv_prefix="$REPORTS_DIR/${test_name}_${timestamp}"
    
    # Run Locust test
    locust \
        -f "$LOCUST_FILE" \
        --headless \
        --users "$users" \
        --spawn-rate "$spawn_rate" \
        --run-time "$duration" \
        --host "$HOST" \
        --html "$report_file" \
        --csv "$csv_prefix" \
        --loglevel INFO \
        $additional_args
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "$test_name test completed successfully"
        log_info "HTML Report: $report_file"
        log_info "CSV Results: ${csv_prefix}_stats.csv"
    else
        log_error "$test_name test failed with exit code $exit_code"
        log_warning "Check the report for details: $report_file"
    fi
    
    return $exit_code
}

run_light_test() {
    run_load_test 10 2 "2m" "light"
}

run_standard_test() {
    run_load_test 50 5 "5m" "standard"
}

run_heavy_test() {
    run_load_test 100 10 "10m" "heavy"
}

run_stress_test() {
    run_load_test 200 20 "15m" "stress"
}

run_ci_test() {
    log_info "Running CI-optimized performance test..."
    
    # CI test focuses on performance thresholds
    local additional_args="--only-summary --stop-timeout 10"
    
    if ! run_load_test 50 5 "5m" "ci" "$additional_args"; then
        log_error "CI performance test failed - performance thresholds not met"
        log_warning "Check the application performance and infrastructure capacity"
        return 1
    fi
    
    log_success "CI performance test passed - all thresholds met"
    return 0
}

run_custom_test() {
    local users=50
    local spawn_rate=5
    local duration="5m"
    local custom_host="$HOST"
    
    # Parse custom options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--users)
                users="$2"
                shift 2
                ;;
            -r|--spawn-rate)
                spawn_rate="$2"
                shift 2
                ;;
            -t|--time)
                duration="$2"
                shift 2
                ;;
            -H|--host)
                custom_host="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                return 1
                ;;
        esac
    done
    
    # Temporarily override HOST for this test
    local original_host="$HOST"
    HOST="$custom_host"
    
    run_load_test "$users" "$spawn_rate" "$duration" "custom"
    local result=$?
    
    # Restore original HOST
    HOST="$original_host"
    
    return $result
}

start_web_ui() {
    log_info "Starting Locust web UI..."
    log_info "Open http://localhost:8089 in your browser"
    log_info "Press Ctrl+C to stop"
    
    locust \
        -f "$LOCUST_FILE" \
        --host "$HOST" \
        --web-host 0.0.0.0 \
        --web-port 8089
}

clean_reports() {
    log_info "Cleaning up reports and logs..."
    
    if [ -d "$REPORTS_DIR" ]; then
        rm -rf "$REPORTS_DIR"
        log_success "Removed reports directory"
    fi
    
    if [ -f "locust.log" ]; then
        rm -f "locust.log"
        log_success "Removed log file"
    fi
    
    log_success "Cleanup completed"
}

# Main script logic
main() {
    case "${1:-help}" in
        install)
            install_dependencies
            ;;
        check)
            check_backend
            ;;
        light)
            check_dependencies && check_backend && run_light_test
            ;;
        standard)
            check_dependencies && check_backend && run_standard_test
            ;;
        heavy)
            check_dependencies && check_backend && run_heavy_test
            ;;
        stress)
            check_dependencies && check_backend && run_stress_test
            ;;
        custom)
            shift
            check_dependencies && check_backend && run_custom_test "$@"
            ;;
        web)
            check_dependencies && start_web_ui
            ;;
        ci)
            check_dependencies && check_backend && run_ci_test
            ;;
        clean)
            clean_reports
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
