"""Build FluentPy's optional C module with the active CPython interpreter.

Use --zig for the portable workspace-local toolchain. Without it, setuptools
uses the platform's normal C compiler (MSVC on Windows, cc on Unix).
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_with_zig(zig: Path, output: Path) -> Path:
    if sys.implementation.name != "cpython":
        raise RuntimeError("The optional native module requires CPython.")
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError(
            "The Zig helper currently supports Windows x64; use the system compiler elsewhere."
        )
    zig = zig.expanduser().resolve()
    if not zig.is_file():
        raise FileNotFoundError(f"Zig executable not found: {zig}")
    sources = [
        ROOT / "native" / name
        for name in (
            "text_accel.c",
            "date_accel.c",
            "drop_accel.c",
            "shortcut_accel.c",
            "time_accel.c",
            "calendar_accel.c",
            "color_accel.c",
            "input_accel.c",
        )
    ]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"Native source not found: {source}")
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        raise RuntimeError("Free-threaded Python builds are not yet supported by this helper.")
    version = f"{sys.version_info.major}{sys.version_info.minor}"
    import_lib = Path(sys.base_prefix) / "libs" / f"python{version}.lib"
    if not import_lib.is_file():
        raise FileNotFoundError(f"CPython development import library not found: {import_lib}")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    build_dir = ROOT / "build" / "native"
    build_dir.mkdir(parents=True, exist_ok=True)
    staging = build_dir / "output"
    staging.mkdir(exist_ok=True)
    compiled = staging / output.name
    env = os.environ.copy()
    for key, folder in (
        ("ZIG_GLOBAL_CACHE_DIR", "zig-global-cache"),
        ("ZIG_LOCAL_CACHE_DIR", "zig-local-cache"),
        ("TEMP", "tmp"),
        ("TMP", "tmp"),
    ):
        path = build_dir / folder
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    command = [
        str(zig),
        "cc",
        "-target",
        "x86_64-windows-gnu",
        "-shared",
        "-O3",
        "-DNDEBUG",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-I",
        sysconfig.get_path("include"),
        *map(str, sources),
        str(import_lib),
        "-o",
        str(compiled),
    ]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    if not compiled.is_file():
        raise RuntimeError("Compiler exited successfully but did not produce the extension.")
    _publish_extension(compiled, output, build_dir)
    return output


def _publish_extension(compiled: Path, output: Path, build_dir: Path) -> None:
    """Preserve a binary held by a running Windows app, and restore on failure."""
    try:
        shutil.copy2(compiled, output)
    except PermissionError:
        # Windows allows an in-use extension to be renamed while its existing
        # process retains the old mapping. Preserve it rather than killing apps.
        if not output.is_relative_to(ROOT):
            raise
        retained = build_dir / "in-use"
        retained.mkdir(exist_ok=True)
        backup = retained / (uuid.uuid4().hex + "-" + output.name)
        output.rename(backup)
        try:
            shutil.copy2(compiled, output)
        except BaseException:
            if output.exists():
                output.unlink()
            backup.rename(output)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", type=Path, default=os.environ.get("FLUENTPY_ZIG"))
    args = parser.parse_args()
    if args.zig:
        suffix = sysconfig.get_config_var("EXT_SUFFIX")
        output = build_with_zig(args.zig, ROOT / "src" / "fluentpy" / f"_native{suffix}")
        print(f"Built: {output}")
    else:
        env = os.environ.copy()
        env["FLUENTPY_BUILD_NATIVE"] = "1"
        subprocess.run(
            [sys.executable, "setup.py", "build_ext", "--inplace"],
            cwd=ROOT,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
