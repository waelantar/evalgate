"""PostgreSQL connectivity and migration-head readiness adapter."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

EXPECTED_ALEMBIC_HEAD = "20260822_0001"


@dataclass(frozen=True, slots=True)
class DatabaseReadiness:
    """Bounded operational state that contains no connection details."""

    database: str
    migration: str

    @property
    def ready(self) -> bool:
        return self.database == "available" and self.migration == "current"


async def check_database_readiness(engine: AsyncEngine) -> DatabaseReadiness:
    """Check connectivity and require exactly the compiled Alembic head."""

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            try:
                result = await connection.execute(text("SELECT version_num FROM alembic_version"))
                heads = tuple(result.scalars().all())
            except Exception:
                return DatabaseReadiness(database="available", migration="mismatch")
    except Exception:
        return DatabaseReadiness(database="unavailable", migration="unknown")

    migration = "current" if heads == (EXPECTED_ALEMBIC_HEAD,) else "mismatch"
    return DatabaseReadiness(database="available", migration=migration)
