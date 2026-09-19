# EG-019: Product-shell polish and governed data onboarding

- Status: Merged to `main` at `0.12.0`; product-shell checks pass, while EG-014 release gates remain open
- Branch: `feat/eg-019-product-shell-onboarding`
- Depends on: EG-018 merged to `main`
- Release: R3
- Version action: Minor `0.11.0 -> 0.12.0`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: G-03/09, FR-04/05/08/12/13, NFR-05/06

## Outcome

A first-time local user can understand what EvalGate is, navigate it on desktop or mobile, switch between accessible light and dark themes, use consistent controls, see exactly how to bring a governed corpus into the current product, and distinguish available local workflows from future hosted capabilities.

## Scope

- Consolidate the product shell around one neutral Notion/Twenty-inspired token system without copying either product's trade dress: typography, spacing, radius, surfaces, borders, status colors, focus, hover, light theme, and dark theme.
- Make the original EvalGate mark and navigation legible in both themes; provide a responsive menu, persistent current-location state, keyboard behavior, and a theme choice that survives reload.
- Use the existing Radix Select dependency for every product picker. Remove native/dropdown styling drift, mojibake glyphs, oversized menus, and theme-inconsistent hover/focus/selected states.
- Add a truthful `Bring data` explanation route. It must describe the current manifest + local ingestion + reviewed-case workflow, keep identifiers in technical details, and never imply that a browser upload or hosted workspace exists.
- Present `Self-serve browser upload`, `Account workspace`, and `Hosted private storage` only as clearly labeled future product lanes with their required architecture/security gates. They are not implemented or available in this story.
- Preserve the EG-018 read-only Showcase inside the same shell without changing its source, model, evaluation, cost, or quality evidence.
- Normalize responsive behavior, content hierarchy, tooltips, links, empty/error states, favicon, and the local-fixture indicator across every existing route.

## Architecture decision gate for future self-serve work

Browser upload, accounts, and hosted private storage cross the current local-workbench boundary. Before any implementation, a separate accepted ADR must decide:

1. single-tenant versus multi-tenant ownership and isolation;
2. identity provider, session, role, invite, and recovery model;
3. encrypted object storage, database tenancy, key management, backup, deletion, and retention;
4. malware/content-type/size scanning and archive/path traversal controls;
5. personal/proprietary-data policy, region, subprocessors, telemetry, and audit log;
6. asynchronous ingestion state machine, idempotency, quota, failure recovery, and cost controls;
7. public/deployed capability and operational ownership.

Until that ADR is accepted, the three hosted lanes remain roadmap evidence only. Do not add a fake upload control, fake account menu, fake storage state, or browser provider key.

## Non-goals

- Implementing uploads, authentication, RBAC, billing, tenant isolation, cloud/object storage, queues, background workers, deployment, or provider execution from the browser.
- Changing corpus/evaluation contracts, model results, source provenance, regression baselines, or EG-018 claims.
- Copying competitor assets, layouts, wording, or distinctive visual trade dress; adding remote fonts, an icon framework, or another component system.
- Hiding technical details, weakening accessibility, or representing planned capabilities as shipped.

## Acceptance evidence

- [ ] Every existing route uses the same light/dark tokens with no legacy palette traces; contrast, focus, hover, selected, disabled, error, and forced-color states remain legible.
- [x] Navigation collapses to an accessible menu at the reviewed breakpoint and works by keyboard at 320px, 768px, and desktop.
- [ ] Every picker uses the shared Radix component and passes keyboard, screen-reader name, viewport, scroll, hover, selected-state, and theme tests with no malformed glyphs.
- [ ] Theme preference persists without hydration flash, remains usable when storage is unavailable, and does not change semantic status meaning.
- [x] `Bring data` explains the real current local workflow and marks upload/account/storage as unavailable future lanes; no mutation endpoint or secret exists in the web bundle.
- [x] EG-018 Showcase content and hashes remain unchanged except for shell presentation; all evaluation numbers are sourced from tracked evidence.
- [x] Component tests, Playwright/axe responsive flows, production build, publication/privacy checks, and the full repository check pass before and after the controlled `0.12.0` bump.

## Implemented evidence

- Pre-bump and post-bump `scripts/check.ps1` passed. The post-bump run covered publication, metadata, release-static, Ruff, mypy, 215 API tests, 37 web unit tests, eight Chromium/axe flows, and the production Vite build at `0.12.0`.
- The added unit/browser checks prove night-mode persistence and verify that the three hosted roadmap lanes expose no upload button or file input.
- The current local workflow is explicit: governed files, manifest, local ingestion, reviewed questions, then comparable evaluation. No upload, account, tenant storage, mutation endpoint, browser secret, deployment, or hosted-service claim was added.
- Manual screen-reader, 200% zoom, forced-colors, and visual review across all routes remain release evidence for the owner; the unchecked acceptance rows are intentionally not auto-approved.
## Required tests and review

- Component tests for routes, theme persistence/fallback, responsive-menu state, shared pickers, and truthful capability labels.
- Playwright keyboard/focus/axe flows in light/dark mode at 320px, 768px, and desktop; browser back/forward and reload on every route.
- Visual review for light/dark contrast, hover/focus/selected/error states, 200% zoom, forced colors, reduced motion, long labels, and offline/blocked requests.
- Bundle and route review proving no upload/account/storage mutation, secret, remote asset, or provider-run control was introduced.

## Stop conditions

- Work requires a new authentication, storage, queue, cloud, tenancy, or deployment architecture without an accepted ADR and explicit owner approval.
- A planned capability would be presented as shipped, a competitor's visual identity would be copied, or EG-018 evidence would be altered to improve the story.
- The predecessor is not merged at exactly `0.11.0`, the assigned Codex profile is unavailable, or a full check exposes an unrelated release blocker.

## Agent and scope control

Use one implementation agent. Product-shell tokens, responsive behavior, and onboarding truthfulness need one accountable owner. Do not create subagents.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; stop if unavailable. Version action: verify the accepted predecessor is `0.11.0`, pass pre-bump checks, apply only `0.12.0` through `docs/WORKFLOW.md`, then rerun version-bound checks. Work only on EG-019 on branch `feat/eg-019-product-shell-onboarding` after EG-018 is reviewed and merged at exactly `0.11.0`. Read `AGENTS.md`, the complete `BLUEPRINT.md`, `docs/product/UX-RESEARCH.md`, EG-017, EG-018, and this story. First inventory and remove legacy style traces, then implement one neutral light/dark token system, legible mark/navigation, responsive accessible menu, shared Radix picker states, and a truthful `Bring data` route that explains current local ingestion while labeling self-serve upload, account workspace, and hosted private storage as unavailable future lanes. Preserve EG-018 evidence unchanged. Do not implement or fake upload, authentication, RBAC, tenant storage, cloud services, queues, billing, deployment, browser provider execution, or secrets; those require a separately accepted ADR and owner gates. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not add another framework, remote assets/fonts, copied competitor trade dress, or unrelated refactors. Run component, Playwright/axe/responsive/theme, build, publication/privacy, and full repository checks before applying the controlled minor bump `0.11.0 -> 0.12.0`, then rerun version-bound checks. Do not merge, create a tag/release, push, deploy, spend, or start EG-014. Finish with changed files, exact checks, manual-review limits, version handoff, and suggested commit message.
