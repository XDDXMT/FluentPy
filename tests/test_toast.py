"""Toast geometry and lifetime must not create transient native child windows."""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import gc
import sys
import unittest
from unittest.mock import patch

from fluentpy import Toast, theme
from fluentpy.qt import QtCore, QtWidgets

if "PySide6" in QtCore.__name__:
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class _ObservedToast(Toast):
    def __init__(self, *args, **kwargs):
        self.show_calls = 0
        self.shown_geometry = []
        super().__init__(*args, **kwargs)

    def show(self):
        self.show_calls += 1
        super().show()

    def showEvent(self, event):
        self.shown_geometry.append(QtCore.QRect(self.geometry()))
        super().showEvent(event)


class _TopLevelLabelShows(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.events = []

    def eventFilter(self, watched, event):
        if (
            event.type() == QtCore.QEvent.Type.Show
            and isinstance(watched, QtWidgets.QLabel)
            and watched.isWindow()
        ):
            self.events.append(watched.text())
        return False


class ToastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.original_mode = theme.mode
        self.previous_excepthook = sys.excepthook
        self.errors = []
        sys.excepthook = lambda _type, error, _tb: self.errors.append(error)
        self.parent = QtWidgets.QWidget()
        self.parent.resize(640, 400)
        self.parent.move(-300, -200)
        self.parent.show()
        self.orphans = []
        self.app.processEvents()

    def tearDown(self):
        try:
            for toast in self.orphans:
                toast.close()
                toast.deleteLater()
            if self.parent is not None:
                self.parent.close()
                self.parent.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            theme.set_mode(self.original_mode)
            self.app.processEvents()
        finally:
            sys.excepthook = self.previous_excepthook
        self.assertEqual(self.errors, [])

    def finish_show(self, toast):
        QTest.qWait(Toast.SHOW_DURATION + 40)
        self.assertAlmostEqual(toast._opacity.opacity(), 1.0)
        self.assertEqual(toast.pos(), toast._rest_pos)

    def finish_close(self):
        QTest.qWait(Toast.HIDE_DURATION + 50)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_parented_toast_is_a_hidden_child_without_a_native_tooltip_window(self):
        toast = Toast("已保存", parent=self.parent)
        self.assertIs(toast.parentWidget(), self.parent)
        self.assertFalse(toast.isWindow())
        self.assertEqual(toast.windowType(), QtCore.Qt.WindowType.Widget)
        self.assertFalse(toast.isVisible())
        toast.show_at()
        self.app.processEvents()
        self.assertTrue(toast.isVisible())
        self.assertIs(toast.window(), self.parent)
        self.assertNotIn(toast, self.app.topLevelWidgets())
        self.assertIsNone(toast.windowHandle())
        self.assertFalse(toast.testAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow))

    def test_construction_never_shows_and_first_frame_is_already_anchored(self):
        toast = _ObservedToast("保存成功", "本次操作已经完成。", parent=self.parent)
        self.app.processEvents()
        self.assertEqual(toast.show_calls, 0)
        self.assertEqual(toast.shown_geometry, [])
        toast.show_at("bottom-right")
        self.app.processEvents()
        self.assertEqual(toast.show_calls, 1)
        self.assertEqual(len(toast.shown_geometry), 1)
        self.assertTrue(self.parent.rect().contains(toast.shown_geometry[0]))
        self.assertLessEqual(abs(toast.shown_geometry[0].y() - toast._rest_pos.y()), 6)
        self.finish_show(toast)
        self.assertEqual(toast.x() + toast.width(), self.parent.width() - 18)
        self.assertEqual(toast.y() + toast.height(), self.parent.height() - 18)

    def test_constructor_and_show_never_expose_an_orphan_label_window(self):
        monitor = _TopLevelLabelShows()
        self.app.installEventFilter(monitor)
        try:
            control = QtWidgets.QLabel("monitor control")
            control.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            control.show()
            self.app.processEvents()
            self.assertEqual(
                monitor.events,
                ["monitor control"],
                "The global monitor must detect transient orphan-label shows",
            )
            control.close()
            control.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            monitor.events.clear()
            toast = _ObservedToast("已保存", "非空详情必须从构造起就有父控件。", parent=self.parent)
            self.app.processEvents()
            self.assertEqual(toast.show_calls, 0)
            self.assertEqual(monitor.events, [])
            toast.show_at()
            self.app.processEvents()
            self.assertIs(toast._title.parentWidget(), toast)
            self.assertIs(toast._detail.parentWidget(), toast)
            self.assertEqual(monitor.events, [])
        finally:
            self.app.removeEventFilter(monitor)

    def test_all_four_placements_use_parent_local_coordinates(self):
        for placement in ("top-left", "top-right", "bottom-left", "bottom-right"):
            with self.subTest(placement=placement):
                toast = Toast("已保存", parent=self.parent)
                toast.show_at(placement)
                self.finish_show(toast)
                self.assertTrue(self.parent.rect().contains(toast.geometry()))
                if placement.endswith("right"):
                    self.assertEqual(toast.x() + toast.width(), self.parent.width() - 18)
                else:
                    self.assertEqual(toast.x(), 18)
                if placement.startswith("bottom"):
                    self.assertEqual(toast.y() + toast.height(), self.parent.height() - 18)
                else:
                    self.assertEqual(toast.y(), 18)
                toast.close()

    def test_small_parent_keeps_even_long_toasts_within_its_bounds(self):
        for size in ((120, 80), (40, 24), (12, 8)):
            self.parent.resize(*size)
            self.app.processEvents()
            for placement in ("top-left", "top-right", "bottom-left", "bottom-right"):
                with self.subTest(size=size, placement=placement):
                    toast = Toast("很长的操作结果标题" * 8, "详细说明 " * 30, self.parent)
                    toast.show_at(placement)
                    self.assertGreater(toast.width(), 0)
                    self.assertGreater(toast.height(), 0)
                    self.assertTrue(self.parent.rect().contains(toast.geometry()), toast.geometry())
                    toast.close()

    def test_parent_resize_reanchors_without_showing_another_window(self):
        toast = _ObservedToast("已完成", parent=self.parent)
        toast.show_at("bottom-right")
        self.finish_show(toast)
        self.parent.resize(420, 260)
        self.app.processEvents()
        self.assertTrue(self.parent.rect().contains(toast.geometry()))
        self.assertEqual(toast.x() + toast.width(), 402)
        self.assertEqual(toast.y() + toast.height(), 242)
        self.assertEqual(toast.show_calls, 1)
        self.assertEqual(len(toast.shown_geometry), 1)

    def test_closed_toast_stays_closed_during_parent_resize_and_can_be_reused(self):
        toast = _ObservedToast("可再次显示", parent=self.parent)
        toast.show_at("bottom-right")
        self.finish_show(toast)
        toast.close()
        self.finish_close()
        self.parent.resize(360, 180)
        self.app.processEvents()
        self.assertFalse(toast.isVisible())
        self.assertEqual(toast.show_calls, 1)
        toast.show_at("top-left")
        self.finish_show(toast)
        self.assertTrue(toast.isVisible())
        self.assertEqual(toast.pos(), QtCore.QPoint(18, 18))
        self.assertEqual(toast.show_calls, 2)

    def test_success_timeout_deletes_the_toast_and_owned_timer(self):
        toast = Toast.success("自动关闭", parent=self.parent, timeout_ms=10)
        destroyed = []
        toast.destroyed.connect(lambda *_: destroyed.append("toast"))
        timers = toast.findChildren(QtCore.QTimer)
        self.assertEqual(len(timers), 1)
        timers[0].destroyed.connect(lambda *_: destroyed.append("timer"))
        self.assertTrue(toast.testAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose))
        self.assertTrue(toast.isVisible())
        gc.collect()
        QTest.qWait(10 + Toast.HIDE_DURATION + 50)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertCountEqual(destroyed, ["toast", "timer"])

    def test_deleting_parent_cancels_timer_and_disconnects_theme_with_live_wrapper(self):
        toast = Toast.success("稍后关闭", parent=self.parent, timeout_ms=100000)
        destroyed = []
        toast.destroyed.connect(lambda *_: destroyed.append(True))
        self.parent.deleteLater()
        self.parent = None
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
        self.assertEqual(self.errors, [])

    def test_theme_and_chinese_font_remain_live_for_the_child_overlay(self):
        toast = Toast("操作完成", "可以继续编辑。", self.parent)
        toast.show_at("top-right")
        self.finish_show(toast)
        for mode, fill in (("light", "#f8f8f8"), ("dark", "#2b2b2b")):
            theme.set_mode(mode)
            self.app.processEvents()
            self.assertIn("Microsoft YaHei UI", toast.font().families())
            self.assertEqual(toast.font().pixelSize(), theme.tokens.font_size + 2)
            self.assertIn(theme.tokens.text, toast.styleSheet())
            path = toast._card_path()
            bounds = path.boundingRect()
            sample = QtCore.QPointF(bounds.right() - 16, bounds.bottom() - 9)
            self.assertTrue(path.contains(sample))
            image = toast.grab().toImage()
            ratio = image.devicePixelRatio()
            self.assertEqual(
                image.pixelColor(round(sample.x() * ratio), round(sample.y() * ratio)).name(), fill
            )
            self.assertTrue(self.parent.rect().contains(toast.geometry()))
            self.assertFalse(toast.isWindow())

    def test_target_prefers_above_and_falls_below_when_near_top(self):
        target = QtWidgets.QPushButton("创建预约", self.parent)
        target.setGeometry(260, 250, 120, 30)
        target.show()
        toast = Toast("完成", "可以继续操作。", target=target)
        self.assertIs(toast.parentWidget(), self.parent)
        toast.show_at()
        QTest.qWait(40)
        self.assertGreater(toast._opacity.opacity(), 0.0)
        self.assertLess(toast._opacity.opacity(), 1.0)
        self.assertEqual(toast.x(), toast._rest_pos.x())
        self.assertGreater(toast.y() - toast._rest_pos.y(), 0)
        self.assertLessEqual(toast.y() - toast._rest_pos.y(), 6)
        self.finish_show(toast)
        self.app.processEvents()
        self.assertEqual(toast._arrow_edge, "bottom")
        self.assertLess(toast.y() + toast._card_path().boundingRect().bottom(), target.y())
        self.assertEqual(toast.x() + toast._arrow_x, target.geometry().center().x())
        self.assertTrue(self.parent.rect().contains(toast.geometry()))
        target.move(260, 5)
        self.app.processEvents()
        self.assertEqual(toast._arrow_edge, "top")
        self.assertGreater(
            toast.y() + toast._card_path().boundingRect().top(), target.geometry().bottom()
        )
        self.assertTrue(self.parent.rect().contains(toast.geometry()))

    def test_target_and_ancestor_moves_follow_without_showing_another_window(self):
        ancestor = QtWidgets.QWidget(self.parent)
        ancestor.setGeometry(60, 60, 500, 300)
        target = QtWidgets.QPushButton("保存", ancestor)
        target.setGeometry(180, 150, 100, 30)
        ancestor.show()
        target.show()
        toast = _ObservedToast("已保存", target=target)
        toast.show_at()
        self.finish_show(toast)
        self.app.processEvents()
        before = QtCore.QPoint(toast.pos())
        target.move(target.pos() + QtCore.QPoint(10, 5))
        self.app.processEvents()
        self.assertEqual(toast.pos(), before + QtCore.QPoint(10, 5))
        ancestor.move(ancestor.pos() + QtCore.QPoint(20, 10))
        self.app.processEvents()
        self.assertEqual(toast.pos(), before + QtCore.QPoint(30, 15))
        self.assertEqual(toast.show_calls, 1)
        self.assertFalse(toast.isWindow())

    def test_close_button_clears_position_and_deletes_success_toast(self):
        toast = Toast.success("关闭提示", parent=self.parent, timeout_ms=0)
        self.finish_show(toast)
        destroyed = []
        toast.destroyed.connect(lambda *_: destroyed.append(True))
        self.assertEqual(toast.close_button.accessibleName(), "关闭提示")
        QTest.mouseClick(toast.close_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertIsNone(toast._placement)
        self.finish_close()
        self.assertEqual(destroyed, [True])

    def test_zero_timeout_remains_until_user_dismisses_it(self):
        toast = Toast.success("保持显示", detail="等待手动关闭。", parent=self.parent, timeout_ms=0)
        destroyed = []
        toast.destroyed.connect(lambda *_: destroyed.append(True))
        self.finish_show(toast)
        QTest.qWait(50)
        self.assertTrue(toast.isVisible())
        self.assertEqual(destroyed, [])
        self.assertFalse(any(timer.isActive() for timer in toast.findChildren(QtCore.QTimer)))
        QTest.mouseClick(toast.close_button, QtCore.Qt.MouseButton.LeftButton)
        self.finish_close()
        self.assertEqual(destroyed, [True])

    def test_hiding_parent_closes_toast_and_reshowing_does_not_resurrect_it(self):
        toast = Toast("临时提示", parent=self.parent)
        toast.show_at()
        self.finish_show(toast)
        self.parent.hide()
        self.app.processEvents()
        self.assertFalse(toast.isVisible())
        self.assertIsNone(toast._placement)
        self.parent.show()
        QTest.qWait(Toast.SHOW_DURATION + 40)
        self.assertFalse(toast.isVisible())

    def test_minimizing_parent_dismisses_its_toast(self):
        toast = Toast("临时提示", parent=self.parent)
        toast.show_at()
        self.finish_show(toast)
        self.parent.showMinimized()
        self.app.processEvents()
        self.assertFalse(toast.isVisible())
        self.assertIsNone(toast._placement)

    def test_destroyed_target_does_not_leave_invalid_geometry_callbacks(self):
        target = QtWidgets.QPushButton("提交", self.parent)
        target.setGeometry(250, 200, 100, 30)
        target.show()
        toast = Toast("完成", "目标删除后应安全关闭。", target=target)
        toast.show_at()
        self.finish_show(toast)
        target.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertFalse(toast.isVisible())
        self.assertIsNone(toast._placement)
        self.parent.resize(700, 450)
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
        self.assertEqual(self.errors, [])

    def test_entry_has_real_intermediate_opacity_and_motion_and_one_show_event(self):
        toast = _ObservedToast("淡入", parent=self.parent)
        toast.show_at("top-left")
        self.assertEqual(toast._opacity.opacity(), 0.0)
        QTest.qWait(40)
        self.assertGreater(toast._opacity.opacity(), 0.0)
        self.assertLess(toast._opacity.opacity(), 1.0)
        self.assertEqual(toast.y(), toast._rest_pos.y())
        self.assertGreater(toast._rest_pos.x() - toast.x(), 0)
        self.assertLessEqual(toast._rest_pos.x() - toast.x(), 12)
        self.finish_show(toast)
        self.assertEqual(len(toast.shown_geometry), 1)
        toast.show_at("bottom-left")
        self.app.processEvents()
        self.assertEqual(toast._opacity.opacity(), 1.0)
        self.assertEqual(toast._reveal.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.assertEqual(len(toast.shown_geometry), 1)

    def test_exit_has_real_intermediate_opacity_motion_and_never_reappears(self):
        toast = _ObservedToast("淡出", parent=self.parent)
        toast.show_at("top-left")
        self.finish_show(toast)
        toast.close()
        self.assertIsNone(toast._placement)
        self.assertTrue(toast.isVisible())
        QTest.qWait(90)
        self.assertGreater(toast._opacity.opacity(), 0.0)
        self.assertLess(toast._opacity.opacity(), 1.0)
        self.assertEqual(toast.y(), toast._rest_pos.y())
        self.assertGreater(toast._rest_pos.x() - toast.x(), 0)
        self.finish_close()
        self.assertFalse(toast.isVisible())
        self.parent.resize(650, 410)
        theme.toggle()
        QTest.qWait(Toast.SHOW_DURATION + 40)
        self.assertFalse(toast.isVisible())
        self.assertEqual(len(toast.shown_geometry), 1)

    def test_close_before_first_frame_deletes_without_late_animation_callbacks(self):
        toast = Toast.success("无需退场的首帧关闭", parent=self.parent, timeout_ms=0)
        destroyed = []
        toast.destroyed.connect(lambda *_: destroyed.append(True))
        self.assertEqual(toast._reveal_progress, 0.0)
        toast.close()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        QTest.qWait(Toast.SHOW_DURATION + Toast.HIDE_DURATION + 50)
        self.assertEqual(destroyed, [True])
        self.assertEqual(self.errors, [])

    def test_single_line_copy_message_uses_compact_card_and_standard_font(self):
        toast = Toast("代码已复制", parent=self.parent)
        toast.show_at()
        self.finish_show(toast)
        self.assertEqual(toast.size(), QtCore.QSize(220, 80))
        self.assertEqual(toast._card_path().boundingRect().size(), QtCore.QSizeF(187, 47))
        self.assertEqual(toast._title.font().pixelSize(), theme.tokens.font_size)
        self.assertEqual(toast._icon.size(), QtCore.QSize(20, 20))
        self.assertEqual(toast.close_button.size(), QtCore.QSize(20, 20))
        self.assertFalse(toast._detail.isVisible())

    def test_hidden_capture_attribute_is_inherited_before_show(self):
        self.parent.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        toast = _ObservedToast("用于隐藏截图", parent=self.parent)
        self.assertTrue(toast.testAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen))
        self.assertEqual(toast.show_calls, 0)
        toast.show_at()
        self.assertEqual(toast.show_calls, 1)

    def test_parentless_toast_is_a_shadowless_tooltip_and_fits_available_screen(self):
        toast = _ObservedToast("无需父窗口", "仍然可显示轻提示。")
        self.orphans.append(toast)
        self.assertTrue(toast.isWindow())
        self.assertEqual(toast.windowType(), QtCore.Qt.WindowType.ToolTip)
        self.assertTrue(toast.windowFlags() & QtCore.Qt.WindowType.NoDropShadowWindowHint)
        self.assertEqual(toast.show_calls, 0)
        for placement in ("top-left", "top-right", "bottom-left", "bottom-right"):
            toast.show_at(placement)
            self.assertTrue(toast.screen().availableGeometry().contains(toast.geometry()))
        self.assertEqual(toast.show_calls, 4)

    def test_success_uses_active_window_if_present_and_supports_no_active_window(self):
        with patch.object(QtWidgets.QApplication, "activeWindow", return_value=self.parent):
            child = Toast.success("自动父窗口", timeout_ms=100000)
        self.assertIs(child.parentWidget(), self.parent)
        self.assertFalse(child.isWindow())
        with patch.object(QtWidgets.QApplication, "activeWindow", return_value=None):
            standalone = Toast.success("独立提示", timeout_ms=100000)
        self.assertIsNone(standalone.parentWidget())
        self.assertEqual(standalone.windowType(), QtCore.Qt.WindowType.ToolTip)
        standalone.close()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
