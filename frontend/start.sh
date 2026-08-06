#!/bin/bash
# Frontend startup script

set -e

echo "Starting KifPilot AI Support Agent Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Start development server
echo "Starting development server on http://localhost:5173"
npm run dev