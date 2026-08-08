"""Guard the framework-independent package boundaries."""

import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {"fastapi", "mcp", "openai", "sqlalchemy"}
PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "evalgate"


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])
    return roots


def test_domain_and_application_do_not_import_frameworks() -> None:
    violations: list[str] = []
    for layer in ("domain", "application"):
        for path in (PACKAGE_ROOT / layer).rglob("*.py"):
            forbidden = _import_roots(path) & FORBIDDEN_IMPORTS
            if forbidden:
                violations.append(f"{path.relative_to(PACKAGE_ROOT)}: {sorted(forbidden)}")

    assert not violations, "Forbidden framework imports:\n" + "\n".join(violations)
