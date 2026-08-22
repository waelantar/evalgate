"""Safety tests for explicit database lifecycle commands."""

from typing import Literal

import pytest
from pydantic import SecretStr

from evalgate.config import Settings
from evalgate.entrypoints.database import DatabaseCommandError, reset_database


def _settings(environment: Literal["local", "ci", "public"]) -> Settings:
    return Settings(
        environment=environment,
        database_url=SecretStr("postgresql+psycopg://ignored:ignored@localhost/ignored"),
    )


def test_reset_requires_explicit_confirmation() -> None:
    with pytest.raises(DatabaseCommandError, match="requires --confirm-destroy-local-data"):
        reset_database(_settings("local"), confirmed=False)


def test_reset_is_rejected_in_public_environment_even_when_confirmed() -> None:
    with pytest.raises(DatabaseCommandError, match="only in local or ci"):
        reset_database(_settings("public"), confirmed=True)


def test_reset_rejects_non_loopback_database_even_in_local_mode() -> None:
    settings = Settings(
        environment="local",
        database_url=SecretStr("postgresql+psycopg://user:value@192.0.2.10/evalgate"),
    )

    with pytest.raises(DatabaseCommandError, match="requires a loopback database host"):
        reset_database(settings, confirmed=True)


def test_reset_rejects_unrelated_loopback_database() -> None:
    settings = Settings(
        environment="local",
        database_url=SecretStr("postgresql+psycopg://user:secret@127.0.0.1/postgres"),
    )

    with pytest.raises(DatabaseCommandError, match="requires the evalgate database name"):
        reset_database(settings, confirmed=True)
