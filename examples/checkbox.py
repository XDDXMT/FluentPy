"""Compact checkbox with a secondary description. Run python examples/checkbox.py."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import CheckBox, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme.fonts import ui_font


class CheckBoxDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("checkBoxDemo")
        self.setWindowTitle("FluentPy · 带说明的复选框")
        self.resize(420, 260)
        self.setMinimumSize(340, 240)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        header = QtWidgets.QHBoxLayout()
        header.addWidget(QtWidgets.QLabel("带说明的复选框", self))
        header.addStretch()
        switch = ToggleSwitch(self)
        switch.setChecked(dark)
        switch.setAccessibleName("深色主题")
        switch.toggled.connect(lambda value: theme.set_mode("dark" if value else "light"))
        header.addWidget(switch)
        layout.addLayout(header)
        layout.addStretch()
        self.check = CheckBox("Other files", self, description="760.0 KB")
        layout.addWidget(self.check, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.result = QtWidgets.QLabel("未选择", self)
        self.check.toggled.connect(
            lambda value: self.result.setText("已选择 Other files" if value else "未选择")
        )
        layout.addWidget(self.result)
        layout.addStretch()
        hint = QtWidgets.QLabel("点击方框或两行文字均可选择，也支持 Tab 和空格。", self)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _apply_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#checkBoxDemo {{ background: {theme.tokens.background}; }}"
            f"QLabel {{ color: {theme.tokens.text_muted}; background: transparent; }}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot")
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = CheckBoxDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()

    def capture():
        if app.focusWidget() is not None:
            app.focusWidget().clearFocus()
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(args.screenshot.resolve())):
            raise RuntimeError("Could not save checkbox demo")
        if args.quit_after_screenshot:
            window.close()
            app.quit()

    if args.screenshot:
        QtCore.QTimer.singleShot(200, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
