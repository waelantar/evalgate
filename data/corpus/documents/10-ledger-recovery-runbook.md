# Northstar Ledger Recovery Runbook

## Purpose
This fictional runbook covers a controlled recovery of the Status Ledger after a failed migration or integrity alert. It does not authorize broad destructive recovery.

## Preconditions
The on-call operator confirms the ledger is not ready, identifies the approved recovery revision, and records a change reference. Normal publication remains paused during recovery.

## Protect evidence
Capture migration identifier, database health, aggregate row counts, and error code. Do not export raw notes, service credentials, or whole event payloads into a ticket.

## Restore path
Deploy the last known compatible application revision and run the reviewed database recovery procedure. Destructive reset is a local-development procedure, not the default production response.

## Verification
Verify database readiness, expected migration head, ledger snapshot consistency, and Board API unavailable-to-ready transition. Do not verify by inventing a field event.

## Reconciliation
Reprocess only accepted event references that were confirmed not to have committed. Resends retain their original event identifier and must pass normal deduplication.

## Notification posture
Suppress duplicate state-change notices during reconciliation. A recovery notice describes service availability, not presumed source conditions.

## Completion
Document the root cause category, recovery revision, reconciliation count, and follow-up owner role. Keep the report free of payload text and personal data.

## Hard negative
This runbook does not define retention periods for backups, vendor recovery guarantees, or a database password rotation process; those topics are outside the synthetic handbook.
