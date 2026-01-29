#!/bin/bash
# ============================================================================
# ReportLift Encryption Key Generator
# ============================================================================
# This script generates a Fernet encryption key for credential storage.
#
# Usage: ./scripts/generate-encryption-key.sh
#
# Output: Prints a new encryption key to stdout
# ============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}ReportLift Encryption Key Generator${NC}"
echo "====================================="
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python is not installed."
    exit 1
fi

# Generate the key
KEY=$($PYTHON -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

echo "Generated Encryption Key:"
echo ""
echo "  $KEY"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  1. Add this to your .env file as: ENCRYPTION_KEY=$KEY"
echo "  2. Keep this key secure - losing it means losing access to encrypted data"
echo "  3. Never commit this key to version control"
echo ""
