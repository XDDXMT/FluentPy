"""Capture the real Showcase at its normal desktop size, without showing it.

Run ``python sites/fluentpy-docs/capture_showcase.py`` for the light poster
and an eight-second GIF of the native navigation, sidebar and tab animations.
Use ``--copy-dir docs/assets`` to update the Markdown documentation as well.
Every frame comes from QWidget.grab(); this never moves the desktop pointer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
import traceback

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]

from PIL import Image, ImageStat
from showcase import BRAND_ICON, create_showcase_window
from fluentpy import QT_API, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


SIZE = (1120, 780)
DURATION_MS = 8000


def create_settled_showcase(app):
    """Wait for layout and the initial sidebar animation before taking a shot."""
    window = create_showcase_window("light", page="navigation")
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.resize(*SIZE)
    window.show()
    # Construction expands the real NavigationView sidebar over time. A grab
    # immediately after show() captures its narrow, intermediate layout.
    QTest.qWait(350)
    app.processEvents()
    if app.focusWidget() is not None:
        app.focusWidget().clearFocus()
    assert (window.width(), window.height()) == SIZE
    assert window.sidebar.width() == 216
    assert getattr(window.stack, "_animation", None) is None
    assert window.brand_mark.pixmap() is not None and not window.brand_mark.text()
    return window


def _grab(window):
    image = window.grab().toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    frame = Image.frombytes("RGBA", (image.width(), image.height()), bytes(image.constBits())).convert("RGB")
    assert frame.size == SIZE, "Run capture at QT_SCALE_FACTOR=1 for 1120 x 780 assets"
    return frame


def record_showcase(window, destination):
    """Record timed clicks on the real Qt controls, using Qt's event loop."""
    def click(widget):
        QTest.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton)

    def route(key):
        click(window._route_buttons[key])

    def document(key):
        click(next(item.widget for item in window.document_tabs._items if item.route_key == key))

    samples = []
    for key in ("cards", "feedback", "code"):
        window.set_page(key, animated=False)
        QTest.qWait(50)
        samples.append(_grab(window))
    window.set_page("cards", animated=False)
    QTest.qWait(220)

    # Reserve a neutral ramp so opacity/slide frames do not tint white text or
    # surfaces. The remaining colours cover all three actual Showcase pages.
    sheet = Image.new("RGB", (SIZE[0], SIZE[1] * len(samples)), "white")
    for index, frame in enumerate(samples):
        sheet.paste(frame, (0, index * SIZE[1]))
    adaptive = sheet.quantize(colors=192).getpalette()[:192 * 3]
    palette = Image.new("P", (1, 1))
    palette.putpalette([channel for gray in range(64) for channel in (round(gray * 255 / 63),) * 3] + adaptive)
    actions = [
        (500, lambda: click(window.sidebar._toggle)),
        (1000, lambda: click(window.sidebar._toggle)),
        (1500, lambda: route("inputs")),
        (2300, lambda: route("navigation")),
        (3000, lambda: click(window.feedback_pivot._items[1].widget)),
        (3700, lambda: click(window.feedback_pivot._items[2].widget)),
        (4400, lambda: (window.stack.currentWidget().ensureWidgetVisible(window.document_stack, 10, 10), document("notes"))),
        (5100, lambda: document("plan")),
        (5800, lambda: route("code")),
        (6600, lambda: route("cards")),
    ]
    frames, timestamps, fired, errors = [], [], set(), []
    unavailable_compositor_frames = []
    clock = QtCore.QElapsedTimer()
    timer = QtCore.QTimer()
    timer.setInterval(83)
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    loop = QtCore.QEventLoop()

    def tick():
        try:
            elapsed = clock.elapsed()
            if elapsed >= DURATION_MS:
                timer.stop()
                loop.quit()
                return
            for index, (at, action) in enumerate(actions):
                if elapsed >= at and index not in fired:
                    action()
                    fired.add(index)
            frame = _grab(window)
            # Some Qt graphics-effect transitions cannot be grabbed offscreen.
            # Keep the last real frame for their elapsed time instead of encoding
            # the unavailable black surface. Every encoded frame is a Qt grab.
            if min(ImageStat.Stat(frame.crop((220, 60, 1100, 740))).mean) < 200:
                unavailable_compositor_frames.append(elapsed)
                return
            frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
            timestamps.append(elapsed)
        except Exception:
            errors.append(traceback.format_exc())
            timer.stop()
            loop.quit()

    clock.start()
    tick()
    timer.timeout.connect(tick)
    timer.start()
    loop.exec()
    if errors:
        raise RuntimeError("\n".join(errors))
    assert len(fired) == len(actions) and len(frames) > 60
    boundaries = [round(value / 10) * 10 for value in timestamps] + [DURATION_MS]
    durations = [max(10, end - start) for start, end in zip(boundaries, boundaries[1:])]
    frames[0].save(destination, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=2, optimize=True)
    with Image.open(destination) as encoded:
        assert encoded.size == SIZE and encoded.info["loop"] == 0
        total = 0
        count = encoded.n_frames
        for index in range(count):
            encoded.seek(index)
            total += encoded.info["duration"]
        assert count > 20 and total == DURATION_MS
    intervals = [end - start for start, end in zip(timestamps, timestamps[1:])]
    return {"path": str(destination), "dimensions": list(SIZE), "bytes": destination.stat().st_size,
            "sampled_frames": len(frames), "encoded_frames": count, "duration_ms": total,
            "mean_interval_ms": statistics.mean(intervals), "native_control_actions": len(fired),
            "unavailable_compositor_frames_skipped": len(unavailable_compositor_frames),
            "real_Qt_widget_grabs_only": True, "desktop_pointer_moved": False}


class _HiddenWindowMonitor(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.visible_roots = []

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Show and isinstance(watched, QtWidgets.QWidget):
            if watched.isWindow() and not watched.testAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen):
                self.visible_roots.append(type(watched).__name__)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SITE / "dist" / "assets" / "previews")
    parser.add_argument("--copy-dir", type=Path)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["QT_SCALE_FACTOR"] = "1"
    if sys.platform == "win32":
        os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(ui_font(14))
    app.setWindowIcon(QtGui.QIcon(str(BRAND_ICON)))
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.Language.Chinese, QtCore.QLocale.Country.China))
    theme.set_mode("light")
    errors, warnings = [], []
    sys.excepthook = lambda kind, error, tb: errors.append("".join(traceback.format_exception(kind, error, tb)))
    QtCore.qInstallMessageHandler(lambda kind, context, message: warnings.append(message))
    monitor = _HiddenWindowMonitor()
    app.installEventFilter(monitor)
    window = create_settled_showcase(app)
    poster = args.output_dir / "showcase-light.png"
    assert window.grab().save(str(poster))
    with Image.open(poster) as image:
        assert image.size == SIZE
    animation = None
    files = [poster]
    if not args.static_only:
        gif = args.output_dir / "showcase-light.gif"
        animation = record_showcase(window, gif)
        files.append(gif)
    window.hide()
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    assert not errors and not warnings and not monitor.visible_roots, (errors, warnings, monitor.visible_roots)
    if args.copy_dir:
        args.copy_dir.mkdir(parents=True, exist_ok=True)
        for source in files:
            shutil.copy2(source, args.copy_dir / source.name)
    report = {"poster": str(poster), "dimensions": list(SIZE), "animation": animation,
              "theme": "light", "callback_errors": errors, "qt_messages": warnings,
              "desktop_visible_roots": monitor.visible_roots}
    (args.output_dir / "showcase-capture-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
