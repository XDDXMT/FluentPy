"""Integrated Qt captions retain Windows frame behavior without a second row."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest
from unittest.mock import patch

from fluentpy import Button, FluentWindow, LineEdit, theme, window_effects
from fluentpy.qt import QtCore, QtGui, QtWidgets


class NativeWindowChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, traceback: self.errors.append(str(error))
        self.window = FluentWindow("Native caption")

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_integrated_windows_caption_is_one_qt_row_and_is_reported_honestly(self):
        with patch.object(self.window, "_native_windows_platform", return_value=True):
            self.window.set_title_bar_enabled(True)
            bar = self.window.title_bar()
            self.assertFalse(self.window.uses_native_caption_buttons())
            self.assertFalse(bar.uses_native_caption_buttons())
            self.assertTrue(self.window._integrated_windows_frame)
            self.assertTrue(self.window.windowFlags() & QtCore.Qt.WindowType.FramelessWindowHint)
            self.assertFalse(self.window.windowFlags() & QtCore.Qt.WindowType(0x00400000))
            self.assertEqual(bar.height(), 48)
            self.assertFalse(bar.title_label.isHidden())
            self.assertTrue(bar.icon_label.isHidden())
            icon = self.window.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
            self.window.setWindowIcon(icon)
            self.assertFalse(bar.icon_label.isHidden())
            self.assertFalse(bar.icon_label.pixmap().isNull())
            for button in (bar.minimize_button, bar.maximize_button, bar.close_button):
                self.assertFalse(button.isHidden())
            search = LineEdit("Search")
            bar.content_layout.addWidget(search)
            action = Button("Help")
            bar.button_layout.addWidget(action)
            self.assertIs(bar.content_layout.itemAt(0).widget(), search)
            self.assertIs(bar.button_layout.itemAt(0).widget(), action)

    def test_caption_visibility_and_double_click_do_not_create_a_second_native_caption(self):
        with patch.object(self.window, "_native_windows_platform", return_value=True):
            self.window.set_title_bar_enabled(True)
            bar = self.window.title_bar()
            bar.set_caption_buttons_visible(maximize=False)
            self.assertTrue(bar.maximize_button.isHidden())
            with patch.object(self.window, "showMaximized") as maximize:
                bar._toggle_maximized()
                maximize.assert_not_called()
                bar.set_caption_buttons_visible()
                self.assertTrue(
                    self.window.windowFlags() & QtCore.Qt.WindowType.WindowMaximizeButtonHint
                )
                bar._toggle_maximized()
                maximize.assert_called_once_with()
            self.assertFalse(bar.maximize_button.isHidden())

    def test_native_toggle_preserves_standard_frame_hints_and_reuses_command_contents(self):
        with patch.object(self.window, "_native_windows_platform", return_value=True):
            original_flags = self.window.windowFlags()
            self.window.set_title_bar_enabled(True)
            bar = self.window.title_bar()
            search = LineEdit()
            search.setText("Retained content")
            bar.content_layout.addWidget(search)
            self.window.set_title_bar_enabled(False)
            self.assertEqual(self.window.windowFlags(), original_flags)
            self.assertTrue(bar.isHidden())
            self.window.set_title_bar_enabled(True)
            self.assertIs(bar, self.window.title_bar())
            self.assertEqual(search.text(), "Retained content")
            self.assertFalse(self.window.uses_native_caption_buttons())

    def test_non_client_caption_is_removed_without_removing_the_whole_native_window(self):
        with patch.object(self.window, "_native_windows_platform", return_value=True):
            self.window.set_title_bar_enabled(True)
            import ctypes
            import ctypes.wintypes

            message = ctypes.wintypes.MSG()
            message.message, message.wParam = 0x0083, 1
            self.assertEqual(
                self.window.nativeEvent(b"windows_generic_MSG", ctypes.addressof(message)),
                (True, 0),
            )
            self.assertTrue(self.window.is_title_bar_enabled())

    def test_close_hover_uses_windows_red_and_white_glyph_in_both_themes(self):
        self.window.set_title_bar_enabled(True)
        button = self.window.title_bar().close_button
        old_mode = theme.mode
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            button._hover_progress = 1.0
            image = button.grab().toImage()
            self.assertEqual(image.pixelColor(5, 5).name(), "#e81123")
            center = image.pixelColor(button.width() // 2, button.height() // 2)
            self.assertGreater(min(center.red(), center.green(), center.blue()), 190)
        theme.set_mode(old_mode)

    def test_explicit_theme_refresh_follows_owner_background_pair_after_repeated_switches(self):
        self.window.set_title_bar_enabled(True)
        self.window.set_background_colors("#edf4fa", "#162231")
        bar = self.window.title_bar()
        original_mode = theme.mode
        for mode, expected in (("dark", "#162231"), ("light", "#edf4fa"), ("dark", "#162231")):
            theme.set_mode(mode)
            bar.refresh_theme()
            image = bar.grab().toImage()
            self.assertEqual(
                image.pixelColor(image.width() // 2, image.height() - 1).name(), expected
            )
            self.assertEqual(
                bar.palette().color(QtGui.QPalette.ColorRole.WindowText).name(), theme.tokens.text
            )
            self.assertEqual(bar.height(), 48)
        original = self.window.windowFlags()
        self.window.set_title_bar_enabled(False)
        self.window.set_title_bar_enabled(True)
        self.assertIs(bar, self.window.title_bar())
        self.assertEqual(bar.height(), 48)
        self.assertEqual(self.window.windowFlags(), original)
        theme.set_mode(original_mode)

    def test_native_corner_request_preserves_styles_and_does_not_turn_the_client_transparent(self):
        self.window.show()
        with (
            patch.object(window_effects, "_dwm_set_int", return_value=True) as request,
            patch.object(window_effects, "_set_window_long_ptr") as replace_style,
        ):
            window_effects.apply_system_backdrop(self.window, theme.mode, True, False)
            self.assertIn(
                (int(self.window.winId()), 33, 2), [call.args for call in request.call_args_list]
            )
            replace_style.assert_not_called()
        image = self.window.grab().toImage()
        self.assertEqual(image.pixelColor(image.width() // 2, image.height() // 2).alpha(), 255)

    def test_window_state_change_refreshes_native_shape_for_both_caption_modes(self):
        for enabled in (False, True):
            self.window.set_title_bar_enabled(enabled)
            with (
                self.subTest(integrated=enabled),
                patch.object(self.window, "_native_windows_platform", return_value=True),
                patch.object(self.window, "_apply_backdrop") as refresh,
            ):
                event = QtGui.QWindowStateChangeEvent(QtCore.Qt.WindowState.WindowNoState)
                self.window.changeEvent(event)
                refresh.assert_called_once_with()

    def test_frame_capture_offscreen_fallback_remains_an_opaque_qt_image(self):
        self.window.resize(500, 360)
        image = window_effects.capture_window_frame(self.window)
        self.assertIsInstance(image, QtGui.QImage)
        self.assertFalse(image.isNull())
        self.assertEqual(image.size(), self.window.size())
        self.assertEqual(image.pixelColor(250, 180).alpha(), 255)


if __name__ == "__main__":
    unittest.main()
