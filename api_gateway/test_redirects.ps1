# Backwards Compatibility Redirect Test Script (PowerShell)
# Tests HTTP 301 redirects from unversioned to versioned API endpoints

Write-Host "🔄 Testing Backwards Compatibility Redirects" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# API Gateway URL (adjust as needed)
$ApiGateway = "http://localhost:8001"

# Test cases: unversioned endpoints that should redirect to v1
$TestEndpoints = @(
    "/api/edge/health",
    "/api/rag/analysis", 
    "/api/prompt/query",
    "/api/notifier/send",
    "/api/vms/clips",
    "/api/voice/transcribe",
    "/api/training/jobs",
    "/api/enhanced-prompt/conversation",
    "/api/agent-orchestrator/tasks",
    "/api/rule-builder/build"
)

# Function to test redirect
function Test-Redirect {
    param([string]$Endpoint)
    
    Write-Host "Testing: $Endpoint" -ForegroundColor Yellow
    
    try {
        # Create HTTP request that doesn't follow redirects
        $response = Invoke-WebRequest -Uri "$ApiGateway$Endpoint" -Method GET -MaximumRedirection 0 -ErrorAction SilentlyContinue
        
        # This shouldn't execute as we expect a redirect, but just in case
        Write-Host "  ❌ Expected redirect but got: $($response.StatusCode)" -ForegroundColor Red
    }
    catch {
        # Check if it's a redirect (301)
        if ($_.Exception.Response.StatusCode -eq 301) {
            $location = $_.Exception.Response.Headers.Location
            $redirectHeader = $_.Exception.Response.Headers["X-API-Version-Redirect"]
            
            Write-Host "  ✅ Status: 301 Moved Permanently" -ForegroundColor Green
            Write-Host "  📍 Location: $location" -ForegroundColor White
            Write-Host "  🏷️  X-API-Version-Redirect: $redirectHeader" -ForegroundColor White
            
            # Verify the redirect URL is correct
            $expectedLocation = "/api/v1" + $Endpoint.Substring(4)
            if ($location -eq $expectedLocation) {
                Write-Host "  ✅ Redirect URL is correct" -ForegroundColor Green
            } else {
                Write-Host "  ❌ Expected: $expectedLocation" -ForegroundColor Red
                Write-Host "  ❌ Got: $location" -ForegroundColor Red
            }
        } else {
            Write-Host "  ❌ Expected 301, got: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Function to test query parameter preservation
function Test-QueryParams {
    $endpoint = "/api/vms/clips?limit=10&status=active"
    Write-Host "Testing query parameter preservation: $endpoint" -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri "$ApiGateway$endpoint" -Method GET -MaximumRedirection 0 -ErrorAction SilentlyContinue
        Write-Host "  ❌ Expected redirect but got: $($response.StatusCode)" -ForegroundColor Red
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 301) {
            $location = $_.Exception.Response.Headers.Location
            
            Write-Host "  ✅ Status: 301 Moved Permanently" -ForegroundColor Green
            Write-Host "  📍 Location: $location" -ForegroundColor White
            
            # Check if query params are preserved
            if ($location -like "*limit=10*" -and $location -like "*status=active*") {
                Write-Host "  ✅ Query parameters preserved" -ForegroundColor Green
            } else {
                Write-Host "  ❌ Query parameters not preserved correctly" -ForegroundColor Red
            }
        } else {
            Write-Host "  ❌ Expected 301, got: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Run tests
Write-Host "Testing individual endpoints:" -ForegroundColor Cyan
Write-Host "----------------------------" -ForegroundColor Cyan
foreach ($endpoint in $TestEndpoints) {
    Test-Redirect $endpoint
}

Write-Host "Testing query parameter preservation:" -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Cyan
Test-QueryParams

Write-Host "✅ Redirect testing completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: These tests require the API Gateway to be running at $ApiGateway" -ForegroundColor Yellow
Write-Host "Start the gateway with: docker-compose up api_gateway" -ForegroundColor Yellow
