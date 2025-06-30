#!/bin/bash

# OSS License Obligations Inventory Script
# Uses grype and syft to scan for vulnerabilities and generate SBOM

set -e

SYFT_PATH="$HOME/bin/syft"
GRYPE_PATH="$HOME/bin/grype"

echo "=== OSS License Obligations Inventory ==="
echo "Date: $(date)"
echo "Tools: Syft $(${SYFT_PATH} --version | cut -d' ' -f2), Grype $(${GRYPE_PATH} --version | cut -d' ' -f2)"
echo

# Function to scan a directory or container image
scan_target() {
    local target=$1
    local name=$(basename "$target")
    
    echo "--- Scanning: $target ---"
    
    # Generate SBOM (Software Bill of Materials)
    echo "Generating SBOM..."
    ${SYFT_PATH} "$target" -o json > "sbom-${name}.json"
    ${SYFT_PATH} "$target" -o table > "sbom-${name}.txt"
    
    # Scan for vulnerabilities
    echo "Scanning for vulnerabilities..."
    ${GRYPE_PATH} "$target" -o json > "vulnerabilities-${name}.json"
    ${GRYPE_PATH} "$target" -o table > "vulnerabilities-${name}.txt"
    
    # Extract license information from SBOM
    echo "Extracting license information..."
    jq -r '.artifacts[]? | select(.licenses != null) | {name: .name, version: .version, licenses: [.licenses[]?.value]} | @json' "sbom-${name}.json" > "licenses-${name}.jsonl" 2>/dev/null || echo "No license information found in SBOM"
    
    echo "Files generated:"
    echo "  - sbom-${name}.json (SBOM in JSON format)"
    echo "  - sbom-${name}.txt (SBOM in table format)"
    echo "  - vulnerabilities-${name}.json (Vulnerabilities in JSON format)"
    echo "  - vulnerabilities-${name}.txt (Vulnerabilities in table format)"
    echo "  - licenses-${name}.jsonl (License information extracted)"
    echo
}

# Usage examples
echo "Usage Examples:"
echo "  $0 /path/to/project                    # Scan local directory"
echo "  $0 node:18                            # Scan Docker image"
echo "  $0 alpine:latest                      # Scan Alpine Linux image"
echo

# If arguments provided, scan them
if [ $# -gt 0 ]; then
    for target in "$@"; do
        scan_target "$target"
    done
else
    echo "No targets specified. Please provide directories or container images to scan."
    echo
    echo "For a multi-tenant system, you might want to scan:"
    echo "  - Your application container images"
    echo "  - Third-party dependencies (package.json, requirements.txt, etc.)"
    echo "  - Base images used in your containers"
    echo "  - Infrastructure-as-Code dependencies"
fi

echo "=== Scan Complete ==="
echo
echo "Next steps for compliance:"
echo "1. Review high-risk licenses (GPL, AGPL, custom licenses)"
echo "2. Document attribution requirements"
echo "3. Check for license compatibility with your product license"
echo "4. Address any critical vulnerabilities found"
echo "5. Set up automated scanning in your CI/CD pipeline"
