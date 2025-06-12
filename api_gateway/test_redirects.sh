#!/bin/bash
# Backwards Compatibility Redirect Test Script
# Tests HTTP 301 redirects from unversioned to versioned API endpoints

echo "🔄 Testing Backwards Compatibility Redirects"
echo "=============================================="
echo ""

# API Gateway URL (adjust as needed)
API_GATEWAY="http://localhost:8001"

# Test cases: unversioned endpoints that should redirect to v1
declare -a TEST_ENDPOINTS=(
    "/api/edge/health"
    "/api/rag/analysis"
    "/api/prompt/query"
    "/api/notifier/send"
    "/api/vms/clips"
    "/api/voice/transcribe"
    "/api/training/jobs"
    "/api/enhanced-prompt/conversation"
    "/api/agent-orchestrator/tasks"
    "/api/rule-builder/build"
)

# Function to test redirect
test_redirect() {
    local endpoint=$1
    echo "Testing: $endpoint"
    
    # Use curl to get headers only (-I) and don't follow redirects (--max-redirs 0)
    response=$(curl -I -s --max-redirs 0 "${API_GATEWAY}${endpoint}" 2>/dev/null)
    
    # Extract status code
    status_code=$(echo "$response" | head -n1 | cut -d' ' -f2)
    
    # Extract Location header
    location=$(echo "$response" | grep -i "^location:" | cut -d' ' -f2- | tr -d '\r')
    
    # Extract custom header
    redirect_header=$(echo "$response" | grep -i "^x-api-version-redirect:" | cut -d' ' -f2- | tr -d '\r')
    
    if [ "$status_code" = "301" ]; then
        echo "  ✅ Status: 301 Moved Permanently"
        echo "  📍 Location: $location"
        echo "  🏷️  X-API-Version-Redirect: $redirect_header"
        
        # Verify the redirect URL is correct
        expected_location="/api/v1${endpoint#/api}"
        if [ "$location" = "$expected_location" ]; then
            echo "  ✅ Redirect URL is correct"
        else
            echo "  ❌ Expected: $expected_location"
            echo "  ❌ Got: $location"
        fi
    else
        echo "  ❌ Expected 301, got: $status_code"
    fi
    echo ""
}

# Test query parameter preservation
test_query_params() {
    local endpoint="/api/vms/clips?limit=10&status=active"
    echo "Testing query parameter preservation: $endpoint"
    
    response=$(curl -I -s --max-redirs 0 "${API_GATEWAY}${endpoint}" 2>/dev/null)
    status_code=$(echo "$response" | head -n1 | cut -d' ' -f2)
    location=$(echo "$response" | grep -i "^location:" | cut -d' ' -f2- | tr -d '\r')
    
    if [ "$status_code" = "301" ]; then
        echo "  ✅ Status: 301 Moved Permanently"
        echo "  📍 Location: $location"
        
        # Check if query params are preserved
        if [[ "$location" == *"limit=10&status=active"* ]]; then
            echo "  ✅ Query parameters preserved"
        else
            echo "  ❌ Query parameters not preserved correctly"
        fi
    else
        echo "  ❌ Expected 301, got: $status_code"
    fi
    echo ""
}

# Run tests
echo "Testing individual endpoints:"
echo "----------------------------"
for endpoint in "${TEST_ENDPOINTS[@]}"; do
    test_redirect "$endpoint"
done

echo "Testing query parameter preservation:"
echo "-----------------------------------"
test_query_params

echo "✅ Redirect testing completed!"
echo ""
echo "Note: These tests require the API Gateway to be running at $API_GATEWAY"
echo "Start the gateway with: docker-compose up api_gateway"
