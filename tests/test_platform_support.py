"""Platform frame policy, native typography and per-user workbench state."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fluentpy import CodeEdit, FluentWindow, LineEdit
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme import fonts


class PlatformSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_native_frame_can_switch_without_losing_page_or_toolbar_content(self):
        window = FluentWindow()
        page = QtWidgets.QWidget()
        window.add_page(page, "Page", route="page")
        window.set_title_bar_enabled(True, native_frame=True)
        search = LineEdit()
        search.setText("preserve me")
        window.title_bar().content_layout.addWidget(search)
        self.assertTrue(window.uses_native_caption_buttons())
        self.assertTrue(window.title_bar().close_button.isHidden())
        self.assertFalse(window.windowFlags() & QtCore.Qt.WindowType.FramelessWindowHint)
        window.set_title_bar_enabled(True, native_frame=False)
        self.assertFalse(window.uses_native_caption_buttons())
        self.assertFalse(window.title_bar().close_button.isHidden())
        self.assertTrue(window.windowFlags() & QtCore.Qt.WindowType.FramelessWindowHint)
        self.assertIs(window.current_page(), page)
        self.assertEqual(search.text(), "preserve me")
        window.close()
        window.deleteLater()

    def test_macos_selects_native_frame_by_default_and_allows_explicit_override(self):
        application_style = self.app.style()
        with patch("fluentpy.widgets.window.sys.platform", "darwin"):
            window = FluentWindow()
            window.set_title_bar_enabled(True)
            self.assertTrue(window.uses_native_caption_buttons())
            window.set_title_bar_enabled(True, native_frame=False)
            self.assertFalse(window.uses_native_caption_buttons())
            self.assertIs(self.app.style(), application_style)
            self.assertNotIn("_fluent_widget_style", self.app.__dict__)
            window.close()
            window.deleteLater()

    def test_wayland_uses_compositor_frame_without_entering_windows_native_code(self):
        with patch.object(self.app, "platformName", return_value="wayland"):
            window = FluentWindow()
            window.set_title_bar_enabled(True)
            self.assertTrue(window.uses_native_caption_buttons())
            self.assertFalse(window._integrated_windows_frame)
            self.assertTrue(window.title_bar().close_button.isHidden())
            window.close()
            window.deleteLater()

    def test_fonts_follow_platform_and_code_remains_monospace(self):
        for platform, expected in (
            ("win32", "Segoe UI"),
            ("darwin", "PingFang SC"),
            ("linux", "Noto Sans CJK SC"),
        ):
            with self.subTest(platform=platform), patch.object(fonts.sys, "platform", platform):
                self.assertIn(expected, fonts.font_families())
                self.assertTrue(fonts.font_families(monospace=True))
                self.assertEqual(fonts.ui_font(17).pixelSize(), 17)
                editor = CodeEdit()
                self.assertTrue(editor.text_edit.font().families())
                self.assertEqual(fonts.code_font(16).pixelSize(), 16)
                editor.deleteLater()

    def test_workbench_data_uses_the_qt_user_directory(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        try:
            from workbench_paths import workbench_data_directory

            with patch.object(
                QtCore.QStandardPaths, "writableLocation", return_value="/user/share"
            ):
                self.assertEqual(workbench_data_directory(), Path("/user/share/FluentPy/Workbench"))
            with patch.object(QtCore.QStandardPaths, "writableLocation", return_value=""):
                with self.assertRaises(RuntimeError):
                    workbench_data_directory()
        finally:
            sys.path.pop(0)

    def tearDown(self):
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
