# EvalGate product-experience conventions

## Purpose

EvalGate is an evidence-control room, not a general chat application. The primary path is:

```text
Governed corpus → retrieval → grounded answer and citations → reviewed evaluation gate
```

The UI explains that sequence before exposing a request form or technical identifiers.

## Information architecture

- **Overview** explains the product boundary, the four-step path, and truthful limitations.
- **Inspect** selects one available governed index by a friendly label, asks a bounded question,
  exposes retrieval/answer/citation progress, and drills into source passages.
- **Evaluations** starts with the reviewed run and metrics, then supports failed-case evidence
  inspection. It does not execute an evaluator.
- **System evidence** shows the active corpus, index policy, and browser mode. It is read-only.

Each destination has a direct path, page title, visible current navigation item, and browser
history support. There are no fake settings, activity, dashboards, or provider controls.

## Identity and components

The original gate-and-evidence-path mark is the only product mark. It is used in the top bar,
browser favicon, and product documentation. Local SVG and system fonts keep the application
offline-friendly and avoid copied visual identity or external font dependencies.

![EvalGate gate-and-evidence-path mark](../../apps/web/public/evalgate-mark.svg)

| Token family | Use |
| --- | --- |
| Ink/navy | Page and panel surfaces |
| Teal | Evidence, primary action, active processing |
| Green | Passing/reviewed status |
| Amber | Limitation and attention notice |
| Red | Failed/recoverable state |
| Monospace | Optional technical detail only |

All supported views use the same panel, status, focus, button, technical-details, and responsive
layout rules in `apps/web/src/styles.css`. Tables and dense records collapse to cards/stacked
controls at small widths rather than requiring horizontal interpretation.

## Human labels and technical identity

Human-readable corpus, index, run, status, and metric names are primary UI content. The browser
obtains selectable indexes only from `GET /api/v1/inspection-catalog`, a bounded read-only
projection of available stored indexes. It submits the returned immutable index ID internally.

UUIDs, SHA-256 values, raw provider identifiers, and evidence IDs are not required to complete a
workflow. They are retained under a visible **Technical details** disclosure for reproduction and
machine contracts. The UI never turns a missing detail into a passing result.

## Client states and error mapping

The browser owns a 30-second deadline, matching the accepted server request cap. Browser-test
configuration may shorten that deadline only for deterministic test execution; production defaults
to 30 seconds and never extends it. Every request cleans up its timer and `AbortController`; stale
late events are ignored by request identity.

| Condition | Stable client code | User-facing response |
| --- | --- | --- |
| Browser deadline | `client.timeout` | Explain that no change was made and offer retry |
| Offline browser | `client.offline` | Ask the user to check connection and retry |
| Typed retrieval problem | `retrieval.*` | Explain the selected evidence source is unavailable |
| Invalid request | `request.invalid` | Ask the user to check the question |
| SSE framing/protocol failure | `stream.protocol` | Explain the response could not be verified |
| Other transport failure | `stream.transport` | Safe generic retry message |
| Explicit cancellation | `stream.cancelled` | Terminal cancelled status with no error alert |

Server Problem Details are parsed only for their stable code/title/detail/request identity. Raw
server, provider, and dependency internals are never displayed. Loading, empty, partial, success,
cancelled, offline, timeout, malformed, and failure states are distinct; a spinner cannot be the
final state.

## Accessibility boundary

The automated suite covers keyboard use, focus movement to cited evidence, safe text rendering,
reduced motion, 320px reflow, axe checks, direct routes, and blocked-request recovery. The manual
record remains the authority for screen-reader, 200% zoom, forced-colors, and cross-browser checks;
unperformed rows stay pending.
