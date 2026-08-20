# Branch, review, and manual-merge workflow

The setup commit lives on `main`. Every implementation story is completed on its own branch and is merged manually only after the repository owner understands and accepts the change.

## One-story rule

- One story or EG-013 sub-story per branch.
- Branch from the latest accepted `main`, never from an unmerged sibling branch.
- Do not combine opportunistic refactors, dependency upgrades, or another story.
- Contract or ADR changes are reviewed before code that depends on them.
- The coding agent may implement, test, explain, and prepare commits. It must not merge, push, or delete the branch. External calls, spending, and deployment are forbidden unless the assigned EG-015 or EG-016 gate has explicit repository-owner authorization for the named action.

## Execution profile and scope budget

Every story declares one Codex model and reasoning effort. `gpt-5.6-sol` is the literal model identifier for the Sol model; do not use `gpt-5.6-solar`. The listed profile is a fixed launcher setting, not permission to self-escalate. If it is unavailable or a concrete test/review finding suggests more reasoning is required, stop and ask the repository owner before changing model or effort.

Implement the minimum code, tests, documentation, and evidence needed for the accepted scope. Cover acceptance-relevant success, failure, boundary, security/privacy, and recovery behavior. Do not invent speculative edge cases, pre-build later stories, add optional architecture/frameworks/services/dependencies, or refactor unrelated code. A missing decision is a stop condition, not an invitation to design beyond the brief.

The Codex profile never grants authority for external actions. EG-015 provider calls and EG-016 resource creation/deployment still require their separate explicit approvals.

## Product-version handoff

EvalGate uses a serialized product-version path following Semantic Versioning. Before `1.0.0`, a minor bump introduces a new observable API, CLI, UI, integration, or distributable capability; a patch bump introduces compatible internal foundation, evidence, governance, or hardening. EG-014 alone may establish `1.0.0`, and only after every R3 release gate passes. After `1.0.0`, normal Semantic Versioning applies.

Each story's literal target assumes the acceptance order in `docs/backlog/README.md`. Even when implementation can be investigated in parallel, the shared version step is serialized. Before touching version metadata, confirm that the branch starts from the declared predecessor on the latest accepted `main`. If it differs, do not reuse, decrement, or guess a version; stop so the plan can be reconciled.

First complete the safe pre-bump implementation checks and resolve their findings. Apply the declared version as the final source change before generating final evidence that records the product version or code identity. Then synchronize only these product-version surfaces as applicable:

- `apps/api/pyproject.toml` and the editable project record in `apps/api/uv.lock`;
- `apps/api/src/evalgate/__init__.py`;
- `apps/web/package.json` and the root-package entries in `apps/web/package-lock.json`;
- OpenAPI product metadata, runtime health metadata, and their direct assertions;
- `CHANGELOG.md` under `Unreleased`, plus release evidence when the owning story requires it.

Discover and inspect the exact occurrences; never use a repository-wide version replacement. API-major paths, stream/event schemas, corpus/index/dataset/prompt versions, evaluation-artifact schemas, image digests, and deployment revisions are independent identifiers. After the bump, rerun the complete required checks and regenerate affected final evidence. If a final gate fails, restore the predecessor metadata in the story branch and report the blocker; a failed, blocked, or abandoned story consumes no version. Coding agents never tag or publish a release.

When an artifact embeds the product version, run pre-bump implementation checks first, apply the declared version, then build and validate the final version-bearing artifact. Only post-bump evidence is acceptance evidence for that artifact. EG-013D therefore produces the `0.9.0` release candidate; EG-014 conditionally establishes `1.0.0` and rebuilds/scans the final image from unchanged accepted definitions.

EG-016 is deliberately different: it does not bump the product or rebuild the image. It promotes the already accepted and scanned R3 `1.0.0` digest and records deployment revision, environment, digest, and verification time separately. Any required runtime change stops EG-016 and becomes a separately reviewed patch release.

## Branch names

Use the exact branch in each `docs/backlog/EG-*.md` brief:

```text
feat/eg-002-provider-ports
feat/eg-003-postgres-schema
fix/eg-007-stream-cancellation
docs/eg-014-release-evidence
```

The prefix is `feat/` for planned capability, `fix/` for a defect discovered within an accepted story, `docs/` for documentation-only work, and `chore/` for tooling-only work.

## Start a story

```powershell
git switch main
git status --short
git switch -c feat/eg-002-provider-ports
```

If a remote exists later, update `main` with the agreed non-destructive command before creating the branch. Start only with a clean worktree. Give the coding agent the implementation brief from the story file.

## Review before merge

The coding agent must finish with:

1. changed files grouped by purpose;
2. architecture and data-flow explanation;
3. commands run and exact results;
4. acceptance-criteria mapping;
5. security, privacy, accessibility, operations, and rollback notes;
6. assumptions, limitations, and unresolved decisions;
7. a suggested Conventional Commit message;
8. the predecessor, bump type, target, synchronized version surfaces, and confirmation that no tag/release was created;
9. an explicit statement that it did not merge, push, or delete the branch; if an EG-015/EG-016 gate was approved, exact external actions and cost, otherwise confirmation that it did not deploy or call a paid provider.

Then inspect the diff and history:

```powershell
git status --short
git diff --check
git diff main...HEAD
git log --oneline main..HEAD
```

Ask questions until every material design and code path is understood. Run the story's checks yourself when practical.

## Manual merge

Only after approval:

```powershell
git switch main
git merge --no-ff feat/eg-002-provider-ports
```

Run the required checks again on `main`. Delete the local branch only after the merge and verification:

```powershell
git branch -d feat/eg-002-provider-ports
```

Do not merge a story whose dependency is not already on `main`. Do not use `git reset --hard`, force-push, or an automatic baseline update as part of this workflow.

## Recovery

If a branch is not acceptable, leave `main` unchanged. Create a follow-up commit on the same branch or abandon it after preserving any evidence needed for review. If a merged change must be undone, prefer a reviewed revert commit so the decision remains visible.
