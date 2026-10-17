"""Capture the library's real in-window time wheels without desktop windows."""
import os
import io
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]
os.environ["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "offscreen"
os.environ["QT_SCALE_FACTOR"] = "1"

from fluentpy import TimePicker, QT_API, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font
from time_picker import TimePickerDemo
from PIL import Image, ImageChops, ImageStat
if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def capture_motion(app, output):
    canvas = QtWidgets.QWidget()
    canvas.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    canvas.setFixedSize(420, 520)
    palette = canvas.palette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(theme.tokens.background))
    canvas.setPalette(palette)
    canvas.setAutoFillBackground(True)
    picker = TimePicker(canvas, use_12_hour=True)
    picker.setGeometry(60, 240, 300, 38)
    picker.setTime(QtCore.QTime(14, 0))
    canvas.show()
    app.processEvents()
    picker.clearFocus()

    def confirm():
        picker._popup.confirm_button.click()
        picker.clearFocus()

    def reset():
        picker.setTime(QtCore.QTime(14, 0))
        picker.clearFocus()

    actions = [
        (450, picker.show_popup), (1100, lambda: picker._popup.wheel.step(1, 1)),
        (1500, lambda: picker._popup.wheel.step(0, 1)), (1850, lambda: picker._popup.wheel.step(2, -1)),
        (2300, confirm), (3200, reset),
    ]
    elapsed = QtCore.QElapsedTimer()
    elapsed.start()
    frames = []
    for target in range(0, 3600, 30):
        if target > elapsed.elapsed():
            QTest.qWait(target-elapsed.elapsed())
        while actions and actions[0][0] <= target:
            actions.pop(0)[1]()
        app.processEvents()
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        assert canvas.grab().save(buffer, "PNG")
        with Image.open(io.BytesIO(bytes(buffer.data()))) as image:
            frame = image.convert("RGB")
            assert min(ImageStat.Stat(frame).mean) > 180, "Unexpected dark capture frame"
            frames.append(frame.copy())
    assert ImageChops.difference(frames[0], frames[-1]).getbbox() is None, "Motion loop must return to its initial frame"
    frames[0].save(output / "time-picker-motion-light.png", optimize=True)
    palette_frames = [frame.quantize(colors=128) for frame in frames]
    palette_frames[0].save(output / "time-picker-motion-light.gif", save_all=True,
        append_images=palette_frames[1:], duration=30, loop=0, disposal=1, optimize=True)
    print("Captured time-picker-motion-light.gif:", len(frames), "opaque Qt frames, 3600ms")
    canvas.close()
    canvas.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    font = ui_font(14)
    font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias | QtGui.QFont.StyleStrategy.NoSubpixelAntialias)
    app.setFont(font)
    output = SITE / "dist/assets/previews"
    for mode in ("light", "dark"):
        theme.set_mode(mode)
        for twelve in (False, True):
            canvas = QtWidgets.QWidget()
            canvas.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
            canvas.setFixedSize(820, 540)
            palette = canvas.palette()
            palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(theme.tokens.background))
            canvas.setPalette(palette)
            canvas.setAutoFillBackground(True)
            field = TimePicker(canvas, use_12_hour=twelve)
            field.setGeometry(28, 250, 300, 38)
            anchor = TimePicker(canvas, use_12_hour=twelve)
            anchor.setGeometry(450, 250, 300, 38)
            anchor.setTime(QtCore.QTime(14, 0))
            canvas.show()
            app.processEvents()
            anchor.show_popup()
            QTest.qWait(260)
            app.processEvents()
            assert not anchor._popup.isWindow()
            image = canvas.grab()
            if mode == "light":
                path = output / f"time-picker-{'12' if twelve else '24'}-light.png"
            else:
                path = ROOT / "build" / f"time-picker-{'12' if twelve else '24'}-dark.png"
            assert image.save(str(path))
            print("Captured", path)
            canvas.close()
            canvas.deleteLater()
            app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        demo = TimePickerDemo()
        demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        demo.show()
        app.processEvents()
        demo.examples.picker12.setTime(QtCore.QTime(14, 0))
        demo.examples.picker12.show_popup()
        QTest.qWait(260)
        path = ROOT / "build" / f"time-picker-demo-{mode}.png"
        assert demo.grab().save(str(path))
        print("Captured", path)
        demo.close()
        demo.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        if mode == "light":
            capture_motion(app, output)


if __name__ == "__main__":
    main()
