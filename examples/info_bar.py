"""InfoBar and ProgressInfoBar using the existing FluentPy controls."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fluentpy import (
    Button,
    CheckBox,
    ComboBox,
    FluentIcon,
    FluentScrollBar,
    HeaderCardWidget,
    InfoBar,
    LineEdit,
    ProgressInfoBar,
    ToggleSwitch,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets, Slot
from fluentpy.theme.fonts import ui_font

POSITIONS = (
    ("top-center", "顶部居中"),
    ("bottom-center", "底部居中"),
    ("top-left", "左上角"),
    ("top-right", "右上角"),
    ("bottom-left", "左下角"),
    ("bottom-right", "右下角"),
    (None, "嵌入下方布局"),
)


class EmbeddedInfoBarExamples(QtWidgets.QWidget):
    """Always-visible examples that participate in the page's normal layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("embeddedInfoBarExamples")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.notice = InfoBar(
            "页面内消息", "这条消息随页面滚动，关闭后下方内容会自动上移。", self, tone="success"
        )
        root.addWidget(self.notice)
        self.form = InfoBar(
            "提交一条备注", "填写下方内容，再点击提交查看表单反馈。", self, orientation="vertical"
        )
        form_row = QtWidgets.QHBoxLayout()
        form_row.setSpacing(8)
        self.note_input = LineEdit("输入示例备注", self.form.content_widget)
        self.note_input.setAccessibleName("嵌入消息示例备注")
        self.submit_button = Button("提交备注", self.form.content_widget)
        self.submit_button.clicked.connect(self.submit_note)
        self.note_input.returnPressed.connect(self.submit_note)
        form_row.addWidget(self.note_input, 1)
        form_row.addWidget(self.submit_button)
        self.form.content_layout.addLayout(form_row)
        root.addWidget(self.form)
        self.task_host = QtWidgets.QWidget(self)
        self.task_layout = QtWidgets.QVBoxLayout(self.task_host)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.setSpacing(0)
        root.addWidget(self.task_host)
        self.task = None
        self.reset_task()
        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(16, 0, 16, 0)
        self.result = QtWidgets.QLabel("这些消息直接占据页面空间；可关闭后观察补位。")
        self.result.setWordWrap(True)
        footer.addWidget(self.result, 1)
        self.restore_button = Button("恢复全部示例")
        self.restore_button.clicked.connect(self.restore_examples)
        footer.addWidget(self.restore_button)
        root.addLayout(footer)
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def submit_note(self):
        text = self.note_input.text().strip()
        if text:
            self.form.set_tone("success")
            self.form.set_title("备注已提交")
            self.form.set_detail(text)
            self.result.setText("已提交示例备注。")
        else:
            self.form.set_tone("warning")
            self.form.set_title("请先填写备注")
            self.form.set_detail("输入框不能为空，请填写内容后重新提交。")
            self.result.setText("尚未提交：备注为空。")
            self.note_input.setFocus()

    def reset_task(self):
        if self.task is not None:
            self.task.hide()
            self.task.close()
            self.task_layout.removeWidget(self.task)
            self.task.deleteLater()
        self.task = ProgressInfoBar(
            "文件处理", "示例进度为 35%，可手动推进或完成。", self.task_host, orientation="vertical"
        )
        self.task.set_progress(35)
        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(8)
        self.advance_button = Button("推进进度", self.task.content_widget)
        self.advance_button.clicked.connect(self.advance_task)
        self.finish_button = Button("完成", self.task.content_widget)
        self.finish_button.clicked.connect(self.finish_task)
        self.reset_button = Button("重新开始", self.task.content_widget)
        self.reset_button.clicked.connect(self.reset_task)
        controls.addWidget(self.advance_button)
        controls.addWidget(self.finish_button)
        controls.addWidget(self.reset_button)
        controls.addStretch()
        self.task.content_layout.addLayout(controls)
        self.task_layout.addWidget(self.task)

    def advance_task(self):
        if self.task.state() != "running":
            return
        value = min(100, self.task.value() + 20)
        self.task.set_progress(value)
        self.task.set_detail(f"已处理 {round(value)}%，进度条直接显示在页面布局中。")
        if value == 100:
            self.finish_task()

    def finish_task(self):
        if self.task.state() != "running":
            return
        self.task.set_detail("示例处理完成，消息保持显示；可点击重新开始。")
        self.task.finish("处理完成", timeout_ms=0)
        self.advance_button.setEnabled(False)
        self.finish_button.setEnabled(False)

    def restore_examples(self):
        self.notice.hide()
        self.notice.show()
        self.note_input.clear()
        self.form.set_tone("info")
        self.form.set_title("提交一条备注")
        self.form.set_detail("填写下方内容，再点击提交查看表单反馈。")
        self.form.hide()
        self.form.show()
        self.reset_task()
        self.result.setText("已恢复所有嵌入示例。")

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#embeddedInfoBarExamples {{background:transparent;}} QWidget#embeddedInfoBarExamples QLabel {{color:{theme.tokens.text};background:transparent;}}"
        )


class InfoBarExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("infoBarExamples")
        self._messages = {}
        self._serial = 0
        self._current_task = None
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.position = ComboBox()
        self.position.addItems([caption for _, caption in POSITIONS])
        self.orientation = ComboBox()
        self.orientation.addItems(["横向排列", "纵向排列"])
        self.width_combo = ComboBox()
        self.width_combo.addItems(["自动宽度", "320", "480", "640"])
        for row, (caption, widget) in enumerate(
            (
                ("显示位置", self.position),
                ("内容方向", self.orientation),
                ("卡片宽度", self.width_combo),
            )
        ):
            grid.addWidget(QtWidgets.QLabel(caption), row, 0)
            grid.addWidget(widget, row, 1)
        self.closable = CheckBox("显示关闭按钮")
        self.closable.setChecked(True)
        self.auto_close = CheckBox("普通消息自动关闭")
        self.auto_close.setChecked(True)
        grid.addWidget(self.closable, 0, 2)
        grid.addWidget(self.auto_close, 1, 2)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)
        self.title_input = LineEdit("消息标题")
        self.title_input.setText("操作提示")
        self.title_input.setAccessibleName("消息标题")
        self.detail_input = LineEdit("消息正文")
        self.detail_input.setText("设置已保存，可以继续编辑。")
        self.detail_input.setAccessibleName("消息正文")
        root.addWidget(self.title_input)
        root.addWidget(self.detail_input)
        action = QtWidgets.QHBoxLayout()
        self.action_check = CheckBox("显示操作按钮")
        self.action_text_input = LineEdit("按钮文字")
        self.action_text_input.setText("撤销")
        self.action_text_input.setEnabled(False)
        self.action_text_input.setAccessibleName("消息条按钮文字")
        self.action_check.toggled.connect(self.action_text_input.setEnabled)
        action.addWidget(self.action_check)
        action.addWidget(self.action_text_input, 1)
        root.addLayout(action)
        buttons = QtWidgets.QHBoxLayout()
        self.tone_buttons = {}
        for tone, caption in (
            ("info", "信息"),
            ("success", "成功"),
            ("warning", "警告"),
            ("error", "失败"),
            ("accent", "自定义"),
        ):
            button = Button(caption)
            button.clicked.connect(lambda _checked=False, t=tone: self.show_message(t))
            buttons.addWidget(button)
            self.tone_buttons[tone] = button
        root.addLayout(buttons)
        tasks = QtWidgets.QGridLayout()
        tasks.setSpacing(8)
        for index, (caption, method) in enumerate(
            (
                ("开始任务", self.start_task),
                ("更新到 65%", self.advance_task),
                ("完成", self.finish_task),
                ("失败", self.fail_task),
                ("关闭全部", self.dismiss_all),
            )
        ):
            button = Button(caption)
            button.clicked.connect(method)
            tasks.addWidget(button, index // 3, index % 3)
        root.addLayout(tasks)
        self.result = QtWidgets.QLabel("消息条可嵌入布局，也可与现有吐司共用窗口内排列。")
        self.result.setWordWrap(True)
        root.addWidget(self.result)
        self.inline_host = QtWidgets.QWidget()
        self.inline_layout = QtWidgets.QVBoxLayout(self.inline_host)
        self.inline_layout.setContentsMargins(0, 0, 0, 0)
        self.inline_layout.setSpacing(0)
        root.addWidget(self.inline_host)
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def _options(self):
        text = self.action_text_input.text() if self.action_check.isChecked() else ""
        return dict(
            orientation=("horizontal", "vertical")[self.orientation.currentIndex()],
            closable=self.closable.isChecked(),
            card_width=(None, 320, 480, 640)[self.width_combo.currentIndex()],
            action_text=text,
            action_callback=(lambda: self.result.setText(f"已触发“{text}”操作。"))
            if text
            else None,
        )

    def _create(self, cls, title, detail, **options):
        placement = POSITIONS[self.position.currentIndex()][0]
        timeout = 4000 if cls is InfoBar and self.auto_close.isChecked() else 0
        if placement is None:
            bar = cls(title, detail, self.inline_host, **options)
            bar.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
            self.inline_layout.addWidget(bar)
            bar.set_timeout(timeout)
            bar.show()
        else:
            bar = cls.notify(
                title,
                detail=detail,
                parent=self.window(),
                placement=placement,
                timeout_ms=timeout,
                **options,
            )
        self._serial += 1
        bar.setProperty("infoBarDemoIdentity", self._serial)
        self._messages[self._serial] = bar
        bar.destroyed.connect(self._released)
        return bar

    @Slot(QtCore.QObject)
    def _released(self, obj):
        self._messages.pop(obj.property("infoBarDemoIdentity"), None)

    def show_message(self, tone="info"):
        options = self._options()
        options["tone"] = tone
        if tone == "accent":
            options.update(icon=FluentIcon.CODE, background="#f0f1fc", dark_background="#303048")
        bar = self._create(InfoBar, self.title_input.text(), self.detail_input.text(), **options)
        self.result.setText("已显示消息条；可切换方向、按钮文字、位置和明暗主题。")
        return bar

    def start_task(self):
        try:
            if (
                self._current_task is not None
                and self._current_task.isVisible()
                and self._current_task.state() == "running"
            ):
                return self._current_task
        except RuntimeError:
            pass
        self._current_task = self._create(
            ProgressInfoBar,
            "正在导出",
            "正在准备文件，请稍候…",
            indeterminate=True,
            **self._options(),
        )
        self.result.setText("任务仅演示状态显示；点击更新进度、完成或失败。")
        return self._current_task

    def _running_task(self):
        try:
            if (
                self._current_task is not None
                and self._current_task.isVisible()
                and self._current_task.state() == "running"
            ):
                return self._current_task
        except RuntimeError:
            self._current_task = None
        self.result.setText("请先开始一个任务。")
        return None

    def advance_task(self):
        task = self._running_task()
        if task is not None:
            task.set_progress(65)
            task.set_detail("已处理 65%，正在写入剩余文件。")

    def finish_task(self):
        task = self._running_task()
        if task is not None:
            task.set_detail("文件已保存，可继续操作。")
            task.finish("导出完成", timeout_ms=1800 if self.auto_close.isChecked() else 0)

    def fail_task(self):
        task = self._running_task()
        if task is not None:
            task.set_detail("请检查输出位置，然后重新开始。")
            task.fail("导出失败")

    def dismiss_all(self):
        for bar in list(self._messages.values()):
            bar.close()

    def hideEvent(self, event):
        self.dismiss_all()
        super().hideEvent(event)

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#infoBarExamples {{background:transparent;}} QWidget#infoBarExamples QLabel {{color:{theme.tokens.text};background:transparent;}}"
        )


class InfoBarDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("infoBarDemo")
        self.setWindowTitle("FluentPy · 消息条")
        self.resize(820, 820)
        self.setMinimumSize(560, 480)
        self.setWindowIcon(
            QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
        )
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("消息条")
        title.setObjectName("infoBarTitle")
        header.addWidget(title, 1)
        header.addWidget(QtWidgets.QLabel("深色模式"))
        toggle = ToggleSwitch()
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        header.addWidget(toggle)
        root.addLayout(header)
        scroll = QtWidgets.QScrollArea()
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBar(FluentScrollBar(parent=scroll))
        content = QtWidgets.QWidget()
        body = QtWidgets.QVBoxLayout(content)
        body.setContentsMargins(0, 0, 0, 0)
        panel = HeaderCardWidget("普通消息与任务状态")
        self.examples = InfoBarExamples()
        panel.body_layout.addWidget(self.examples)
        body.addWidget(panel)
        body.addStretch()
        scroll.setWidget(content)
        content.setAutoFillBackground(False)
        root.addWidget(scroll, 1)
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#infoBarDemo,QScrollArea {{background:{theme.tokens.background};border:none;}} QLabel {{color:{theme.tokens.text};background:transparent;}} QLabel#infoBarTitle {{font-size:24px;font-weight:600;}}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setFont(ui_font(14))
    window = InfoBarDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    if args.screenshot:

        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.screenshot))
            if args.quit_after_screenshot:
                app.quit()

        QtCore.QTimer.singleShot(250, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
