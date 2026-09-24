# ADR-0014: Enforce actionable container risk and disclose residual upstream risk

- Status: Accepted
- Date: 2026-09-24
- Owners: repository owner and release assurance
- Stories: EG-021, EG-014

## Context

The original release invariant rejected every unresolved HIGH or CRITICAL finding. The exact
`0.12.2` runtime image has no fixable HIGH/CRITICAL finding, but Trivy reports 44 HIGH findings in
the pinned Debian base for which no fixed version is available. Treating those findings as absent
would be false; treating every unavailable upstream fix as locally remediable would make the gate
non-actionable. The repository owner explicitly approved the EG-021 enforcement and disclosure
policy before its evidence was generated.

## Decision

The release gate fails on every fixable HIGH or CRITICAL container finding. A separate scan retains
and publishes every HIGH/CRITICAL finding, including upstream-unfixed findings. Residual findings
require an explicit owner decision, remain visible in release evidence, and must never be described
as a clean or vulnerability-free image. Scanner identity, database time, exact image ID, SBOM, and
both reports are recorded together.

## Consequences

- Teams can act on every blocking result without suppressing unavailable upstream fixes.
- The release record communicates 44 accepted upstream-unfixed HIGH findings for `0.12.2`.
- A newly fixable finding, any CRITICAL finding, scanner failure, missing full report, or missing
  owner decision blocks release.
- Base-image refreshes must rerun both scans and may change the residual-risk decision.

## Verification

`scripts/release_supply_chain.ps1` pins Trivy `0.74.0`, creates an exact-image CycloneDX SBOM,
fails its actionable scan on fixable HIGH/CRITICAL findings, retains the all-findings report, and
records hashes and counts in one summary.

## Revisit trigger

Revisit when the base image changes, an upstream fix becomes available, a CRITICAL finding appears,
or the scanner/policy changes.
