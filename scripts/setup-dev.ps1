# Surveillance System - Geliştirme Ortamı Hazırlama Scripti
# Bu script geliştirme için gerekli araçları kurar ve ortamı hazırlar

param(
    [switch]$SkipPython,
    [switch]$SkipNodejs,
    [switch]$SkipTools,
    [switch]$FullSetup
)

function Write-ColorOutput($ForegroundColor) {
    if ($Host.UI.RawUI.ForegroundColor) {
        $fc = $Host.UI.RawUI.ForegroundColor
        $Host.UI.RawUI.ForegroundColor = $ForegroundColor
        if ($args) {
            Write-Output $args
        } else {
            $input | Write-Output
        }
        $Host.UI.RawUI.ForegroundColor = $fc
    } else {
        if ($args) {
            Write-Output $args
        } else {
            $input | Write-Output
        }
    }
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Info { Write-ColorOutput Cyan $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }

Write-Host @"
🛠️  Surveillance System - Geliştirme Ortamı Hazırlama
==================================================
"@ -ForegroundColor Magenta

# Python sanal ortamı kurulumu
function Install-PythonEnvironment {
    if ($SkipPython) {
        Write-Warning "Python kurulumu atlanıyor..."
        return
    }

    Write-Info "🐍 Python geliştirme ortamı hazırlanıyor..."
    
    # Python kontrolü
    try {
        $pythonVersion = python --version
        Write-Success "✅ Python bulundu: $pythonVersion"
    }
    catch {
        Write-Error "❌ Python bulunamadı. Lütfen Python 3.8+ kurun."
        return
    }

    # Sanal ortam oluştur
    if (!(Test-Path "venv")) {
        Write-Info "📦 Python sanal ortamı oluşturuluyor..."
        python -m venv venv
        Write-Success "✅ Sanal ortam oluşturuldu"
    }

    # Sanal ortamı aktif et
    Write-Info "🔄 Sanal ortam aktif ediliyor..."
    & .\venv\Scripts\Activate.ps1

    # Temel paketleri kur
    Write-Info "📚 Temel Python paketleri kuruluyor..."
    pip install --upgrade pip setuptools wheel

    # Geliştirme araçlarını kur
    Write-Info "🔧 Geliştirme araçları kuruluyor..."
    pip install pytest pytest-cov black flake8 mypy pre-commit isort bandit safety

    # Proje gereksinimlerini kur
    $requirementFiles = @(
        "requirements.txt",
        "requirements-dev.txt"
    )

    foreach ($reqFile in $requirementFiles) {
        if (Test-Path $reqFile) {
            Write-Info "📋 $reqFile gereksinimleri kuruluyor..."
            pip install -r $reqFile
        }
    }

    # Servis gereksinimlerini kur
    $services = Get-ChildItem -Directory | Where-Object { Test-Path "$($_.Name)/requirements.txt" }
    foreach ($service in $services) {
        Write-Info "📦 $($service.Name) gereksinimleri kuruluyor..."
        pip install -r "$($service.Name)/requirements.txt"
    }

    Write-Success "✅ Python geliştirme ortamı hazır"
}

# Node.js ortamı kurulumu (mobile app için)
function Install-NodeEnvironment {
    if ($SkipNodejs) {
        Write-Warning "Node.js kurulumu atlanıyor..."
        return
    }

    Write-Info "📱 Node.js geliştirme ortamı hazırlanıyor..."
    
    # Node.js kontrolü
    try {
        $nodeVersion = node --version
        Write-Success "✅ Node.js bulundu: $nodeVersion"
    }
    catch {
        Write-Warning "⚠️  Node.js bulunamadı. Mobile app geliştirme için Node.js kurmanız önerilir."
        return
    }

    # Mobile app dizininde npm install
    if (Test-Path "mobile-app/package.json") {
        Write-Info "📱 Mobile app dependencies kuruluyor..."
        Set-Location "mobile-app"
        npm install
        Set-Location ".."
        Write-Success "✅ Mobile app dependencies kuruldu"
    }

    # Website dizininde npm install
    if (Test-Path "website/package.json") {
        Write-Info "🌐 Website dependencies kuruluyor..."
        Set-Location "website"
        npm install
        Set-Location ".."
        Write-Success "✅ Website dependencies kuruldu"
    }
}

# Geliştirme araçlarını kur
function Install-DevelopmentTools {
    if ($SkipTools) {
        Write-Warning "Geliştirme araçları kurulumu atlanıyor..."
        return
    }

    Write-Info "🔧 Geliştirme araçları hazırlanıyor..."

    # Pre-commit hooks kurulumu
    if (Test-Path ".pre-commit-config.yaml") {
        Write-Info "🪝 Pre-commit hooks kuruluyor..."
        pre-commit install
        Write-Success "✅ Pre-commit hooks kuruldu"
    }

    # VS Code ayarları
    $vscodeDir = ".vscode"
    if (!(Test-Path $vscodeDir)) {
        New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
    }

    # VS Code settings.json
    $vscodeSettings = @{
        "python.defaultInterpreterPath" = "./venv/Scripts/python.exe"
        "python.formatting.provider" = "black"
        "python.linting.enabled" = $true
        "python.linting.flake8Enabled" = $true
        "python.linting.mypyEnabled" = $true
        "files.associations" = @{
            "*.dockerfile" = "dockerfile"
            "docker-compose*.yml" = "dockercompose"
        }
        "docker.defaultRegistryPath" = "surveillance"
        "[python]" = @{
            "editor.formatOnSave" = $true
            "editor.codeActionsOnSave" = @{
                "source.organizeImports" = $true
            }
        }
    }

    $vscodeSettings | ConvertTo-Json -Depth 4 | Out-File -FilePath "$vscodeDir/settings.json" -Encoding UTF8
    Write-Success "✅ VS Code ayarları oluşturuldu"

    # Launch configuration
    $launchConfig = @{
        version = "0.2.0"
        configurations = @(
            @{
                name = "Debug FastAPI"
                type = "python"
                request = "launch"
                program = "${workspaceFolder}/api_gateway/main.py"
                console = "integratedTerminal"
                envFile = "${workspaceFolder}/.env"
            },
            @{
                name = "Debug Edge Service"
                type = "python"
                request = "launch"
                program = "${workspaceFolder}/edge_service/main.py"
                console = "integratedTerminal"
                envFile = "${workspaceFolder}/.env"
            }
        )
    }

    $launchConfig | ConvertTo-Json -Depth 4 | Out-File -FilePath "$vscodeDir/launch.json" -Encoding UTF8
    Write-Success "✅ VS Code launch configuration oluşturuldu"

    # Task configuration
    $taskConfig = @{
        version = "2.0.0"
        tasks = @(
            @{
                label = "Run Tests"
                type = "shell"
                command = "pytest"
                group = "test"
                presentation = @{
                    echo = $true
                    reveal = "always"
                    focus = $false
                    panel = "shared"
                }
            },
            @{
                label = "Format Code"
                type = "shell"
                command = "black ."
                group = "build"
            },
            @{
                label = "Lint Code"
                type = "shell"
                command = "flake8 ."
                group = "build"
            },
            @{
                label = "Type Check"
                type = "shell"
                command = "mypy ."
                group = "build"
            },
            @{
                label = "Build Docker Images"
                type = "shell"
                command = "docker-compose build"
                group = "build"
            },
            @{
                label = "Start System"
                type = "shell"
                command = ".\quick-start.ps1"
                group = "build"
            }
        )
    }

    $taskConfig | ConvertTo-Json -Depth 4 | Out-File -FilePath "$vscodeDir/tasks.json" -Encoding UTF8
    Write-Success "✅ VS Code task configuration oluşturuldu"
}

# Test veritabanı kurulumu
function Setup-TestDatabase {
    Write-Info "🗄️  Test veritabanı hazırlanıyor..."
    
    # Test için ayrı .env dosyası
    $testEnvContent = @"
# Test Environment Configuration
ENVIRONMENT=test
POSTGRES_DB=test_events_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
DATABASE_URL=postgresql://test_user:test_password@localhost:5433/test_events_db
REDIS_URL=redis://localhost:6380/0
"@

    $testEnvContent | Out-File -FilePath ".env.test" -Encoding UTF8
    Write-Success "✅ Test environment dosyası oluşturuldu"
}

# Makefile oluştur
function New-Makefile {
    Write-Info "📋 Makefile oluşturuluyor..."
    
    $makefileContent = @"
# Surveillance System Makefile
# Windows PowerShell komutları için

.PHONY: help install start stop status clean test lint format type-check build

help: ## Bu yardım mesajını göster
	@echo "Surveillance System - Makefile Commands"
	@echo "======================================"
	@echo ""
	@echo "install     - Geliştirme ortamını kur"
	@echo "start       - Sistemi başlat"
	@echo "stop        - Sistemi durdur"
	@echo "status      - Sistem durumunu kontrol et"
	@echo "test        - Testleri çalıştır"
	@echo "lint        - Code linting"
	@echo "format      - Code formatting"
	@echo "type-check  - Type checking"
	@echo "build       - Docker images build et"
	@echo "clean       - Sistemi temizle"

install: ## Geliştirme ortamını kur
	powershell -ExecutionPolicy Bypass -File setup-dev.ps1

start: ## Sistemi başlat
	powershell -ExecutionPolicy Bypass -File quick-start.ps1

stop: ## Sistemi durdur
	powershell -ExecutionPolicy Bypass -File quick-start.ps1 -Stop

status: ## Sistem durumunu kontrol et
	powershell -ExecutionPolicy Bypass -File check-status.ps1

test: ## Testleri çalıştır
	pytest tests/ -v --cov=.

lint: ## Code linting
	flake8 .
	bandit -r . -x tests/

format: ## Code formatting
	black .
	isort .

type-check: ## Type checking
	mypy .

build: ## Docker images build et
	docker-compose build

clean: ## Sistemi temizle
	powershell -ExecutionPolicy Bypass -File setup-windows.ps1 clean
"@

    $makefileContent | Out-File -FilePath "Makefile" -Encoding UTF8
    Write-Success "✅ Makefile oluşturuldu"
}

# Ana kurulum fonksiyonu
function Install-DevEnvironment {
    Write-Host "🚀 Geliştirme ortamı kurulumu başlıyor..." -ForegroundColor Green
    
    Install-PythonEnvironment
    Install-NodeEnvironment
    Install-DevelopmentTools
    Setup-TestDatabase
    New-Makefile
    
    if ($FullSetup) {
        Write-Info "🔄 Tam kurulum için ana sistemi de kuruyor..."
        & .\setup-windows.ps1 -DevMode
    }
    
    Write-Host @"

🎉 Geliştirme ortamı hazır!
=========================

Geliştirme araçları:
• Python sanal ortamı: .\venv\Scripts\Activate.ps1
• VS Code ayarları: .vscode/ dizininde
• Pre-commit hooks: git commit'lerinde otomatik kontrol

Kullanışlı komutlar:
• Testleri çalıştır: pytest
• Kodu formatla: black .
• Kod kontrolü: flake8 .
• Type checking: mypy .
• Pre-commit test: pre-commit run --all-files

VS Code'da F5 ile debug modunda çalıştırabilirsiniz.
Ctrl+Shift+P -> "Tasks: Run Task" ile build görevlerini çalıştırabilirsiniz.

"@ -ForegroundColor Green
}

# Script'i çalıştır
Install-DevEnvironment
