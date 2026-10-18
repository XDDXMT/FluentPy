"""Existing Qt editor actions, scoped routing and safe menu lifetimes."""
import os
from pathlib import Path
import sys
import unittest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
from workbench_context_menus import WorkbenchContextMenus
from fluentpy import ActionMenu, CodeEdit, EditableComboBox, LineEdit, PinCodeEdit, SpinBox, TextEdit
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class WorkbenchContextMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.previous_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: self.errors.append(str(value))
        self.root = QtWidgets.QWidget()
        self.root.resize(850, 700)
        self.body = QtWidgets.QVBoxLayout(self.root)
        self.line = LineEdit()
        self.line.setText('alpha beta')
        self.body.addWidget(self.line)
        self.manager = WorkbenchContextMenus(self.root)
        self.root.show()
        self.app.processEvents()

    def flush(self):
        for _ in range(2):
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            self.app.processEvents()

    def tearDown(self):
        self.manager.close()
        self.root.close()
        self.root.deleteLater()
        self.flush()
        sys.excepthook = self.previous_hook
        self.assertEqual(self.errors, [])

    def open(self, widget=None, *, keyboard=False, point=None):
        widget = widget or self.line
        point = point or QtCore.QPoint(28, 16)
        reason = QtGui.QContextMenuEvent.Reason.Keyboard if keyboard else QtGui.QContextMenuEvent.Reason.Mouse
        event = QtGui.QContextMenuEvent(reason, point, widget.mapToGlobal(point))
        QtWidgets.QApplication.sendEvent(widget, event)
        self.assertTrue(event.isAccepted())
        self.assertIsInstance(self.manager.menu, ActionMenu)
        self.assertTrue(self.manager.menu._opened)
        self.manager.menu._reveal.setCurrentTime(self.manager.menu.SHOW_DURATION)
        return self.manager.menu

    def action(self, name):
        return next(action for action in self.manager.menu.actions() if action.objectName() == name)

    def finish(self):
        self.manager.menu.dismiss(immediate=True)
        self.flush()

    def test_native_actions_are_reused_and_copy_paste_undo_keep_qt_behavior(self):
        self.line.setFocus()
        self.line.setSelection(0, 5)
        menu = self.open()
        native = self.manager.native_menu
        copy = self.action('edit-copy')
        self.assertIn(copy, native.actions())
        self.assertIs(copy.parent(), native)
        self.assertEqual(copy.text(), '复制')
        menu._activate(copy)
        self.assertEqual(self.app.clipboard().text(), 'alpha')
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        self.line.setCursorPosition(len(self.line.text()))
        self.app.clipboard().setText('!')
        menu = self.open()
        menu._activate(self.action('edit-paste'))
        self.assertEqual(self.line.text(), 'alpha beta!')
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        menu = self.open()
        self.assertTrue(self.action('edit-undo').isEnabled())
        menu._activate(self.action('edit-undo'))
        self.assertEqual(self.line.text(), 'alpha beta')

    def test_readonly_and_password_fields_keep_native_action_restrictions(self):
        self.line.setReadOnly(True)
        self.line.selectAll()
        self.open()
        self.assertTrue(self.action('edit-copy').isEnabled())
        self.assertFalse(any(a.isEnabled() for a in self.manager.menu.actions() if a.objectName() in ('edit-cut', 'edit-paste', 'edit-delete')))
        self.finish()
        self.line.setReadOnly(False)
        self.line.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.line.selectAll()
        self.open()
        self.assertFalse(self.action('edit-copy').isEnabled())
        self.assertFalse(self.action('edit-cut').isEnabled())

    def test_standard_chinese_action_labels_fit_beside_their_native_shortcuts(self):
        menu = self.open()
        self.app.processEvents()
        for row in menu._items:
            label = row.action.text()
            shortcut = row.action.shortcut().toString(QtGui.QKeySequence.SequenceFormat.NativeText)
            shortcut_width = row.fontMetrics().horizontalAdvance(shortcut) if shortcut else 0
            # The rendered action row reserves its icon/check column and the
            # shortcut column. Verify the actual remaining label can fit.
            rect = row._paint_rect()
            available = round(rect.right() - (rect.left() + 35) - 12 - shortcut_width - (18 if shortcut else 0))
            self.assertEqual(row.fontMetrics().elidedText(label, QtCore.Qt.TextElideMode.ElideRight, available), label)

    def test_dynamic_code_text_spin_combo_and_pin_editors_are_found_without_hooks(self):
        code = CodeEdit()
        text = TextEdit()
        spin = SpinBox()
        combo = EditableComboBox()
        pin = PinCodeEdit(4, masked=False)
        for widget in (code, text, spin, combo, pin):
            self.body.addWidget(widget)
        self.app.processEvents()
        targets = (code.text_edit.viewport(), text.viewport(), spin.lineEdit(), combo.lineEdit(), pin.cells()[0])
        sources = (code.text_edit, text, spin.lineEdit(), combo.lineEdit(), pin.cells()[0])
        for target, source in zip(targets, sources):
            self.open(target)
            self.assertIs(self.manager.current_source, source)
            self.finish()
        self.app.clipboard().setText('1234')
        self.open(pin.cells()[0])
        self.manager.menu._activate(self.action('edit-paste'))
        self.assertEqual(pin.text(), '1234')

    def test_keyboard_context_menu_uses_caret_and_its_native_shortcut_works(self):
        self.line.setFocus()
        self.line.setSelection(6, 4)
        QTest.keyClick(self.line, QtCore.Qt.Key.Key_F10, QtCore.Qt.KeyboardModifier.ShiftModifier)
        menu = self.manager.menu
        self.assertTrue(menu._opened)
        self.assertEqual(menu._context_position, self.manager._caret_point(self.line))
        menu._reveal.setCurrentTime(menu.SHOW_DURATION)
        QTest.keyClick(self.app.focusWidget(), QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.app.clipboard().text(), 'beta')
        self.assertTrue(menu._closing)

    def test_registered_parent_bubbles_from_children_and_uses_local_coordinates(self):
        card = QtWidgets.QFrame()
        layout = QtWidgets.QVBoxLayout(card)
        label = QtWidgets.QLabel('卡片标题')
        nested = LineEdit()
        layout.addWidget(label)
        layout.addWidget(nested)
        self.body.addWidget(card)
        self.app.processEvents()
        points, calls = [], []
        def build(menu, point):
            points.append(point)
            menu.add_action('查看示例', callback=lambda: calls.append(True))
        self.manager.register(card, build)
        point = QtCore.QPoint(12, 10)
        menu = self.open(label, point=point)
        self.assertEqual(points, [label.mapTo(card, point)])
        menu._activate(menu.actions()[0])
        self.assertEqual(calls, [True])
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        self.open(nested)
        self.assertIs(self.manager.current_source, nested)
        self.assertEqual(len(points), 1)

    def test_copy_selected_item_view_values_has_no_destructive_actions(self):
        view = QtWidgets.QTableWidget(2, 2)
        for row in range(2):
            for column in range(2):
                view.setItem(row, column, QtWidgets.QTableWidgetItem(f'{row},{column}'))
        self.body.addWidget(view)
        self.app.processEvents()
        view.selectAll()
        menu = self.open(view.viewport())
        self.assertEqual([action.objectName() for action in menu.actions()], ['view-copy'])
        menu._activate(menu.actions()[0])
        self.assertEqual(self.app.clipboard().text(), '0,0\t0,1\n1,0\t1,1')

    def test_original_native_actions_live_until_exit_animation_finishes(self):
        menu = self.open()
        native = self.manager.native_menu
        native_destroyed = []
        native.destroyed.connect(lambda: native_destroyed.append(True))
        menu.dismiss()
        self.app.processEvents()
        self.assertIs(self.manager.native_menu, native)
        self.assertEqual(native_destroyed, [])
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        self.assertIsNone(self.manager.native_menu)
        self.assertEqual(native_destroyed, [True])
        self.assertEqual(menu.actions(), [])

    def test_spin_arrow_region_keeps_native_editing_and_step_limits(self):
        spin = SpinBox()
        spin.setRange(0, 2)
        spin.setValue(1)
        self.body.addWidget(spin)
        self.app.processEvents()
        menu = self.open(spin, point=QtCore.QPoint(spin.width() - 5, 8))
        self.assertIs(self.manager.current_source, spin)
        self.assertIn(self.action('edit-copy'), self.manager.native_menu.actions())
        menu._activate(self.action('spin-step-up'))
        self.assertEqual(spin.value(), 2)
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        self.open(spin)
        self.assertFalse(self.action('spin-step-up').isEnabled())
        self.finish()
        spin.setReadOnly(True)
        self.open(spin)
        self.assertFalse(self.action('spin-step-up').isEnabled())
        self.assertFalse(self.action('spin-step-down').isEnabled())

    def test_native_scrollbar_menu_uses_qt_actions_and_inverted_position_mapping(self):
        scroll = QtWidgets.QScrollBar(QtCore.Qt.Orientation.Horizontal)
        scroll.setRange(0, 100)
        scroll.setPageStep(10)
        scroll.setSingleStep(3)
        self.body.addWidget(scroll)
        self.app.processEvents()
        menu = self.open(scroll, point=QtCore.QPoint(scroll.width() // 4, 5))
        self.assertIs(self.manager.current_source, scroll)
        menu._activate(self.action('scroll-step-add'))
        self.assertEqual(scroll.value(), 3)
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        point = QtCore.QPoint(scroll.width() // 4, 5)
        menu = self.open(scroll, point=point)
        menu._activate(self.action('scroll-here'))
        regular = scroll.value()
        self.assertLess(regular, 50)
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        scroll.setInvertedAppearance(True)
        menu = self.open(scroll, point=point)
        menu._activate(self.action('scroll-here'))
        self.assertGreater(scroll.value(), 50)
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.flush()
        scroll.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self.assertIsNone(self.manager._target(scroll))

    def test_dialog_teardown_recreates_the_reparented_menu_without_stale_wrappers(self):
        dialog = QtWidgets.QDialog(self.root)
        layout = QtWidgets.QVBoxLayout(dialog)
        field = LineEdit()
        layout.addWidget(field)
        dialog.show()
        self.app.processEvents()
        previous = self.open(field)
        self.assertIs(previous.parentWidget(), dialog)
        dialog.close()
        dialog.deleteLater()
        self.flush()
        self.assertIsNone(self.manager.menu)
        current = self.open(self.line)
        self.assertIsNot(current, previous)
        self.assertIs(current.parentWidget(), self.root)

    def test_other_windows_and_existing_action_menu_editors_are_not_hijacked(self):
        foreign = QtWidgets.QWidget()
        foreign_field = LineEdit(parent=foreign)
        foreign.resize(300, 100)
        foreign.show()
        self.app.processEvents()
        self.assertIsNone(self.manager._target(foreign_field))
        advanced = ActionMenu(self.root)
        field = LineEdit()
        advanced.add_widget(field)
        advanced.popup(self.line)
        self.assertIsNone(self.manager._target(field))
        advanced.dismiss(immediate=True)
        foreign.close()
        foreign.deleteLater()
        self.flush()

    def test_repeated_requests_and_unregister_close_do_not_accumulate_native_menus(self):
        for _ in range(12):
            self.open()
            self.finish()
        self.assertEqual(self.root.findChildren(QtWidgets.QMenu), [])
        target = QtWidgets.QLabel('注册目标', self.root)
        self.manager.register(target, lambda menu, point: menu.add_action('测试'))
        target.deleteLater()
        self.flush()
        self.assertEqual(self.manager._registrations, {})
        self.manager.close()
        self.manager.close()
        self.flush()
        self.assertTrue(self.manager._closed)
        self.assertIsNone(self.manager.menu)


if __name__ == '__main__':
    unittest.main()
