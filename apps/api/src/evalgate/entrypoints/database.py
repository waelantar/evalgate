"""Explicit, guarded database migration and reset commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from evalgate.config import Settings


class DatabaseCommandError(RuntimeError):
    """A safe database operation was rejected before mutation."""


def _alembic_config(settings: Settings) -> Config:
    api_root = Path(__file__).resolve().parents[3]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url.get_secret_value())
    return config


def seed_empty(settings: Settings) -> None:
    """Create or upgrade an empty database schema without inserting rows."""

    command.upgrade(_alembic_config(settings), "head")


def reset_database(settings: Settings, *, confirmed: bool) -> None:
    """Rebuild the reproducible schema after an explicit local/CI confirmation."""

    if settings.environment not in {"local", "ci"}:
        raise DatabaseCommandError("database reset is allowed only in local or ci environments")
    if not confirmed:
        raise DatabaseCommandError("database reset requires --confirm-destroy-local-data")
    database_url = make_url(settings.database_url.get_secret_value())
    host = database_url.host
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise DatabaseCommandError("database reset requires a loopback database host")
    database = database_url.database or ""
    if database != "evalgate" and not database.startswith("evalgate_test_"):
        raise DatabaseCommandError("database reset requires the evalgate database name")

    config = _alembic_config(settings)
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def main() -> None:
    """Run one explicit database lifecycle command."""

    parser = argparse.ArgumentParser(prog="evalgate-db")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed-empty", help="upgrade schema to head without inserting rows")
    reset_parser = subparsers.add_parser("reset", help="rebuild the reproducible local schema")
    reset_parser.add_argument("--confirm-destroy-local-data", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    try:
        if args.command == "seed-empty":
            seed_empty(settings)
        else:
            reset_database(settings, confirmed=args.confirm_destroy_local_data)
    except DatabaseCommandError as error:
        parser.error(str(error))
