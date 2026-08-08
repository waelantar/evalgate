# Branch, review, and manual-merge workflow

The setup commit lives on `main`. Every implementation story is completed on its own branch and is merged manually only after the repository owner understands and accepts the change.

## One-story rule

- One story or EG-013 sub-story per branch.
- Branch from the latest accepted `main`, never from an unmerged sibling branch.
- Do not combine opportunistic refactors, dependency upgrades, or another story.
- Contract or ADR changes are reviewed before code that depends on them.
- The coding agent may implement, test, explain, and prepare commits. It must not merge, push, or delete the branch. External calls, spending, and deployment are forbidden unless the assigned EG-015 or EG-016 gate has explicit repository-owner authorization for the named action.

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
8. an explicit statement that it did not merge, push, or delete the branch; if an EG-015/EG-016 gate was approved, exact external actions and cost, otherwise confirmation that it did not deploy or call a paid provider.

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
