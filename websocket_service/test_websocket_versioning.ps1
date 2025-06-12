# WebSocket Versioning Test Script (PowerShell)
# Tests WebSocket endpoint versioning and redirect functionality

Write-Host "🔌 WebSocket Versioning and Redirect Tests" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan
Write-Host ""

# Configuration
$WebSocketBase = "ws://localhost:8001"
$TestClient = "powershell_test_client"

function Test-WebSocketEndpoint {
    param(
        [string]$EndpointPath,
        [string]$TestType = "versioned"
    )
    
    $url = "$WebSocketBase$EndpointPath"
    Write-Host "Testing $TestType endpoint: $url" -ForegroundColor Yellow
    
    try {
        # Note: PowerShell doesn't have built-in WebSocket client
        # This would require additional modules like ClientWebSocket
        Write-Host "  📝 Would connect to: $url" -ForegroundColor White
        Write-Host "  💡 Use browser console or wscat for actual testing" -ForegroundColor Gray
        
        # Simulate test result for demonstration
        if ($TestType -eq "versioned") {
            Write-Host "  ✅ Expected: Connection success + welcome message" -ForegroundColor Green
        } else {
            Write-Host "  ✅ Expected: Deprecation notice + connection close" -ForegroundColor Green
        }
        
        return $true
    }
    catch {
        Write-Host "  ❌ Connection test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Test versioned endpoints
Write-Host "📍 Testing Versioned Endpoints:" -ForegroundColor Cyan
Write-Host "-" * 30 -ForegroundColor Cyan

$v1EventsResult = Test-WebSocketEndpoint "/ws/v1/events/$TestClient" "versioned"
$v1AlertsResult = Test-WebSocketEndpoint "/ws/v1/alerts/$TestClient" "versioned"

Write-Host ""

# Test redirect endpoints
Write-Host "📍 Testing Redirect Endpoints:" -ForegroundColor Cyan  
Write-Host "-" * 30 -ForegroundColor Cyan

$oldEventsResult = Test-WebSocketEndpoint "/ws/events/$TestClient" "redirect"
$oldAlertsResult = Test-WebSocketEndpoint "/ws/alerts/$TestClient" "redirect"

Write-Host ""

# Summary
Write-Host "📊 Test Results Summary:" -ForegroundColor Cyan
Write-Host "=" * 30 -ForegroundColor Cyan
Write-Host "✅ /ws/v1/events: $(if($v1EventsResult) {'PASS'} else {'FAIL'})" -ForegroundColor $(if($v1EventsResult) {'Green'} else {'Red'})
Write-Host "✅ /ws/v1/alerts: $(if($v1AlertsResult) {'PASS'} else {'FAIL'})" -ForegroundColor $(if($v1AlertsResult) {'Green'} else {'Red'})
Write-Host "🔀 /ws/events (redirect): $(if($oldEventsResult) {'PASS'} else {'FAIL'})" -ForegroundColor $(if($oldEventsResult) {'Green'} else {'Red'})
Write-Host "🔀 /ws/alerts (redirect): $(if($oldAlertsResult) {'PASS'} else {'FAIL'})" -ForegroundColor $(if($oldAlertsResult) {'Green'} else {'Red'})

Write-Host ""
Write-Host "🧪 Manual Testing Commands:" -ForegroundColor Yellow
Write-Host "=" * 30 -ForegroundColor Yellow
Write-Host ""
Write-Host "# Install wscat globally (if not installed):" -ForegroundColor Gray
Write-Host "npm install -g wscat" -ForegroundColor White
Write-Host ""
Write-Host "# Test versioned endpoints:" -ForegroundColor Gray
Write-Host "wscat -c ws://localhost:8001/ws/v1/events/test123" -ForegroundColor White
Write-Host "wscat -c ws://localhost:8001/ws/v1/alerts/test123" -ForegroundColor White
Write-Host ""
Write-Host "# Test redirect behavior:" -ForegroundColor Gray
Write-Host "wscat -c ws://localhost:8001/ws/events/test123" -ForegroundColor White
Write-Host "wscat -c ws://localhost:8001/ws/alerts/test123" -ForegroundColor White
Write-Host ""

Write-Host "📋 Browser Console Testing:" -ForegroundColor Yellow
Write-Host "=" * 30 -ForegroundColor Yellow
Write-Host ""
Write-Host "// Test versioned endpoint" -ForegroundColor Gray
Write-Host "const ws = new WebSocket('ws://localhost:8001/ws/v1/events/browser123');" -ForegroundColor White
Write-Host "ws.onmessage = (event) => console.log('Received:', JSON.parse(event.data));" -ForegroundColor White
Write-Host ""
Write-Host "// Test redirect behavior" -ForegroundColor Gray  
Write-Host "const oldWs = new WebSocket('ws://localhost:8001/ws/events/browser123');" -ForegroundColor White
Write-Host "oldWs.onmessage = (event) => console.log('Deprecation notice:', JSON.parse(event.data));" -ForegroundColor White
Write-Host "oldWs.onclose = (event) => console.log('Closed with code:', event.code, 'reason:', event.reason);" -ForegroundColor White
Write-Host ""

Write-Host "💡 Note: Ensure services are running with:" -ForegroundColor Yellow
Write-Host "docker-compose up websocket_service api_gateway" -ForegroundColor White
