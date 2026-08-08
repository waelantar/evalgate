# EG-013B: Accessibility and browser-content safety

- Status: Planned; EG-013 epic child
- Branch: `feat/eg-013b-accessibility-safety`
- Depends on: EG-008 and EG-011 merged to `main`
- Release: R3
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

> Work only on EG-013B on branch `feat/eg-013b-accessibility-safety`. Read `AGENTS.md`, `BLUEPRINT.md`, the web/stream/results contracts, and this story. Confirm EG-008 and EG-011 are merged to clean `main`. Audit and harden the entire supported answer and results UI for keyboard/focus/live-region/zoom/contrast/reduced-motion behavior and centralized safe content/link rendering; add automated and documented manual evidence. Do not redesign the product, add a UI framework, or claim full conformance beyond evidence. Do not merge, push, or deploy. Finish with accessibility/content-safety explanation, changed files, exact results/manual checklist, limitations, and suggested commit message.
