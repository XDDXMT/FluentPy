"""Window notifications must never cover title bars or other window chrome."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
import unittest

from fluentpy import ColorToast, FluentWindow, InfoBar, ProgressInfoBar, ProgressToast, Toast
from fluentpy.qt import QtCore, QtWidgets


class NotificationBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.windows = []
        self.errors = []
        self.previous_hook = sys.excepthook
        sys.excepthook = lambda kind, value, traceback: self.errors.append(str(value))

    def tearDown(self):
        for window in self.windows:
            window.close()
            window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.previous_hook
        self.assertEqual(self.errors, [])

    def window(self, *, show=True):
        window = FluentWindow("Notification bounds")
        window.resize(800, 600)
        window.set_title_bar_enabled(True)
        self.windows.append(window)
        if show:
            window.show()
            self.app.processEvents()
        return window

    def content_bounds(self, window):
        content = window.centralWidget()
        return QtCore.QRect(content.mapTo(window, QtCore.QPoint()), content.size())

    def settle(self, toast):
        toast._reveal.setCurrentTime(toast._reveal.duration())
        toast._stack_motion.setCurrentTime(toast._stack_motion.duration())
        self.app.processEvents()

    def discard(self, toast):
        toast._allow_close = True
        toast.close()
        toast.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_all_notification_types_and_positions_stay_in_content_from_first_frame(self):
        window = self.window()
        for notification in (Toast, ColorToast, ProgressToast, InfoBar, ProgressInfoBar):
            for placement in Toast.PLACEMENTS:
                with self.subTest(notification=notification.__name__, placement=placement):
                    toast = notification("通知", "操作已完成。", parent=window)
                    toast.show_at(placement)
                    for fraction in (0, .4, 1):
                        toast._reveal.setCurrentTime(round(toast.SHOW_DURATION * fraction))
                        self.app.processEvents()
                        self.assertTrue(self.content_bounds(window).contains(toast.geometry()), toast.geometry())
                    self.discard(toast)

    def test_existing_notification_reflows_when_title_height_or_window_size_changes(self):
        window = self.window()
        toast = InfoBar("离线预览", "连接服务并登录后，即可启动游戏。", window)
        toast.show_at("top-right")
        self.settle(toast)
        for title_height, size in ((96, (800, 600)), (64, (480, 360)), (112, (500, 300))):
            with self.subTest(title_height=title_height, size=size):
                window.title_bar().setFixedHeight(title_height)
                window.resize(*size)
                self.app.processEvents()
                self.settle(toast)
                self.assertTrue(toast.isVisible())
                self.assertEqual(toast.y(), self.content_bounds(window).top() + 18)
                self.assertTrue(self.content_bounds(window).contains(toast.geometry()))

    def test_notifications_created_before_window_show_use_the_final_content_area(self):
        window = self.window(show=False)
        toast = InfoBar("离线预览", "初始化期间创建的通知", window)
        toast.show_at("top-right")
        window.show()
        self.app.processEvents()
        self.settle(toast)
        self.assertTrue(self.content_bounds(window).contains(toast.geometry()))
        self.assertEqual(toast.y(), self.content_bounds(window).top() + 18)

    def test_overflowing_mixed_stack_and_close_animations_never_enter_title_bar(self):
        window = self.window()
        window.resize(480, 350)
        self.app.processEvents()
        messages = []
        for notification in (Toast, InfoBar, ColorToast, ProgressToast, ProgressInfoBar):
            messages.append(notification("消息", "窗口内混合通知", window))
            messages[-1].show_at("top-right")
        members = messages[-1]._stack.members()
        self.assertLess(len(members), len(messages))
        for toast in members:
            self.settle(toast)
            self.assertTrue(self.content_bounds(window).contains(toast.geometry()))
        newest = messages[-1]
        newest.close()
        newest._reveal.setCurrentTime(newest.HIDE_DURATION // 2)
        for toast in members:
            self.assertTrue(self.content_bounds(window).contains(toast.geometry()))

    def test_target_near_content_top_does_not_put_arrow_or_card_into_title_bar(self):
        window = self.window()
        target = QtWidgets.QPushButton("操作", window.centralWidget())
        target.setGeometry(260, 4, 100, 32)
        target.show()
        toast = Toast("操作提示", "说明", target=target)
        toast.show_at()
        self.settle(toast)
        self.assertTrue(self.content_bounds(window).contains(toast.geometry()))
        self.assertIsNotNone(toast._arrow_edge)

    def test_standard_main_window_excludes_menus_toolbars_and_status_bar(self):
        window = QtWidgets.QMainWindow()
        window.resize(720, 480)
        window.setCentralWidget(QtWidgets.QWidget())
        window.menuBar().addMenu("文件")
        window.addToolBar("工具").addAction("操作")
        window.statusBar().showMessage("状态栏")
        self.windows.append(window)
        window.show()
        self.app.processEvents()
        for placement in Toast.PLACEMENTS:
            toast = InfoBar("通知", parent=window)
            toast.show_at(placement)
            self.settle(toast)
            self.assertTrue(self.content_bounds(window).contains(toast.geometry()))
            self.discard(toast)

    def test_plain_widget_and_inline_bar_keep_their_existing_layout(self):
        window = QtWidgets.QWidget()
        window.resize(720, 480)
        self.windows.append(window)
        layout = QtWidgets.QVBoxLayout(window)
        inline = InfoBar("嵌入提示", "继续由父布局控制", window)
        layout.addWidget(inline)
        layout.addStretch()
        window.show()
        self.app.processEvents()
        before = QtCore.QRect(inline.geometry())
        toast = Toast("普通窗口", parent=window)
        toast.show_at("top-right")
        self.settle(toast)
        self.assertEqual(toast.y(), 18)
        self.assertEqual(inline.geometry(), before)
        self.assertIsNone(inline._placement)
