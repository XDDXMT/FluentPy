"""Native color controls. Run python examples/colors.py or run_colors.bat."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fluentpy import (
    Button,
    ColorDialog,
    ColorPaletteButton,
    ColorPickerButton,
    ColorPickerPanel,
    ColorSwatchGroup,
    EyeDropperButton,
    FluentScrollBar,
    HeaderCardWidget,
    ToggleSwitch,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


def label(text, *, muted=False):
    widget = QtWidgets.QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    widget.setObjectName("colorMuted" if muted else "colorLabel")
    return widget


class ColorExamples(QtWidgets.QWidget):
    """Embeddable demo; never changes the global theme or starts screen capture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("colorExamples")
        # Start stacked so a scroll area's first size negotiation does not
        # inherit the combined minimum width of the two desktop columns.
        root = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.TopToBottom, self)
        self.columns = root
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        self.editor_card = HeaderCardWidget("精确编辑")
        self.panel = ColorPickerPanel("#e4579b", enable_alpha=True)
        self.editor_card.body_layout.setContentsMargins(16, 14, 16, 16)
        self.editor_card.body_layout.addWidget(self.panel)
        self.editor_card.body_layout.addWidget(label("Hex · RGB / HSV · Alpha", muted=True))
        root.addWidget(self.editor_card, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        column = QtWidgets.QVBoxLayout()
        column.setSpacing(16)
        self.choices_card = HeaderCardWidget("选择颜色")
        self.choices_card.body_layout.setContentsMargins(16, 14, 16, 16)
        self.palette_button = ColorPaletteButton("#0078d4")
        self.picker_button = ColorPickerButton("#e4579b")
        self.eyedropper = EyeDropperButton("#0078d4")
        for title, button in (
            ("主题色板", self.palette_button),
            ("完整编辑器", self.picker_button),
            ("屏幕取色", self.eyedropper),
        ):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(label(title), 1)
            row.addWidget(button)
            self.choices_card.body_layout.addLayout(row)
        self.dialog_button = Button("打开颜色对话框")
        self.dialog_button.clicked.connect(self._open_dialog)
        self.choices_card.body_layout.addWidget(self.dialog_button)
        self.choices_card.body_layout.addWidget(
            label("展开后可先预览；点击确定才保存。Esc 或取消恢复原色。", muted=True)
        )
        column.addWidget(self.choices_card)
        swatch_card = HeaderCardWidget("快捷色块")
        swatch_card.body_layout.setContentsMargins(16, 14, 16, 16)
        self.swatches = ColorSwatchGroup()
        self.swatches.setMinimumHeight(72)
        swatch_card.body_layout.addWidget(self.swatches)
        self.result = label("当前颜色 · #e4579b")
        self.result.setAccessibleName("颜色操作结果")
        swatch_card.body_layout.addWidget(self.result)
        column.addWidget(swatch_card)
        column.addStretch()
        root.addLayout(column)
        self.dialog = None
        self.panel.colorChanged.connect(self._live_color)
        self.picker_button.colorChanged.connect(self._chosen)
        self.palette_button.colorChanged.connect(self._chosen)
        self.swatches.colorChanged.connect(self._chosen)
        self.eyedropper.colorChanged.connect(self._chosen)
        self.eyedropper.failed.connect(lambda message: self.result.setText(message))
        self._refresh_theme()
        theme.subscribe(self, self._refresh_theme)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= 700
        direction = (
            QtWidgets.QBoxLayout.Direction.LeftToRight
            if wide
            else QtWidgets.QBoxLayout.Direction.TopToBottom
        )
        if self.columns.direction() != direction:
            self.columns.setDirection(direction)
            self.columns.setStretch(0, 3 if wide else 0)
            self.columns.setStretch(1, 2 if wide else 0)
            self.updateGeometry()

    def _live_color(self, color):
        self.result.setText("编辑中 · " + color.name(QtGui.QColor.NameFormat.HexArgb))

    def _chosen(self, color):
        if not color.isValid():
            self.result.setText("已选择自动颜色")
            return
        self.panel.set_color(color)
        self.result.setText("已选择 · " + color.name(QtGui.QColor.NameFormat.HexArgb))

    def _open_dialog(self):
        if self.dialog is None:
            self.dialog = ColorDialog(parent=self.window(), enable_alpha=True)
            self.destroyed.connect(self.dialog.deleteLater)
            self.dialog.colorSelected.connect(self._chosen)
        self.dialog.set_color(self.panel.color())
        self.dialog.open()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#colorExamples {{ background: transparent; }}"
            f"QWidget#colorExamples QLabel#colorLabel {{ color: {theme.tokens.text}; background: transparent; font-weight:400; }}"
            f"QWidget#colorExamples QLabel#colorMuted {{ color: {theme.tokens.text_muted}; background: transparent; font-size:12px; font-weight:400; }}"
        )


class ColorDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("colorDemo")
        self.setWindowTitle("FluentPy · 颜色与取色")
        self.setWindowIcon(
            QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
        )
        self.resize(820, 740)
        self.setMinimumSize(650, 440)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(18)
        heading = QtWidgets.QHBoxLayout()
        title = label("颜色与取色")
        title.setObjectName("colorTitle")
        heading.addWidget(title, 1)
        heading.addWidget(label("深色模式"))
        self.theme_toggle = ToggleSwitch()
        self.theme_toggle.setChecked(dark)
        self.theme_toggle.toggled.connect(
            lambda checked: theme.set_mode("dark" if checked else "light")
        )
        heading.addWidget(self.theme_toggle)
        root.addLayout(heading)
        root.addWidget(label("色板、精确编辑与屏幕取色，使用同一组原生 Qt 控件。", muted=True))
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBar(FluentScrollBar(parent=scroll))
        self.content = ColorExamples()
        scroll.setWidget(self.content)
        self.content.setAutoFillBackground(False)
        root.addWidget(scroll, 1)
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#colorDemo, QScrollArea {{ background:{theme.tokens.background}; border:none; }}"
            f"QWidget#colorDemo QLabel {{ color:{theme.tokens.text}; background:transparent; }}"
            "QLabel#colorTitle {font-size:24px;font-weight:600;}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    app.setFont(ui_font(14))
    window = ColorDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    if args.screenshot:

        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.screenshot))
            if args.quit_after_screenshot:
                app.quit()

        QtCore.QTimer.singleShot(350, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
