#!/bin/bash
# KifPilot AI Support Agent - Restore Script
# Usage: ./restore.sh [environment] [backup_name]

set -e

ENVIRONMENT=${1:-production}
BACKUP_NAME=${2}

if [ -z "$BACKUP_NAME" ]; then
    echo "Usage: ./restore.sh [environment] [backup_name]"
    echo "Available backups:"
    ls -1 ./backups/
    exit 1
fi

COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="./backups"

if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Error: Backup directory not found: $BACKUP_PATH"
    exit 1
fi

if [ ! -f "$BACKUP_PATH/manifest.json" ]; then
    echo "Error: Invalid backup - manifest.json not found"
    exit 1
fi

echo "=========================================="
echo "Restoring KifPilot AI Support Agent"
echo "Environment: $ENVIRONMENT"
echo "Backup: $BACKUP_NAME"
echo "=========================================="

# Read manifest
MANIFEST=$(cat "$BACKUP_PATH/manifest.json")
echo "Backup info:"
echo "$MANIFEST" | jq .

# Confirm restoration
read -p "This will overwrite current data. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restoration cancelled."
    exit 1
fi

echo "Stopping services..."
docker compose -f "docker-compose.yml" --env-file "$ENV_FILE" down

echo "Restoring SQLite database..."
docker compose -f "docker-compose.yml" run --rm backend sqlite3 /app/data/kifpilot.db < "$BACKUP_PATH/kifpilot.db.sql"

echo "Restoring ChromaDB..."
docker compose -f "docker-compose.yml" run --rm -v "$(pwd)/$BACKUP_PATH/chroma_db.tar.gz:/backup/chroma_db.tar.gz" chromadb tar xzf /backup/chroma_db.tar.gz -C /

echo "Restoring uploads..."
tar xzf "$BACKUP_PATH/uploads.tar.gz" -C ./uploads

echo "Restoring configuration..."
cp "$BACKUP_PATH/env.backup" .env 2>/dev/null || true
cp "$BACKUP_PATH/env.production.backup" .env.production 2>/dev/null || true

echo "Starting services..."
docker compose -f "docker-compose.yml" --env-file "$ENV_FILE" up -d

echo "Waiting for services to be healthy..."
sleep 15

# Check service health
docker compose -f "docker-compose.yml" ps

echo "=========================================="
echo "Restoration completed successfully!"
echo "=========================================="