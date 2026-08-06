#!/bin/bash
# KifPilot AI Support Agent - Start Script
# Usage: ./start.sh [environment]
# Example: ./start.sh production

set -e

ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

echo "=========================================="
echo "Starting KifPilot AI Support Agent"
echo "Environment: $ENVIRONMENT"
echo "Compose file: $COMPOSE_FILE"
echo "Env file: $ENV_FILE"
echo "=========================================="

# Check if required files exist
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file $ENV_FILE not found!"
    echo "Please copy .env.example to $ENV_FILE and configure it."
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: Compose file $COMPOSE_FILE not found!"
    exit 1
fi

# Create necessary directories
echo "Creating required directories..."
mkdir -p ./data ./chroma_db ./uploads ./logs ./nginx_logs ./ssl ./chroma ./ollama

# Set permissions
chmod 755 ./data ./chroma_db ./uploads ./logs ./nginx_logs ./ssl

# Pull latest images
echo "Pulling latest images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

# Build images
echo "Building images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache

# Start services
echo "Starting services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo "Checking service health..."
docker compose -f "$COMPOSE_FILE" ps

echo "=========================================="
echo "KifPilot AI Support Agent started successfully!"
echo "=========================================="
echo "Frontend: http://localhost"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "ChromaDB: http://localhost:8001"
echo "Ollama: http://localhost:11434"
echo "=========================================="