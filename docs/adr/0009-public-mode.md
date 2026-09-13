# ADR-0009: Read-only bounded public posture

- Status: Accepted with deployment gate
- Date: 2026-08-08
- Stories: EG-013A, EG-013C, EG-016

## Context

A public AI endpoint creates privacy, abuse, cost, XSS, and mutation risks. A secret embedded in a browser is not a control.

## Decision

Public mode disables ingestion and evaluation imports/triggers, does not persist public content, keeps provider secrets server-side, and allows ask only behind layered request/token/concurrency/daily/provider-account limits and a kill switch. Access control may replace anonymous ask at the deployment gate.

## Consequences

Public questions and raw IPs are not logged. Rate identity is minimized and short-lived. Deployment remains optional.

## Verification

EG-013A implements the explicit environment/route matrix, bounded HTTP middleware, exact-origin
CORS/security headers, trusted-edge rate-identity interface, provider endpoint allowlist, and
content-redaction/adversarial tests. See `docs/security/public-mode.md` and the application threat
model. Layered abuse/cost enforcement and the kill switch remain EG-013C; host verification and any
deployment remain EG-016.
