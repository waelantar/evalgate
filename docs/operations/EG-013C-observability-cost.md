# EG-013C observability and provider-neutral cost controls

## Boundary

EvalGate `0.8.3` provides a small process-local policy for a future live-generation composition.
It does not choose or call a provider, use a monitoring vendor, create a metrics endpoint, persist
public questions, or make a deployment claim. Public HTTP remains generation-disabled.

`ControlledGenerationPort` wraps exactly one explicit provider port. It acquires a process-local
permit before invoking that provider, emits a fixed telemetry event after completion, rejection, or
outage, and re-raises the original failure. It never substitutes a fixture or another provider.
An outage enters the configured cooldown; an operator can set the server-side kill switch through
the composed `GenerationControl` instance.

## Required deployment configuration

Public configuration requires one complete declared set of values. There are deliberately no
repository-default public amounts: deployment must supply a reviewed provider/hosting budget.

```dotenv
EVALGATE_GENERATION_MAXIMUM_INPUT_TOKENS=<reviewed integer>
EVALGATE_GENERATION_MAXIMUM_OUTPUT_TOKENS=<reviewed integer>
EVALGATE_GENERATION_PER_CLIENT_CONCURRENCY=<reviewed integer>
EVALGATE_GENERATION_GLOBAL_CONCURRENCY=<reviewed integer>
EVALGATE_GENERATION_DAILY_REQUEST_ALLOWANCE=<reviewed integer>
EVALGATE_GENERATION_PROVIDER_ACCOUNT_CAP_USD=<reviewed decimal>
EVALGATE_GENERATION_COOLDOWN_SECONDS=<reviewed non-negative seconds>
EVALGATE_GENERATION_KILL_SWITCH_ENABLED=false
```

A missing public set fails closed with `generation.public_limits_required`; a partial set fails
with `generation.partial_limits_forbidden`. Current account spend is a server-side composition
input: this repository does not query a provider billing API.

## Structured telemetry and metric cardinality

Structured events contain only event, operation, status, code, request ID, run ID, duration, input
tokens, output tokens, and cost. No event API accepts question text, answer text, evidence, headers,
credentials, raw IP, or the rate pseudonym.

The in-memory metric adapter accepts only this fixed label schema:

| Metric | Labels |
| --- | --- |
| `requests` | `operation`, `status`, `code` |
| `generation_usage` | `status` |
| `generation_rejections` | `code` |
| `generation_state` | `state` |
| `database_pool` | `state` |

Request IDs, run IDs, client identities, index versions, provider revisions, URLs, and content are
never metric labels. An exporter or monitoring backend is a separate decision.

## Operator state and limitations

`GenerationControl.state()` exposes only generation-enabled, kill-switch, cooldown, global-active,
daily-request, and daily-cost fields. It omits client identity and content. State is process-local
and resets on restart; it is not a distributed quota system. EG-016 must compose these controls with
an approved host, account-spend observation, a server-only kill-switch operation, and live
smoke/rollback evidence.
