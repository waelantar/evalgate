# Northstar Validation Policy v3

## Policy status
This is the current validation policy. It applies after cryptographic verification and before ledger publication.

## Hard rejections
Northstar rejects a missing signature, invalid signature, malformed required field, unsupported required schema version, or envelope over 64 KiB. A hard rejection creates a typed reason code without retaining free-text payload content in logs.

## Quarantine
An otherwise well-formed event may be quarantined for duplicate identifier conflict, sequence regression, or unrecognized optional schema extension. Quarantine is reviewable and is not a successful publication.

## Duplicate handling
An exact resend with the same event identifier and payload digest is acknowledged without creating a second ledger entry. The same identifier with a different digest is quarantined.

## Sequence handling
An event with an older source sequence is accepted only when the source explicitly marks it as a correction and names the replaced event reference. Otherwise it is quarantined.

## Clock handling
An `occurred_at` value more than 24 hours ahead of receipt time is quarantined. A stale event is not automatically false; it is evaluated with its source sequence.

## Review record
The operator records the reason code, event reference, disposition, and reviewer role. The review record excludes payload notes and credential material.

## Prohibited shortcut
Operators must not edit a rejected payload, disable signature verification, or replay it under a new event identifier to clear a queue.
