# EG-013A: Public-mode application security and privacy

- Status: Planned; EG-013 epic child
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

- [ ] Public-mode route matrix is integration-tested and mutation is unavailable.
- [ ] Logs/errors/database contain no question, answer, chunk, raw IP, auth header, or credential.
- [ ] Security headers/CORS/input limits/trusted-proxy behavior have failing and passing tests.
- [ ] Threat model and residual prompt-injection risk are updated honestly.

## Required tests and review

- Run public/local route-matrix, bounds, CORS/header/proxy, pseudonym TTL, redaction, SSRF-configuration, XSS/scheme, citation-spoof, injection-fixture, and secret-scanning tests; perform a threat-model review.

## Expected file ownership

- Environment/route policy, validation and security middleware, outbound allowlist and rate-identity interfaces, adversarial integration tests, threat model, and public-mode security documentation.

## Stop conditions

- Authentication, a host-specific edge identity, public ingestion, content persistence, or arbitrary outbound URL is proposed.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `high`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.8.0` on the latest accepted `main`, apply only the declared patch to `0.8.1` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-013A on branch `feat/eg-013a-public-security`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0009, completed contracts, and this story. Confirm dependencies are merged to clean `main`. Implement and test the environment/route policy, bounded validation, exact-origin/security headers, server-only outbound configuration, minimized short-lived rate identity, redaction, and adversarial security cases. Do not choose a host/auth product, add public ingestion/persistence, embed a browser secret, deploy, or claim a penetration test. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, tag/release, or start another story. Finish with trust-boundary explanation, files, exact security evidence, residual risks, version handoff, and suggested commit message.
