"""Interactive task notifications. Run: python examples/progress_toast.py."""

from __future__ import annotations

import argparse
from importlib import resources
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import AccentButton, Button, ComboBox, ProgressToast, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, Slot
from fluentpy.theme.fonts import ui_font


class ProgressToastExamples(QtWidgets.QWidget):
    """Real library widgets; QTimeLine only simulates a task for the demo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = {}
        self._serial = 0
        self._last_placement = "bottom-right"
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        modes = QtWidgets.QHBoxLayout()
        modes.addWidget(QtWidgets.QLabel("任务类型", self))
        self.mode = ComboBox(self)
        self.mode.addItems(["显示下载进度", "未知总量，等待完成"])
        self.mode.setMinimumWidth(210)
        modes.addWidget(self.mode)
        modes.addStretch()
        layout.addLayout(modes)
        corners = QtWidgets.QGridLayout()
        for index, (placement, caption) in enumerate((("top-left", "左上角"), ("top-center", "顶部居中"), ("top-right", "右上角"),
                                   ("bottom-left", "左下角"), ("bottom-center", "底部居中"), ("bottom-right", "右下角"))):
            button = Button(caption, self)
            button.clicked.connect(lambda _checked=False, p=placement: self.start_task(p))
            corners.addWidget(button,index//3,index%3)
        layout.addLayout(corners)
        self.caption = QtWidgets.QLabel("可重复点击：底部向上叠放，顶部向下叠放；关闭后自动补位。", self)
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        actions = QtWidgets.QHBoxLayout()
        repeat = Button("连发三条",self)
        repeat.clicked.connect(self.start_batch)
        actions.addWidget(repeat)
        failure = Button("模拟失败", self)
        failure.clicked.connect(self.fail_tasks)
        dismiss = Button("关闭全部", self)
        dismiss.clicked.connect(self.dismiss_all)
        actions.addWidget(failure)
        actions.addWidget(dismiss)
        actions.addStretch()
        layout.addLayout(actions)

    def start_task(self, placement):
        self._last_placement=placement
        self._begin(placement,self.mode.currentIndex()==1)

    def start_batch(self):
        for _ in range(3):self.start_task(self._last_placement)

    def _begin(self, placement, indeterminate):
        toast = ProgressToast.start("正在下载文件，请稍候…", parent=self.window(),
                                    placement=placement, indeterminate=indeterminate,severity="warning")
        self._serial += 1
        toast.setProperty("demoPlacement", placement)
        toast.setProperty("demoIdentity", self._serial)
        timeline = QtCore.QTimeLine(4200, toast)
        timeline.setEasingCurve(QtCore.QEasingCurve.Type.Linear)
        timeline.setUpdateInterval(40)
        timeline.setFrameRange(0, 100)
        if not indeterminate:
            timeline.frameChanged.connect(toast.set_progress)
        timeline.finished.connect(lambda: toast.finish("下载完成", timeout_ms=2000))
        self._tasks[self._serial] = (toast, timeline)

        toast.destroyed.connect(self._task_released)
        timeline.start()
        self.caption.setText("此处为进度演示，不实际下载文件。鼠标移到提示上可暂停自动收起。")

    @Slot(QtCore.QObject)
    def _task_released(self, destroyed):
        # Qt emits destroyed() with a QObject wrapper after the subclass has
        # been torn down; wrapper identity is not reliable at this point.
        self._tasks.pop(destroyed.property("demoIdentity"), None)

    def fail_tasks(self):
        for toast, timeline in list(self._tasks.values()):
            timeline.stop()
            toast.fail("下载失败，请重试", timeout_ms=0)

    def dismiss_all(self):
        for toast, timeline in list(self._tasks.values()):
            timeline.stop()
            toast.close()

    def hideEvent(self, event):
        self.dismiss_all()
        super().hideEvent(event)


class ProgressToastDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("progressToastDemo")
        self.setWindowTitle("FluentPy · 任务进度提示")
        self.setWindowIcon(QtGui.QIcon(str(resources.files('fluentpy.assets').joinpath('brand/fluentpy.svg'))))
        self.resize(900, 600)
        self.setMinimumSize(640, 460)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 30)
        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("任务进度提示", self)
        title.setObjectName("demoTitle")
        top.addStretch()
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)
        root.addStretch()
        note = QtWidgets.QLabel("多条任务可同时显示，关闭后自动补位。", self)
        note.setObjectName("demoSubtitle")
        root.addWidget(note)
        root.addSpacing(12)
        self.examples = ProgressToastExamples(self)
        root.addWidget(self.examples)
        appearance = QtWidgets.QHBoxLayout()
        appearance.addStretch()
        appearance.addWidget(QtWidgets.QLabel("深色", self))
        toggle = ToggleSwitch(self)
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        appearance.addWidget(toggle)
        root.addLayout(appearance)
        root.addStretch()
        footer = QtWidgets.QLabel("四角堆叠 · 平滑补位 · 单段循环条 · 完成／失败 · 悬停暂停", self)
        footer.setObjectName("demoFooter")
        footer.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)
        self._previews = []
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def show_preview(self):
        for placement, title, state in (
            ("top-left", "正在下载文件，请稍候…", "progress"),
            ("top-right", "正在准备文件…", "indeterminate"),
            ("bottom-left", "下载完成", "success"),
            ("bottom-right", "连接中断，请重试", "error"),
        ):
            toast = ProgressToast(title, parent=self, indeterminate=state == "indeterminate")
            toast.show_at(placement)
            toast.set_progress(58 if state == "progress" else 32)
            if state == "indeterminate":
                toast.set_indeterminate(True)
            elif state == "success":
                toast.finish(timeout_ms=0)
            elif state == "error":
                toast.fail(timeout_ms=0)
            self._previews.append(toast)

    def _apply_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f'QWidget#progressToastDemo {{ background: {theme.tokens.background}; }}'
            f'QLabel {{ color: {theme.tokens.text}; background: transparent; font-size: 14px; }}'
            f'QLabel#demoTitle {{ font-size: 22px; font-weight: 600; }}'
            f'QLabel#demoSubtitle {{ font-size: 20px; }}'
            f'QLabel#demoFooter {{ color: {theme.tokens.text_muted}; font-size: 12px; }}'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot")
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = ProgressToastDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()

    def capture():
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(args.screenshot.resolve())):
            raise RuntimeError("Could not save the progress notification preview")
        if args.quit_after_screenshot:
            window.close()
            app.quit()

    if args.screenshot:
        window.show_preview()
        QtCore.QTimer.singleShot(ProgressToast.SHOW_DURATION + 80, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
