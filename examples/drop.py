"""File and folder drop areas. Run: python examples/drop.py."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import Button, FileDropWidget, FolderDropWidget, SimpleCardWidget, TextEdit, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


class _DropPreviewSurface(SimpleCardWidget):
    def _surface_color(self):
        return QtGui.QColor(theme.tokens.surface_high)


class DropExamples(QtWidgets.QWidget):
    """The same library widgets are used by the standalone demo and showcase."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        self.file_drop = FileDropWidget(self)
        self.folder_drop = FolderDropWidget(self)
        for title, drop in (("拖放文件组件", self.file_drop), ("拖放文件夹组件", self.folder_drop)):
            label = QtWidgets.QLabel(title, self)
            label.setObjectName("dropSectionTitle")
            root.addWidget(label)
            surface = _DropPreviewSurface(self)
            surface.setObjectName("dropExampleSurface")
            content = QtWidgets.QVBoxLayout(surface)
            content.setContentsMargins(14, 14, 14, 14)
            content.addWidget(drop, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
            drop.setFixedSize(drop.sizeHint())
            root.addWidget(surface)
            drop.pathsSelected.connect(self._selected)
            drop.pathsRejected.connect(self._rejected)
            drop.errorOccurred.connect(self._error)
        row = QtWidgets.QHBoxLayout()
        self.status = QtWidgets.QLabel("拖入本地文件或点击浏览，查看选中结果。", self)
        self.status.setWordWrap(True)
        row.addWidget(self.status, 1)
        clear = Button("清空", self)
        clear.clicked.connect(self.clear)
        row.addWidget(clear)
        root.addLayout(row)
        self.result = TextEdit(self)
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("选择结果")
        self.result.setMinimumHeight(70)
        self.result.setMaximumHeight(100)
        root.addWidget(self.result)
        self._refresh_theme()
        theme.subscribe(self, self._refresh_theme)

    def _selected(self, paths):
        self.result.setPlainText("\n".join(paths))
        self.status.setText(f"已选择 {len(paths)} 项。文件夹原样返回路径。")

    def _rejected(self, paths):
        reasons = {"extension": "文件类型不支持", "type": "请选择对应类型", "missing": "路径不存在",
                   "duplicate": "重复项目", "multiple": "仅接受一项", "invalid": "路径无效"}
        summary = "；".join(f"{QtCore.QFileInfo(path).fileName() or path}：{reasons.get(reason, reason)}" for path, reason in paths[:3])
        self.status.setText(f"有 {len(paths)} 项未接收。{summary}")

    def _error(self, error):
        self.status.setText("检查失败：" + error)

    def clear(self):
        self.file_drop.clear()
        self.folder_drop.clear()
        self.result.clear()
        self.status.setText("拖入本地文件或点击浏览，查看选中结果。")

    def _refresh_theme(self):
        tokens = theme.tokens
        for label in self.findChildren(QtWidgets.QLabel):
            if label.parentWidget() is self:
                label.setFont(ui_font(14))
                label.setStyleSheet(f"color: {tokens.text}; background: transparent;")
        for label in self.findChildren(QtWidgets.QLabel, "dropSectionTitle"):
            label.setFont(ui_font(14))
            font = label.font()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            label.setFont(font)


class DropDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("dropDemo")
        self.setWindowTitle("FluentPy · 拖放文件与文件夹")
        self.resize(880, 650)
        self.setMinimumSize(440, 620)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(20)
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("拖放文件与文件夹", self)
        header.addWidget(title, 1)
        header.addWidget(QtWidgets.QLabel("深色", self))
        toggle = ToggleSwitch(self)
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda value: theme.set_mode("dark" if value else "light"))
        header.addWidget(toggle)
        root.addLayout(header)
        self.examples = DropExamples(self)
        root.addWidget(self.examples)
        root.addStretch()
        self._refresh_theme()
        theme.subscribe(self, self._refresh_theme)

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(f"QWidget#dropDemo {{ background: {theme.tokens.background}; }}")
        for label in self.findChildren(QtWidgets.QLabel):
            if label.parentWidget() is self:
                label.setStyleSheet(f"color: {theme.tokens.text}; background: transparent;")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = DropDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    def capture():
        app.processEvents()
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(args.screenshot.resolve())):
            raise RuntimeError("Unable to save drop preview")
        if args.quit_after_screenshot:
            app.quit()
    if args.screenshot:
        QtCore.QTimer.singleShot(250, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
