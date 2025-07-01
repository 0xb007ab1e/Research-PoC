#!/bin/bash
# Virtual Environment Bootstrap Script for MCP Services
# Handles Python "externally-managed environment" issues by creating per-service virtual environments

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if we're in CI environment
is_ci() {
    [ -n "${CI}" ] || [ -n "${GITHUB_ACTIONS}" ] || [ -n "${GITLAB_CI}" ] || [ -n "${JENKINS_URL}" ]
}

# Function to create or activate virtual environment
setup_venv() {
    local service_dir="$1"
    local service_name="$2"
    
    if [ ! -d "$service_dir" ]; then
        print_error "Service directory $service_dir does not exist"
        return 1
    fi
    
    cd "$service_dir"
    
    print_info "Setting up virtual environment for $service_name in $service_dir"
    
    # Check if .venv directory exists
    if [ ! -d ".venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv .venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment"
            return 1
        fi
        print_success "Virtual environment created at $service_dir/.venv"
    else
        print_info "Virtual environment already exists at $service_dir/.venv"
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source .venv/bin/activate
    
    # Upgrade pip, setuptools, and wheel first
    print_info "Upgrading core packages..."
    pip install --upgrade pip setuptools wheel
    
    print_success "Virtual environment for $service_name is ready"
}

# Function to install requirements with fallback for CI
install_requirements() {
    local service_dir="$1"
    local service_name="$2"
    local original_dir=$(pwd)
    
    cd "$service_dir"
    
    if [ ! -f "requirements.txt" ]; then
        print_warning "No requirements.txt found in $service_dir"
        return 0
    fi
    
    print_info "Installing requirements for $service_name..."
    
    # Check if virtual environment is activated
    if [ -n "$VIRTUAL_ENV" ]; then
        print_info "Installing in virtual environment: $VIRTUAL_ENV"
        pip install -r requirements.txt
    elif is_ci; then
        print_warning "CI environment detected, using --break-system-packages"
        pip install --break-system-packages -r requirements.txt
    else
        print_error "No virtual environment activated and not in CI"
        print_error "Please run setup_venv first or use CI environment"
        return 1
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Requirements installed successfully for $service_name"
    else
        print_error "Failed to install requirements for $service_name"
        return 1
    fi
}

# Function to run command in virtual environment
run_in_venv() {
    local service_dir="$1"
    local service_name="$2"
    shift 2
    local cmd="$@"
    
    cd "$service_dir"
    
    if [ -d ".venv" ]; then
        print_info "Running command in virtual environment for $service_name: $cmd"
        (
            source .venv/bin/activate
            eval "$cmd"
        )
    elif is_ci; then
        print_warning "No virtual environment found, running in CI mode"
        eval "$cmd"
    else
        print_error "No virtual environment found for $service_name"
        return 1
    fi
}

# Function to setup and install for a service
setup_service() {
    local service_dir="$1"
    local service_name="$2"
    local original_dir=$(pwd)
    
    print_info "Setting up service: $service_name"
    
    # Setup virtual environment
    setup_venv "$service_dir" "$service_name"
    if [ $? -ne 0 ]; then
        cd "$original_dir"
        return 1
    fi
    
    # Install requirements
    install_requirements "$service_dir" "$service_name"
    if [ $? -ne 0 ]; then
        cd "$original_dir"
        return 1
    fi
    
    cd "$original_dir"
    print_success "Service $service_name setup complete"
}

# Main function
main() {
    local action="${1:-help}"
    local service_dir="$2"
    local service_name="$3"
    
    case "$action" in
        "setup")
            if [ -z "$service_dir" ] || [ -z "$service_name" ]; then
                print_error "Usage: $0 setup <service_directory> <service_name>"
                exit 1
            fi
            setup_service "$service_dir" "$service_name"
            ;;
        "setup_venv")
            if [ -z "$service_dir" ] || [ -z "$service_name" ]; then
                print_error "Usage: $0 setup_venv <service_directory> <service_name>"
                exit 1
            fi
            setup_venv "$service_dir" "$service_name"
            ;;
        "install")
            if [ -z "$service_dir" ] || [ -z "$service_name" ]; then
                print_error "Usage: $0 install <service_directory> <service_name>"
                exit 1
            fi
            install_requirements "$service_dir" "$service_name"
            ;;
        "run")
            if [ -z "$service_dir" ] || [ -z "$service_name" ]; then
                print_error "Usage: $0 run <service_directory> <service_name> <command>"
                exit 1
            fi
            shift 3
            run_in_venv "$service_dir" "$service_name" "$@"
            ;;
        "help"|*)
            echo "Virtual Environment Bootstrap Script for MCP Services"
            echo ""
            echo "Usage: $0 <action> [arguments]"
            echo ""
            echo "Actions:"
            echo "  setup <service_dir> <service_name>    - Setup venv and install requirements"
            echo "  setup_venv <service_dir> <service_name> - Only setup virtual environment"
            echo "  install <service_dir> <service_name>  - Install requirements (with venv or CI fallback)"
            echo "  run <service_dir> <service_name> <cmd> - Run command in virtual environment"
            echo "  help                                   - Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  CI                - Set to enable CI mode (uses --break-system-packages)"
            echo "  GITHUB_ACTIONS    - Auto-detected CI environment"
            echo "  GITLAB_CI         - Auto-detected CI environment"
            echo "  JENKINS_URL       - Auto-detected CI environment"
            echo ""
            echo "Examples:"
            echo "  $0 setup services/context-service context-service"
            echo "  $0 run services/context-service context-service 'python main.py'"
            echo "  $0 install services/text-summarization text-summarization"
            ;;
    esac
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
