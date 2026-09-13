# R3 operational drills

These runbooks cover the failure modes required before the R3 release review. They are local,
reproducible procedures only; they do not claim deployment, cloud operations, paging, or incident
response maturity.

## Graceful shutdown

- Prerequisites: release Compose profile built; database healthy; API reachable on the selected local port.
- Detection: `/health/live` returns `alive` and `/health/ready` returns `ready` before shutdown.
- Containment: stop only the API container with a finite grace period.
- Recovery: start the same image again with `docker compose --profile release up -d api`.
- Verification: liveness and readiness return the same product version after restart.
- Rollback: use the previous accepted image digest if restart fails because of application behavior.
- Last drill result: recorded by `scripts/release_candidate.ps1` in `artifacts/release/eg-013d-smoke.json`.

## Provider outage and cooldown

- Prerequisites: EG-013C `GenerationControl` and `ControlledGenerationPort` tests pass.
- Detection: provider errors are surfaced as typed provider-unavailable failures and enter cooldown.
- Containment: the wrapper never falls back to fixture or another provider.
- Recovery: wait for the configured cooldown or enable the kill switch while investigating.
- Verification: EG-013C unit tests prove cooldown state, no fallback, and content-free telemetry.
- Rollback: disable live generation and keep deterministic fixture flows available locally.
- Last drill result: covered by automated EG-013C tests; no external provider call is required here.

## Database reset and restore

- Prerequisites: local PostgreSQL service, migrations, governed corpus, and reference snapshot when real retrieval is required.
- Detection: readiness reports `not_ready` with database or migration checks.
- Containment: do not run destructive downgrade commands; preserve current evidence artifacts first.
- Recovery: use the existing guarded `evalgate-db seed-empty`, then ingest the declared corpus again.
- Verification: `/health/ready` returns `ready`; ingestion reports the same immutable corpus/index identities.
- Rollback: when data cannot be preserved, use reproducible reset from versioned inputs rather than a schema downgrade.
- Last drill result: database reset/restore remains a local release-review drill; this story documents the procedure and keeps the destructive reset out of default scripts.

## Previous-image rollback

- Prerequisites: previous accepted image digest and matching database compatibility record.
- Detection: current image fails smoke or operator review after local promotion.
- Containment: stop the current API container only.
- Recovery: set the local image reference to the previous digest and start the API against the compatible database.
- Verification: liveness, readiness, and fixture ask/search smoke pass on the prior digest.
- Rollback: if schema compatibility is unsafe, restore/reset from reproducible inputs instead of downgrading migrations.
- Last drill result: pending a previous accepted image digest from release review; no unsafe default command exists.

## Credential exposure and rotation

- Prerequisites: provider key only in `.env` or a protected GitHub secret; never in browser code or pull-request workflows.
- Detection: publication checks, metadata checks, and manual review detect committed keys or credential URLs.
- Containment: disable the exposed key at the provider, remove it from local configuration, and keep the public kill switch enabled.
- Recovery: create a new provider key in the approved secret store and restart the trusted process.
- Verification: secret scan passes and the protected live-evaluation workflow requires the secret explicitly.
- Rollback: run in fixture mode until the replacement key and budget controls are verified.
- Last drill result: covered by publication checks and EG-015 protected-secret workflow review; no key was committed.

## Public generation kill switch

- Prerequisites: complete EG-013C generation limit configuration and live generation explicitly enabled by a later approved composition.
- Detection: operator sees budget, outage, abuse, or provider-quality concern.
- Containment: set `EVALGATE_GENERATION_KILL_SWITCH_ENABLED=true` and restart the process.
- Recovery: unset the kill switch only after the budget/provider issue has a reviewed disposition.
- Verification: EG-013C tests reject generation while the kill switch is enabled and expose content-free state.
- Rollback: disable live generation and keep read-only retrieval/result routes available.
- Last drill result: covered by EG-013C automated tests; public deployment remains out of scope.
