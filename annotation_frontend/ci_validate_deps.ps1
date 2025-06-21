#!/usr/bin/env pwsh
<#
.SYNOPSIS
    CI/CD Dependency Validation Script for Windows (PowerShell)

.DESCRIPTION
    This script validates that all dependencies in requirements.txt are properly
    pinned to specific versions and checks for security vulnerabilities.
    Designed for use in CI/CD pipelines on Windows systems.

.PARAMETER RequirementsFile
    Path to the requirements file (default: requirements.txt)

.PARAMETER Strict
    If specified, treats warnings as errors

.PARAMETER CheckSecurity
    If specified, performs security vulnerability checks using pip-audit

.PARAMETER GenerateLock
    If specified, generates a requirements.lock file

.PARAMETER Help
    Show help information

.EXAMPLE
    .\ci_validate_deps.ps1
    .\ci_validate_deps.ps1 -Strict -CheckSecurity -GenerateLock

.NOTES
    Author: Generated for Surveillance System
    Version: 2.0
    Compatible with: PowerShell 5.1+ and PowerShell Core 6+
#>

[CmdletBinding()]
param(
    [string]$RequirementsFile = "requirements.txt",
    [switch]$Strict,
    [switch]$CheckSecurity,
    [switch]$GenerateLock,
    [switch]$Help
)

# Set error action preference for strict error handling
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Define colors for output
$Colors = @{
    Info = "Green"
    Warning = "Yellow"
    Error = "Red"
    Header = "Cyan"
    Success = "Magenta"
}

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

Write-ColoredOutput "🔍 CI/CD Dependency Validation" $Blue
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
    Write-ColoredOutput "❌ Python is not available" $Red
    exit 1
}

# Check if requirements file exists
if (-not (Test-Path $RequirementsFile)) {
    Write-ColoredOutput "❌ Requirements file '$RequirementsFile' not found" $Red
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
        Write-ColoredOutput "✅ Dependency validation passed" $Green
        exit 0
    } else {
        Write-ColoredOutput "❌ Dependency validation failed" $Red        exit 1
    }
} catch {
    Write-ColoredOutput "Failed to run validation script: $($_.Exception.Message)" $Red
    exit 1
}
