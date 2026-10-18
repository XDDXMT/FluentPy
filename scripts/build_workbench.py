"""Build an x64 Windows portable workbench with its C extension and Qt runtime."""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit("Build the Windows package on Windows.")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    sys.path.insert(0, str(ROOT / "src"))
    from fluentpy.backends import text, date, time, calendar, drop, shortcut, color
    from fluentpy.backends import input as segmented
    assert all(module.backend_name() == "native" for module in (text, date, time, calendar, drop, shortcut, color, segmented)), "Build the current C extension before packaging."
    staging = ROOT / "build" / "workbench-exe"
    staging.mkdir(parents=True, exist_ok=True)
    output = ROOT / "dist" / "workbench" / version
    output.mkdir(parents=True, exist_ok=True)
    app_folder = output / "FluentPy-Workbench"
    if app_folder.exists():
        raise SystemExit("Preserving the existing app folder. Move it aside before rebuilding.")
    from fluentpy.qt import QtCore, QtGui, QtWidgets
    import PySide6
    import shiboken6
    from PIL import Image
    app = QtWidgets.QApplication([])
    rendered = QtGui.QIcon(str(ROOT / "src/fluentpy/assets/brand/fluentpy.svg")).pixmap(256, 256)
    assert rendered.save(str(staging / "icon.png"))
    Image.open(staging / "icon.png").save(staging / "fluentpy.ico", sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
    notice_dir = staging / "licenses"
    notice_dir.mkdir(exist_ok=True)
    for name in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt", "GPL-2.0-only.txt"):
        target = notice_dir / name
        if not target.exists():
            with urlopen("https://raw.githubusercontent.com/qt/qtbase/v6.11.1/LICENSES/" + name, timeout=30) as response:
                target.write_bytes(response.read())
    hooks = staging / "hooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "hook-tables.py").write_text("# tables is the local workbench example, not the PyTables package.\n", encoding="utf-8")
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--noupx",
            "--name", "FluentPy-Workbench", "--distpath", str(output), "--workpath", str(staging / "pyinstaller"),
            "--specpath", str(staging), "--icon", str(staging / "fluentpy.ico"),
            "--paths", str(ROOT / "src"), "--paths", str(ROOT / "examples"), "--paths", str(ROOT / "scripts"),
            "--additional-hooks-dir", str(hooks),
            "--hidden-import", "fluentpy._native", "--hidden-import", "code_editor", "--hidden-import", "text_performance",
            "--hidden-import", "benchmark_text", "--hidden-import", "workbench_smoke", "--collect-data", "fluentpy",
            "--exclude-module", "PyQt6", "--exclude-module", "PyQt5", "--exclude-module", "PySide2",
            "--exclude-module", "tkinter", "--exclude-module", "matplotlib", "--exclude-module", "numpy"]
    data_files = [(ROOT / "LICENSE", "."), (ROOT / "THIRD_PARTY_NOTICES.md", "."), (ROOT / "licenses", "licenses"),
                  (notice_dir, "licenses/Qt"), (ROOT / "scripts/benchmark_text.py", "scripts"),
                  (ROOT / "benchmarks/baseline-original-source.json", "benchmarks"),
                  (ROOT / "src/fluentpy/widgets/code_edit.py", "src/fluentpy/widgets"),
                  (ROOT / "src/fluentpy/backends/text.py", "src/fluentpy/backends"), (ROOT / "native/text_accel.c", "native")]
    data_files.append((Path(sys.base_prefix) / "LICENSE.txt", "licenses/Python"))
    installer = metadata.distribution("pyinstaller")
    installer_license = next(path for path in installer.files if str(path).endswith("licenses/COPYING.txt"))
    data_files.append((Path(installer.locate_file(installer_license)), "licenses/PyInstaller"))
    for path, target in data_files:
        args.extend(["--add-data", str(path) + os.pathsep + target])
    args.append(str(ROOT / "scripts/workbench_launcher.py"))
    environment = os.environ.copy()
    # Do not resolve Qt dependencies from PDF/image tools on the host PATH.
    windows = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(map(str, (Path(sys.executable).parent,
        Path(sys.executable).parent / "Scripts", Path(PySide6.__file__).parent,
        Path(shiboken6.__file__).parent, windows / "System32", windows)))
    for name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "PYTHONPATH"):
        environment.pop(name, None)
    subprocess.run(args, cwd=ROOT, env=environment, check=True)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, app_folder / name)
    (app_folder / "使用说明.txt").write_text(
        f"FluentPy 工作台 {version} · Windows x64 便携版\n\n解压整个文件夹，双击 FluentPy-Workbench.exe。无需安装 Python，不需要管理员权限。\n"
        "请保留 _internal 文件夹，不要只复制 EXE。\n\n设置会保存在当前 Windows 用户下；性能报告位于 %LOCALAPPDATA%\\FluentPy\\Workbench\\benchmarks。\n"
        "FluentPy 使用 MIT 许可，随包附带的 Python、Qt/PySide6 与图标各自适用其许可证。Qt 动态库位于 _internal，可用兼容版本替换；Qt/PySide6 源码与许可见 https://code.qt.io/ 和 https://www.qt.io/qt-for-python 。\n"
        "文档：https://fluentpy.mcxmcl.cn/\n源码：https://github.com/XDDXMT/FluentPy\n", encoding="utf-8-sig")
    archive = output / f"FluentPy-Workbench-{version}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(app_folder.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (output / "SHA256SUMS.txt").write_text(digest + "  " + archive.name + "\n", encoding="ascii")
    manifest = {"version": version, "platform": "windows-x64", "python": sys.version.split()[0],
                "pyside6": metadata.version("PySide6"), "pyinstaller": metadata.version("pyinstaller"),
                "file": archive.name, "size": archive.stat().st_size, "sha256": digest}
    (output / "workbench-release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
