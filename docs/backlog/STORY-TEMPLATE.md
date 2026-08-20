# EG-XXX: Story title

- Status: Planned
- Branch: `type/eg-xxx-short-name`
- Depends on:
- Release:
- Version action: `<Patch|Minor|First stable|None>: <predecessor> -> <target>`
- Codex profile: `<model>` with `<low|medium|high>` reasoning
- Blueprint requirements:

## Outcome

One observable outcome.

## Scope

- Included change.

## Non-goals

- Explicit exclusion.

## Acceptance evidence

- [ ] Observable criterion and reproducing command.

## Required tests and review

- Test layer and failure path.

## Expected file ownership

- Path ownership, not a mandate to change every file.

## Stop conditions

- Decision that requires owner approval or a new ADR.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `<model>`, reasoning effort `<low|medium|high>`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after pre-bump implementation checks pass and before final version-bound evidence, verify `<predecessor>` on the latest accepted `main`, apply only the declared `<patch|minor|first-stable|none>` action to `<target>` through the controlled surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun the complete required checks; if the predecessor or a final gate differs, restore/retain the predecessor and stop. Work only on EG-XXX on branch `type/eg-xxx-short-name`. Read `AGENTS.md`, `BLUEPRINT.md`, the linked ADRs/contracts, and this story first. Confirm dependencies are on `main` and the worktree is clean. Implement only the stated scope with acceptance tests and update traceability/status honestly. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, spend, call a paid provider, update a baseline automatically, tag/release, or start another story. Stop at every listed decision gate. Finish by explaining the design and data flow, listing changed files, mapping acceptance evidence, reporting exact commands/results and residual risks, reporting the version handoff, suggesting a commit message, and stating explicitly that no merge or external action occurred.
