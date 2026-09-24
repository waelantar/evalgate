# EG-022: Close Showcase mobile reflow blocker

- Status: Completed and verified locally; pending owner review and manual merge
- Branch: `fix/eg-022-showcase-reflow`
- Depends on: EG-014 audit rerun merged to `main`
- Release: R3
- Version action: Patch `0.12.2 -> 0.12.3`
- Codex profile: `gpt-5.6-terra` with `low` reasoning
- Blueprint requirements: FR-13, NFR-06, and section 18 engineering-quality gates

## Outcome

Every primary route fits the 320 CSS-pixel layout viewport without page-level horizontal scrolling.
Long immutable revisions and source paths wrap inside the Showcase process cards, while intentionally
wide evidence tables retain their bounded local scrollers. Product metadata agrees at `0.12.3`.

## Scope

- Add intrinsic-size containment and safe wrapping to flow-list items.
- Extend the existing 320px Playwright check across Overview, Inspect, Bring data, Evaluations,
  Showcase, and System evidence.
- Reconcile the release record and accessibility evidence without claiming human screen-reader
  review.
- Apply patch `0.12.2 -> 0.12.3` only after the focused pre-bump frontend checks pass.

## Non-goals

- Visual redesign, content changes, new dependency, accessibility waiver, provider call, deployment,
  merge, push, tag, or stable `1.0.0` release.

## Acceptance evidence

- [x] Every primary route has `scrollWidth <= innerWidth` at 320 by 720 CSS pixels.
- [x] Showcase long revision/path text wraps without changing the intentionally scrollable tables.
- [x] The complete Chromium E2E/axe suite and frontend production build pass.
- [x] Full repository, integration, exact-image smoke, SBOM, and actionable scan gates pass at `0.12.3`.
- [x] Human accessibility rows remain explicit and are not marked complete by the coding agent.

## Expected file ownership

- `apps/web/src/styles.css` and the existing Playwright E2E file.
- Controlled product-version, image-evidence, backlog, workflow, and release-status surfaces.

## Stop conditions

- The fix needs a new layout system, dependency, content removal, table behavior change, or waiver.
- Any release, security, retrieval, integration, or version-consistency gate fails.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `low`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after focused pre-bump frontend checks pass, verify `0.12.2` on the latest accepted `main`, apply only the declared patch to `0.12.3` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun the complete required checks; if the predecessor or a final gate differs, restore/retain `0.12.2` and stop. Work only on EG-022 on branch `fix/eg-022-showcase-reflow`. Read `AGENTS.md`, `BLUEPRINT.md`, the release-readiness record, accessibility review, and this story first. Apply the narrow CSS containment fix and extend the existing 320px Playwright check across every primary route. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Run the complete repository, integration, image smoke, SBOM, and actionable scan gates. Keep intentionally wide tables locally scrollable. Do not redesign, waive human accessibility review, merge, push, deploy, spend, call a provider, tag/release, or start final EG-014. Stop on any failing gate. Finish with changed files, exact checks, manual-review limits, version handoff, and a suggested commit message.
