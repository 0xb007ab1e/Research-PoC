#!/bin/bash

# Script to update and regenerate dependency lock files
# This ensures all services have their dependencies harmonized and locked

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"

echo "🔄 Updating dependency lock files..."

# Ensure we have pip-tools available
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

echo "Activating virtual environment and installing pip-tools..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip pip-tools

# Services to update
services=(
    "services/context-service"
    "services/text-summarization"
    "tests"
)

for service in "${services[@]}"; do
    service_path="$PROJECT_ROOT/$service"
    
    if [ -f "$service_path/requirements.in" ]; then
        echo "📦 Updating $service..."
        cd "$service_path"
        
        # Generate locked requirements
        pip-compile requirements.in --output-file requirements.lock --upgrade
        
        echo "✅ Updated $service/requirements.lock"
    else
        echo "⚠️  No requirements.in found for $service"
    fi
done

echo "🎉 All dependency lock files updated successfully!"
echo ""
echo "Next steps:"
echo "1. Review the changes in requirements.lock files"
echo "2. Test your services with the new dependencies"
echo "3. Commit the updated lock files to version control"
