# EG-013A: Public-mode application security and privacy

- Status: Implemented and locally verified on review branch; awaiting owner review and manual merge
- Branch: `feat/eg-013a-public-security`
- Depends on: EG-008, EG-010, and EG-011 merged to `main`
- Release: R3
- Version action: Patch `0.8.0 -> 0.8.1`
- Codex profile: `gpt-5.6-sol` with `high` reasoning
- Blueprint requirements: NFR-05, NFR-08, NFR-12, ADR-0009

## Outcome

The application has an enforceable public mode with privileged mutation absent/disabled, bounded inputs, no content persistence/logging, minimized rate identity, and tested abuse/security boundaries.

## Scope

- Environment policy matrix for local, CI, trusted evaluation, and public modes.
- Disable ingestion/artifact import/evaluation mutation publicly; read-only routes remain explicit.
- Body/query/result/time limits, exact-origin CORS, security headers, trusted proxy policy, and server-side provider endpoint allowlist.
- Short-lived keyed rate pseudonym/trusted-edge interface with TTL and no raw-IP logging.
- XSS/invalid scheme, SSRF configuration, oversized input, citation spoof, injection fixture, route-policy, and redaction tests.

## Non-goals

- Host selection, WAF, accounts/RBAC/SSO, shared browser token, public deployment, cost telemetry UI, or penetration-test claim.

## Acceptance evidence

- [x] Public-mode route matrix is integration-tested and mutation is unavailable.
- [x] Logs/errors/database contain no question, answer, chunk, raw IP, auth header, or credential.
- [x] Security headers/CORS/input limits/trusted-proxy behavior have failing and passing tests.
- [x] Threat model and residual prompt-injection risk are updated honestly.

## Implementation evidence

- The framework-free environment matrix distinguishes `local`, `ci`, `trusted_evaluation`, and
  `public`; ingestion, artifact import, deterministic/live evaluation, and HTTP composition enforce
  their declared capabilities without enabling an HTTP mutation route.
- Public HTTP uses an exact route allowlist, disables docs/OpenAPI, enforces the 16 KiB body limit
  while chunks arrive, bounds the full ASGI lifecycle to 30 seconds by default, caps existing query
  and page fields, applies exact-origin CORS, and adds deny-by-default security headers.
- Forwarding headers are accepted only from configured literal proxy IPs. The resolved address is
  immediately HMAC-keyed into a TTL-bucketed 32-hex pseudonym; neither raw address nor pseudonym is
  logged or persisted by EG-013A.
- Settings and the OpenRouter adapter independently reject every provider base URL except the exact
  reviewed HTTPS endpoint. Adapter/configuration errors remain content-free.
- React adversarial coverage proves XSS and `javascript:` strings remain text/buttons, while the
  existing grounded-answer tests continue to reject citation spoofing and keep injection fixtures
  structurally separated as untrusted evidence.
- `scripts/check.ps1` passed post-bump: publication and metadata checks, formatting, Ruff, strict
  mypy, 199 backend unit/contract/security tests (14 integration tests deliberately excluded by the
  script), 31 frontend unit/component tests, 3 Chromium E2E/axe tests, and the production build.
- A separate forced PostgreSQL/reference run passed all 14 integration tests with database and
  reference skip guards enabled. The pinned snapshot was provisioned locally and is not committed.
- Product metadata was synchronized from `0.8.0` to `0.8.1`; independent FastEmbed, corpus, index,
  dataset, prompt, artifact-schema, and historical live-evaluation identities were not changed.
- The reviewed threat model is `docs/security/threat-model.md`. It explicitly leaves layered
  usage/cost limits and kill switch to EG-013C, the complete browser/accessibility audit to EG-013B,
  image/scans/SBOM to EG-013D, and any deployment decision to EG-016.

## Required tests and review

- Run public/local route-matrix, bounds, CORS/header/proxy, pseudonym TTL, redaction, SSRF-configuration, XSS/scheme, citation-spoof, injection-fixture, and secret-scanning tests; perform a threat-model review.

## Expected file ownership

- Environment/route policy, validation and security middleware, outbound allowlist and rate-identity interfaces, adversarial integration tests, threat model, and public-mode security documentation.

## Stop conditions

- Authentication, a host-specific edge identity, public ingestion, content persistence, or arbitrary outbound URL is proposed.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `high`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.8.0` on the latest accepted `main`, apply only the declared patch to `0.8.1` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-013A on branch `feat/eg-013a-public-security`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0009, completed contracts, and this story. Confirm dependencies are merged to clean `main`. Implement and test the environment/route policy, bounded validation, exact-origin/security headers, server-only outbound configuration, minimized short-lived rate identity, redaction, and adversarial security cases. Do not choose a host/auth product, add public ingestion/persistence, embed a browser secret, deploy, or claim a penetration test. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, tag/release, or start another story. Finish with trust-boundary explanation, files, exact security evidence, residual risks, version handoff, and suggested commit message.
