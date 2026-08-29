# Northstar Source Onboarding Procedure

## Purpose
This procedure admits a new fictional Beacon Relay source key only after its envelope behavior and ownership boundary are reviewed. It does not onboard devices, people, or real locations.

## Request
The coordinator opens a source request with proposed synthetic source key, schema version, expected cadence, and responsible role. The request excludes personal contacts and credentials.

## Validation trial
The source sends test envelopes to the isolated validation environment. Tests cover signature verification, required fields, duplicate resend, sequence progression, and bounded note behavior.

## Key exchange
The fictional access process establishes verification material outside the handbook. The onboarding record contains only a key reference, never secret material.

## Initial state
Before the first accepted event, the ledger state is `unknown`. Operators must not assign `nominal` merely because onboarding completed.

## Activation
The release steward activates the source after the validation trial and change record are approved. The source key then appears in Board API summaries according to access policy.

## Failure
Failed validation leaves the source inactive. The requester corrects the integration through the normal change process; operators do not waive signature or ordering checks.

## Deactivation
The coordinator may deactivate a source key through a reviewed change. Deactivation does not erase already accepted evidence references.
