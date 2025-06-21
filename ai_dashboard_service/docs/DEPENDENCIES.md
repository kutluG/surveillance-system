# AI Dashboard Service Dependencies

This document describes the dependency management approach for the AI Dashboard Service, including pinned versions, validation processes, and security auditing.

## Pinned Dependencies

All dependencies are pinned to specific versions to ensure reproducible builds across environments. The following packages are currently pinned:

### Core Framework
- **fastapi==0.115.12**: Latest stable version with improved performance and security
- **uvicorn[standard]==0.32.1**: ASGI server with WebSocket and HTTP/2 support
- **pydantic==2.10.4**: Data validation with improved type checking
- **pydantic-settings==2.7.0**: Configuration management
- **python-multipart==0.0.9**: File upload support

### Rate Limiting & Caching
- **slowapi==0.1.9**: FastAPI-compatible rate limiting
- **redis==5.2.1**: In-memory data store for caching and rate limiting

### HTTP Client
- **httpx==0.28.1**: Async HTTP client for service-to-service communication

### AI/ML
- **openai==1.54.4**: Latest OpenAI API client with enhanced features
- **numpy==1.26.4**: Scientific computing library

### Database
- **sqlalchemy[asyncio]==2.0.36**: Async ORM with PostgreSQL support
- **asyncpg==0.30.0**: Fast PostgreSQL driver for asyncio

### Security & Monitoring
- **pip-audit==2.9.0**: Vulnerability scanning for dependencies
- **python-json-logger==2.0.7**: Structured logging
- **PyJWT==2.8.0**: JSON Web Token implementation

### Shared Dependencies
The service uses the local `shared` package for common middleware and utilities:
- Rate limiting middleware
- Audit logging
- Authentication helpers
- Metrics collection

## Version Pinning Rationale

### FastAPI (0.115.12)
- Latest stable release with security improvements
- Enhanced WebSocket support
- Better OpenAPI documentation generation
- Improved dependency injection

### OpenAI (1.54.4)
- Latest API client with function calling improvements
- Better error handling and retry logic
- Support for new model versions
- Enhanced streaming capabilities

### Pydantic (2.10.4)
- Significant performance improvements over v1
- Better type hint support
- Enhanced validation error messages
- Improved serialization

### SQLAlchemy (2.0.36)
- Modern async/await support
- Better type checking with mypy
- Improved performance
- Enhanced relationship loading

## Validation Process

### Dependency Pinning Validation
Run the validation script to ensure all dependencies are properly pinned:

```bash
cd ai_dashboard_service
python scripts/validate_requirements.py
```

This script:
- Checks all `requirements*.txt` files
- Ensures all packages use `==` version pinning
- Reports any unpinned or loosely pinned dependencies
- Exits with code 1 if validation fails

### Security Audit
Run the security audit to check for known vulnerabilities:

```bash
cd ai_dashboard_service
python scripts/audit_dependencies.py
```

This script:
- Uses `pip-audit` to scan for known vulnerabilities
- Checks against the PyPA Advisory Database
- Reports any vulnerable packages
- Exits with code 1 if vulnerabilities are found
## CI/CD Integration

The dependency validation and security audit are integrated into the GitHub Actions workflow:

```yaml
- name: Validate pinned dependencies
  run: |
    cd ai_dashboard_service
    python scripts/validate_requirements.py

- name: Install dependencies
  run: |
    cd ai_dashboard_service
    python -m pip install --upgrade pip
    pip install -r requirements.txt

- name: Audit dependencies for vulnerabilities
  run: |
    cd ai_dashboard_service
    python scripts/audit_dependencies.py

- name: Check for unused imports
  run: |
    cd ai_dashboard_service
    pip install unimport
    unimport --check --diff app/
```

## Local Development

### Setting up the environment
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Validate the installation:
   ```bash
   python scripts/validate_requirements.py
   python scripts/audit_dependencies.py
   ```

### Adding new dependencies
1. Add the new package with a pinned version to `requirements.txt`
2. Run validation: `python scripts/validate_requirements.py`
3. Run security audit: `python scripts/audit_dependencies.py`
4. Test the application to ensure compatibility
5. Update this documentation if needed

### Upgrading dependencies
1. Research the new version for breaking changes
2. Update the pinned version in `requirements.txt`
3. Run validation and security audit
4. Run the full test suite
5. Update documentation with rationale for the upgrade

## Troubleshooting

### Validation Failures
- **Unpinned dependencies**: Ensure all packages use `==` syntax
- **Missing dependencies**: Check that all imports have corresponding entries
- **File not found**: Ensure you're running from the correct directory

### Security Audit Failures
- **Vulnerabilities found**: Upgrade affected packages to secure versions
- **pip-audit not found**: Install with `pip install pip-audit>=2.7.0`
- **Network issues**: Ensure internet connectivity for vulnerability database

### Import Issues
- **Unused imports**: Remove unused imports flagged by `unimport`
- **Missing imports**: Add missing packages to `requirements.txt`
- **Version conflicts**: Check for compatible version ranges

## Maintenance Schedule

- **Weekly**: Run security audits to check for new vulnerabilities
- **Monthly**: Review for available updates to pinned versions
- **Quarterly**: Major version updates and dependency review
- **As needed**: Security patches and critical bug fixes

## Contact

For questions about dependency management or security issues, contact the development team or file an issue in the project repository.

---

**Last Updated:** June 19, 2025  
**Next Review:** July 19, 2025
