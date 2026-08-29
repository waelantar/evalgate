# Northstar Data Handling Policy

## Classification
Northstar classifies signed envelope metadata, ledger references, board summaries, and operational logs by purpose. Classification does not establish a legal basis or real-world data category.

## Minimal collection
Relay Intake uses only fields required by the current envelope specification. Optional free-text notes are bounded and excluded from routine logs and board responses.

## Board data
The Board API exposes current status summaries and references only. It never exposes signatures, raw payloads, source-side notes, or access credentials.

## Derived data
Aggregate metrics may count typed outcomes and queue depth. They must not reconstruct a raw note or a source event through unbounded labels.

## Export restriction
There is no unrestricted export endpoint in the fictional system. A reviewed audit request receives only the minimum evidence references needed for its stated purpose.

## Retention boundary
The handbook gives no numeric retention schedule for raw events, board summaries, or logs. Such a schedule must be supplied by a separate approved policy, not guessed from this text.

## Deletion request trap
This corpus contains no procedure for real-person deletion requests because it contains no real-person data. Do not infer a legal workflow from that absence.

## Security incident
Suspected exposure of credentials or raw payload content is handled as a security incident: contain access, preserve minimal evidence, and notify the coordinator role through the approved process.
