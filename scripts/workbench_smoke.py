"""Exercise the frozen app without a source checkout or installed Python."""
from __future__ import annotations

import importlib
from importlib import resources
import json
from pathlib import Path
import sys
import time


def main(destination: Path) -> int:
    from fluentpy import __version__, FluentIcon, fluent_icon, theme
    from fluentpy.qt import QtCore, QtWidgets
    from showcase import PAGES, Showcase
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    modules = {name: importlib.import_module("fluentpy.backends." + name)
               for name in ("text", "date", "time", "calendar", "drop", "shortcut", "color", "input")}
    backends = {name: module.backend_name() for name, module in modules.items()}
    assert set(backends.values()) == {"native"}, backends
    assert modules["text"].json_spans('{"ok":true}')
    assert modules["date"].days_in_month(2024, 2) == 29
    assert modules["time"].step_time(23, 59, 1, 1) == (23, 0)
    assert modules["calendar"].shift_date((2024, 2, 28), days=2) == (2024, 3, 1)
    assert modules["drop"].normalize_extensions([".txt"]) == (".txt",)
    assert modules["shortcut"].normalize(ord("s"), 0x04000000) == (ord("S"), 0x04000000)
    assert modules["color"].parse_hex("#123456") == (18, 52, 86, 255)
    assert modules["input"].split_code("1234", 4) == ("1", "2", "3", "4")
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    errors, frames, checked = [], [], []
    def exception(kind, value, tb):
        errors.append(str(value))
        app.exit(1)
    sys.excepthook = exception
    window = Showcase(restore_preferences=False)
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.startup_splash.firstFramePainted.connect(lambda: frames.append({"initialized": window._initialized, "ms": round((time.perf_counter() - started) * 1000, 2)}))
    window.startupFailed.connect(lambda message: (errors.append(message), app.exit(1)))
    def verify():
        try:
            assert frames and frames[0]["initialized"] is False, frames
            assert window._initialized and len(window._page_indexes) == len(PAGES)
            window.set_theme_transition_enabled(False)
            for mode in ("light", "dark"):
                theme.set_mode(mode)
                for route, _title, _icon in PAGES:
                    window.set_page(route, animated=False)
                    app.processEvents()
                    assert not window.grab().isNull(), route
                    checked.append(mode + ":" + route)
                    if route in ("overview", "tables", "settings"):
                        assert window.grab().save(str(destination.parent / ("frozen-" + route + "-" + mode + ".png")))
            for icon in FluentIcon:
                assert not fluent_icon(icon).pixmap(24, 24).isNull(), icon
            assert resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg").is_file()
            from workbench_settings import _local_declarations
            assert "暂不可用" not in _local_declarations()
            assert not errors, errors
            destination.write_text(json.dumps({"version": __version__, "frozen": bool(getattr(sys, "frozen", False)), "executable": sys.executable, "backends": backends,
                "startup_frames": frames, "checked_routes": checked, "icons": len(list(FluentIcon)), "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
            window.close()
            app.exit(0)
        except Exception as error:
            errors.append(str(error))
            destination.write_text(json.dumps({"errors": errors, "checked_routes": checked}, ensure_ascii=False, indent=2), encoding="utf-8")
            window.close()
            app.exit(1)
    window.ready.connect(verify)
    QtCore.QTimer.singleShot(60000, lambda: (errors.append("Frozen startup timed out"), app.exit(2)))
    window.show()
    result = app.exec()
    if result and not destination.exists():
        destination.write_text(json.dumps({"errors": errors}, ensure_ascii=False), encoding="utf-8")
    return result
