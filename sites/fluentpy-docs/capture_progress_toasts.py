"""Capture the actual Qt task notification animations without desktop windows."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

from capture_animations import (
    ROOT, SITE, LOOP_MS, SAMPLE_MS, QTest, QtCore, QtGui, QtWidgets,
    _capture_font, _font_families, _image, _write_gif,
)
from PIL import ImageChops
from fluentpy import Button, ProgressToast, theme


class Canvas(QtWidgets.QWidget):
    def __init__(self, indeterminate):
        super().__init__()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.setObjectName("taskCanvas")
        self.setStyleSheet("QWidget#taskCanvas { background: #fafbfc; }")
        self.setFont(_capture_font())
        self.setFixedSize(520, 190)
        self.indeterminate = indeterminate
        self.message = None
        self.button = Button("开始任务", self)
        self.button.setGeometry(24, 132, 116, 32)
        self.button.clicked.connect(self.start)
        self.shows, self.orphans = 0, []

    def start(self):
        self.message = ProgressToast.start("正在下载文件，请稍候…", parent=self,
            placement="top-left" if self.indeterminate else "bottom-right",
            indeterminate=self.indeterminate)
        self.message.destroyed.connect(self.released)

    def released(self):
        self.message = None

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.Type.Show:
            if isinstance(widget, ProgressToast) and widget.parentWidget() is self:
                self.shows += 1
            if isinstance(widget, QtWidgets.QLabel) and widget.isWindow():
                self.orphans.append(widget.text())
        return False


def capture(app, indeterminate):
    canvas = Canvas(indeterminate)
    app.installEventFilter(canvas)
    canvas.show()
    QTest.qWait(80)
    _image(canvas)
    frames, times, states = [], [], []
    actions = set()
    failures = []
    poster = None
    clock = QtCore.QElapsedTimer()
    loop = QtCore.QEventLoop()
    timer = QtCore.QTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.setInterval(SAMPLE_MS)
    fonts = {}

    def tick():
        nonlocal poster
        try:
            elapsed = clock.elapsed()
            if elapsed >= LOOP_MS:
                timer.stop()
                loop.quit()
                return
            if elapsed >= 400 and "start" not in actions:
                QTest.mouseClick(canvas.button, QtCore.Qt.MouseButton.LeftButton)
                actions.add("start")
                fonts["title"] = _font_families(canvas.message._title, canvas.message._title.text())
            toast = canvas.message
            if toast is not None:
                for at, value in ((750, 18), (1100, 46), (1450, 76), (1750, 88)):
                    if not indeterminate and elapsed >= at and at not in actions:
                        toast.set_progress(value)
                        actions.add(at)
                if elapsed >= 2050 and "finish" not in actions:
                    toast.finish("下载完成", timeout_ms=0)
                    actions.add("finish")
                if elapsed >= 2950 and "close" not in actions:
                    QTest.mouseClick(toast.close_button, QtCore.Qt.MouseButton.LeftButton)
                    actions.add("close")
                states.append({"ms": elapsed, "state": toast.state(), "opacity": toast._opacity.opacity(),
                    "progress": toast._display_value, "width": toast.width(), "closing": toast._closing})
            if elapsed >= 3300:
                canvas.button.clearFocus()
            frame = _image(canvas)
            frames.append(frame)
            times.append(elapsed)
            if poster is None and 1250 <= elapsed < 1800:
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
        assert not failures, failures
        assert canvas.message is None and canvas.shows == 1 and not canvas.orphans
        assert ImageChops.difference(frames[0], frames[-1]).getbbox() is None
        entering = [s for s in states if 0 < s["opacity"] < 1 and not s["closing"]]
        exiting = [s for s in states if 0 < s["opacity"] < 1 and s["closing"]]
        assert len(entering) >= 4 and len(exiting) >= 4
        assert len({s["width"] for s in states if s["state"] == "success"}) >= 4
        name = "progress-toast" + ("-indeterminate" if indeterminate else "") + "-light"
        output = SITE / "dist" / "assets" / "previews"
        poster.save(output / f"{name}.png", optimize=True)
        result = _write_gif(frames, times, output / f"{name}.gif")
        result.update({"entry_intermediate_frames": len(entering), "exit_intermediate_frames": len(exiting),
                       "show_events": canvas.shows, "orphan_labels": canvas.orphans, "fonts": fonts,
                       "states": states})
        return result
    finally:
        timer.stop()
        app.removeEventFilter(canvas)
        canvas.close()
        canvas.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    theme.set_mode("light")
    errors = []
    previous_hook = sys.excepthook
    sys.excepthook = lambda kind, error, tb: errors.append("".join(traceback.format_exception(kind, error, tb)))
    try:
        results = [capture(app, mode) for mode in (False, True)]
        assert not errors, errors
        report = ROOT / "build" / "progress-toast-capture-validation.json"
        report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps([{key: value for key, value in result.items() if key not in {"states", "encoded_frame_durations_ms"}}
                          for result in results], ensure_ascii=False, indent=2))
    finally:
        sys.excepthook = previous_hook


if __name__ == "__main__":
    main()
