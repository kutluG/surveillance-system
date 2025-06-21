# Performance Testing Script for Annotation Backend (PowerShell)
# This script provides convenient commands for running various load test scenarios

param(
    [string]$Command = "help",
    [int]$Users = 50,
    [int]$SpawnRate = 5,
    [string]$Duration = "5m",
    [string]$TargetHost = "http://localhost:8001"
)

# Configuration
$LocustFile = "locustfile.py"
$ReportsDir = "reports"
$DefaultHost = if ($env:HOST) { $env:HOST } else { "http://localhost:8001" }

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Show-Usage {
    Write-Host "Performance Testing Script for Annotation Backend"
    Write-Host ""
    Write-Host "Usage: .\run-performance-tests.ps1 -Command <COMMAND> [OPTIONS]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  install             Install performance testing dependencies"
    Write-Host "  check               Check if backend is available"
    Write-Host "  light               Run light load test (10 users, 2m)"
    Write-Host "  standard            Run standard load test (50 users, 5m)"
    Write-Host "  heavy               Run heavy load test (100 users, 10m)"
    Write-Host "  stress              Run stress test (200 users, 15m)"
    Write-Host "  custom              Run custom test with specified parameters"
    Write-Host "  web                 Start Locust web UI for interactive testing"
    Write-Host "  ci                  Run CI-optimized test (standard test in headless mode)"
    Write-Host "  clean               Clean up generated reports and logs"
    Write-Host ""
    Write-Host "Options for custom command:"
    Write-Host "  -Users N            Number of concurrent users (default: 50)"
    Write-Host "  -SpawnRate N        User spawn rate per second (default: 5)"
    Write-Host "  -Duration DURATION  Test duration (e.g., 5m, 300s) (default: 5m)"
    Write-Host "  -Host URL           Target host URL (default: http://localhost:8001)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run-performance-tests.ps1 -Command install"
    Write-Host "  .\run-performance-tests.ps1 -Command check"
    Write-Host "  .\run-performance-tests.ps1 -Command standard"
    Write-Host "  .\run-performance-tests.ps1 -Command custom -Users 100 -SpawnRate 10 -Duration 10m"
    Write-Host "  .\run-performance-tests.ps1 -Command web"
    Write-Host "  .\run-performance-tests.ps1 -Command ci"
}

function Test-Dependencies {
    Write-Info "Checking dependencies..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>$null
        if (-not $pythonVersion) {
            Write-ErrorMsg "Python is not installed or not in PATH"
            return $false
        }
    } catch {
        Write-ErrorMsg "Python is not installed or not in PATH"
        return $false
    }
    
    # Check Locust
    try {
        python -c "import locust" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Locust is not installed. Run '.\run-performance-tests.ps1 -Command install' first."
            return $false
        }
    } catch {
        Write-ErrorMsg "Locust is not installed. Run '.\run-performance-tests.ps1 -Command install' first."
        return $false
    }
    
    Write-Success "All dependencies are available"
    return $true
}

function Test-Backend {
    param([string]$TestHost = $DefaultHost)
    
    Write-Info "Checking backend availability at $TestHost..."
    
    try {
        Invoke-RestMethod -Uri "$TestHost/health" -Method Get -TimeoutSec 10 -ErrorAction SilentlyContinue | Out-Null
        Write-Success "Backend is available at $TestHost"
        return $true
    } catch {
        Write-ErrorMsg "Backend is not available at $TestHost"
        Write-Warning "Make sure the annotation backend is running"
        return $false
    }
}

function Install-Dependencies {
    Write-Info "Installing performance testing dependencies..."
    
    if (Test-Path "requirements-performance.txt") {
        python -m pip install -r requirements-performance.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Dependencies installed successfully"
        } else {
            Write-ErrorMsg "Failed to install dependencies"
            return $false
        }
    } else {
        Write-Warning "requirements-performance.txt not found, installing Locust only"
        python -m pip install locust
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Locust installed successfully"
        } else {
            Write-ErrorMsg "Failed to install Locust"
            return $false
        }
    }
    
    return $true
}

function Initialize-ReportsDir {
    if (-not (Test-Path $ReportsDir)) {
        New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
        Write-Info "Created reports directory: $ReportsDir"
    }
}

function Invoke-LoadTest {
    param(
        [int]$TestUsers,
        [int]$TestSpawnRate,
        [string]$TestDuration,
        [string]$TestName,
        [string]$TargetHost = $DefaultHost,
        [string]$AdditionalArgs = ""
    )
    
    Write-Info "Starting $TestName load test..."
    Write-Info "Configuration: $TestUsers users, spawn rate $TestSpawnRate/s, duration $TestDuration"
    Write-Info "Target: $TargetHost"
    
    Initialize-ReportsDir
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $reportFile = "$ReportsDir\${TestName}_${timestamp}.html"
    $csvPrefix = "$ReportsDir\${TestName}_${timestamp}"
    
    # Build Locust command
    $locustCmd = @(
        "locust",
        "-f", $LocustFile,
        "--headless",
        "--users", $TestUsers,
        "--spawn-rate", $TestSpawnRate,
        "--run-time", $TestDuration,
        "--host", $TargetHost,
        "--html", $reportFile,
        "--csv", $csvPrefix,
        "--loglevel", "INFO"
    )
    
    if ($AdditionalArgs) {
        $locustCmd += $AdditionalArgs.Split(' ')
    }
    
    # Run Locust test
    & $locustCmd[0] $locustCmd[1..($locustCmd.Length-1)]
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Success "$TestName test completed successfully"
        Write-Info "HTML Report: $reportFile"
        Write-Info "CSV Results: ${csvPrefix}_stats.csv"
    } else {
        Write-ErrorMsg "$TestName test failed with exit code $exitCode"
        Write-Warning "Check the report for details: $reportFile"
    }
    
    return $exitCode -eq 0
}

function Invoke-LightTest {
    return Invoke-LoadTest -TestUsers 10 -TestSpawnRate 2 -TestDuration "2m" -TestName "light"
}

function Invoke-StandardTest {
    return Invoke-LoadTest -TestUsers 50 -TestSpawnRate 5 -TestDuration "5m" -TestName "standard"
}

function Invoke-HeavyTest {
    return Invoke-LoadTest -TestUsers 100 -TestSpawnRate 10 -TestDuration "10m" -TestName "heavy"
}

function Invoke-StressTest {
    return Invoke-LoadTest -TestUsers 200 -TestSpawnRate 20 -TestDuration "15m" -TestName "stress"
}

function Invoke-CiTest {
    Write-Info "Running CI-optimized performance test..."
    
    # CI test focuses on performance thresholds
    $additionalArgs = "--only-summary --stop-timeout 10"
    
    $success = Invoke-LoadTest -TestUsers 50 -TestSpawnRate 5 -TestDuration "5m" -TestName "ci" -AdditionalArgs $additionalArgs
    
    if (-not $success) {
        Write-ErrorMsg "CI performance test failed - performance thresholds not met"
        Write-Warning "Check the application performance and infrastructure capacity"
        return $false
    }
    
    Write-Success "CI performance test passed - all thresholds met"
    return $true
}

function Invoke-CustomTest {
    return Invoke-LoadTest -TestUsers $Users -TestSpawnRate $SpawnRate -TestDuration $Duration -TestName "custom" -TargetHost $TargetHost
}

function Start-WebUI {
    Write-Info "Starting Locust web UI..."
    Write-Info "Open http://localhost:8089 in your browser"
    Write-Info "Press Ctrl+C to stop"
    
    locust -f $LocustFile --host $DefaultHost --web-host 0.0.0.0 --web-port 8089
}

function Clear-Reports {
    Write-Info "Cleaning up reports and logs..."
    
    if (Test-Path $ReportsDir) {
        Remove-Item -Path $ReportsDir -Recurse -Force
        Write-Success "Removed reports directory"
    }
    
    if (Test-Path "locust.log") {
        Remove-Item -Path "locust.log" -Force
        Write-Success "Removed log file"
    }
    
    Write-Success "Cleanup completed"
}

# Main script logic
switch ($Command.ToLower()) {
    "install" {
        Install-Dependencies
    }
    "check" {
        Test-Backend
    }
    "light" {
        if ((Test-Dependencies) -and (Test-Backend)) {
            Invoke-LightTest
        }
    }
    "standard" {
        if ((Test-Dependencies) -and (Test-Backend)) {
            Invoke-StandardTest
        }
    }
    "heavy" {
        if ((Test-Dependencies) -and (Test-Backend)) {
            Invoke-HeavyTest
        }
    }
    "stress" {
        if ((Test-Dependencies) -and (Test-Backend)) {
            Invoke-StressTest
        }
    }    "custom" {
        if ((Test-Dependencies) -and (Test-Backend -TestHost $TargetHost)) {
            Invoke-CustomTest
        }
    }
    "web" {
        if (Test-Dependencies) {
            Start-WebUI
        }
    }
    "ci" {
        if ((Test-Dependencies) -and (Test-Backend)) {
            $success = Invoke-CiTest
            if (-not $success) {
                exit 1
            }
        }
    }
    "clean" {
        Clear-Reports
    }
    default {
        if ($Command -ne "help") {
            Write-ErrorMsg "Unknown command: $Command"
            Write-Host ""
        }
        Show-Usage
        if ($Command -ne "help") {
            exit 1
        }
    }
}
