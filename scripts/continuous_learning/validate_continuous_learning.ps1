# Continuous Learning Pipeline Validation Script
# Validates the implementation without requiring Docker

Write-Host "=== Continuous Learning Pipeline Validation ===" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0

function Test-FileExists {
    param($FilePath, $Description)
    if (Test-Path $FilePath) {
        Write-Host "✓ $Description" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ $Description - File not found: $FilePath" -ForegroundColor Red
        $script:ErrorCount++
        return $false
    }
}

function Test-PythonSyntax {
    param($FilePath, $Description)
    try {
        python -m py_compile $FilePath 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $Description - Syntax OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $Description - Syntax Error" -ForegroundColor Red
            $script:ErrorCount++
            return $false
        }
    } catch {
        Write-Host "⚠ $Description - Could not validate (Python not available)" -ForegroundColor Yellow
        $script:WarningCount++
        return $false
    }
}

function Test-DockerFile {
    param($FilePath, $Description)
    if (Test-Path $FilePath) {
        $content = Get-Content $FilePath -Raw
        if ($content -match "FROM" -and $content -match "COPY" -and $content -match "WORKDIR") {
            Write-Host "✓ $Description - Dockerfile structure OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $Description - Invalid Dockerfile structure" -ForegroundColor Red
            $script:ErrorCount++
            return $false
        }
    } else {
        Write-Host "✗ $Description - Dockerfile not found" -ForegroundColor Red
        $script:ErrorCount++
        return $false
    }
}

function Test-Requirements {
    param($FilePath, $Description)
    if (Test-Path $FilePath) {
        $content = Get-Content $FilePath
        $requiredPackages = @("fastapi", "uvicorn", "confluent-kafka", "pydantic")
        $missingPackages = @()
        
        foreach ($package in $requiredPackages) {
            if (-not ($content | Where-Object { $_ -match $package })) {
                $missingPackages += $package
            }
        }
        
        if ($missingPackages.Count -eq 0) {
            Write-Host "✓ $Description - All required packages present" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠ $Description - Missing packages: $($missingPackages -join ', ')" -ForegroundColor Yellow
            $script:WarningCount++
            return $false
        }
    } else {
        Write-Host "✗ $Description - Requirements file not found" -ForegroundColor Red
        $script:ErrorCount++
        return $false
    }
}

Write-Host "`n1. Validating Hard Example Collector..." -ForegroundColor Yellow
Test-FileExists "hard_example_collector/main.py" "Hard Example Collector main.py"
Test-FileExists "hard_example_collector/Dockerfile" "Hard Example Collector Dockerfile"
Test-FileExists "hard_example_collector/requirements.txt" "Hard Example Collector requirements.txt"
Test-PythonSyntax "hard_example_collector/main.py" "Hard Example Collector Python syntax"
Test-DockerFile "hard_example_collector/Dockerfile" "Hard Example Collector Dockerfile"
Test-Requirements "hard_example_collector/requirements.txt" "Hard Example Collector requirements"

Write-Host "`n2. Validating Annotation Frontend..." -ForegroundColor Yellow
Test-FileExists "annotation_frontend/main.py" "Annotation Frontend main.py"
Test-FileExists "annotation_frontend/Dockerfile" "Annotation Frontend Dockerfile"
Test-FileExists "annotation_frontend/requirements.txt" "Annotation Frontend requirements.txt"
Test-FileExists "annotation_frontend/templates/index.html" "Annotation Frontend template"
Test-PythonSyntax "annotation_frontend/main.py" "Annotation Frontend Python syntax"
Test-DockerFile "annotation_frontend/Dockerfile" "Annotation Frontend Dockerfile"
Test-Requirements "annotation_frontend/requirements.txt" "Annotation Frontend requirements"

Write-Host "`n3. Validating Training Service..." -ForegroundColor Yellow
Test-FileExists "training_service/main.py" "Training Service main.py"
Test-FileExists "training_service/Dockerfile" "Training Service Dockerfile"
Test-FileExists "training_service/requirements.txt" "Training Service requirements.txt"
Test-PythonSyntax "training_service/main.py" "Training Service Python syntax"
Test-DockerFile "training_service/Dockerfile" "Training Service Dockerfile"
Test-Requirements "training_service/requirements.txt" "Training Service requirements"

Write-Host "`n4. Validating Edge Service Integration..." -ForegroundColor Yellow
Test-FileExists "edge_service/inference.py" "Enhanced Edge Service inference.py"
Test-PythonSyntax "edge_service/inference.py" "Edge Service inference.py syntax"

# Check if kafka-python is in edge service requirements
if (Test-Path "edge_service/requirements.txt") {
    $edgeRequirements = Get-Content "edge_service/requirements.txt"
    if ($edgeRequirements | Where-Object { $_ -match "kafka-python" }) {
        Write-Host "✓ Edge Service - Kafka dependency added" -ForegroundColor Green
    } else {
        Write-Host "⚠ Edge Service - Kafka dependency might be missing" -ForegroundColor Yellow
        $WarningCount++
    }
} else {
    Write-Host "✗ Edge Service - requirements.txt not found" -ForegroundColor Red
    $ErrorCount++
}

Write-Host "`n5. Validating Docker Compose Configuration..." -ForegroundColor Yellow
if (Test-Path "docker-compose.yml") {
    $composeContent = Get-Content "docker-compose.yml" -Raw
    
    $requiredServices = @("hard_example_collector", "annotation_frontend", "training_service")
    foreach ($service in $requiredServices) {
        if ($composeContent -match $service) {
            Write-Host "✓ Docker Compose - $service service defined" -ForegroundColor Green
        } else {
            Write-Host "✗ Docker Compose - $service service missing" -ForegroundColor Red
            $ErrorCount++
        }
    }
    
    # Check for required ports
    $requiredPorts = @("8010", "8011", "8012")
    foreach ($port in $requiredPorts) {
        if ($composeContent -match $port) {
            Write-Host "✓ Docker Compose - Port $port configured" -ForegroundColor Green
        } else {
            Write-Host "⚠ Docker Compose - Port $port might not be configured" -ForegroundColor Yellow
            $WarningCount++
        }
    }
    
    # Check for Kafka dependency
    if ($composeContent -match "kafka.*depends_on" -or $composeContent -match "depends_on.*kafka") {
        Write-Host "✓ Docker Compose - Kafka dependencies configured" -ForegroundColor Green
    } else {
        Write-Host "⚠ Docker Compose - Kafka dependencies might not be configured" -ForegroundColor Yellow
        $WarningCount++
    }
} else {
    Write-Host "✗ Docker Compose - docker-compose.yml not found" -ForegroundColor Red
    $ErrorCount++
}

Write-Host "`n6. Validating Configuration Scripts..." -ForegroundColor Yellow
Test-FileExists "create_kafka_topics.ps1" "Kafka topics creation script"
Test-FileExists "test_continuous_learning.ps1" "Pipeline test script"
Test-FileExists "monitor_kafka_topics.ps1" "Kafka monitoring script"
Test-FileExists "CONTINUOUS_LEARNING.md" "Documentation"

Write-Host "`n7. Checking Kafka Topic Configuration..." -ForegroundColor Yellow
if (Test-Path "create_kafka_topics.ps1") {
    $topicsScript = Get-Content "create_kafka_topics.ps1" -Raw
    $requiredTopics = @("hard-examples", "labeled-examples", "model-updates")
    
    foreach ($topic in $requiredTopics) {
        if ($topicsScript -match $topic) {
            Write-Host "✓ Kafka Topics - $topic topic configured" -ForegroundColor Green
        } else {
            Write-Host "✗ Kafka Topics - $topic topic missing" -ForegroundColor Red
            $ErrorCount++
        }
    }
} else {
    Write-Host "✗ Kafka Topics - Creation script not found" -ForegroundColor Red
    $ErrorCount++
}

Write-Host "`n8. Validating API Endpoints..." -ForegroundColor Yellow

# Check Hard Example Collector endpoints
if (Test-Path "hard_example_collector/main.py") {
    $collectorContent = Get-Content "hard_example_collector/main.py" -Raw
    $requiredEndpoints = @("/health", "/stats", "/configure")
    
    foreach ($endpoint in $requiredEndpoints) {
        if ($collectorContent -match "@app\.(get|post).*$endpoint") {
            Write-Host "✓ Hard Example Collector - $endpoint endpoint defined" -ForegroundColor Green
        } else {
            Write-Host "⚠ Hard Example Collector - $endpoint endpoint might be missing" -ForegroundColor Yellow
            $WarningCount++
        }
    }
}

# Check Training Service endpoints
if (Test-Path "training_service/main.py") {
    $trainingContent = Get-Content "training_service/main.py" -Raw
    $requiredEndpoints = @("/health", "/stats", "/train")
    
    foreach ($endpoint in $requiredEndpoints) {
        if ($trainingContent -match "@app\.(get|post).*$endpoint") {
            Write-Host "✓ Training Service - $endpoint endpoint defined" -ForegroundColor Green
        } else {
            Write-Host "⚠ Training Service - $endpoint endpoint might be missing" -ForegroundColor Yellow
            $WarningCount++
        }
    }
}

Write-Host "`n=== Validation Summary ===" -ForegroundColor Cyan
Write-Host "Errors: $ErrorCount" -ForegroundColor $(if ($ErrorCount -eq 0) { "Green" } else { "Red" })
Write-Host "Warnings: $WarningCount" -ForegroundColor $(if ($WarningCount -eq 0) { "Green" } else { "Yellow" })

if ($ErrorCount -eq 0) {
    Write-Host "`n✓ Continuous Learning Pipeline implementation is ready!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Start Docker Desktop"
    Write-Host "2. Run: .\test_continuous_learning.ps1 -StartServices"
    Write-Host "3. Monitor with: .\monitor_kafka_topics.ps1"
    Write-Host "4. Open annotation interface: http://localhost:8011"
} else {
    Write-Host "`n✗ Implementation has errors that need to be fixed" -ForegroundColor Red
    Write-Host "Please review the errors above and fix them before proceeding."
}

Write-Host "`nValidation complete." -ForegroundColor Cyan
