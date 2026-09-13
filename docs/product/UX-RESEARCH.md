# EvalGate product-experience research

- Research date: 2026-09-13
- Scope: public product documentation plus direct open-source issue reports
- Decision: build a focused evaluation workbench, not a chat clone or a copy of another brand

## Current product problem

The current interface proves the underlying contracts, but it does not yet explain the product to
a new user. It renders every workflow in one long page, starts with a raw `index_version` text
field, exposes UUIDs and checksums as primary content, has no persistent navigation or visual
identity, and reduces transport failures to generic text. A browser request that never produces a
response can remain visually busy instead of reaching a bounded, actionable failure state.

This is a product-comprehension problem as much as a styling problem. EvalGate must help a user
understand the path from corpus to retrieval to answer to citations to release decision without
requiring prior RAG or infrastructure knowledge.

## Patterns worth adopting

| Reference | Useful interaction pattern | EvalGate adaptation |
| --- | --- | --- |
| [Braintrust experiment comparison](https://www.braintrust.dev/docs/evaluate/compare-experiments) | Aggregate summary first, regression sorting, explicit baseline, then inline/side-by-side case diffs | Lead with release decision and changed metrics, then let users drill into failed cases and evidence |
| [LangSmith experiment analysis](https://docs.langchain.com/langsmith/analyze-an-experiment) | Named datasets and experiments, configurable focused views, visible progress, filters, trace detail panel | Human-readable run names, compact result table, clear progress/failure state, and an evidence drawer |
| [Langfuse comparison](https://langfuse.com/docs/evaluation/experiments/compare-experiments) | Same dataset/evaluator identity, aggregate trade-offs, case-level comparison, human review | Make comparability and limitations visible before displaying deltas; do not hide missing cases |
| [Phoenix experiments](https://arize.com/docs/phoenix/datasets-and-experiments/how-to-experiments) | Dataset → experiment → evaluation mental model, UI and SDK workflows, repetitions | Use a short, visible workflow model and show variance/repetitions without inventing a live executor |
| [Opik dashboards](https://www.comet.com/docs/opik/tracing/dashboards/dashboards) | In-context metrics and experiment comparison views | Use small decision cards only for summaries; retain data-dense tables for comparisons |
| [Promptfoo web viewer](https://www.promptfoo.dev/docs/usage/web-ui/) | Local-first results viewer centered on a model/prompt result matrix | Keep the local-first posture and provide a compact multi-model comparison surface |

## Direct feedback constraints

The research also records failure modes rather than copying only polished screenshots:

- A [Promptfoo issue](https://github.com/promptfoo/promptfoo/issues/7203) reports that unused
  prompt/provider columns create an extremely wide, mostly empty table. EvalGate must show only
  compared dimensions and provide a responsive list/card fallback rather than compressing an
  unreadable desktop table onto mobile.
- A [Phoenix issue](https://github.com/Arize-ai/phoenix/issues/13726) describes auto-generated
  hexadecimal experiment projects as hard to find and organize. Stable IDs belong in technical
  details and machine contracts; the primary UI needs meaningful names.
- A [Langfuse issue](https://github.com/langfuse/langfuse/issues/15216) reports UI rows whose blank
  inputs and mismatched traces disagree with correct API data. EvalGate must test UI/API identity
  parity and never imply that missing presentation data is a passing result.
- A [Langfuse workshop issue](https://github.com/langfuse/langfuse-workshop/issues/13) shows how a
  plausible default can silently target the wrong evaluation object. EvalGate must label fixture,
  retrieval, and governed-live evidence explicitly and explain the consequence before action.
- A [Langfuse issue](https://github.com/langfuse/langfuse/issues/9674) reports an experiment call
  hanging without producing UI results. Every EvalGate request needs an owned timeout, terminal UI
  state, safe error code, retry path, and cancellation cleanup.

These reports are individual observations, not prevalence measurements. They are used as concrete
design hazards, not claims that every referenced product has the same problem.

## EvalGate identity and information architecture

The identity is **evidence control room**: calm, precise, inspectable, and visibly different from a
chat application.

- Product mark: an original gate-and-evidence-path SVG, used consistently in the favicon, product
  header, empty states, and repository documentation. It must remain legible at 16 pixels and in
  monochrome; do not reuse a competitor mark.
- Visual tokens: ink/navy surfaces, teal evidence/action, amber warning, red regression, green pass,
  neutral grays, a restrained radius scale, consistent elevation/borders, system sans typography,
  and monospace only inside optional technical details.
- Shell: persistent top navigation for Overview, Inspect, Evaluations, and System evidence; visible
  environment/mode and API status; responsive navigation with an accessible small-screen pattern.
- Overview: what EvalGate does, a four-step corpus → retrieve → answer/cite → release-gate diagram,
  truthful current-mode limitations, and direct next actions.
- Inspect: a friendly governed-corpus selector, sample questions, visible processing stages,
  grounded answer, citations, and retrieved evidence. It is not a chat transcript.
- Evaluations: named runs, decision summary, filters, baseline/candidate comparison, regressions
  first, and case detail with retrieved-versus-reviewed evidence.
- System evidence: human-readable corpus/index/model/prompt identities and verification status;
  full UUIDs and SHA-256 values appear only in an explicit “Technical details” disclosure with a
  copy action.

## Interaction and error contract

- The browser consumes the existing typed API/SSE errors through one normalized client problem
  shape: stable code, safe title, safe explanation, retryability, and optional correlation detail.
- Loading, empty, partial, success, cancelled, offline, timeout, malformed-response, and server
  failure are different states. A spinner never substitutes for a terminal state.
- A blocked fetch must terminate through a tested browser-owned deadline compatible with the
  existing 30-second server cap. Cancelling must clear timers and state and must not later surface
  a stale failure.
- Recovery text tells the user what happened, what is safe to retry, and whether the data may be
  incomplete. Technical codes are visible and copyable; raw server/provider details remain hidden.
- Navigation, dialogs/drawers, tooltips, charts, and tables retain keyboard, focus, screen-reader,
  reduced-motion, zoom, contrast, touch-target, and safe-text guarantees.

## Real-world showcase direction

The preferred source candidate is a small pinned subset of the official
[`kubernetes/website`](https://github.com/kubernetes/website) troubleshooting and operations
documentation. The repository's [license](https://github.com/kubernetes/website/blob/main/LICENSE)
is CC BY 4.0 for documentation and requires attribution; code samples and trademarks need separate
care. The source commit, selected paths, original URLs, attribution, license boundary, normalized
bytes, and hashes must be reviewed before any content enters EvalGate.

This would be a real-world documentation showcase, not a public benchmark and not production-user
traffic. EvalGate-authored questions and human labels must be described as a curated demonstration
set. Runtime URL crawling remains prohibited.

The OpenRouter candidate set supplied for later evaluation is:

- [`deepseek/deepseek-v4-flash`](https://openrouter.ai/deepseek/deepseek-v4-flash)
- [`deepseek/deepseek-v4-flash-0731`](https://openrouter.ai/deepseek/deepseek-v4-flash-0731)
- [`z-ai/glm-5.3-flash`](https://openrouter.ai/z-ai/glm-5.3-flash)
- [`tencent/hy3`](https://openrouter.ai/tencent/hy3)
- [`xiaomi/mimo-v2.5`](https://openrouter.ai/xiaomi/mimo-v2.5)

Availability, price, retention, ZDR routing, structured-output support, and provider identity are
time-sensitive and must be reverified at execution. As of this research, the MiMo page says it does
not support `response_format`; it therefore cannot silently join a structured-output comparison.
The implementation story requires a separate decision if that remains true.
