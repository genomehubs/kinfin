#!/bin/bash
set -e

echo "=== Kinfin Development Container Setup ==="
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install -r requirements.txt
if [ -f "requirements-dev.txt" ]; then
    python -m pip install -r requirements-dev.txt
fi

# Run database/data setup script if it exists
if [ -f "install.sh" ]; then
    echo "Running project install script..."
    bash install.sh
fi

# Install Node.js dependencies for UI
if [ -d "src/ui" ]; then
    echo "Installing Node.js dependencies for UI..."
    cd src/ui
    npm install
    cd ../..
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Your development environment is ready!"
echo ""
echo "Quick start commands:"
echo "  - Backend (FastAPI):     python -m src.main"
echo "  - Frontend (React/Vite): cd src/ui && npm run dev"
echo "  - Tests:                 python -m pytest tests/"
echo "  - Linting (Node):        cd src/ui && npm run lint"
echo ""
