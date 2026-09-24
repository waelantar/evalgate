# EG-013B accessibility and browser-content-safety review

## Scope and evidence boundary

This record covers the supported local inspection and read-only evaluation-results views. The
automated suite was rerun successfully on EvalGate `1.0.0` and covers the persistent
product shell, friendly source selector, direct routes, finite timeout recovery, responsive menu,
and theme persistence. It documents automated evidence for EG-013B/EG-017/EG-019; it is not a WCAG
conformance claim or a substitute for a formal accessibility audit.

## Executed automated browser review

- Browser engine: Playwright-managed Chromium, using the repository's pinned Playwright test
  dependency and the local Vite application.
- Viewports: the normal desktop project and a 320-by-720 CSS-pixel reflow case.
- Automated assistive setup: axe-core browser analysis; no screen-reader software was automated.
- Human assistive setup: repository owner Wael Antar reported a passed review on 2026-09-24 using
  Chrome, Windows Narrator, 200% browser zoom, and Windows High Contrast.
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

The following was completed and reported by the repository owner on 2026-09-24. The coding agent
records that owner-supplied evidence and does not represent it as an automated result.

| Check | Setup | Expected result | Status |
| --- | --- | --- | --- |
| Keyboard flow | Chromium, keyboard only | Tab order reaches navigation, Evidence source, Your question, Inspect answer, Cancel request, citations, and results controls; Enter/Space activate buttons. | Passed by owner, 2026-09-24. |
| Answer status and cancellation | Chromium plus Windows Narrator | One concise state announcement per phase; streamed answer tokens are not repeatedly announced; cancellation announces `Cancelled`. | Passed by owner, 2026-09-24. |
| Error recovery | Chromium plus Windows Narrator | A safe error is announced and receives focus; Retry is reachable and returns to a usable results view. | Passed by owner, 2026-09-24. |
| Citation navigation | Chromium, keyboard only | Activating a citation moves focus to its evidence article, with visible focus styling. | Passed by owner, 2026-09-24. |
| Zoom and reflow | Chromium at 200% browser zoom and 320 CSS pixels | No loss of content or controls and no required horizontal page scrolling. | Passed by owner, 2026-09-24. |
| Contrast and reduced motion | Chromium with Windows High Contrast and `prefers-reduced-motion: reduce` | Text, controls, and focus indicators remain distinguishable; citation navigation avoids smooth movement when reduced motion is requested. | Passed by owner, 2026-09-24. |

## EG-014 browser audit update (2026-09-24)

Browser-use/CDP inspection originally found one release-blocking responsive defect outside the
existing E2E coverage: long revision/path text made Showcase 367 CSS pixels wide at a 320px
viewport. EG-022 adds intrinsic-size containment and safe wrapping to flow cards. The expanded
Playwright test now verifies Overview, Inspect, Bring data, Evaluations, Showcase, and System
evidence at 320 by 720 CSS pixels; every document fits its layout viewport and the intentionally
wide comparison tables retain their own bounded scrollers. The owner subsequently completed the
human review rows above. This closes the R3 manual review gate but is not a formal WCAG conformance
claim.

## Content-safety policy

Corpus/model strings render only as React text nodes through
`apps/web/src/presentation/safeContent.ts`; the policy prohibits HTML parsing and
`dangerouslySetInnerHTML`. EvalGate has no corpus/model-authored outbound links. If a reviewed
future view needs one, `safeExternalHref` allows only absolute `https:` and `mailto:` URLs;
relative, `javascript:`, `data:`, and malformed URLs are rejected.

## Remaining limitations

- The human assistive-technology result is owner-reported for Chrome, Windows Narrator, and Windows
  High Contrast; NVDA, JAWS, VoiceOver, Safari, Firefox, and mobile devices remain untested.
- This evidence is a bounded release gate, not a formal WCAG conformance audit.
- Third-party content is not rendered in the supported UI; any future rich-text or external-link
  requirement needs a separate review before implementation.
