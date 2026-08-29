# Northstar Envelope v2 Migration Note

## Status
This is the approved migration note for the fictional V1-to-V2 envelope cutover. It explains compatibility handling and is subordinate to the current v2 specification.

## Cutover rule
After the declared V2 cutover, Relay Intake accepts only V2 envelopes from activated sources. V1 is retained for historical interpretation and is not a live fallback.

## Identifier change
V2 requires a resend to retain its original `event_id`. Integrations that create a new ID for a resend must be corrected before activation.

## Signature change
V2 signs the canonical envelope excluding its signature member. A V1 payload-only signature is not valid V2 evidence.

## Ordering change
V2 uses monotonic `source_sequence` for source ordering. Receipt time remains recorded but cannot replace a missing or invalid sequence.

## Size change
V2 lowers the maximum envelope from the historical 128 KiB to 64 KiB. The smaller limit is intentional and current.

## Rollback posture
If cutover verification fails, pause activation and restore the compatible Northstar application revision. Do not reactivate V1 by silently interpreting V1 messages as V2.

## Completion evidence
Completion records source keys tested, V2 validation outcomes, configuration revision, and approved change reference. It contains no raw source payloads or keys.
