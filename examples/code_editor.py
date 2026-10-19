"""Standalone editable JSON demo. Run: python examples/code_editor.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fluentpy import Button, CodeEdit, ToggleSwitch, theme  # noqa: E402
from fluentpy.qt import QtCore, QtGui, QtWidgets  # noqa: E402
from fluentpy.theme.fonts import ui_font  # noqa: E402

SAMPLE = json.dumps(
    {
        "TotalCount": 2,
        "RequestId": "27A90792-2B98-5435-8589-A2AF90E6C374",
        "PageSize": 500,
        "PageNumber": 1,
        "Records": [
            {
                "RecordName": name,
                "Comment": "",
                "SiteId": 594022096258736,
                "SiteName": "example.com",
                "RecordSourceType": "Domain",
                "CreateTime": "2026-01-08T12:24:57Z",
                "Data": {"Value": "example.com"},
                "Ttl": 1,
                "Proxied": True,
                "RecordType": "CNAME",
                "UpdateTime": "2026-01-08T12:24:57Z",
                "BizName": "web",
                "HostPolicy": "follow_hostname",
                "RecordId": 4294374396209216 + index,
                "AuthConf": {},
                "RecordCname": "",
            }
            for index, name in enumerate(("app.example.com", "chat.example.com"))
        ],
    },
    ensure_ascii=False,
    indent=2,
)


class CodeEditorDemo(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FluentPy · 代码编辑器 Demo")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        self.editor = CodeEdit()
        self.editor.set_indent_size(2)
        layout.addWidget(self.editor, 1)

        self.position = QtWidgets.QLabel()
        layout.addWidget(self.position)
        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(10)
        self.reset_button = Button("还原示例")
        self.reset_button.clicked.connect(self.reset_sample)
        footer.addWidget(self.reset_button)
        footer.addStretch()
        footer.addWidget(QtWidgets.QLabel("深色"))
        self.dark_toggle = ToggleSwitch()
        self.dark_toggle.setChecked(theme.mode.value == "dark")
        self.dark_toggle.toggled.connect(
            lambda checked: theme.set_mode("dark" if checked else "light")
        )
        footer.addWidget(self.dark_toggle)
        layout.addLayout(footer)
        self.editor.text_edit.cursorPositionChanged.connect(self._update_position)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)
        self.reset_sample()
        self.adjustSize()

    def reset_sample(self) -> None:
        self.editor.set_code(SAMPLE)
        cursor = QtGui.QTextCursor(self.editor.text_edit.document().findBlockByNumber(4))
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
        self.editor.text_edit.setTextCursor(cursor)
        self.editor.setFocus()
        self._update_position()
        QtCore.QTimer.singleShot(0, self._scroll_to_start)

    def _scroll_to_start(self) -> None:
        self.editor.text_edit.verticalScrollBar().setValue(0)
        self.editor.text_edit.horizontalScrollBar().setValue(0)

    def _update_position(self) -> None:
        cursor = self.editor.text_edit.textCursor()
        self.position.setText(f"JSON  ·  {cursor.blockNumber() + 1}:{cursor.positionInBlock() + 1}")

    def _apply_theme(self) -> None:
        font = QtGui.QFont()
        font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI"])
        font.setPixelSize(14)
        self.reset_button.setFont(font)
        light = theme.mode.value == "light"
        background, text = ("#ffffff", "#697078") if light else ("#191919", "#a7a7a7")
        self.setStyleSheet(
            f"CodeEditorDemo {{ background: {background}; }}"
            f'QLabel {{ color: {text}; font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 12px; background: transparent; }}'
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="FluentPy code editor demo")
    parser.add_argument("--large", action="store_true", help="Open an 820 x 620 preview window")
    parser.add_argument("--dark", action="store_true", help="Start in dark mode")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    theme.set_mode("dark" if args.dark else "light")
    window = CodeEditorDemo()
    if args.large:
        window.resize(820, 620)
    window.show()
    QtCore.QTimer.singleShot(0, window.editor.setFocus)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
