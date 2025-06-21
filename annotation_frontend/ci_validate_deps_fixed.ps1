# CI/CD Dependency Validation Script (PowerShell)
# This script is designed to run in Windows CI/CD pipelines to ensure
# all dependencies are properly pinned and secure.

param(
    [string]$RequirementsFile = "requirements.txt",
    [switch]$Strict,
    [switch]$CheckSecurity,
    [switch]$GenerateLock,
    [switch]$Help
)

function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

if ($Help) {
    Write-Host "Usage: .\ci_validate_deps.ps1 [-Strict] [-CheckSecurity] [-GenerateLock] [-RequirementsFile FILE]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Strict          Treat warnings as errors"
    Write-Host "  -CheckSecurity   Check for known security vulnerabilities"
    Write-Host "  -GenerateLock    Generate requirements.lock file"
    Write-Host "  -RequirementsFile Path to requirements file (default: requirements.txt)"
    exit 0
}

Write-ColoredOutput "CI/CD Dependency Validation" "Blue"
Write-Host "============================================"
Write-Host "Requirements file: $RequirementsFile"
Write-Host "Strict mode: $Strict"
Write-Host "Security check: $CheckSecurity"
Write-Host "Generate lock: $GenerateLock"
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion"
} catch {
    Write-ColoredOutput "ERROR: Python is not available" "Red"
    exit 1
}

# Check if requirements file exists
if (-not (Test-Path $RequirementsFile)) {
    Write-ColoredOutput "ERROR: Requirements file '$RequirementsFile' not found" "Red"
    exit 1
}

# Build validation arguments
$ValidationArgs = @("--requirements", $RequirementsFile)

if ($Strict) {
    $ValidationArgs += "--strict"
}

if ($CheckSecurity) {
    $ValidationArgs += "--check-security"
}

if ($GenerateLock) {
    $ValidationArgs += "--generate-lock"
}

# Run validation
try {
    & python validate_dependencies.py @ValidationArgs
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-ColoredOutput "SUCCESS: Dependency validation passed" "Green"
        exit 0
    } else {
        Write-ColoredOutput "ERROR: Dependency validation failed" "Red"
        exit 1
    }
} catch {
    Write-ColoredOutput "ERROR: Failed to run validation script: $_" "Red"
    exit 1
}
