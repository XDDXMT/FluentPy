"""Capture real Qt expansion/collapse animations without showing a desktop window.

Run: python sites/fluentpy-docs/capture_expandable_previews.py
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

from capture_animations import _capture_font, _image
from PIL import Image, ImageChops
from expandable_cards import ExpandableSettings
from fluentpy import QT_API, theme
from fluentpy.qt import QtCore, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


LOOP_MS = 5000
SAMPLE_MS = 25
CANVAS_SIZE = (390, 400)


def _write_gif(frames, elapsed, target):
    palette = frames[0].quantize(colors=256)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    boundaries = [round(value / 10) * 10 for value in elapsed] + [LOOP_MS]
    durations = [max(10, end - start) for start, end in zip(boundaries, boundaries[1:])]
    indexed[0].save(target, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, disposal=2, optimize=True)
    with Image.open(target) as gif:
        first = gif.convert("RGB")
        corners = [(0, 0), (gif.width - 1, 0), (0, gif.height - 1),
                   (gif.width - 1, gif.height - 1)]
        background = [first.getpixel(point) for point in corners]
        count = gif.n_frames
        duration = 0
        for index in range(count):
            gif.seek(index)
            duration += gif.info["duration"]
            frame = gif.convert("RGB")
            assert [frame.getpixel(point) for point in corners] == background
            assert frame.getbbox() is not None, "Black animation frame"
        assert ImageChops.difference(first, gif.convert("RGB")).getbbox() is None
        assert gif.info["loop"] == 0
    assert target.stat().st_size < 900 * 1024
    return {"path": str(target), "bytes": target.stat().st_size,
            "dimensions": list(frames[0].size), "sampled_frames": len(frames),
            "encoded_frames": count, "encoded_duration_ms": duration,
            "stable_opaque_background": True, "loop_returns_to_initial_canvas": True}


def capture(app, mode, output):
    theme.set_mode(mode)
    host = QtWidgets.QWidget()
    host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    host.setObjectName("expandableCapture")
    host.setFont(_capture_font())
    host.setStyleSheet(f"QWidget#expandableCapture {{ background: {theme.tokens.background}; }}")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(20, 12, 20, 12)
    layout.setSpacing(0)
    content = ExpandableSettings(host)
    content.result.hide()
    layout.addWidget(content, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    layout.addStretch()
    host.setFixedSize(*CANVAS_SIZE)
    host.show()
    QTest.qWait(180)
    app.processEvents()
    assert content.accordion.height() <= host.height() - 24, "Expanded card exceeds the capture canvas"
    image = output / f"cards-expandable-{mode}.png"
    if not host.grab().save(str(image)):
        raise RuntimeError(f"Unable to save {image}")

    cards = [content.blend_card, content.hue_card, content.sharp_card]
    actions = [(500, cards[0]), (1200, cards[1]), (1950, cards[1]),
               (2600, cards[2]), (3300, cards[2]), (3950, cards[0])]
    performed = set()
    frames, elapsed, heights, failures = [], [], [], []
    clock = QtCore.QElapsedTimer()
    timer = QtCore.QTimer()
    timer.setInterval(SAMPLE_MS)
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    loop = QtCore.QEventLoop()

    def tick():
        try:
            now = clock.elapsed()
            if now >= LOOP_MS:
                timer.stop()
                loop.quit()
                return
            for index, (at, card) in enumerate(actions):
                if now >= at and index not in performed:
                    card.header_button.click()
                    performed.add(index)
            frames.append(_image(host))
            elapsed.append(now)
            heights.append([card.height() for card in cards])
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
    assert len(performed) == len(actions)
    assert all(len({sample[index] for sample in heights}) > 4 for index in range(3)), \
        "Each group must have genuine intermediate expansion/collapse frames"
    assert [card.is_expanded() for card in cards] == [True, False, False]
    report = _write_gif(frames, elapsed, output / f"cards-expandable-{mode}.gif")
    report["native_card_heights_per_group"] = [len({sample[index] for sample in heights}) for index in range(3)]
    intervals = [end - start for start, end in zip(elapsed, elapsed[1:])]
    report["actual_intervals_ms"] = {
        "minimum": min(intervals), "maximum": max(intervals),
        "mean": round(sum(intervals) / len(intervals), 2),
    }
    report["poster"] = {"path": str(image), "bytes": image.stat().st_size,
                        "dimensions": [host.width(), host.height()]}
    assert not any(widget.isVisible() and not widget.testAttribute(
        QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen) for widget in app.topLevelWidgets()), \
        "Unexpected visible desktop window"
    host.close()
    host.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SITE / "dist/assets/previews")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    errors = []
    def error_hook(kind, error, tb):
        errors.append("".join(traceback.format_exception(kind, error, tb)))
        traceback.print_exception(kind, error, tb)
    sys.excepthook = error_hook
    reports = [capture(app, mode, args.output_dir) for mode in ("light", "dark")]
    if errors:
        raise RuntimeError("Qt callbacks:\n" + "\n".join(errors))
    print(json.dumps({"previews": reports, "qt_callback_errors": errors,
                      "roots_hidden_from_desktop": True}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
