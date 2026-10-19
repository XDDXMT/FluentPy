"""The window example opens on request and keeps real Qt page state."""

import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from fluent_window import MODES, WindowDemo, WindowExamples

from fluentpy import Button, CheckBox, ComboBox, FluentWindow, LineEdit, TextEdit
from fluentpy.qt import QtCore, QtGui, QtWidgets


class WindowDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.previous_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: self.errors.append(str(value))
        self.owner = QtWidgets.QWidget()
        self.owner.resize(900, 650)
        layout = QtWidgets.QVBoxLayout(self.owner)
        self.examples = WindowExamples()
        layout.addWidget(self.examples)
        self.owner.show()
        self.app.processEvents()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.previous_hook
        self.assertEqual(self.errors, [])

    def test_configuration_is_native_and_does_not_open_a_window_automatically(self):
        self.assertIsNone(self.examples.demo_window)
        self.assertIsInstance(self.examples.mode_combo, ComboBox)
        self.assertIsInstance(self.examples.title_bar_check, CheckBox)
        self.assertIsInstance(self.examples.open_button, Button)
        self.assertEqual([w for w in self.owner.findChildren(FluentWindow)], [])

    def test_launch_reuses_the_same_real_window_and_reopening_after_close_is_safe(self):
        self.examples.mode_combo.setCurrentIndex(MODES.index("top"))
        window = self.examples.open_window()
        self.app.processEvents()
        self.assertIsInstance(window, WindowDemo)
        self.assertTrue(window.isWindow())
        self.assertEqual(window.navigation_mode(), "top")
        self.assertIs(window.parentWidget(), self.owner)
        self.assertIs(self.examples.open_window(), window)
        window.close()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertIsNone(self.examples.demo_window)
        replacement = self.examples.open_window()
        self.assertIsNot(replacement, window)

    def test_document_state_survives_history_and_all_layout_changes(self):
        window = self.examples.open_window()
        self.assertIsInstance(window.document_name, LineEdit)
        self.assertIsInstance(window.document_editor, TextEdit)
        window.switch_to("documents", animated=False)
        window.document_editor.setPlainText("保留真实编辑内容")
        for mode in MODES:
            window.mode_combo.setCurrentIndex(MODES.index(mode))
            window.switch_to("settings", animated=False)
            self.assertTrue(window.go_back())
            self.assertEqual(window.current_route(), "documents")
            self.assertEqual(window.document_editor.toPlainText(), "保留真实编辑内容")
        window.save_button.click()
        self.assertIn("已记录文档", window.activity_log.toPlainText())

    def test_titlebar_search_and_native_titlebar_toggle_keep_content(self):
        window = self.examples.open_window()
        window._title_search.setText("项目说明")
        window._title_search.returnPressed.emit()
        self.assertEqual(window.current_route(), "documents")
        search = window._title_search
        window.title_bar_check.setChecked(False)
        self.assertFalse(window.is_title_bar_enabled())
        window.title_bar_check.setChecked(True)
        self.assertTrue(window.is_title_bar_enabled())
        self.assertIs(window._title_search, search)
        self.assertEqual(search.text(), "项目说明")
        self.assertIs(window.current_page(), window._pages["documents"])

    def test_mica_and_solid_background_choices_stay_synchronized_and_keep_documents(self):
        self.assertTrue(self.examples.backdrop_check.isChecked())
        self.assertEqual(self.examples.backdrop_check.text(), "云母效果（Windows 11）")
        self.examples.background_check.setChecked(True)
        self.assertFalse(self.examples.backdrop_check.isChecked())
        window = self.examples.open_window()
        self.assertFalse(window.is_backdrop_enabled())
        self.assertTrue(window.background_check.isChecked())
        self.assertEqual(window._background_colors[0].name(), "#eef3f8")
        window.switch_to("documents", animated=False)
        window.document_editor.setPlainText("保留云母切换前的文档")
        window.backdrop_check.setChecked(True)
        self.assertTrue(window.is_backdrop_enabled())
        self.assertFalse(window.background_check.isChecked())
        self.assertIsNone(window._background_colors)
        window.background_check.setChecked(True)
        self.assertFalse(window.is_backdrop_enabled())
        self.assertFalse(window.backdrop_check.isChecked())
        self.examples.backdrop_check.setChecked(True)
        self.assertFalse(self.examples.background_check.isChecked())
        self.assertIs(self.examples.open_window(), window)
        self.assertTrue(window.is_backdrop_enabled())
        self.assertTrue(window.backdrop_check.isChecked())
        self.assertFalse(window.background_check.isChecked())
        self.assertEqual(window.current_route(), "documents")
        self.assertEqual(window.document_editor.toPlainText(), "保留云母切换前的文档")
        for area in window._pages.values():
            self.assertTrue(area.widget().autoFillBackground())
            self.assertEqual(
                area.widget().palette().color(QtGui.QPalette.ColorRole.Window).alpha(), 255
            )


if __name__ == "__main__":
    unittest.main()
