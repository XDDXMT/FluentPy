"""Startup ownership, input shielding, geometry, completion and cleanup."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from splash_screen import SplashDemo, SplashExamples, brand_icon

from fluentpy import Button, FluentWindow, LineEdit, SplashScreen, theme
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class SplashScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.old_mode = theme.mode
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.host = FluentWindow("Startup test")
        self.host.set_title_bar_enabled(True)
        self.host.setWindowIcon(brand_icon())
        self.host.resize(720, 480)
        self.editor = LineEdit()
        self.editor.setText("retain this value")
        self.button = Button("Underlying action")
        self.clicks = []
        self.button.clicked.connect(lambda: self.clicks.append(True))
        self.host.content_layout.addWidget(self.editor)
        self.host.content_layout.addWidget(self.button)
        self.host.content_layout.addStretch()
        self.host.show()
        self.app.processEvents()
        self.editor.setFocus()
        self.splash = SplashScreen(parent=self.host)

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        theme.set_mode(self.old_mode)
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_parent_required_constructed_hidden_and_no_new_native_window(self):
        with self.assertRaises(TypeError):
            SplashScreen()
        before = {int(widget.winId()) for widget in self.app.topLevelWidgets()}
        self.assertTrue(self.splash.isHidden())
        self.assertFalse(self.splash.isWindow())
        self.assertFalse(self.splash.icon().isNull())
        self.splash.show()
        self.app.processEvents()
        self.assertEqual(before, {int(widget.winId()) for widget in self.app.topLevelWidgets()})
        self.assertIs(self.splash.parentWidget(), self.host)
        self.assertFalse(self.splash.testAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow))
        self.assertFalse(
            self.splash.testAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        )

    def test_content_coverage_excludes_caption_and_tracks_resize_and_caption_toggle(self):
        self.splash.show()
        self.app.processEvents()
        self.assertEqual(self.splash.geometry(), QtCore.QRect(0, 48, 720, 432))
        self.host.resize(820, 550)
        self.app.processEvents()
        self.assertEqual(self.splash.geometry(), QtCore.QRect(0, 48, 820, 502))
        self.host.set_title_bar_enabled(False)
        self.app.processEvents()
        self.assertEqual(self.splash.geometry(), self.host.rect())
        self.host.set_title_bar_enabled(True)
        self.host.title_bar().set_bar_height(60)
        self.app.processEvents()
        self.assertEqual(self.splash.y(), 60)
        self.assertEqual(self.splash.geometry().bottom(), self.host.rect().bottom())

    def test_logo_only_center_and_size_defensive_copy_and_small_parent_bounds(self):
        self.splash.show()
        self.assertEqual(self.splash.text(), "")
        self.assertFalse(self.splash.is_loading())
        self.splash.set_icon_size(QtCore.QSize(102, 88))
        icon, text, spinner = self.splash._content_rects()
        self.assertEqual(icon.size(), QtCore.QSizeF(102, 88))
        self.assertEqual(icon.center(), QtCore.QRectF(self.splash.rect()).center())
        size = self.splash.icon_size()
        size.setWidth(1)
        self.assertEqual(self.splash.icon_size().width(), 102)
        for size in (0, -1, True, "96", QtCore.QSize(10, 0)):
            with self.assertRaises(ValueError):
                self.splash.set_icon_size(size)
        self.splash.set_loading(True)
        self.splash.set_text("正在准备界面…")
        for width, height in ((320, 220), (120, 140), (40, 40)):
            self.host.resize(width, height)
            self.app.processEvents()
            for rect in self.splash._content_rects():
                if not rect.isEmpty():
                    self.assertTrue(QtCore.QRectF(self.splash.rect()).contains(rect), rect)

    def test_input_blocked_under_overlay_and_caption_action_remains_usable(self):
        self.splash.show()
        self.app.processEvents()
        QTest.keyClicks(self.editor, "blocked")
        QTest.keyClick(self.splash, QtCore.Qt.Key.Key_Tab)
        self.assertFalse(self.editor.hasFocus())
        self.assertEqual(self.editor.text(), "retain this value")
        target = self.button.mapTo(self.host, self.button.rect().center())
        self.assertIs(self.host.childAt(target), self.splash)
        bar = self.host.title_bar()
        self.assertTrue(bar.title_label.isHidden())
        QTest.mouseClick(bar.maximize_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertTrue(self.host.isMaximized())
        QTest.mouseClick(bar.maximize_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(self.host.isMaximized())
        self.app.processEvents()
        self.assertTrue(bar.title_label.isHidden())

    def test_startup_caption_has_only_window_controls_and_restores_latest_metadata_and_contents(
        self,
    ):
        bar = self.host.title_bar()
        search = LineEdit()
        search.setText("retained search")
        action = Button("Theme action")
        bar.content_layout.addWidget(search)
        bar.button_layout.addWidget(action)
        bar.forward_button.hide()
        self.splash.show()
        self.app.processEvents()
        for control in (
            bar.back_button,
            bar.forward_button,
            bar.icon_label,
            bar.title_label,
            bar._content,
            bar._actions,
        ):
            self.assertTrue(control.isHidden())
        for control in (bar.minimize_button, bar.maximize_button, bar.close_button):
            self.assertTrue(control.isVisible())
        self.host.setWindowTitle("Updated while loading")
        self.host.setWindowIcon(brand_icon())
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.host.resize(self.host.width() + 2, self.host.height() + 2)
            self.app.processEvents()
            self.assertTrue(bar.title_label.isHidden())
            self.assertTrue(bar.icon_label.isHidden())
            self.assertEqual(
                bar.grab().toImage().pixelColor(10, 10), self.splash._resolved_background_color()
            )
        self.splash.finish(animated=False)
        self.assertTrue(bar.back_button.isVisible())
        self.assertTrue(bar.forward_button.isHidden())
        self.assertTrue(bar.title_label.isVisible())
        self.assertTrue(bar.icon_label.isVisible())
        self.assertTrue(search.isVisible())
        self.assertTrue(action.isVisible())
        self.assertEqual(search.text(), "retained search")
        self.assertEqual(bar.title_label.accessibleName(), "Updated while loading")

    def test_overlapping_splashes_and_direct_destruction_do_not_restore_caption_too_early(self):
        bar = self.host.title_bar()
        self.splash.show()
        second = SplashScreen(parent=self.host)
        second.show()
        second.finish(animated=False)
        self.assertTrue(bar.title_label.isHidden())
        self.splash.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertTrue(bar.title_label.isVisible())
        self.assertFalse(bar._startup_splashes)
        second.deleteLater()

    def test_fade_blocks_until_finished_once_then_restores_values_and_focus(self):
        done = []
        self.splash.finished.connect(lambda: done.append(True))
        self.splash.show()
        self.splash.finish()
        self.splash.finish()
        self.assertTrue(self.splash.isVisible())
        self.splash._fade.setCurrentTime(100)
        self.assertGreater(self.splash._opacity, 0)
        self.assertLess(self.splash._opacity, 1)
        self.splash._fade.setCurrentTime(self.splash._fade.duration())
        self.assertTrue(self.splash.isHidden())
        self.assertEqual(done, [True])
        self.assertFalse(self.splash._input_filter_installed)
        self.assertEqual(self.editor.text(), "retain this value")
        self.assertIs(self.host.focusWidget(), self.editor)
        QTest.keyClicks(self.editor, "!")
        self.assertEqual(self.editor.text(), "retain this value!")
        self.splash.finish()
        self.assertEqual(done, [True])
        self.splash.show()
        self.assertEqual(self.splash._opacity, 1)
        self.splash.finish(animated=False)
        self.assertEqual(done, [True, True])

    def test_spinner_and_filters_stop_when_hidden_and_parent_owned_destruction(self):
        self.splash.set_loading(True)
        self.assertNotEqual(self.splash._spinner.state(), QtCore.QAbstractAnimation.State.Running)
        self.splash.show()
        self.assertEqual(self.splash._spinner.state(), QtCore.QAbstractAnimation.State.Running)
        self.host.hide()
        self.assertEqual(self.splash._spinner.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.assertFalse(self.splash._input_filter_installed)
        self.splash.finish()
        self.host.show()
        self.assertTrue(self.splash.isHidden())
        destroyed = []
        self.splash.destroyed.connect(lambda: destroyed.append(True))
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        self.host = FluentWindow()

    def test_hiding_parent_during_exit_completes_once_without_resurrecting_splash(self):
        done = []
        self.splash.finished.connect(lambda: done.append(True))
        self.splash.show()
        self.splash.finish()
        self.splash._fade.setCurrentTime(80)
        self.host.hide()
        self.assertEqual(done, [True])
        self.assertTrue(self.splash.isHidden())
        self.assertFalse(self.splash._input_filter_installed)
        self.host.show()
        self.app.processEvents()
        self.assertFalse(self.splash.isVisible())
        self.assertTrue(self.host.title_bar().title_label.isVisible())
        self.assertEqual(done, [True])

    def test_theme_and_paired_background_paint_without_host_style_mutation(self):
        original = self.host.styleSheet()
        self.splash.show()
        for mode in ("dark", "light", "dark"):
            theme.set_mode(mode)
            image = self.splash.grab().toImage()
            self.assertEqual(image.pixelColor(5, 5), QtGui.QColor(theme.tokens.background))
        self.splash.set_background_colors("#edf4fa", "#162231")
        self.assertEqual(self.splash.grab().toImage().pixelColor(5, 5).name(), "#162231")
        with self.assertRaises(ValueError):
            self.splash.set_background_colors("#80ffffff", "#000000")
        self.splash.clear_background_colors()
        self.assertEqual(self.host.styleSheet(), original)

    def test_example_replays_and_full_overlay_cleanup_without_extra_windows(self):
        demo = SplashExamples()
        self.host.content_layout.addWidget(demo)
        self.app.processEvents()
        demo.retained_input.setText("kept")
        demo.size_spin.setValue(128)
        demo.loading_check.setChecked(True)
        demo.text_edit.setText("自定义提示")
        demo.replay()
        self.assertEqual(demo.preview_splash.icon_size(), QtCore.QSize(128, 128))
        self.assertEqual(demo.preview_splash.text(), "自定义提示")
        demo._finish_preview()
        demo.preview_splash._fade.setCurrentTime(220)
        self.assertEqual(demo.retained_input.text(), "kept")
        full = demo.preview_window()
        self.assertIs(full.parentWidget(), self.host)
        self.assertTrue(full.isVisible())
        demo.hide()
        self.assertTrue(full.isHidden())
        self.assertIsNone(demo._window_splash)
        self.assertFalse(demo._timer.isActive())

    def test_embedded_preview_tab_reaches_configuration_outside_covered_region(self):
        demo = SplashExamples()
        self.host.content_layout.addWidget(demo)
        self.app.processEvents()
        demo.preview_splash.setFocus()
        QTest.keyClick(demo.preview_splash, QtCore.Qt.Key.Key_Tab)
        self.assertIsNot(self.app.focusWidget(), demo.retained_input)
        self.assertIsNot(self.app.focusWidget(), demo.preview_splash)

    def test_standalone_demo_constructs_without_automatic_extra_top_level_windows(self):
        demo = SplashDemo()
        try:
            demo.show()
            self.app.processEvents()
            self.assertTrue(demo.is_title_bar_enabled())
            self.assertIsNone(demo.examples._window_splash)
        finally:
            demo.close()
            demo.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
