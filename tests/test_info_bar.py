"""Message-bar composition, native layout and task lifecycle regressions."""

import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from fluentpy import (
    Button,
    ColorToast,
    FluentIcon,
    InfoBar,
    LineEdit,
    ProgressBar,
    ProgressInfoBar,
    ProgressToast,
    theme,
)
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class InfoBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(error)
        self.mode = theme.mode
        self.owner = QtWidgets.QWidget()
        self.owner.resize(980, 800)
        self.owner.show()
        self.app.processEvents()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def settle(self, bar):
        bar._reveal.setCurrentTime(bar.SHOW_DURATION)
        bar._stack_motion.setCurrentTime(240)
        self.app.processEvents()

    def assert_fits(self, bar, widget):
        self.assertTrue(
            bar._card_rect().contains(
                QtCore.QRectF(widget.mapTo(bar, QtCore.QPoint()), widget.size())
            )
        )
        if isinstance(widget, QtWidgets.QLabel):
            self.assertGreaterEqual(widget.height(), widget.heightForWidth(widget.width()))

    def test_status_factories_are_owned_child_bars_and_use_distinct_tinted_surfaces(self):
        colors = []
        before = set(self.app.topLevelWidgets())
        for method, tone in (
            (InfoBar.info, "info"),
            (InfoBar.success, "success"),
            (InfoBar.warning, "warning"),
            (InfoBar.error, "error"),
        ):
            bar = method("状态", detail="消息正文", parent=self.owner, timeout_ms=0)
            self.settle(bar)
            self.assertEqual(bar.tone(), tone)
            self.assertIsInstance(bar, ColorToast)
            self.assertFalse(bar.isWindow())
            self.assertIsNone(bar.windowHandle())
            self.assertEqual(bar._placement, "top-center")
            colors.append(bar.background_color().name())
            bar.hide()
        self.assertEqual(len(set(colors)), 4)
        self.assertEqual(set(self.app.topLevelWidgets()), before)

    def test_horizontal_and_vertical_text_geometry_and_long_content_remain_inside(self):
        bar = InfoBar("保存完成", "修改已写入本地文件。", self.owner, card_width=640)
        bar.show_at()
        self.settle(bar)
        title = bar._title.mapTo(bar, QtCore.QPoint())
        body = bar._detail.mapTo(bar, QtCore.QPoint())
        self.assertGreater(body.x(), title.x())
        self.assertLess(abs(body.y() - title.y()), 12)
        bar.set_orientation("vertical")
        self.app.processEvents()
        self.assertGreater(
            bar._detail.mapTo(bar, QtCore.QPoint()).y(), bar._title.mapTo(bar, QtCore.QPoint()).y()
        )
        bar.set_detail("这是需要换行的消息内容。" * 6)
        bar.set_action("立即重试", close_on_action=False)
        for orientation in ("horizontal", "vertical"):
            bar.set_orientation(orientation)
            for width in (240, 241, 300, 340, 420, 640):
                bar.set_card_width(width)
                self.app.processEvents()
                for widget in (bar._title, bar._detail, bar.action_button, bar.close_button):
                    self.assert_fits(bar, widget)

    def test_action_text_callback_and_extra_native_controls_share_one_container(self):
        calls = []
        bar = InfoBar(
            "操作提示",
            "正文",
            self.owner,
            action_text="打开目录",
            action_callback=lambda: calls.append(1),
            close_on_action=False,
        )
        editor = LineEdit("备注", bar.content_widget)
        bar.content_layout.addWidget(editor)
        cancel = Button("取消", bar.content_widget)
        cancel.clicked.connect(bar.close)
        bar.content_layout.addWidget(cancel)
        bar.show_at()
        self.settle(bar)
        self.assertIs(bar.content_layout, bar.content_widget.layout())
        self.assertIsInstance(bar.action_button, Button)
        for widget in (editor, cancel, bar.action_button):
            self.assert_fits(bar, widget)
        bar.action_button.click()
        self.assertEqual(calls, [1])
        self.assertFalse(bar._closing)
        cancel.click()
        self.assertTrue(bar._closing)

    def test_closable_can_be_changed_without_disabling_programmatic_close(self):
        bar = InfoBar("固定消息", "由应用关闭", self.owner, closable=False)
        bar.show_at()
        self.settle(bar)
        self.assertFalse(bar.is_closable())
        self.assertTrue(bar.close_button.isHidden())
        bar.set_closable(True)
        self.app.processEvents()
        self.assertTrue(bar.close_button.isVisible())
        closed = []
        bar.closed.connect(lambda: closed.append(1))
        bar.close()
        bar.close()
        bar._reveal.setCurrentTime(bar.HIDE_DURATION)
        self.assertEqual(closed, [1])
        self.assertFalse(bar.isVisible())

    def test_inline_layout_keeps_its_position_while_fading_and_can_be_reused(self):
        layout = QtWidgets.QVBoxLayout(self.owner)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addWidget(QtWidgets.QLabel("页面内容"))
        bar = InfoBar("嵌入消息", "内联内容", self.owner)
        layout.addWidget(bar)
        layout.addStretch()
        bar.show()
        self.app.processEvents()
        before = bar.pos()
        self.assertIsNone(bar._stack)
        self.assertIsNone(bar._placement)
        bar.set_timeout(0)
        bar.close()
        bar._reveal.setCurrentTime(80)
        self.assertEqual(bar.pos(), before)
        bar._reveal.setCurrentTime(bar.HIDE_DURATION)
        bar.show()
        self.app.processEvents()
        self.assertFalse(bar._closing)
        self.assertEqual(bar._opacity.opacity(), 1.0)
        self.assertIsNone(bar._stack)
        self.assert_fits(bar, bar._detail)

    def test_custom_background_pair_theme_override_and_validation_are_atomic(self):
        bar = InfoBar(
            "自定义",
            "正文",
            self.owner,
            icon=FluentIcon.CODE,
            background="#f0f1fc",
            dark_background="#303048",
        )
        theme.set_mode("light")
        bar.show_at()
        self.settle(bar)
        self.assertEqual(bar.background_color().name(), "#f0f1fc")
        theme.set_mode("dark")
        bar._background_motion.setCurrentTime(180)
        self.assertEqual(bar.background_color().name(), "#303048")
        copy = bar.background_color()
        copy.setRed(255)
        self.assertEqual(bar.background_color().name(), "#303048")
        with self.assertRaises(ValueError):
            bar.set_background("#eeeeee", "invalid")
        self.assertEqual(bar.background_color().name(), "#303048")
        bar.set_background()
        self.assertNotEqual(bar.background_color().name(), "#303048")
        bar.set_icon(QtGui.QIcon())
        self.assertIsInstance(bar._status_icon.source, QtGui.QIcon)
        bar.set_icon(None)
        self.assertIsNone(bar._status_icon.source)

    def test_mixed_stacks_share_existing_manager_and_resize_with_owner(self):
        for placement in InfoBar.PLACEMENTS:
            bar = InfoBar.notify(
                "消息条", detail="正文", parent=self.owner, placement=placement, timeout_ms=0
            )
            toast = ProgressToast.start("已有进度吐司", parent=self.owner, placement=placement)
            self.settle(bar)
            self.settle(toast)
            self.assertIs(bar._stack, toast._stack)
            self.assertFalse(bar.geometry().intersects(toast.geometry().adjusted(14, 14, -14, -14)))
            self.owner.resize(720, 700)
            self.app.processEvents()
            self.assertTrue(self.owner.rect().contains(bar.geometry()))
            bar.hide()
            toast.hide()
        self.owner.hide()

    def test_timeout_starts_after_entry_and_pauses_on_hover(self):
        bar = InfoBar.notify("消息", parent=self.owner, timeout_ms=60)
        self.assertFalse(bar._timeout.isActive())
        self.settle(bar)
        self.assertTrue(bar._timeout.isActive())
        self.app.sendEvent(
            bar, QtGui.QEnterEvent(QtCore.QPointF(), QtCore.QPointF(), QtCore.QPointF())
        )
        QTest.qWait(75)
        self.assertTrue(bar.isVisible())
        self.assertFalse(bar._timeout.isActive())
        self.app.sendEvent(bar, QtCore.QEvent(QtCore.QEvent.Type.Leave))
        QTest.qWait(60 + bar.HIDE_DURATION + 30)

    def test_invalid_options_do_not_create_visible_orphan_windows(self):
        for options in (
            {"orientation": "diagonal"},
            {"closable": 1},
            {"icon": 7},
            {"background": "invalid"},
            {"dark_background": "#202020"},
            {"placement": "center"},
        ):
            with self.subTest(options=options), self.assertRaises((ValueError, TypeError)):
                InfoBar.notify("消息", parent=self.owner, **options)
        self.assertEqual({w for w in self.app.topLevelWidgets() if w.isVisible()}, {self.owner})

    def test_progress_uses_existing_native_bar_and_smoothly_commits_values(self):
        task = ProgressInfoBar.start(
            "导出", detail="准备文件", parent=self.owner, indeterminate=True
        )
        self.settle(task)
        self.assertIsInstance(task.progress_bar, ProgressBar)
        self.assertTrue(task.progress_bar.isHidden())
        self.assertEqual(task._activity.state(), QtCore.QAbstractAnimation.State.Running)
        changes = []
        task.progressChanged.connect(changes.append)
        task.set_progress(42.5)
        self.assertFalse(task.is_indeterminate())
        self.assertTrue(task.progress_bar.isVisible())
        task._progress_motion.setCurrentTime(110)
        self.assertGreater(task.progress_bar.value(), 0)
        self.assertLess(task.progress_bar.value(), 425)
        task._progress_motion.setCurrentTime(220)
        self.assertEqual(task.progress_bar.value(), 425)
        self.assertEqual(changes, [42.5])
        task.set_progress(65)
        task.hide()
        task.show_at()
        self.settle(task)
        self.assertEqual(task.progress_bar.value(), 650)

    def test_task_completion_emits_once_preserves_custom_content_and_ignores_late_updates(self):
        task = ProgressInfoBar("导出", "准备文件", self.owner, indeterminate=True)
        button = Button("打开输出目录", task.content_widget)
        task.content_layout.addWidget(button)
        task.show_at()
        self.settle(task)
        events = []
        task.finished.connect(events.append)
        task.finish("导出完成", timeout_ms=0)
        task._progress_motion.setCurrentTime(220)
        self.assertEqual(task.state(), "success")
        self.assertEqual(task.title(), "导出完成")
        self.assertEqual(task.value(), 100.0)
        self.assertEqual(task.progress_bar.value(), 1000)
        self.assertEqual(events, [True])
        self.assertTrue(button.isVisible())
        self.assertEqual(task._activity.state(), QtCore.QAbstractAnimation.State.Stopped)
        task.set_progress(3)
        task.fail()
        self.assertEqual(task.value(), 100.0)
        self.assertEqual(events, [True])
        self.assertFalse(task._timeout.isActive())

    def test_task_failure_preserves_progress_and_custom_icon_can_be_reset(self):
        task = ProgressInfoBar.start("导出", parent=self.owner, icon=FluentIcon.FOLDER)
        self.settle(task)
        self.assertTrue(task._task_custom_icon)
        self.assertTrue(task._status_icon.isVisible())
        task.set_icon(None)
        self.app.processEvents()
        self.assertTrue(task._task_icon.isVisible())
        task.set_progress(36)
        task._progress_motion.setCurrentTime(220)
        task.fail("写入失败")
        self.assertEqual(task.value(), 36.0)
        self.assertEqual(task.progress_bar.value(), 360)
        self.assertEqual(task.tone(), "error")
        self.assertEqual(task._task_icon.state, "error")
        self.assertFalse(task._timeout.isActive())
        theme.toggle()
        self.assertIn(task.color().name(), task.progress_bar.styleSheet())

    def test_task_invalid_progress_and_completion_parameters_preserve_state(self):
        task = ProgressInfoBar("导出", parent=self.owner)
        for value in (float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                task.set_progress(value)
        with self.assertRaises(ValueError):
            task.finish(timeout_ms=-1)
        with self.assertRaises(TypeError):
            task.finish(7)
        self.assertEqual(task.state(), "running")
        self.assertEqual(task.value(), 0.0)

    def test_demo_is_idle_and_can_embed_editable_actions_and_drive_a_task(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
        try:
            from info_bar import InfoBarExamples

            demo = InfoBarExamples(self.owner)
            demo.resize(650, 600)
            demo.show()
            self.app.processEvents()
            self.assertEqual(demo._messages, {})
            demo.position.setCurrentIndex(6)
            demo.action_check.setChecked(True)
            demo.action_text_input.setText("重新打开")
            bar = demo.show_message("success")
            self.app.processEvents()
            self.assertIsNone(bar._stack)
            self.assertEqual(bar.action_button.text(), "重新打开")
            bar.action_button.click()
            self.assertIn("重新打开", demo.result.text())
            task = demo.start_task()
            self.app.processEvents()
            demo.advance_task()
            self.assertEqual(task.value(), 65.0)
            demo.auto_close.setChecked(False)
            demo.finish_task()
            self.assertEqual(task.state(), "success")
            demo.hide()
            task._reveal.setCurrentTime(task.HIDE_DURATION)
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
