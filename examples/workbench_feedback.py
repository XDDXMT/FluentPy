"""A focused notification playground using existing FluentPy widgets."""

from __future__ import annotations

from info_bar import EmbeddedInfoBarExamples

from fluentpy import (
    AccentButton,
    Button,
    CheckBox,
    ColorPickerButton,
    ColorToast,
    ComboBox,
    ExpandableCardWidget,
    InfoBar,
    LineEdit,
    ProgressInfoBar,
    ProgressToast,
    SegmentedWidget,
    Slider,
    TextButton,
    Toast,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets, Slot
from fluentpy.theme.fonts import ui_font

COMPONENTS = (
    ("info", "消息条", "InfoBar"),
    ("color", "顶部色条吐司", "ColorToast"),
    ("task-info", "任务消息条", "ProgressInfoBar"),
    ("task-toast", "任务吐司", "ProgressToast"),
    ("toast", "轻提示", "Toast"),
)
POSITIONS = (
    ("top-center", "顶部居中"),
    ("bottom-center", "底部居中"),
    ("top-left", "左上角"),
    ("top-right", "右上角"),
    ("bottom-left", "左下角"),
    ("bottom-right", "右下角"),
)
TONES = (
    ("info", "信息"),
    ("success", "成功"),
    ("warning", "警告"),
    ("error", "失败"),
    ("accent", "强调"),
)


def caption(text, name="studioCaption"):
    label = QtWidgets.QLabel(text)
    label.setObjectName(name)
    label.setWordWrap(True)
    return label


def field(layout, title, widget):
    group = QtWidgets.QWidget()
    box = QtWidgets.QVBoxLayout(group)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(5)
    label = caption(title)
    label.setBuddy(widget)
    box.addWidget(label)
    box.addWidget(widget)
    layout.addWidget(group)
    return group


class FeedbackPlayground(QtWidgets.QWidget):
    """One live preview and one inspector instead of a stack of button grids."""

    def __init__(self, show_masked, show_frameless, parent=None):
        super().__init__(parent)
        self.setObjectName("feedbackPlayground")
        self._preview = None
        self._messages = {}
        self._serial = 0
        self._positions = []
        self._section = "playground"
        self._custom_strip_color = None
        self._refresh = QtCore.QTimer(self)
        self._refresh.setSingleShot(True)
        self._refresh.setInterval(160)
        self._refresh.timeout.connect(self.refresh_preview)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)
        self.tabs = SegmentedWidget()
        for key, title in (
            ("playground", "自定义测试"),
            ("embedded", "嵌入示例"),
            ("dialogs", "对话框"),
        ):
            self.tabs.add_item(key, title)
        root.addWidget(self.tabs, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.editor = QtWidgets.QWidget()
        self.workspace = QtWidgets.QBoxLayout(
            QtWidgets.QBoxLayout.Direction.LeftToRight, self.editor
        )
        self.workspace.setContentsMargins(0, 0, 0, 0)
        self.workspace.setSpacing(18)
        self._build_preview()
        self._build_inspector()
        self.workspace.addWidget(self.preview_shell, 1)
        self.workspace.addWidget(self.inspector)
        self.embedded_page = QtWidgets.QFrame()
        self.embedded_page.setObjectName("studioSurface")
        embedded = QtWidgets.QVBoxLayout(self.embedded_page)
        embedded.setContentsMargins(18, 18, 18, 18)
        embedded.setSpacing(8)
        embedded.addWidget(caption("页面中的真实布局", "studioHeading"))
        embedded.addWidget(caption("试着关闭消息、提交备注或推进任务，观察页面如何随内容变化。"))
        self.embedded_examples = EmbeddedInfoBarExamples()
        embedded.addWidget(self.embedded_examples)
        self.dialog_page = QtWidgets.QFrame()
        self.dialog_page.setObjectName("studioSurface")
        dialog = QtWidgets.QVBoxLayout(self.dialog_page)
        dialog.setContentsMargins(28, 28, 28, 28)
        dialog.setSpacing(16)
        dialog.addWidget(caption("一次确认，完成一个操作", "studioHeading"))
        dialog.addWidget(caption("选择对话框样式，打开后体验确认、取消和关闭。"))
        dialog_row = QtWidgets.QHBoxLayout()
        self.dialog_choice = ComboBox()
        self.dialog_choice.addItems(["遮罩确认框", "无边框对话框"])
        self.dialog_button = AccentButton("打开对话框")
        self.dialog_button.clicked.connect(
            lambda: (show_masked if self.dialog_choice.currentIndex() == 0 else show_frameless)()
        )
        dialog_row.addWidget(self.dialog_choice, 1)
        dialog_row.addWidget(self.dialog_button)
        dialog.addLayout(dialog_row)
        self.dialog_result = caption("操作结果会显示在这里。")
        dialog.addWidget(self.dialog_result)
        dialog.addStretch()
        self.dialog_page.setMinimumHeight(260)
        for page in (self.editor, self.embedded_page, self.dialog_page):
            root.addWidget(page)
        self.embedded_page.hide()
        self.dialog_page.hide()
        self.tabs.currentChanged.connect(self._change_section)
        self.component.currentIndexChanged.connect(self._component_changed)
        for widget in (self.title_input, self.detail_input, self.action_input):
            widget.textChanged.connect(self.schedule_preview)
        for widget in (
            self.inline_position,
            self.overlay_position,
            self.orientation,
            self.width_choice,
            self.task_state,
        ):
            widget.currentIndexChanged.connect(self.schedule_preview)
        self.tone.currentIndexChanged.connect(self._tone_changed)
        for widget in (self.action_check, self.closable, self.auto_close, self.unknown):
            widget.toggled.connect(self.schedule_preview)
        self.action_check.toggled.connect(self.action_input.setVisible)
        self.progress.valueChanged.connect(self._progress_changed)
        self.color_picker.colorChanged.connect(self._color_changed)
        self._component_changed()
        theme.subscribe(self, self._apply_theme)
        self._apply_theme()

    def _build_preview(self):
        self.preview_shell = QtWidgets.QFrame()
        self.preview_shell.setObjectName("studioPreviewShell")
        box = QtWidgets.QVBoxLayout(self.preview_shell)
        box.setContentsMargins(18, 16, 18, 16)
        box.setSpacing(12)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(caption("实时预览", "studioHeading"), 1)
        self.api_badge = caption("InfoBar", "studioBadge")
        head.addWidget(self.api_badge)
        box.addLayout(head)
        self.preview_hint = caption("修改右侧内容，预览会同步更新。")
        box.addWidget(self.preview_hint)
        self.canvas = QtWidgets.QFrame()
        self.canvas.setObjectName("studioCanvas")
        self.canvas.setMinimumHeight(250)
        self.canvas.setMinimumWidth(0)
        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )
        self.inline_layout = QtWidgets.QVBoxLayout(self.canvas)
        self.inline_layout.setContentsMargins(8, 8, 8, 8)
        self.inline_layout.addStretch()
        self.inline_holder = QtWidgets.QWidget(self.canvas)
        self.inline_body = QtWidgets.QVBoxLayout(self.inline_holder)
        self.inline_body.setContentsMargins(0, 0, 0, 0)
        self.inline_body.setSpacing(0)
        self.inline_layout.addWidget(self.inline_holder)
        self.inline_layout.addStretch()
        box.addWidget(self.canvas, 1)
        self.task_controls = QtWidgets.QWidget()
        task = QtWidgets.QVBoxLayout(self.task_controls)
        task.setContentsMargins(0, 0, 0, 0)
        task.setSpacing(8)
        task_head = QtWidgets.QHBoxLayout()
        self.progress_label = caption("进度 35%")
        task_head.addWidget(self.progress_label, 1)
        self.task_state = ComboBox()
        self.task_state.addItems(["进行中", "成功", "失败"])
        task_head.addWidget(self.task_state)
        task.addLayout(task_head)
        self.progress = Slider()
        self.progress.setRange(0, 100)
        self.progress.setValue(35)
        task.addWidget(self.progress)
        box.addWidget(self.task_controls)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.test_button = AccentButton("测试效果")
        self.test_button.clicked.connect(self.test_current)
        self.stack_button = Button("连续三条")
        self.stack_button.clicked.connect(self.test_stack)
        self.clear_button = TextButton("清除")
        self.clear_button.clicked.connect(self.clear_messages)
        row.addWidget(self.test_button)
        row.addWidget(self.stack_button)
        row.addStretch()
        row.addWidget(self.clear_button)
        box.addLayout(row)
        self.result = caption("预览区中的组件可以直接操作。")
        box.addWidget(self.result)

    def _build_inspector(self):
        self.inspector = QtWidgets.QFrame()
        self.inspector.setObjectName("studioSurface")
        self.inspector.setFixedWidth(280)
        box = QtWidgets.QVBoxLayout(self.inspector)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(12)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(caption("自定义", "studioHeading"), 1)
        reset = TextButton("重置")
        reset.clicked.connect(self.reset_options)
        head.addWidget(reset)
        box.addLayout(head)
        self.component = ComboBox()
        self.component.addItems([title for _, title, _ in COMPONENTS])
        field(box, "组件", self.component)
        self.title_input = LineEdit("输入标题")
        self.title_input.setText("操作提示")
        self.title_input.setAccessibleName("预览标题")
        self.detail_input = LineEdit("输入正文")
        self.detail_input.setText("修改内容，立即查看消息效果。")
        self.detail_input.setCursorPosition(0)
        self.detail_input.setAccessibleName("预览正文")
        field(box, "标题", self.title_input)
        field(box, "正文", self.detail_input)
        pair = QtWidgets.QHBoxLayout()
        pair.setSpacing(8)
        self.tone = ComboBox()
        self.tone.addItems([text for _, text in TONES])
        self.tone.setCurrentIndex(1)
        self.inline_position = ComboBox()
        self.inline_position.addItems(["嵌入布局"] + [title for _, title in POSITIONS])
        self.overlay_position = ComboBox()
        self.overlay_position.addItems([title for _, title in POSITIONS] + ["跟随按钮"])
        self.overlay_position.hide()
        self.position = self.inline_position
        position_holder = QtWidgets.QWidget()
        positions = QtWidgets.QVBoxLayout(position_holder)
        positions.setContentsMargins(0, 0, 0, 0)
        positions.setSpacing(0)
        positions.addWidget(self.inline_position)
        positions.addWidget(self.overlay_position)
        for control in (self.tone, self.inline_position, self.overlay_position):
            control.setMinimumWidth(0)
        self.tone_group = field(pair, "状态", self.tone)
        field(pair, "显示位置", position_holder)
        box.addLayout(pair)
        self.action_check = CheckBox("添加操作按钮")
        box.addWidget(self.action_check)
        self.action_input = LineEdit("按钮文字")
        self.action_input.setText("查看详情")
        self.action_input.setAccessibleName("预览按钮文字")
        self.action_input.hide()
        box.addWidget(self.action_input)
        self.advanced = ExpandableCardWidget("更多设置")
        self.advanced.body_layout.setSpacing(10)
        options = self.advanced.body_layout
        self.orientation = ComboBox()
        self.orientation.addItems(["横向排列", "纵向排列"])
        self.orientation_group = field(options, "内容方向", self.orientation)
        self.width_choice = ComboBox()
        self.width_choice.addItems(["自动宽度", "240", "320", "480", "640"])
        self.width_group = field(options, "卡片宽度", self.width_choice)
        self.color_picker = ColorPickerButton("#009faa", enable_alpha=False)
        self.color_group = field(options, "顶部颜色", self.color_picker)
        self.closable = CheckBox("显示关闭按钮")
        self.closable.setChecked(True)
        options.addWidget(self.closable)
        self.auto_close = CheckBox("测试消息自动关闭")
        self.auto_close.setChecked(True)
        options.addWidget(self.auto_close)
        self.unknown = CheckBox("未知进度")
        options.addWidget(self.unknown)
        box.addWidget(self.advanced)
        box.addStretch()

    def kind(self):
        return COMPONENTS[self.component.currentIndex()][0]

    def placement(self):
        index = self.position.currentIndex()
        return self._positions[index] if 0 <= index < len(self._positions) else None

    def _component_changed(self):
        kind = self.kind()
        is_info = kind in ("info", "task-info")
        is_task = kind.startswith("task-")
        selected = self.placement()
        self.position = self.inline_position if is_info else self.overlay_position
        self.inline_position.setVisible(is_info)
        self.overlay_position.setVisible(not is_info)
        with QtCore.QSignalBlocker(self.position):
            self._positions = (
                ([None] if is_info else [])
                + [key for key, _ in POSITIONS]
                + ([] if is_info else ["target"])
            )
            index = self._positions.index(selected) if selected in self._positions else 0
            self.position.setCurrentIndex(max(0, index))
        self.api_badge.setText(COMPONENTS[self.component.currentIndex()][2])
        self.task_controls.setVisible(is_task)
        self.tone_group.setVisible(not is_task and kind != "toast")
        self.orientation_group.setVisible(is_info)
        self.width_group.setVisible(kind in ("info", "task-info", "color"))
        self.color_group.setVisible(kind == "color")
        self.unknown.setVisible(is_task)
        self.closable.setVisible(is_info)
        self.auto_close.setVisible(not is_task)
        self.action_check.setVisible(kind in ("info", "task-info", "color"))
        self.action_input.setVisible(
            self.action_check.isVisible() and self.action_check.isChecked()
        )
        self.schedule_preview()

    def schedule_preview(self, *_args):
        self.stack_button.setVisible(self.placement() not in (None, "target"))
        task = self.kind().startswith("task-")
        self.progress.setEnabled(
            task and self.task_state.currentIndex() == 0 and not self.unknown.isChecked()
        )
        if self.isVisible() and self._section == "playground":
            self._refresh.start()

    def _tone_changed(self, *_args):
        self._custom_strip_color = None
        self.schedule_preview()

    def _color_changed(self, color):
        self._custom_strip_color = QtGui.QColor(color)
        self.schedule_preview()

    def _progress_changed(self, value):
        self.progress_label.setText(f"进度 {value}%")
        if (
            isinstance(self._preview, (ProgressInfoBar, ProgressToast))
            and self.kind().startswith("task-")
            and self.task_state.currentIndex() == 0
        ):
            try:
                self._preview.set_progress(value)
            except RuntimeError:
                self.schedule_preview()

    def _dispose_preview(self):
        if self._preview is None:
            return
        widget = self._preview
        self._preview = None
        try:
            self.inline_body.removeWidget(widget)
            widget.hide()
            widget.close()
            widget.deleteLater()
        except RuntimeError:
            pass

    def _create_message(self, parent, *, preview=False, title=None):
        kind = self.kind()
        title = self.title_input.text() if title is None else title
        detail = self.detail_input.text()
        tone = TONES[self.tone.currentIndex()][0]
        width = (None, 240, 320, 480, 640)[self.width_choice.currentIndex()]
        action = self.action_input.text() if self.action_check.isChecked() else ""
        callback = (lambda: self.result.setText(f"已触发“{action}”操作。")) if action else None
        options = dict(
            card_width=width,
            action_text=action,
            action_callback=callback,
            close_on_action=False if preview else True,
        )
        target = self.test_button if not preview and self.placement() == "target" else None
        if target is not None:
            options["target"] = target
        if kind in ("info", "task-info"):
            cls = InfoBar if kind == "info" else ProgressInfoBar
            options.update(
                orientation=("horizontal", "vertical")[self.orientation.currentIndex()],
                closable=self.closable.isChecked(),
            )
            if kind == "info":
                options["tone"] = tone
            else:
                options["indeterminate"] = self.unknown.isChecked()
            message = cls(title, detail, parent, **options)
        elif kind == "color":
            message = ColorToast(
                title, detail, parent, tone=tone, color=self._custom_strip_color, **options
            )
            if preview and self._custom_strip_color is None:
                with QtCore.QSignalBlocker(self.color_picker):
                    self.color_picker.set_color(message.color())
        elif kind == "task-toast":
            message = ProgressToast(
                title, detail, parent, indeterminate=self.unknown.isChecked(), target=target
            )
        else:
            message = Toast(title, detail, parent, target=target)
        if kind.startswith("task-"):
            if not self.unknown.isChecked():
                message.set_progress(self.progress.value())
            state = self.task_state.currentIndex()
            if state == 1:
                message.finish(timeout_ms=0)
            elif state == 2:
                message.fail(timeout_ms=0)
        if not preview:
            message.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
            if kind in ("info", "color") and self.auto_close.isChecked():
                message.set_timeout(4000)
            elif kind == "toast" and self.auto_close.isChecked():
                timer = QtCore.QTimer(message)
                timer.setSingleShot(True)
                timer.timeout.connect(message.close)
                timer.start(4000)
        return message

    def refresh_preview(self):
        self._refresh.stop()
        if not self.isVisible() or self._section != "playground":
            return
        self._dispose_preview()
        placement = self.placement()
        inline = placement is None and self.kind() in ("info", "task-info")
        self._preview = self._create_message(
            self.inline_holder if inline else self.canvas, preview=True
        )
        width = min(max(1, self.canvas.width() - 16), self._preview.sizeHint().width())
        self.canvas.setMinimumHeight(max(250, min(640, self._preview.heightForWidth(width) + 36)))
        if inline:
            self.inline_body.addWidget(self._preview)
            self._preview.show()
        else:
            self._preview.show_at(
                "top-center" if placement == "target" else placement or "top-center"
            )
        self.preview_hint.setText(
            "嵌入布局 · 可以直接点击组件内的按钮。"
            if inline
            else "点击测试效果，消息将带箭头指向测试按钮。"
            if placement == "target"
            else "窗口浮层 · 位置和堆叠均可实际测试。"
        )

    def test_current(self):
        self.refresh_preview()
        placement = self.placement()
        if placement is None:
            self.result.setText("已恢复嵌入预览，组件由真实页面布局管理。")
            return
        message = self._create_message(self.window())
        message.show_at("top-center" if placement == "target" else placement)
        self._track(message)
        self.result.setText("已在工作台窗口中显示；悬停、操作按钮和关闭均可测试。")
        return message

    def test_stack(self):
        placement = self.placement()
        if placement in (None, "target"):
            return
        for index in range(3):
            message = self._create_message(
                self.window(), title=f"{self.title_input.text()} · {index + 1}"
            )
            message.show_at(placement)
            self._track(message)
        self.result.setText("已连续显示三条，关闭其中一条可检查自动补位。")

    def _track(self, message):
        self._serial += 1
        message.setProperty("feedbackPlaygroundIdentity", self._serial)
        self._messages[self._serial] = message
        message.destroyed.connect(self._released)

    @Slot(QtCore.QObject)
    def _released(self, obj):
        self._messages.pop(obj.property("feedbackPlaygroundIdentity"), None)

    def dismiss_external(self):
        for message in list(self._messages.values()):
            try:
                message.hide()
                message.close()
            except RuntimeError:
                pass

    def clear_messages(self):
        self._refresh.stop()
        self._dispose_preview()
        self.dismiss_external()
        self.result.setText("已清除；点击测试效果或修改参数重新显示。")

    def reset_options(self):
        self.title_input.setText("操作提示")
        self.detail_input.setText("修改内容，立即查看消息效果。")
        self.detail_input.setCursorPosition(0)
        self.tone.setCurrentIndex(1)
        self.position.setCurrentIndex(0)
        self.orientation.setCurrentIndex(0)
        self.width_choice.setCurrentIndex(0)
        self.action_check.setChecked(False)
        self.action_input.setText("查看详情")
        self.closable.setChecked(True)
        self.auto_close.setChecked(True)
        self.unknown.setChecked(False)
        self.task_state.setCurrentIndex(0)
        self.progress.setValue(35)
        self._custom_strip_color = None
        with QtCore.QSignalBlocker(self.color_picker):
            self.color_picker.set_color("#009faa")
        self.advanced.set_expanded(False)
        self.schedule_preview()

    def _change_section(self, key):
        self._section = key
        self._refresh.stop()
        self.dismiss_external()
        for route, page in (
            ("playground", self.editor),
            ("embedded", self.embedded_page),
            ("dialogs", self.dialog_page),
        ):
            page.setVisible(key == route)
        if key == "playground":
            self._refresh.start(0)
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= 720
        self.workspace.setDirection(
            QtWidgets.QBoxLayout.Direction.LeftToRight
            if wide
            else QtWidgets.QBoxLayout.Direction.TopToBottom
        )
        if wide:
            self.inspector.setFixedWidth(280)
        else:
            self.inspector.setMinimumWidth(0)
            self.inspector.setMaximumWidth(16777215)
        self.inspector.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed if wide else QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.schedule_preview()

    def showEvent(self, event):
        super().showEvent(event)
        if self._section == "playground":
            self._refresh.start(0)

    def hideEvent(self, event):
        self._refresh.stop()
        self.dismiss_external()
        self._dispose_preview()
        super().hideEvent(event)

    def _apply_theme(self):
        dark = theme.mode.value == "dark"
        tokens = theme.tokens
        accent = QtGui.QColor(tokens.accent)
        base = QtGui.QColor("#202a32" if dark else "#edf4f7")
        tint = QtGui.QColor.fromRgbF(
            *(a + (b - a) * 0.045 for a, b in zip(base.getRgbF()[:3], accent.getRgbF()[:3]))
        ).name()
        surface = "#282d34" if dark else "#ffffff"
        border = "#3b4650" if dark else "#dce5eb"
        self.setFont(ui_font(14))
        self.setStyleSheet(f"""
QWidget#feedbackPlayground {{background:transparent;}}
QFrame#studioPreviewShell {{background:{tint};border:1px solid {border};border-radius:10px;}}
QFrame#studioCanvas {{background:{"#1c242c" if dark else "#f5f9fb"};border:1px solid {border};border-radius:8px;}}
QFrame#studioSurface {{background:{surface};border:1px solid {border};border-radius:10px;}}
QLabel#studioCaption {{color:{tokens.text_muted};background:transparent;border:none;font-size:12px;}}
QLabel#studioHeading {{color:{tokens.text};background:transparent;border:none;font-size:15px;font-weight:600;}}
QLabel#studioBadge {{color:{tokens.accent};background:transparent;border:none;font-size:12px;}}
""")
