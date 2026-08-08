# EG-013A: Public-mode application security and privacy

- Status: Planned; EG-013 epic child
- Branch: `feat/eg-013a-public-security`
- Depends on: EG-008, EG-010, and EG-011 merged to `main`
- Release: R3
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

> Work only on EG-013A on branch `feat/eg-013a-public-security`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0009, completed contracts, and this story. Confirm dependencies are merged to clean `main`. Implement and test the environment/route policy, bounded validation, exact-origin/security headers, server-only outbound configuration, minimized short-lived rate identity, redaction, and adversarial security cases. Do not choose a host/auth product, add public ingestion/persistence, embed a browser secret, deploy, or claim a penetration test. Do not merge or push. Finish with trust-boundary explanation, files, exact security evidence, residual risks, and suggested commit message.
