# EvalGate API

This package contains framework-independent domain/application layers plus independent inbound/outbound adapters. EG-002 defines typed provider, clock, and identity ports, explicitly labeled deterministic fixtures, and fail-closed reference-snapshot verification. The PostgreSQL adapter reports connectivity and exact Alembic-head readiness. HTTP still implements health endpoints only; product endpoints remain planned in `BLUEPRINT.md` and the backlog.

```sh
uv sync --project apps/api --locked
uv run --project apps/api evalgate-api
```

From the repository root, forward-only empty-schema setup is explicit:

```sh
uv run --project apps/api evalgate-db seed-empty
```

Real database tests create and destroy only uniquely named `evalgate_test_*` databases on the
configured PostgreSQL 18 server:

```sh
EVALGATE_TEST_ADMIN_URL=postgresql://evalgate:evalgate_local_only@127.0.0.1:5432/evalgate \
  uv run --project apps/api pytest -m integration
```

See [the migration guide](migrations/README.md) before using the guarded local reset.
