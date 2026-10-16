import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.widgets.navigation import NavigationSidebar


class NavigationSidebarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = QtWidgets.QWidget()
        self.window.resize(600, 500)
        layout = QtWidgets.QHBoxLayout(self.window)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = NavigationSidebar(self.window)
        layout.addWidget(self.sidebar)
        layout.addWidget(QtWidgets.QWidget(self.window), 1)
        for text in ("主页", "组件", "动画"):
            self.sidebar.add_item(QtGui.QIcon(), text)
        self.sidebar.add_separator()
        self.sidebar.add_footer_item(QtGui.QIcon(), "设置")
        self.window.show()
        self.settle()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def settle(self):
        self.app.processEvents()
        self.sidebar.layout().activate()
        self.app.processEvents()

    def assert_rows_fit(self):
        for widget in self.sidebar._widgets:
            with self.subTest(widget=type(widget).__name__, width=self.sidebar.width()):
                self.assertEqual(widget.width(), self.sidebar.width() - 8)
                if not widget.isHidden():
                    self.assertEqual(widget.x(), 4)
                    self.assertLessEqual(widget.geometry().right(), self.sidebar.width() - 5)

    def finish_width(self):
        animation = self.sidebar._width_animation
        animation.setCurrentTime(animation.duration())
        self.settle()

    def test_default_widths_and_rows(self):
        self.assertEqual(self.sidebar.width(), 48)
        self.assert_rows_fit()
        self.sidebar.set_expanded(True)
        self.finish_width()
        self.assertEqual(self.sidebar.width(), 322)
        self.assert_rows_fit()
        self.sidebar.set_expanded(False)
        self.finish_width()
        self.assertEqual(self.sidebar.width(), 48)
        self.assert_rows_fit()

    def test_custom_width_updates_all_rows_and_new_entries(self):
        self.sidebar.set_expanded_width(216)
        self.sidebar.set_expanded(True)
        self.finish_width()
        self.assertEqual(self.sidebar.width(), 216)
        self.assert_rows_fit()
        added = self.sidebar.add_item(QtGui.QIcon(), "新增")
        self.sidebar.add_separator()
        footer = self.sidebar.add_footer_item(QtGui.QIcon(), "关于")
        self.settle()
        self.assertEqual(added.width(), 208)
        self.assertEqual(footer.width(), 208)
        self.assert_rows_fit()
        self.sidebar.set_expanded_width(172)
        self.settle()
        self.assertEqual(self.sidebar.width(), 172)
        self.assert_rows_fit()

    def test_rows_follow_each_width_animation_frame(self):
        self.sidebar.set_expanded_width(216)
        for expanded in (True, False):
            self.sidebar.set_expanded(expanded)
            for milliseconds in (0, 15, 45, 75, 110, 149, 150):
                self.sidebar._width_animation.setCurrentTime(milliseconds)
                self.settle()
                self.assert_rows_fit()
            self.assertEqual(self.sidebar.width(), 216 if expanded else 48)

    def test_rapid_toggle_restarts_from_current_width(self):
        self.sidebar.set_expanded_width(216)
        for _ in range(5):
            before = self.sidebar.width()
            self.sidebar.toggle()
            self.assertEqual(self.sidebar._width_animation.startValue(), before)
            self.sidebar._width_animation.setCurrentTime(40)
            self.settle()
            self.assert_rows_fit()
        self.finish_width()
        self.assertTrue(self.sidebar.expanded)
        self.assertEqual(self.sidebar.width(), 216)
        self.sidebar.toggle()
        self.finish_width()
        self.assertFalse(self.sidebar.expanded)
        self.assertEqual(self.sidebar.width(), 48)
        self.assert_rows_fit()

    def test_layout_request_preserves_indicator_animation(self):
        self.sidebar.set_current_index(2)
        animation = self.sidebar._indicator_animation
        animation.setCurrentTime(55)
        before = self.sidebar._indicator.geometry()
        self.app.sendEvent(self.sidebar, QtCore.QEvent(QtCore.QEvent.Type.LayoutRequest))
        self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Running)
        self.assertEqual(animation.currentTime(), 55)
        self.assertEqual(self.sidebar._indicator.geometry(), before)
        animation.setCurrentTime(animation.duration())
        self.assertEqual(self.sidebar._indicator.geometry(), self.sidebar._indicator_target(2))

    def test_width_animation_does_not_interrupt_selection_animation(self):
        self.sidebar.set_current_index(2)
        self.sidebar._indicator_animation.setCurrentTime(45)
        self.sidebar.set_expanded_width(216)
        self.sidebar.set_expanded(True)
        self.sidebar._width_animation.setCurrentTime(75)
        self.settle()
        animation = self.sidebar._indicator_animation
        self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Running)
        self.assertEqual(animation.endValue(), self.sidebar._indicator_target(2))
        self.assertNotEqual(self.sidebar._indicator.geometry(), animation.endValue())

    def test_moving_footer_retargets_remaining_indicator_animation(self):
        self.sidebar.set_current_index(3)
        animation = self.sidebar._indicator_animation
        animation.setCurrentTime(50)
        previous_target = animation.endValue()
        self.window.resize(600, 700)
        self.settle()
        self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Running)
        self.assertNotEqual(animation.endValue(), previous_target)
        self.assertEqual(animation.endValue(), self.sidebar._indicator_target(3))
        self.assertLessEqual(animation.duration(), 160)
        animation.setCurrentTime(animation.duration())
        self.assertEqual(self.sidebar._indicator.geometry(), self.sidebar._indicator_target(3))
        self.sidebar.set_current_index(0)
        self.assertEqual(animation.duration(), 210)

    def test_invalid_expanded_width_leaves_geometry_unchanged(self):
        for width in (119, 0, -1, 216.0, "216", None):
            with self.subTest(width=width), self.assertRaises(ValueError):
                self.sidebar.set_expanded_width(width)
        self.sidebar.set_expanded(True)
        self.finish_width()
        self.assertEqual(self.sidebar.width(), 322)


if __name__ == "__main__":
    unittest.main()
