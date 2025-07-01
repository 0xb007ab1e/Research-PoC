# Dependency Management

⬅️ **[Back to Main Documentation](./README.md)**

This document outlines the dependency management strategy implemented for the MCP POC project, including dependency freezing, harmonization, and security vulnerability scanning.

> 📖 **See Also:** [Main README](./README.md) • [Local Development](./LOCAL_DEVELOPMENT.md) • [CI/CD Pipeline](./README-CICD.md)

## Overview

We use a two-tier approach for dependency management:
- **requirements.in**: High-level dependencies without version pins
- **requirements.lock**: Locked dependencies with exact versions for reproducible builds

## Structure

```
├── services/
│   ├── context-service/
│   │   ├── requirements.in      # High-level dependencies
│   │   ├── requirements.lock    # Locked dependencies (generated)
│   │   └── requirements.txt     # Legacy pinned requirements (kept for reference)
│   └── text-summarization/
│       ├── requirements.in      # High-level dependencies
│       ├── requirements.lock    # Locked dependencies (generated)
│       └── requirements.txt     # Legacy pinned requirements (kept for reference)
├── tests/
│   ├── requirements.in          # Test dependencies
│   └── requirements.lock        # Locked test dependencies (generated)
└── scripts/
    └── update-deps.sh           # Utility script to update all lock files
```

## Tools Used

- **pip-tools**: For generating locked requirements from high-level dependencies
- **Safety**: For scanning dependencies for known security vulnerabilities
- **Bandit**: For static security analysis of Python code

## Workflow

### 1. Adding New Dependencies

When adding a new dependency:

1. Add it to the appropriate `requirements.in` file without version pinning:
   ```ini
   # Add new dependency
   fastapi
   ```

2. Regenerate the lock file:
   ```bash
   ./scripts/update-deps.sh
   ```

3. Test your application with the new dependencies
4. Commit both `requirements.in` and `requirements.lock` files

### 2. Updating Dependencies

To update all dependencies to their latest compatible versions:

```bash
./scripts/update-deps.sh
```

This script:
- Updates all `requirements.lock` files from their respective `requirements.in` files
- Uses the `--upgrade` flag to get the latest compatible versions
- Maintains dependency resolution across all services

### 3. Security Scanning

Security vulnerability scanning is integrated into the CI/CD pipeline and can be run manually:

#### Using Safety (Dependency Vulnerabilities)
```bash
# Install dependencies first
pip install -r requirements.lock

# Scan for vulnerabilities
safety check
```

#### Using Bandit (Code Security)
```bash
# Install bandit
pip install bandit

# Run security scan
bandit -r . -f json -o bandit-report.json
```

## CI/CD Integration

The CI workflows have been updated to:

1. **Use Lock Files**: Install dependencies from `requirements.lock` when available
2. **Cache Optimization**: Include lock files in cache keys for better invalidation
3. **Security Gates**: Run Safety and Bandit scans as part of the pipeline
4. **Fail Fast**: Stop builds if critical security vulnerabilities are found

### Cache Strategy

Dependencies are cached using both `requirements.lock` and `requirements.txt` files as cache keys:

```yaml
key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.lock', '**/requirements.txt') }}
```

## Security Vulnerability Management

### Automated Scanning

1. **Safety**: Scans for known vulnerabilities in dependencies
   - Runs on every CI build
   - Reports uploaded as artifacts
   - Configurable to fail builds on critical vulnerabilities

2. **Bandit**: Static analysis for common security issues
   - Scans Python code for security anti-patterns
   - Integrated into the security-scan job
   - Results uploaded to GitHub Security tab

### Manual Security Review

For manual security reviews:

```bash
# Check for outdated packages
pip list --outdated

# Scan with Safety
safety check --json --output safety-report.json

# Scan with Bandit  
bandit -r . -f txt
```

## Best Practices

### Dependency Management
1. **Pin in Lock Files Only**: Keep `requirements.in` files unpinned for flexibility
2. **Regular Updates**: Run `./scripts/update-deps.sh` weekly
3. **Test After Updates**: Always test applications after dependency updates
4. **Version Control**: Commit both `.in` and `.lock` files

### Security
1. **Monitor Vulnerabilities**: Review Safety reports in CI
2. **Update Promptly**: Address security vulnerabilities quickly
3. **Principle of Least Privilege**: Only include necessary dependencies
4. **Review New Dependencies**: Audit new packages before adding

### CI/CD
1. **Reproducible Builds**: Always use lock files in production builds
2. **Cache Efficiency**: Include lock files in cache keys
3. **Fail Fast**: Configure security scans to fail builds on critical issues
4. **Artifact Retention**: Keep security reports for compliance

## Troubleshooting

### Common Issues

1. **Dependency Conflicts**
   ```bash
   # Clear virtual environment and regenerate
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install pip-tools
   ./scripts/update-deps.sh
   ```

2. **Security Scan Failures**
   ```bash
   # Check specific vulnerability
   safety check --json | jq '.vulnerabilities[]'
   
   # Update specific package
   # Edit requirements.in to pin safe version
   # Regenerate lock file
   ```

3. **Cache Issues**
   ```bash
   # Clear pip cache
   pip cache purge
   
   # Clear GitHub Actions cache via UI or API
   ```

## Files Reference

- `requirements.in`: High-level dependencies without versions
- `requirements.lock`: Exact versions for reproducible builds  
- `scripts/update-deps.sh`: Updates all lock files
- `.github/workflows/`: CI configuration with security scanning
- `DEPENDENCY-MANAGEMENT.md`: This documentation

## Dependencies Overview

### Core Services
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server  
- **Pydantic**: Data validation
- **SQLAlchemy**: Database ORM
- **AsyncPG**: Async PostgreSQL driver

### Security & Auth
- **python-jose**: JWT handling
- **passlib**: Password hashing
- **cryptography**: Cryptographic operations

### AI/ML (text-summarization)
- **OpenAI**: AI service integration
- **transformers**: Hugging Face transformers
- **torch**: PyTorch framework
- **sentence-transformers**: Sentence embeddings

### Observability
- **structlog**: Structured logging
- **prometheus-client**: Metrics
- **opentelemetry-**: Distributed tracing

### Security Tools
- **safety**: Dependency vulnerability scanning
- **bandit**: Static security analysis

### Testing
- **pytest**: Testing framework
- **pytest-asyncio**: Async testing
- **testcontainers**: Docker-based testing
- **locust**: Load testing
