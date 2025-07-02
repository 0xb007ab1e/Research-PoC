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

# Certificate generation script for mTLS between MCP services
# Generates a root CA and service certificates for secure inter-service communication

set -e

# Configuration
CERTS_DIR="./certs"
CA_DIR="${CERTS_DIR}/ca"
SERVICES_DIR="${CERTS_DIR}/services"

# Certificate validity (days)
CA_VALIDITY=3650  # 10 years for CA
CERT_VALIDITY=365 # 1 year for service certificates

# Service names (for SAN)
SERVICES=("auth-service" "context-service" "text-summarization")

echo "=== MCP Services Certificate Generation ==="
echo "Generating certificates for secure inter-service communication..."

# Create directory structure
mkdir -p "${CA_DIR}" "${SERVICES_DIR}"

# Clean up existing certificates
rm -f "${CA_DIR}"/* "${SERVICES_DIR}"/*

echo "Step 1: Generating Root CA..."

# Generate CA private key
openssl genrsa -out "${CA_DIR}/ca-key.pem" 4096

# Generate CA certificate
openssl req -new -x509 -days ${CA_VALIDITY} -key "${CA_DIR}/ca-key.pem" \
    -out "${CA_DIR}/ca-cert.pem" \
    -subj "/C=US/ST=CA/L=San Francisco/O=MCP Services/OU=Security/CN=MCP Root CA"

echo "✓ Root CA certificate generated"

# Create OpenSSL config for server certificates
cat > "${CA_DIR}/server.conf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = CA
L = San Francisco
O = MCP Services
OU = Microservices

[v3_req]
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
EOF

echo "Step 2: Generating service certificates..."

for service in "${SERVICES[@]}"; do
    echo "  Generating certificate for ${service}..."
    
    # Update alt_names in config for current service
    sed -i '/\[alt_names\]/,$d' "${CA_DIR}/server.conf"
    cat >> "${CA_DIR}/server.conf" << EOF
[alt_names]
DNS.1 = ${service}
DNS.2 = ${service}.default.svc.cluster.local
DNS.3 = ${service}-service
DNS.4 = localhost
IP.1 = 127.0.0.1
EOF

    # Generate service private key
    openssl genrsa -out "${SERVICES_DIR}/${service}-key.pem" 2048
    
    # Generate certificate signing request
    openssl req -new -key "${SERVICES_DIR}/${service}-key.pem" \
        -out "${SERVICES_DIR}/${service}.csr" \
        -config "${CA_DIR}/server.conf" \
        -subj "/C=US/ST=CA/L=San Francisco/O=MCP Services/OU=Microservices/CN=${service}"
    
    # Sign the certificate with CA
    openssl x509 -req -in "${SERVICES_DIR}/${service}.csr" \
        -CA "${CA_DIR}/ca-cert.pem" \
        -CAkey "${CA_DIR}/ca-key.pem" \
        -CAcreateserial \
        -out "${SERVICES_DIR}/${service}-cert.pem" \
        -days ${CERT_VALIDITY} \
        -extensions v3_req \
        -extfile "${CA_DIR}/server.conf"
    
    # Clean up CSR
    rm "${SERVICES_DIR}/${service}.csr"
    
    echo "  ✓ ${service} certificate generated"
done

echo "Step 3: Setting up combined certificate files..."

# Create combined cert+key files for easier deployment
for service in "${SERVICES[@]}"; do
    cat "${SERVICES_DIR}/${service}-cert.pem" "${SERVICES_DIR}/${service}-key.pem" > "${SERVICES_DIR}/${service}-combined.pem"
done

echo "Step 4: Creating Kubernetes secrets manifests..."

mkdir -p "${CERTS_DIR}/k8s"

# Generate CA secret
kubectl create secret generic mcp-ca-cert \
    --from-file=ca-cert.pem="${CA_DIR}/ca-cert.pem" \
    --dry-run=client -o yaml > "${CERTS_DIR}/k8s/ca-secret.yaml"

# Generate service secrets
for service in "${SERVICES[@]}"; do
    kubectl create secret tls "${service}-tls" \
        --cert="${SERVICES_DIR}/${service}-cert.pem" \
        --key="${SERVICES_DIR}/${service}-key.pem" \
        --dry-run=client -o yaml > "${CERTS_DIR}/k8s/${service}-tls-secret.yaml"
done

echo "Step 5: Creating Docker Compose volume configurations..."

mkdir -p "${CERTS_DIR}/docker"

# Copy certificates for Docker Compose
for service in "${SERVICES[@]}"; do
    service_dir="${CERTS_DIR}/docker/${service}"
    mkdir -p "${service_dir}"
    
    # Copy service certificate and key
    cp "${SERVICES_DIR}/${service}-cert.pem" "${service_dir}/server-cert.pem"
    cp "${SERVICES_DIR}/${service}-key.pem" "${service_dir}/server-key.pem"
    
    # Copy CA certificate for client verification
    cp "${CA_DIR}/ca-cert.pem" "${service_dir}/ca-cert.pem"
done

echo "Step 6: Setting proper permissions..."

# Set secure permissions
chmod 600 "${CA_DIR}/ca-key.pem"
chmod 644 "${CA_DIR}/ca-cert.pem"

for service in "${SERVICES[@]}"; do
    chmod 600 "${SERVICES_DIR}/${service}-key.pem"
    chmod 644 "${SERVICES_DIR}/${service}-cert.pem"
    chmod 600 "${SERVICES_DIR}/${service}-combined.pem"
    
    # Docker permissions
    chmod 600 "${CERTS_DIR}/docker/${service}/server-key.pem"
    chmod 644 "${CERTS_DIR}/docker/${service}/server-cert.pem"
    chmod 644 "${CERTS_DIR}/docker/${service}/ca-cert.pem"
done

echo "Step 7: Generating certificate verification script..."

cat > "${CERTS_DIR}/verify-certs.sh" << 'EOF'
#!/bin/bash

# Certificate verification script
CERTS_DIR="$(dirname "$0")"

echo "=== Certificate Verification ==="

# Verify CA certificate
echo "Verifying CA certificate..."
openssl x509 -in "${CERTS_DIR}/ca/ca-cert.pem" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After)"

# Verify service certificates
for service in "auth-service" "context-service" "text-summarization"; do
    echo ""
    echo "Verifying ${service} certificate..."
    
    # Check certificate against CA
    openssl verify -CAfile "${CERTS_DIR}/ca/ca-cert.pem" "${CERTS_DIR}/services/${service}-cert.pem"
    
    # Show certificate details
    openssl x509 -in "${CERTS_DIR}/services/${service}-cert.pem" -text -noout | grep -E "(Subject:|Subject Alternative Name|Not Before|Not After)"
done

echo ""
echo "Certificate verification complete!"
EOF

chmod +x "${CERTS_DIR}/verify-certs.sh"

echo ""
echo "=== Certificate Generation Complete! ==="
echo ""
echo "Generated files:"
echo "  Root CA:"
echo "    ${CA_DIR}/ca-cert.pem     - Root CA certificate"
echo "    ${CA_DIR}/ca-key.pem      - Root CA private key"
echo ""
echo "  Service certificates:"
for service in "${SERVICES[@]}"; do
    echo "    ${SERVICES_DIR}/${service}-cert.pem    - ${service} certificate"
    echo "    ${SERVICES_DIR}/${service}-key.pem     - ${service} private key"
done
echo ""
echo "  Docker Compose:"
echo "    ${CERTS_DIR}/docker/      - Certificates organized for Docker Compose"
echo ""
echo "  Kubernetes:"
echo "    ${CERTS_DIR}/k8s/         - Kubernetes secret manifests"
echo ""
echo "Usage:"
echo "  1. For Docker Compose: Update docker-compose.yml to mount certificate volumes"
echo "  2. For Kubernetes: Apply secrets with 'kubectl apply -f ${CERTS_DIR}/k8s/'"
echo "  3. Set REQUESTS_CA_BUNDLE environment variable to CA certificate path"
echo "  4. Verify certificates: run '${CERTS_DIR}/verify-certs.sh'"
echo ""
echo "Security Notes:"
echo "  - CA private key is secured with 600 permissions"
echo "  - Service private keys are secured with 600 permissions"
echo "  - Certificates are valid for ${CERT_VALIDITY} days"
echo "  - CA certificate is valid for ${CA_VALIDITY} days"
echo ""
echo "Next steps:"
echo "  1. Update Docker Compose configuration for mTLS"
echo "  2. Update Helm charts for certificate mounting"
echo "  3. Configure services to use TLS with client certificate verification"
