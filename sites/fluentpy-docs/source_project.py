"""Locate FluentPy when this website is bundled or checked out independently."""

from __future__ import annotations

import ast
import os
from pathlib import Path

SITE = Path(__file__).resolve().parent


def source_root() -> Path:
    """Find library sources for API extraction and real Qt preview capture."""
    configured = os.environ.get("FLUENTPY_SOURCE_ROOT")
    candidates = (
        [Path(configured).expanduser()]
        if configured
        else [
            SITE.parents[1],
            SITE.parent / "FluentPy",
            SITE.parent / "fluentpy",
        ]
    )
    for candidate in candidates:
        root = candidate.resolve()
        if (root / "src/fluentpy/__init__.py").is_file():
            return root
    raise FileNotFoundError(
        "FluentPy source checkout was not found. Clone XDDXMT/FluentPy beside "
        "FluentPy-Docs or set FLUENTPY_SOURCE_ROOT to its absolute path. "
        "Serving the existing dist/ does not require library sources."
    )


def repository_root() -> Path:
    """Keep deployment artifacts inside the repository that owns this website."""
    bundled = SITE.parents[1]
    return bundled if (bundled / "src/fluentpy/__init__.py").is_file() else SITE


def source_version() -> str:
    """Read the public version without importing Qt or loading a C extension."""
    tree = ast.parse((source_root() / "src/fluentpy/__init__.py").read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise ValueError("The component checkout does not declare __version__.")
