"""Capture real Toast animations for the local documentation.

Run ``python sites/fluentpy-docs/capture_animations.py`` from the repository.
Requires the project's Qt binding and Pillow. On Windows this deliberately uses
the Windows Qt platform (for system fonts), with every root marked
WA_DontShowOnScreen before show(). Only our own QWidget.grab() is captured.
The JSON printed at the end records real sampling times and encoded GIF timing.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import statistics
import sys
import traceback


SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path.insert(0, str(ROOT / "src"))

# Font discovery is incomplete with Qt's Windows offscreen plugin. Hidden native
# roots give the real glyphs without displaying a window on the desktop.
if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PIL import Image, ImageChops

from fluentpy import Button, QT_API, Toast, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


SAMPLE_MS = 25
LOOP_MS = 4000
PRESS_MS = 500
RELEASE_MS = 625
CLOSE_PRESS_MS = 2700
CLOSE_RELEASE_MS = 2800
MAX_GIF_BYTES = 700 * 1024


def _capture_font() -> QtGui.QFont:
    font = ui_font(14)
    # Grayscale antialiasing is appropriate for exported bitmap assets. Native
    # ClearType RGB fringes otherwise change colour in an indexed GIF palette.
    font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias |
                          QtGui.QFont.StyleStrategy.NoSubpixelAntialias)
    return font


def _image(widget: QtWidgets.QWidget) -> Image.Image:
    """Read this widget's Qt backing surface, with no desktop capture."""
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    if not widget.grab().save(buffer, "PNG"):
        raise RuntimeError("QWidget.grab() could not encode the animation frame")
    with Image.open(io.BytesIO(bytes(buffer.data()))) as image:
        return image.convert("RGB")


def _font_families(widget: QtWidgets.QWidget, text: str) -> list[str]:
    layout = QtGui.QTextLayout(text, widget.font())
    layout.beginLayout()
    layout.createLine()
    layout.endLayout()
    runs = layout.glyphRuns()
    if not runs or any(0 in run.glyphIndexes() for run in runs):
        raise RuntimeError(f"Missing actual Qt glyphs for {text!r}")
    return sorted({run.rawFont().familyName() for run in runs})


class Canvas(QtWidgets.QWidget):
    def __init__(self, kind: str):
        super().__init__()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.setObjectName("animationCanvas")
        self.setFont(_capture_font())
        self.setStyleSheet("QWidget#animationCanvas { background: #fafbfc; }")
        self.kind = kind
        self.message: Toast | None = None
        self.show_events = 0
        self.orphan_label_shows: list[str] = []
        self.fonts: dict[str, list[str]] = {}
        self.button = Button("复制代码" if kind == "compact" else "保存灵感", self)
        self.button.setFont(_capture_font())
        if kind == "compact":
            self.setFixedSize(460, 180)
            self.button.setGeometry(32, 110, 116, 36)
        else:
            self.setFixedSize(760, 250)
            self.button.setGeometry(287, 174, 186, 40)
        self.button.clicked.connect(self._show_message)

    def _show_message(self):
        if self.kind == "compact":
            QtWidgets.QApplication.clipboard().setText("print('Hello, FluentPy!')")
            self.message = Toast.success("代码已复制", parent=self, timeout_ms=0)
        else:
            self.message = Toast.success(
                "已保存", detail="灵感已经收好，可以开始下一段创作。",
                target=self.button, timeout_ms=0,
            )
        assert not self.message.isWindow()
        assert self.message.testAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.message.destroyed.connect(self._message_destroyed)
        self.fonts["message_title"] = _font_families(self.message._title, self.message._title.text())
        if self.message._detail.text():
            self.fonts["message_detail"] = _font_families(self.message._detail, self.message._detail.text())

    def _message_destroyed(self):
        self.message = None

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Show:
            if isinstance(watched, Toast) and watched.parentWidget() is self:
                self.show_events += 1
            elif isinstance(watched, QtWidgets.QLabel) and watched.isWindow():
                self.orphan_label_shows.append(watched.text())
        return super().eventFilter(watched, event)


def _write_gif(frames: list[Image.Image], elapsed: list[int], path: Path) -> dict:
    # One palette for the entire sequence avoids colour flicker during fades.
    # Build it from all real frames, rather than just the opaque poster.
    # Keep text at full resolution when discovering colours. Downsampling a
    # thin glyph first can remove its black pixels from the adaptive palette.
    unique = {frame.tobytes(): frame for frame in frames}
    columns = 4
    width, height = frames[0].size
    rows = (len(unique) + columns - 1) // columns
    palette_source = Image.new("RGB", (columns * width, rows * height), "#fafbfc")
    for index, frame in enumerate(unique.values()):
        palette_source.paste(frame, ((index % columns) * width, (index // columns) * height))
    adaptive = palette_source.quantize(colors=128).getpalette()[:128 * 3]
    # Reserve a neutral ramp so fading dark UI text never maps to icon green.
    neutral = [channel for value in range(128) for channel in (round(value * 255 / 127),) * 3]
    palette = Image.new("P", (1, 1))
    palette.putpalette(neutral + adaptive)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    # GIF stores durations in 10ms ticks. Round boundaries, not each 25ms
    # interval independently, so alternating 20/30ms samples keep their timing.
    boundaries = [round(time / 10) * 10 for time in elapsed] + [LOOP_MS]
    durations = [max(10, end - start) for start, end in zip(boundaries, boundaries[1:])]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, disposal=2, optimize=True)
    size = path.stat().st_size
    if size >= MAX_GIF_BYTES:
        raise RuntimeError(f"Animation exceeds 700 KiB: {path.name}: {size}")
    with Image.open(path) as gif:
        if gif.size != frames[0].size or gif.info.get("loop") != 0:
            raise RuntimeError(f"Invalid GIF dimensions/loop: {path}")
        first = gif.convert("RGB")
        encoded_durations = []
        for index in range(gif.n_frames):
            gif.seek(index)
            encoded_durations.append(gif.info.get("duration", 0))
        encoded_frames = gif.n_frames
        if ImageChops.difference(first, gif.convert("RGB")).getbbox() is not None:
            raise RuntimeError(f"Encoded GIF does not end on its clean initial canvas: {path}")
    return {
        "gif": str(path), "bytes": size, "dimensions": list(frames[0].size),
        "sampled_frames": len(frames), "encoded_frames": encoded_frames,
        "encoded_loop_returns_to_initial_canvas": True,
        "encoded_duration_ms": sum(encoded_durations),
        "encoded_frame_durations_ms": encoded_durations,
    }


def capture(app: QtWidgets.QApplication, kind: str, output: Path) -> dict:
    canvas = Canvas(kind)
    assert canvas.testAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    app.installEventFilter(canvas)
    canvas.show()
    QTest.qWait(100)
    canvas.fonts["trigger"] = _font_families(canvas.button, canvas.button.text())
    _image(canvas)  # Warm up PNG/Pillow before starting the measured timeline.
    frames: list[Image.Image] = []
    times: list[int] = []
    observations: list[dict] = []
    actions: set[str] = set()
    failures: list[str] = []
    loop = QtCore.QEventLoop()
    clock = QtCore.QElapsedTimer()
    timer = QtCore.QTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.setInterval(SAMPLE_MS)
    poster: Image.Image | None = None

    def tick():
        nonlocal poster
        try:
            elapsed = clock.elapsed()
            if elapsed >= LOOP_MS:
                timer.stop()
                loop.quit()
                return
            if elapsed >= PRESS_MS and "press" not in actions:
                QTest.mousePress(canvas.button, QtCore.Qt.MouseButton.LeftButton)
                actions.add("press")
            if elapsed >= RELEASE_MS and "release" not in actions:
                QTest.mouseRelease(canvas.button, QtCore.Qt.MouseButton.LeftButton)
                actions.add("release")
            if elapsed >= CLOSE_PRESS_MS and "close_press" not in actions:
                assert canvas.message is not None
                QTest.mousePress(canvas.message.close_button, QtCore.Qt.MouseButton.LeftButton)
                actions.add("close_press")
            if elapsed >= CLOSE_RELEASE_MS and "close_release" not in actions:
                assert canvas.message is not None
                QTest.mouseRelease(canvas.message.close_button, QtCore.Qt.MouseButton.LeftButton)
                actions.add("close_release")
            message = canvas.message
            observations.append({
                "elapsed_ms": elapsed,
                "opacity": message._opacity.opacity() if message is not None else None,
                "position": [message.x(), message.y()] if message is not None else None,
                "closing": bool(message is not None and message._closing),
                "arrow_edge": message._arrow_edge if message is not None else None,
            })
            frame = _image(canvas)
            if frame.size != (canvas.width(), canvas.height()):
                raise RuntimeError("Expected 1x widget capture; check Qt scaling settings")
            frames.append(frame)
            times.append(elapsed)
            if poster is None and message is not None and message._opacity.opacity() == 1.0:
                poster = frame.copy()
        except Exception:
            failures.append(traceback.format_exc())
            timer.stop()
            loop.quit()

    try:
        clock.start()
        tick()
        timer.timeout.connect(tick)
        timer.start()
        loop.exec()
        if failures:
            raise RuntimeError("\n".join(failures))
        assert actions == {"press", "release", "close_press", "close_release"}
        assert canvas.message is None, "Close must finish and DeleteOnClose must recycle the Toast"
        assert poster is not None and canvas.show_events == 1
        assert not canvas.orphan_label_shows
        entering = [s for s in observations if s["opacity"] is not None and 0 < s["opacity"] < 1 and not s["closing"]]
        exiting = [s for s in observations if s["opacity"] is not None and 0 < s["opacity"] < 1 and s["closing"]]
        assert len(entering) >= 4 and len(exiting) >= 3, "Both real animation phases must be captured"
        assert observations[-1]["opacity"] is None
        assert ImageChops.difference(frames[0], frames[-1]).getbbox() is None, "Loop must return to its clean initial canvas"
        assert len({tuple(s["position"]) for s in entering}) > 1, "Entry must include the actual position animation"
        if kind == "anchored":
            assert all(s["arrow_edge"] == "bottom" for s in observations if s["opacity"] is not None)
        name = f"toast-{kind}-light"
        poster_path = output / f"{name}.png"
        poster.save(poster_path, optimize=True)
        report = _write_gif(frames, times, output / f"{name}.gif")
        intervals = [end - begin for begin, end in zip(times, times[1:])]
        report.update({
            "poster": str(poster_path), "poster_bytes": poster_path.stat().st_size,
            "requested_sample_interval_ms": SAMPLE_MS,
            "actual_sample_intervals_ms": intervals,
            "actual_interval_min_ms": min(intervals), "actual_interval_max_ms": max(intervals),
            "actual_interval_mean_ms": round(statistics.mean(intervals), 3),
            "show_duration_ms": Toast.SHOW_DURATION, "hide_duration_ms": Toast.HIDE_DURATION,
            "entry_intermediate_frames": len(entering), "exit_intermediate_frames": len(exiting),
            "message_show_events": canvas.show_events, "fonts": canvas.fonts,
            "orphan_label_shows": canvas.orphan_label_shows,
            "root_hidden_from_desktop": canvas.testAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen),
            "deleted_after_close": canvas.message is None,
        })
        return report
    finally:
        timer.stop()
        app.removeEventFilter(canvas)
        canvas.hide()
        canvas.close()
        canvas.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SITE / "dist" / "assets" / "previews")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    theme.set_mode("light")
    theme.set_active(True)
    errors = []
    previous_hook = sys.excepthook
    sys.excepthook = lambda kind, error, tb: errors.append("".join(traceback.format_exception(kind, error, tb)))
    clipboard = app.clipboard()
    mime = clipboard.mimeData()
    saved_clipboard = {format: bytes(mime.data(format)) for format in mime.formats()} if mime is not None else {}
    try:
        reports = [capture(app, kind, args.output_dir) for kind in ("compact", "anchored")]
        if errors:
            raise RuntimeError("Qt callback errors:\n" + "\n".join(errors))
    finally:
        restored = QtCore.QMimeData()
        for format, data in saved_clipboard.items():
            restored.setData(format, QtCore.QByteArray(data))
        clipboard.setMimeData(restored)
        sys.excepthook = previous_hook
    restored_mime = clipboard.mimeData()
    assert all(bytes(restored_mime.data(format)) == data for format, data in saved_clipboard.items())
    print(json.dumps({"qt_api": QT_API, "platform": app.platformName(),
                      "qt_callback_errors": errors, "captures": reports,
                      "clipboard_restored": True}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
