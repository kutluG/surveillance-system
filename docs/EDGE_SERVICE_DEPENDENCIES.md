# Edge Service Dependencies Management

This document outlines the dependency management strategy for the edge service, including security auditing, version pinning, and CI/CD integration.

## Overview

The edge service uses a single, consolidated `requirements.txt` file with pinned versions to ensure:
- **Reproducible builds** across all environments
- **Security compliance** through automated vulnerability scanning
- **Dependency hygiene** enforcement in CI/CD pipelines

## File Structure

```
edge_service/
├── requirements.txt          # Main dependencies file (version-pinned)
├── Dockerfile               # Uses requirements.txt for installation
└── ...

scripts/
├── audit_dependencies.py    # Security vulnerability scanner
└── validate_requirements.py # Version pinning validator
```

## Requirements Management

### Consolidated Requirements File

All Python dependencies for the edge service are consolidated in `edge_service/requirements.txt`. The previous `requirements_edge_service.txt` has been removed to eliminate duplication.

### Version Pinning Strategy

All packages must be pinned to exact versions using the `==` operator:

```
# ✅ Correct - exact version pinning
fastapi==0.104.1
opencv-python==4.8.1.78
paho-mqtt==1.6.1

# ❌ Incorrect - flexible versioning
fastapi>=0.100.0
opencv-python~=4.8.0
requests
```

### Dependencies Categories

The requirements.txt is organized into logical categories:

1. **Core Web Framework**: FastAPI, Uvicorn
2. **Computer Vision**: OpenCV, NumPy, Pillow
3. **Communication**: MQTT, Kafka clients
4. **Monitoring**: Prometheus, OpenTelemetry
5. **Utilities**: Logging, validation, authentication
6. **Security**: pip-audit for vulnerability scanning

## Security Auditing

### Automated Vulnerability Scanning

The `scripts/audit_dependencies.py` script performs automated security auditing:

```bash
# Run security audit locally
python scripts/audit_dependencies.py
```

**Features:**
- Uses `pip-audit` to check for known vulnerabilities
- Fails build on any detected vulnerabilities
- Provides clear output with remediation guidance
- 5-minute timeout to prevent hanging builds

**Example Output:**
```
🔍 Running security audit on Python dependencies...
📋 Audit Results:
No known vulnerabilities found
✅ Security audit passed - no vulnerabilities found!
```

### Vulnerability Response Process

When vulnerabilities are detected:

1. **Immediate Action**: CI build fails, preventing deployment
2. **Assessment**: Review vulnerability details and impact
3. **Resolution**: Update to patched version or find alternative
4. **Verification**: Re-run audit to confirm fix

## Requirements Validation

### Version Pinning Validation

The `scripts/validate_requirements.py` script ensures all dependencies are properly pinned:

```bash
# Validate all requirements files
python scripts/validate_requirements.py

# Validate specific file
python scripts/validate_requirements.py edge_service/requirements.txt
```

**Validation Rules:**
- All packages must use exact version pinning (`==`)
- No unpinned dependencies allowed
- No flexible versioning (`>=`, `~=`, etc.)
- Empty version specifications are rejected

**Example Output:**
```
🔍 Validating Python dependency version pinning...
📁 Found 1 requirements files to check

📋 Checking edge_service/requirements.txt...
✅ All dependencies in requirements.txt are properly pinned

✅ All dependencies are properly pinned!
🎉 Reproducible builds ensured!
```

## CI/CD Integration

### Pipeline Steps

The CI pipeline includes dependency validation and security checks:

```yaml
- name: Validate pinned dependencies
  run: python scripts/validate_requirements.py

- name: Install Python dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt

- name: Audit dependencies for vulnerabilities
  run: python scripts/audit_dependencies.py
```

### Build Process

1. **Validation**: Check that all dependencies are properly pinned
2. **Installation**: Install exact versions from requirements.txt
3. **Security Audit**: Scan for known vulnerabilities
4. **Continue**: Proceed with linting, testing, and deployment

### Failure Scenarios

The build fails and stops deployment if:
- Any dependencies are not version-pinned
- Security vulnerabilities are detected
- pip-audit tool fails or times out

## Local Development

### Setting Up Dependencies

```bash
# Install dependencies for development
pip install -r edge_service/requirements.txt

# Validate your requirements
python scripts/validate_requirements.py

# Run security audit
python scripts/audit_dependencies.py
```

### Adding New Dependencies

When adding new packages:

1. **Pin the Version**: Always specify exact version (`==`)
2. **Categorize**: Add to appropriate section in requirements.txt
3. **Validate**: Run validation script to ensure compliance
4. **Audit**: Check for security vulnerabilities
5. **Test**: Verify the dependency works as expected

Example:
```bash
# Add new dependency with exact version
echo "new-package==1.2.3" >> edge_service/requirements.txt

# Validate the change
python scripts/validate_requirements.py

# Check for vulnerabilities
python scripts/audit_dependencies.py
```

### Updating Dependencies

To update dependencies safely:

1. **Research**: Check changelog and breaking changes
2. **Update**: Modify version in requirements.txt
3. **Test**: Run local tests to ensure compatibility
4. **Validate**: Run validation and audit scripts
5. **Commit**: Submit changes through normal PR process

```bash
# Example update process
sed -i 's/fastapi==0.104.1/fastapi==0.105.0/' edge_service/requirements.txt
python scripts/validate_requirements.py
python scripts/audit_dependencies.py
pip install -r edge_service/requirements.txt
# Run tests...
```

## Docker Integration

The edge service Dockerfile uses the consolidated requirements.txt:

```dockerfile
# Copy and install requirements
COPY edge_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

This ensures that the same pinned versions used in CI are deployed to production.

## Best Practices

### Dependency Management

1. **Always Pin Versions**: Use exact versions (`==`) for all packages
2. **Regular Updates**: Schedule regular dependency updates
3. **Security First**: Run audits before and after updates
4. **Test Thoroughly**: Validate functionality after version changes
5. **Document Changes**: Update this file when changing strategy

### Development Workflow

1. **Before Coding**: Ensure local environment matches requirements
2. **Adding Dependencies**: Follow the documented process
3. **Before Committing**: Run validation and audit scripts locally
4. **PR Reviews**: Include dependency changes in code review

### Production Deployment

1. **Verified Builds**: Only deploy if CI passes all checks
2. **Container Scanning**: Additional security scanning in deployment pipeline
3. **Rollback Plan**: Be prepared to revert problematic updates
4. **Monitoring**: Watch for runtime issues after updates

## Troubleshooting

### Common Issues

**Unpinned Dependency Error:**
```
❌ Found 1 unpinned dependencies:
   • Line 15: requests (no version specified)
```
*Solution*: Add exact version: `requests==2.31.0`

**Security Vulnerability Detected:**
```
❌ Security vulnerabilities detected!
Found 1 known vulnerability in 1 package
```
*Solution*: Update to patched version or find secure alternative

**pip-audit Not Found:**
```
❌ pip-audit not found. Please install it with: pip install pip-audit>=2.6.0
```
*Solution*: Install pip-audit or ensure it's in requirements.txt

### Getting Help

1. **Check Logs**: Review full CI output for detailed error messages
2. **Local Testing**: Reproduce issues locally before debugging
3. **Documentation**: Refer to pip-audit and dependency documentation
4. **Team Support**: Consult with team for complex dependency conflicts

## Future Improvements

### Planned Enhancements

1. **Automated Updates**: Implement dependabot or similar for version updates
2. **License Scanning**: Add license compliance checking
3. **Performance Monitoring**: Track dependency impact on build times
4. **Advanced Reporting**: Generate detailed security and compliance reports

### Monitoring and Metrics

1. **Build Time**: Track impact of dependency changes on CI duration
2. **Security Score**: Monitor vulnerability count over time
3. **Update Frequency**: Track how often dependencies are updated
4. **Failure Rate**: Monitor CI failure rate due to dependency issues
