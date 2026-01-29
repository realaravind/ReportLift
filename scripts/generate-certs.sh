#!/bin/bash
# ============================================================================
# ReportLift Self-Signed Certificate Generator
# ============================================================================
# This script generates self-signed TLS certificates for development/testing.
# For production, use certificates from a trusted Certificate Authority (CA).
#
# Usage: ./scripts/generate-certs.sh [domain]
#
# Arguments:
#   domain    Optional. The domain name for the certificate. Default: localhost
#
# Output:
#   certs/cert.pem    - The certificate file
#   certs/key.pem     - The private key file
# ============================================================================

set -e

# Configuration
DOMAIN="${1:-localhost}"
CERT_DIR="certs"
DAYS_VALID=365
KEY_SIZE=2048

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}ReportLift Certificate Generator${NC}"
echo "=================================="
echo ""

# Check if OpenSSL is installed
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: OpenSSL is not installed.${NC}"
    echo "Please install OpenSSL and try again."
    exit 1
fi

# Create certs directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Check if certificates already exist
if [ -f "$CERT_DIR/cert.pem" ] || [ -f "$CERT_DIR/key.pem" ]; then
    echo -e "${YELLOW}Warning: Certificates already exist in $CERT_DIR/${NC}"
    read -p "Do you want to overwrite them? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Existing certificates preserved."
        exit 0
    fi
fi

echo "Generating self-signed certificate for: $DOMAIN"
echo "Certificate will be valid for: $DAYS_VALID days"
echo ""

# Generate private key and certificate
openssl req -x509 \
    -nodes \
    -days "$DAYS_VALID" \
    -newkey rsa:"$KEY_SIZE" \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/CN=$DOMAIN/O=ReportLift/C=US" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"

# Set appropriate permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo ""
echo -e "${GREEN}Certificates generated successfully!${NC}"
echo ""
echo "Files created:"
echo "  - $CERT_DIR/cert.pem (certificate)"
echo "  - $CERT_DIR/key.pem (private key)"
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_DIR/cert.pem" -noout -subject -dates
echo ""
echo -e "${YELLOW}Note: This is a self-signed certificate for development only.${NC}"
echo "For production, obtain certificates from a trusted CA (e.g., Let's Encrypt)."
echo ""
echo "To use with ReportLift:"
echo "  docker-compose -f docker-compose.prod.yml up -d"
