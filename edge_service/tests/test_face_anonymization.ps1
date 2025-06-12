# Face Anonymization Test Script
# This script tests the face anonymization functionality

param(
    [switch]$SetupModels,
    [switch]$RunTests,
    [switch]$All
)

Write-Host "Face Anonymization Test Suite" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$EdgeServicePath = "c:\Users\kutlu\OneDrive\Desktop\surveillance-system\edge_service"
$ModelsPath = Join-Path $EdgeServicePath "models"

# Function to run command and check result
function Invoke-CommandWithCheck {
    param(
        [string]$Command,
        [string]$Description
    )
    
    Write-Host "`n$Description..." -ForegroundColor Yellow
    
    try {
        $result = Invoke-Expression $Command
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $Description completed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $Description failed with exit code $LASTEXITCODE" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "✗ $Description failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to setup face detection models
function Setup-FaceModels {
    Write-Host "`nSetting up face detection models..." -ForegroundColor Cyan
    
    # Change to edge service directory
    Push-Location $EdgeServicePath
    
    try {
        # Run the model setup script
        $success = Invoke-CommandWithCheck "python setup_face_models.py models" "Face models download"
        
        if ($success) {
            # Verify models directory
            if (Test-Path $ModelsPath) {
                $modelFiles = @(
                    "haarcascade_frontalface_default.xml",
                    "opencv_face_detector.pbtxt", 
                    "opencv_face_detector_uint8.pb"
                )
                
                $allModelsPresent = $true
                foreach ($file in $modelFiles) {
                    $filePath = Join-Path $ModelsPath $file
                    if (Test-Path $filePath) {
                        $size = (Get-Item $filePath).Length
                        Write-Host "✓ $file ($size bytes)" -ForegroundColor Green
                    } else {
                        Write-Host "✗ Missing: $file" -ForegroundColor Red
                        $allModelsPresent = $false
                    }
                }
                
                if ($allModelsPresent) {
                    Write-Host "✓ All face detection models are present" -ForegroundColor Green
                } else {
                    Write-Host "✗ Some face detection models are missing" -ForegroundColor Red
                }
            } else {
                Write-Host "✗ Models directory not created" -ForegroundColor Red
            }
        }
    } finally {
        Pop-Location
    }
}

# Function to run unit tests
function Run-UnitTests {
    Write-Host "`nRunning face anonymization unit tests..." -ForegroundColor Cyan
    
    Push-Location $EdgeServicePath
    
    try {
        # Install test dependencies if not present
        Invoke-CommandWithCheck "pip install pytest pytest-asyncio pytest-mock" "Installing test dependencies"
        
        # Run specific face anonymization tests
        $testFiles = @(
            "tests/test_face_anonymization.py",
            "tests/test_integration_anonymization.py"
        )
        
        foreach ($testFile in $testFiles) {
            if (Test-Path $testFile) {
                $success = Invoke-CommandWithCheck "python -m pytest $testFile -v" "Running $testFile"
                if (-not $success) {
                    Write-Host "✗ Test failures detected in $testFile" -ForegroundColor Red
                }
            } else {
                Write-Host "✗ Test file not found: $testFile" -ForegroundColor Red
            }
        }
        
        # Run all tests with coverage
        Write-Host "`nRunning full test suite with coverage..." -ForegroundColor Yellow
        Invoke-CommandWithCheck "python -m pytest tests/ --cov=face_anonymization --cov-report=term-missing" "Test coverage analysis"
        
    } finally {
        Pop-Location
    }
}

# Function to test API endpoints
function Test-APIEndpoints {
    Write-Host "`nTesting face anonymization API endpoints..." -ForegroundColor Cyan
    
    # Check if edge service is running
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 5
        Write-Host "✓ Edge service is running" -ForegroundColor Green
        
        # Test privacy status endpoint
        try {
            $privacyStatus = Invoke-RestMethod -Uri "http://localhost:8001/privacy/status" -Method GET
            Write-Host "✓ Privacy status endpoint working" -ForegroundColor Green
            Write-Host "   - Enabled: $($privacyStatus.enabled)" -ForegroundColor White
            Write-Host "   - Privacy Level: $($privacyStatus.privacy_level)" -ForegroundColor White
            Write-Host "   - Method: $($privacyStatus.anonymization_method)" -ForegroundColor White
        } catch {
            Write-Host "✗ Privacy status endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        # Test privacy configuration endpoint
        try {
            $configData = @{
                privacy_level = "moderate"
                anonymization_method = "blur"
            } | ConvertTo-Json
            
            $configResponse = Invoke-RestMethod -Uri "http://localhost:8001/privacy/configure" -Method POST -Body $configData -ContentType "application/json"
            Write-Host "✓ Privacy configuration endpoint working" -ForegroundColor Green
        } catch {
            Write-Host "✗ Privacy configuration endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        # Test privacy test endpoint
        try {
            $testResponse = Invoke-RestMethod -Uri "http://localhost:8001/privacy/test" -Method POST
            Write-Host "✓ Privacy test endpoint working" -ForegroundColor Green
        } catch {
            Write-Host "✗ Privacy test endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        
    } catch {
        Write-Host "✗ Edge service not running. Start it with: uvicorn main:app --host 0.0.0.0 --port 8001" -ForegroundColor Red
    }
}

# Function to check environment configuration
function Check-Environment {
    Write-Host "`nChecking environment configuration..." -ForegroundColor Cyan
    
    $envFile = "c:\Users\kutlu\OneDrive\Desktop\surveillance-system\.env"
    
    if (Test-Path $envFile) {
        Write-Host "✓ .env file found" -ForegroundColor Green
        
        $envContent = Get-Content $envFile
        $anonymizationVars = @(
            "ANONYMIZATION_ENABLED",
            "PRIVACY_LEVEL", 
            "ANONYMIZATION_METHOD",
            "FACE_MODEL_PATH"
        )
        
        foreach ($var in $anonymizationVars) {
            $found = $envContent | Where-Object { $_ -match "^$var=" }
            if ($found) {
                Write-Host "✓ $var = $($found -replace '^[^=]+=','')" -ForegroundColor Green
            } else {
                Write-Host "✗ Missing environment variable: $var" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "✗ .env file not found" -ForegroundColor Red
    }
    
    # Check Docker configuration
    $dockerCompose = "c:\Users\kutlu\OneDrive\Desktop\surveillance-system\docker-compose.yml"
    if (Test-Path $dockerCompose) {
        $dockerContent = Get-Content $dockerCompose
        if ($dockerContent | Where-Object { $_ -match "ANONYMIZATION_ENABLED" }) {
            Write-Host "✓ Docker Compose has anonymization configuration" -ForegroundColor Green
        } else {
            Write-Host "✗ Docker Compose missing anonymization configuration" -ForegroundColor Red
        }
    }
}

# Function to generate test report
function Generate-TestReport {
    Write-Host "`nGenerating test report..." -ForegroundColor Cyan
    
    $reportPath = Join-Path $EdgeServicePath "test_report.txt"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    $report = @"
Face Anonymization Test Report
Generated: $timestamp

Environment Status:
"@
    
    # Add environment check results to report
    $report += "`n" + (Check-Environment | Out-String)
    
    # Save report
    $report | Out-File -FilePath $reportPath -Encoding UTF8
    Write-Host "✓ Test report saved to: $reportPath" -ForegroundColor Green
}

# Main execution logic
if ($All -or $SetupModels) {
    Setup-FaceModels
}

if ($All -or $RunTests) {
    Run-UnitTests
}

if ($All) {
    Check-Environment
    Test-APIEndpoints
    Generate-TestReport
}

# Show usage if no parameters
if (-not ($SetupModels -or $RunTests -or $All)) {
    Write-Host "`nUsage:" -ForegroundColor Yellow
    Write-Host "  .\test_face_anonymization.ps1 -SetupModels   # Download face detection models" -ForegroundColor White
    Write-Host "  .\test_face_anonymization.ps1 -RunTests      # Run unit tests" -ForegroundColor White  
    Write-Host "  .\test_face_anonymization.ps1 -All           # Run complete test suite" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\test_face_anonymization.ps1 -SetupModels" -ForegroundColor Gray
    Write-Host "  .\test_face_anonymization.ps1 -RunTests" -ForegroundColor Gray
    Write-Host "  .\test_face_anonymization.ps1 -All" -ForegroundColor Gray
}

Write-Host "`nFace anonymization testing completed!" -ForegroundColor Cyan
