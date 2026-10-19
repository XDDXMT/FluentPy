"""GUI entry point for the Windows portable workbench."""

from __future__ import annotations

import importlib
import io
import os
import sys
import traceback
from pathlib import Path


def _restore_redirected_streams():
    """Windowed EXEs still need the pipes supplied by benchmark QProcess."""
    if sys.platform != "win32":
        return
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetFileType.argtypes = [wintypes.HANDLE]
    kernel.GetFileType.restype = wintypes.DWORD
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.DuplicateHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel.DuplicateHandle.restype = wintypes.BOOL
    process = kernel.GetCurrentProcess()
    for name, identifier in (("stdout", -11), ("stderr", -12)):
        if getattr(sys, name) is not None:
            continue
        handle = kernel.GetStdHandle(identifier & 0xFFFFFFFF)
        if not handle or kernel.GetFileType(handle) != 3:  # FILE_TYPE_PIPE
            continue
        duplicate = wintypes.HANDLE()
        if kernel.DuplicateHandle(process, handle, process, ctypes.byref(duplicate), 0, False, 2):
            descriptor = msvcrt.open_osfhandle(duplicate.value, os.O_WRONLY | os.O_BINARY)
            setattr(
                sys,
                name,
                io.TextIOWrapper(io.FileIO(descriptor, "w"), encoding="utf-8", write_through=True),
            )


def main():
    if not getattr(sys, "frozen", False):
        root = Path(__file__).resolve().parents[1]
        sys.path[:0] = [str(root / "src"), str(root / "examples"), str(root / "scripts")]
    else:
        _restore_redirected_streams()
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FluentPy" / "Workbench"
        os.environ.setdefault(
            "FLUENTPY_BENCHMARK_REPORT", str(local / "benchmarks" / "text-performance.json")
        )
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        from workbench_smoke import main as check

        return check(Path(sys.argv[2]).resolve())
    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        del sys.argv[1]
        from benchmark_text import main as benchmark

        return benchmark()
    if len(sys.argv) > 2 and sys.argv[1] == "--example":
        name = sys.argv[2]
        if name not in ("code_editor", "text_performance"):
            raise ValueError("Unknown standalone example")
        del sys.argv[1:3]
        return importlib.import_module(name).main()
    from showcase import main as showcase

    return showcase()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        details = traceback.format_exc()
        directory = (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FluentPy" / "Workbench"
        )
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / "startup-error.log"
        destination.write_text(details, encoding="utf-8")
        if "--self-test" in sys.argv:
            index = sys.argv.index("--self-test")
            Path(sys.argv[index + 1]).write_text(details, encoding="utf-8")
        if "--benchmark" not in sys.argv:
            from fluentpy.qt import QtWidgets

            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            QtWidgets.QMessageBox.critical(
                None, "FluentPy 工作台", "启动失败，错误记录已保存到：\n" + str(destination)
            )
        raise SystemExit(1)
