# Runbooks

Runbooks are created and drilled by the story that introduces the corresponding failure mode. Planned R3 runbooks:

- local setup and clean reset;
- database outage and migration mismatch;
- provider timeout/outage and cooldown;
- stream cancellation/resource cleanup;
- public generation kill switch;
- graceful shutdown;
- image rollback;
- reproducible demo database reset/restore;
- credential exposure and rotation;
- cost/allowance exhaustion.

An undrilled placeholder is not operational evidence. Every completed runbook records prerequisites, detection, containment, recovery, verification, rollback, and last drill result.

EG-013D adds the first R3 runbook bundle in
[R3 operational drills](R3-operational-drills.md). Items backed only by automated tests or pending
release-review inputs are labeled that way; they are not overstated as production incident drills.
