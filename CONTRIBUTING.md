# Contributing

Read `BLUEPRINT.md`, `AGENTS.md`, the relevant ADRs, and the assigned story brief before making a change.

## Workflow

1. Start from an issue or `docs/backlog/EG-*.md` brief with satisfied dependencies.
2. Create the exact focused branch from the story, such as `feat/eg-005-hybrid-retrieval`.
3. Change contracts and ADRs before code that depends on them.
4. Add tests and evidence required by the story.
5. Run `scripts/check.ps1` or `scripts/check.sh`.
6. Open a pull request using the template and link the story, requirement IDs, evidence, and risks.

The coding agent must stop before merge or push. The repository owner reviews the branch, asks for a complete explanation, reruns the relevant evidence, and performs a manual `--no-ff` merge using `docs/WORKFLOW.md`.

Use Conventional Commit subjects. Keep commits small enough to review and do not combine unrelated cleanup with a story.

## Status and evidence

Do not mark a feature verified without a reproducible command and result. Do not represent deterministic fixture output as retrieval or generation quality. Never update a reviewed baseline automatically or without a change record.

## Data and privacy

Do not add personal, confidential, scraped, or proprietary data. New corpus content needs an approved manifest and license. Remove machine-specific absolute paths and metadata from public artifacts.
