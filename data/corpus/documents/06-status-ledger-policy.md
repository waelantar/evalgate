# Northstar Status Ledger Policy

## Purpose
The Status Ledger holds the currently publishable status for each synthetic source key and an immutable reference to the accepted event that established it.

## State vocabulary
The current vocabulary is `nominal`, `degraded`, `paused`, and `unknown`. `unknown` means Northstar lacks sufficient recent verified evidence; it does not mean a source is safe or unsafe.

## Publication rule
Only an accepted event can change published state. A quarantined event, an operator comment, or an unverified notification cannot change the ledger.

## Staleness
The ledger marks a source stale after 30 minutes without a verified update. The Board API must display stale state as stale and must not silently substitute a predicted status.

## Corrections
A correction may replace the state derived from an earlier event when the correction explicitly references that event and passes validation. Both event references remain auditable.

## Retention
The ledger retains state and event references for the handbook's synthetic demonstration window. It does not retain raw free-text notes after validation.

## Read consistency
Board reads use one committed ledger snapshot. A client may receive an unavailable response during a controlled ledger migration rather than a mixed revision.

## Hard negative
The ledger never estimates travel time, staffing, weather, inventory, physical safety, or customer impact. Questions about those topics are unanswerable from this corpus.
