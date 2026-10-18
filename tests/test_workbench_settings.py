"""Real preference controls, independent sidebar scrolling and persisted state."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import sys
import re
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from showcase import Showcase
from workbench_settings import DEFAULT_PREFERENCES, WorkbenchSettings, load_preferences
from fluentpy import ComboBox, Slider, ToggleSwitch, FluentScrollBar, GroupHeaderCardWidget, HyperlinkButton, TextEdit, __version__, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class WorkbenchSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.mode = theme.mode
        self.accent = theme.tokens.custom_accent
        self.temp = QtCore.QTemporaryDir()
        self.path = str(Path(self.temp.path()) / "workbench.ini")
        self.store = QtCore.QSettings(self.path, QtCore.QSettings.Format.IniFormat)
        self.window = Showcase(preferences=self.store, startup=False)
        self.window.show()
        QTest.qWait(350)
        self.form = self.window.settings_content

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)
        theme.set_accent(self.accent)
        self.temp.remove()

    def test_settings_are_existing_library_controls(self):
        self.assertIs(type(self.form.theme_choice), ComboBox)
        self.assertIs(type(self.form.accent_choice), ComboBox)
        self.assertIs(type(self.form.width_slider), Slider)
        for control in (self.form.expanded_toggle, self.form.animation_toggle,
                        self.form.backend_toggle, self.form.mica_toggle):
            self.assertIs(type(control), ToggleSwitch)
        self.assertEqual([card.title() for card in self.form.findChildren(GroupHeaderCardWidget)],
                         ["外观", "导航", "交互与状态", "关于 FluentPy"])
        self.assertIs(type(self.window.sidebar.scroll_area.verticalScrollBar()), FluentScrollBar)

    def test_mica_switch_applies_immediately_and_keeps_the_page_and_editor_contents(self):
        self.assertTrue(DEFAULT_PREFERENCES["mica_enabled"])
        self.assertTrue(self.form.mica_toggle.isChecked())
        self.assertTrue(self.window.is_backdrop_enabled())
        self.assertFalse(self.store.contains('workbench/mica_enabled'))
        self.assertEqual(self.form.mica_toggle.accessibleName(), "云母效果（Windows 11）")
        self.window.set_page('code', animated=False)
        self.window.code_editor.set_code('retained document')
        self.form.mica_toggle.click()
        self.assertFalse(self.window.is_backdrop_enabled())
        self.assertFalse(self.window._preferences['mica_enabled'])
        self.assertFalse(self.store.value('workbench/mica_enabled', True, type=bool))
        self.assertEqual(self.window.current_route(), 'code')
        self.assertEqual(self.window.code_editor.code(), 'retained document')
        self.form.mica_toggle.click()
        self.assertTrue(self.window.is_backdrop_enabled())
        self.assertTrue(self.store.value('workbench/mica_enabled', False, type=bool))
        if self.app.platformName() == 'offscreen':
            self.assertFalse(self.window.backdrop_applied())
        area = self.window.current_page()
        self.assertEqual(area.widget().palette().color(QtGui.QPalette.ColorRole.Window).alpha(), 255)
        image = area.viewport().grab().toImage()
        background = image.pixelColor(image.width() - 24, 10)
        self.assertEqual(background.alpha(), 255)
        self.assertEqual(background.name(), self.window._resolved_background_color().name())

    def test_footer_tracks_actual_material_state_without_changing_the_user_preference(self):
        original = dict(self.window._preferences)
        self.window.set_page('code', animated=False)
        self.window.code_editor.set_code('retained footer state')
        for applied in (True, False):
            with patch.object(self.window, 'backdrop_applied', return_value=applied):
                self.window.backdropChanged.emit(applied)
                expected = 'transparent' if applied else self.window._resolved_shell_color().name()
                self.assertIn('background:' + expected, self.window._footer.styleSheet())
                self.assertIn('border-top:1px solid ' + theme.tokens.border, self.window._footer.styleSheet())
                self.assertFalse(self.window._footer.autoFillBackground())
            self.assertEqual(self.window._preferences, original)
            self.assertTrue(self.form.mica_toggle.isChecked())
            self.assertTrue(self.window.is_backdrop_enabled())
            self.assertFalse(self.store.contains('workbench/mica_enabled'))
            self.assertEqual(self.window.current_route(), 'code')
            self.assertEqual(self.window.code_editor.code(), 'retained footer state')

    def test_footer_text_keeps_theme_contrast_after_mode_and_material_changes(self):
        labels = self.window._footer.findChildren(QtWidgets.QLabel)
        self.assertEqual({label.objectName() for label in labels}, {'muted', 'backendBadge', 'railCaption'})
        for index in (1, 0):
            self.form.theme_choice.setCurrentIndex(index)
            self.app.processEvents()
            expected = QtGui.QColor(theme.tokens.text_muted)
            for applied in (True, False):
                with patch.object(self.window, 'backdrop_applied', return_value=applied):
                    self.window.backdropChanged.emit(applied)
                    self.app.processEvents()
                    for label in labels:
                        self.assertEqual(label.foregroundRole(), QtGui.QPalette.ColorRole.PlaceholderText)
                        self.assertEqual(label.palette().color(label.foregroundRole()), expected,
                                         (index, applied, label.objectName()))
                        image = label.grab().toImage()
                        nearest = min(
                            max(abs(pixel.red() - expected.red()), abs(pixel.green() - expected.green()),
                                abs(pixel.blue() - expected.blue()))
                            for y in range(image.height()) for x in range(image.width())
                            if (pixel := image.pixelColor(x, y)).alpha() > 0)
                        self.assertLessEqual(nearest, 24, (index, applied, label.objectName(), nearest))

    def test_theme_and_header_switch_stay_synchronized(self):
        self.form.theme_choice.setCurrentIndex(1)
        self.assertEqual(theme.mode.value, "dark")
        self.assertTrue(self.window.theme_toggle.isChecked())
        self.window.theme_toggle.click()
        self.assertEqual(theme.mode.value, "light")
        self.assertEqual(self.form.theme_choice.currentIndex(), 0)
        self.form.accent_choice.setCurrentIndex(1)
        self.assertEqual(theme.tokens.accent, "#0078d4")
        self.form.theme_choice.setCurrentIndex(1)
        self.assertEqual(theme.tokens.accent, "#60cdff")

    def test_sidebar_width_expansion_page_motion_and_backend_visibility_apply(self):
        self.form.width_slider.setValue(248)
        self.assertEqual(self.window.sidebar.width(), 248)
        self.form.expanded_toggle.click()
        QTest.qWait(180)
        self.assertEqual(self.window.sidebar.width(), 48)
        self.assertFalse(self.window.sidebar_search.isVisible())
        self.assertTrue(self.window._route_buttons["settings"].isVisible())
        self.window.sidebar.toggle()
        QTest.qWait(180)
        self.assertTrue(self.form.expanded_toggle.isChecked())
        self.form.animation_toggle.click()
        self.window.set_page("settings")
        self.assertIsNone(self.window.stack._animation)
        self.form.backend_toggle.click()
        self.assertTrue(self.window.backend_badge.isHidden())

    def test_nav_search_keeps_settings_fixed_and_enter_navigates_to_match(self):
        self.window.resize(900, 650)
        self.app.processEvents()
        self.assertGreater(self.window.sidebar.scroll_area.verticalScrollBar().maximum(), 0)
        settings = self.window._route_buttons["settings"]
        original = settings.mapTo(self.window, QtCore.QPoint())
        self.window.sidebar_search.setText("日历")
        self.assertEqual(self.window.navigation.current_route(), "overview")
        QTest.keyClick(self.window.sidebar_search, QtCore.Qt.Key.Key_Return)
        self.assertEqual(self.window.navigation.current_route(), "calendar")
        self.assertEqual(settings.mapTo(self.window, QtCore.QPoint()), original)
        self.window.sidebar_search.setText("设置")
        QTest.keyClick(self.window.sidebar_search, QtCore.Qt.Key.Key_Return)
        self.assertEqual(self.window.navigation.current_route(), "settings")

    def test_preferences_survive_reopen_and_reset_preserves_editor_contents(self):
        self.form.theme_choice.setCurrentIndex(1)
        self.form.accent_choice.setCurrentIndex(2)
        self.form.width_slider.setValue(260)
        self.form.backend_toggle.setChecked(False)
        self.form.animation_toggle.setChecked(False)
        self.form.mica_toggle.setChecked(False)
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.window = Showcase(preferences=QtCore.QSettings(self.path, QtCore.QSettings.Format.IniFormat), startup=False)
        self.window.show()
        QTest.qWait(350)
        self.form = self.window.settings_content
        self.assertEqual(theme.mode.value, "dark")
        self.assertEqual(self.form.accent_choice.currentIndex(), 2)
        self.assertEqual(self.window.sidebar.width(), 260)
        self.assertTrue(self.window.backend_badge.isHidden())
        self.assertFalse(self.form.animation_toggle.isChecked())
        self.assertFalse(self.form.mica_toggle.isChecked())
        self.assertFalse(self.window.is_backdrop_enabled())
        self.window._documents["notes"].setPlainText("保留的文档")
        self.form.reset_button.click()
        QTest.qWait(200)
        self.assertEqual(load_preferences(self.store), DEFAULT_PREFERENCES)
        self.assertEqual(self.window._preferences, DEFAULT_PREFERENCES)
        self.assertTrue(self.form.mica_toggle.isChecked())
        self.assertTrue(self.window.is_backdrop_enabled())
        self.assertEqual(self.window._documents["notes"].toPlainText(), "保留的文档")

    def test_invalid_stored_values_fall_back_to_defaults(self):
        for key in DEFAULT_PREFERENCES:
            self.store.setValue("workbench/" + key, "invalid")
        self.assertEqual(load_preferences(self.store), DEFAULT_PREFERENCES)

    def test_about_author_and_version_match_project_metadata(self):
        metadata = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text(encoding='utf-8')
        author = re.search(r'authors\s*=\s*\[\s*\{\s*name\s*=\s*"([^"]+)"', metadata).group(1)
        self.assertEqual(self.form.author_row.title_label.text(), author)
        self.assertEqual(self.form.author_row.content_label.text(), '项目作者 · GitHub：XDDXMT')
        self.assertEqual(self.form.version_row.title_label.text(), 'FluentPy ' + __version__)
        self.assertEqual(self.form.version_row.content_label.text(), f'{QT_API} · Qt {QtCore.qVersion()}')
        self.assertFalse(self.form.declarations_card.is_expanded())

    def test_external_links_only_open_on_explicit_click_and_do_not_change_preferences(self):
        with patch.object(QtGui.QDesktopServices, 'openUrl', return_value=True) as open_url:
            form = WorkbenchSettings(DEFAULT_PREFERENCES)
            changes = []
            form.preferenceChanged.connect(lambda *args: changes.append(args))
            open_url.assert_not_called()
            expected = {
                form.documentation_link: 'https://fluentpy.mcxmcl.cn/',
                form.author_link: 'https://github.com/XDDXMT',
                form.repository_link: 'https://github.com/XDDXMT/FluentPy',
                form.issues_link: 'https://github.com/XDDXMT/FluentPy/issues',
            }
            self.assertEqual(len(form.findChildren(HyperlinkButton)), len(expected))
            for button, url in expected.items():
                self.assertIs(type(button), HyperlinkButton)
                self.assertEqual(button.url, url)
                button.click()
                self.assertEqual(open_url.call_args.args[0].toString(), url)
            self.assertEqual(open_url.call_count, len(expected))
            self.assertEqual(changes, [])
            form.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_local_notices_are_complete_plain_read_only_text(self):
        self.assertIs(type(self.form.declarations_view), TextEdit)
        self.assertTrue(self.form.declarations_view.isReadOnly())
        self.assertFalse(self.form.declarations_view.acceptRichText())
        root = Path(__file__).resolve().parents[1]
        text = self.form.declarations_view.toPlainText()
        for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
            self.assertIn((root / name).read_text(encoding='utf-8-sig').strip(), text)
        self.assertIn('Copyright (c) 2026 FluentPy contributors', text)
        self.form.declarations_card.set_expanded(True, animated=False)
        self.form.declarations_view.setFocus()
        QTest.keyClicks(self.form.declarations_view, 'read only')
        self.assertEqual(self.form.declarations_view.toPlainText(), text)

    def test_about_and_expanded_notices_fit_small_workbench_with_wide_sidebar_in_both_themes(self):
        self.window.resize(900, 650)
        self.form.width_slider.setValue(280)
        self.window.set_page('settings', animated=False)
        self.form.declarations_card.set_expanded(True, animated=False)
        for index in (0, 1):
            self.form.theme_choice.setCurrentIndex(index)
            QTest.qWait(220)
            area = self.window.stack.currentWidget()
            self.assertLessEqual(area.widget().width(), area.viewport().width())
            self.assertEqual(area.horizontalScrollBar().maximum(), 0)
            self.assertEqual(self.window.sidebar.width(), 280)
            for card in self.form.findChildren(GroupHeaderCardWidget):
                for row in card.groups():
                    if row.control is None:
                        continue
                    rect = QtCore.QRect(row.control.mapTo(self.form, QtCore.QPoint()), row.control.size())
                    self.assertGreaterEqual(rect.left(), 0)
                    self.assertLess(rect.right(), self.form.width())
            self.assertLessEqual(self.form.declarations_view.width(), self.form.width())
            links = (self.form.documentation_link, self.form.author_link,
                     self.form.repository_link, self.form.issues_link)
            painted = []
            draw_text = QtGui.QPainter.drawText
            def check_text(painter, *arguments):
                if painter.device() in links and isinstance(arguments[0], QtCore.QRectF):
                    rect, text = arguments[0], arguments[-1]
                    width = QtGui.QFontMetricsF(painter.font()).horizontalAdvance(text)
                    painted.append((text, rect.width(), width))
                return draw_text(painter, *arguments)
            with patch.object(QtGui.QPainter, 'drawText', check_text):
                for link in links:
                    self.assertFalse(link.grab().isNull())
            self.assertCountEqual([item[0] for item in painted], [link.text() for link in links])
            for text, available, required in painted:
                self.assertGreaterEqual(available, required, text)


if __name__ == "__main__":
    unittest.main()
