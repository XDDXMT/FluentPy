"""Interactive task notifications. Run: python examples/progress_toast.py."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import AccentButton, Button, ComboBox, ProgressToast, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtWidgets, Slot
from fluentpy.theme.fonts import ui_font


class ProgressToastExamples(QtWidgets.QWidget):
    """Real library widgets; QTimeLine only simulates a task for the demo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = {}
        self._identities = {}
        self._serial = 0
        self._pending = {}
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
        corners = QtWidgets.QHBoxLayout()
        for placement, caption in (("top-left", "左上角"), ("top-right", "右上角"),
                                   ("bottom-left", "左下角"), ("bottom-right", "右下角")):
            button = Button(caption, self)
            button.clicked.connect(lambda _checked=False, p=placement: self.start_task(p))
            corners.addWidget(button)
        layout.addLayout(corners)
        self.caption = QtWidgets.QLabel("选择一个位置，体验进度更新 → 完成 → 自动收起。", self)
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        actions = QtWidgets.QHBoxLayout()
        failure = Button("模拟失败", self)
        failure.clicked.connect(self.fail_tasks)
        dismiss = Button("关闭全部", self)
        dismiss.clicked.connect(self.dismiss_all)
        actions.addWidget(failure)
        actions.addWidget(dismiss)
        actions.addStretch()
        layout.addLayout(actions)

    def start_task(self, placement):
        pending = self._pending.pop(placement, None)
        if pending is not None:
            pending.stop()
            pending.deleteLater()
        current = self._tasks.get(placement)
        indeterminate = self.mode.currentIndex() == 1
        if current is not None:
            toast, timeline = current
            timeline.stop()
            toast.close()
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            self._pending[placement] = timer

            def replace():
                if self._pending.pop(placement, None) is timer:
                    self._begin(placement, indeterminate)
                timer.deleteLater()

            timer.timeout.connect(replace)
            timer.start(ProgressToast.HIDE_DURATION + 20)
        else:
            self._begin(placement, indeterminate)

    def _begin(self, placement, indeterminate):
        toast = ProgressToast.start("正在下载文件，请稍候…", parent=self.window(),
                                    placement=placement, indeterminate=indeterminate)
        self._serial += 1
        toast.setProperty("demoPlacement", placement)
        toast.setProperty("demoIdentity", self._serial)
        self._identities[placement] = self._serial
        timeline = QtCore.QTimeLine(4200, toast)
        timeline.setEasingCurve(QtCore.QEasingCurve.Type.Linear)
        timeline.setUpdateInterval(40)
        timeline.setFrameRange(0, 100)
        if not indeterminate:
            timeline.frameChanged.connect(toast.set_progress)
        timeline.finished.connect(lambda: toast.finish("下载完成", timeout_ms=2000))
        self._tasks[placement] = (toast, timeline)

        toast.destroyed.connect(self._task_released)
        timeline.start()
        self.caption.setText("此处为进度演示，不实际下载文件。鼠标移到提示上可暂停自动收起。")

    @Slot(QtCore.QObject)
    def _task_released(self, destroyed):
        # Qt emits destroyed() with a QObject wrapper after the subclass has
        # been torn down; wrapper identity is not reliable at this point.
        placement = destroyed.property("demoPlacement")
        if self._identities.get(placement) == destroyed.property("demoIdentity"):
            self._tasks.pop(placement, None)
            self._identities.pop(placement, None)

    def fail_tasks(self):
        for toast, timeline in list(self._tasks.values()):
            timeline.stop()
            toast.fail("下载失败，请重试", timeout_ms=0)

    def dismiss_all(self):
        for timer in self._pending.values():
            timer.stop()
            timer.deleteLater()
        self._pending.clear()
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
        note = QtWidgets.QLabel("一张小卡片，接住任务的整个过程。", self)
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
        footer = QtWidgets.QLabel("平滑进度 · 状态切换 · 四角定位 · 悬停暂停 · 明暗主题", self)
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
