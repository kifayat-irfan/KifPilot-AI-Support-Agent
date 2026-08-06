#!/bin/bash
# Backend startup script

set -e

echo "Starting KifPilot AI Support Agent Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Initialize database
echo "Initializing database..."
python -c "from app.infrastructure.database import init_db; import asyncio; asyncio.run(init_db())"

# Start server
echo "Starting server on http://0.0.0.0:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000