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


def main() -> int:
    failures = validate_json() + validate_markdown_links() + validate_action_pins()
    if failures:
        print("Metadata check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Metadata check passed: JSON, local Markdown links, and action pins are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
