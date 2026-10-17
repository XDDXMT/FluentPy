"""Optional CPython accelerator; package metadata remains in pyproject.toml."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.errors import ExecError


ROOT = Path(__file__).resolve().parent
MODE = os.environ.get("FLUENTPY_BUILD_NATIVE", "auto").lower()
if MODE not in {"auto", "0", "1"}:
    raise RuntimeError("FLUENTPY_BUILD_NATIVE must be auto, 0 (Python only), or 1 (required).")


class OptionalNativeBuild(build_ext):
    def build_extension(self, ext: Extension) -> None:
        zig = os.environ.get("FLUENTPY_ZIG")
        if not zig:
            super().build_extension(ext)
            return
        spec = importlib.util.spec_from_file_location(
            "fluentpy_native_build", ROOT / "scripts" / "build_native.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            module.build_with_zig(Path(zig), Path(self.get_ext_fullpath(ext.name)))
        except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
            raise ExecError(str(exc)) from exc


setup(
    ext_modules=[] if MODE == "0" else [
        Extension(
            "fluentpy._native",
            sources=["native/text_accel.c", "native/date_accel.c", "native/drop_accel.c", "native/shortcut_accel.c", "native/time_accel.c", "native/calendar_accel.c"],
            depends=["native/date_accel.h", "native/drop_accel.h", "native/shortcut_accel.h", "native/time_accel.h", "native/calendar_accel.h"],
            optional=MODE != "1",
        )
    ],
    cmdclass={"build_ext": OptionalNativeBuild},
)
