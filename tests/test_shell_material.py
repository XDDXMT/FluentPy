"""Shared shell colors, native-material alpha and safe opaque fallback."""
import ctypes
import ctypes.wintypes
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch

from fluentpy import FluentWindow, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets


class ShellMaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.original = theme.mode
        theme.set_mode('light')
        self.window = FluentWindow('Shell material')
        self.window.set_title_bar_enabled(True)
        self.window.resize(700, 440)
        self.window.content_layout.setContentsMargins(0, 0, 0, 0)
        page = QtWidgets.QWidget()
        self.window.add_sub_interface(page, QtGui.QIcon(), 'Content', 'content')
        self.window.set_navigation_mode('expanded')
        self.window.set_navigation_width(216)
        self.window.show()
        self.app.processEvents()
        self.window.navigation_view().sidebar._width_animation.setCurrentTime(150)
        self.app.processEvents()
        self.sidebar = self.window.navigation_view().sidebar

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.original)

    def samples(self, image):
        return [image.pixelColor(point) for point in (
            QtCore.QPoint(350, 24),
            self.sidebar.mapTo(self.window, QtCore.QPoint(2, 180)),
            self.window.current_page().mapTo(self.window, QtCore.QPoint(40, 80)))]

    def test_caption_and_navigation_share_shell_while_content_has_separate_background(self):
        for mode in ('light', 'dark', 'light'):
            theme.set_mode(mode)
            self.app.processEvents()
            caption, navigation, content = self.samples(self.window.grab().toImage())
            self.assertEqual(caption, navigation)
            self.assertEqual(caption, self.window._resolved_shell_color())
            self.assertEqual(content, self.window._resolved_background_color())
            self.assertNotEqual(caption, content)

    def test_content_corner_reveals_shell_without_masking_the_native_window(self):
        stack = self.window.navigation_view().stack
        for mode in ('light', 'dark'):
            theme.set_mode(mode)
            for action in (self.window.showMaximized, self.window.showNormal):
                action()
                self.app.processEvents()
                with self.subTest(mode=mode, maximized=self.window.isMaximized()):
                    mask = stack.mask()
                    self.assertFalse(mask.contains(QtCore.QPoint(0, 0)))
                    self.assertTrue(mask.contains(QtCore.QPoint(15, 0)))
                    self.assertTrue(mask.contains(QtCore.QPoint(0, 15)))
                    self.assertTrue(mask.contains(stack.rect().bottomRight()))
                    self.assertTrue(self.window.mask().isEmpty())
                    self.assertFalse(stack.testAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow))
                    image = self.window.grab().toImage()
                    corner = stack.mapTo(self.window, QtCore.QPoint(0, 0))
                    content = stack.mapTo(self.window, QtCore.QPoint(16, 16))
                    self.assertEqual(image.pixelColor(corner), self.window._resolved_shell_color())
                    self.assertEqual(image.pixelColor(content), self.window._resolved_background_color())

    def test_material_keeps_the_content_corner_clear_and_page_interior_opaque(self):
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True), \
             patch.object(self.window, '_forward_nonclient_activation', return_value=1):
            self.window.set_backdrop_enabled(True)
            stack = self.window.navigation_view().stack
            image = self.window.grab().toImage()
            corner = stack.mapTo(self.window, QtCore.QPoint(0, 0))
            content = stack.mapTo(self.window, QtCore.QPoint(16, 16))
            self.assertEqual(image.pixelColor(corner).alpha(), 0)
            self.assertEqual(image.pixelColor(content).alpha(), 255)

    def test_material_exposes_only_shell_and_turning_off_restores_opaque_colors(self):
        changes = []
        self.window.backdropChanged.connect(changes.append)
        flags = self.window.windowFlags()
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True), \
             patch.object(self.window, '_forward_nonclient_activation', return_value=1):
            self.window.set_backdrop_enabled(True)
            self.assertTrue(self.window.backdrop_applied())
            self.assertTrue(self.window.is_backdrop_enabled())
            image = self.window.grab().toImage()
            caption, navigation, content = self.samples(image)
            self.assertEqual((caption.alpha(), navigation.alpha(), content.alpha()), (0, 0, 255))
            self.assertFalse(self.window.testAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground))
            self.assertEqual(self.window.windowFlags(), flags)
            self.assertEqual(self.window.windowOpacity(), 1.0)
            cached = self.samples(self.window._capture_theme_frame().toImage())
            self.assertTrue(all(color.alpha() == 255 for color in cached))
            self.assertEqual(cached[0], cached[1])
            self.assertEqual(self.window._backdrop_snapshot_depth, 0)
            self.window.set_backdrop_enabled(False)
        self.assertFalse(self.window.backdrop_applied())
        self.assertFalse(self.window.testAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground))
        self.assertTrue(self.window.centralWidget().autoFillBackground())
        self.assertEqual(changes, [True, False])
        self.assertTrue(all(color.alpha() == 255 for color in self.samples(self.window.grab().toImage())))

    def test_rejected_material_preserves_requested_preference_with_opaque_fallback(self):
        with patch('fluentpy.widgets.window.apply_system_backdrop', return_value=False):
            self.window.set_backdrop_enabled(True)
        self.assertTrue(self.window.is_backdrop_enabled())
        self.assertFalse(self.window.backdrop_applied())
        self.assertTrue(all(color.alpha() == 255 for color in self.samples(self.window.grab().toImage())))

    def test_offscreen_platform_never_exposes_a_transparent_shell(self):
        with patch.object(self.window, '_native_windows_platform', return_value=False), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True) as apply:
            self.window.set_backdrop_enabled(True)
            self.assertFalse(apply.call_args.args[-1])
        self.assertTrue(self.window.is_backdrop_enabled())
        self.assertFalse(self.window.backdrop_applied())
        self.assertTrue(all(color.alpha() == 255 for color in self.samples(self.window.grab().toImage())))

    def test_navigation_created_after_material_keeps_default_page_opaque(self):
        window = FluentWindow('Late navigation')
        window.set_title_bar_enabled(True)
        window.content_layout.setContentsMargins(0, 0, 0, 0)
        window.resize(700, 440)
        try:
            with patch.object(window, '_native_windows_platform', return_value=True), \
                 patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True), \
                 patch.object(window, '_forward_nonclient_activation', return_value=1):
                window.set_backdrop_enabled(True)
                window.show()
                self.app.processEvents()
                page = QtWidgets.QWidget()
                window.add_page(page, 'Late page', route='late')
                window.set_navigation_mode('expanded')
                self.app.processEvents()
                sidebar = window.navigation_view().sidebar
                self.assertFalse(sidebar.testAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent))
                image = window.grab().toImage()
                self.assertEqual(image.pixelColor(350, 24).alpha(), 0)
                self.assertEqual(image.pixelColor(sidebar.mapTo(window, QtCore.QPoint(2, 180))).alpha(), 0)
                content = image.pixelColor(page.mapTo(window, QtCore.QPoint(30, 60)))
                self.assertEqual(content.alpha(), 255)
                self.assertEqual(content, window._resolved_background_color())
        finally:
            window.close()
            window.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_disabling_material_while_hidden_restores_ordinary_painting(self):
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True), \
             patch.object(self.window, '_forward_nonclient_activation', return_value=1):
            self.window.set_backdrop_enabled(True)
            self.window.hide()
            self.window.set_backdrop_enabled(False)
        self.assertFalse(self.window.backdrop_applied())
        self.assertFalse(self.window.testAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground))
        self.assertTrue(self.window.centralWidget().autoFillBackground())

    def test_material_theme_transition_uses_opaque_frames_and_reverses_continuously(self):
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True), \
             patch.object(self.window, '_forward_nonclient_activation', return_value=1):
            self.window.set_backdrop_enabled(True)
            self.window.set_theme_transition_enabled(True)
            theme.set_mode('dark')
            transition = self.window._theme_transition
            self.assertTrue(transition.is_running())
            for frame in (transition.layer.frame, transition.layer.target_frame):
                colors = self.samples(frame.toImage())
                self.assertEqual([color.alpha() for color in colors], [255, 255, 255])
                self.assertEqual(colors[0], colors[1])
                self.assertNotEqual(colors[0], colors[2])
            transition.animation.setCurrentTime(100)
            before = self.samples(self.window.grab().toImage())
            theme.set_mode('light')
            self.assertEqual(self.samples(self.window.grab().toImage()), before)
            transition.animation.setCurrentTime(transition.duration)
            self.assertFalse(transition.is_running())
            self.assertTrue(transition.layer.frame.isNull())
            self.assertEqual([color.alpha() for color in self.samples(self.window.grab().toImage())], [0, 0, 255])

    def test_nonclient_activation_reaches_windows_only_when_material_is_applied(self):
        message = ctypes.wintypes.MSG()
        message.hWnd, message.message, message.wParam = 777, 0x0086, 1
        self.window._backdrop_enabled = self.window._backdrop_applied = True
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch.object(self.window, '_forward_nonclient_activation', return_value=5) as forward:
            self.assertEqual(self.window.nativeEvent(b'windows_generic_MSG', ctypes.addressof(message)), (True, 5))
            forward.assert_called_once_with(777, 1, 0)
            self.window._integrated_windows_frame = True
            self.assertEqual(self.window.nativeEvent(b'windows_generic_MSG', ctypes.addressof(message)), (True, 5))
            self.assertEqual(forward.call_args.args, (777, 1, -1))
            self.window._integrated_windows_frame = False
        self.window._backdrop_applied = False


if __name__ == '__main__':
    unittest.main()
