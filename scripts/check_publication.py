"""Fail on machine-specific paths or process artifacts unsafe for publication."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "node_modules", "dist", "coverage", ".cache"}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mako",
    ".py",
    ".ps1",
    ".sh",
    ".toml",
    ".tsx",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}

PATTERNS = {
    "Windows user path": re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s]+", re.IGNORECASE),
    "Unix user path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
    "email address": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    ),
    "URL credential": re.compile(r"https?://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE),
}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.name in {"uv.lock", "package-lock.json"}:
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {
            ".editorconfig",
            ".env.example",
            ".gitattributes",
            ".gitignore",
            ".nvmrc",
            ".python-version",
            "LICENSE",
            "Makefile",
        }:
            files.append(path)
    return files


def main() -> int:
    failures: list[str] = []
    for path in iter_text_files():
        content = path.read_text(encoding="utf-8")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {label}")

    if failures:
        print("Publication check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"Publication check passed for {len(iter_text_files())} text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
