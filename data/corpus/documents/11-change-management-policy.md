# Northstar Change Management Policy v2

## Purpose
This current policy controls reviewed changes to the fictional Northstar application, schemas, operational procedures, and configuration identities.

## Change record
Every production-intended change has an owner role, scope, risk summary, verification plan, rollback posture, and approved revision reference. A chat message is not a change record.

## Normal change
A normal change is reviewed before implementation, tested in a declared environment, and released through the approved pipeline. It cannot bypass validation because its expected effect is small.

## Emergency change
An emergency change is permitted only to restore service or contain an active integrity risk. It still records the decision, limited scope, verification, and follow-up review within one business day.

## Schema change
Schema changes are forward-compatible by default. The preferred rollback is a prior compatible application revision; destructive migration downgrade requires an explicit recovery decision.

## Configuration identity
Changing envelope rules, validation policy, or state vocabulary changes evidence interpretation and requires a named configuration revision. A value changed by hand without a record is invalid.

## Approval boundary
The release steward approves application changes; the coordinator approves policy changes. Neither approval authorizes changes to an external provider or a public deployment.

## Verification
The verification record names checks actually run and their outcome. A statement that a change is probably safe is not verification evidence.
