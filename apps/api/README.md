# EvalGate API

This package contains framework-independent domain/application layers plus independent inbound/outbound adapters. EG-002 defines typed provider, clock, and identity ports, explicitly labeled deterministic fixtures, and fail-closed reference-snapshot verification. HTTP still implements health endpoints only; product endpoints remain planned in `BLUEPRINT.md` and the backlog.

```sh
uv sync --project apps/api --locked
uv run --project apps/api evalgate-api
```
