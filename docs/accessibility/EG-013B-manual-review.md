# EG-013B accessibility and browser-content-safety review

## Scope and evidence boundary

This record covers the supported local inspection and read-only evaluation-results views in
EvalGate `0.8.2`. It documents the evidence gathered for EG-013B; it is not a WCAG
conformance claim or a substitute for a formal accessibility audit.

## Executed automated browser review

- Browser engine: Playwright-managed Chromium, using the repository's pinned Playwright test
  dependency and the local Vite application.
- Viewports: the normal desktop project and a 320-by-720 CSS-pixel reflow case.
- Assistive setup: axe-core browser analysis. No screen-reader software was automated or claimed
  as tested.
- Checks: heading/label semantics and axe analysis for the results view; keyboard Ask and citation
  activation; focus transfer to the cited evidence article; inert model/corpus HTML and
  `javascript:` content; 320-pixel reflow; and reduced-motion citation navigation.

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
| Keyboard flow | Chromium, keyboard only | Tab order reaches Question, Index version, Ask, Cancel, citations, and results controls; Enter/Space activate buttons. | Automated coverage; human spot-check pending. |
| Answer status and cancellation | Chromium plus a screen reader selected by the reviewer | One concise state announcement per phase; streamed answer tokens are not repeatedly announced; cancellation announces `Cancelled`. | Screen-reader review pending. |
| Error recovery | Chromium plus the selected screen reader | A safe error is announced and receives focus; Retry is reachable and returns to a usable results view. | Browser focus automated; screen-reader review pending. |
| Citation navigation | Chromium, keyboard only | Activating a citation moves focus to its evidence article, with visible focus styling. | Automated coverage; human spot-check pending. |
| Zoom and reflow | Chromium at 200% browser zoom and 320 CSS pixels | No loss of content or controls and no required horizontal page scrolling. | 320-pixel automated; 200% manual review pending. |
| Contrast and reduced motion | Chromium with forced-colors/high-contrast setting and `prefers-reduced-motion: reduce` | Text, controls, and focus indicators remain distinguishable; citation navigation avoids smooth movement when reduced motion is requested. | Reduced motion automated; forced-colors review pending. |

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
