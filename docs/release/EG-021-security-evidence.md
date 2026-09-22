# EG-021 security evidence

Status: **completed locally; pending owner review and manual merge**

Verified on 2026-09-22 from branch `chore/eg-021-release-security-evidence`.
No image, SBOM, tag, release, push, or deployment was published.

## Dependency gates

- Full and production-only npm audits report zero vulnerabilities after the compatible Vitest
  `4.1.11` and `js-yaml 4.3.2` lock remediation.
- The hashed `uv export --locked --all-groups` set reports zero vulnerabilities with
  `pip-audit 2.10.1` after the dev-only `httpx2/httpcore2 2.13.0` lock update.
- The official Python base is pinned to `python:3.13.15-slim-trixie` digest
  `sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0`.
- Runtime pip was removed after the locked install. This removes pip's shipped vendored
  `msgpack 1.1.2` and `setuptools 70.3.0` code rather than suppressing their advisories.

## Candidate evidence

The exact `0.12.2` candidate runs as `10001:10001`, reports `0.12.2`, passes
liveness/readiness after the standard host-side migration, and stops gracefully.

- Local image ID:
  `sha256:494a1359ef7bfdcd664eaf19061b25c856e39e96dc721871359a143ae2b2ed66`
- Pinned scanner:
  `aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969`
  (Trivy `0.74.0`)
- Smoke evidence SHA-256:
  `fff517aecadc5082a2c6bf17f36a18db05f4f52e344e950d2e262cc1b1930ae2`
- CycloneDX SBOM SHA-256:
  `51bd02168b8432893032a846851767ffb817674245471d8b48b145ab1689101e`
- Actionable scan SHA-256:
  `93323ccf860496e7bbc96e22b1c2a5d128e715c88d9bd77cbbeb95cb0b5c25ff`
- All-findings scan SHA-256:
  `cd5a1aa7d8edf20624cef441f38359cfb4fb8807ccb11c0268fc33fa51afcd70`

The owner-approved gate fails on every fixable HIGH/CRITICAL finding and retains a separate
all-findings report. The actionable result contains zero findings. The disclosure report contains
44 upstream-unfixed HIGH findings: 43 `affected` and one `fix_deferred`. This is accepted residual
upstream risk, not a claim that the image is vulnerability-free.

## Verification and disposition

The final repository matrix passed: 215 backend non-integration tests, 37 frontend tests, eight
Chromium E2E tests, lint, formatting, typing, metadata, publication, release-static, Compose, and
production build checks. All 16 isolated PostgreSQL/reference integration tests passed. The npm,
Python lock, candidate smoke, pinned Trivy, and CycloneDX gates also passed.

EG-021 consumes patch version `0.12.2` and is accepted locally under the documented actionable-risk
policy. The branch is ready for owner review and manual merge. EG-014 alone may perform the final
`0.12.2 -> 1.0.0` release-evidence sequence after the remaining human accessibility and exact-commit
CI gates are satisfied.
