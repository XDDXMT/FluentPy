"""Native backdrop setup, rollback, and frame coexistence contracts."""
import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from fluentpy import ThemeMode
from fluentpy.qt import QtCore
from fluentpy import window_effects


class WindowEffectTests(unittest.TestCase):
    def setUp(self):
        self.widget = Mock()
        self.widget.winId.return_value = 123
        self.widget._integrated_windows_frame = False
        self.widget._backdrop_applied = False
        self.widget.isMaximized.return_value = False
        self.widget.isFullScreen.return_value = False

    def test_unsupported_platform_never_allocates_a_native_handle(self):
        with patch.object(window_effects.sys, 'platform', 'linux'):
            self.assertFalse(window_effects.apply_system_backdrop(self.widget, ThemeMode.LIGHT, True))
        self.widget.winId.assert_not_called()

    def test_success_requires_material_and_whole_client_extension(self):
        with patch.object(window_effects.sys, 'platform', 'win32'), \
                patch.object(window_effects, '_backdrop_policy_allows', return_value=True), \
                patch.object(window_effects, '_dwm_set_int', return_value=True) as attribute, \
                patch.object(window_effects, '_extend_frame', return_value=True) as extend, \
                patch.object(window_effects, '_set_window_long_ptr') as set_style:
            for mode, dark in ((ThemeMode.LIGHT, 0), (ThemeMode.DARK, 1)):
                self.assertTrue(window_effects.apply_system_backdrop(self.widget, mode, False))
                self.assertEqual(attribute.call_args_list[-4:],
                                 [call(123, 20, dark), call(123, 33, 2),
                                  call(123, 34, -1), call(123, 38, 2)])
                self.assertEqual(extend.call_args, call(123, True))
            set_style.assert_not_called()

    def test_rejected_attribute_and_extension_each_roll_back(self):
        for rejected in ('attribute', 'extension', 'exception'):
            with self.subTest(rejected=rejected), \
                    patch.object(window_effects.sys, 'platform', 'win32'), \
                    patch.object(window_effects, '_backdrop_policy_allows', return_value=True), \
                    patch.object(window_effects, '_dwm_set_int', return_value=True) as attribute, \
                    patch.object(window_effects, '_extend_frame', return_value=True) as extend:
                if rejected == 'attribute':
                    attribute.side_effect = lambda hwnd, key, value: (key, value) != (38, 2)
                elif rejected == 'extension':
                    extend.side_effect = [False, True]
                else:
                    extend.side_effect = [OSError('composition changed'), True]
                self.assertFalse(window_effects.apply_system_backdrop(self.widget, ThemeMode.DARK, True))
                self.assertEqual(attribute.call_args, call(123, 38, 1))
                self.assertEqual(extend.call_args, call(123, False, False))

    def test_disable_and_policy_change_restore_integrated_resize_inset(self):
        self.widget._integrated_windows_frame = True
        for enabled in (False, True):
            with self.subTest(enabled=enabled), \
                    patch.object(window_effects.sys, 'platform', 'win32'), \
                    patch.object(window_effects, '_backdrop_policy_allows', return_value=False) as policy, \
                    patch.object(window_effects, '_dwm_set_int', return_value=True) as attribute, \
                    patch.object(window_effects, '_extend_frame', return_value=True) as extend:
                self.assertFalse(window_effects.apply_system_backdrop(self.widget, ThemeMode.LIGHT, True, enabled))
                self.assertEqual(attribute.call_args, call(123, 38, 1))
                extend.assert_called_once_with(123, False, True)
                if not enabled:
                    policy.assert_not_called()

    def test_native_errors_leave_the_qt_fallback_available(self):
        self.widget.winId.side_effect = RuntimeError('No native handle')
        with patch.object(window_effects.sys, 'platform', 'win32'), \
                patch.object(window_effects, '_dwm_set_int') as attribute:
            self.assertFalse(window_effects.apply_system_backdrop(self.widget, ThemeMode.LIGHT, True))
            attribute.assert_not_called()

    def test_native_shape_restores_round_corners_and_default_border_after_maximize_or_fullscreen(self):
        for maximized, fullscreen in ((False, False), (True, False), (False, True), (False, False)):
            with self.subTest(maximized=maximized, fullscreen=fullscreen), \
                 patch.object(window_effects, '_dwm_set_int', return_value=True) as attribute:
                self.widget.isMaximized.return_value = maximized
                self.widget.isFullScreen.return_value = fullscreen
                self.assertTrue(window_effects._apply_window_shape(self.widget, 123))
                expanded = maximized or fullscreen
                self.assertEqual(attribute.call_args_list,
                    [call(123, 33, 1 if expanded else 2), call(123, 34, -2 if expanded else -1)])

    def test_integrated_frame_retains_resize_commands_without_duplicate_native_caption(self):
        position = Mock()
        windows_app = SimpleNamespace(platformName=lambda: 'windows')
        self.widget.windowFlags.return_value = (
            QtCore.Qt.WindowType.WindowMinimizeButtonHint |
            QtCore.Qt.WindowType.WindowMaximizeButtonHint)
        with patch.object(window_effects.sys, 'platform', 'win32'), \
             patch.object(window_effects.QtWidgets.QApplication, 'instance', return_value=windows_app), \
             patch.object(window_effects.ctypes, 'windll', SimpleNamespace(user32=SimpleNamespace(SetWindowPos=position)), create=True), \
             patch.object(window_effects, '_get_window_long_ptr', return_value=0x96cf0000), \
             patch.object(window_effects, '_set_window_long_ptr') as replace_style, \
             patch.object(window_effects, '_dwm_set_int', return_value=True) as attribute, \
             patch.object(window_effects, '_extend_frame', return_value=True) as extend:
            for applied in (False, True):
                self.widget._backdrop_applied = applied
                self.assertTrue(window_effects.apply_integrated_window_frame(self.widget, ThemeMode.LIGHT))
                replace_style.assert_called_with(123, -16, 0x960f0000)
                extend.assert_called_with(123, applied, True)
            self.assertEqual(position.call_count, 2)
            self.assertTrue(all(request.args[1] != 2 for request in attribute.call_args_list),
                            'Disabling non-client rendering would remove active Mica tint')

    def test_frame_extension_uses_documented_negative_margins_and_can_restore(self):
        margins = []
        def capture(hwnd, address):
            value = ctypes.cast(address, ctypes.POINTER(window_effects._Margins)).contents
            margins.append((hwnd, value.cxLeftWidth, value.cxRightWidth,
                            value.cyTopHeight, value.cyBottomHeight))
            return 0
        native = SimpleNamespace(DwmExtendFrameIntoClientArea=Mock(side_effect=capture))
        with patch.object(window_effects.ctypes, 'windll', SimpleNamespace(dwmapi=native), create=True):
            self.assertTrue(window_effects._extend_frame(123, True))
            self.assertTrue(window_effects._extend_frame(123, False, True))
            self.assertTrue(window_effects._extend_frame(123, False, False))
        self.assertEqual(margins, [(123, -1, -1, -1, -1), (123, 1, 1, 1, 1), (123, 0, 0, 0, 0)])

    def test_integrated_frame_preserves_mica_and_all_unrelated_window_styles(self):
        app = Mock(); app.platformName.return_value = 'windows'
        old_style = 0x90000000 | 0x00400000 | 0x00020000
        self.widget.windowFlags.return_value = (QtCore.Qt.WindowType.WindowMinimizeButtonHint
                                                | QtCore.Qt.WindowType.WindowMaximizeButtonHint)
        for applied in (True, False):
            self.widget._backdrop_applied = applied
            with self.subTest(applied=applied), \
                    patch.object(window_effects.sys, 'platform', 'win32'), \
                    patch.object(window_effects.QtWidgets.QApplication, 'instance', return_value=app), \
                    patch.object(window_effects, '_get_window_long_ptr', return_value=old_style), \
                    patch.object(window_effects, '_set_window_long_ptr') as set_style, \
                    patch.object(window_effects, '_dwm_set_int', return_value=True), \
                    patch.object(window_effects, '_extend_frame', return_value=True) as extend, \
                    patch.object(window_effects.ctypes, 'windll', Mock(), create=True):
                self.assertTrue(window_effects.apply_integrated_window_frame(self.widget, ThemeMode.LIGHT))
                extend.assert_called_once_with(123, applied, True)
                self.assertEqual(set_style.call_args, call(123, -16, (old_style & ~0x00C00000)
                                                         | 0x00040000 | 0x00080000 | 0x00010000))


class BackdropPolicyTests(unittest.TestCase):
    def setUp(self):
        def composition(address):
            ctypes.cast(address, ctypes.POINTER(ctypes.wintypes.BOOL)).contents.value = True
            return 0
        self.dwm = SimpleNamespace(DwmIsCompositionEnabled=Mock(side_effect=composition))

    def policy(self):
        return window_effects._backdrop_policy_allows()

    def test_supported_composited_system_honors_contrast_and_transparency(self):
        with patch.object(window_effects.sys, 'getwindowsversion', return_value=SimpleNamespace(build=26200), create=True), \
                patch.object(window_effects.ctypes, 'windll', SimpleNamespace(dwmapi=self.dwm), create=True), \
                patch.object(window_effects, '_high_contrast_enabled', return_value=False) as contrast, \
                patch.object(window_effects, '_transparency_effects_enabled', return_value=True) as transparency:
            self.assertTrue(self.policy())
            transparency.return_value = False
            self.assertFalse(self.policy())
            transparency.return_value = True
            for state in (True, None):
                contrast.return_value = state
                self.assertFalse(self.policy())

    def test_unsupported_composition_or_version_and_query_failure_fall_back(self):
        with patch.object(window_effects.sys, 'getwindowsversion', return_value=SimpleNamespace(build=22000), create=True), \
                patch.object(window_effects.ctypes, 'windll', SimpleNamespace(dwmapi=self.dwm), create=True), \
                patch.object(window_effects, '_high_contrast_enabled', return_value=False), \
                patch.object(window_effects, '_transparency_effects_enabled', return_value=True) as transparency:
            self.assertFalse(self.policy())
            self.dwm.DwmIsCompositionEnabled.assert_not_called()
            with patch.object(window_effects.sys, 'getwindowsversion', return_value=SimpleNamespace(build=26200)):
                self.dwm.DwmIsCompositionEnabled.side_effect = None
                self.dwm.DwmIsCompositionEnabled.return_value = -1
                self.assertFalse(self.policy())
                self.dwm.DwmIsCompositionEnabled.return_value = 0  # Leaves enabled=False.
                self.assertFalse(self.policy())
                transparency.side_effect = PermissionError('preference unavailable')
                self.dwm.DwmIsCompositionEnabled.side_effect = lambda pointer: setattr(
                    ctypes.cast(pointer, ctypes.POINTER(ctypes.wintypes.BOOL)).contents, 'value', True) or 0
                self.assertFalse(self.policy())

    def test_transparency_preference_is_read_only_and_missing_uses_system_default(self):
        registry = MagicMock()
        registry.QueryValueEx.return_value = (0, 4)
        with patch.dict('sys.modules', {'winreg': registry}):
            self.assertFalse(window_effects._transparency_effects_enabled())
            registry.QueryValueEx.return_value = (1, 4)
            self.assertTrue(window_effects._transparency_effects_enabled())
            registry.QueryValueEx.return_value = ('0', 1)
            self.assertFalse(window_effects._transparency_effects_enabled())
            registry.QueryValueEx.side_effect = FileNotFoundError()
            self.assertTrue(window_effects._transparency_effects_enabled())
        registry.SetValueEx.assert_not_called()
        registry.CreateKey.assert_not_called()


if __name__ == '__main__':
    unittest.main()
