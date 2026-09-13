# EG-017: Product identity, explainable UX, and resilient client states

- Status: Planned
- Branch: `feat/eg-017-product-experience`
- Depends on: EG-011, EG-013A, EG-013B, and the initial EG-014 audit merged to `main`
- Release: R3
- Version action: Minor `0.9.0 -> 0.10.0`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: G-03, G-09, FR-04/05/08/12/13, NFR-05/06

## Outcome

A newcomer can understand what EvalGate does, complete the supported inspect and evaluation flows,
see what is happening under the hood, recover from failures, and inspect technical evidence only
when wanted through a coherent responsive product interface.

## Product decisions

- Use the evidence-control-room direction in `docs/product/UX-RESEARCH.md`; do not imitate or copy
  a competitor's trade dress.
- Add an original code-native SVG product mark and favicon. Use one repository-wide token system
  for color, typography, spacing, radius, elevation, status, and focus.
- Use a persistent responsive product shell with truthful destinations only: Overview, Inspect,
  Evaluations, and System evidence. No dead navigation, fake settings, fake activity, or dashboard
  numbers.
- Present human-readable names first. UUIDs, hashes, raw provider/model identifiers, and schema
  versions remain available under a clearly labeled technical-details disclosure and in API
  contracts, never as the main label or required manual input.

## Scope

- Restructure the current single page into navigable views with document titles, page headings,
  subtitles, contextual explanations, breadcrumbs when useful, empty-state guidance, and one
  primary action per view. Keep routing dependency-free unless a measured need proves otherwise.
- Add a bounded read-only index/catalog projection if required so the UI can select a real
  available corpus/index by friendly label while submitting the immutable internal identifier.
  Do not add ingestion, mutation, uploads, or arbitrary paths/URLs.
- Replace the free-text index UUID field with the catalog selector, truthful fixture/reference
  mode labels, example questions, and a visible retrieval → answer → citation-validation stage
  model. Preserve expert evidence inspection without presenting a chat transcript.
- Rework evaluation results into named run summaries, baseline/candidate context, understandable
  metric labels and explanations, regression-first filters, responsive case detail, and explicit
  limitations. Do not invent data or an interactive evaluator.
- Add accessible icons, info help, tooltips/popovers, safe diagrams/illustrations, status badges,
  skeleton/progress/empty/error/retry states, and mobile navigation using original local SVG or
  semantic HTML/CSS assets. Do not add an icon framework or remote font/CDN for aesthetics alone.
- Normalize HTTP Problem Details, stream failures, malformed responses, offline failures, and
  timeouts into one typed frontend problem contract. Show a safe stable error code, explanation,
  retry/cancel action, and optional correlation detail; never expose server/provider internals.
- Add a browser-owned finite deadline compatible with the accepted 30-second server cap. Prove a
  deliberately blocked request leaves loading, reaches a terminal timeout state, permits retry,
  and ignores stale late completion. Timer and AbortController cleanup must be deterministic.
- Finish responsive behavior at 320px, 768px, and desktop; tables must not become compressed,
  empty-column grids. Preserve keyboard, focus, zoom, forced-colors, reduced-motion, contrast,
  touch targets, and safe rendering.
- Document the design tokens, component/state conventions, information architecture, human-label
  rules, and frontend/backend error mapping so the identity persists across later repository work.

## Non-goals

- Chat history, general chatbot layout, arbitrary dashboards, fake analytics, accounts/RBAC,
  ingestion UI, live provider selection from the browser, provider keys, a component framework,
  remote fonts/assets, copied competitor visuals, decorative animation, or an unrelated backend
  refactor.

## Acceptance evidence

- [ ] The browser tab, product header, empty states, and documentation use the original SVG mark;
      favicon and accessible-name behavior pass automated browser checks.
- [ ] All four real destinations support direct navigation, browser back/forward, visible current
      location, correct document title/heading, keyboard use, and a small-screen navigation mode.
- [ ] A first-time user can select a friendly corpus/index and complete Inspect without typing or
      understanding a UUID; hashes/UUIDs are absent from primary UI and available in technical
      details for reproducibility.
- [ ] Overview and Inspect explain the real data flow and clearly distinguish fixture mechanics,
      real retrieval evidence, and governed live evidence without claiming deployment or quality.
- [ ] Evaluation summary → regression list → case/evidence drill-down works without blank or
      irrelevant columns and has explicit loading, empty, partial, and failure states.
- [ ] HTTP/SSE failures map to stable safe codes. A Playwright-blocked request reaches the bounded
      timeout state, stops all busy indicators, supports retry, and produces no stale completion.
- [ ] Axe plus keyboard, focus, 320px/768px reflow, 200% zoom, forced-colors, reduced-motion, and
      content-safety tests pass; the manual accessibility record is updated only for checks a human
      actually performs.
- [ ] `./scripts/check.ps1`, focused API contract tests, component tests, and Playwright flows pass
      from a clean checkout before the controlled `0.10.0` bump and again afterward.

## Required tests and review

- Contract tests for any bounded read-only catalog projection and human-label/internal-ID mapping.
- Component tests for routes, status/help components, technical disclosure, problem mapping,
  timers, cancellation, retry, and stale-response suppression.
- Playwright happy-path and network-blocked/offline/malformed/server-error flows at desktop and
  small viewports, with axe and keyboard/focus assertions.
- Visual review against the committed token/identity guide at 320px, 768px, desktop, 200% zoom,
  forced colors, dark OS preference if supported, and reduced motion. Do not approve rows that were
  not manually exercised.

## Expected file ownership

- `apps/web/index.html`, `apps/web/public/`, `apps/web/src/`, focused web tests/E2E, and the minimum
  read-only API/application projection plus OpenAPI/tests needed for friendly selection.
- `docs/product/`, `docs/accessibility/`, `README.md`, `BLUEPRINT.md`, changelog, and controlled
  product-version surfaces only after pre-bump verification.

## Stop conditions

- A proposed view requires fake/unimplemented data, a new UI framework/design system dependency,
  ingestion/mutation, authentication, browser provider secrets, or a change to evidence identity.
- Backend error contracts cannot support the needed safe client state without a separately reviewed
  contract change, or manual accessibility review cannot be truthfully completed.

## Agent and scope control

Use one implementation agent. Do not create subagents: this story has one tightly coupled frontend
identity/state owner, and parallel writers would create inconsistent design tokens and error rules.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; stop if the profile is unavailable. Version action: verify the latest accepted `main` is exactly `0.9.0`; implement and pass every pre-bump gate, then apply only the minor bump to `0.10.0` through `docs/WORKFLOW.md` controlled surfaces and rerun all checks. Work only on EG-017 on `feat/eg-017-product-experience`. Read `AGENTS.md`, complete `BLUEPRINT.md`, `docs/product/UX-RESEARCH.md`, ADR-0005, ADR-0009, the HTTP/OpenAPI/SSE contracts, EG-011 and EG-013B evidence, and this story. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Build the original SVG mark/favicon, persistent responsive shell, Overview/Inspect/Evaluations/System-evidence views, friendly catalog selection, progressive technical disclosure, durable design tokens, and typed finite frontend failure/recovery states. Make the product explain corpus → retrieval → answer/citation → release gate without becoming a chat clone. Use human-readable labels first; retain UUID/hash identity only in technical details and machine contracts. Add no fake navigation/data, ingestion UI, account system, browser secret, provider selector, framework/icon/font dependency, copied brand, speculative abstraction, unrelated refactor, or later-story model comparison. Reproduce the blocked-request problem and prove timeout, cancellation, retry, and stale-response handling with tests. Run focused contract/component/E2E/accessibility/responsive/content-safety checks and the full repository matrix before and after the version bump. Update docs and manual-review rows truthfully. Do not merge, push, deploy, spend, call a provider, tag/release, or start another story. Use one agent and no subagents. Finish with the UX architecture, state/error mapping, changed files, exact checks, accessibility evidence/limitations, version handoff, and suggested commit message.
