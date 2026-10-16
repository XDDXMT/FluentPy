"""A message card anchored to its trigger. Run: python examples/toast.py."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import Button, Toast, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme.fonts import ui_font


class ToastDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setWindowTitle("FluentPy · 消息浮层")
        self.setObjectName("toastDemo")
        self.resize(820, 380)
        self.setMinimumSize(660, 300)
        self.message = None
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 24)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("消息浮层"))
        controls.addStretch()
        controls.addWidget(QtWidgets.QLabel("深色"))
        toggle = ToggleSwitch()
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        controls.addWidget(toggle)
        root.addLayout(controls)
        root.addStretch(1)
        self.trigger = Button("Top", self)
        self.trigger.setFixedSize(186, 40)
        self.trigger.clicked.connect(self.show_message)
        root.addWidget(self.trigger, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        root.addSpacing(36)
        caption = QtWidgets.QLabel("点击 Top 显示 · 点击 × 关闭 · 提示绘制在主窗口内部")
        caption.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        root.addWidget(caption)
        root.addStretch(1)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def show_message(self):
        if self.message is not None:
            try:
                self.message.hide()
                self.message.close()
            except RuntimeError:
                pass
        self.message = Toast.success(
            "Lesson 4", detail="表达敬意吧，表达出敬意，然后迈向回旋的另一个全新阶段！",
            parent=self, target=self.trigger, timeout_ms=0,
        )

    def _apply_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f'QWidget#toastDemo {{ background: {"#ffffff" if theme.mode.value == "light" else "#202020"}; }}'
            f'QLabel {{ color: {theme.tokens.text}; background: transparent; font-size: 14px; }}'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = ToastDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    def ready():
        window.show_message()
        if args.screenshot:
            QtCore.QTimer.singleShot(Toast.SHOW_DURATION + 40, capture)
    def capture():
        if args.screenshot:
            app.processEvents()
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(args.screenshot.resolve())):
                raise RuntimeError("Unable to save message preview")
            if args.quit_after_screenshot:
                app.quit()
    QtCore.QTimer.singleShot(150, ready)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
