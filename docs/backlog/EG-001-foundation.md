# EG-001: Reproducible repository foundation

- Status: Verified locally by the setup commit
- Branch: Initial setup on `main`; future corrections use `chore/eg-001-foundation-fix`
- Depends on: Approved R0 blueprint
- Release: R1
- Blueprint requirements: NFR-01, NFR-02, NFR-04, CON-01, CON-02

## Outcome

A clean, truthful repository can install, lint, type-check, test, build, and validate its PostgreSQL Compose configuration without implementing product features.

## Scope

- Governance, ADR, contract, backlog, security, contribution, and release skeletons.
- Python/FastAPI health-only foundation with framework-boundary test.
- React/Vite foundation screen explicitly labeled as foundation only.
- PostgreSQL/pgvector Compose service, lockfiles, local scripts, and secret-free CI.

## Non-goals

- Corpus, migrations/schema, embeddings, retrieval, generation, stream, evaluation, MCP, provider, container image, or deployment.

## Acceptance evidence

- [x] Blueprint is the first Git commit.
- [x] Publication, metadata, Compose, backend format/lint/type/test, and web lint/test/build checks pass.
- [x] No remote, secret, provider call, deployment, or product capability beyond the explicitly scoped health/status foundation exists.

## Required tests and review

- Run `scripts/check.ps1` or `scripts/check.sh`; inspect the two-commit history, ignored generated files, privacy scan, and absence of remotes/features.

## Expected file ownership

- Root governance/tooling, `.github/`, `scripts/`, health-only `apps/` foundations, `contracts/`, `docs/`, and empty governed `data/` directories.

## Stop conditions

- A correction would add product capability, call an external service, rewrite published history, or exceed the setup-only boundary.

## Copy-paste coding-agent brief

> Audit or correct only the EG-001 foundation on branch `chore/eg-001-foundation-fix`. Do not add any product capability. Read `AGENTS.md`, `BLUEPRINT.md`, and this story. Reproduce every foundation check, fix only setup/governance/tooling defects, and preserve the blueprint-first history. Do not merge, push, deploy, call providers, or start EG-002. Finish with an explanation, changed files, exact commands/results, limitations, and a suggested commit message.
