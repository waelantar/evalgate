# EG-018 OpenRouter candidate preflight

Checked: 2026-09-18. This is preflight evidence only. It does not authorize a paid call, corpus egress, fallback, browser secret, deployment, push, merge, tag, or release.

OpenRouter candidate pages currently report structured `response_format` support for all five user-supplied model slugs, including `xiaomi/mimo-v2.5`. The required request posture remained unchanged for the approved run: OpenRouter `/responses`, JSON-schema output, `temperature: 0`, `provider.zdr: true`, `provider.data_collection: "deny"`, `provider.allow_fallbacks: false`, `provider.require_parameters: true`, and per-model price/budget caps.

The repository owner approved EG-018 Kubernetes corpus evidence egress to OpenRouter with no fallback, no browser secret, a USD 1.00 cap, and a USD 0.80 stop limit. Three compatible low-cost candidates were executed; see `docs/evaluation/EG-018-live-comparison.md` for the reviewed, limitation-heavy result.

Primary sources checked:

- https://openrouter.ai/deepseek/deepseek-v4-flash
- https://openrouter.ai/deepseek/deepseek-v4-flash-0731
- https://openrouter.ai/z-ai/glm-5.3-flash
- https://openrouter.ai/tencent/hy3
- https://openrouter.ai/xiaomi/mimo-v2.5
- https://openrouter.ai/docs/api_reference/overview
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/docs/guides/features/structured-outputs
