# 📦 Enhanced Prompt Service - Dependency Management

This document provides comprehensive information about dependency management, security auditing, and version pinning for the Enhanced Prompt Service.

## 🎯 Overview

The Enhanced Prompt Service follows strict dependency management practices to ensure:
- **Reproducible builds** across environments
- **Security compliance** through regular vulnerability audits
- **Version stability** with exact version pinning
- **Automated validation** in CI/CD pipelines

## 📋 Current Dependencies

### Core Framework & Server
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `fastapi` | 0.115.6 | Web framework | Regular security updates |
| `uvicorn[standard]` | 0.32.1 | ASGI server | Includes WebSocket support |

### Data & Validation
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `pydantic` | 2.10.4 | Data validation | Enhanced type safety |
| `redis` | 5.2.1 | Caching & queues | Redis 7+ compatible |

### AI & ML Integration
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `openai` | 1.54.4 | OpenAI API client | Latest stable with enhanced features |
| `weaviate-client` | 4.10.0 | Vector database | Supports latest Weaviate |

### Security & Authentication
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `PyJWT` | 2.10.1 | JWT handling | Latest security fixes |
| `python-jose[cryptography]` | 3.4.0 | JWT/JWS/JWE library | Cryptography backend |

### Utilities & Support
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `requests` | 2.32.4 | HTTP client | Security fix for CVE-2024-47081 |
| `python-dateutil` | 2.9.0 | Date parsing | Stable utility |
| `python-json-logger` | 2.0.7 | Structured logging | JSON log formatting |
| `slowapi` | 0.1.9 | Rate limiting | Request throttling |

### Development & Security Tools
| Package | Version | Purpose | Security Notes |
|---------|---------|---------|----------------|
| `pip-audit` | 2.9.0 | Vulnerability scanning | OSV database integration |

## 🔧 Version Pinning Strategy

### Why Pin Versions?
1. **Reproducible Builds**: Ensures identical dependency versions across environments
2. **Security Control**: Prevents automatic upgrades to potentially vulnerable versions
3. **Stability**: Avoids breaking changes from minor/patch updates
4. **Debugging**: Eliminates version-related issues in production

### Pinning Rules
- ✅ **Use exact versions** (`==2.10.4`) for all dependencies
- ❌ **Avoid range operators** (`>=2.8.0,<3.0.0`) in production
- ✅ **Pin transitive dependencies** when they cause issues
- ✅ **Document version choices** for critical packages

## 🔍 Security Auditing

### Automated Vulnerability Scanning

We use `pip-audit` to scan for known vulnerabilities in our dependencies:

```bash
# Run security audit
python scripts/audit_dependencies.py

# Manual pip-audit execution
pip-audit --format json --progress-spinner off
```

### Audit Schedule
- **CI/CD**: Every build and PR
- **Weekly**: Automated security scan
- **Monthly**: Dependency update review
- **Emergency**: Upon security advisories

### Vulnerability Response Process
1. **Detection**: CI fails or security alert received
2. **Assessment**: Evaluate impact and exploitability
3. **Resolution**: Update to patched version
4. **Testing**: Verify fix doesn't break functionality
5. **Deployment**: Deploy updated dependencies

## 🔧 Local Development

### Setup Instructions

1. **Clone and navigate to service directory**:
   ```bash
   cd enhanced_prompt_service
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Validate requirements before installation**:
   ```bash
   python scripts/validate_requirements.py
   ```

4. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Run security audit**:
   ```bash
   python scripts/audit_dependencies.py
   ```

### Development Workflow

1. **Before making changes**:
   ```bash
   python scripts/validate_requirements.py
   python scripts/audit_dependencies.py
   ```

2. **Adding new dependencies**:
   ```bash
   # Install new package
   pip install package-name==x.y.z
   
   # Add to requirements.txt with exact version
   echo "package-name==x.y.z" >> requirements.txt
   
   # Validate and audit
   python scripts/validate_requirements.py
   python scripts/audit_dependencies.py
   ```

3. **Updating dependencies**:
   ```bash
   # Check for updates (manual research)
   pip list --outdated
   
   # Update specific package
   pip install package-name==new-version
   
   # Update requirements.txt
   # Validate and test thoroughly
   ```

## 🚀 CI/CD Integration

### GitHub Actions Workflow

Our CI pipeline includes comprehensive dependency validation:

```yaml
- name: 🔍 Validate pinned dependencies
  run: python scripts/validate_requirements.py

- name: 📦 Install dependencies
  run: pip install -r requirements.txt

- name: 🔐 Audit dependencies for vulnerabilities
  run: python scripts/audit_dependencies.py
```

### Build Requirements
- All dependencies must be pinned to exact versions
- No known vulnerabilities allowed
- Security audit must pass
- Dependencies must install successfully

## 📊 Dependency Update Strategy

### Regular Updates (Monthly)
1. **Research**: Check for new versions of key dependencies
2. **Testing**: Update in development environment
3. **Validation**: Run full test suite
4. **Security**: Execute vulnerability scan
5. **Documentation**: Update this document

### Security Updates (Immediate)
1. **Alert**: Receive security advisory
2. **Assessment**: Evaluate impact on our service
3. **Update**: Apply security patch immediately
4. **Testing**: Expedited testing process
5. **Deployment**: Emergency deployment if necessary

### Major Version Updates (Quarterly)
1. **Planning**: Schedule major updates during maintenance windows
2. **Testing**: Extensive testing in staging environment
3. **Migration**: Code changes for breaking changes
4. **Rollback**: Prepare rollback strategy
5. **Monitoring**: Enhanced monitoring post-deployment

## 🛠️ Scripts Reference

### validate_requirements.py
```bash
# Validate all dependencies are properly pinned
python scripts/validate_requirements.py

# Returns:
# - Exit code 0: All dependencies properly pinned
# - Exit code 1: Unpinned dependencies found
```

### audit_dependencies.py
```bash
# Run security vulnerability audit
python scripts/audit_dependencies.py

# Returns:
# - Exit code 0: No vulnerabilities found
# - Exit code 1: Vulnerabilities detected or audit failed
```

## 🚨 Troubleshooting

### Common Issues

**Unpinned Dependencies**:
```bash
❌ Unpinned dependency: pydantic (>=2.8.0,<3.0.0)
```
**Solution**: Replace with exact version (`pydantic==2.10.4`)

**Vulnerability Found**:
```bash
❌ Found 1 vulnerabilities:
📦 Package: requests (v2.28.0)
🆔 ID: PYSEC-2023-74
```
**Solution**: Update to patched version

**pip-audit Not Found**:
```bash
❌ pip-audit not found. Please install it with: pip install pip-audit
```
**Solution**: Install pip-audit or use requirements.txt

### Recovery Procedures

**Broken Dependencies**:
1. Revert to last known good requirements.txt
2. Clear pip cache: `pip cache purge`
3. Reinstall: `pip install -r requirements.txt`
4. Validate: `python scripts/validate_requirements.py`

**Security Alert Response**:
1. Identify affected package and version
2. Find patched version from security advisory
3. Update requirements.txt with patched version
4. Test thoroughly in development
5. Deploy with monitoring

## 📞 Support

For dependency-related issues:
1. Check this documentation first
2. Run validation and audit scripts
3. Review CI/CD logs for specific errors
4. Consult security advisories for affected packages
5. Update dependencies following the documented process

## 📝 Changelog

### 2025-06-18 - Initial Implementation
- ✅ Pinned all dependencies to exact versions
- ✅ Upgraded critical packages (OpenAI, FastAPI, etc.)
- ✅ Added automated vulnerability scanning
- ✅ Implemented requirements validation
- ✅ Created comprehensive CI/CD integration
- ✅ Documented dependency management processes
