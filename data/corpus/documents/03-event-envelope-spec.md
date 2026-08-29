# Northstar Event Envelope Specification v2

## Status
This is the current envelope specification. It supersedes v1 for all events accepted after the v2 cutover recorded in the migration note.

## Required fields
An envelope contains `event_id`, `source_key`, `occurred_at`, `schema_version`, `payload`, and `signature`. `event_id` is an opaque identifier, not a person or device serial number.

## Event identifier
The sender generates a unique `event_id` for one business event. A resend keeps the same identifier. A corrected event receives a new identifier and names the earlier event in payload metadata.

## Source key
`source_key` is a synthetic stable label such as `zone-amber`. It identifies an approved reporting source, not a geographic address, user, or customer.

## Ordering
The payload contains a monotonic `source_sequence`. Northstar may accept a late event but marks it for reconciliation if its sequence is older than the latest accepted sequence for that source.

## Signature
The signature covers the canonical UTF-8 envelope excluding the signature member. Verification failure is a hard rejection and must not be retried by changing payload content.

## Payload limits
The canonical envelope is limited to 64 KiB. Individual free-text notes are limited to 2,000 characters and are treated as untrusted evidence, never as executable instructions.

## Compatibility
Unknown optional payload members are retained only in the audit reference. Unknown required schema versions are quarantined until a reviewed compatibility change is released.
