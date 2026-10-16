"""FluentPy interactive showcase. Run ``python examples/showcase.py``."""

from __future__ import annotations

import argparse
from importlib import resources
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import (  # noqa: E402
    AccentButton, AnimatedStackedWidget, BreadcrumbBar, Button, CheckBox, CodeEdit, ComboBox,
    DoubleSpinBox, EditableComboBox, FluentIcon, FluentScrollBar, FluentWindow,
    FramelessDialog, IconButton, LineEdit, MaskedDialog, NavigationItem, NavigationView,
    NoteEvent, NoteTimeline, OutlinedButton, PasswordLineEdit, Pivot,
    ProgressBar, RadioButton, SearchLineEdit, SegmentedWidget, Slider,
    SpinBox, TabBar, TextButton, TextEdit, Toast, ToggleSwitch, fluent_icon, theme,
)
from fluentpy.backends.text import native_available  # noqa: E402
from fluentpy.qt import QtCore, QtGui, QtWidgets  # noqa: E402
from fluentpy.theme.fonts import ui_font  # noqa: E402

try:
    from fluentpy import DatePicker
except ImportError:
    DatePicker = None


SAMPLE = '''{
  "project": "FluentPy",
  "description": "一个可以直接操作的组件工作台",
  "theme": "follow your choice",
  "features": [
    "日期选择器",
    "导航与反馈",
    "C 后端 JSON 高亮"
  ],
  "records": [
    {"id": 1, "name": "组件体验", "enabled": true},
    {"id": 2, "name": "Unicode 中文 😀", "enabled": false}
  ],
  "license": "MIT"
}'''

PAGES = (
    ("overview", "概览", FluentIcon.HOME),
    ("inputs", "输入与日期", FluentIcon.CALENDAR_LTR),
    ("cards", "卡片与设置", FluentIcon.TABLE),
    ("feedback", "导航与反馈", FluentIcon.NAVIGATION),
    ("code", "代码与性能", FluentIcon.CODE),
    ("notes", "音符视图", FluentIcon.MUSIC_NOTE_2),
)

BRAND_ICON = resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")


def label(text: str = "", *, role: str = "", wrap: bool = False) -> QtWidgets.QLabel:
    widget = QtWidgets.QLabel(text)
    if role:
        widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def button_row(*widgets: QtWidgets.QWidget, stretch: bool = True) -> QtWidgets.QHBoxLayout:
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(8)
    for widget in widgets:
        row.addWidget(widget)
    if stretch:
        row.addStretch(1)
    return row


class Panel(QtWidgets.QFrame):
    """Quiet solid surface for the example's layout, using live theme tokens."""

    def __init__(self, title: str = "", description: str = "") -> None:
        super().__init__()
        self.setObjectName("showcasePanel")
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(20, 18, 20, 18)
        self.body.setSpacing(12)
        if title:
            self.body.addWidget(label(title, role="panelTitle"))
        if description:
            self.body.addWidget(label(description, role="muted", wrap=True))
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _apply_theme(self) -> None:
        tokens = theme.tokens
        self.setStyleSheet(
            f"QFrame#showcasePanel {{ background: {tokens.surface}; border: 1px solid {tokens.border}; border-radius: 7px; }}"
            f"QLabel#panelTitle {{ color: {tokens.text}; font-size: 16px; font-weight: 600; }}"
        )


class Showcase(FluentWindow):
    def __init__(self, *, dark: bool = False, page: str = "overview") -> None:
        theme.set_mode("dark" if dark else "light")
        super().__init__("FluentPy · 示例工作台")
        self.setWindowIcon(QtGui.QIcon(str(BRAND_ICON)))
        self.resize(1120, 780)
        self.setMinimumSize(900, 650)
        self._bookings: list[dict] = []
        self._extra_windows: list[QtWidgets.QWidget] = []
        self._route_buttons: dict[str, NavigationItem] = {}
        self._page_indexes: dict[str, int] = {}
        self._masked: MaskedDialog | None = None
        self._frameless: FramelessDialog | None = None
        self._active_toast: Toast | None = None
        self._note_timer = QtCore.QTimer(self)
        self._note_timer.setInterval(30)
        self._note_elapsed = QtCore.QElapsedTimer()
        self._note_start = 0.0
        self._note_timer.timeout.connect(self._advance_notes)

        layout = self.content_layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QtWidgets.QFrame()
        header.setObjectName("showcaseHeader")
        header_row = QtWidgets.QHBoxLayout(header)
        header_row.setContentsMargins(24, 15, 24, 15)
        header_row.setSpacing(12)
        brand = label(role="showcaseMark")
        brand.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        brand.setFixedSize(34, 34)
        brand.setPixmap(self.windowIcon().pixmap(QtCore.QSize(30, 34), self.devicePixelRatioF()))
        brand.setAccessibleName("FluentPy 主图标")
        self.brand_mark = brand
        header_row.addWidget(brand)
        header_row.addWidget(label("FluentPy", role="showcaseBrand"))
        header_row.addSpacing(4)
        header_row.addWidget(label("示例工作台", role="muted"))
        header_row.addStretch(1)
        header_row.addWidget(label("C 后端就绪" if native_available() else "Python 兼容模式", role="backendBadge"))
        header_row.addSpacing(12)
        self.theme_caption = label("深色" if dark else "浅色", role="muted")
        header_row.addWidget(self.theme_caption)
        self.theme_toggle = ToggleSwitch()
        self.theme_toggle.setChecked(dark)
        self.theme_toggle.setAccessibleName("切换深色模式")
        self.theme_toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        header_row.addWidget(self.theme_toggle)
        layout.addWidget(header)

        self.navigation = NavigationView(self)
        self.sidebar = self.navigation.sidebar
        self.sidebar.set_expanded_width(216)
        self.sidebar.set_expanded(True)
        self.stack = self.navigation.stack
        layout.addWidget(self.navigation, 1)

        footer = QtWidgets.QFrame()
        footer.setObjectName("showcaseFooter")
        footer_row = QtWidgets.QHBoxLayout(footer)
        footer_row.setContentsMargins(24, 9, 24, 9)
        self.activity = label("就绪，选择一个组件开始体验。", role="muted")
        footer_row.addWidget(self.activity, 1)
        footer_row.addWidget(label("FluentPy 0.1", role="railCaption"))
        layout.addWidget(footer)

        builders = {
            "overview": self._overview_page, "inputs": self._inputs_page,
            "cards": self._cards_page, "feedback": self._feedback_page,
            "code": self._code_page, "notes": self._notes_page,
        }
        for index, (key, title, icon) in enumerate(PAGES):
            self._route_buttons[key] = self.navigation.add_sub_interface(
                builders[key](), fluent_icon(icon), title, key,
            )
            self._page_indexes[key] = index
        self.navigation.currentChanged.connect(self._on_page_changed)
        self._apply_showcase_theme()
        theme.subscribe(self, self._apply_showcase_theme)
        self.set_page(page, animated=False)
        self._on_page_changed(self.navigation.current_route())

    def _page(self, title: str, subtitle: str) -> tuple[QtWidgets.QScrollArea, QtWidgets.QVBoxLayout]:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBar(FluentScrollBar(parent=scroll))
        scroll.setObjectName("showcaseScroll")
        content = QtWidgets.QWidget()
        content.setObjectName("showcasePage")
        body = QtWidgets.QVBoxLayout(content)
        body.setContentsMargins(28, 25, 28, 28)
        body.setSpacing(18)
        body.addWidget(label(title, role="pageTitle"))
        body.addWidget(label(subtitle, role="muted", wrap=True))
        scroll.setWidget(content)
        return scroll, body

    def _cards_page(self):
        from cards import create_cards_content

        scroll, body = self._page("卡片与设置", "从应用列表到分组设置，体验五种卡片的布局和交互。")
        self.cards_content = create_cards_content(scroll.widget())
        body.addWidget(self.cards_content)
        body.addStretch(1)
        return scroll

    def _date_picker(self, parent: QtWidgets.QWidget | None = None):
        if DatePicker is None:
            return None
        try:
            return DatePicker(parent)
        except RuntimeError:
            return None

    @staticmethod
    def _date_unavailable() -> QtWidgets.QLabel:
        return label("日期选择器需要当前 Python 对应的 C 扩展。编译后重启示例即可使用。", role="muted", wrap=True)

    def set_page(self, route: str, *, animated: bool = True) -> None:
        route = {"dates": "inputs", "date": "inputs", "navigation": "feedback", "performance": "code"}.get(route, route)
        if route not in self._page_indexes:
            route = "overview"
        self.navigation.set_current_route(route, animated=animated)

    def _on_page_changed(self, route: str) -> None:
        if route != "notes":
            self._pause_notes()
        self.activity.setText("当前页面 · " + dict((key, text) for key, text, _icon in PAGES)[route])

    def _toast(self, title: str, detail: str = "", placement: str = "target", *, target=None) -> None:
        if self._active_toast is not None:
            try:
                self._active_toast.hide()
                self._active_toast.close()
            except RuntimeError:  # A timed message may already be deleted by Qt.
                pass
        sender = self.sender()
        if target is None and isinstance(sender, QtWidgets.QWidget):
            target = sender
        self._active_toast = Toast.success(
            title, detail=detail, parent=self, target=target if placement == "target" else None,
            placement="top-right" if placement == "target" else placement, timeout_ms=4000,
        )
        self.activity.setText(title + (" · " + detail if detail else ""))

    def _overview_page(self):
        page, body = self._page("从一个小工作台开始", "选择日期、编辑文本、切换页面。这里的控件和操作都可以直接体验。")
        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(16)
        plan = Panel("今天的小计划", "用几个简单控件组合一份可操作的计划。")
        tasks = [CheckBox(text) for text in ("体验日期选择与范围限制", "编辑一段 JSON", "试试对话框与提示")]
        progress = ProgressBar()
        progress.setRange(0, len(tasks))
        progress.setValue(1)
        tasks[0].setChecked(True)
        for task in tasks:
            plan.body.addWidget(task)
            task.toggled.connect(lambda _checked, items=tasks: progress.setValue(sum(item.isChecked() for item in items)))
        plan.body.addWidget(progress)
        plan.body.addSpacing(6)
        plan.body.addWidget(label("给下一次体验选个日期", role="muted"))
        self.overview_date = self._date_picker()
        if self.overview_date is not None:
            self.overview_date.set_date(QtCore.QDate.currentDate().addDays(1))
            self.overview_date.dateChanged.connect(lambda date: self.activity.setText("计划日期 · " + (date.toString("yyyy-MM-dd") if date.isValid() else "未选择")))
            plan.body.addWidget(self.overview_date)
        else:
            plan.body.addWidget(self._date_unavailable())
        open_date = AccentButton("打开日期体验")
        open_date.clicked.connect(lambda: self.set_page("inputs"))
        plan.body.addLayout(button_row(open_date))
        columns.addWidget(plan, 1)

        quick = Panel("沿着组件走一遍", "每个页面都是一组完整的小场景。")
        for title, detail, route in (
            ("输入与日期", "预约表单、清空日期、限定可选范围。", "inputs"),
            ("代码与性能", "真实 JSON 高亮与独立性能对照。", "code"),
            ("音符视图", "双轨音符、进度演示与定位。", "notes"),
        ):
            quick.body.addWidget(label(title, role="smallTitle"))
            quick.body.addWidget(label(detail, role="muted", wrap=True))
            action = TextButton("去体验 →")
            action.clicked.connect(lambda _checked=False, key=route: self.set_page(key))
            quick.body.addLayout(button_row(action))
        columns.addWidget(quick, 1)
        body.addLayout(columns)
        strip = Panel("熟悉的 Qt，统一的视觉语言")
        strip.body.addWidget(label("保留控件常用的 Qt 使用方式，用主题、间距和清晰的反馈把界面连起来。输入与选择会立即反映到页面中。", role="muted", wrap=True))
        controls = button_row(Button("标准按钮"), OutlinedButton("描边按钮"), TextButton("轻量按钮"))
        for index in range(controls.count() - 1):
            controls.itemAt(index).widget().clicked.connect(lambda _checked=False: self._toast("按钮已响应", "切换到其他页面可以体验更多组合。"))
        strip.body.addLayout(controls)
        body.addWidget(strip)
        body.addStretch(1)
        return page

    def _inputs_page(self):
        page, body = self._page("输入与日期", "从选择一个日期，到提交一份预约。清空、回填和范围限制都在这里。")
        date_card = Panel("预约一次组件体验", "选择日期后，右侧会同步显示当前选择；提交只保存在本次示例会话中。")
        date_grid = QtWidgets.QGridLayout()
        date_grid.setHorizontalSpacing(20)
        date_grid.setVerticalSpacing(10)
        date_grid.addWidget(label("预约日期", role="muted"), 0, 0)
        date_grid.addWidget(label("当前选择", role="muted"), 0, 1)
        self.date_picker = self._date_picker()
        self.date_result = label("尚未选择", role="dateValue")
        date_grid.addWidget(self.date_result, 1, 1)
        self.date_detail = label("未选择日期时保持空值。", role="muted", wrap=True)
        date_grid.addWidget(self.date_detail, 2, 1)
        if self.date_picker is not None:
            date_grid.addWidget(self.date_picker, 1, 0)
            self.date_picker.set_date_range(QtCore.QDate.currentDate().addYears(-10), QtCore.QDate.currentDate().addYears(10))
            self.date_picker.dateChanged.connect(self._update_date)
        else:
            date_grid.addWidget(self._date_unavailable(), 1, 0, 2, 1)
        actions = QtWidgets.QWidget()
        action_layout = QtWidgets.QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        today = Button("今天")
        clear = Button("清空")
        today.setEnabled(self.date_picker is not None)
        clear.setEnabled(self.date_picker is not None)
        today.clicked.connect(lambda: self.date_picker.set_date(QtCore.QDate.currentDate()))
        clear.clicked.connect(lambda: self.date_picker.clear())
        action_layout.addWidget(today)
        action_layout.addWidget(clear)
        action_layout.addStretch()
        date_grid.addWidget(actions, 2, 0)
        date_grid.setColumnStretch(0, 1)
        date_grid.setColumnStretch(1, 1)
        date_card.body.addLayout(date_grid)
        self.date_limit = CheckBox("仅允许选择今天起 90 天内的日期")
        self.date_limit.setEnabled(self.date_picker is not None)
        self.date_limit.toggled.connect(self._limit_dates)
        date_card.body.addWidget(self.date_limit)
        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        form.addWidget(label("预约名称", role="muted"), 0, 0)
        form.addWidget(label("体验方向", role="muted"), 0, 1)
        self.booking_name = LineEdit("例如：周末的桌面应用计划")
        self.booking_name.setText("我的 FluentPy 体验")
        self.booking_type = ComboBox()
        self.booking_type.addItems(["完整组件体验", "输入与日期", "代码编辑器", "导航与反馈"])
        form.addWidget(self.booking_name, 1, 0)
        form.addWidget(self.booking_type, 1, 1)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)
        date_card.body.addLayout(form)
        submit = AccentButton("创建预约")
        self.booking_submit = submit
        submit.setEnabled(self.date_picker is not None)
        submit.clicked.connect(self._save_booking)
        next_week = Button("回填下周日期")
        next_week.setEnabled(self.date_picker is not None)
        next_week.clicked.connect(lambda: self.date_picker.set_date(QtCore.QDate.currentDate().addDays(7)))
        date_card.body.addLayout(button_row(submit, next_week))
        self.booking_result = label("创建的预约会显示在这里。", role="muted", wrap=True)
        date_card.body.addWidget(self.booking_result)
        body.addWidget(date_card)

        inputs = Panel("文本输入", "输入框保留清空、搜索和密码显隐等常用交互。")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(9)
        search = SearchLineEdit("搜索示例组件")
        password = PasswordLineEdit("试着输入一段密码")
        password.setText("fluent-example")
        editable = EditableComboBox()
        editable.addItems(["桌面应用", "工具工作台", "音乐编辑器"])
        search_result = label("输入搜索词，会即时显示在下方。", role="muted", wrap=True)
        search.textChanged.connect(lambda text: search_result.setText("正在查找：" + text if text else "输入搜索词，会即时显示在下方。"))
        grid.addWidget(label("搜索输入框", role="muted"), 0, 0)
        grid.addWidget(label("密码输入框", role="muted"), 0, 1)
        grid.addWidget(search, 1, 0)
        grid.addWidget(password, 1, 1)
        grid.addWidget(label("可编辑下拉框", role="muted"), 2, 0)
        grid.addWidget(editable, 3, 0)
        grid.addWidget(search_result, 2, 1, 2, 1)
        inputs.body.addLayout(grid)
        memo = TextEdit()
        memo.setPlaceholderText("记录这次体验的想法……")
        memo.setPlainText("用日期选择器安排时间，用清晰的反馈确认每一次操作。")
        memo.setFixedHeight(110)
        inputs.body.addWidget(memo)
        body.addWidget(inputs)

        options = Panel("选择与数值")
        opt_grid = QtWidgets.QGridLayout()
        opt_grid.setHorizontalSpacing(16)
        opt_grid.setVerticalSpacing(9)
        count = SpinBox()
        count.setRange(1, 12)
        count.setValue(3)
        amount = DoubleSpinBox()
        amount.setRange(0, 100)
        amount.setSingleStep(0.5)
        amount.setValue(2.5)
        opt_grid.addWidget(label("参与人数", role="muted"), 0, 0)
        opt_grid.addWidget(label("体验时长 / 小时", role="muted"), 0, 1)
        opt_grid.addWidget(count, 1, 0)
        opt_grid.addWidget(amount, 1, 1)
        preference = label("当前选择：专注模式", role="muted")
        radios = QtWidgets.QButtonGroup(page)
        radio_row = QtWidgets.QHBoxLayout()
        for title in ("专注模式", "自由探索"):
            radio = RadioButton(title)
            radios.addButton(radio)
            radio_row.addWidget(radio)
            radio.toggled.connect(lambda checked, text=title: preference.setText("当前选择：" + text) if checked else None)
            radio.setChecked(title == "专注模式")
        radio_row.addStretch()
        options.body.addLayout(opt_grid)
        options.body.addLayout(radio_row)
        options.body.addWidget(preference)
        body.addWidget(options)
        body.addStretch(1)
        return page

    def _update_date(self, date: QtCore.QDate) -> None:
        if date.isValid():
            self.date_result.setText(date.toString("MM 月 dd 日"))
            locale = QtCore.QLocale(QtCore.QLocale.Language.Chinese, QtCore.QLocale.Country.China)
            self.date_detail.setText(locale.toString(date, "yyyy 年 · dddd"))
            self.activity.setText("已选择日期 · " + date.toString("yyyy-MM-dd"))
        else:
            self.date_result.setText("尚未选择")
            self.date_detail.setText("未选择日期时保持空值。")
            self.activity.setText("日期已清空")

    def _limit_dates(self, limited: bool) -> None:
        if self.date_picker is None:
            return
        today = QtCore.QDate.currentDate()
        self.date_picker.set_date_range(today if limited else today.addYears(-10), today.addDays(90) if limited else today.addYears(10))
        self.activity.setText("日期范围 · 今天起 90 天" if limited else "日期范围 · 前后各 10 年")

    def _save_booking(self) -> None:
        if self.date_picker is None:
            return
        date = self.date_picker.date()
        if not date.isValid():
            self._toast("先选择一个日期", "点击日期输入框，或使用“回填下周日期”。", target=self.booking_submit)
            return
        name = self.booking_name.text().strip()
        if not name:
            self.booking_name.setFocus()
            self._toast("写一个预约名称", "名称会和所选日期一起保存在本次会话中。", target=self.booking_submit)
            return
        self._bookings.append({"name": name, "date": date.toString("yyyy-MM-dd"), "kind": self.booking_type.currentText()})
        self.booking_result.setText(f"已创建 {len(self._bookings)} 份预约 · {name} · {date.toString('yyyy-MM-dd')} · {self.booking_type.currentText()}")
        self._toast("预约已创建", name + " · " + date.toString("yyyy-MM-dd"), target=self.booking_submit)

    def _feedback_page(self):
        page, body = self._page("导航与反馈", "页面切换、标签、进度和对话框，组成一个有回应的界面。")
        navigation = Panel("从路径走进页面")
        breadcrumb = BreadcrumbBar()
        for key, title in (("workspace", "工作台"), ("projects", "我的项目"), ("current", "FluentPy")):
            breadcrumb.add_item(key, title)
        path_result = label("当前路径：FluentPy", role="muted")
        breadcrumb.currentChanged.connect(lambda key: path_result.setText("当前路径：" + {"workspace": "工作台", "projects": "我的项目", "current": "FluentPy"}[key]))
        navigation.body.addWidget(breadcrumb)
        navigation.body.addWidget(path_result)
        self.feedback_pivot = Pivot()
        self.pivot_stack = AnimatedStackedWidget()
        self.pivot_stack.setFixedHeight(76)
        pivot_indexes = {}
        for key, title, detail in (
            ("project", "项目", "在这里组织你的组件体验，输入的内容会保留在各自页面。"),
            ("activity", "活动", "日期选择和预约结果会实时反映到页面。"),
            ("settings", "设置", "使用侧栏菜单展开或收起导航，顶部开关可切换整个工作台的主题。"),
        ):
            content = QtWidgets.QWidget(self.pivot_stack)
            content_layout = QtWidgets.QVBoxLayout(content)
            content_layout.setContentsMargins(0, 8, 0, 8)
            content_layout.setSpacing(4)
            content_layout.addWidget(label(title, role="smallTitle"))
            content_layout.addWidget(label(detail, role="muted", wrap=True))
            content_layout.addStretch(1)
            pivot_indexes[key] = self.pivot_stack.addWidget(content)
            self.feedback_pivot.add_item(key, title)
        self.feedback_pivot.currentChanged.connect(
            lambda key: self.pivot_stack.setCurrentIndex(pivot_indexes[key])
        )
        navigation.body.addWidget(self.feedback_pivot, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        navigation.body.addWidget(self.pivot_stack)
        body.addWidget(navigation)

        documents = Panel("可以切换的文档", "切换标签时保留各页编辑内容；点击 + 新建，点击 × 关闭。")
        self.document_tabs = TabBar()
        self.document_stack = AnimatedStackedWidget()
        self.document_stack.setFixedHeight(136)
        self._document_keys: list[str] = []
        self._documents: dict[str, QtWidgets.QWidget] = {}
        self._next_document = 1
        self._empty_document = label("标签已关闭，点击 + 新建一页。", role="muted")
        self._empty_document.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.document_stack.addWidget(self._empty_document)
        self.document_stack.setAnimationDuration(0)
        self.document_tabs.currentChanged.connect(self._select_document)
        self.document_tabs.tabAddRequested.connect(self._add_document)
        self.document_tabs.tabCloseRequested.connect(self._close_document)
        plan = CodeEdit()
        plan.set_indent_size(2)
        plan.set_code('{\n  "project": "FluentPy",\n  "tasks": ["体验导航", "编辑文档"]\n}')
        self._register_document("plan", "体验计划.json", plan, FluentIcon.CODE)
        notes = TextEdit()
        notes.setPlainText("在这里记录体验的想法。\n切换标签后，这些文字仍会保留。")
        self._register_document("notes", "随手记.md", notes, FluentIcon.DOCUMENT)
        # Initial content is ready immediately; later user switches use the native transition.
        self._select_document("plan")
        self.document_stack.setAnimationDuration(180)
        documents.body.addWidget(self.document_tabs)
        documents.body.addWidget(self.document_stack)
        body.addWidget(documents)

        feedback = Panel("每个操作，都有回应", "提示默认指向触发按钮，点击 × 关闭；也可以选择窗口四角。")
        self.toast_position = ComboBox()
        self.toast_position.addItems(["跟随按钮（带箭头）", "右上角", "右下角", "左上角", "左下角"])
        toast_button = AccentButton("显示轻提示")
        self.toast_button = toast_button
        toast_button.clicked.connect(lambda: self._toast("操作已完成", "可以继续下一步，也可以点击右上角关闭提示。", ("target", "top-right", "bottom-right", "top-left", "bottom-left")[self.toast_position.currentIndex()], target=toast_button))
        mask_button = Button("打开遮罩对话框")
        mask_button.clicked.connect(self._show_masked)
        frameless = Button("无边框对话框")
        frameless.clicked.connect(self._show_frameless)
        feedback.body.addLayout(button_row(self.toast_position, toast_button))
        feedback.body.addLayout(button_row(mask_button, frameless))
        self.feedback_result = label("对话框的确认与取消结果会显示在这里。", role="muted", wrap=True)
        feedback.body.addWidget(self.feedback_result)
        self.slider = Slider()
        self.slider.setRange(0, 100)
        self.slider.setValue(42)
        progress = ProgressBar()
        progress.setRange(0, 100)
        progress.setValue(42)
        progress_text = label("体验进度 42%", role="muted")
        self.slider.valueChanged.connect(progress.setValue)
        self.slider.valueChanged.connect(lambda value: progress_text.setText(f"体验进度 {value}%"))
        feedback.body.addWidget(progress_text)
        feedback.body.addWidget(self.slider)
        feedback.body.addWidget(progress)
        body.addWidget(feedback)

        icons = Panel("把常用操作放到手边", "点击图标会复制对应的 FluentIcon 枚举名。")
        icon_row = QtWidgets.QHBoxLayout()
        for icon in (FluentIcon.ADD, FluentIcon.DOCUMENT_SAVE, FluentIcon.CALENDAR_LTR, FluentIcon.COPY, FluentIcon.SETTINGS, FluentIcon.HEART):
            action = IconButton(fluent_icon(icon), tooltip="复制 FluentIcon." + icon.name)
            action.setFixedSize(42, 38)
            action.clicked.connect(lambda _checked=False, key=icon: self._copy("FluentIcon." + key.name, "图标名称已复制"))
            icon_row.addWidget(action)
        icon_row.addStretch()
        icons.body.addLayout(icon_row)
        body.addWidget(icons)
        body.addStretch(1)
        return page

    def _register_document(self, key: str, title: str, editor: QtWidgets.QWidget,
                           icon: FluentIcon = FluentIcon.DOCUMENT) -> None:
        self._document_keys.append(key)
        self._documents[key] = editor
        self.document_stack.addWidget(editor)
        self.document_tabs.add_tab(key, title, fluent_icon(icon))

    def _select_document(self, key: str) -> None:
        self.document_stack.setCurrentWidget(self._documents.get(key, self._empty_document))

    def _add_document(self) -> None:
        number = self._next_document
        self._next_document += 1
        editor = TextEdit()
        editor.setPlaceholderText("在新文档中写点什么……")
        key = f"new-{number}"
        self._register_document(key, f"新文档 {number}", editor)
        self.document_tabs.set_current_tab(key)

    def _close_document(self, index: int) -> None:
        if not 0 <= index < len(self._document_keys):
            return
        key = self._document_keys.pop(index)
        editor = self._documents.pop(key)
        self.document_stack.removeWidget(editor)
        editor.deleteLater()

    def _show_masked(self) -> None:
        if self._masked is None:
            self._masked = MaskedDialog("保存这份体验记录？", "修改名称后确认，结果会留在当前页面。", self)
            self._draft_name = LineEdit("记录名称")
            self._draft_name.setText("我的 FluentPy 体验")
            self._masked.add_content_widget(self._draft_name)
            self._masked.setYesButtonText("保存记录")
            self._masked.setClosableOnMaskClicked(True)
            self._masked.accepted.connect(lambda: self._finish_feedback("已保存：" + (self._draft_name.text().strip() or "未命名记录")))
            self._masked.rejected.connect(lambda: self._finish_feedback("已取消，本次记录未保存。"))
        self._masked.open()

    def _show_frameless(self) -> None:
        if self._frameless is None:
            self._frameless = FramelessDialog("继续探索？", "确认后可以接着体验其他页面，取消会留在这里。", self)
            self._frameless.accepted.connect(lambda: self._finish_feedback("已确认继续探索。"))
            self._frameless.rejected.connect(lambda: self._finish_feedback("已取消，留在当前页面。"))
        self._frameless.open()

    def _finish_feedback(self, message: str) -> None:
        self.feedback_result.setText(message)
        self.activity.setText(message)

    def _code_page(self):
        page, body = self._page("代码与性能", "编辑一段 JSON，观察行号、缩进引导和高亮。性能测量在独立窗口中运行。")
        code = Panel("可编辑的 JSON", "C 扩展可用时，代码编辑器自动使用 C 分词；Qt 继续负责文本布局和绘制。")
        self.code_editor = CodeEdit()
        self.code_editor.set_indent_size(2)
        self.code_editor.set_code(SAMPLE)
        self.code_editor.setMinimumHeight(285)
        code.body.addWidget(self.code_editor)
        reset = Button("还原示例")
        reset.clicked.connect(lambda: self.code_editor.set_code(SAMPLE))
        copy = Button("复制代码")
        copy.clicked.connect(lambda: self._copy(self.code_editor.code(), "代码已复制"))
        undo = TextButton("撤销")
        undo.clicked.connect(self.code_editor.text_edit.undo)
        redo = TextButton("重做")
        redo.clicked.connect(self.code_editor.text_edit.redo)
        code.body.addLayout(button_row(reset, copy, undo, redo))
        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(10)
        modes = SegmentedWidget()
        modes.add_item("json", "JSON")
        modes.add_item("plain", "纯文本")
        modes.currentChanged.connect(self.code_editor.set_language)
        controls.addWidget(modes)
        controls.addStretch()
        controls.addWidget(label("字号", role="muted"))
        size = SpinBox()
        size.setRange(10, 24)
        size.setValue(self.code_editor.font_size())
        size.setFixedWidth(104)
        size.valueChanged.connect(self.code_editor.set_font_size)
        controls.addWidget(size)
        self.code_position = label("1 : 1", role="muted")
        controls.addWidget(self.code_position)
        self.code_editor.text_edit.cursorPositionChanged.connect(self._update_code_position)
        code.body.addLayout(controls)
        body.addWidget(code)

        performance = Panel("用同一份数据对照", "载入、完整高亮、编辑和滚动分别测量。C 分词提速不等于所有界面操作都会等比例提速。")
        report_path = ROOT / "benchmarks" / "text-performance.json"
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            native = report["summary"]["native"]
            original = report["summary"]["legacy"]
            performance.body.addWidget(label(f"最近本机报告 · {report['dataset']['lines']:,} 行 JSON · {report['repeat']} 次中位数", role="muted"))
            performance.body.addWidget(label(f"完整载入  {original['load_ready_ms']:.2f} ms → {native['load_ready_ms']:.2f} ms", role="smallTitle"))
        except (OSError, ValueError, KeyError, TypeError):
            performance.body.addWidget(label("还没有本机测量报告，打开性能对照窗口即可生成。", role="muted", wrap=True))
        open_performance = AccentButton("打开性能对照")
        open_performance.clicked.connect(lambda: self._open_example("text_performance.py"))
        open_code = Button("独立代码编辑器")
        open_code.clicked.connect(lambda: self._open_example("code_editor.py"))
        performance.body.addLayout(button_row(open_performance, open_code))
        body.addWidget(performance)
        body.addStretch(1)
        return page

    def _update_code_position(self) -> None:
        cursor = self.code_editor.text_edit.textCursor()
        self.code_position.setText(f"{cursor.blockNumber() + 1} : {cursor.positionInBlock() + 1}")

    def _copy(self, text: str, message: str) -> None:
        QtWidgets.QApplication.clipboard().setText(text)
        self._toast(message)

    def _open_example(self, filename: str) -> None:
        executable = Path(sys.executable)
        if executable.name.lower() == "pythonw.exe":
            executable = executable.with_name("python.exe")
        process = QtCore.QProcess(self)
        process.setProgram(str(executable))
        process.setArguments(["-B", str(ROOT / "examples" / filename)] + (["--dark"] if theme.mode.value == "dark" else []))
        process.setWorkingDirectory(str(ROOT))
        launch_result = process.startDetached()
        started = launch_result[0] if isinstance(launch_result, tuple) else launch_result
        process.deleteLater()
        if started:
            self.activity.setText("已打开独立示例 · " + filename)
        else:
            self._toast("示例未能启动", "请使用当前 Python 直接运行 examples/" + filename)

    def _notes_page(self):
        page, body = self._page("让音符变成可读的时间", "用双轨短句体验音符布局、时间定位与主题切换。进度演示只移动游标，不播放声音。")
        view = Panel("音符时间轴")
        self.timeline = NoteTimeline()
        self.timeline.setMinimumHeight(210)
        self.timeline.set_empty_text("暂无音符，选择一段示例开始。")
        view.body.addWidget(self.timeline)
        self.note_source = ComboBox()
        self.note_source.addItems(["双轨短句", "单轨旋律", "空状态"])
        self.note_play = AccentButton("演示进度")
        self.note_play.clicked.connect(self._toggle_notes)
        reset = Button("回到开头")
        reset.clicked.connect(self._reset_notes)
        view.body.addLayout(button_row(self.note_source, self.note_play, reset))
        self.note_scrub = Slider()
        self.note_scrub.setRange(0, 7500)
        self.note_scrub.valueChanged.connect(lambda value: self._seek_notes(value / 1000))
        view.body.addWidget(self.note_scrub)
        self.note_position = label("0.00 / 7.50 秒", role="muted")
        view.body.addWidget(self.note_position)
        self.timeline.positionChanged.connect(self._sync_notes)
        self.note_source.currentIndexChanged.connect(self._load_notes)
        self._load_notes(0)
        body.addWidget(view)
        settings = Panel("让显示适合这段音符")
        fixed = CheckBox("固定音域为 MIDI 48–84")
        fixed.toggled.connect(lambda checked: self.timeline.set_pitch_range(48, 84) if checked else self.timeline.set_pitch_range())
        settings.body.addWidget(fixed)
        palette = ComboBox()
        palette.addItems(["默认轨道配色", "薄荷与蓝色"])
        palette.currentIndexChanged.connect(lambda index: self.timeline.set_track_colors(["#009faa", "#5c72c9"] if index else ["#8b7ec8", "#4aabb6"]))
        settings.body.addWidget(palette)
        settings.body.addWidget(label("拖动滑块可定位；播放过程中切换页面会暂停演示。", role="muted", wrap=True))
        body.addWidget(settings)
        body.addStretch(1)
        return page

    def _load_notes(self, index: int) -> None:
        self._pause_notes()
        if index == 2:
            self.timeline.clear()
        else:
            pitches = (60, 64, 67, 65, 62, 64, 69, 67, 64, 62, 60, 64, 62, 60)
            notes = [NoteEvent(i * 0.5, 0.35, pitch) for i, pitch in enumerate(pitches)]
            if index == 0:
                notes.extend(NoteEvent(i, 0.75, pitch, track=1) for i, pitch in enumerate((48, 55, 50, 57, 52, 55, 48)))
            self.timeline.set_notes(notes, duration=7.5)
        self.note_play.setEnabled(bool(self.timeline.notes()))
        self.note_scrub.setEnabled(bool(self.timeline.notes()))
        self._sync_notes(self.timeline.position())

    def _sync_notes(self, seconds: float) -> None:
        self.note_position.setText(f"{seconds:.2f} / {self.timeline.duration():.2f} 秒")
        blocker = QtCore.QSignalBlocker(self.note_scrub)
        self.note_scrub.setValue(round(seconds * 1000))
        del blocker

    def _pause_notes(self) -> None:
        self._note_timer.stop()
        if hasattr(self, "note_play"):
            self.note_play.setText("演示进度")

    def _toggle_notes(self) -> None:
        if self._note_timer.isActive():
            self._pause_notes()
            return
        if self.timeline.position() >= self.timeline.duration():
            self.timeline.set_position(0.0)
        self._note_start = self.timeline.position()
        self._note_elapsed.start()
        self._note_timer.start()
        self.note_play.setText("暂停演示")

    def _advance_notes(self) -> None:
        self.timeline.set_position(self._note_start + self._note_elapsed.elapsed() / 1000)
        if self.timeline.position() >= self.timeline.duration():
            self._pause_notes()

    def _seek_notes(self, seconds: float) -> None:
        self.timeline.set_position(seconds)
        if self._note_timer.isActive():
            self._note_start = seconds
            self._note_elapsed.restart()

    def _reset_notes(self) -> None:
        self._pause_notes()
        self.timeline.set_position(0.0)

    def _apply_showcase_theme(self) -> None:
        tokens = theme.tokens
        dark = tokens.mode.value == "dark"
        self.theme_caption.setText("深色" if dark else "浅色")
        blocker = QtCore.QSignalBlocker(self.theme_toggle)
        self.theme_toggle.setChecked(dark)
        del blocker
        styles = (
            f"QFrame#showcaseHeader {{ background: {tokens.surface}; border-bottom: 1px solid {tokens.border}; }}"
            f"QFrame#showcaseFooter {{ background: {tokens.surface}; border-top: 1px solid {tokens.border}; }}"
            f"QWidget#showcasePage, QScrollArea#showcaseScroll {{ background: {tokens.background}; border: none; }}"
            f"QScrollArea#showcaseScroll > QWidget > QWidget {{ background: {tokens.background}; }}"
            f"QLabel#showcaseBrand {{ color: {tokens.text}; font-size: 19px; font-weight: 600; }}"
            f"QLabel#pageTitle {{ color: {tokens.text}; font-size: 26px; font-weight: 600; }}"
            f"QLabel#smallTitle {{ color: {tokens.text}; font-size: 15px; font-weight: 600; }}"
            f"QLabel#dateValue {{ color: {tokens.text}; font-size: 24px; font-weight: 600; }}"
            f"QLabel#railCaption {{ color: {tokens.text_muted}; font-size: 12px; }}"
            f"QLabel#backendBadge {{ color: {tokens.accent}; font-size: 12px; }}"
        )
        self.setStyleSheet(self.styleSheet() + styles)
        central = self.centralWidget()
        central.setStyleSheet(central.styleSheet() + styles)

    def closeEvent(self, event) -> None:
        self._note_timer.stop()
        super().closeEvent(event)


def create_showcase_window(mode: str = "light", page: str = "overview") -> Showcase:
    return Showcase(dark=mode == "dark", page=page)


def main() -> int:
    parser = argparse.ArgumentParser(description="FluentPy interactive showcase")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--page", default="overview", choices=[key for key, _text, _icon in PAGES] + ["dates", "date", "navigation", "performance"])
    parser.add_argument("--screenshot", type=Path, metavar="ABSOLUTE_PATH")
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot")
    if args.screenshot and not args.screenshot.is_absolute():
        parser.error("--screenshot must be an absolute path")
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    app.setApplicationName("FluentPy Showcase")
    app.setWindowIcon(QtGui.QIcon(str(BRAND_ICON)))
    app.setOrganizationName("FluentPy")
    app.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.Language.Chinese, QtCore.QLocale.Country.China))
    window = Showcase(dark=args.dark, page=args.page)
    if args.quit_after_screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    if args.screenshot:
        def capture() -> None:
            try:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(args.screenshot)):
                    raise OSError("Could not save screenshot")
                print("Screenshot saved: " + str(args.screenshot), flush=True)
            except OSError as error:
                print(str(error), file=sys.stderr, flush=True)
                if args.quit_after_screenshot:
                    window.close()
                    app.exit(1)
                return
            if args.quit_after_screenshot:
                window.close()
                app.quit()
        QtCore.QTimer.singleShot(350, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
