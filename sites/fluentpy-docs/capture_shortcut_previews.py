"""Capture native Qt shortcut keycaps and a complete edit/save interaction."""
from __future__ import annotations

import json
import sys
import traceback

from capture_animations import (ROOT, SITE, LOOP_MS, SAMPLE_MS, QTest, QtCore, QtWidgets,
                               _capture_font, _font_families, _image, _write_gif)
from PIL import ImageChops
from fluentpy import ShortcutPicker, theme


class Canvas(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.setObjectName("shortcutCanvas")
        self.setStyleSheet("QWidget#shortcutCanvas { background: #fafbfc; }")
        self.setFixedSize(720, 480)
        self.picker = ShortcutPicker("Ctrl+Shift+A", self)
        self.picker.move(28, 396)
        self.picker.resize(self.picker.sizeHint())
        self.caption = QtWidgets.QLabel("点击铅笔，录制快捷键", self)
        self.caption.setFont(_capture_font())
        self.caption.setGeometry(28, 358, 350, 28)
        self.orphans = []

    def eventFilter(self, widget, event):
        if event.type() == QtCore.QEvent.Type.Show and isinstance(widget, QtWidgets.QLabel) and widget.isWindow():
            self.orphans.append(widget.text())
        return False


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    theme.set_mode("light")
    canvas = Canvas()
    app.installEventFilter(canvas)
    canvas.show()
    QTest.qWait(180)
    output = SITE / "dist" / "assets" / "previews"
    _image(canvas.picker).save(output / "shortcut-picker-light.png", optimize=True)
    frames, times, actions, errors = [], [], set(), []
    poster, fonts = None, {}
    loop, timer, clock = QtCore.QEventLoop(), QtCore.QTimer(), QtCore.QElapsedTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.setInterval(SAMPLE_MS)
    old_hook = sys.excepthook
    sys.excepthook = lambda kind, error, tb: errors.append("".join(traceback.format_exception(kind, error, tb)))

    def tick():
        nonlocal poster
        try:
            ms = clock.elapsed()
            if ms >= LOOP_MS:
                timer.stop()
                loop.quit()
                return
            if ms >= 350 and "open" not in actions:
                QTest.mouseClick(canvas.picker.edit_button, QtCore.Qt.MouseButton.LeftButton)
                actions.add("open")
                assert not canvas.picker._editor.isWindow()
                assert canvas.picker._editor.windowHandle() is None
                fonts['keys'] = _font_families(canvas.picker._editor.recorder, 'Ctrl Shift A')
            editor = canvas.picker._editor
            if editor is not None:
                if ms >= 850 and "enter" not in actions:
                    QTest.keyClick(editor.recorder, QtCore.Qt.Key.Key_Return,
                        QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier)
                    actions.add("enter")
                if ms >= 1350 and "alt" not in actions:
                    QTest.keyClick(editor.recorder, QtCore.Qt.Key.Key_L, QtCore.Qt.KeyboardModifier.AltModifier)
                    actions.add("alt")
                if ms >= 1900 and "reset" not in actions:
                    QTest.mouseClick(editor.reset_button, QtCore.Qt.MouseButton.LeftButton)
                    actions.add("reset")
                if ms >= 2250 and "alt-again" not in actions:
                    QTest.keyClick(editor.recorder, QtCore.Qt.Key.Key_L, QtCore.Qt.KeyboardModifier.AltModifier)
                    actions.add("alt-again")
                if ms >= 2800 and "save" not in actions:
                    QTest.mouseClick(editor.yes_button, QtCore.Qt.MouseButton.LeftButton)
                    actions.add("save")
            if ms >= 3350 and "restore" not in actions:
                assert canvas.picker.key_sequence().toString() == 'Alt+L', canvas.picker.key_sequence().toString()
                canvas.picker.set_key_sequence("Ctrl+Shift+A")
                canvas.picker.clearFocus()
                canvas.picker.edit_button.clearFocus()
                actions.add("restore")
            frame = _image(canvas)
            frames.append(frame)
            times.append(ms)
            if poster is None and 1550 <= ms < 1850:
                poster = frame.copy()
        except Exception:
            errors.append(traceback.format_exc())
            timer.stop()
            loop.quit()

    try:
        clock.start()
        tick()
        timer.timeout.connect(tick)
        timer.start()
        loop.exec()
        assert not errors, errors
        assert len(actions) == 7 and canvas.picker._editor is None
        assert not canvas.orphans, canvas.orphans
        assert ImageChops.difference(frames[0], frames[-1]).getbbox() is None
        poster.save(output / 'shortcut-recording-light.png', optimize=True)
        result = _write_gif(frames, times, output / 'shortcut-recording-light.gif')
        result.update({'actions': sorted(actions), 'orphan_labels': canvas.orphans, 'fonts': fonts})
        (ROOT / 'build/shortcut-capture-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in result.items() if key != 'encoded_frame_durations_ms'}, ensure_ascii=False, indent=2))
    finally:
        timer.stop()
        app.removeEventFilter(canvas)
        sys.excepthook = old_hook
        canvas.close()
        canvas.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == '__main__':
    main()
