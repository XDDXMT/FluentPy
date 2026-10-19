"""Build a reviewed sdist and isolated wheels. This script never uploads."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]


def run(*args, env=None):
    subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", type=Path, help="Use the local Windows x64 Zig compiler")
    parser.add_argument(
        "--native", action="store_true", help="Also require a wheel with the C extension"
    )
    args = parser.parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    name, version = project["name"], project["version"]
    tree = ast.parse((ROOT / "src/fluentpy/__init__.py").read_text(encoding="utf-8-sig"))
    public_version = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets
        )
    )
    if name != "fluentpy-qt" or public_version != version:
        parser.error(
            "Review the distribution name and keep the public and project versions identical"
        )
    output = ROOT / "dist" / "pypi" / version
    if output.exists() and any(output.iterdir()):
        parser.error(f"Preserving existing release files: {output}")
    run(ROOT / "scripts/check_quality.py")
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["FLUENTPY_BUILD_NATIVE"] = "0"
    env.pop("FLUENTPY_ZIG", None)
    run("-m", "build", "--no-isolation", "--sdist", "--outdir", output, ROOT, env=env)
    sources = list(output.glob("*.tar.gz"))
    if len(sources) != 1:
        raise RuntimeError("Expected exactly one source distribution")
    staging_parent = ROOT / "build"
    staging_parent.mkdir(exist_ok=True)
    # Both wheels start from the same sdist in separate temporary checkouts.
    # A native build can never leak a cached .pyd into the universal wheel.
    for mode in ("0", "1") if args.native else ("0",):
        with tempfile.TemporaryDirectory(prefix="pypi-source-", dir=staging_parent) as directory:
            with tarfile.open(sources[0]) as archive:
                archive.extractall(directory, filter="data")
            source = next(Path(directory).iterdir())
            wheel_env = env.copy()
            wheel_env["FLUENTPY_BUILD_NATIVE"] = mode
            if mode == "1" and args.zig:
                wheel_env["FLUENTPY_ZIG"] = str(args.zig.resolve(strict=True))
            run(
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                output,
                source,
                env=wheel_env,
            )
    artifacts = sorted([*output.glob("*.whl"), *sources])
    run("-m", "twine", "check", "--strict", *artifacts)
    manifest = {
        "name": name,
        "version": version,
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
    }
    (output / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Release prepared without uploading: {output}", flush=True)


if __name__ == "__main__":
    main()
