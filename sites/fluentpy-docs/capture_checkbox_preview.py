"""Capture the real compact two-line CheckBox in light mode."""
from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path.insert(0, str(ROOT / 'src'))

from fluentpy import CheckBox, RadioButton, theme
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme.fonts import ui_font


def main():
    app = QtWidgets.QApplication([])
    app.setFont(ui_font(14))
    theme.set_mode('light')
    canvas = QtWidgets.QWidget()
    canvas.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    canvas.setObjectName('checkCanvas')
    canvas.setStyleSheet('QWidget#checkCanvas { background: #f7f9fc; }')
    check = CheckBox('Other files', canvas, description='760.0 KB')
    check.resize(check.sizeHint())
    check.move(6, 6)
    canvas.resize(check.width()+12, check.height()+12)
    canvas.show()
    app.processEvents()
    check.clearFocus()
    for state, suffix in ((False, ''), (True, '-checked')):
        check.setChecked(state)
        app.processEvents()
        preview = SITE / f'dist/assets/previews/checkbox-description{suffix}-light.png'
        assert canvas.grab().save(str(preview))
        print(f'{preview}: {canvas.width()}x{canvas.height()}')
    canvas.close()
    plain = QtWidgets.QWidget()
    plain.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    plain.setObjectName('plainCheckPreview')
    plain.setStyleSheet('QWidget#plainCheckPreview { background: #fafbfc; }')
    row = QtWidgets.QHBoxLayout(plain)
    row.setContentsMargins(20, 18, 20, 18)
    row.setSpacing(16)
    row.addStretch()
    for widget in (CheckBox('保留上次的选择'), RadioButton('轻量模式')):
        widget.setChecked(True)
        row.addWidget(widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
    row.addStretch()
    plain.resize(440, 138)
    plain.show()
    app.processEvents()
    if app.focusWidget():
        app.focusWidget().clearFocus()
    assert plain.grab().save(str(SITE / 'dist/assets/previews/checks-light.png'))
    plain.close()


if __name__ == '__main__':
    main()
