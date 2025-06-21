# E2E Test Runner Script for Windows PowerShell
# This script sets up the test environment and runs Playwright E2E tests

param(
    [string]$Browser = "chromium",
    [switch]$Headed = $false,
    [switch]$Docker = $false,
    [switch]$NoCleanup = $false,
    [switch]$Debug = $false,
    [switch]$Help = $false
)

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

function Write-Status {
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

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Show-Usage {
    Write-Host "Usage: .\run-e2e-tests.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Browser BROWSER         Browser to test with (chromium, firefox, webkit, all) [default: chromium]"
    Write-Host "  -Headed                  Run tests in headed mode"
    Write-Host "  -Docker                  Use Docker Compose for test environment"
    Write-Host "  -NoCleanup               Don't cleanup test environment after tests"
    Write-Host "  -Debug                   Run tests in debug mode"
    Write-Host "  -Help                    Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run-e2e-tests.ps1                    # Run chromium tests in headless mode"
    Write-Host "  .\run-e2e-tests.ps1 -Browser firefox -Headed  # Run firefox tests in headed mode"
    Write-Host "  .\run-e2e-tests.ps1 -Browser all -Docker      # Run all browsers using Docker"
    Write-Host "  .\run-e2e-tests.ps1 -Debug                    # Run tests in debug mode"
}

if ($Help) {
    Show-Usage
    exit 0
}

# Validate browser option
$ValidBrowsers = @("chromium", "firefox", "webkit", "all")
if ($Browser -notin $ValidBrowsers) {
    Write-Error "Invalid browser: $Browser"
    Show-Usage
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "package.json") -or -not (Test-Path "playwright.config.ts")) {
    Write-Error "This script must be run from the annotation_frontend directory"
    exit 1
}

# If debug mode, enable headed mode
if ($Debug) {
    $Headed = $true
}

$Cleanup = -not $NoCleanup

# Function to cleanup test environment
function Invoke-Cleanup {
    if ($Cleanup) {
        Write-Status "Cleaning up test environment..."
        
        if ($Docker) {
            Write-Status "Stopping Docker services..."
            try {
                docker-compose -f ..\docker-compose.e2e.yml down -v --remove-orphans 2>$null
            } catch {
                # Ignore errors during cleanup
            }
        } else {
            # Kill local processes if they exist
            try {
                Get-Process | Where-Object { $_.ProcessName -like "*python*" -and $_.CommandLine -like "*main.py*" } | Stop-Process -Force
            } catch {
                # Ignore errors
            }
        }
        
        Write-Success "Cleanup completed"
    }
}

# Register cleanup on exit
Register-EngineEvent PowerShell.Exiting -Action { Invoke-Cleanup }

# Function to wait for service
function Wait-ForService {
    param(
        [string]$HostName,
        [int]$Port,
        [string]$ServiceName,
        [int]$Timeout = 60
    )
    
    Write-Status "Waiting for $ServiceName to be ready..."
    
    $count = 0    do {
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.ConnectAsync($HostName, $Port).Wait(1000)
            if ($tcpClient.Connected) {
                $tcpClient.Close()
                Write-Success "$ServiceName is ready"
                return $true
            }
        } catch {
            # Connection failed, continue waiting
        }
        
        Start-Sleep -Seconds 1
        $count++
        
        if ($count -gt $Timeout) {
            Write-Error "$ServiceName failed to start within $Timeout seconds"
            return $false
        }
    } while ($true)
}

# Function to test port
function Test-Port {
    param(
        [string]$HostName = "localhost",
        [int]$Port
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ConnectAsync($HostName, $Port).Wait(1000)
        $result = $tcpClient.Connected
        $tcpClient.Close()
        return $result
    } catch {
        return $false
    }
}

# Function to setup test environment using Docker
function Initialize-DockerEnv {
    Write-Status "Setting up Docker test environment..."
    
    # Start services
    docker-compose -f ..\docker-compose.e2e.yml up -d
      # Wait for services
    if (-not (Wait-ForService -HostName "localhost" -Port 5433 -ServiceName "PostgreSQL" -Timeout 60)) { exit 1 }
    if (-not (Wait-ForService -HostName "localhost" -Port 6380 -ServiceName "Redis" -Timeout 30)) { exit 1 }
    if (-not (Wait-ForService -HostName "localhost" -Port 9093 -ServiceName "Kafka" -Timeout 120)) { exit 1 }
    if (-not (Wait-ForService -HostName "localhost" -Port 8001 -ServiceName "Annotation Backend" -Timeout 60)) { exit 1 }
    
    Write-Success "Docker environment is ready"
}

# Function to setup test environment locally
function Initialize-LocalEnv {
    Write-Status "Setting up local test environment..."
    
    # Check if required services are running
    if (-not (Test-Port -Port 5432)) {
        Write-Error "PostgreSQL is not running on localhost:5432"
        Write-Status "Please start PostgreSQL or use -Docker option"
        exit 1
    }
    
    if (-not (Test-Port -Port 6379)) {
        Write-Error "Redis is not running on localhost:6379"
        Write-Status "Please start Redis or use -Docker option"
        exit 1
    }
    
    if (-not (Test-Port -Port 9092)) {
        Write-Error "Kafka is not running on localhost:9092"
        Write-Status "Please start Kafka or use -Docker option"
        exit 1
    }
    
    # Start the annotation backend
    Write-Status "Starting annotation backend..."
    $env:DATABASE_URL = "postgresql://surveillance_user:surveillance_pass_5487@localhost:5432/events_db"
    $env:REDIS_URL = "redis://localhost:6379"
    $env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
    $env:PORT = "8001"
    $env:ENV = "test"
    
    Start-Process -FilePath "python" -ArgumentList "main.py" -NoNewWindow
      # Wait for backend to start
    if (-not (Wait-ForService -HostName "localhost" -Port 8001 -ServiceName "Annotation Backend" -Timeout 30)) { exit 1 }
    
    Write-Success "Local environment is ready"
}

# Main execution
Write-Status "Starting E2E test execution..."
Write-Status "Browser: $Browser"
Write-Status "Headed: $Headed"
Write-Status "Docker: $Docker"
Write-Status "Debug: $Debug"

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Status "Installing Node.js dependencies..."
    npm ci
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install Node.js dependencies"
        exit 1
    }
}

# Install Playwright browsers
Write-Status "Installing Playwright browsers..."
if ($Browser -eq "all") {
    npx playwright install --with-deps
} else {
    npx playwright install --with-deps $Browser
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Playwright browsers"
    exit 1
}

# Setup test environment
if ($Docker) {
    Initialize-DockerEnv
} else {
    Initialize-LocalEnv
}

# Set environment variables for tests
$env:CI = "false"
if ($Docker) {
    $env:DATABASE_URL = "postgresql://surveillance_user:surveillance_pass_5487@localhost:5433/events_db"
    $env:REDIS_URL = "redis://localhost:6380"
    $env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9093"
} else {
    $env:DATABASE_URL = "postgresql://surveillance_user:surveillance_pass_5487@localhost:5432/events_db"
    $env:REDIS_URL = "redis://localhost:6379"
    $env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
}
$env:PORT = "8001"
$env:ENV = "test"

# Run tests
Write-Status "Running Playwright E2E tests..."

try {
    if ($Debug) {
        Write-Status "Running in debug mode..."
        npx playwright test --project=$Browser --debug
    } elseif ($Headed) {
        npx playwright test --project=$Browser --headed
    } else {
        npx playwright test --project=$Browser
    }
    
    # Check test results
    if ($LASTEXITCODE -eq 0) {
        Write-Success "All E2E tests passed!"
        
        # Show report location
        if (Test-Path "playwright-report\index.html") {
            Write-Status "Test report available at: playwright-report\index.html"
            Write-Status "Open with: npx playwright show-report"
        }
    } else {
        Write-Error "Some E2E tests failed"
        
        # Show artifacts location
        if (Test-Path "test-results") {
            Write-Status "Test artifacts available in: test-results\"
        }
        
        exit 1
    }
} finally {
    Invoke-Cleanup
}
