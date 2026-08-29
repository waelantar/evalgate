# Northstar Notification Policy

## Purpose
Notifications summarize approved changes for fictional internal teams. They are informational and never replace direct incident coordination.

## Trigger
The worker sends a notice only after the Status Ledger commits a changed state or staleness transition. A duplicate accepted resend produces no second notice.

## Content
A notice contains source key, previous state, new state, event reference, and board link label. It excludes raw notes, signatures, credentials, and personal information.

## Recipient groups
Recipient groups are role-based aliases maintained outside this corpus. The worker receives only an approved group label and does not resolve individual addresses.

## Rate limit
The worker sends at most one state-change notice per source key within five minutes. A later change during the window is summarized in the next eligible notice.

## Delivery failure
A temporary destination failure is retried with bounded backoff three times. A permanent failure is recorded as a delivery state and is not retried indefinitely.

## Escalation
Notification delivery failure does not change ledger state and does not create an incident automatically. The on-call operator decides whether the failed notification matters.

## Citation trap
This policy's notification limit is five minutes. It is not the ledger staleness limit, which is thirty minutes.
