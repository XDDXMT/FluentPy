"""Record, preview and save a shortcut. Run: python examples/shortcut_picker.py."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import Button, ShortcutPicker, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


class ShortcutExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(QtWidgets.QLabel("激活快捷键", self))
        self.picker = ShortcutPicker("Ctrl+Shift+A", self)
        self.picker.set_reserved_sequences(["Ctrl+S", "Ctrl+O"])
        layout.addWidget(self.picker, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.value = QtWidgets.QLabel("当前：Ctrl+Shift+A", self)
        layout.addWidget(self.value)
        self.shortcut = QtGui.QShortcut(self.picker.key_sequence(), self)
        self.shortcut.activated.connect(self._triggered)
        self._count = 0
        self.picker.sequenceChanged.connect(self._update_shortcut)
        note = QtWidgets.QLabel(
            "点击铅笔后按下组合键；保存才会回填。保存后可在本窗口按下快捷键体验，Ctrl+S、Ctrl+O在此示例中标为已占用。",
            self,
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QtWidgets.QHBoxLayout()
        restore = Button("设为 Ctrl+Shift+A", self)
        restore.clicked.connect(lambda: self.picker.set_key_sequence("Ctrl+Shift+A"))
        clear = Button("清空", self)
        clear.clicked.connect(self.picker.clear)
        row.addWidget(restore)
        row.addWidget(clear)
        row.addStretch()
        layout.addLayout(row)

    def _update_shortcut(self, text):
        self.shortcut.setKey(self.picker.key_sequence())
        self.value.setText("当前：" + (text or "未设置"))

    def _triggered(self):
        self._count += 1
        self.value.setText(f"快捷键已触发 {self._count} 次")


class ShortcutDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("shortcutDemo")
        self.setWindowTitle("FluentPy · 快捷键选择器")
        self.resize(800, 570)
        self.setMinimumSize(500, 440)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 26, 32, 26)
        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("快捷键选择器", self)
        title.setObjectName("demoTitle")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("深色", self))
        toggle = ToggleSwitch(self)
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        top.addWidget(toggle)
        layout.addLayout(top)
        layout.addStretch()
        self.examples = ShortcutExamples(self)
        layout.addWidget(self.examples)
        layout.addStretch()
        backend = (
            "C 加速" if self.examples.picker.acceleration_backend() == "native" else "Python 兼容"
        )
        bottom = QtWidgets.QLabel(f"Qt 原生按键事件 · {backend}组合键校验 · 页内浮层", self)
        bottom.setObjectName("muted")
        layout.addWidget(bottom)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _apply_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#shortcutDemo {{ background: {theme.tokens.background}; }}"
            f"QLabel {{ color: {theme.tokens.text}; background: transparent; font-size: 14px; }}"
            "QLabel#demoTitle { font-size: 22px; font-weight: 600; }"
            f"QLabel#muted {{ color: {theme.tokens.text_muted}; font-size: 12px; }}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--editor", action="store_true")
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot")
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = ShortcutDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    if args.editor:
        window.examples.picker.open_editor()

    def capture():
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(args.screenshot.resolve())):
            raise RuntimeError("Could not save shortcut preview")
        if args.quit_after_screenshot:
            window.close()
            app.quit()

    if args.screenshot:
        QtCore.QTimer.singleShot(350, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
