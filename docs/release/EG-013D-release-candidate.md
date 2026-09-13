# EG-013D release-candidate evidence

- Story: EG-013D
- Product version prepared by this story: 0.9.0
- Local image name: `evalgate-api:0.9.0`
- Publication state: not pushed, not deployed, and not released

## Release image definition

The committed `Dockerfile` defines a single API release-candidate image from the digest-pinned
`python:3.13.15-slim-trixie` base image. The runtime uses UID/GID `10001:10001`, disables access-log
content by relying on the existing API entrypoint, exposes only port `8000`, and checks
`/health/live` inside the container.

The `release` Compose profile adds the API container beside the existing digest-pinned PostgreSQL
18/pgvector service. The profile is opt-in and local-only; it does not push to a registry, create a
cloud resource, or select a deployment target.

## Local acceptance commands

```powershell
.\scripts\release_candidate.ps1
.\scripts\release_supply_chain.ps1
uv run --python 3.13.15 --project apps/api --locked python scripts/check_release_static.py
```

Expected ignored artifacts:

- `artifacts/release/eg-013d-smoke.json`
- `artifacts/release/eg-013d-sbom.cdx.json`
- `artifacts/release/eg-013d-scan.json`
- `artifacts/release/eg-013d-supply-chain-summary.json`

The SBOM script uses Syft for CycloneDX when available, then Docker SBOM as a local fallback. The
container scanner uses Trivy first and Grype second when either is available. If those local tools
are missing, it writes explicit waiver records and does not label the waiver as a completed scan.

The local EG-013D run built `evalgate-api:0.9.0` as image ID
`sha256:c6c86cc9c95d89935d1c7740c9e5ad9bb80e61f85ffca1062e6ccb50753c7222`. Liveness returned
EvalGate `0.9.0`, readiness returned database `available` and migration `current`, and graceful
API termination completed with `docker compose --profile release stop -t 10 api`.

A persistent CI workflow that uploads release artifacts is not added by this branch because that
would create an external artifact-publication path. Add it only after explicit repository-owner
approval for the workflow and artifact egress.

The local EG-013D run built `evalgate-api:0.9.0` as image ID
`sha256:c6c86cc9c95d89935d1c7740c9e5ad9bb80e61f85ffca1062e6ccb50753c7222`. Liveness returned
EvalGate `0.9.0`, readiness returned database `available` and migration `current`, and graceful
API termination completed with `docker compose --profile release stop -t 10 api`.

## Required finding disposition

Release review must classify every scanner finding as one of:

- `fixed_before_release`
- `accepted_with_waiver`
- `not_applicable`
- `blocked_release`

No severity-critical or severity-high finding may remain unresolved for a release. A missing local
scanner is a tool-availability waiver only, not a passed scan.

## Rollback boundary

Rollback uses a previously accepted image digest and the runbook in
[R3 operational drills](../runbooks/R3-operational-drills.md). Destructive migration downgrade is
not a default command. If schema state cannot safely run with the prior image, the recovery path is a
reviewed restore/reset from reproducible inputs.
