import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sys
import unittest
from unittest.mock import patch

from fluentpy import ShortcutPicker, ShortcutDialog, theme
from fluentpy.backends import shortcut
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def text(sequence):
    return sequence.toString(QtGui.QKeySequence.SequenceFormat.PortableText)


class ShortcutPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.old_hook = sys.excepthook
        self.errors = []
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(error)
        self.old_mode = theme.mode
        self.parent = QtWidgets.QWidget()
        self.parent.resize(800, 570)
        layout = QtWidgets.QVBoxLayout(self.parent)
        self.picker = ShortcutPicker('Ctrl+Shift+A')
        layout.addWidget(self.picker)
        self.parent.show()
        self.parent.activateWindow()
        self.app.processEvents()

    def tearDown(self):
        if self.parent is not None:
            self.parent.close()
            self.parent.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.old_mode)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def editor(self):
        self.picker.open_editor()
        dialog = self.picker._editor
        dialog._fade.setCurrentTime(180)
        self.app.processEvents()
        return dialog

    def finish(self):
        QTest.qWait(130)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_roundtrip_programmatic_api_and_single_change_signals(self):
        changes, sequences = [], []
        self.picker.sequenceChanged.connect(changes.append)
        self.picker.keySequenceChanged.connect(lambda seq: sequences.append(text(seq)))
        for value in ('Alt+L', QtGui.QKeySequence('Alt+L'), ''):
            self.picker.setKeySequence(value)
        self.assertEqual(changes, ['Alt+L', ''])
        self.assertEqual(changes, sequences)
        self.assertTrue(self.picker.keySequence().isEmpty())
        self.assertIn('未设置', self.picker.key_caps.accessibleName())

    def test_record_preview_only_commits_on_save_and_contains_no_native_window(self):
        changes = []
        self.picker.sequenceChanged.connect(changes.append)
        QTest.mouseClick(self.picker.edit_button, QtCore.Qt.MouseButton.LeftButton)
        dialog = self.picker._editor
        self.assertIsNotNone(dialog)
        self.assertFalse(dialog.isWindow())
        self.assertIsNone(dialog.windowHandle())
        self.assertIs(dialog.window(), self.parent)
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_L, QtCore.Qt.KeyboardModifier.AltModifier)
        self.assertEqual(text(dialog.key_sequence()), 'Alt+L')
        self.assertEqual(text(self.picker.key_sequence()), 'Ctrl+Shift+A')
        self.assertEqual(changes, [])
        QTest.mouseClick(dialog.yes_button, QtCore.Qt.MouseButton.LeftButton)
        self.finish()
        self.assertEqual(changes, ['Alt+L'])
        self.assertEqual(text(self.picker.key_sequence()), 'Alt+L')
        self.assertIsNone(self.picker._editor)

    def test_cancel_reset_and_clear_are_transactional(self):
        dialog = self.editor()
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_L, QtCore.Qt.KeyboardModifier.AltModifier)
        QTest.mouseClick(dialog.reset_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(text(dialog.key_sequence()), 'Ctrl+Shift+A')
        dialog.clear()
        self.assertTrue(dialog.key_sequence().isEmpty())
        dialog.reject()
        self.finish()
        self.assertEqual(text(self.picker.key_sequence()), 'Ctrl+Shift+A')
        dialog = self.editor()
        dialog.clear()
        dialog.accept()
        self.finish()
        self.assertTrue(self.picker.key_sequence().isEmpty())

    def test_reserved_conflict_blocks_save_then_valid_key_reenables_it(self):
        self.picker.set_reserved_sequences(['Ctrl+S', 'Ctrl+O'])
        dialog = self.editor()
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_S, QtCore.Qt.KeyboardModifier.ControlModifier)
        self.assertFalse(dialog.yes_button.isEnabled())
        self.assertIn('占用', dialog.message_label.text())
        dialog.accept()
        self.assertTrue(dialog.isVisible())
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_F9)
        self.assertTrue(dialog.yes_button.isEnabled())
        dialog.accept()
        self.finish()
        self.assertEqual(text(self.picker.key_sequence()), 'F9')
        with self.assertRaises(ValueError):
            self.picker.set_key_sequence('Ctrl+S')
        copies = self.picker.reserved_sequences()
        copies.clear()
        self.assertEqual(len(self.picker.reserved_sequences()), 2)

    def test_return_is_recorded_when_listening_but_activates_save_when_button_focused(self):
        dialog = self.editor()
        modifiers = QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_Return, modifiers)
        self.assertEqual(text(dialog.key_sequence()), 'Ctrl+Shift+Return')
        self.assertFalse(dialog._finished)
        dialog.yes_button.setFocus()
        QTest.keyClick(dialog.yes_button, QtCore.Qt.Key.Key_Return)
        self.finish()
        self.assertEqual(text(self.picker.key_sequence()), 'Ctrl+Shift+Return')

    def test_modifier_only_preview_and_auto_repeat_do_not_replace_candidate(self):
        dialog = self.editor()
        QTest.keyPress(dialog.recorder, QtCore.Qt.Key.Key_Control)
        self.assertEqual(text(dialog.key_sequence()), 'Ctrl+Shift+A')
        QTest.keyRelease(dialog.recorder, QtCore.Qt.Key.Key_Control)
        event = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_L,
                               QtCore.Qt.KeyboardModifier.AltModifier, 'l', True, 5)
        self.app.sendEvent(dialog.recorder, event)
        self.assertEqual(text(dialog.key_sequence()), 'Ctrl+Shift+A')

    def test_tab_focus_stays_inside_dialog_and_escape_discards(self):
        dialog = self.editor()
        for _ in range(9):
            focus = self.app.focusWidget()
            QTest.keyClick(focus, QtCore.Qt.Key.Key_Tab)
            self.assertTrue(dialog.isAncestorOf(self.app.focusWidget()))
        QTest.keyClick(self.app.focusWidget(), QtCore.Qt.Key.Key_Backtab, QtCore.Qt.KeyboardModifier.ShiftModifier)
        self.assertTrue(dialog.isAncestorOf(self.app.focusWidget()))
        QTest.keyClick(self.app.focusWidget(), QtCore.Qt.Key.Key_Escape)
        self.finish()
        self.assertIsNone(self.picker._editor)
        self.assertEqual(text(self.picker.key_sequence()), 'Ctrl+Shift+A')

    def test_application_shortcut_override_is_scoped_and_removed_after_close(self):
        dialog = self.editor()
        def override(target):
            event = QtGui.QKeyEvent(QtCore.QEvent.Type.ShortcutOverride, QtCore.Qt.Key.Key_S,
                                   QtCore.Qt.KeyboardModifier.ControlModifier)
            event.setAccepted(False)
            self.app.sendEvent(target, event)
            return event.isAccepted()
        self.assertTrue(override(self.parent))
        other = QtWidgets.QWidget()
        try:
            self.assertFalse(override(other))
        finally:
            other.deleteLater()
        dialog.reject()
        self.finish()
        self.assertFalse(override(self.parent))

    def test_real_window_shortcut_is_suspended_while_recording_and_restored(self):
        triggered = []
        action = QtGui.QShortcut(QtGui.QKeySequence('Ctrl+Shift+A'), self.parent)
        action.activated.connect(lambda: triggered.append(True))
        self.picker.setFocus()
        QTest.qWait(20)
        modifiers = QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier
        QTest.keyClick(self.picker, QtCore.Qt.Key.Key_A, modifiers)
        self.assertEqual(triggered, [True])
        dialog = self.editor()
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_A, modifiers)
        self.assertEqual(triggered, [True])
        dialog.reject()
        self.finish()
        self.picker.setFocus()
        QTest.keyClick(self.picker, QtCore.Qt.Key.Key_A, modifiers)
        self.assertEqual(triggered, [True, True])

    def test_deleting_trigger_closes_editor_even_when_owner_survives(self):
        dialog = self.editor()
        closed = []
        dialog.destroyed.connect(lambda: closed.append(True))
        self.picker.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(closed, [True])
        self.parent.resize(900, 650)
        self.app.processEvents()

    def test_disable_hide_and_parent_hide_dismiss_without_commit_or_resurrection(self):
        for action in ('disable', 'hide-picker', 'hide-parent'):
            with self.subTest(action=action):
                self.parent.show()
                self.picker.show()
                self.picker.setEnabled(True)
                dialog = self.editor()
                destroyed = []
                dialog.destroyed.connect(lambda: destroyed.append(True))
                QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_Z)
                if action == 'disable':
                    self.picker.setEnabled(False)
                elif action == 'hide-picker':
                    self.picker.hide()
                else:
                    self.parent.hide()
                self.app.processEvents()
                self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
                self.assertEqual(destroyed, [True])
                self.assertEqual(text(self.picker.key_sequence()), 'Ctrl+Shift+A')
                self.parent.show()
                self.app.processEvents()
                self.assertIsNone(self.picker._editor)

    def test_parent_destruction_and_theme_changes_leave_no_callback(self):
        self.editor()
        self.parent.deleteLater()
        self.parent = None
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        for mode in ('light', 'dark'):
            theme.set_mode(mode)
            self.app.processEvents()
        QTest.qWait(230)

    def test_dialog_repeated_open_and_owner_resize(self):
        dialog = self.editor()
        self.picker.open_editor()
        self.assertIs(self.picker._editor, dialog)
        self.assertEqual(len(self.parent.findChildren(ShortcutDialog)), 1)
        for size in ((600, 450), (420, 350), (800, 570)):
            self.parent.resize(*size)
            self.app.processEvents()
            self.assertEqual(dialog.geometry(), self.parent.rect())
            self.assertTrue(dialog.rect().contains(dialog._panel.geometry()))
            self.assertIsNone(dialog.windowHandle())

    def test_long_keycaps_and_conflict_follow_theme(self):
        self.picker.set_key_sequence('Ctrl+Alt+Shift+Meta+Print')
        self.picker.set_reserved_sequences(['Ctrl+S'])
        dialog = self.editor()
        QTest.keyClick(dialog.recorder, QtCore.Qt.Key.Key_S, QtCore.Qt.KeyboardModifier.ControlModifier)
        for mode in ('light', 'dark'):
            theme.set_mode(mode)
            self.app.processEvents()
            self.assertFalse(dialog.yes_button.isEnabled())
            self.assertIn('占用', dialog.message_label.text())
            self.assertFalse(dialog.grab().isNull())
            self.assertIn('Microsoft YaHei UI', dialog.recorder.font().families())

    def test_invalid_and_missing_c_inputs_do_not_allocate_partial_widgets(self):
        before = len(self.parent.findChildren(QtWidgets.QWidget))
        for value in ('Ctrl+K, Ctrl+C', 'Ctrl+', 'NoSuchKey123', 123, object()):
            with self.subTest(value=str(value)), self.assertRaises((TypeError, ValueError)):
                ShortcutPicker(value, self.parent)
        with patch.object(shortcut, '_extension', None), patch.dict(os.environ, {'FLUENTPY_BACKEND': 'native'}):
            with self.assertRaises(RuntimeError):
                ShortcutPicker('Ctrl+A', self.parent)
        self.assertEqual(len(self.parent.findChildren(QtWidgets.QWidget)), before)

    def test_constructing_and_showing_never_displays_an_orphan_label(self):
        shown = []
        class Monitor(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.Type.Show and isinstance(obj, QtWidgets.QLabel) and obj.isWindow():
                    shown.append(obj.text())
                return False
        monitor = Monitor()
        self.app.installEventFilter(monitor)
        try:
            self.editor()
            self.assertEqual(shown, [])
        finally:
            self.app.removeEventFilter(monitor)


if __name__ == '__main__':
    unittest.main()
