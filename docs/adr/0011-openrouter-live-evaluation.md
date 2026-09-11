# ADR-0011: OpenRouter DeepSeek live evaluation

- Status: Accepted for EG-015 implementation
- Date: 2026-09-10
- Story: EG-015

## Context

EG-015 needs one governed live generation and advisory judge strategy before EvalGate can make any
generation-quality claim. ADR-0010 intentionally deferred provider selection because model
availability, prices, retention, and routing behavior change. The repository owner approved
OpenRouter with `deepseek/deepseek-v4-flash`, a USD 4.60 hard budget, and a USD 4.14 stop limit.

Primary source checks on 2026-09-10:

- OpenRouter lists `deepseek/deepseek-v4-flash` as DeepSeek V4 Flash 0423, released 2026-04-24,
  with high and xhigh reasoning support, structured output support, and a 1M-token context window.
- OpenRouter lists the visible model price at approximately USD 0.0679 per 1M input tokens and
  USD 0.168 per 1M output tokens, with routed provider prices varying by host.
- OpenRouter documents provider routing fields including `allow_fallbacks`, `data_collection`,
  `zdr`, `max_price`, and `require_parameters`.

## Decision

Use OpenRouter's Responses-compatible endpoint with model `deepseek/deepseek-v4-flash` for both
generation and the advisory judge. The adapter sends only the synthetic CC0 EvalGate question and
selected evidence needed for a bounded case. Requests use structured JSON output, high reasoning,
returned reasoning-token exclusion, `temperature: 0`, `provider.zdr: true`,
`provider.data_collection: "deny"`,
`provider.allow_fallbacks: false`, `provider.require_parameters: true`, and provider price caps.

The provider key is accepted only through `EVALGATE_OPENROUTER_API_KEY` from an ignored local
`.env` file or the protected GitHub secret with the same name. The protected workflow is
`workflow_dispatch` only, has no pull-request trigger, does not use `pull_request_target`, and
uploads bounded artifacts only.

## Consequences

The normal API and browser remain fixture-only unless a future public-mode story opens a separate
runtime path with additional limits. Pull-request CI remains secret-free. The generated artifact
records provider/model identity, prompt policy hash, usage, cost, repetitions, human labels, judge
labels, agreement, variance-relevant per-repetition status, and limitations. It does not store API
keys, prompts, raw completions, or corpus text.

The judge is advisory because the same model acts as generator and judge. Any automatic blocking
claim requires later calibrated evidence that this story does not assume.

## Verification

Adapter tests assert request policy fields, typed redacted failures, and budget-stop enforcement.
Live-evaluation tests validate a generation artifact against the contract using fake provider ports.
The protected workflow is inspected by repository checks and is excluded from ordinary PR CI.
