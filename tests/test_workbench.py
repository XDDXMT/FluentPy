"""Reference-app navigation, filtering and retained editor state."""
import os
from pathlib import Path
import sys
import unittest

os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
from showcase import Showcase,PAGES
from fluentpy.qt import QtCore,QtWidgets,QT_API
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
        self.window=Showcase();self.window.show();QTest.qWait(350)

    def tearDown(self):
        self.window.close();self.window.deleteLater()
        self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);self.app.processEvents()

    def test_startup_is_catalog_without_automatic_tasks_or_extra_windows(self):
        self.assertEqual(self.window.navigation.current_route(),'overview')
        self.assertEqual(len(PAGES),12)
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
        self.assertEqual(sum(not card.isHidden() for card,_ in self.window.catalog_cards),11)
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


if __name__=='__main__':unittest.main()
