"""Isolated real-PostgreSQL fixtures for EG-003 integration tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import make_url


@pytest.fixture
def database_url() -> Iterator[str]:
    admin_url_value = os.getenv("EVALGATE_TEST_ADMIN_URL")
    if admin_url_value is None:
        if os.getenv("EVALGATE_REQUIRE_DATABASE_TESTS") == "1":
            pytest.fail("required database tests have no EVALGATE_TEST_ADMIN_URL")
        pytest.skip("EVALGATE_TEST_ADMIN_URL is required for real PostgreSQL integration tests")

    admin_url = make_url(admin_url_value)
    database_name = f"evalgate_test_{uuid.uuid4().hex}"
    host = admin_url.host or "127.0.0.1"
    port = admin_url.port or 5432
    user = admin_url.username
    password = admin_url.password
    with psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname="postgres",
        autocommit=True,
    ) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    test_url = admin_url.set(
        drivername="postgresql+psycopg",
        database=database_name,
    ).render_as_string(hide_password=False)
    try:
        yield test_url
    finally:
        with psycopg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres",
            autocommit=True,
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))
