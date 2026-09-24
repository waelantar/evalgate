# EG-013B accessibility and browser-content-safety review

## Scope and evidence boundary

This record covers the supported local inspection and read-only evaluation-results views. The
automated suite was rerun successfully on EvalGate `0.12.3` and covers the persistent
product shell, friendly source selector, direct routes, finite timeout recovery, responsive menu,
and theme persistence. It documents automated evidence for EG-013B/EG-017/EG-019; it is not a WCAG
conformance claim or a substitute for a formal accessibility audit.

## Executed automated browser review

- Browser engine: Playwright-managed Chromium, using the repository's pinned Playwright test
  dependency and the local Vite application.
- Viewports: the normal desktop project and a 320-by-720 CSS-pixel reflow case.
- Assistive setup: axe-core browser analysis. No screen-reader software was automated or claimed
  as tested.
- Checks: heading/label semantics and axe analysis for overview, inspection, and results views;
  keyboard Inspect and citation activation; focus transfer to the cited evidence article; inert
  model/corpus HTML and `javascript:` content; direct navigation; blocked-request timeout/retry;
  320-pixel reflow; and reduced-motion citation navigation.

The repeatable command is:

```powershell
Set-Location apps/web
npm.cmd run test:e2e
```

## Manual owner checklist

The following requires a human using the target browser and assistive technology. It was not
represented as completed by the coding agent.

| Check | Setup | Expected result | Status |
| --- | --- | --- | --- |
| Keyboard flow | Chromium, keyboard only | Tab order reaches navigation, Evidence source, Your question, Inspect answer, Cancel request, citations, and results controls; Enter/Space activate buttons. | Automated coverage; human spot-check pending. |
| Answer status and cancellation | Chromium plus a screen reader selected by the reviewer | One concise state announcement per phase; streamed answer tokens are not repeatedly announced; cancellation announces `Cancelled`. | Screen-reader review pending. |
| Error recovery | Chromium plus the selected screen reader | A safe error is announced and receives focus; Retry is reachable and returns to a usable results view. | Browser focus automated; screen-reader review pending. |
| Citation navigation | Chromium, keyboard only | Activating a citation moves focus to its evidence article, with visible focus styling. | Automated coverage; human spot-check pending. |
| Zoom and reflow | Chromium at 200% browser zoom and 320 CSS pixels | No loss of content or controls and no required horizontal page scrolling. | 320-pixel automated; 200% manual review pending. |
| Contrast and reduced motion | Chromium with forced-colors/high-contrast setting and `prefers-reduced-motion: reduce` | Text, controls, and focus indicators remain distinguishable; citation navigation avoids smooth movement when reduced motion is requested. | Reduced motion automated; forced-colors review pending. |

## EG-014 browser audit update (2026-09-24)

Browser-use/CDP inspection originally found one release-blocking responsive defect outside the
existing E2E coverage: long revision/path text made Showcase 367 CSS pixels wide at a 320px
viewport. EG-022 adds intrinsic-size containment and safe wrapping to flow cards. The expanded
Playwright test now verifies Overview, Inspect, Bring data, Evaluations, Showcase, and System
evidence at 320 by 720 CSS pixels; every document fits its layout viewport and the intentionally
wide comparison tables retain their own bounded scrollers. A 200%-zoom equivalent did not overflow
in the sampled desktop viewport, and forced-colors emulation activated, but those observations do
not replace the human review rows above.

The automated Showcase reflow blocker is closed. Every still-pending human row continues to block
the WCAG/release claim and is not marked complete or waived by EG-022.

## Content-safety policy

Corpus/model strings render only as React text nodes through
`apps/web/src/presentation/safeContent.ts`; the policy prohibits HTML parsing and
`dangerouslySetInnerHTML`. EvalGate has no corpus/model-authored outbound links. If a reviewed
future view needs one, `safeExternalHref` allows only absolute `https:` and `mailto:` URLs;
relative, `javascript:`, `data:`, and malformed URLs are rejected.

## Remaining limitations

- The record has no NVDA, Narrator, JAWS, or VoiceOver execution result. The repository owner
  must complete and date the screen-reader rows before any accessibility claim beyond this
  automated evidence.
- The browser suite is Chromium-only. Safari, Firefox, forced-colors, and mobile-device testing
  remain outside this story's executed evidence.
- Third-party content is not rendered in the supported UI; any future rich-text or external-link
  requirement needs a separate review before implementation.
