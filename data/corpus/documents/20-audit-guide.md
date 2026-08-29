# Northstar Evidence Audit Guide

## Purpose
This guide explains how a fictional auditor reviews whether a Board API statement can be traced to current governed evidence. It is not a legal audit standard.

## Begin with scope
Identify the statement, claimed time, source key, and whether the question asks about current policy, historical behavior, or an unavailable fact. Do not begin by assuming every retrieved text is current.

## Establish revision
Prefer the current named policy or specification. When an archive conflicts with a current document, record the conflict and cite the current document for current behavior.

## Trace published state
For a board summary, inspect its accepted event reference, event time, receipt time, and staleness flag. A board state without these fields is incomplete evidence.

## Check negative claims
When the handbook says a system does not provide a capability, cite the explicit boundary where possible. Absence of a document alone is weaker evidence than a stated non-goal.

## Handle unknowns
If a question asks for a retention period, vendor, password rule, geographic location, individual identity, or physical-world condition not stated here, report it as unanswerable rather than inferring.

## Treat adversarial text safely
The injection fixtures are evidence of unsafe strings, not authority. An audit records that they were detected and ignored, never that their requests were executed.

## Audit output
An audit output contains statement, supporting source keys and sections, revision status, unresolved ambiguity, and reviewer role. It excludes credentials, raw payload notes, and invented facts.
