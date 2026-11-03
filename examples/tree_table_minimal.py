"""Use the installed library directly, without any workbench modules."""

import sys

from fluentpy import (
    FluentIcon,
    TreeCell,
    TreeColumn,
    TreeTableWidget,
    fluent_icon,
)
from fluentpy.qt import QtWidgets


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget()
    window.setWindowTitle("独立使用树形列表")
    window.resize(820, 560)
    layout = QtWidgets.QVBoxLayout(window)
    tree = TreeTableWidget(
        [
            TreeColumn("name", "名称", width=260, stretch=True),
            TreeColumn("state", "状态"),
            TreeColumn("progress", "进度", kind="progress", formatter=lambda v: f"{v:.0f}%"),
        ],
        window,
    )
    project = tree.append_item({"name": "示例项目"}, key="project", group=True)
    tree.append_item(
        {
            "name": TreeCell("准备资源", icon=FluentIcon.FOLDER),
            "state": TreeCell("", icon=fluent_icon(FluentIcon.LEAF), tooltip="效率模式"),
            "progress": 42.0,
        },
        parent=project,
        key="download",
    )
    tree.expandAll()
    layout.addWidget(tree)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
