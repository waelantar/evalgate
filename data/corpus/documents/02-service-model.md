# Northstar Service Model

## Components
The fictional service has Relay Intake, Validation Queue, Status Ledger, Board API, and Notification Worker. Each component has one narrow responsibility and records only the evidence needed for that responsibility.

## Relay Intake
Relay Intake receives a signed JSON envelope from Beacon Relay. It rejects unsigned, malformed, oversized, and expired envelopes before they reach the Validation Queue.

## Validation Queue
The Validation Queue checks schema version, source identifier format, and event ordering. It may delay an event for review; it never rewrites the source payload to make it pass.

## Status Ledger
The Status Ledger stores the current board state plus a short immutable event reference. It is not the authoritative history of field work and must not be used to infer missing events.

## Board API
The Board API exposes approved summaries to authenticated internal clients. It returns a typed unavailable response when the ledger is stale rather than presenting last-known state as live.

## Notification Worker
The Notification Worker sends a bounded notice for approved state changes. It deduplicates by event reference and does not retry a rejected recipient indefinitely.

## Time model
All service timestamps are UTC and include an offset when displayed. Event time comes from the signed envelope; receipt time comes from Northstar. These are distinct facts.

## Ownership
The coordinator owns operating policy. The on-call operator owns incident response. The release steward owns approved application changes. No role may bypass the change record.
