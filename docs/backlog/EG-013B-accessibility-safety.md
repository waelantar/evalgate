# EG-013B: Accessibility and browser-content safety

- Status: Planned; EG-013 epic child
- Branch: `feat/eg-013b-accessibility-safety`
- Depends on: EG-008 and EG-011 merged to `main`
- Release: R3
- Version action: Patch `0.8.1 -> 0.8.2`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: NFR-05, NFR-06

## Outcome

The complete supported web flow meets WCAG 2.2 AA evidence expectations and renders all corpus/model content through a constrained, tested presentation boundary.

## Scope

- Audit/fix semantics, keyboard order, focus management, live regions, errors, cancellation, citation navigation, contrast, zoom/reflow, touch targets, and reduced motion.
- Central safe-rendering/link policy with raw HTML disabled and allowlisted schemes.
- Component, axe, keyboard, and Playwright accessibility/security tests.
- Manual screen-reader/zoom/contrast checklist with environment and limitations.

## Non-goals

- Visual redesign, new component/design framework, localization, native mobile app, or unsupported WCAG conformance claim.

## Acceptance evidence

- [ ] Automated checks and all critical keyboard flows pass for ask, cancel, error, evidence, and results views.
- [ ] Focus/live announcements are understandable without duplicated token noise.
- [ ] XSS payloads, unsafe links, raw HTML, and model-authored fake citations remain inert.
- [ ] Manual review record names tested browsers/assistive setup and remaining limitations.

## Required tests and review

- Run component, axe, keyboard, safe-rendering, unsafe-link, fake-citation, zoom/reflow, reduced-motion, and Playwright answer/results flows; complete the documented manual browser/assistive-technology review.

## Expected file ownership

- Central web rendering/link policy, answer/results accessibility fixes, focused component and E2E tests, accessibility fixtures, and a versioned manual review record.

## Stop conditions

- A new UI/design framework, contract change, or inaccessible third-party component is required.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.8.1` on the latest accepted `main`, apply only the declared patch to `0.8.2` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-013B on branch `feat/eg-013b-accessibility-safety`. Read `AGENTS.md`, `BLUEPRINT.md`, the web/stream/results contracts, and this story. Confirm EG-008 and EG-011 are merged to clean `main`. Audit and harden the entire supported answer and results UI for keyboard/focus/live-region/zoom/contrast/reduced-motion behavior and centralized safe content/link rendering; add automated and documented manual evidence. Do not redesign the product, add a UI framework, or claim full conformance beyond evidence. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, tag/release, or start another story. Finish with accessibility/content-safety explanation, changed files, exact results/manual checklist, limitations, version handoff, and suggested commit message.
