"""Check Python and C style before preparing a release."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="Apply formatting and safe lint fixes")
    args = parser.parse_args(argv)

    if importlib.util.find_spec("ruff") is None:
        parser.error('Install development tools first: python -m pip install -e ".[dev]"')
    clang = shutil.which("clang-format")
    if clang is None:
        name = "clang-format.exe" if sys.platform == "win32" else "clang-format"
        candidate = Path(sys.executable).parent / name
        if candidate.is_file():
            clang = str(candidate)
    if clang is None:
        parser.error('clang-format is missing; install the project’s ".[dev]" dependencies')

    ruff = [sys.executable, "-m", "ruff"]
    native = sorted(path for path in (ROOT / "native").iterdir() if path.suffix in {".c", ".h"})
    if args.fix:
        commands = [
            [*ruff, "format", "."],
            [*ruff, "check", ".", "--fix"],
            [*ruff, "format", "."],
            [clang, "-i", *map(str, native)],
        ]
    else:
        commands = [
            [*ruff, "check", "."],
            [*ruff, "format", ".", "--check"],
            [clang, "--dry-run", "--Werror", *map(str, native)],
        ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
