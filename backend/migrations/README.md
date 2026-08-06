# Database Migrations

This directory contains Alembic database migrations for the KifPilot AI Support Agent.

## Running Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Migration Structure

- `versions/` - Contains individual migration scripts
- `env.py` - Alembic environment configuration
- `script.py.mako` - Migration script template
- `alembic.ini` - Alembic configuration (in backend root)