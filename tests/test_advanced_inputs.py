import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys
import unittest

from fluentpy import AffixLineEdit, Button, LineEdit, PinCodeEdit, theme
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class AdvancedInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.old_hook = sys.excepthook
        self.errors = []
        sys.excepthook = lambda kind, error, tb: self.errors.append(error)
        self.owner = QtWidgets.QWidget()
        self.owner.resize(600, 220)
        self.layout = QtWidgets.QVBoxLayout(self.owner)
        self.owner.show()
        self.owner.activateWindow()
        self.app.processEvents()
        self.old_theme = theme.mode

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.old_theme)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def add(self, widget):
        self.layout.addWidget(widget)
        self.app.processEvents()
        return widget

    def test_affixes_are_not_editable_and_clear_only_the_middle(self):
        entry = self.add(AffixLineEdit("example.hostname", prefix="https://", suffix=".com"))
        self.assertIsInstance(entry, LineEdit)
        entry.setText("example")
        self.assertEqual(entry.text(), "example")
        self.assertEqual(entry.full_text(), "https://example.com")
        entry._clear_button.click()
        self.assertEqual(entry.text(), "")
        self.assertEqual(entry.prefix(), "https://")
        self.assertEqual(entry.suffix(), ".com")

    def test_affixes_reserve_text_and_clear_button_space_and_can_be_replaced(self):
        entry = self.add(AffixLineEdit(prefix="https://", suffix=".com"))
        entry.setText("host")
        self.assertLess(entry._prefix_label.geometry().right(), entry.textMargins().left())
        self.assertLess(
            entry._clear_button.geometry().right(), entry._suffix_label.geometry().left()
        )
        entry.set_prefix("")
        entry.set_suffix("元")
        entry.set_clear_button_enabled(False)
        self.assertTrue(entry._prefix_label.isHidden())
        self.assertEqual(entry.full_text(), "host元")
        self.assertTrue(entry._clear_button.isHidden())

    def test_long_affixes_fit_narrow_widgets_in_both_themes(self):
        entry = self.add(
            AffixLineEdit(prefix="very long prefix" * 3, suffix="very long suffix" * 3)
        )
        entry.setFixedWidth(180)
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            self.app.processEvents()
            self.assertFalse(entry.grab().isNull())
            self.assertGreaterEqual(
                entry.width() - entry.textMargins().left() - entry.textMargins().right(), 40
            )
            self.assertEqual(entry.text(), "")

    def test_pin_types_advances_and_emits_completion_without_exposing_display(self):
        pin = self.add(PinCodeEdit())
        completed = []
        pin.completed.connect(completed.append)
        for index, char in enumerate("1234"):
            cell = pin.cells()[index]
            cell.setFocus()
            QTest.keyClicks(cell, char)
            self.assertIs(self.app.focusWidget(), pin.cells()[min(index + 1, 3)])
            self.assertIsInstance(cell, LineEdit)
        self.assertEqual(pin.text(), "1234")
        self.assertTrue(pin.is_complete())
        self.assertEqual(completed, ["1234"])
        self.assertNotEqual(pin.cells()[0].displayText(), "1")
        pin.set_masked(False)
        self.assertEqual(pin.cells()[0].displayText(), "1")

    def test_pin_backspace_delete_arrows_and_empty_slots(self):
        pin = self.add(PinCodeEdit())
        pin.set_text("1234")
        cell = pin.cells()[3]
        cell.setFocus()
        QTest.keyClick(cell, QtCore.Qt.Key.Key_Backspace)
        self.assertEqual(pin.text(), "123")
        QTest.keyClick(cell, QtCore.Qt.Key.Key_Backspace)
        self.assertEqual(pin.text(), "12")
        self.assertIs(self.app.focusWidget(), pin.cells()[2])
        QTest.keyClick(pin.cells()[2], QtCore.Qt.Key.Key_Left)
        self.assertIs(self.app.focusWidget(), pin.cells()[1])
        QTest.keyClick(pin.cells()[1], QtCore.Qt.Key.Key_Delete)
        self.assertEqual(pin.text(), "1")

    def test_pin_whole_paste_replaces_from_start_and_overlong_paste_truncates(self):
        pin = self.add(PinCodeEdit())
        pin.set_text("11")
        pin.cells()[2].setFocus()
        clipboard = self.app.clipboard()
        previous = clipboard.text()
        try:
            clipboard.setText("987654")
            pin.paste()
        finally:
            clipboard.setText(previous)
        self.assertEqual(pin.text(), "9876")
        self.assertIs(self.app.focusWidget(), pin.cells()[-1])

    def test_pin_invalid_input_and_read_only_leave_value_unchanged(self):
        pin = self.add(PinCodeEdit())
        pin.set_text("12")
        rejected = []
        pin.inputRejected.connect(rejected.append)
        pin.cells()[2].setFocus()
        QTest.keyClicks(pin.cells()[2], "x")
        self.assertEqual(pin.text(), "12")
        self.assertEqual(len(rejected), 1)
        with self.assertRaises(ValueError):
            pin.set_text("1x")
        self.assertEqual(pin.text(), "12")
        pin.set_read_only(True)
        QTest.keyClicks(pin.cells()[2], "3")
        pin.cells()[2].insert("9")
        self.assertEqual(pin.text(), "12")
        pin.set_text("5678")
        self.assertEqual(pin.text(), "5678")

    def test_empty_clipboard_paste_and_insert_do_not_erase_a_cell(self):
        pin = self.add(PinCodeEdit())
        pin.set_text("1234")
        pin.cells()[0].setFocus()
        clipboard = self.app.clipboard()
        previous = clipboard.text()
        try:
            clipboard.clear()
            pin.paste()
            pin.cells()[0].paste()
            pin.cells()[0].insert("")
        finally:
            clipboard.setText(previous)
        self.assertEqual(pin.text(), "1234")

    def test_pin_unicode_ime_and_resizing_cells_preserve_qt_ownership(self):
        pin = self.add(PinCodeEdit(4, digits_only=False))
        event = QtGui.QInputMethodEvent()
        event.setCommitString("中文🙂A")
        self.app.sendEvent(pin.cells()[0], event)
        self.assertEqual(pin.text(), "中文🙂A")
        self.assertTrue(pin.is_complete())
        self.assertEqual(pin.cells()[2].text(), "🙂")
        with self.assertRaises(ValueError):
            pin.set_digits_only(True)
        self.assertFalse(pin.digits_only())
        pin.set_length(6)
        self.assertEqual(pin.length(), 6)
        self.assertEqual(pin.text(), "中文🙂A")
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertTrue(all(cell.parentWidget() is pin for cell in pin.cells()))
        self.assertFalse(any(cell.isWindow() for cell in pin.cells()))

    def test_tab_can_leave_pin_and_does_not_wrap_forever(self):
        pin = self.add(PinCodeEdit())
        after = self.add(Button("下一项"))
        pin.cells()[-1].setFocus()
        QTest.keyClick(pin.cells()[-1], QtCore.Qt.Key.Key_Tab)
        self.assertIs(self.app.focusWidget(), after)
