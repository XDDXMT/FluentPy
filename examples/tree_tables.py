"""One tree-list playground with metrics, tasks and an external resource model."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from component_playground import PlaygroundWindow

from fluentpy import (
    Button,
    CheckBox,
    ComboBox,
    FluentIcon,
    SearchLineEdit,
    TreeCell,
    TreeColumn,
    TreeFilterProxyModel,
    TreeFlattenProxyModel,
    TreeRole,
    TreeTableView,
    TreeTableWidget,
    fluent_icon,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font

RIGHT = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter


def percent(value):
    return f"{value:.1f}%"


def megabytes(value):
    return f"{value:,.1f} MB"


class TreeTableExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick = 0
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(12)
        row = QtWidgets.QHBoxLayout()
        self.scene = ComboBox()
        self.scene.addItems(["应用与资源", "项目与任务", "文件资源 · Qt 模型"])
        self.scene.setAccessibleName("树形列表示例场景")
        self.search = SearchLineEdit("搜索各列与副标题")
        self.mode = ComboBox()
        self.mode.addItems(["层级", "平铺"])
        self.mode.setMaximumWidth(100)
        self.mode.setAccessibleName("层级或平铺显示")
        row.addWidget(self.scene)
        row.addWidget(self.mode)
        row.addWidget(self.search, 1)
        self.body.addLayout(row)
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setMinimumHeight(370)
        self.stack.setFixedHeight(430)
        self.metrics = self._metrics()
        self.tasks = self._tasks()
        self.resources = self._resources()
        self.trees = (self.metrics, self.tasks, self.resources)
        for tree in self.trees:
            if isinstance(tree, TreeTableWidget):
                tree.set_flat_sorting_enabled(True)
                tree.sortModeChanged.connect(lambda mode, view=tree: self._mode_changed(view, mode))
            tree.setAccessibleName("可展开的多列数据列表")
            tree.set_empty_text("没有匹配项，试试清空搜索。")
            tree.cellActionTriggered.connect(self._activate)
            tree.contextMenuAboutToShow.connect(self._extend_menu)
            self.stack.addWidget(tree)
            tree.expandAll()
        self.body.addWidget(self.stack)
        row = QtWidgets.QHBoxLayout()
        self.density = ComboBox()
        self.density.addItems(["紧凑", "舒适"])
        self.density.setAccessibleName("列表行密度")
        self.live = CheckBox("实时演示")
        self.step = Button("更新一批")
        self.copy = Button("复制选中")
        row.addWidget(self.density)
        row.addWidget(self.live)
        row.addStretch()
        row.addWidget(self.step)
        row.addWidget(self.copy)
        self.body.addLayout(row)
        self.result = QtWidgets.QLabel(
            "资源数值为演示数据。右键表头选择列；拖动表头可调整顺序与宽度。"
        )
        self.result.setWordWrap(True)
        self.result.setForegroundRole(QtGui.QPalette.ColorRole.PlaceholderText)
        self.body.addWidget(self.result)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(900)
        self.timer.timeout.connect(self.update_batch)
        self.scene.currentIndexChanged.connect(self._change_scene)
        self.mode.currentIndexChanged.connect(self._change_mode)
        self.search.textChanged.connect(self._filter)
        self.density.currentIndexChanged.connect(self._density)
        self.live.toggled.connect(self._live_changed)
        self.step.clicked.connect(self.update_batch)
        self.copy.clicked.connect(lambda: self.current_tree().copy_selection(include_headers=True))
        self._density(0)

    def current_tree(self):
        return self.trees[self.stack.currentIndex()]

    def _metrics(self):
        columns = [
            TreeColumn("name", "名称", width=230, minimum_width=120, stretch=True),
            TreeColumn("state", "状态", width=120),
            TreeColumn(
                "cpu",
                "CPU",
                width=73,
                minimum_width=64,
                alignment=RIGHT,
                heat=True,
                formatter=lambda v: f"{v:.1f}".rstrip("0").rstrip(".") + "%",
            ),
            TreeColumn(
                "memory",
                "内存",
                width=73,
                minimum_width=64,
                alignment=RIGHT,
                heat=True,
                maximum=4096,
                formatter=megabytes,
            ),
            TreeColumn(
                "disk",
                "磁盘",
                width=73,
                minimum_width=64,
                heat=True,
                alignment=RIGHT,
                formatter=lambda value: f"{value:g} MB/秒",
            ),
            TreeColumn(
                "network",
                "网络",
                width=73,
                minimum_width=64,
                alignment=RIGHT,
                heat=True,
                formatter=lambda value: f"{value:g} Mbps",
            ),
            TreeColumn(
                "gpu",
                "GPU",
                width=73,
                minimum_width=64,
                heat=True,
                alignment=RIGHT,
                formatter=lambda value: f"{value:g}%",
            ),
        ]
        tree = TreeTableWidget(columns)
        tree.setUniformRowHeights(True)
        tree.set_visual_style("windows")
        tree.setFont(ui_font(13))
        tree.set_column_separators(True)
        tree.set_header_summary("cpu", "15%")
        tree.set_header_summary("memory", "75%")
        tree.set_header_summary("network", "0%")
        tree.set_header_summary("disk", "0%")
        tree.set_header_summary("gpu", "12%")
        group = tree.append_item({"name": "应用"}, key="apps", group=True)
        for number, (name, icon, cpu, memory) in enumerate(
            [
                ("FluentPy 工作台", FluentIcon.DESKTOP, 3.2, 182.5),
                ("浏览器", FluentIcon.GLOBE, 14.5, 1860.4),
                ("代码编辑器", FluentIcon.CODE, 6.8, 733.0),
                ("音乐播放器", FluentIcon.MUSIC_NOTE_2, 0.8, 168.1),
            ]
        ):
            item = tree.append_item(
                {
                    "name": TreeCell(f"{name} (3)", icon=icon),
                    "state": TreeCell("", icon=fluent_icon(FluentIcon.LEAF), tooltip="效率模式")
                    if number % 2
                    else "",
                    "cpu": cpu,
                    "memory": memory,
                    "network": number * 0.7,
                    "disk": 0.1 if number % 2 == 0 else 0.0,
                    "gpu": number * 0.3,
                },
                parent=group,
                key=f"app-{number}",
            )
            for child in range(2):
                tree.append_item(
                    [f"{name} · 子任务 {child + 1}", "", cpu / 3, memory / 3, 0.0, 0.0, 0.0],
                    parent=item,
                )
        return tree

    def _tasks(self):
        tree = TreeTableWidget(
            [
                TreeColumn("name", "项目 / 任务", width=290, stretch=True),
                TreeColumn("owner", "负责人", width=95, editable=True),
                TreeColumn("state", "状态", width=105, kind="badge"),
                TreeColumn(
                    "progress",
                    "进度",
                    width=125,
                    kind="progress",
                    alignment=RIGHT,
                    formatter=percent,
                    editable=True,
                ),
                TreeColumn("action", "操作", width=90, kind="action"),
            ]
        )
        tree.set_header_summary("name", "2 个项目")
        for number, title in enumerate(("FluentPy 组件库", "示例资源包")):
            project = tree.append_item(
                {"name": TreeCell(title, icon=FluentIcon.FOLDER)},
                key=f"project-{number}",
                group=True,
            )
            for child, title in enumerate(("整理界面与交互", "准备文档和示例", "检查安装与运行")):
                tree.append_item(
                    {
                        "name": TreeCell(
                            title,
                            subtitle="勾选名称前的方框记录完成状态",
                            check_state=QtCore.Qt.CheckState.Unchecked,
                        ),
                        "owner": "开发者",
                        "state": "进行中",
                        "progress": 18.0 + child * 24,
                        "action": "暂停",
                    },
                    parent=project,
                    key=f"task-{number}-{child}",
                )
        return tree

    def _resources(self):
        columns = [
            TreeColumn("name", "资源名称", width=300, stretch=True),
            TreeColumn("type", "类型", width=115, kind="badge"),
            TreeColumn(
                "size",
                "大小",
                width=135,
                alignment=RIGHT,
                formatter=lambda value: f"{value / 1024:,.1f} KB",
            ),
            TreeColumn("action", "操作", width=90, kind="action"),
        ]
        view = TreeTableView(columns)
        self.resource_model = QtGui.QStandardItemModel(0, 4, self)
        self.resource_model.setHorizontalHeaderLabels([column.title for column in columns])
        self.resource_proxy = TreeFilterProxyModel(self)
        self.resource_flat = TreeFlattenProxyModel(self)
        self._resources_flat = False
        self._resource_switching = False
        self.resource_proxy.setSourceModel(self.resource_model)
        view.setModel(self.resource_proxy)
        view.header().sortIndicatorChanged.connect(self._resource_sort_changed)
        for folder, rows in (
            ("界面资源", [("启动图.svg", "矢量图", 16240), ("窗口预览.png", "图片", 492830)]),
            ("项目文件", [("使用说明.md", "文档", 8192), ("主题配置.json", "配置", 1024)]),
        ):
            item = QtGui.QStandardItem(folder)
            item.setIcon(fluent_icon(FluentIcon.FOLDER))
            self.resource_model.appendRow(
                [item, QtGui.QStandardItem(), QtGui.QStandardItem(), QtGui.QStandardItem()]
            )
            for name, kind, size in rows:
                cells = [
                    QtGui.QStandardItem(name),
                    QtGui.QStandardItem(kind),
                    QtGui.QStandardItem(),
                    QtGui.QStandardItem("查看"),
                ]
                cells[0].setIcon(fluent_icon(FluentIcon.DOCUMENT))
                cells[0].setData("使用调用方的 QStandardItemModel", TreeRole.Subtitle)
                cells[2].setData(size, QtCore.Qt.ItemDataRole.DisplayRole)
                for cell in cells:
                    cell.setEditable(False)
                item.appendRow(cells)
        return view

    def _density(self, index):
        for tree in self.trees:
            tree.set_row_height((28 if tree is self.metrics else 32) if index == 0 else 44)

    def _change_scene(self, index):
        self.stack.setCurrentIndex(index)
        tree = self.current_tree()
        mode = (
            tree.sort_mode()
            if isinstance(tree, TreeTableWidget)
            else "flat"
            if self._resources_flat
            else "hierarchical"
        )
        self._mode_changed(tree, mode)
        self._filter(self.search.text())

    def _mode_changed(self, tree, mode):
        if tree is self.current_tree():
            previous = self.mode.blockSignals(True)
            self.mode.setCurrentIndex(1 if mode == "flat" else 0)
            self.mode.blockSignals(previous)

    def _change_mode(self, index):
        tree = self.current_tree()
        mode = "flat" if index else "hierarchical"
        if isinstance(tree, TreeTableWidget):
            tree.set_sort_mode(mode)
        else:
            self._set_resource_mode(bool(index))

    def _set_resource_mode(self, flat):
        if self._resources_flat == flat:
            return
        tree = self.resources
        state = tree.header().saveState()
        self._resource_switching = True
        try:
            self._resources_flat = flat
            if flat:
                self.resource_flat.setSourceModel(self.resource_model)
                self.resource_proxy.setSourceModel(self.resource_flat)
            else:
                self.resource_proxy.setSourceModel(self.resource_model)
                self.resource_flat.setSourceModel(None)
            tree.setRootIsDecorated(not flat)
            tree.header().restoreState(state)
            if not flat:
                tree.sortByColumn(-1, QtCore.Qt.SortOrder.AscendingOrder)
                tree.expandAll()
        finally:
            self._resource_switching = False

    def _resource_sort_changed(self, column, order):
        if column >= 0 and not self._resources_flat and not self._resource_switching:
            self._set_resource_mode(True)
            self._mode_changed(self.resources, "flat")

    def _filter(self, text):
        tree = self.current_tree()
        if isinstance(tree, TreeTableWidget):
            tree.set_filter_text(text)
        else:
            self.resource_proxy.set_filter_text(text)
            tree.expandAll()

    def _activate(self, index):
        tree = self.current_tree()
        name = index.siblingAtColumn(0).data()
        if tree is self.tasks:
            source = tree.source_index(index)
            first = tree.source_model.itemFromIndex(source.siblingAtColumn(0))
            paused = index.data() == "暂停"
            tree.update_item(
                first,
                {"state": "已暂停" if paused else "进行中", "action": "继续" if paused else "暂停"},
            )
        self.result.setText(f"已触发「{name}」的单元格操作；业务处理由使用者连接信号。")

    def _extend_menu(self, menu, index):
        if index.isValid():
            name = index.siblingAtColumn(0).data()
            menu.addSeparator()
            menu.addAction("查看条目信息").triggered.connect(
                lambda: self.result.setText(f"当前条目：{name}；菜单可按条目和多选状态扩展。")
            )

    def update_batch(self):
        self._tick += 1
        if self.current_tree() is self.metrics:
            with self.metrics.batch_update():
                for number, value in enumerate((3.2, 14.5, 6.8, 0.8)):
                    self.metrics.update_item(
                        f"app-{number}", {"cpu": value + (self._tick % 7) * 0.4}
                    )
            self.metrics.set_header_summary("cpu", f"{15 + self._tick % 7}%")
        elif self.current_tree() is self.tasks:
            with self.tasks.batch_update():
                for project in range(2):
                    for child in range(3):
                        item = self.tasks.item(f"task-{project}-{child}")
                        if item.parent().child(item.row(), 4).text() == "继续":
                            continue
                        progress = (
                            item.parent()
                            .child(item.row(), 3)
                            .data(QtCore.Qt.ItemDataRole.DisplayRole)
                        )
                        self.tasks.update_item(item, {"progress": min(100.0, progress + 1.0)})
        self.result.setText("已局部更新；选中项、展开状态和滚动位置继续保留。")

    def _live_changed(self, enabled):
        if enabled and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._live_changed(self.live.isChecked())


class TreeTableDemo(PlaygroundWindow):
    def __init__(self, dark=False):
        super().__init__("树形数据列表", TreeTableExamples, dark=dark)
        self.resize(1050, 820)
        self.setMinimumSize(740, 720)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    window = TreeTableDemo(args.dark)
    window.show()
    sys.exit(app.exec())
