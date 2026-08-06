#!/bin/bash
# KifPilot AI Support Agent - Update Script
# Usage: ./update.sh [environment] [version_tag]

set -e

ENVIRONMENT=${1:-production}
VERSION_TAG=${2:-latest}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

echo "=========================================="
echo "Updating KifPilot AI Support Agent"
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION_TAG"
echo "=========================================="

# Pull latest code (if git repo)
if [ -d ".git" ]; then
    echo "Pulling latest code..."
    git pull origin main
fi

# Pull latest images
echo "Pulling latest images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

# Build images
echo "Building images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache

# Stop services gracefully
echo "Stopping services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down

# Start updated services
echo "Starting updated services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 15

# Check service health
docker compose -f "$COMPOSE_FILE" ps

echo "=========================================="
echo "Update completed successfully!"
echo "=========================================="
echo "Services status:"
docker compose -f "$COMPOSE_FILE" ps