"""Selectable language highlighting. Run: python examples/code_editor.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fluentpy import Button, CodeEdit, ComboBox, ToggleSwitch, theme  # noqa: E402
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

LANGUAGE_LABELS = {
    "json": "JSON",
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c": "C",
    "cpp": "C++",
    "csharp": "C#",
    "go": "Go",
    "rust": "Rust",
    "sql": "SQL",
    "html": "HTML",
    "xml": "XML",
    "css": "CSS",
    "yaml": "YAML",
    "shell": "Shell",
    "plain": "纯文本",
}
LANGUAGE_SAMPLES = {
    "json": SAMPLE,
    "python": 'from fluentpy import CodeEdit\n\nclass Example:\n    """选择语言，保留原始代码。"""\n    def greet(self, name: str = "FluentPy"):\n        return f"Hello, {name}!"  # 😀\n',
    "java": 'public class Example {\n    public static void main(String[] args) {\n        String name = "FluentPy";\n        System.out.println("Hello, " + name);\n    }\n}\n',
    "javascript": 'const name = "FluentPy";\nasync function load() {\n    const response = await fetch("/api/example");\n    return await response.json();\n}\n',
    "typescript": 'interface User {\n    name: string;\n    enabled: boolean;\n}\nconst user: User = { name: "FluentPy", enabled: true };\n',
    "c": '#include <stdio.h>\n\nint main(void) {\n    printf("Hello, FluentPy!\\n");\n    return 0;\n}\n',
    "cpp": '#include <string>\n#include <vector>\n\nint main() {\n    std::vector<std::string> names = {"FluentPy"};\n    return 0;\n}\n',
    "csharp": 'public class Example {\n    public string Name { get; set; } = "FluentPy";\n    public bool Enabled => true;\n}\n',
    "go": 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, FluentPy!")\n}\n',
    "rust": 'fn main() {\n    let name: &str = "FluentPy";\n    println!("Hello, {}!", name);\n}\n',
    "sql": "-- 查询已启用项目\nSELECT id, name\nFROM projects\nWHERE enabled = true\nORDER BY name;\n",
    "html": '<!-- FluentPy 示例 -->\n<section class="card">\n    <h1>Hello, FluentPy!</h1>\n    <button type="button">开始使用</button>\n</section>\n',
    "xml": '<?xml version="1.0"?>\n<project name="FluentPy">\n    <enabled>true</enabled>\n</project>\n',
    "css": ".card {\n    background: #ffffff;\n    color: #101010;\n    border-radius: 8px;\n}\n",
    "yaml": "project: FluentPy\nversion: 0.7.3\nenabled: true\nfeatures:\n  - code-editor\n  - native-widgets\n",
    "shell": '#!/bin/sh\nname="FluentPy"\nfor item in "$name"; do\n    echo "$item"\ndone\n',
    "plain": "纯文本模式保留内容、光标与撤销记录。\n选择其他语言只改变颜色渲染。\n",
}


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
        self.language_choice = ComboBox()
        self.language_choice.setAccessibleName("语法高亮语言")
        for language, title in LANGUAGE_LABELS.items():
            self.language_choice.addItem(title, language)
        self.language_choice.currentIndexChanged.connect(self._language_changed)
        footer.addWidget(self.language_choice)
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
        self.editor.set_code(LANGUAGE_SAMPLES[self.editor.language()])
        document = self.editor.text_edit.document()
        cursor = QtGui.QTextCursor(document.findBlockByNumber(min(4, document.blockCount() - 1)))
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
        self.position.setText(
            f"{LANGUAGE_LABELS[self.editor.language()]}  ·  {cursor.blockNumber() + 1}:{cursor.positionInBlock() + 1}"
        )

    def _language_changed(self, index):
        self.editor.set_language(self.language_choice.currentData())
        self._update_position()

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
