# Northstar Release Procedure

## Entry criteria
Release begins when a reviewed change record exists, required checks have passed, and the release steward confirms the target revision. A green local build alone is insufficient.

## Build identity
Build once from the reviewed revision and record its immutable artifact identity. The same artifact moves through approved environments; rebuilding to obtain a different result is prohibited.

## Migration order
Apply reviewed forward migrations before enabling application behavior that requires them. Confirm readiness against the expected migration head before traffic is considered restored.

## Deployment window
The coordinator selects a window with an on-call operator available. The procedure does not claim a universal maintenance window or any customer notification schedule.

## Smoke verification
Verify liveness, readiness, one bounded Board API read, and absence of new typed error spikes. Do not manufacture a signed field event for a smoke test.

## Rollback
If verification fails, restore the prior compatible application artifact and place the Board API in unavailable mode if ledger compatibility is uncertain. Do not default to destructive migration downgrade.

## Release note
The release note states changed behavior, migration identifiers, known limitations, and actual verification. It does not assert physical-source conditions or user impact not evidenced by Northstar.

## Completion
Mark the change released only after the release steward records the artifact identity and verification results. Deployed and released are distinct states in this fictional process.
