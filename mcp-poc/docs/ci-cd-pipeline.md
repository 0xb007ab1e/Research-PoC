# Enhanced CI/CD Pipeline Documentation

## Overview

This document describes the enhanced CI/CD pipeline for the MCP (Model Context Protocol) platform. The pipeline implements security-first practices with BuildKit, SBOM generation, comprehensive testing, Cosign image signing, and automated deployment to kind clusters for smoke testing.

## Pipeline Features

### 🏗️ BuildKit + SBOM Generation
- **Docker BuildKit**: All images are built using Docker BuildKit for improved performance and security
- **Multi-platform builds**: Support for `linux/amd64` and `linux/arm64` architectures
- **SBOM Generation**: Software Bill of Materials generated using both Docker BuildKit and Syft
- **Provenance**: Build provenance metadata attached to images
- **Layer caching**: Optimized build caching for faster CI/CD

### 🛡️ Comprehensive Security Testing
- **Unit Tests**: Service-specific unit tests with coverage reporting
- **Integration Tests**: Cross-service integration testing
- **Security Scans**:
  - Python: Bandit (static analysis) + Safety (dependency vulnerabilities)
  - Go: govulncheck for vulnerability scanning
  - Container Images: Trivy for vulnerability scanning
- **Secret Detection**: Trivy secret scanning
- **License Compliance**: License scanning and forbidden license detection

### 🔐 Image Signing with Cosign
- **Keyless Signing**: Uses Sigstore's keyless signing with GitHub OIDC
- **SBOM Signing**: Signs both container images and SBOMs
- **Verification**: Automated signature verification in deployment pipeline
- **Transparency**: Integration with Rekor transparency log

### 🚀 Automated Kind Deployment
- **Local Kubernetes**: Deploys to kind (Kubernetes in Docker) cluster
- **Smoke Tests**: Automated health checks and API testing
- **Service Mesh Ready**: Network policies and security contexts
- **Cleanup**: Automated cluster cleanup after testing

## Pipeline Stages

### 1. Preparation
```yaml
prepare:
  - Matrix strategy setup for multi-service builds
  - Service configuration detection
  - Test command mapping
```

### 2. Testing & Security
```yaml
test:
  - Unit tests (Python pytest, Go test)
  - Security scanning (Bandit, Safety, govulncheck)
  - Code coverage reporting
  - Test artifact upload

integration-test:
  - Cross-service integration tests
  - Database migrations
  - API contract testing
```

### 3. Build & SBOM
```yaml
build:
  - Docker BuildKit setup
  - Multi-platform image builds
  - SBOM generation (SPDX + CycloneDX formats)
  - Container registry push
  - Trivy vulnerability scanning
```

### 4. Signing
```yaml
sign:
  - Cosign keyless signing
  - SBOM artifact signing
  - Transparency log integration
```

### 5. Deployment & Testing
```yaml
deploy-kind:
  - Kind cluster setup
  - PostgreSQL installation
  - Service deployment via Helm
  - Smoke tests execution
  - Signature verification
  - Cleanup
```

### 6. Notification
```yaml
notify:
  - Pipeline status reporting
  - Artifact inventory
  - Security findings summary
```

## Services Configuration

### Text Summarization Service (Python)
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Build**: Multi-stage Dockerfile with distroless runtime
- **Tests**: pytest with coverage
- **Security**: Bandit + Safety

### Context Service (Python)
- **Language**: Python 3.11
- **Framework**: FastAPI/httpx
- **Build**: Slim Python image with non-root user
- **Tests**: pytest
- **Security**: Bandit + Safety

### Auth Service (Go)
- **Language**: Go 1.21
- **Framework**: Custom HTTP server
- **Build**: Distroless static with ko support
- **Tests**: Go test with coverage
- **Security**: govulncheck

## SBOM Management

### Generation Tools
- **Docker BuildKit**: Automatic SBOM generation during build
- **Syft**: Additional SBOM generation in SPDX and CycloneDX formats
- **Ko**: For Go services with integrated SBOM support

### Formats
- **SPDX JSON**: Industry standard format
- **CycloneDX JSON**: OWASP standard for security analysis
- **Attestation**: SLSA provenance and SBOM attestations

### Storage & Signing
- **Artifacts**: Uploaded to GitHub Actions artifacts
- **Registry**: Attached to container images as attestations
- **Signing**: Cosign signs both images and SBOMs
- **Retention**: 90-day retention for compliance

## Security Features

### Image Security
- **Distroless base images**: Minimal attack surface
- **Non-root execution**: Security contexts enforce non-root
- **Read-only filesystems**: Immutable runtime environments
- **Network policies**: Kubernetes network segmentation

### Vulnerability Management
- **Continuous scanning**: Every build includes vulnerability scans
- **Severity thresholds**: Configurable failure thresholds
- **False positive management**: `.trivyignore` for approved exceptions
- **License compliance**: Forbidden license detection

### Supply Chain Security
- **Provenance**: Build provenance with GitHub attestations
- **Signing**: All artifacts signed with Cosign
- **Verification**: Automated signature verification
- **Transparency**: Rekor log integration

## Usage

### Local Development
```bash
# Install dependencies and set up development environment
make local-dev

# Run tests
make test-all

# Build images locally
make build-all

# Run complete CI pipeline locally
make ci-pipeline
```

### Manual Deployment
```bash
# Set up kind cluster
make kind-setup

# Deploy services
make kind-deploy

# Run smoke tests
make kind-test

# Cleanup
make kind-cleanup
```

### Registry Operations
```bash
# Build with SBOM
make build-with-sbom

# Push to registry
make push-all

# Sign images
make sign-all

# Scan for vulnerabilities
make scan-images
```

## Environment Variables

### Required
- `GITHUB_TOKEN`: For registry authentication and Cosign signing
- `REGISTRY`: Container registry (default: ghcr.io)

### Optional
- `VERSION`: Image version tag (default: git commit SHA)
- `BRANCH`: Git branch name (default: current branch)
- `COSIGN_EXPERIMENTAL`: Enable keyless signing (set to 1)

## Configuration Files

### Pipeline Configuration
- `.github/workflows/enhanced-ci-cd.yml`: Main CI/CD workflow
- `Makefile`: Local development and CI operations
- `.ko.yaml`: Ko configuration for Go services

### Security Configuration
- `trivy.yaml`: Trivy vulnerability scanner configuration
- `.trivyignore`: Vulnerability exceptions
- `.secret-scan.yaml`: Secret scanning patterns

### Service Configuration
- `services/*/Dockerfile`: Service-specific build configuration
- `gitops/charts/*`: Helm charts for deployment
- `services/*/helm/*`: Service-specific Helm charts

## Monitoring & Observability

### Metrics
- Build duration and success rates
- Test coverage and pass rates
- Vulnerability counts and severity
- Deployment success rates

### Alerts
- Build failures
- Security threshold breaches
- Deployment failures
- Certificate expiration

### Dashboards
- Pipeline health overview
- Security posture dashboard
- SBOM inventory
- Signature verification status

## Compliance & Governance

### Standards
- **SLSA Level 3**: Build provenance and supply chain security
- **NIST SSDF**: Secure software development framework
- **SPDX 2.3**: Software package data exchange
- **CycloneDX 1.4**: Component analysis and security

### Auditing
- Complete build provenance
- Immutable artifact signing
- Transparency log entries
- Test execution records

### Retention
- Build artifacts: 30 days
- SBOMs: 90 days
- Security scan results: 90 days
- Deployment logs: 30 days

## Troubleshooting

### Common Issues

#### Build Failures
1. Check Dockerfile syntax
2. Verify dependency resolution
3. Review BuildKit logs
4. Check platform compatibility

#### Test Failures
1. Review test logs in artifacts
2. Check service dependencies
3. Verify database migrations
4. Review environment variables

#### Deployment Issues
1. Check kind cluster status
2. Verify image pull policies
3. Review Helm chart values
4. Check service health endpoints

#### Signing Issues
1. Verify GitHub OIDC token
2. Check Cosign installation
3. Review registry permissions
4. Verify keyless signing setup

### Debug Commands
```bash
# Check cluster status
kubectl cluster-info --context kind-mcp-test

# View pipeline logs
kubectl logs -n mcp-system deployment/auth-service

# Check image signatures
cosign verify --certificate-identity=... image:tag

# Inspect SBOM
syft image:tag -o json | jq '.artifacts[] | .name'
```

## Future Enhancements

### Planned Features
- **Multi-environment deployment**: Staging and production pipelines
- **Advanced security**: OPA policy enforcement
- **Performance testing**: Load and performance benchmarks
- **Chaos engineering**: Resilience testing integration
- **GitOps integration**: ArgoCD deployment automation

### Technology Roadmap
- **SLSA Level 4**: Enhanced build isolation
- **gRPC health checks**: Advanced service monitoring
- **Service mesh**: Istio/Linkerd integration
- **Policy as Code**: Open Policy Agent integration
- **Advanced monitoring**: Prometheus/Grafana stack

## Contributing

### Pipeline Changes
1. Test changes locally with `make ci-pipeline`
2. Update documentation
3. Add appropriate tests
4. Submit pull request

### Adding Services
1. Create service-specific Dockerfile
2. Add to build matrix in workflow
3. Create Helm chart
4. Add to Makefile targets
5. Update documentation

### Security Updates
1. Review security scan results
2. Update base images
3. Patch vulnerabilities
4. Update `.trivyignore` if needed
5. Re-scan and verify fixes
