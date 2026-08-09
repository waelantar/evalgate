"""Validate repository metadata without network access."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "node_modules", "dist", "coverage", ".cache"}
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
ACTION_REF = re.compile(r"^\s*-\s+uses:\s+[^@\s]+@([^\s#]+)", re.MULTILINE)
SHA = re.compile(r"^[a-f0-9]{40}$")
STORY_PROFILE = re.compile(
    r"^- Codex profile: `([^`]+)` with `(low|medium|high)` reasoning$",
    re.MULTILINE,
)
STORY_VERSION = re.compile(r"^- Version action: (.+)$", re.MULTILINE)
SEMVER = re.compile(r"\b\d+\.\d+\.\d+\b")
ALLOWED_STORY_PROFILES = {
    "gpt-5.5": {"low", "medium", "high"},
    "gpt-5.6-luna": {"low", "medium", "high"},
    "gpt-5.6-terra": {"low", "medium", "high"},
    "gpt-5.6-sol": {"low", "medium", "high"},
}
COPY_PASTE_HEADING = "## Copy-paste coding-agent brief"
SCOPE_GUARD = (
    "Implement only cases explicitly required by this story, accepted contracts/ADRs, "
    "or an observed failing test. Do not invent speculative edge cases, future-proof "
    "abstractions, new dependencies/frameworks, opportunistic refactors, later-story "
    "work, or silent contract/architecture decisions; stop and report instead."
)


def is_included(path: Path) -> bool:
    return path.is_file() and not any(part in EXCLUDED_PARTS for part in path.parts)


def validate_json() -> list[str]:
    failures: list[str] = []
    for path in ROOT.rglob("*.json"):
        if not is_included(path) or path.name == "package-lock.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            failures.append(f"{path.relative_to(ROOT)}: invalid JSON: {error}")
    return failures


def validate_markdown_links() -> list[str]:
    failures: list[str] = []
    for path in ROOT.rglob("*.md"):
        if not is_included(path):
            continue
        content = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(content):
            target = match.group(1).strip().strip("<>")
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative_target = unquote(target.split("#", maxsplit=1)[0])
            if not relative_target:
                continue
            resolved = (path.parent / relative_target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                failures.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                line = content.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: missing link target: {target}")
    return failures


def validate_action_pins() -> list[str]:
    failures: list[str] = []
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        content = path.read_text(encoding="utf-8")
        for match in ACTION_REF.finditer(content):
            reference = match.group(1)
            if not SHA.fullmatch(reference):
                line = content.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: action is not SHA-pinned")
    return failures


def validate_story_briefs() -> list[str]:
    failures: list[str] = []
    for path in sorted((ROOT / "docs" / "backlog").glob("EG-*.md")):
        relative = path.relative_to(ROOT)
        content = path.read_text(encoding="utf-8")
        profiles = STORY_PROFILE.findall(content)
        version_actions = STORY_VERSION.findall(content)

        if len(profiles) != 1:
            failures.append(f"{relative}: expected exactly one Codex profile metadata line")
            continue
        if len(version_actions) != 1:
            failures.append(f"{relative}: expected exactly one version action metadata line")
            continue
        if content.count(COPY_PASTE_HEADING) != 1:
            failures.append(f"{relative}: expected exactly one copy-paste brief")
            continue

        model, effort = profiles[0]
        if effort not in ALLOWED_STORY_PROFILES.get(model, set()):
            failures.append(f"{relative}: unsupported Codex profile {model}/{effort}")

        prompt = content.split(COPY_PASTE_HEADING, maxsplit=1)[1]
        profile_instruction = (
            f"Execution profile (configure before starting): `{model}`, "
            f"reasoning effort `{effort}`."
        )
        if profile_instruction not in prompt:
            failures.append(f"{relative}: prompt does not repeat its exact Codex profile")
        if "Do not substitute the model or raise effort" not in prompt:
            failures.append(f"{relative}: prompt lacks the model/effort escalation boundary")
        if "Version action:" not in prompt:
            failures.append(f"{relative}: prompt lacks its version action")
        for version in set(SEMVER.findall(version_actions[0])):
            if version not in prompt:
                failures.append(
                    f"{relative}: prompt does not repeat planned product version {version}"
                )
        if SCOPE_GUARD not in prompt:
            failures.append(f"{relative}: prompt lacks the canonical bounded-scope guard")
        if "tag/release" not in prompt:
            failures.append(f"{relative}: prompt does not forbid agent-created releases")

    return failures


def main() -> int:
    failures = (
        validate_json()
        + validate_markdown_links()
        + validate_action_pins()
        + validate_story_briefs()
    )
    if failures:
        print("Metadata check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(
        "Metadata check passed: JSON, local Markdown links, action pins, and story "
        "execution controls are valid."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
