# EG-016: Optional bounded public deployment

- Status: Optional and blocked until explicit external-resource authorization
- Branch: `feat/eg-016-public-deployment`
- Depends on: EG-014 accepted on `main`, verified live-service decision if public ask is enabled, and explicit deployment approval
- Release: R5
- Blueprint requirements: G-07, NFR-08, NFR-09, ADR-0009, ADR-0010

## Outcome

One verified host runs the accepted image and PostgreSQL seed with read-only privileged posture, approved access controls/limits, redacted operations, and tested smoke, kill, rollback, and shutdown paths.

## Scope

- Reverify one host's current pricing, region, pgvector, streaming/proxy, TLS, secrets, log retention, sleep/cold-start, rollback, egress, and spending controls using primary sources; record ADR.
- Provider-native configuration committed without secrets; manual protected deployment of the already scanned image digest.
- Decide access-controlled versus bounded anonymous ask; configure all approved rate/token/concurrency/daily/account limits and kill switch.
- Post-deploy privacy/security/stream/health smoke, cost observation, rollback and shutdown drill, verified public URL/status record.

## Non-goals

- Multi-cloud, Kubernetes, Terraform without reproducibility evidence, auto-deploy on merge, public mutation, new product capability, or deployment claim before verification.

## Acceptance evidence

- [ ] Explicit authorization covers account/resource creation, region, maximum spend, and public access posture.
- [ ] Same R3 image digest is deployed through protected manual promotion; secrets remain server-side.
- [ ] Privileged routes, logging/privacy, limits, kill switch, stream proxy behavior, smoke, rollback, and shutdown pass at the live URL.
- [ ] Current costs/retention/limitations and verified timestamp are recorded; deployment can be disabled safely.

## Required tests and review

- Before provisioning, review current primary-source capability/cost/retention evidence and approval; after authorization, run configuration validation, digest verification, live health/security/privacy/limits/stream smoke, cost observation, rollback, kill-switch, and shutdown drills.

## Expected file ownership

- One provider decision ADR, provider-native secret-free deployment configuration, protected promotion workflow, host-specific runbook/drill records, and verified release/deployment status documentation.

## Stop conditions

- No explicit authority, current price/capability/retention cannot be verified, budget lacks a hard ceiling, required controls fail, or deployment needs an architecture change.

## Copy-paste coding-agent brief

> Work only on EG-016 on branch `feat/eg-016-public-deployment`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0009, ADR-0010, R3 evidence, and this story. Do not create any external resource until explicit authorization names the host/account, region, access posture, and maximum spend. Using current primary sources, record the single-host decision and provider-native secret-free configuration; only after approval, manually promote the existing scanned digest and verify privileged-route denial, limits, kill switch, privacy, streaming, health, smoke, rollback, and shutdown. Do not add features, clouds, Kubernetes, automatic deployment, or public mutation. Do not merge or push. Finish with source-backed decision, external actions/cost, deployed digest/URL evidence, exact tests/drills, limitations, teardown path, and suggested commit message.
