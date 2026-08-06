#!/bin/bash
# KifPilot AI Support Agent - Backup Script
# Usage: ./backup.sh [environment] [backup_name]

set -e

ENVIRONMENT=${1:-production}
BACKUP_NAME=${2:-kifpilot_backup_$(date +%Y%m%d_%H%M%S)}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "Starting KifPilot AI Support Agent Backup"
echo "Environment: $ENVIRONMENT"
echo "Backup name: $BACKUP_NAME"
echo "=========================================="

# Create backup directory
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
mkdir -p "$BACKUP_PATH"

echo "Stopping services for consistent backup..."
docker compose -f "docker-compose.yml" --env-file "$ENV_FILE" stop backend chromadb

echo "Backing up SQLite database..."
docker compose -f "docker-compose.yml" --env-file "$ENV_FILE" run --rm backup sqlite3 /app/data/kifpilot.db .dump > "$BACKUP_PATH/kifpilot.db.sql"

echo "Backing up ChromaDB..."
docker compose -f "docker-compose.yml" run --rm chromadb tar czf - /chroma/chroma > "$BACKUP_PATH/chroma_db.tar.gz"

echo "Backing up uploads..."
tar czf "$BACKUP_PATH/uploads.tar.gz" -C ./uploads .

echo "Backing up configuration..."
cp .env "$BACKUP_PATH/env.backup" 2>/dev/null || true
cp .env.production "$BACKUP_PATH/env.production.backup" 2>/dev/null || true

echo "Creating backup manifest..."
cat > "$BACKUP_PATH/manifest.json" <<EOF
{
  "backup_name": "$BACKUP_NAME",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
  "components": {
    "sqlite": "kifpilot.db.sql",
    "chromadb": "chroma_db.tar.gz",
    "uploads": "uploads.tar.gz",
    "config": ["env.backup", "env.production.backup"]
  }
}
EOF

echo "Restarting services..."
docker compose -f "docker-compose.yml" --env-file "$ENV_FILE" start backend chromadb

echo "=========================================="
echo "Backup completed successfully!"
echo "Backup location: $BACKUP_PATH"
echo "=========================================="
echo "Backup contents:"
ls -la "$BACKUP_PATH"