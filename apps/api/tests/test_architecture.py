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


def test_domain_and_application_keep_dependency_direction() -> None:
    violations: list[str] = []
    allowed_prefixes = {
        "domain": ("evalgate.domain",),
        "application": ("evalgate.application", "evalgate.domain"),
    }

    for layer, allowed in allowed_prefixes.items():
        for path in (PACKAGE_ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module_names: list[str] = []
                if isinstance(node, ast.Import):
                    module_names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_names.append(node.module)
                for module_name in module_names:
                    if module_name.startswith("evalgate.") and not module_name.startswith(allowed):
                        violations.append(f"{path.relative_to(PACKAGE_ROOT)} imports {module_name}")

    assert not violations, "Invalid internal dependency direction:\n" + "\n".join(violations)
