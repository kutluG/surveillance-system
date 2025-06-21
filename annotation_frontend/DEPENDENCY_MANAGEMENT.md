# Dependency Management Guide

## Overview

This guide covers the dependency management system implemented for the Annotation Frontend Service, including version pinning, validation, and security checks.

## 🎯 Objectives

- **Reproducible Builds**: All critical dependencies are pinned to specific versions
- **Security**: Regular checks for known vulnerabilities
- **Quality**: Validation prevents unpinned or duplicate dependencies
- **Automation**: CI/CD integration ensures consistent validation

## 📦 Pinned Dependencies

All critical dependencies are pinned to specific versions in `requirements.txt`:

```txt
# Core web framework and ASGI server
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Rate limiting
slowapi==0.1.9

# Data validation and settings
pydantic==2.11.5
pydantic-settings==2.1.0

# Authentication and security
PyJWT==2.8.0
python-jose[cryptography]==3.3.0

# ... (see requirements.txt for complete list)
```

## 🔧 Tools and Scripts

### 1. Dependency Validator (`validate_dependencies.py`)

Main validation script that checks:
- ✅ Version pinning for critical packages
- ✅ Duplicate dependencies
- ✅ Semantic versioning compliance
- ✅ Security vulnerabilities (with pip-audit)

**Usage:**
```bash
# Basic validation
python validate_dependencies.py

# Strict mode (warnings as errors)
python validate_dependencies.py --strict

# Include security check
python validate_dependencies.py --check-security

# Generate lock file
python validate_dependencies.py --generate-lock
```

### 2. CI/CD Scripts

- **PowerShell**: `ci_validate_deps_fixed.ps1` (Windows)
- **Bash**: `ci_validate_deps.sh` (Linux/macOS)
- **GitHub Actions**: `.github_workflows_dependency-validation.yml`

### 3. Pre-commit Hook (`pre-commit-hook.py`)

Automatically validates dependencies before commits:
```bash
# Setup
cp pre-commit-hook.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Or use make
make pre-commit-setup
```

### 4. Makefile Commands

Convenient commands for dependency management:
```bash
make help              # Show all available commands
make install           # Install production dependencies
make install-dev       # Install dev dependencies + security tools
make validate-deps     # Basic validation
make validate-strict   # Strict validation
make check-security    # Security vulnerability check
make generate-lock     # Generate requirements.lock
make ci-validate       # Full CI pipeline
```

## 🔍 Validation Rules

### Critical Packages (Must be pinned with `==`)
- `fastapi`
- `uvicorn`
- `pydantic`
- `confluent-kafka`
- `python-jose`
- `pyjwt`
- `structlog`
- `pytest`

### Allowed Version Ranges
Limited packages that can use version ranges:
- `python-json-logger` (for compatibility)
- `prometheus_client` (for compatibility)

### Validation Checks
1. **Pinning Check**: Critical packages must use exact pinning (`==`)
2. **Duplicate Check**: No duplicate package entries
3. **Format Check**: Versions should follow semantic versioning
4. **Security Check**: No known vulnerabilities (requires pip-audit)

## 🚀 CI/CD Integration

### GitHub Actions Workflow

The workflow runs on:
- Push to `main` or `develop` branches
- Pull requests affecting requirements files
- Manual triggers

**Features:**
- ✅ Multi-Python version testing (3.11, 3.12)
- ✅ Multi-service validation
- ✅ Security audit with pip-audit
- ✅ Lock file generation
- ✅ Artifact upload for lock files

### Validation Matrix

| Service | Python 3.11 | Python 3.12 | Security Check |
|---------|:------------:|:------------:|:--------------:|
| annotation_frontend | ✅ | ✅ | ✅ |
| advanced_rag_service | ✅ | ✅ | ✅ |
| agent_orchestrator | ✅ | ✅ | ✅ |
| edge_service | ✅ | ✅ | ✅ |

## 🔒 Security Features

### 1. Vulnerability Scanning
- **pip-audit**: Checks against PyPI Advisory Database
- **safety**: Additional vulnerability database
- **bandit**: Static security analysis

### 2. Security Workflow
```bash
# Install security tools
make install-dev

# Run security check
make check-security

# Full security audit (CI)
python validate_dependencies.py --check-security
```

### 3. Security Reporting
- JSON format vulnerability reports
- Integration with GitHub Security tab
- Automated issue creation for vulnerabilities

## 📋 Best Practices

### 1. Updating Dependencies

**Safe Update Process:**
1. Test in development environment
2. Update one dependency at a time
3. Run full test suite
4. Validate with strict mode
5. Check for security issues

```bash
# Update workflow
pip install package==new_version
make validate-strict
make test
make check-security
```

### 2. New Dependencies

**Adding New Dependencies:**
1. Pin to specific version
2. Classify as critical or non-critical
3. Update validation rules if needed
4. Document the decision

```bash
# Add new dependency
echo "new-package==1.2.3" >> requirements.txt
make validate-strict
```

### 3. Emergency Updates

**Security Patches:**
1. Immediate update to patched version
2. Test critical functionality
3. Deploy with monitoring
4. Full test suite post-deployment

## 🐛 Troubleshooting

### Common Issues

**1. Validation Fails - Unpinned Package**
```
Error: Package 'fastapi' is not pinned to a specific version
```
**Solution:** Pin to specific version: `fastapi==0.104.1`

**2. Security Vulnerability Found**
```
Security vulnerability CVE-2023-xxxx found in package 1.0.0
```
**Solution:** Update to patched version or find alternative

**3. Duplicate Package Error**
```
Duplicate package 'requests' (also on line 15)
```
**Solution:** Remove duplicate entry from requirements.txt

### Debug Commands

```bash
# Check current versions
pip list | grep package-name

# Validate specific file
python validate_dependencies.py --requirements custom-requirements.txt

# Generate detailed report
python validate_dependencies.py --check-security --generate-lock
```

## 📊 Monitoring

### Metrics to Track
- ✅ Number of pinned vs unpinned dependencies
- ✅ Security vulnerabilities found/fixed
- ✅ Validation success rate in CI
- ✅ Time since last dependency update

### Alerts
- 🚨 New security vulnerability detected
- ⚠️ Validation failure in CI
- 📅 Dependencies not updated in 30+ days

## 🔮 Future Enhancements

### Planned Features
1. **Automated Dependency Updates**: Bot for safe updates
2. **Dependency Graph Analysis**: Visualize dependency relationships
3. **License Compliance**: Check dependency licenses
4. **Performance Impact**: Monitor dependency load times
5. **AI-Powered Updates**: ML-based safe update suggestions

### Integration Opportunities
1. **Slack/Teams Notifications**: Real-time alerts
2. **JIRA Integration**: Automatic ticket creation
3. **Grafana Dashboards**: Dependency health metrics
4. **SonarQube Integration**: Code quality + dependency security

## 📚 References

- [Python Packaging User Guide](https://packaging.python.org/)
- [pip-audit Documentation](https://pypi.org/project/pip-audit/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Hooks](https://pre-commit.com/)
