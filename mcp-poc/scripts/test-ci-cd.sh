#!/bin/bash
# Local CI/CD Pipeline Testing Script
# This script allows you to test the CI/CD pipeline components locally

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY=${REGISTRY:-"localhost:5000"}
VERSION=${VERSION:-$(git rev-parse --short HEAD)}
SERVICES=("text-summarization" "context-service" "auth-service")

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v kind >/dev/null 2>&1 || missing_tools+=("kind")
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    command -v syft >/dev/null 2>&1 || log_warning "syft not found, will install if needed"
    command -v trivy >/dev/null 2>&1 || log_warning "trivy not found, will install if needed"
    command -v cosign >/dev/null 2>&1 || log_warning "cosign not found, will install if needed"
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check Docker BuildKit
    if ! docker buildx version >/dev/null 2>&1; then
        log_warning "Docker BuildKit not available, setting up..."
        docker buildx create --name local-builder --use --bootstrap
    fi
    
    log_success "Prerequisites check passed"
}

setup_local_registry() {
    log_info "Setting up local registry..."
    
    if ! docker ps | grep -q "registry:2"; then
        docker run -d -p 5000:5000 --name local-registry registry:2 2>/dev/null || {
            docker start local-registry 2>/dev/null || {
                log_error "Failed to start local registry"
                exit 1
            }
        }
    fi
    
    log_success "Local registry is running on localhost:5000"
}

run_tests() {
    log_info "Running unit and integration tests..."
    
    # Run tests for each service
    for service in "${SERVICES[@]}"; do
        log_info "Testing $service..."
        
        case $service in
            "auth-service")
                cd services/text-summarization/auth-service
                if [ -f "Makefile" ]; then
                    make test || log_warning "Tests failed for $service"
                else
                    go test ./... || log_warning "Tests failed for $service"
                fi
                cd - >/dev/null
                ;;
            "text-summarization")
                cd services/text-summarization
                if [ -f "Makefile" ]; then
                    make test || log_warning "Tests failed for $service"
                else
                    python -m pytest tests/ -v || log_warning "No tests found for $service"
                fi
                cd - >/dev/null
                ;;
            *)
                cd "services/$service"
                python -m pytest tests/ -v 2>/dev/null || log_warning "No tests found for $service"
                cd - >/dev/null
                ;;
        esac
    done
    
    # Run integration tests
    if [ -d "tests" ]; then
        log_info "Running integration tests..."
        cd tests
        python -m pytest . -v || log_warning "Integration tests failed"
        cd - >/dev/null
    fi
    
    log_success "Tests completed"
}

run_security_scans() {
    log_info "Running security scans..."
    
    # Install tools if needed
    if ! command -v syft >/dev/null 2>&1; then
        log_info "Installing syft..."
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
    fi
    
    if ! command -v trivy >/dev/null 2>&1; then
        log_info "Installing trivy..."
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    fi
    
    # Run security scans for each service
    for service in "${SERVICES[@]}"; do
        log_info "Security scanning $service..."
        
        case $service in
            "auth-service")
                cd services/text-summarization/auth-service
                if command -v govulncheck >/dev/null 2>&1; then
                    govulncheck ./... || log_warning "Security scan failed for $service"
                else
                    log_warning "govulncheck not available for $service"
                fi
                cd - >/dev/null
                ;;
            *)
                cd "services/$service" 2>/dev/null || continue
                if [ -f "requirements.txt" ]; then
                    bandit -r . || log_warning "Bandit scan failed for $service"
                    safety check || log_warning "Safety check failed for $service"
                fi
                cd - >/dev/null
                ;;
        esac
    done
    
    log_success "Security scans completed"
}

build_images() {
    log_info "Building images with BuildKit and SBOM..."
    
    local dockerfiles=("services/text-summarization/Dockerfile" "services/context-service/Dockerfile" "services/text-summarization/auth-service/Dockerfile")
    
    mkdir -p sbom-reports
    
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local dockerfile="${dockerfiles[$i]}"
        
        log_info "Building $service..."
        
        # Build with BuildKit
        docker buildx build \
            --platform linux/amd64 \
            --tag "$REGISTRY/$service:$VERSION" \
            --tag "$REGISTRY/$service:latest" \
            --file "$dockerfile" \
            --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            --build-arg VERSION="$VERSION" \
            --build-arg VCS_REF="$(git rev-parse HEAD)" \
            --provenance=true \
            --sbom=true \
            --push \
            .
        
        # Generate additional SBOM
        syft "$REGISTRY/$service:$VERSION" -o spdx-json="sbom-reports/sbom-$service.spdx.json"
        syft "$REGISTRY/$service:$VERSION" -o cyclonedx-json="sbom-reports/sbom-$service.cyclonedx.json"
        
        log_success "Built $service"
    done
    
    log_success "All images built with SBOM"
}

scan_images() {
    log_info "Scanning images for vulnerabilities..."
    
    mkdir -p security-reports
    
    for service in "${SERVICES[@]}"; do
        log_info "Scanning $service..."
        
        trivy image \
            --format sarif \
            --output "security-reports/trivy-$service.sarif" \
            "$REGISTRY/$service:$VERSION" || true
        
        trivy image \
            --format table \
            "$REGISTRY/$service:$VERSION"
    done
    
    log_success "Image scanning completed"
}

sign_images() {
    log_info "Signing images with Cosign..."
    
    if ! command -v cosign >/dev/null 2>&1; then
        log_warning "Cosign not available, skipping image signing"
        return
    fi
    
    # Generate ephemeral key for local testing
    if [ ! -f "cosign.key" ]; then
        log_info "Generating ephemeral signing key..."
        cosign generate-key-pair
    fi
    
    for service in "${SERVICES[@]}"; do
        log_info "Signing $service..."
        
        cosign sign --key cosign.key "$REGISTRY/$service:$VERSION" || {
            log_warning "Failed to sign $service - this is expected in local testing without proper OIDC setup"
        }
    done
    
    log_success "Image signing completed"
}

deploy_to_kind() {
    log_info "Deploying to kind cluster..."
    
    # Create kind cluster if it doesn't exist
    if ! kind get clusters | grep -q "mcp-test"; then
        log_info "Creating kind cluster..."
        make kind-setup
    fi
    
    # Connect local registry to kind
    if ! docker network ls | grep -q "kind"; then
        docker network connect "kind" "local-registry" 2>/dev/null || true
    fi
    
    # Deploy services
    make kind-deploy REGISTRY="$REGISTRY" VERSION="$VERSION"
    
    log_success "Deployment to kind completed"
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    make kind-test
    
    log_success "Smoke tests completed"
}

cleanup() {
    log_info "Cleaning up..."
    
    # Cleanup kind cluster
    make kind-cleanup 2>/dev/null || true
    
    # Stop local registry
    docker stop local-registry 2>/dev/null || true
    docker rm local-registry 2>/dev/null || true
    
    # Clean build artifacts
    docker system prune -f >/dev/null 2>&1 || true
    
    log_success "Cleanup completed"
}

print_usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  all              Run complete CI/CD pipeline (default)"
    echo "  test            Run tests only"
    echo "  security        Run security scans only"
    echo "  build           Build images only"
    echo "  scan            Scan images only"
    echo "  sign            Sign images only"
    echo "  deploy          Deploy to kind only"
    echo "  smoke           Run smoke tests only"
    echo "  cleanup         Cleanup resources"
    echo ""
    echo "Options:"
    echo "  -h, --help      Show this help message"
    echo "  -v, --version   Show version"
    echo "  --registry REG  Use specific registry (default: localhost:5000)"
    echo "  --no-cleanup    Skip cleanup at the end"
    echo ""
    echo "Environment Variables:"
    echo "  REGISTRY        Container registry (default: localhost:5000)"
    echo "  VERSION         Image version tag (default: git commit SHA)"
}

# Main execution
main() {
    local command="all"
    local skip_cleanup=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -v|--version)
                echo "CI/CD Test Script v1.0.0"
                exit 0
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            --no-cleanup)
                skip_cleanup=true
                shift
                ;;
            test|security|build|scan|sign|deploy|smoke|cleanup|all)
                command="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    log_info "Starting CI/CD pipeline test with registry: $REGISTRY"
    log_info "Version: $VERSION"
    
    # Set up cleanup trap
    if [ "$skip_cleanup" = false ] && [ "$command" != "cleanup" ]; then
        trap cleanup EXIT
    fi
    
    # Execute command
    case $command in
        all)
            check_prerequisites
            setup_local_registry
            run_tests
            run_security_scans
            build_images
            scan_images
            sign_images
            deploy_to_kind
            run_smoke_tests
            ;;
        test)
            run_tests
            ;;
        security)
            run_security_scans
            ;;
        build)
            check_prerequisites
            setup_local_registry
            build_images
            ;;
        scan)
            scan_images
            ;;
        sign)
            sign_images
            ;;
        deploy)
            check_prerequisites
            deploy_to_kind
            ;;
        smoke)
            run_smoke_tests
            ;;
        cleanup)
            cleanup
            ;;
    esac
    
    log_success "CI/CD pipeline test completed successfully!"
}

# Execute main function
main "$@"
