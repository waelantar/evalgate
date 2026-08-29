# Archived Event Envelope Specification v1

## Archive status
This document is historical. It is retained to test superseded-fact handling. It must not be used to configure current Relay Intake.

## Former identifier rule
V1 allowed a sender to create a new event identifier for a resend after a timeout. V2 forbids that behavior because it made deduplication ambiguous.

## Former ordering rule
V1 treated receipt time as the primary ordering value. V2 uses the sender's `source_sequence` and records receipt time separately.

## Former signature scope
V1 documented a signature over the payload only. V2 signs the canonical envelope excluding the signature member.

## Former size limit
V1 described a 128 KiB maximum envelope. The current v2 limit is 64 KiB.

## Former note handling
V1 did not define a note-size limit. The current v2 specification caps free-text notes at 2,000 characters.

## Migration warning
Do not combine V1 and V2 field semantics in one parser. A relay using V1 must be migrated through the reviewed cutover procedure.

## Citation trap
The former rules above are intentionally believable but obsolete. A correct answer about current acceptance behavior cites v2, not this archive.
