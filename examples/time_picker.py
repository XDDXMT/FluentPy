"""Two time-picker formats. Run: python examples/time_picker.py."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import Button, HeaderCardWidget, TimePicker, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


class TimeExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timeExamples")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.picker24 = TimePicker()
        self.picker12 = TimePicker(use_12_hour=True)
        self.picker24.setAccessibleName("24小时制时间")
        self.picker12.setAccessibleName("12小时制时间")
        self.results = []
        for picker, title, description in (
            (self.picker24, "24 小时制", "小时与分钟，独立滚动选择。"),
            (self.picker12, "12 小时制", "增加 AM／PM，时间值仍统一为24小时制。"),
        ):
            card = HeaderCardWidget(title)
            hint = QtWidgets.QLabel(description)
            hint.setWordWrap(True)
            hint.setObjectName("muted")
            card.body_layout.addWidget(hint)
            picker.setMaximumWidth(300)
            card.body_layout.addSpacing(20)
            card.body_layout.addWidget(picker)
            result = QtWidgets.QLabel("尚未选择时间")
            result.setObjectName("result")
            result.setWordWrap(True)
            self.results.append(result)
            card.body_layout.addWidget(result)
            picker.timeChanged.connect(
                lambda value, label=result: label.setText(
                    "当前时间 · " + value.toString("HH:mm") if value.isValid() else "尚未选择时间"
                )
            )
            picker.timeAccepted.connect(
                lambda value, label=result: label.setText("已确认 · " + value.toString("HH:mm"))
            )
            row = QtWidgets.QHBoxLayout()
            current = Button("当前时间")
            current.clicked.connect(
                lambda _checked=False, view=picker: view.setTime(QtCore.QTime.currentTime())
            )
            clear = Button("清空")
            clear.clicked.connect(picker.clear)
            row.addWidget(current)
            row.addWidget(clear)
            row.addStretch()
            card.body_layout.addLayout(row)
            card.body_layout.addStretch()
            layout.addWidget(card, 1)
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#timeExamples QLabel {{ color: {theme.tokens.text}; background: transparent; }}"
            f"QWidget#timeExamples QLabel#muted {{ color: {theme.tokens.text_muted}; font-size: 12px; }}"
            f"QWidget#timeExamples QLabel#result {{ color: {theme.tokens.accent}; font-size: 13px; }}"
        )


class TimePickerDemo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("timeDemo")
        self.setWindowTitle("FluentPy · 时间选择器")
        self.setWindowIcon(QtGui.QIcon(str(ROOT / "src/fluentpy/assets/brand/fluentpy.svg")))
        self.resize(900, 640)
        self.setMinimumSize(720, 560)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 26, 32, 24)
        layout.setSpacing(18)
        top = QtWidgets.QHBoxLayout()
        brand = QtWidgets.QLabel("FLUENTPY  /  TIME PICKER")
        brand.setObjectName("eyebrow")
        top.addWidget(brand)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("深色"))
        self.dark = ToggleSwitch()
        self.dark.setChecked(theme.mode.value == "dark")
        self.dark.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        top.addWidget(self.dark)
        layout.addLayout(top)
        title = QtWidgets.QLabel("为下一件事，选个时间。")
        title.setObjectName("title")
        layout.addWidget(title)
        detail = QtWidgets.QLabel("滚动、拖动或点击相邻行；✓确认，×、Esc或点击外部取消。")
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        layout.addWidget(detail)
        self.examples = TimeExamples(self)
        layout.addWidget(self.examples, 1)
        footer = QtWidgets.QLabel("方向键切换列与数值 · Tab切换确认／取消 · 选择精确到分钟")
        footer.setObjectName("muted")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        self.backend = QtWidgets.QLabel(
            "后端：" + self.examples.picker24.acceleration_backend() + " · C优先，Python兼容"
        )
        self.backend.setObjectName("muted")
        layout.addWidget(self.backend)
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#timeDemo {{ background: {theme.tokens.background}; }}"
            f"QWidget#timeDemo > QLabel {{ color: {theme.tokens.text}; background: transparent; }}"
            f"QLabel#title {{ font-size: 26px; font-weight: 600; }}"
            f"QLabel#eyebrow {{ color: {theme.tokens.accent}; font-size: 11px; }}"
            f"QLabel#muted {{ color: {theme.tokens.text_muted}; font-size: 12px; }}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--open", choices=("24", "12"))
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    theme.set_mode("dark" if args.dark else "light")
    demo = TimePickerDemo()
    demo.show()
    if args.open:
        picker = demo.examples.picker12 if args.open == "12" else demo.examples.picker24
        picker.setTime(QtCore.QTime(14, 0))
        QtCore.QTimer.singleShot(120, picker.show_popup)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
