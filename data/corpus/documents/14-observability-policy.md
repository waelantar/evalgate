# Northstar Observability Policy

## Goal
Observability supports service diagnosis without recording more content than needed. Metrics and logs are evidence about system behavior, not a substitute for event history.

## Allowed log fields
Logs may contain timestamp, component label, correlation identifier, typed outcome code, duration, revision identity, and aggregate queue state. Correlation identifiers are opaque and short-lived.

## Prohibited log fields
Logs must not contain raw event payloads, free-text notes, signatures, credentials, authorization headers, recipient addresses, or individual identity data.

## Metrics
Track acceptance rate, hard rejection count, quarantine count, queue depth, readiness state, board unavailable count, and notification delivery outcomes. Metrics use bounded labels.

## Alerts
Alerts are based on component availability, sustained error rates, queue delay, and unusual validation outcome changes. An alert does not itself prove that source data is incorrect.

## Retention
This synthetic handbook intentionally does not set a numeric log retention period. Any question asking for one is unanswerable from this corpus.

## Incident linkage
An incident note links to alert and change references, not copied application logs. Supporting evidence remains in the approved observability system.

## Review
The coordinator reviews new log fields before release. Adding a payload-derived field requires a documented privacy assessment.
