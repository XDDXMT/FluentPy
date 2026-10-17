"""Capture actual Qt inputs and FluentPy focus states for the introduction."""

import os
from pathlib import Path
import sys

# Windows offscreen font discovery misses CJK; hidden native roots retain the
# system's real fallback fonts without showing a window on the desktop.
os.environ["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "offscreen"
os.environ["QT_SCALE_FACTOR"] = "2"
SITE = Path(__file__).resolve().parent
from source_project import source_root
sys.path.insert(0, str(source_root() / "src"))

from fluentpy import LineEdit, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


def main():
    app = QtWidgets.QApplication([])
    # Use Qt's bundled standard style for a reproducible light QLineEdit,
    # independent of the Windows system theme or native composition state.
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(QtCore.Qt.ColorScheme.Light)
    font = ui_font(14)
    font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias | QtGui.QFont.StyleStrategy.NoSubpixelAntialias)
    app.setFont(font)
    app.setPalette(app.style().standardPalette())
    theme.set_mode("light")
    theme.set_active(True)
    output = SITE / "dist" / "assets" / "previews"
    output.mkdir(parents=True, exist_ok=True)
    for name, input_type in (("qt", QtWidgets.QLineEdit), ("fluent", LineEdit)):
        canvas = QtWidgets.QWidget()
        canvas.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        canvas.setFixedSize(260, 58)
        palette = canvas.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#fafbfc"))
        canvas.setPalette(palette)
        canvas.setAutoFillBackground(True)
        edit = input_type(parent=canvas)
        edit.setText("把灵感写下来")
        edit.setFont(font)
        text = QtGui.QTextLayout(edit.text(), edit.font())
        text.beginLayout()
        text.createLine()
        text.endLayout()
        runs = text.glyphRuns()
        assert runs and all(0 not in run.glyphIndexes() for run in runs), "Missing Chinese glyphs"
        edit.setFixedSize(236, 34)
        edit.move(12, 12)
        edit.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        canvas.show()
        app.processEvents()
        image = canvas.grab()
        path = output / f"migration-input-{name}-light.png"
        assert image.save(str(path)), path
        print(f"Captured {path.name}: {image.width()}x{image.height()} (260x58 logical)")
        if name == "fluent":
            # Settle the widget's own focus timeline; no desktop focus is needed.
            edit._focus_animation.setStartValue(0.0)
            edit._focus_animation.setEndValue(1.0)
            edit._focus_animation.setCurrentTime(edit._focus_animation.duration())
            app.processEvents()
            path = output / "migration-input-focus-light.png"
            assert canvas.grab().save(str(path)), path
            print(f"Captured {path.name}: native focus state")
        canvas.close()
        canvas.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    main()
