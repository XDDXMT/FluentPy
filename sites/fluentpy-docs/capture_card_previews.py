"""Render the real card variants and hover GIF at the demo's logical size.

Run: python sites/fluentpy-docs/capture_card_previews.py
All roots are hidden before show(); only our own QWidget.grab() is recorded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples"), str(SITE)]

from capture_animations import _capture_font, _font_families, _image
from PIL import Image, ImageChops
from cards import CardsDemo, TILES_PREVIEW_SIZE
from fluentpy import QT_API, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class CursorMarker(QtWidgets.QWidget):
    """A painted cursor inside the preview, never the desktop mouse pointer."""
    def __init__(self, parent, tile):
        super().__init__(parent)
        width = max(12, round(tile.width() * 0.13))
        self.setFixedSize(width, round(width * 29 / 23))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 23, self.height() / 29)
        path = QtGui.QPainterPath(QtCore.QPointF(2, 2))
        for point in ((2, 23), (8, 18), (12, 27), (16, 25), (12, 16), (20, 16), (2, 2)):
            path.lineTo(*point)
        painter.setPen(QtGui.QPen(QtGui.QColor("#262626"), 1.2,
                                    QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap,
                                    QtCore.Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(QtGui.QColor("#ffffff"))
        painter.drawPath(path)


def hover(tile, entering: bool):
    if entering:
        local = QtCore.QPointF(tile.rect().center())
        screen = QtCore.QPointF(tile.mapToGlobal(tile.rect().center()))
        event = QtGui.QEnterEvent(local, local, screen)
    else:
        event = QtCore.QEvent(QtCore.QEvent.Type.Leave)
    QtCore.QCoreApplication.sendEvent(tile, event)


def corners_of(size):
    width, height = size
    return ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))


def write_hover_gif(frames, elapsed, target):
    # Emoji gradients need the complete 256-colour palette. Unlike a fade,
    # hover changes only neutral card surfaces, so the opaque first Qt frame
    # provides a stable full-resolution palette for every colourful glyph.
    palette = frames[0].quantize(colors=256)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    boundaries = [round(time / 10) * 10 for time in elapsed] + [4000]
    durations = [max(10, end - start) for start, end in zip(boundaries, boundaries[1:])]
    indexed[0].save(target, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, disposal=2, optimize=True)
    assert target.stat().st_size < 700 * 1024
    with Image.open(target) as gif:
        first = gif.convert("RGB")
        encoded_duration = 0
        count = gif.n_frames
        for index in range(count):
            gif.seek(index)
            encoded_duration += gif.info["duration"]
            # Reject transparent/black corners after indexed GIF encoding.
            for x, y in corners_of(gif.size):
                assert min(gif.convert("RGB").getpixel((x, y))) > 235
        assert ImageChops.difference(first, gif.convert("RGB")).getbbox() is None
        assert gif.size == tuple(TILES_PREVIEW_SIZE) and gif.info["loop"] == 0
    return {"gif": str(target), "bytes": target.stat().st_size, "dimensions": list(TILES_PREVIEW_SIZE),
            "sampled_frames": len(frames), "encoded_frames": count, "encoded_duration_ms": encoded_duration,
            "encoded_loop_returns_to_initial_canvas": True, "all_corners_pale": True}


def record_tiles(app, content, output: Path) -> dict:
    surface = content.tiles_preview
    assert (surface.width(), surface.height()) == tuple(TILES_PREVIEW_SIZE)
    marker = CursorMarker(surface, content.tiles[0])
    frames, elapsed, samples = [], [], []
    actions = set()
    failures = []
    clock = QtCore.QElapsedTimer()
    timer = QtCore.QTimer()
    timer.setInterval(25)
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    loop = QtCore.QEventLoop()
    _image(surface)

    def tick():
        try:
            now = clock.elapsed()
            if now >= 4000:
                timer.stop()
                loop.quit()
                return
            for index, tile in enumerate(content.tiles):
                for at, entering in ((500 + index * 1000, True), (1100 + index * 1000, False)):
                    key = (index, entering)
                    if now >= at and key not in actions:
                        if entering:
                            cursor_x = min(round(tile.width() * 0.82), tile.width() - marker.width() - 2)
                            cursor_y = min(round(tile.height() * 0.36), tile.height() - marker.height() - 2)
                            marker.move(tile.pos() + QtCore.QPoint(max(0, cursor_x), max(0, cursor_y)))
                            marker.show()
                            marker.raise_()
                        else:
                            marker.hide()
                        hover(tile, entering)
                        actions.add(key)
            frames.append(_image(surface))
            elapsed.append(now)
            samples.append([tile._hover_progress for tile in content.tiles])
        except Exception:
            failures.append(traceback.format_exc())
            timer.stop()
            loop.quit()

    clock.start()
    tick()
    timer.timeout.connect(tick)
    timer.start()
    loop.exec()
    if failures:
        raise RuntimeError("\n".join(failures))
    assert len(actions) == 6
    assert all(any(0 < sample[index] < 1 for sample in samples) for index in range(3))
    assert samples[-1] == [0.0, 0.0, 0.0]
    report = write_hover_gif(frames, elapsed, output / "cards-elevated-light.gif")
    report["actual_intervals_ms"] = [end - begin for begin, end in zip(elapsed, elapsed[1:])]
    report["real_hover_intermediate_frames"] = [sum(0 < sample[index] < 1 for sample in samples) for index in range(3)]
    report["desktop_pointer_moved"] = False
    marker.deleteLater()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SITE / "dist" / "assets" / "previews")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    theme.set_mode("light")
    errors = []
    def error_hook(kind, error, tb):
        errors.append("".join(traceback.format_exception(kind, error, tb)))
        traceback.print_exception(kind, error, tb)
    sys.excepthook = error_hook
    window = CardsDemo()
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    window.fit_preview()
    QTest.qWait(150)
    content = window.content
    fonts = {}
    for text in content.findChildren(QtWidgets.QLabel):
        if text.text():
            fonts[text.text()] = _font_families(text, text.text())
    hosts = []
    images = []

    def save(name, widget, width):
        host = QtWidgets.QWidget()
        host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        host.setObjectName("cardCaptureRoot")
        host.setFont(content.font())
        host.setStyleSheet(content.styleSheet() + f"QWidget#cardCaptureRoot {{ background: {theme.tokens.background}; }}")
        host.setFixedWidth(width)
        layout = QtWidgets.QVBoxLayout(host)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(widget)
        host.show()
        host.adjustSize()
        QTest.qWait(70)
        host.adjustSize()
        app.processEvents()
        target = args.output_dir / f"{name}-light.png"
        if not host.grab().save(str(target)):
            raise RuntimeError(f"Unable to save {target}")
        images.append({"path": str(target), "dimensions": [host.width(), host.height()], "bytes": target.stat().st_size})
        hosts.append(host)

    # Capture elevated cards before removing siblings from the full demo.
    elevated = args.output_dir / "cards-elevated-light.png"
    assert content.tiles_preview.grab().save(str(elevated))
    with Image.open(elevated) as poster:
        rgba = poster.convert("RGBA")
        assert rgba.size == tuple(TILES_PREVIEW_SIZE)
        corners = [rgba.getpixel(point) for point in corners_of(rgba.size)]
        assert all(color[3] == 255 and min(color[:3]) > 235 for color in corners)
    images.append({"path": str(elevated), "dimensions": list(TILES_PREVIEW_SIZE), "bytes": elevated.stat().st_size,
                   "opaque_pale_corners": corners})
    # Preserve the group's live, compact layout before reparenting other cards.
    group = args.output_dir / "cards-group-light.png"
    assert content.settings.grab().save(str(group))
    images.append({"path": str(group), "dimensions": [content.settings.width(), content.settings.height()], "bytes": group.stat().st_size})
    animation = record_tiles(app, content, args.output_dir)
    save("cards-apps", content.apps_preview, 760)
    save("cards-simple", content.application_cards[1], 760)
    save("cards-header", content.requirements, 480)
    window.hide()
    for host in hosts:
        host.hide()
        host.close()
        host.deleteLater()
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    if errors:
        raise RuntimeError("Qt callbacks:\n" + "\n".join(errors))
    print(json.dumps({"images": images, "animation": animation, "fonts": fonts,
                      "qt_callback_errors": errors, "roots_hidden_from_desktop": True}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
