#!/bin/bash
#
# MIT License
#
# Copyright (c) 2024 MCP Platform Contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Script to lint and format code across the MCP platform
# Ensures consistent code quality and style standards

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if tools are available
check_tools() {
    local missing_tools=()
    
    if ! command -v black >/dev/null 2>&1; then
        missing_tools+=("black")
    fi
    
    if ! command -v flake8 >/dev/null 2>&1; then
        missing_tools+=("flake8")
    fi
    
    if ! command -v autopep8 >/dev/null 2>&1; then
        missing_tools+=("autopep8")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_info "Install them with: pip install --break-system-packages ${missing_tools[*]}"
        exit 1
    fi
}

# Format Python code with black
format_python() {
    print_info "Formatting Python code with black..."
    
    if black --check --diff . >/dev/null 2>&1; then
        print_success "All Python files are already formatted correctly"
    else
        print_info "Formatting Python files..."
        black .
        print_success "Python files formatted successfully"
    fi
}

# Lint Python code with flake8
lint_python() {
    print_info "Linting Python code with flake8..."
    
    if flake8 .; then
        print_success "Python linting passed"
    else
        print_error "Python linting failed - please fix the issues above"
        return 1
    fi
}

# Lint shell scripts
lint_shell() {
    print_info "Checking shell script syntax..."
    
    local failed=0
    for script in $(find . -name "*.sh" -type f); do
        if bash -n "$script"; then
            print_success "✓ $script"
        else
            print_error "✗ $script has syntax errors"
            failed=1
        fi
    done
    
    if [ $failed -eq 0 ]; then
        print_success "All shell scripts have valid syntax"
    else
        print_error "Some shell scripts have syntax errors"
        return 1
    fi
}

# Check for MIT license headers
check_license_headers() {
    print_info "Checking for MIT license headers..."
    
    local missing_headers=()
    
    # Check Python files (excluding vendored/generated code)
    for file in $(find . -name "*.py" -type f -not -path "./migrations/*" -not -path "./.venv/*" -not -path "./venv/*" -not -path "*/site-packages/*" -not -path "*/migrations/versions/*" -not -path "*/test_*" -not -path "*/__pycache__/*"); do
        # Skip __init__.py files and test files as they typically don't need headers
        if [[ "$file" == *"/__init__.py" ]] || [[ "$file" == */test_* ]]; then
            continue
        fi
        
        if ! head -30 "$file" | grep -q "MIT License"; then
            missing_headers+=("$file")
        fi
    done
    
    # Check shell scripts (excluding vendored code)
    for file in $(find . -name "*.sh" -type f -not -path "./.venv/*" -not -path "./venv/*" -not -path "*/site-packages/*"); do
        # Skip postgres init scripts as they may have different licensing
        if [[ "$file" == */postgres-init/* ]]; then
            continue
        fi
        
        if ! head -30 "$file" | grep -q "MIT License"; then
            missing_headers+=("$file")
        fi
    done
    
    if [ ${#missing_headers[@]} -ne 0 ]; then
        print_warning "Files missing MIT license headers:"
        for file in "${missing_headers[@]}"; do
            echo "  $file"
        done
        print_info "Please add MIT license headers to these files"
    else
        print_success "All files have MIT license headers"
    fi
}

# Main function
main() {
    local mode="${1:-all}"
    
    echo "🔧 MCP Platform Code Quality Tools"
    echo "=================================="
    echo ""
    
    check_tools
    
    case "$mode" in
        "format")
            format_python
            ;;
        "lint")
            lint_python
            lint_shell
            ;;
        "check-headers")
            check_license_headers
            ;;
        "all"|*)
            format_python
            echo ""
            lint_python
            echo ""
            lint_shell
            echo ""
            check_license_headers
            ;;
    esac
    
    echo ""
    print_success "Code quality check complete!"
    echo ""
    echo "Available modes:"
    echo "  $0 format        - Format Python code only"
    echo "  $0 lint          - Lint Python and shell scripts"
    echo "  $0 check-headers - Check for MIT license headers"
    echo "  $0 all           - Run all checks (default)"
}

main "$@"
