"""Qt title-bar ownership, extension points and native-window delegation."""
import os
import sys
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from fluentpy.theme import theme
from fluentpy.widgets.title_bar import FluentTitleBar
from fluentpy.widgets.button import Button

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.maximized = False
        self.minimize_calls = self.maximize_calls = self.normal_calls = self.close_calls = 0
        self.history = ["overview", "editor", "settings"]
        self.history_index = 1
        self.native_handle = Mock()
        self.native_handle.startSystemMove.return_value = True

    def showMinimized(self):
        self.minimize_calls += 1

    def showMaximized(self):
        self.maximize_calls += 1
        self.maximized = True

    def showNormal(self):
        self.normal_calls += 1
        self.maximized = False

    def isMaximized(self):
        return self.maximized

    def close(self):
        self.close_calls += 1
        return True

    def windowHandle(self):
        return self.native_handle

    def can_go_back(self):
        return self.history_index > 0

    def can_go_forward(self):
        return self.history_index < len(self.history) - 1

    def go_back(self):
        if self.can_go_back():
            self.history_index -= 1

    def go_forward(self):
        if self.can_go_forward():
            self.history_index += 1


class TitleBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, traceback: self.errors.append(error)
        self.owner = Window()
        self.owner.resize(860, 300)
        self.bar = FluentTitleBar(self.owner)
        layout = QtWidgets.QVBoxLayout(self.owner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.bar)
        layout.addStretch()
        self.owner.show()
        self.app.processEvents()

    def tearDown(self):
        self.owner.hide()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_caption_actions_delegate_to_the_owner_and_state_changes_update_the_button(self):
        self.bar.minimize_button.click()
        self.assertEqual(self.owner.minimize_calls, 1)
        self.bar.maximize_button.click()
        self.assertEqual(self.owner.maximize_calls, 1)
        self.assertEqual(self.bar.maximize_button.accessibleName(), "还原")
        self.bar.maximize_button.click()
        self.assertEqual(self.owner.normal_calls, 1)
        self.assertEqual(self.bar.maximize_button.toolTip(), "最大化")
        self.owner.maximized = True
        self.app.sendEvent(self.owner, QtCore.QEvent(QtCore.QEvent.Type.WindowStateChange))
        self.assertEqual(self.bar.maximize_button.toolTip(), "还原")
        self.bar.close_button.click()
        self.assertEqual(self.owner.close_calls, 1)

    def test_navigation_uses_history_availability_and_syncs_after_each_action(self):
        self.bar.back_button.click()
        self.assertEqual(self.owner.history_index, 0)
        self.assertFalse(self.bar.back_button.isEnabled())
        self.bar.forward_button.click()
        self.bar.forward_button.click()
        self.assertEqual(self.owner.history_index, 2)
        self.assertFalse(self.bar.forward_button.isEnabled())
        self.owner.history_index = 1
        self.bar.sync_navigation()
        self.assertTrue(self.bar.forward_button.isEnabled())
        self.assertTrue(self.bar.back_button.isEnabled())

    def test_long_title_elides_and_tracks_title_and_icon_changes_without_setting_window_flags(self):
        flags = self.owner.windowFlags()
        title = "FluentPy 工作台 / 一个需要完整保留但允许省略显示的长标题 " * 6
        self.owner.setWindowTitle(title)
        self.app.processEvents()
        self.assertEqual(self.bar.title_label.accessibleName(), title)
        self.assertNotEqual(self.bar.title_label.text(), title)
        self.assertLessEqual(self.bar.title_label.fontMetrics().horizontalAdvance(
            self.bar.title_label.text()), self.bar.title_label.width())
        self.assertEqual(self.bar.title_label.toolTip(), title)
        self.owner.setWindowTitle("文件")
        self.assertEqual(self.bar.title_label.text(), "文件")
        self.assertEqual(self.bar.title_label.toolTip(), "")
        icon = self.bar.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        self.owner.setWindowIcon(icon)
        self.assertFalse(self.bar.icon_label.isHidden())
        self.assertFalse(self.bar.icon_label.pixmap().isNull())
        self.owner.setWindowIcon(QtGui.QIcon())
        self.assertTrue(self.bar.icon_label.isHidden())
        self.assertEqual(self.owner.windowFlags(), flags)

    def test_blank_and_title_drag_use_only_an_existing_window_handle(self):
        self.owner.winId = Mock(side_effect=AssertionError("drag must not allocate a native handle"))
        QTest.mousePress(self.bar, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(300, 20))
        self.owner.native_handle.startSystemMove.assert_called_once_with()
        self.owner.native_handle.startSystemMove.reset_mock()
        QTest.mousePress(self.bar.title_label, QtCore.Qt.MouseButton.LeftButton)
        self.owner.native_handle.startSystemMove.assert_called_once_with()
        handle = self.owner.native_handle
        self.owner.native_handle = None
        QTest.mousePress(self.bar, QtCore.Qt.MouseButton.LeftButton)
        handle.startSystemMove.assert_called_once_with()
        self.owner.winId.assert_not_called()

    def test_custom_search_and_action_widgets_remain_interactive_without_starting_drag(self):
        search = QtWidgets.QLineEdit()
        search.setPlaceholderText("搜索项目")
        search.setFixedWidth(220)
        action = Button("保存")
        calls = []
        action.clicked.connect(lambda: calls.append("saved"))
        self.bar.content_layout.addWidget(search)
        self.bar.button_layout.addWidget(action)
        self.app.processEvents()
        QTest.mouseClick(search, QtCore.Qt.MouseButton.LeftButton)
        QTest.keyClicks(search, "example")
        QTest.mouseClick(action, QtCore.Qt.MouseButton.LeftButton)
        QTest.mouseDClick(action, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(search.text(), "example")
        self.assertEqual(calls, ["saved"])
        self.assertEqual(self.owner.maximize_calls, 0)
        self.assertIs(search.parentWidget(), self.bar._content)
        self.assertIs(action.parentWidget(), self.bar._actions)
        self.owner.native_handle.startSystemMove.assert_not_called()

    def test_ignored_custom_control_events_do_not_bubble_into_window_operations(self):
        widget = QtWidgets.QWidget()
        widget.setFixedSize(80, 32)
        self.bar.content_layout.addWidget(widget)
        self.app.processEvents()
        QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton)
        QTest.mouseDClick(widget, QtCore.Qt.MouseButton.LeftButton)
        self.owner.native_handle.startSystemMove.assert_not_called()
        self.assertEqual(self.owner.maximize_calls, 0)

    def test_double_click_respects_configuration_and_maximize_visibility_and_enabled_state(self):
        self.assertTrue(self.bar.double_click_enabled())
        QTest.mouseDClick(self.bar, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.owner.maximize_calls, 1)
        self.bar.set_double_click_enabled(False)
        QTest.mouseDClick(self.bar, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.owner.normal_calls, 0)
        self.bar.set_double_click_enabled(True)
        self.bar.set_caption_buttons_visible(maximize=False)
        QTest.mouseDClick(self.bar, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.owner.normal_calls, 0)
        self.bar.set_caption_buttons_visible()
        self.bar.maximize_button.setEnabled(False)
        QTest.mouseDClick(self.bar, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.owner.normal_calls, 0)
        self.bar.maximize_button.setEnabled(True)
        QTest.mouseDClick(self.bar, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.owner.normal_calls, 1)

    def test_plain_qwidget_owner_and_theme_subscription_follow_qt_ownership(self):
        plain_owner = QtWidgets.QWidget()
        flags = plain_owner.windowFlags()
        bar = FluentTitleBar(plain_owner)
        self.assertIs(bar.parentWidget(), plain_owner)
        self.assertEqual(bar.height(), 48)
        self.assertFalse(bar.back_button.isEnabled())
        self.assertFalse(bar.forward_button.isEnabled())
        self.assertIsNone(plain_owner.windowHandle())
        self.assertEqual(plain_owner.windowFlags(), flags)
        deleted = []
        bar.destroyed.connect(lambda: deleted.append(True))
        plain_owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(deleted, [True])
        old_mode = theme.mode
        theme.toggle()
        theme.set_mode(old_mode)

    def test_theme_switch_paints_owner_background_and_readable_title_and_captions_over_stale_qss(self):
        old_mode = theme.mode
        # Reproduce an ancestor's stale scoped foreground while the window
        # coordinator has already supplied its new palette background.
        self.owner.setStyleSheet("QLabel {color:#1b1d22;} QWidget {font-size:14px;}")
        self.owner.setWindowTitle("Theme title")
        self.owner._resolved_background_color = lambda: self.owner._caption_test_background
        def contains_color(image, color):
            return any(max(abs(image.pixelColor(x, y).red() - color.red()),
                           abs(image.pixelColor(x, y).green() - color.green()),
                           abs(image.pixelColor(x, y).blue() - color.blue())) <= 3
                       for y in range(image.height()) for x in range(image.width()))
        for mode in ('dark', 'light', 'dark'):
            background = QtGui.QColor('#20242f' if mode == 'dark' else '#f3f5fb')
            self.owner._caption_test_background = background
            palette = self.owner.palette()
            palette.setColor(QtGui.QPalette.ColorRole.Window, background)
            self.owner.setPalette(palette)
            theme.set_mode(mode)
            self.bar.refresh_theme()
            self.app.processEvents()
            image = self.bar.grab().toImage()
            self.assertEqual(image.pixelColor(image.width() // 2, image.height() - 1), background)
            self.assertTrue(contains_color(self.bar.title_label.grab().toImage(), QtGui.QColor(theme.tokens.text)))
            for button in (self.bar.minimize_button, self.bar.maximize_button, self.bar.close_button):
                button._reset_interaction()
                self.assertTrue(contains_color(button.grab().toImage(), QtGui.QColor(theme.tokens.text)))
                self.assertEqual(button.height(), 48)
        theme.set_mode(old_mode)

    def test_configured_height_survives_native_refresh_theme_changes_and_qt_fixed_height_entry(self):
        self.assertEqual(self.bar.bar_height(), 48)
        for height, setter in ((60, self.bar.set_bar_height), (56, self.bar.setFixedHeight)):
            setter(height)
            self.bar._set_native_caption(False)
            self.bar.refresh_theme()
            self.owner.resize(920, 350)
            self.app.processEvents()
            self.assertEqual(self.bar.bar_height(), height)
            self.assertEqual(self.bar.height(), height)
            for button in (self.bar.back_button, self.bar.forward_button, self.bar.minimize_button,
                           self.bar.maximize_button, self.bar.close_button):
                self.assertEqual(button.height(), height)
        for invalid in (0, 31, True, 48.5):
            with self.assertRaises(ValueError):
                self.bar.set_bar_height(invalid)
            self.assertEqual(self.bar.bar_height(), 56)


if __name__ == "__main__":
    unittest.main()
