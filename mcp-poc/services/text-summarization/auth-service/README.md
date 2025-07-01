# Auth Service

A production-ready OAuth2.1 authorization server with PKCE support, JWT signing via HashiCorp Vault, and comprehensive observability.

## Features

- **OAuth2.1 with PKCE**: Full OAuth2.1 implementation with mandatory PKCE support
- **JWT Signing**: RS256 JWT signing using HashiCorp Vault Transit Secrets Engine
- **Key Rotation**: Automatic 24-hour key rotation via Vault
- **mTLS Support**: Mutual TLS for secure service-to-service communication
- **Prometheus Metrics**: Comprehensive metrics for monitoring and alerting
- **Distroless Container**: Minimal attack surface with distroless static image
- **Health Checks**: Built-in health check endpoints
- **Graceful Shutdown**: Proper signal handling and graceful shutdown

## Endpoints

### OAuth2.1 Endpoints

- `GET /authorize` - OAuth2.1 authorization endpoint
- `POST /token` - OAuth2.1 token endpoint
- `GET /.well-known/jwks.json` - JSON Web Key Set endpoint

### Internal Endpoints

- `POST /introspect` - Token introspection (requires mTLS or Bearer auth)
- `GET /health` - Health check endpoint
- `GET /metrics` - Prometheus metrics endpoint

## Quick Start

### Using Docker Compose

1. Clone the repository and navigate to the auth-service directory
2. Start the services:

```bash
docker-compose up -d
```

This will start:
- HashiCorp Vault (dev mode)
- Auth Service
- Prometheus (for monitoring)

### Manual Setup

1. **Start Vault** (in dev mode for testing):

```bash
vault server -dev -dev-listen-address=0.0.0.0:8200
```

2. **Initialize Vault Transit Engine**:

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token

vault secrets enable transit
vault write -f transit/keys/jwt-signing-key type=rsa-2048
```

3. **Build and run the service**:

```bash
go mod tidy
go build -o auth-service ./cmd/server
./auth-service
```

## Configuration

The service is configured via environment variables:

### Server Configuration

- `SERVER_PORT` - Server port (default: 8443)
- `TLS_CERT_FILE` - TLS certificate file for HTTPS/mTLS
- `TLS_KEY_FILE` - TLS private key file
- `SERVER_READ_TIMEOUT` - Read timeout (default: 30s)
- `SERVER_WRITE_TIMEOUT` - Write timeout (default: 30s)

### Vault Configuration

- `VAULT_ADDR` - Vault server address (default: http://localhost:8200)
- `VAULT_TOKEN` - Vault authentication token
- `VAULT_TRANSIT_KEY` - Transit key name (default: jwt-signing-key)

### JWT Configuration

- `JWT_ISSUER` - JWT issuer claim (default: https://auth-service)
- `JWT_AUDIENCE` - JWT audience claim (default: api)
- `JWT_TOKEN_EXPIRATION` - Access token expiration (default: 24h)
- `JWT_REFRESH_TOKEN_TTL` - Refresh token TTL (default: 168h)
- `JWT_KEY_ROTATION_INTERVAL` - Key rotation interval (default: 24h)

### OAuth Configuration

- `OAUTH_CLIENT_ID` - OAuth client ID (default: default-client)
- `OAUTH_REDIRECT_URI` - Allowed redirect URI
- `OAUTH_CODE_EXPIRATION` - Authorization code expiration (default: 10m)
- `OAUTH_PKCE_REQUIRED` - Require PKCE (default: true)

## OAuth2.1 Flow Example

### 1. Authorization Request

```bash
curl "http://localhost:8443/authorize?response_type=code&client_id=demo-client&redirect_uri=http://localhost:3000/callback&scope=openid+profile&state=xyz&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256"
```

### 2. Token Exchange

```bash
curl -X POST http://localhost:8443/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=AUTHORIZATION_CODE&redirect_uri=http://localhost:3000/callback&client_id=demo-client&code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
```

### 3. Token Introspection

```bash
curl -X POST http://localhost:8443/introspect \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "token=JWT_TOKEN_TO_INTROSPECT"
```

### 4. JWKS Endpoint

```bash
curl http://localhost:8443/.well-known/jwks.json
```

## PKCE Example

### Generate Code Verifier and Challenge

```python
import base64
import hashlib
import secrets

# Generate code verifier
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

# Generate code challenge
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('utf-8')).digest()
).decode('utf-8').rstrip('=')

print(f"Code Verifier: {code_verifier}")
print(f"Code Challenge: {code_challenge}")
```

## Testing

Run the unit tests:

```bash
go test ./...
```

Run tests with coverage:

```bash
go test -cover ./...
```

## Monitoring

### Prometheus Metrics

The service exposes metrics at `/metrics`:

- `auth_service_http_requests_total` - Total HTTP requests
- `auth_service_http_request_duration_seconds` - Request duration
- `auth_service_authorization_requests_total` - OAuth authorization requests
- `auth_service_token_requests_total` - OAuth token requests
- `auth_service_jwt_tokens_generated_total` - JWT tokens generated
- `auth_service_vault_operations_total` - Vault operations
- `auth_service_key_cache_hits_total` - Key cache hits
- `auth_service_active_authorization_codes` - Active authorization codes
- `auth_service_key_rotations_total` - Key rotations

### Health Checks

Health check endpoint: `GET /health`

Returns:
```json
{
  "status": "healthy",
  "service": "auth-service"
}
```

## Security Features

### mTLS Support

Configure mTLS by setting:
- `TLS_CERT_FILE` - Server certificate
- `TLS_KEY_FILE` - Server private key
- `CA_CERT_FILE` - CA certificate for client verification

### Security Headers

The service automatically adds security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`

### JWT Security

- RS256 signing algorithm
- Key rotation every 24 hours
- Secure key storage in Vault
- Short-lived access tokens (24h default)
- Longer-lived refresh tokens (7 days default)

## Production Deployment

### Container Image

Build the distroless container:

```bash
docker build -t auth-service:latest .
```

### Kubernetes Deployment

Example Kubernetes manifests:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: auth-service:latest
        ports:
        - containerPort: 8443
        env:
        - name: VAULT_ADDR
          value: "https://vault.internal"
        - name: VAULT_TOKEN
          valueFrom:
            secretKeyRef:
              name: vault-token
              key: token
        livenessProbe:
          httpGet:
            path: /health
            port: 8443
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8443
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Vault Production Setup

For production, use Vault with proper authentication:

1. Enable Kubernetes auth method
2. Create service account and role
3. Use Vault Agent for token renewal

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OAuth Client  │    │   Auth Service  │    │  HashiCorp Vault│
│                 │    │                 │    │                 │
│                 │◄──►│                 │◄──►│ Transit Engine  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Prometheus    │
                       │    Metrics      │
                       └─────────────────┘
```

## Development

### Project Structure

```
auth-service/
├── cmd/server/          # Main application
├── internal/
│   ├── config/         # Configuration
│   ├── handlers/       # HTTP handlers
│   ├── middleware/     # HTTP middleware
│   ├── models/         # Data models
│   └── services/       # Business logic
├── pkg/
│   ├── vault/          # Vault client
│   └── metrics/        # Prometheus metrics
├── tests/              # Unit tests
├── Dockerfile          # Container image
├── docker-compose.yml  # Development setup
└── README.md
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License.
