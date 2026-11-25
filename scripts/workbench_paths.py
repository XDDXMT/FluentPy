"""Per-user workbench state, using the desktop's standard data directory."""

from pathlib import Path


def workbench_data_directory() -> Path:
    from fluentpy.qt import QtCore

    location = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.GenericDataLocation
    )
    if not location:
        raise RuntimeError("The operating system did not provide a writable user data directory")
    return Path(location) / "FluentPy" / "Workbench"
