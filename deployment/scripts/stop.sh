#!/bin/bash
# KifPilot AI Support Agent - Stop Script
# Usage: ./stop.sh [environment]

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
echo "Stopping KifPilot AI Support Agent"
echo "Environment: $ENVIRONMENT"
echo "=========================================="

# Stop services
echo "Stopping services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down

# Optionally remove volumes (uncomment if needed)
# echo "Removing volumes..."
# docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v

echo "=========================================="
echo "KifPilot AI Support Agent stopped successfully!"
echo "=========================================="