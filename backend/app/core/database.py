import sys
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import database_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with database_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_migrations() -> None:
    try:
        # Get the current alembic version from the database
        async with database_manager.session_factory() as session:
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar_one_or_none()

        # Get the head version from alembic script directory
        from alembic.script import ScriptDirectory
        from alembic.config import Config
        import os

        # Get the absolute path to the backend directory (3 levels up from app/core/database.py)
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        migrations_dir = os.path.join(backend_dir, "migrations")
        config = Config(os.path.join(backend_dir, "alembic.ini"))
        # Override script_location to absolute path
        config.set_main_option("script_location", migrations_dir)
        script_dir = ScriptDirectory.from_config(config)
        head_revisions = script_dir.get_heads()

        if current_version is None:
            logger.warning(
                "Database has no migrations applied",
                hint="Run 'alembic upgrade head' to apply migrations",
            )
            return

        if current_version not in head_revisions:
            logger.warning(
                "Database migrations are not up to date",
                current=current_version,
                head=head_revisions,
                hint="Run 'alembic upgrade head' to apply pending migrations",
            )
    except Exception as e:
        logger.warning("Failed to check migration status", error=str(e))


async def init_database() -> None:
    database_manager.initialize()
    await check_migrations()


async def close_database() -> None:
    await database_manager.close()