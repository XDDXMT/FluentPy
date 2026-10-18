"""Reference-app navigation, filtering and retained editor state."""
import os
from pathlib import Path
import sys
import unittest

os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
from showcase import Showcase,PAGES
from fluentpy.qt import QtCore,QtGui,QtWidgets,QT_API
from fluentpy import ActionMenu, theme
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.previous={widget for widget in self.app.topLevelWidgets() if widget.isVisible()}
        self.window=Showcase(restore_preferences=False,startup=False);self.window.show();QTest.qWait(350)

    def tearDown(self):
        self.window.close();self.window.deleteLater()
        self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);self.app.processEvents()

    def test_startup_is_catalog_without_automatic_tasks_or_extra_windows(self):
        self.assertEqual(self.window.navigation.current_route(),'overview')
        self.assertEqual(len(PAGES),16)
        self.assertEqual(len({key for key,_,_ in PAGES}),len(PAGES))
        visible={widget for widget in self.app.topLevelWidgets() if widget.isVisible()}-self.previous
        self.assertEqual(visible,{self.window})
        self.assertFalse(self.window._note_timer.isActive())
        self.assertIsNone(self.window._active_toast)
        self.assertFalse(hasattr(self.window,'booking_submit'))
        self.assertFalse(self.window.brand_mark.pixmap().isNull())

    def test_catalog_filters_real_component_names_and_recovers_from_empty_results(self):
        self.window.component_filter.setText('DateRangePicker');self.app.processEvents()
        self.assertEqual(sum(not card.isHidden() for card,_ in self.window.catalog_cards),1)
        self.window.component_filter.setText('no such component');self.app.processEvents()
        self.assertTrue(self.window.catalog_empty.isVisible())
        self.window.component_filter.clear();self.app.processEvents()
        self.assertEqual(sum(not card.isHidden() for card,_ in self.window.catalog_cards),len(PAGES)-2)
        self.assertFalse(self.window.catalog_empty.isVisible())

    def test_all_routes_fit_the_minimum_window_width(self):
        self.window.resize(900,650)
        for key,_,_ in PAGES:
            self.window.set_page(key,animated=False);self.app.processEvents()
            QTest.qWait(20)
            self.assertEqual(self.window.navigation.current_route(),key)
            scroll=self.window.stack.currentWidget()
            self.assertLessEqual(scroll.widget().width(),scroll.viewport().width(),key)

    def test_document_and_input_values_survive_page_switches(self):
        self.window.set_page('navigation',animated=False)
        editor=self.window._documents['notes'];editor.setPlainText('保留这份内容')
        self.window.document_tabs.set_current_tab('notes')
        self.window.set_page('cards',animated=False)
        self.window.set_page('navigation',animated=False)
        self.assertEqual(editor.toPlainText(),'保留这份内容')
        self.window._add_document();self.assertEqual(len(self.window._document_keys),3)
        self.window.set_page('wheels',animated=False)
        self.window.date_picker.set_date(QtCore.QDate(2024,2,29))
        self.window.set_page('buttons',animated=False);self.window.set_page('wheels',animated=False)
        self.assertEqual(self.window.date_picker.date(),QtCore.QDate(2024,2,29))

    def test_workbench_uses_fluent_window_history_and_a_visible_slider_route(self):
        self.assertTrue(self.window.is_title_bar_enabled())
        self.assertIs(self.window.navigation, self.window.navigation_view())
        self.assertIs(self.window.menuWidget(), self.window.title_bar())
        self.window.sidebar_search.setText('滑块')
        self.app.processEvents()
        self.assertFalse(self.window._route_buttons['sliders'].isHidden())
        QTest.keyClick(self.window.sidebar_search, QtCore.Qt.Key.Key_Return)
        self.assertEqual(self.window.current_route(), 'sliders')
        self.assertTrue(self.window.slider_examples.isVisible())
        self.assertTrue(self.window.title_bar().back_button.isEnabled())
        self.window.title_bar().back_button.click()
        self.assertEqual(self.window.current_route(), 'overview')

    def _context(self, target, point=None):
        point = point or target.rect().center()
        QtWidgets.QApplication.sendEvent(target, QtGui.QContextMenuEvent(
            QtGui.QContextMenuEvent.Reason.Mouse, point, target.mapToGlobal(point)))
        self.app.processEvents()
        menu = self.window.context_menus.menu
        self.assertIsInstance(menu, ActionMenu)
        self.assertTrue(menu._opened)
        return menu

    def test_sidebar_catalog_and_document_tabs_use_advanced_context_actions(self):
        card = next(card for card, _ in self.window.catalog_cards if card.property('componentRoute') == 'sliders')
        menu = self._context(card)
        menu._activate(next(action for action in menu.actions() if action.text() == '查看示例'))
        self.assertEqual(self.window.current_route(), 'sliders')
        self.window.set_page('navigation', animated=False)
        self.app.processEvents()
        first = self.window.document_tabs._items[0].widget
        QTest.mouseClick(first, QtCore.Qt.MouseButton.RightButton,
                         pos=QtCore.QPoint(first.width()-18, 18))
        self.assertEqual(len(self.window._document_keys), 2)
        menu = self._context(first)
        menu._activate(next(action for action in menu.actions() if action.text() == '关闭此文档'))
        self.assertEqual(len(self.window._document_keys), 1)
        self.assertEqual(len(self.window.document_tabs._items), 1)

    def test_code_editor_uses_qt_edit_actions_in_the_advanced_menu(self):
        self.window.set_page('code', animated=False)
        self.app.processEvents()
        editor = self.window.code_editor.text_edit
        editor.selectAll()
        menu = self._context(editor.viewport())
        self.assertTrue(any(action.isEnabled() and action.shortcut().matches(
            QtGui.QKeySequence.StandardKey.Copy) == QtGui.QKeySequence.SequenceMatch.ExactMatch
            for action in menu.actions()))

    def test_theme_transition_keeps_real_workbench_target_pixels_and_stable_parent_styles(self):
        self.assertTrue(self.window.is_theme_transition_enabled())
        window_style, root_style = self.window.styleSheet(), self.window.centralWidget().styleSheet()
        area = self.window.stack.currentWidget()
        background = area.viewport().mapTo(self.window, QtCore.QPoint(area.viewport().width()-30, 12))
        points = [QtCore.QPoint(300, 24), background]
        before = self.window.grab().toImage()
        self.window.theme_toggle.click()
        transition = self.window._theme_transition
        self.assertTrue(transition.is_running())
        target = transition.layer.target_frame.toImage()
        transition.animation.setCurrentTime(transition.duration//2)
        middle = self.window.grab().toImage()
        transition.animation.setCurrentTime(transition.duration)
        end = self.window.grab().toImage()
        for point in points:
            with self.subTest(point=point):
                self.assertEqual(target.pixelColor(point), end.pixelColor(point), 'Cached target must not contain black or stale regions')
                first, last, half = (image.pixelColor(point).lightness() for image in (before, end, middle))
                self.assertLess(min(first, last), half)
                self.assertLess(half, max(first, last))
        self.assertEqual(self.window.styleSheet(), window_style)
        self.assertEqual(self.window.centralWidget().styleSheet(), root_style)
        self.assertEqual(self.window.title_bar().bar_height(), 48)
        self.window.set_page('settings', animated=False)
        self.app.processEvents()
        self.window.settings_content.theme_choice.setCurrentIndex(0)
        self.assertEqual(theme.mode.value, 'light')
        self.assertTrue(transition.is_running())
        transition.finish()


if __name__=='__main__':unittest.main()
