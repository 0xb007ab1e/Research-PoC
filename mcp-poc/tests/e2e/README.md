# End-to-End Workflow Tests

This directory contains comprehensive end-to-end tests that validate the complete MCP workflow.

## Test Workflow

The `test_workflow.py` script performs the following validation:

1. **Stack Startup**: Starts the complete development stack using `docker-compose.dev.yml`
2. **Authentication Flow**: 
   - Obtains OAuth2.1 authorization code from auth-service (bypassing browser)
   - Exchanges code for JWT access token using PKCE flow
3. **Context Creation**: Creates context data via context-service with JWT + tenant headers
4. **Text Summarization**: Processes text through text-summarization service
5. **Cleanup**: Stops and removes all containers

## Requirements

- Docker and docker-compose installed
- All service certificates generated in `certs/docker/`
- Python 3.11+ with required dependencies
- Network access to localhost ports 8000, 8001, 8443

## Usage

### Standalone Execution
```bash
# Run directly from project root
python tests/e2e/test_workflow.py

# Or make it executable and run
chmod +x tests/e2e/test_workflow.py
./tests/e2e/test_workflow.py
```

### Via Makefile
```bash
# Run as part of comprehensive test suite
make test-all
```

### Via Pytest
```bash
# Run with pytest
pytest tests/e2e/test_workflow.py -v
```

## Test Configuration

The test uses the following configuration:

- **Tenant ID**: `test-tenant-e2e`
- **User ID**: `test-user-e2e`
- **Client ID**: `demo-client` (from auth-service config)
- **Redirect URI**: `http://localhost:3000/callback`
- **Semantic Threshold**: 0.75
- **Startup Timeout**: 180 seconds

## Certificate Requirements

The test requires mTLS certificates to be available:

```
certs/docker/
├── auth-service/
│   ├── ca-cert.pem
│   ├── server-cert.pem
│   └── server-key.pem
├── context-service/
│   ├── ca-cert.pem
│   ├── server-cert.pem
│   └── server-key.pem
└── text-summarization/
    ├── ca-cert.pem
    ├── server-cert.pem
    └── server-key.pem
```

## Exit Codes

- **0**: All tests passed successfully
- **1**: One or more tests failed
- **Non-zero**: System error or startup failure

## Troubleshooting

### Common Issues

1. **Certificate not found**: Ensure certificates are generated using the cert generation scripts
2. **Services not healthy**: Check docker-compose logs for service startup issues
3. **Port conflicts**: Ensure ports 8000, 8001, 8443, 5432, 8200, 6379 are available
4. **Network issues**: Verify Docker network `mcp-development` is created

### Debug Mode

For detailed debugging, modify the test to enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Manual Service Testing

Test individual services:

```bash
# Start stack
docker-compose -f docker-compose.dev.yml up -d

# Test auth service health
curl -k --cert certs/docker/auth-service/server-cert.pem \
     --key certs/docker/auth-service/server-key.pem \
     --cacert certs/docker/auth-service/ca-cert.pem \
     https://localhost:8443/health

# Test context service health  
curl -k --cert certs/docker/context-service/server-cert.pem \
     --key certs/docker/context-service/server-key.pem \
     --cacert certs/docker/context-service/ca-cert.pem \
     https://localhost:8001/healthz

# Test text summarization health
curl -k --cert certs/docker/text-summarization/server-cert.pem \
     --key certs/docker/text-summarization/server-key.pem \
     --cacert certs/docker/text-summarization/ca-cert.pem \
     https://localhost:8000/healthz
```

## Integration with CI/CD

This test is automatically integrated into the `make test-all` target and runs after unit tests but before any deployment tests. It validates that:

- All services can start and achieve healthy status
- OAuth2.1 authentication flow works end-to-end
- Service-to-service communication via mTLS works
- Database operations work correctly
- AI/ML processing pipeline functions
- Error handling and edge cases are covered

The test is designed to be deterministic and can be safely run in CI/CD environments.
