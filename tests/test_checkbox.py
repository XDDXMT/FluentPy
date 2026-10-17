import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sys
import unittest

from fluentpy import CheckBox, theme
from fluentpy.qt import QT_API, QtCore, QtWidgets

if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class CheckBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(error)
        self.old_mode = theme.mode
        self.window = QtWidgets.QWidget()
        self.window.resize(300, 180)
        self.check = CheckBox('Other files', self.window, description='760.0 KB')
        self.check.move(16, 16)
        self.check.resize(self.check.sizeHint())
        self.window.show()
        self.window.activateWindow()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.old_mode)
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_description_click_toggles_once_with_native_signals(self):
        clicks, toggles, states = [], [], []
        self.check.clicked.connect(lambda checked=False: clicks.append(checked))
        self.check.toggled.connect(toggles.append)
        self.check.stateChanged.connect(states.append)
        QTest.mouseClick(self.check, QtCore.Qt.MouseButton.LeftButton,
                         pos=QtCore.QPoint(50, self.check.height()-8))
        self.assertTrue(self.check.isChecked())
        self.assertEqual(len(clicks), 1)
        self.assertEqual(toggles, [True])
        self.assertEqual(states, [QtCore.Qt.CheckState.Checked.value])

    def test_title_and_indicator_click_and_keyboard_space(self):
        QTest.mouseClick(self.check, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(45, 12))
        self.assertTrue(self.check.isChecked())
        QTest.mouseClick(self.check, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(12, 12))
        self.assertFalse(self.check.isChecked())
        self.check.clearFocus()
        self.check.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
        self.assertTrue(self.check.hasFocus())
        QTest.keyClick(self.check, QtCore.Qt.Key.Key_Space)
        self.assertTrue(self.check.isChecked())

    def test_description_updates_accessibility_geometry_and_can_be_removed(self):
        toggles = []
        self.check.toggled.connect(toggles.append)
        self.check.setChecked(True)
        self.assertEqual(self.check.accessibleDescription(), '760.0 KB')
        described_height = self.check.sizeHint().height()
        self.check.setDescription('A much longer secondary description')
        self.assertEqual(self.check.description(), 'A much longer secondary description')
        self.assertGreater(self.check.sizeHint().width(), 150)
        self.assertEqual(self.check.accessibleDescription(), self.check.description())
        self.check.set_description('')
        self.assertLess(self.check.sizeHint().height(), described_height)
        self.assertEqual(self.check.minimumHeight(), self.check.sizeHint().height())
        self.assertEqual(self.check.accessibleDescription(), '')
        self.assertTrue(self.check.isChecked())
        self.assertEqual(toggles, [True])

    def test_tristate_still_cycles_with_description(self):
        self.check.setTristate(True)
        expected = [QtCore.Qt.CheckState.PartiallyChecked, QtCore.Qt.CheckState.Checked, QtCore.Qt.CheckState.Unchecked]
        for state in expected:
            self.check.click()
            self.assertEqual(self.check.checkState(), state)
        self.assertFalse(self.check.isChecked())

    def test_disabled_control_does_not_activate_in_either_theme(self):
        self.check.setChecked(True)
        self.check.setEnabled(False)
        toggles = []
        self.check.toggled.connect(toggles.append)
        for mode in ('light', 'dark'):
            theme.set_mode(mode)
            QTest.mouseClick(self.check, QtCore.Qt.MouseButton.LeftButton)
            QTest.keyClick(self.check, QtCore.Qt.Key.Key_Space)
            self.check.click()
            self.assertFalse(self.check.grab().isNull())
            self.assertTrue(self.check.isChecked())
        self.assertEqual(toggles, [])

    def test_large_font_narrow_layout_and_rtl_remain_operable(self):
        font = self.check.font()
        original_height = self.check.minimumHeight()
        font.setPixelSize(24)
        self.check.setFont(font)
        self.assertGreater(self.check.minimumHeight(), original_height)
        self.check.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self.check.resize(90, self.check.minimumHeight())
        self.assertFalse(self.check.grab().isNull())
        QTest.mouseClick(self.check, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(75, 15))
        self.assertTrue(self.check.isChecked())


if __name__ == '__main__':
    unittest.main()
