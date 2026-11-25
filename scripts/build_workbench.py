"""Build a native-host portable workbench; no cross compilation is attempted."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import zipfile
from importlib import metadata
from pathlib import Path
from urllib.request import urlopen

import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output directory (never overwritten)")
    parser.add_argument("--require-native", action="store_true", help="Require all nine C backends")
    options = parser.parse_args()
    target = {"win32": "windows", "darwin": "macos", "linux": "linux"}.get(sys.platform)
    if target is None:
        parser.error("Supported build hosts: Windows, Linux and macOS")
    architecture = platform.machine().lower()
    architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(
        architecture, architecture
    )
    platform_tag = f"{target}-{architecture}"
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    sys.path.insert(0, str(ROOT / "src"))
    from fluentpy.backends import calendar, color, date, drop, shortcut, syntax, text, time
    from fluentpy.backends import input as segmented

    backends = {
        module.__name__.rsplit(".", 1)[-1]: module.backend_name()
        for module in (text, date, time, calendar, drop, shortcut, color, segmented, syntax)
    }
    if options.require_native and set(backends.values()) != {"native"}:
        parser.error("Build the current C extension before requiring native backends")
    staging = ROOT / "build" / "workbench-exe"
    staging.mkdir(parents=True, exist_ok=True)
    output = (options.output or ROOT / "dist" / "workbench" / version).resolve()
    if output.exists() and any(output.iterdir()):
        parser.error(f"Preserving existing release files: {output}")
    output.mkdir(parents=True, exist_ok=True)
    app_folder = output / ("FluentPy-Workbench.app" if target == "macos" else "FluentPy-Workbench")
    if app_folder.exists():
        raise SystemExit("Preserving the existing app folder. Move it aside before rebuilding.")
    import PySide6
    import shiboken6
    from PIL import Image

    from fluentpy.qt import QtCore, QtGui, QtWidgets

    # QPixmap needs a live application while the icon is rendered.
    _app = QtWidgets.QApplication([])
    rendered = QtGui.QIcon(str(ROOT / "src/fluentpy/assets/brand/fluentpy.svg")).pixmap(256, 256)
    assert rendered.save(str(staging / "icon.png"))
    icon_path = staging / "icon.png"
    if target == "windows":
        icon_path = staging / "fluentpy.ico"
        Image.open(staging / "icon.png").save(
            icon_path, sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)]
        )
    elif target == "macos":
        icon_path = staging / "fluentpy.icns"
        Image.open(staging / "icon.png").resize((1024, 1024)).save(icon_path)
    notice_dir = staging / "licenses"
    notice_dir.mkdir(exist_ok=True)
    for name in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt", "GPL-2.0-only.txt"):
        license_path = notice_dir / name
        if not license_path.exists():
            with urlopen(
                f"https://raw.githubusercontent.com/qt/qtbase/v{QtCore.qVersion()}/LICENSES/"
                + name,
                timeout=30,
            ) as response:
                license_path.write_bytes(response.read())
    hooks = staging / "hooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "hook-tables.py").write_text(
        "# tables is the local workbench example, not the PyTables package.\n", encoding="utf-8"
    )
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--noupx",
        "--name",
        "FluentPy-Workbench",
        "--distpath",
        str(output),
        "--workpath",
        str(staging / "pyinstaller"),
        "--specpath",
        str(staging),
        "--icon",
        str(icon_path),
        "--paths",
        str(ROOT / "src"),
        "--paths",
        str(ROOT / "examples"),
        "--paths",
        str(ROOT / "scripts"),
        "--additional-hooks-dir",
        str(hooks),
        "--hidden-import",
        "fluentpy._native",
        "--hidden-import",
        "code_editor",
        "--hidden-import",
        "text_performance",
        "--hidden-import",
        "benchmark_text",
        "--hidden-import",
        "workbench_smoke",
        "--exclude-module",
        "PyQt6",
        "--exclude-module",
        "PyQt5",
        "--exclude-module",
        "PySide2",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "numpy",
    ]
    data_files = [
        (ROOT / "examples/assets", "assets"),
        (ROOT / "src/fluentpy/assets", "fluentpy/assets"),
        (ROOT / "LICENSE", "."),
        (ROOT / "THIRD_PARTY_NOTICES.md", "."),
        (ROOT / "licenses", "licenses"),
        (notice_dir, "licenses/Qt"),
        (ROOT / "scripts/benchmark_text.py", "scripts"),
        (ROOT / "benchmarks/baseline-original-source.json", "benchmarks"),
        (ROOT / "src/fluentpy/widgets/code_edit.py", "src/fluentpy/widgets"),
        (ROOT / "src/fluentpy/backends/text.py", "src/fluentpy/backends"),
        (ROOT / "native/text_accel.c", "native"),
    ]
    python_license = next(
        (
            path
            for path in (
                Path(sys.base_prefix) / "LICENSE.txt",
                Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
            )
            if path.is_file()
        ),
        None,
    )
    if python_license is None:
        python_license = notice_dir / "Python-LICENSE.txt"
        release = ".".join(map(str, sys.version_info[:3]))
        with urlopen(
            f"https://raw.githubusercontent.com/python/cpython/v{release}/LICENSE", timeout=30
        ) as response:
            python_license.write_bytes(response.read())
    data_files.append((python_license, "licenses/Python"))
    installer = metadata.distribution("pyinstaller")
    installer_license = next(
        path for path in installer.files if str(path).endswith("licenses/COPYING.txt")
    )
    data_files.append((Path(installer.locate_file(installer_license)), "licenses/PyInstaller"))
    for path, destination in data_files:
        args.extend(["--add-data", str(path) + os.pathsep + destination])
    args.append(str(ROOT / "scripts/workbench_launcher.py"))
    environment = os.environ.copy()
    if target == "windows":
        # Avoid Qt DLLs from unrelated applications on the Windows PATH.
        windows = Path(environment.get("SystemRoot", r"C:\Windows"))
        environment["PATH"] = os.pathsep.join(
            map(
                str,
                (
                    Path(sys.executable).parent,
                    Path(sys.executable).parent / "Scripts",
                    Path(PySide6.__file__).parent,
                    Path(shiboken6.__file__).parent,
                    windows / "System32",
                    windows,
                ),
            )
        )
    for name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "PYTHONPATH"):
        environment.pop(name, None)
    subprocess.run(args, cwd=ROOT, env=environment, check=True)
    resources = app_folder / "Contents/Resources" if target == "macos" else app_folder
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, resources / name)
    launch = {
        "windows": "FluentPy-Workbench.exe",
        "macos": "FluentPy-Workbench.app",
        "linux": "./FluentPy-Workbench",
    }[target]
    (resources / "使用说明.txt").write_text(
        f"FluentPy 工作台 {version} · {platform_tag}\n\n完整解压后运行 {launch}。无需安装 Python。\n"
        "请保留完整目录或 app 包，不能只复制可执行文件。设置、日志和报告保存在系统当前用户数据目录。\n"
        "Linux 仍需桌面图形、字体及音频系统库；macOS 发布分发需自行完成签名和公证。\n"
        "FluentPy 使用 MIT 许可，随包附带的 Python、Qt/PySide6 与图标各自适用其许可证。Qt 动态库位于 _internal，可用兼容版本替换；Qt/PySide6 源码与许可见 https://code.qt.io/ 和 https://www.qt.io/qt-for-python 。\n"
        "文档：https://fluentpy.mcxmcl.cn/\n源码：https://github.com/XDDXMT/FluentPy\n",
        encoding="utf-8-sig",
    )
    # tar preserves Unix executable modes and macOS framework symlinks.
    archive = (
        output
        / f"FluentPy-Workbench-{version}-{platform_tag}.{'zip' if target == 'windows' else 'tar.gz'}"
    )
    if target == "windows":
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for path in sorted(app_folder.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(output).as_posix())
    else:
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(app_folder, arcname=app_folder.name)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (output / "SHA256SUMS.txt").write_text(digest + "  " + archive.name + "\n", encoding="ascii")
    manifest = {
        "version": version,
        "platform": platform_tag,
        "backends": backends,
        "python": sys.version.split()[0],
        "pyside6": metadata.version("PySide6"),
        "pyinstaller": metadata.version("pyinstaller"),
        "file": archive.name,
        "size": archive.stat().st_size,
        "sha256": digest,
    }
    (output / "workbench-release.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest), flush=True)


if __name__ == "__main__":
    main()
