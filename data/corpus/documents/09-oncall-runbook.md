# Northstar On-Call Runbook

## Entry condition
Use this runbook when Relay Intake, Validation Queue, Status Ledger, Board API, or Notification Worker shows a declared health failure or sustained error budget breach.

## First action
Confirm the failing component, time window, and alert identifier. Do not copy raw payloads, credentials, or individual recipient details into an incident note.

## Triage
Check liveness, readiness, recent deployment record, queue depth, and dependency status. A component can be live while not ready; readiness governs whether it may serve current data.

## Intake failure
For signature or schema failures, preserve only typed reason codes and aggregate counts. Do not disable validation to restore throughput.

## Ledger failure
When the ledger is unavailable, place the Board API in typed unavailable mode. Do not manually edit a board response or promote a cached status to current.

## Queue growth
If validation queue depth grows, identify whether failures are hard rejects, quarantines, or dependency delay. Drain only through normal validated processing after the cause is understood.

## Communication
State the impacted component, user-visible behavior, known facts, and next review time. Do not speculate about physical conditions or individual sources.

## Exit criteria
Close the event after readiness is restored, queued work is accounted for, the change record is linked, and any deferred reconciliation has an owner role and due review.
