"""Standalone FluentPy wheel date picker. Run: python examples/date_picker.py."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import AccentButton, Button, DatePicker, ToggleSwitch, theme  # noqa: E402
from fluentpy.qt import QtCore, QtGui, QtWidgets  # noqa: E402
from fluentpy.theme.fonts import ui_font  # noqa: E402


class DatePickerDemo(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dateDemo")
        self.setWindowTitle("FluentPy · 日期选择器")
        self.resize(860, 630)
        self.setMinimumSize(760, 600)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 24)
        root.setSpacing(14)
        top = QtWidgets.QHBoxLayout()
        eyebrow = QtWidgets.QLabel("FLUENTPY  /  DATE PICKER")
        eyebrow.setObjectName("eyebrow")
        top.addWidget(eyebrow)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("深色"))
        self.dark = ToggleSwitch()
        self.dark.setChecked(theme.mode.value == "dark")
        self.dark.toggled.connect(lambda value: theme.set_mode("dark" if value else "light"))
        top.addWidget(self.dark)
        root.addLayout(top)
        title = QtWidgets.QLabel("为下一件事，选个日子。")
        title.setObjectName("title")
        root.addWidget(title)
        subtitle = QtWidgets.QLabel("点击年、月、日，展开三列滚轮。确认后才会保存，取消时保留原来的选择。")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        root.addSpacing(12)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(24)
        form = QtWidgets.QFrame()
        form.setObjectName("demoCard")
        left = QtWidgets.QVBoxLayout(form)
        left.setContentsMargins(24, 25, 24, 25)
        left.setSpacing(12)
        form_title = QtWidgets.QLabel("日期选择")
        form_title.setObjectName("sectionTitle")
        left.addWidget(form_title)
        help_label = QtWidgets.QLabel("留空也可以。先选一个日期试试。")
        help_label.setObjectName("muted")
        left.addWidget(help_label)
        left.addSpacing(30)
        self.picker = DatePicker()
        self.picker.setFixedWidth(300)
        left.addWidget(self.picker)
        self.result = QtWidgets.QLabel("尚未选择日期")
        self.result.setObjectName("dateResult")
        left.addWidget(self.result)
        left.addSpacing(18)
        actions = QtWidgets.QHBoxLayout()
        sample = AccentButton("示例日期")
        sample.clicked.connect(lambda: self.picker.set_date(QtCore.QDate(2024, 2, 26)))
        clear = Button("清空")
        clear.clicked.connect(self.picker.clear)
        actions.addWidget(sample)
        actions.addWidget(clear)
        actions.addStretch()
        left.addLayout(actions)
        left.addStretch()
        self.picker.dateChanged.connect(self._changed)
        body.addWidget(form, 1)

        notes = QtWidgets.QVBoxLayout()
        notes.setSpacing(12)
        heading = QtWidgets.QLabel("滚动、点击，也可以用键盘。")
        heading.setObjectName("sectionTitle")
        heading.setWordWrap(True)
        notes.addWidget(heading)
        for title_text, detail in (
            ("01  三列独立选择", "滚轮或拖动选择年、月、日。点击相邻行，也能直接切换。"),
            ("02  确认才保存", "✓ 或 Enter 确认，×、Esc 或点击外部取消。左右方向键切换列。"),
            ("03  日历运算自动适配", "优先C运算，缺少扩展时使用Python；2月29日切换年份会调整为有效日期。"),
        ):
            label = QtWidgets.QLabel(title_text)
            label.setObjectName("noteTitle")
            label.setWordWrap(True)
            notes.addWidget(label)
            text = QtWidgets.QLabel(detail)
            text.setObjectName("muted")
            text.setWordWrap(True)
            notes.addWidget(text)
        notes.addSpacing(6)
        notes.addWidget(QtWidgets.QLabel("限定范围示例 · 2024 年 2 月"))
        self.bounded = DatePicker()
        self.bounded.set_date_range(QtCore.QDate(2024, 2, 1), QtCore.QDate(2024, 2, 29))
        self.bounded.set_date(QtCore.QDate(2024, 2, 26))
        notes.addWidget(self.bounded)
        notes.addStretch()
        body.addLayout(notes, 1)
        root.addLayout(body, 1)
        backend = "C 加速" if self.picker.acceleration_backend() == "native" else "Python 兼容"
        footer = QtWidgets.QLabel(f"默认尺寸 300 × 38 · {backend} / Qt 绘制")
        footer.setObjectName("muted")
        root.addWidget(footer)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _changed(self, date: QtCore.QDate) -> None:
        self.result.setText(date.toString("yyyy 年 M 月 d 日") if date.isValid() else "尚未选择日期")

    def _apply_theme(self) -> None:
        tokens = theme.tokens
        self.setFont(ui_font(14, self.font()))
        self.setStyleSheet(f'''
QWidget#dateDemo {{ background: {tokens.background}; }}
QLabel {{ color: {tokens.text}; background: transparent; font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 14px; }}
QLabel#eyebrow {{ color: {tokens.accent}; font-size: 11px; font-weight: 600; }}
QLabel#title {{ font-size: 28px; font-weight: 600; }}
QLabel#sectionTitle {{ font-size: 18px; font-weight: 600; }}
QLabel#noteTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#muted {{ color: {tokens.text_muted}; font-size: 12px; }}
QLabel#dateResult {{ color: {tokens.accent}; font-size: 14px; }}
QFrame#demoCard {{ background: {tokens.surface}; border: 1px solid {tokens.border}; border-radius: 10px; }}
''')

    def save_preview(self, path: Path, *, popup: bool = False) -> None:
        """Render this demo's own Qt surfaces, including its real popup."""
        if popup:
            self.picker.set_date(QtCore.QDate(2024, 2, 26))
            self.picker.show_popup()
            app = QtWidgets.QApplication.instance()
            app.processEvents()
            # Keep the complete flyout inside this demo's illustration canvas.
            self.picker._popup.move(self.mapToGlobal(QtCore.QPoint(self.width() - 390, 125)))
            app.processEvents()
        image = self.grab()
        if popup:
            painter = QtGui.QPainter(image)
            position = self.picker._popup.pos() - self.mapToGlobal(QtCore.QPoint())
            painter.drawPixmap(position, self.picker._popup.grab())
            painter.end()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(path)):
            raise RuntimeError(f"Could not render {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--open", action="store_true", help="Open the primary date picker")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    theme.set_mode("dark" if args.dark else "light")
    try:
        window = DatePickerDemo()
    except RuntimeError as error:
        QtWidgets.QMessageBox.critical(None, "后端配置错误", str(error))
        return 1
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    if args.screenshot:
        def capture():
            window.save_preview(args.screenshot.resolve(), popup=args.open)
            if args.quit_after_screenshot:
                app.quit()
        QtCore.QTimer.singleShot(160, capture)
    elif args.open:
        QtCore.QTimer.singleShot(100, window.picker.show_popup)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
