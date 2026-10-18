"""Cascades, native widget rows, context anchors and real tray menu support."""
import os
from pathlib import Path
import sys
import unittest
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from fluentpy import ActionMenu, SystemTrayMenu, Button, LineEdit, Slider, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class MenuExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.owner = QtWidgets.QWidget()
        self.owner.resize(900, 620)
        self.anchor = Button('菜单', self.owner)
        self.anchor.setGeometry(60, 80, 140, 34)
        self.menu = ActionMenu(self.owner)
        self.owner.show()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def open(self):
        self.assertTrue(self.menu.popup(self.anchor))
        self.menu._reveal.setCurrentTime(self.menu.SHOW_DURATION)
        self.app.processEvents()

    def test_short_native_edit_labels_keep_full_text_beside_shortcuts(self):
        for label, shortcut in (('复制', 'Ctrl+C'), ('全选', 'Ctrl+A'), ('撤销', 'Ctrl+Z')):
            self.menu.add_action(label, shortcut=shortcut)
        self.open()
        for row in self.menu._items:
            metrics = row.fontMetrics()
            shortcut = row.action.shortcut().toString(QtGui.QKeySequence.SequenceFormat.NativeText)
            available = row.width() - 1 - 10 - 25 - 12 - metrics.horizontalAdvance(shortcut) - 18
            self.assertGreaterEqual(available, metrics.horizontalAdvance(row.action.text()))

    def test_cascade_keyboard_leaf_triggers_once_and_closes_every_level(self):
        sub = self.menu.add_menu('导出')
        nested = sub.add_menu('图像')
        leaf = nested.add_action('PNG')
        calls = []
        self.menu.triggered.connect(calls.append)
        self.open()
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Right)
        self.assertTrue(sub._opened)
        sub._reveal.setCurrentTime(sub.SHOW_DURATION)
        QTest.keyClick(sub, QtCore.Qt.Key.Key_Right)
        self.assertTrue(nested._opened)
        nested._reveal.setCurrentTime(nested.SHOW_DURATION)
        QTest.keyClick(nested, QtCore.Qt.Key.Key_Return)
        self.menu._reveal.setCurrentTime(self.menu.HIDE_DURATION)
        self.assertEqual(calls, [leaf])
        self.assertFalse(any(menu._opened for menu in (self.menu, sub, nested)))

    def test_parent_rows_remain_clickable_and_left_returns_without_triggering(self):
        sub = self.menu.add_menu('更多')
        sub.add_action('子项')
        normal = self.menu.add_action('普通动作')
        calls = []
        normal.triggered.connect(lambda: calls.append(True))
        self.open()
        self.menu._open_active_submenu()
        sub._reveal.setCurrentTime(sub.SHOW_DURATION)
        self.assertFalse(sub.mask().contains(self.menu._surface.geometry().topLeft()))
        QTest.keyClick(sub, QtCore.Qt.Key.Key_Left)
        self.assertFalse(sub._opened)
        self.assertTrue(self.menu._opened)
        self.menu._select(0)
        self.menu._open_active_submenu()
        QTest.mouseClick(self.menu._items[1], QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(calls, [True])

    def test_submenu_flips_at_right_edge_and_rejects_cycles_or_sharing(self):
        sub = self.menu.add_menu('子菜单')
        sub.add_action('第一项')
        self.anchor.move(730, 100)
        self.open()
        self.menu._open_active_submenu()
        sub._reveal.setCurrentTime(sub.SHOW_DURATION)
        self.assertTrue(self.owner.rect().contains(sub._surface.geometry()))
        self.assertLess(sub._surface.x(), self.menu._surface.x())
        with self.assertRaises(ValueError):
            sub.add_menu('循环', self.menu)
        with self.assertRaises(ValueError):
            ActionMenu(self.owner).add_menu('共享', sub)

    def test_mixed_native_widgets_survive_rebuild_and_keep_keyboard_input(self):
        field = LineEdit('菜单内输入')
        field.setMinimumWidth(270)
        action = self.menu.add_widget(field)
        self.menu.add_separator()
        command = self.menu.add_action('应用')
        self.open()
        self.assertLessEqual(self.menu._content.width(), self.menu._scroll.viewport().width())
        self.assertTrue(self.menu._scroll.viewport().rect().contains(
            QtCore.QRect(field.mapTo(self.menu._scroll.viewport(), QtCore.QPoint()), field.size())))
        field.setFocus()
        QTest.keyClicks(field, 'native')
        self.assertEqual(field.text(), 'native')
        self.assertTrue(self.menu._opened)
        command.setText('立即应用')
        self.app.processEvents()
        self.assertIs(action.defaultWidget(), field)
        self.assertEqual(field.text(), 'native')
        QTest.keyClick(field, QtCore.Qt.Key.Key_Escape)
        self.menu._reveal.setCurrentTime(self.menu.HIDE_DURATION)
        self.assertFalse(self.menu._opened)

    def test_exclusive_qaction_group_preserves_radio_behavior(self):
        group = QtGui.QActionGroup(self.menu)
        a = self.menu.add_action('名称', checkable=True, checked=True)
        b = self.menu.add_action('日期', checkable=True)
        group.addAction(a)
        group.addAction(b)
        self.open()
        self.menu._select(1)
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Return)
        self.assertTrue(b.isChecked())
        self.assertFalse(a.isChecked())

    def test_context_position_is_local_and_reopening_preserves_requested_point(self):
        self.menu.add_action('复制')
        self.menu.popup_at(self.owner, QtCore.QPoint(450, 240))
        self.menu._reveal.setCurrentTime(self.menu.SHOW_DURATION)
        self.assertAlmostEqual(self.menu._surface.x(), 440, delta=1)
        self.menu.popup_at(self.owner, QtCore.QPoint(100, 320))
        self.menu._reveal.setCurrentTime(self.menu.SHOW_DURATION)
        self.assertAlmostEqual(self.menu._surface.x(), 90, delta=1)

    def test_deleting_submenu_or_hiding_anchor_cleans_up_filters(self):
        sub = self.menu.add_menu('子菜单')
        sub.add_action('子项')
        self.open()
        self.menu._open_active_submenu()
        self.anchor.hide()
        self.assertFalse(self.menu._opened)
        self.assertFalse(sub._opened)
        sub.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(self.menu.actions(), [])

    def test_tray_menu_is_native_qmenu_accepted_by_qsystemtrayicon(self):
        menu = SystemTrayMenu(self.owner)
        menu.add_action('显示窗口')
        menu.addSeparator()
        menu.add_action('保持运行', checkable=True, checked=True)
        tray = QtWidgets.QSystemTrayIcon(self.owner)
        tray.setContextMenu(menu)
        self.assertIs(tray.contextMenu(), menu)
        self.assertIsInstance(menu, QtWidgets.QMenu)
        self.assertFalse(tray.isVisible())
        theme.set_mode('dark')
        self.assertIn(theme.tokens.surface, menu.styleSheet())
        theme.set_mode('light')

    def test_selection_fades_while_the_new_action_is_immediately_usable(self):
        self.menu.add_action('第一项')
        command = self.menu.add_action('第二项')
        calls = []
        command.triggered.connect(lambda: calls.append(True))
        self.open()
        first, second = self.menu._items
        first._selection_animation.setCurrentTime(120)
        self.menu._select(1)
        second._selection_animation.setCurrentTime(60)
        self.assertTrue(second.active)
        self.assertFalse(first.active)
        self.assertGreater(second._selection_progress, 0)
        self.assertLess(second._selection_progress, 1)
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Return)
        self.assertEqual(calls, [True])
        self.assertTrue(self.menu._closing)

    def test_submenu_moves_sideways_and_fades_without_blocking_parent_input(self):
        sub = self.menu.add_menu('更多')
        sub.add_action('子项')
        command = self.menu.add_action('普通动作')
        calls = []
        command.triggered.connect(lambda: calls.append(True))
        self.open()
        self.menu._open_active_submenu()
        sub._reveal.setCurrentTime(sub.SHOW_DURATION // 3)
        self.assertEqual(sub._surface.y(), sub._rest.y())
        self.assertNotEqual(sub._surface.x(), sub._rest.x())
        sub._reveal.setCurrentTime(sub.SHOW_DURATION)
        self.menu._items[1].entered.emit()
        self.assertIsNone(self.menu._child_menu)
        self.assertTrue(sub._closing)
        self.assertTrue(sub.isVisible())
        self.assertTrue(sub.testAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Return)
        self.assertEqual(calls, [True])
        self.menu._reveal.setCurrentTime(self.menu.HIDE_DURATION)
        self.assertFalse(sub._opened)
        self.assertFalse(sub._filter_installed)

    def test_reopening_during_dismiss_restores_input_and_does_not_duplicate_callbacks(self):
        command = self.menu.add_action('运行')
        calls = []
        command.triggered.connect(lambda: calls.append(True))
        self.open()
        self.menu.dismiss()
        self.menu._reveal.setCurrentTime(40)
        self.assertTrue(self.menu.testAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.open()
        self.assertFalse(self.menu.testAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Return)
        self.assertEqual(calls, [True])


class ContextMenuExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
        from menus import MenuExamples
        cls.example_type = MenuExamples

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.owner = QtWidgets.QWidget()
        self.owner.resize(900, 700)
        layout = QtWidgets.QVBoxLayout(self.owner)
        self.example = self.example_type()
        layout.addWidget(self.example)
        self.owner.show()
        self.app.processEvents()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_all_main_variants_open_at_the_native_context_event_point(self):
        target = self.example.context_target
        for index in range(4):
            self.example.kind.setCurrentIndex(index)
            self.app.processEvents()
            point = QtCore.QPoint(35 + index * 12, 45 + index * 7)
            event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse, point, target.mapToGlobal(point))
            QtWidgets.QApplication.sendEvent(target, event)
            menu = self.example.menu
            self.assertTrue(event.isAccepted())
            self.assertTrue(menu._opened)
            self.assertIs(menu.anchor_widget(), target)
            self.assertEqual(menu._context_position, point)
            menu._reveal.setCurrentTime(menu.SHOW_DURATION)
            self.assertEqual(menu._rest.x(), target.mapTo(self.owner, point).x() - 10)
            menu.dismiss(immediate=True)

    def test_actual_right_button_opens_default_menu_once_without_a_dropdown(self):
        target = self.example.context_target
        point = QtCore.QPoint(95, 80)
        calls = []
        self.example.menu.aboutToShow.connect(lambda: calls.append(True))
        QTest.mouseClick(target, QtCore.Qt.MouseButton.RightButton, pos=point)
        self.app.processEvents()
        self.assertTrue(self.example.menu._opened)
        self.assertEqual(self.example.menu._context_position, point)
        self.assertEqual(calls, [True])
        self.assertIsNone(self.example.open_button.menu())
        self.assertIsNone(self.example.tray_icon)

    def test_keyboard_context_requests_use_the_target_center(self):
        target = self.example.context_target
        for key, modifiers in ((QtCore.Qt.Key.Key_F10, QtCore.Qt.KeyboardModifier.ShiftModifier),
                               (QtCore.Qt.Key.Key_Menu, QtCore.Qt.KeyboardModifier.NoModifier)):
            target.setFocus()
            QTest.keyClick(target, key, modifiers)
            self.assertTrue(self.example.menu._opened)
            self.assertEqual(self.example.menu._context_position, target.rect().center())
            self.example.menu.dismiss(immediate=True)

    def test_fast_reopening_at_the_same_point_is_a_new_context_request(self):
        target = self.example.context_target
        point = QtCore.QPoint(40, 50)
        for index in range(4):
            self.example.kind.setCurrentIndex(index)
            self.app.processEvents()
            QTest.mouseClick(target, QtCore.Qt.MouseButton.RightButton, pos=point)
            self.app.processEvents()
            self.assertTrue(self.example.menu._opened, index)
            self.assertEqual(self.example.menu._context_position, point)
            self.example.menu.dismiss(immediate=True)

    def test_inline_slider_displays_raw_values_and_keeps_the_context_menu_open(self):
        self.example.kind.setCurrentIndex(2)
        self.app.processEvents()
        self.example._context_menu(QtCore.QPoint(80, 70))
        self.example.menu._reveal.setCurrentTime(self.example.menu.SHOW_DURATION)
        slider = self.example.widget_slider
        slider.setValue(73)
        slider.show_value_tip()
        self.assertEqual(slider._value_label.text(), '73')
        self.assertEqual(self.example.result.text(), '当前值：73')
        self.assertTrue(self.example.menu._opened)


if __name__ == '__main__':
    unittest.main()
