"""A real multipage FluentWindow with native Qt content and retained state."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fluentpy import (
    AccentButton,
    Button,
    CheckBox,
    ComboBox,
    ExpandableCardWidget,
    FluentIcon,
    FluentScrollBar,
    FluentWindow,
    HeaderCardWidget,
    LineEdit,
    SearchLineEdit,
    SpinBox,
    TextEdit,
    ToggleSwitch,
    fluent_icon,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets

MODES = ("auto", "expanded", "compact", "top")
MODE_LABELS = ("随窗口宽度调整", "展开侧栏", "紧凑侧栏", "顶部导航")


def _caption(text, *, muted=False, heading=False):
    label = QtWidgets.QLabel(text)
    label.setWordWrap(True)
    if muted:
        label.setObjectName("muted")
    if heading:
        label.setStyleSheet("font-size:25px;font-weight:600;")
    return label


def _form_row(layout, title, control):
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(16)
    label = _caption(title)
    label.setMinimumWidth(105)
    row.addWidget(label)
    row.addWidget(control, 1)
    layout.addLayout(row)


class WindowDemo(FluentWindow):
    """Use one window type for responsive rail and top navigation layouts."""

    def __init__(
        self, dark=None, *, mode="auto", title_bar=True, tinted=False, backdrop=True, parent=None
    ):
        if dark is not None:
            theme.set_mode("dark" if dark else "light")
        super().__init__("FluentPy · 项目工作区", parent)
        self.set_theme_transition_enabled(True)
        self.setWindowFlag(QtCore.Qt.WindowType.Window, True)
        self.setWindowIcon(
            QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
        )
        self.resize(1040, 720)
        self.setMinimumSize(720, 560)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self._events = []
        self._pages = {}
        self._syncing = False
        self._title_search = None
        self.set_navigation_width(224)

        for route, text, icon, builder, position in (
            ("overview", "项目概览", FluentIcon.HOME, self._overview_page, "header"),
            ("documents", "项目说明", FluentIcon.DOCUMENT, self._documents_page, "scroll"),
            ("activity", "活动记录", FluentIcon.CLOCK, self._activity_page, "scroll"),
            ("settings", "设置", FluentIcon.SETTINGS, self._settings_page, "bottom"),
        ):
            page = builder()
            self._pages[route] = page
            self.add_page(page, text, fluent_icon(icon), route=route, position=position)

        self.navigation_view().sidebar.set_header_widget(self._sidebar_search())
        self.currentChanged.connect(self._page_changed)
        self.historyChanged.connect(self._history_changed)
        self.mode_combo.setCurrentIndex(MODES.index(mode))
        self.title_bar_check.setChecked(title_bar)
        self.background_check.setChecked(tinted)
        self.backdrop_check.setChecked(backdrop and not tinted)
        self.set_navigation_mode(mode)
        self._set_title_bar(title_bar)
        self._set_tinted(tinted)
        self._set_backdrop(backdrop and not tinted)
        self._page_changed(self.current_route())
        self._append_activity("项目工作区已打开。")
        theme.subscribe(self, self._sync_theme)
        self._sync_theme()

    def _page(self, title, detail):
        area = QtWidgets.QScrollArea()
        area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setVerticalScrollBar(FluentScrollBar(parent=area))
        area.setStyleSheet("QScrollArea {border:none;}")
        area.viewport().setAutoFillBackground(True)
        area.viewport().setBackgroundRole(QtGui.QPalette.ColorRole.Window)
        page = QtWidgets.QWidget()
        area.setWidget(page)
        page.setAutoFillBackground(True)
        page.setBackgroundRole(QtGui.QPalette.ColorRole.Window)
        body = QtWidgets.QVBoxLayout(page)
        body.setContentsMargins(28, 24, 28, 24)
        body.setSpacing(18)
        body.addWidget(_caption(title, heading=True))
        body.addWidget(_caption(detail, muted=True))
        return area, body

    def _overview_page(self):
        page, body = self._page(
            "项目工作区", "从任务到文档，在同一个窗口中完成。切换页面或导航布局时，编辑内容会保留。"
        )
        summary = HeaderCardWidget("当前项目")
        row = QtWidgets.QHBoxLayout()
        name = _caption("FluentPy\n原生 Qt 界面组件库")
        name.setStyleSheet("font-size:18px;font-weight:600;")
        row.addWidget(name, 1)
        row.addWidget(_caption("0.6.9\nMIT 开源协议", muted=True))
        summary.body_layout.addLayout(row)
        body.addWidget(summary)

        tasks = HeaderCardWidget("今天的安排")
        self.task_checks = []
        for title, detail, checked in (
            ("整理项目说明", "补充安装步骤与使用记录", False),
            ("检查窗口布局", "缩小窗口，体验紧凑导航", False),
            ("确认开源协议", "项目使用 MIT 协议", True),
        ):
            line = QtWidgets.QHBoxLayout()
            check = CheckBox(title)
            check.setChecked(checked)
            check.toggled.connect(
                lambda state, name=title: self._append_activity(
                    f"{name}：" + ("已完成" if state else "待处理")
                )
            )
            self.task_checks.append(check)
            line.addWidget(check, 1)
            line.addWidget(_caption(detail, muted=True), 1)
            tasks.body_layout.addLayout(line)
        body.addWidget(tasks)

        commands = QtWidgets.QHBoxLayout()
        edit = AccentButton("编辑项目说明")
        edit.clicked.connect(lambda: self.switch_to("documents"))
        activity = Button("查看活动")
        activity.clicked.connect(lambda: self.switch_to("activity"))
        commands.addWidget(edit)
        commands.addWidget(activity)
        commands.addStretch()
        body.addLayout(commands)
        self.route_status = _caption("", muted=True)
        body.addWidget(self.route_status)
        body.addStretch()
        return page

    def _documents_page(self):
        page, body = self._page(
            "项目说明", "这是可编辑的真实页面。输入一些文字，再切换页面、折叠侧栏或使用返回按钮。"
        )
        card = HeaderCardWidget("说明文档")
        self.document_name = LineEdit("文档标题")
        self.document_name.setText("FluentPy 使用记录")
        card.body_layout.addWidget(self.document_name)
        self.document_editor = TextEdit()
        self.document_editor.setMinimumHeight(240)
        self.document_editor.setPlainText(
            "项目目标\n\n使用 FluentPy 构建清晰、易用的桌面界面。\n\n待办事项\n1. 阅读组件文档\n2. 调整窗口导航\n3. 完成第一个页面\n\n这里的文字可以直接编辑，切换页面后仍会保留。"
        )
        card.body_layout.addWidget(self.document_editor)
        row = QtWidgets.QHBoxLayout()
        self.save_button = AccentButton("记录保存")
        self.save_button.clicked.connect(self._save_document)
        row.addWidget(self.save_button)
        self.document_status = _caption("修改仅保存在本次演示窗口中。", muted=True)
        row.addWidget(self.document_status, 1)
        card.body_layout.addLayout(row)
        body.addWidget(card)
        body.addStretch()
        return page

    def _activity_page(self):
        page, body = self._page(
            "活动记录", "这里记录实际操作。标题栏的返回与前进按页面访问历史工作，不会清空页面。"
        )
        card = HeaderCardWidget("本次会话")
        self.activity_log = TextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMinimumHeight(300)
        card.body_layout.addWidget(self.activity_log)
        row = QtWidgets.QHBoxLayout()
        back = Button("返回上一页")
        forward = Button("前进")
        back.clicked.connect(self.go_back)
        forward.clicked.connect(self.go_forward)
        self.history_back = back
        self.history_forward = forward
        row.addWidget(back)
        row.addWidget(forward)
        row.addStretch()
        card.body_layout.addLayout(row)
        body.addWidget(card)
        body.addStretch()
        return page

    def _settings_page(self):
        page, body = self._page(
            "设置", "调整后立即生效。侧栏模式使用同一组页面，设置入口固定在底部。"
        )
        appearance = HeaderCardWidget("窗口外观")
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(MODE_LABELS)
        self.mode_combo.currentIndexChanged.connect(lambda index: self._set_mode(MODES[index]))
        _form_row(appearance.body_layout, "导航布局", self.mode_combo)
        self.dark_toggle = ToggleSwitch()
        self.dark_toggle.setChecked(theme.mode.value == "dark")
        self.dark_toggle.toggled.connect(
            lambda checked: theme.set_mode("dark" if checked else "light")
        )
        _form_row(appearance.body_layout, "深色模式", self.dark_toggle)
        self.title_bar_check = CheckBox("使用可扩展标题栏")
        self.title_bar_check.toggled.connect(self._set_title_bar)
        appearance.body_layout.addWidget(self.title_bar_check)
        self.background_check = CheckBox("使用浅灰蓝 / 深蓝背景")
        self.background_check.toggled.connect(self._set_tinted)
        appearance.body_layout.addWidget(self.background_check)
        body.addWidget(appearance)

        advanced = ExpandableCardWidget("更多设置")
        self.window_name = LineEdit("窗口标题")
        self.window_name.setText(self.windowTitle())
        self.window_name.textChanged.connect(self.setWindowTitle)
        _form_row(advanced.body_layout, "窗口标题", self.window_name)
        self.sidebar_width = SpinBox()
        self.sidebar_width.setRange(180, 300)
        self.sidebar_width.setValue(224)
        self.sidebar_width.valueChanged.connect(self.set_navigation_width)
        _form_row(advanced.body_layout, "展开宽度", self.sidebar_width)
        self.search_check = CheckBox("在标题栏中显示搜索框")
        self.search_check.setChecked(True)
        self.search_check.toggled.connect(self._sync_title_search)
        advanced.body_layout.addWidget(self.search_check)
        self.backdrop_check = CheckBox("云母效果（Windows 11）")
        self.backdrop_check.setToolTip("让标题栏与导航使用系统材质；不支持时使用普通背景。")
        self.backdrop_check.toggled.connect(self._set_backdrop)
        advanced.body_layout.addWidget(self.backdrop_check)
        advanced.body_layout.addWidget(_caption("页面内容保持清晰的普通背景。", muted=True))
        body.addWidget(advanced)
        body.addStretch()
        return page

    def _sidebar_search(self):
        search = SearchLineEdit("搜索页面")
        search.setMinimumWidth(0)
        search.textChanged.connect(self.navigation_view().sidebar.set_filter_text)
        search.returnPressed.connect(lambda: self._open_search(search.text()))
        return search

    def _open_search(self, text):
        for route, title in (
            ("overview", "项目概览"),
            ("documents", "项目说明"),
            ("activity", "活动记录"),
            ("settings", "设置"),
        ):
            if text.strip() and (text.casefold() in title.casefold() or text.casefold() in route):
                self.navigation_view().sidebar.set_filter_text("")
                self.switch_to(route)
                return

    def _set_mode(self, mode):
        self.set_navigation_mode(mode)
        self._append_activity("导航布局：" + MODE_LABELS[MODES.index(mode)])
        self._history_changed()

    def _set_title_bar(self, enabled):
        self.set_title_bar_enabled(enabled)
        bar = self.title_bar()
        if enabled and bar is not None and not bar.property("demoSearchInstalled"):
            search = SearchLineEdit("搜索页面")
            search.setFixedWidth(220)
            search.setToolTip("输入页面名称，按 Enter 打开")
            search.returnPressed.connect(lambda: self._open_search(search.text()))
            bar.content_layout.addWidget(search, 1)
            bar.setProperty("demoSearchInstalled", True)
            self._title_search = search
        self._sync_title_search()

    def _sync_title_search(self, *_args):
        if self._title_search is not None:
            self._title_search.setVisible(self.search_check.isChecked())

    def _set_tinted(self, enabled):
        if enabled:
            with QtCore.QSignalBlocker(self.backdrop_check):
                self.backdrop_check.setChecked(False)
            self.set_backdrop_enabled(False)
            self.set_background_colors("#eef3f8", "#202934")
        else:
            self.clear_background_colors()

    def _set_backdrop(self, enabled):
        if enabled:
            with QtCore.QSignalBlocker(self.background_check):
                self.background_check.setChecked(False)
            self.clear_background_colors()
        self.set_backdrop_enabled(enabled)

    def _save_document(self):
        self.document_status.setText("已记录于 " + QtCore.QTime.currentTime().toString("HH:mm:ss"))
        self._append_activity("已记录文档：" + (self.document_name.text() or "未命名文档"))

    def _append_activity(self, text):
        self._events.append(QtCore.QTime.currentTime().toString("HH:mm:ss") + "  " + text)
        if hasattr(self, "activity_log"):
            self.activity_log.setPlainText("\n".join(self._events))
            self.activity_log.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _page_changed(self, route):
        titles = {
            "overview": "项目概览",
            "documents": "项目说明",
            "activity": "活动记录",
            "settings": "设置",
        }
        self.route_status.setText(
            "当前页面：" + titles.get(route, route) + "   ·   缩小窗口可体验自动紧凑导航"
        )
        self._append_activity("打开页面：" + titles.get(route, route))
        self._history_changed()

    def _history_changed(self):
        self.history_back.setEnabled(self.can_go_back())
        self.history_forward.setEnabled(self.can_go_forward())

    def _sync_theme(self):
        blocker = QtCore.QSignalBlocker(self.dark_toggle)
        self.dark_toggle.setChecked(theme.mode.value == "dark")
        del blocker


class WindowExamples(QtWidgets.QWidget):
    """Small workbench controls that open one actual, configurable window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.demo_window = None
        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(MODE_LABELS)
        _form_row(body, "导航布局", self.mode_combo)
        self.title_bar_check = CheckBox("使用可扩展标题栏")
        self.title_bar_check.setChecked(True)
        body.addWidget(self.title_bar_check)
        options = ExpandableCardWidget("更多外观设置")
        self.background_check = CheckBox("使用浅灰蓝 / 深蓝背景")
        self.backdrop_check = CheckBox("云母效果（Windows 11）")
        self.backdrop_check.setToolTip("让标题栏与导航使用系统材质；不支持时使用普通背景。")
        self.backdrop_check.setChecked(True)
        self.background_check.toggled.connect(
            lambda checked: self.backdrop_check.setChecked(False) if checked else None
        )
        self.backdrop_check.toggled.connect(
            lambda checked: self.background_check.setChecked(False) if checked else None
        )
        options.body_layout.addWidget(self.background_check)
        options.body_layout.addWidget(self.backdrop_check)
        body.addWidget(options)
        row = QtWidgets.QHBoxLayout()
        self.open_button = AccentButton("打开实际窗口")
        self.open_button.clicked.connect(self.open_window)
        row.addWidget(self.open_button)
        row.addWidget(_caption("4 个页面 · 页面历史 · 底部设置 · 标题栏搜索", muted=True), 1)
        body.addLayout(row)
        self.result = _caption("选择布局后打开；再次点击可应用设置并返回已打开的窗口。", muted=True)
        body.addWidget(self.result)

    def open_window(self):
        mode = MODES[self.mode_combo.currentIndex()]
        if self.demo_window is None:
            self.demo_window = WindowDemo(
                mode=mode,
                title_bar=self.title_bar_check.isChecked(),
                parent=self.window(),
                tinted=self.background_check.isChecked(),
                backdrop=self.backdrop_check.isChecked(),
            )
            self.demo_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
            self.demo_window.destroyed.connect(self._window_destroyed)
        else:
            window = self.demo_window
            window.mode_combo.setCurrentIndex(MODES.index(mode))
            window.title_bar_check.setChecked(self.title_bar_check.isChecked())
            window.background_check.setChecked(self.background_check.isChecked())
            window.backdrop_check.setChecked(self.backdrop_check.isChecked())
        self.demo_window.show()
        self.demo_window.raise_()
        self.demo_window.activateWindow()
        self.result.setText("窗口已打开：可编辑项目说明、切换布局，并在设置页调整外观。")
        return self.demo_window

    def _window_destroyed(self):
        self.demo_window = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--mode", choices=MODES, default="auto")
    parser.add_argument("--native-title-bar", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    demo = WindowDemo(dark=args.dark, mode=args.mode, title_bar=not args.native_title_bar)
    demo.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
