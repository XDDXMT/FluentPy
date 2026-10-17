import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sys
import unittest
from unittest.mock import patch

from fluentpy import (Button, TextButton, HyperlinkButton, ActionMenu, ToggleButton, ToggleIconButton,
    PillToggleButton, DropDownButton, AccentDropDownButton, SplitButton, AccentSplitButton,
    LoadingButton, AccentIconButton, TransparentIconButton, FluentIcon, theme)
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class AdvancedButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(error)
        self.old_mode = theme.mode
        self.parent = QtWidgets.QWidget()
        self.parent.resize(900, 600)
        self.anchor = Button('菜单', self.parent)
        self.anchor.setGeometry(40, 80, 120, 32)
        self.menu = ActionMenu(self.parent)
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

    def open(self, menu=None, anchor=None):
        menu = menu or self.menu
        self.assertTrue(menu.popup(anchor or self.anchor))
        menu._reveal.setCurrentTime(menu.SHOW_DURATION)
        self.app.processEvents()
        return menu

    def test_keyboard_enter_and_space_activate_once_and_show_press_animation(self):
        calls = []
        self.anchor.clicked.connect(lambda: calls.append(True))
        self.anchor.clearFocus()
        self.anchor.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
        self.assertTrue(self.anchor._keyboard_focus)
        QTest.keyPress(self.anchor, QtCore.Qt.Key.Key_Return)
        self.anchor._press_animation.setCurrentTime(35)
        self.assertGreater(self.anchor._press_progress, 0)
        self.assertLess(self.anchor._press_progress, 1)
        QTest.keyRelease(self.anchor, QtCore.Qt.Key.Key_Return)
        self.assertEqual(calls, [True])
        QTest.keyClick(self.anchor, QtCore.Qt.Key.Key_Space)
        self.assertEqual(calls, [True, True])
        self.anchor.setEnabled(False)
        QTest.keyClick(self.anchor, QtCore.Qt.Key.Key_Return)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.anchor._press_progress, 0)

    def test_hide_and_focus_loss_cancel_held_return_without_late_activation(self):
        calls = []
        self.anchor.clicked.connect(lambda: calls.append(True))
        self.anchor.setFocus()
        QTest.keyPress(self.anchor, QtCore.Qt.Key.Key_Return)
        self.anchor.hide()
        QTest.keyRelease(self.anchor, QtCore.Qt.Key.Key_Return)
        self.anchor.show()
        self.assertEqual(calls, [])
        self.assertFalse(self.anchor.isDown())
        self.assertEqual(self.anchor._hover_progress, 0)

    def test_toggle_transition_persists_and_works_with_native_exclusive_groups(self):
        a = ToggleButton('A', self.parent)
        b = PillToggleButton('B', self.parent)
        a.setGeometry(30, 150, 90, 32)
        b.setGeometry(140, 150, 90, 32)
        a.show(); b.show()
        group = QtWidgets.QButtonGroup(self.parent)
        group.setExclusive(True)
        group.addButton(a); group.addButton(b)
        QTest.mouseClick(a, QtCore.Qt.MouseButton.LeftButton)
        a._selection_animation.setCurrentTime(80)
        self.assertTrue(a.isChecked())
        self.assertGreater(a._selection, 0)
        self.assertLess(a._selection, 1)
        QTest.mouseClick(b, QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(a.isChecked())
        self.assertTrue(b.isChecked())
        b.hide()
        self.assertEqual(b._selection, 1)
        b.show()
        for mode in ('light', 'dark'):
            theme.set_mode(mode)
            self.assertFalse(b.grab().isNull())

    def test_new_icon_variants_keep_standard_size_and_native_check_state(self):
        for cls in (ToggleIconButton, AccentIconButton, TransparentIconButton):
            widget = cls(FluentIcon.HEART, self.parent)
            self.assertEqual(widget.size(), QtCore.QSize(32, 32))
            widget.show()
            self.assertFalse(widget.grab().isNull())
        toggle = ToggleIconButton(FluentIcon.HEART, self.parent)
        toggle.click()
        self.assertTrue(toggle.isChecked())

    def test_loading_blocks_mouse_keyboard_click_and_animate_click(self):
        button = LoadingButton('保存', self.parent)
        button.setGeometry(30, 160, 150, 32)
        button.show()
        calls = []
        button.clicked.connect(lambda: calls.append(True))
        button.click()
        button.set_loading(True, text='正在保存…')
        self.assertFalse(button.isEnabled())
        self.assertTrue(button._visual_enabled())
        button.click()
        button.animateClick()
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        QTest.keyClick(button, QtCore.Qt.Key.Key_Return)
        QTest.qWait(120)
        self.assertEqual(calls, [True])
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Running)
        button.set_loading(False)
        self.assertEqual(button.text(), '保存')
        self.assertTrue(button.isEnabled())
        button.click()
        self.assertEqual(calls, [True, True])

    def test_loading_preserves_external_disabled_state_and_updated_idle_text(self):
        button = LoadingButton('保存', self.parent)
        button.show()
        changes = []
        button.loadingChanged.connect(changes.append)
        button.set_loading(True)
        button.setText('重试保存')
        button.setDisabled(True)
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Stopped)
        button.set_loading(False)
        self.assertFalse(button.isEnabled())
        self.assertEqual(button.text(), '重试保存')
        button.setEnabled(True)
        self.assertTrue(button.isEnabled())
        self.assertEqual(changes, [True, False])

    def test_loading_stops_offscreen_and_resumes_when_shown(self):
        button = LoadingButton('任务', self.parent)
        button.set_loading(True)
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Stopped)
        button.show()
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Running)
        self.parent.setEnabled(False)
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.parent.setEnabled(True)
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Running)
        button.hide()
        self.assertEqual(button._spinner.state(), QtCore.QAbstractAnimation.State.Stopped)

    def test_hyperlink_opens_only_requested_supported_urls(self):
        with patch.object(QtGui.QDesktopServices, 'openUrl', return_value=True) as opened:
            for url in ('https://example.com/docs', '', 'javascript:alert(1)'):
                link = HyperlinkButton('链接', self.parent, url=url)
                link.click()
            self.assertEqual(opened.call_count, 1)
            self.assertEqual(opened.call_args.args[0].toString(), 'https://example.com/docs')

    def test_disabled_text_button_remains_transparent(self):
        button = TextButton('禁用', self.parent)
        button.setEnabled(False)
        self.assertEqual(button._surface_color().alpha(), 0)
        button.show()
        # The button's empty corner must show the parent's surface, not a black block.
        self.assertEqual(button.grab().toImage().pixelColor(3, 3), self.parent.grab().toImage().pixelColor(button.x()+3, button.y()+3))

    def test_menu_entry_exit_have_intermediate_frames_and_no_native_window(self):
        self.menu.add_action('保存', icon=FluentIcon.DOCUMENT_SAVE)
        self.assertTrue(self.menu.popup(self.anchor))
        self.assertFalse(self.menu.isWindow())
        self.assertIsNone(self.menu.windowHandle())
        self.assertEqual(self.menu._opacity.opacity(), 0)
        self.menu._reveal.setCurrentTime(70)
        self.assertGreater(self.menu._opacity.opacity(), 0)
        self.assertLess(self.menu._opacity.opacity(), 1)
        self.assertNotEqual(self.menu._surface.pos(), self.menu._rest)
        self.menu._reveal.setCurrentTime(self.menu.SHOW_DURATION)
        self.menu.dismiss()
        self.menu._reveal.setCurrentTime(60)
        self.assertGreater(self.menu._opacity.opacity(), 0)
        self.assertLess(self.menu._opacity.opacity(), 1)
        self.menu._reveal.setCurrentTime(self.menu.HIDE_DURATION)
        self.assertFalse(self.menu.isVisible())

    def test_keyboard_skips_disabled_hidden_separator_and_triggers_once(self):
        first = self.menu.add_action('第一项')
        self.menu.add_action('不可用', enabled=False)
        self.menu.add_separator()
        hidden = self.menu.add_action('隐藏项')
        hidden.setVisible(False)
        checked = self.menu.add_action('标记', checkable=True)
        events = []
        self.menu.triggered.connect(events.append)
        self.open()
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Down)
        self.assertIs(self.menu._items[self.menu._active].action, checked)
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Return)
        self.assertTrue(checked.isChecked())
        self.assertEqual(events, [checked])
        QTest.qWait(150)
        self.open()
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_End)
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Home)
        self.assertIs(self.menu._items[self.menu._active].action, first)

    def test_mouse_action_and_outside_dismiss_do_not_trigger_twice(self):
        action = self.menu.add_action('动作')
        calls = []
        action.triggered.connect(lambda: calls.append(True))
        self.open()
        QTest.mouseClick(self.menu._items[0], QtCore.Qt.MouseButton.LeftButton)
        QTest.qWait(150)
        self.assertEqual(calls, [True])
        self.open()
        QTest.mouseClick(self.menu, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(850, 550))
        QTest.qWait(150)
        self.assertEqual(calls, [True])
        self.assertFalse(self.menu.isVisible())

    def test_menu_flip_resize_and_anchor_move_stay_inside_owner(self):
        for index in range(8):
            self.menu.add_action('菜单项'+str(index))
        self.anchor.move(750, 550)
        self.open()
        self.assertLess(self.menu._surface.y(), self.anchor.y())
        self.assertTrue(self.parent.rect().contains(self.menu._surface.geometry()))
        self.anchor.move(40, 80)
        self.app.processEvents()
        self.assertGreater(self.menu._surface.y(), self.anchor.y())
        self.parent.resize(450, 350)
        self.app.processEvents()
        self.assertTrue(self.parent.rect().contains(self.menu._surface.geometry()))

    def test_short_menu_does_not_show_spurious_scrollbar_long_menu_can_reach_end(self):
        for index in range(4):
            self.menu.add_action(f'项目 {index}')
        self.open()
        self.assertEqual(self.menu._scroll.verticalScrollBar().maximum(), 0)
        self.menu.dismiss(immediate=True)
        self.menu.clear()
        for index in range(120):
            self.menu.add_action(f'项目 {index}')
        self.assertEqual(len(self.menu._items), 0, 'Batch addition should defer layout work')
        self.open()
        self.assertGreater(self.menu._scroll.verticalScrollBar().maximum(), 0)
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_End)
        self.assertEqual(self.menu._active, 119)
        self.assertGreater(self.menu._scroll.verticalScrollBar().value(), 0)

    def test_action_changes_and_deletion_update_live_rows_without_stale_callbacks(self):
        action = self.menu.add_action('原文案')
        other = self.menu.add_action('其他')
        self.open()
        action.setText('修改后的文案')
        self.app.processEvents()
        self.assertEqual(self.menu._items[0].text(), '修改后的文案')
        action.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(self.menu.actions(), [other])
        self.assertEqual(len(self.menu._items), 1)
        self.assertFalse(self.menu.grab().isNull())
        self.menu.clear()
        self.assertFalse(self.menu.isVisible())

    def test_empty_and_all_disabled_menus_are_safe(self):
        self.assertFalse(self.menu.popup(self.anchor))
        self.menu.add_action('暂不可用', enabled=False)
        self.open()
        self.assertEqual(self.menu._active, -1)
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Return)
        self.assertTrue(self.menu.isVisible())
        QTest.keyClick(self.menu, QtCore.Qt.Key.Key_Escape)
        QTest.qWait(150)
        self.assertFalse(self.menu.isVisible())

    def test_clear_releases_owned_actions_and_preserves_shared_or_borrowed_actions(self):
        owned = self.menu.add_action('本菜单拥有')
        shared = self.menu.add_action('其他菜单也在使用')
        borrowed = QtGui.QAction('外部拥有', self.parent)
        self.menu.addAction(borrowed)
        other = ActionMenu(self.parent)
        other.addAction(shared)
        destroyed = []
        owned.destroyed.connect(lambda: destroyed.append('owned'))
        shared.destroyed.connect(lambda: destroyed.append('shared'))
        borrowed.destroyed.connect(lambda: destroyed.append('borrowed'))
        self.menu.clear()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, ['owned'])
        self.assertEqual(self.menu.actions(), [])
        self.assertEqual(other.actions(), [shared])
        self.open(other)
        self.assertEqual(other._items[0].text(), '其他菜单也在使用')

    def test_dropdown_arrow_rotates_and_shared_menu_marks_only_active_anchor(self):
        menu = self.menu
        menu.add_action('动作')
        a = DropDownButton('A', self.parent, menu=menu)
        b = AccentDropDownButton('B', self.parent, menu=menu)
        a.setGeometry(30, 150, 120, 32); b.setGeometry(160, 150, 120, 32)
        a.show(); b.show()
        a.click()
        a._arrow_animation.setCurrentTime(80)
        self.assertGreater(a._arrow_progress, 0)
        self.assertLess(a._arrow_progress, 1)
        self.assertEqual(b._arrow_progress, 0)
        b.click()
        self.assertIs(menu.anchor_widget(), b)
        a._arrow_animation.setCurrentTime(160)
        b._arrow_animation.setCurrentTime(160)
        self.assertEqual(a._arrow_progress, 0)
        self.assertEqual(b._arrow_progress, 1)
        menu.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertIsNone(a.menu())
        self.assertIsNone(b.menu())

    def test_split_main_action_is_independent_from_menu_hit_region(self):
        for cls in (SplitButton, AccentSplitButton):
            with self.subTest(cls=cls.__name__):
                menu = ActionMenu(self.parent)
                menu.add_action('更多操作')
                split = cls('保存', self.parent, menu=menu)
                split.setGeometry(40, 180, 150, 32)
                split.show()
                calls = []
                split.clicked.connect(lambda: calls.append(True))
                QTest.mouseClick(split.main_button, QtCore.Qt.MouseButton.LeftButton)
                self.assertEqual(calls, [True])
                self.assertFalse(menu.isVisible())
                QTest.mouseClick(split.menu_button, QtCore.Qt.MouseButton.LeftButton)
                self.assertTrue(menu.isVisible())
                self.assertEqual(calls, [True])
                self.assertIs(menu.anchor_widget(), split)
                menu.dismiss(immediate=True)
                split.hide()

    def test_only_one_action_menu_is_open_per_window(self):
        self.menu.add_action('A')
        self.open()
        other = ActionMenu(self.parent)
        other.add_action('B')
        self.open(other)
        self.assertFalse(self.menu.isVisible())
        self.assertTrue(other.isVisible())

    def test_anchor_hide_disable_deletion_and_owner_hide_dismiss_menu(self):
        self.menu.add_action('动作')
        self.open()
        self.anchor.setEnabled(False)
        self.assertFalse(self.menu.isVisible())
        self.anchor.setEnabled(True)
        self.open()
        self.anchor.hide()
        self.assertFalse(self.menu.isVisible())
        self.anchor.show()
        self.open()
        self.parent.hide()
        self.parent.show()
        self.assertFalse(self.menu.isVisible())
        self.open()
        self.anchor.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertFalse(self.menu.isVisible())

    def test_repeated_open_close_and_owner_destruction_leave_no_theme_callbacks(self):
        self.menu.add_action('动作')
        signals = []
        self.menu.aboutToShow.connect(lambda: signals.append('show'))
        self.menu.aboutToHide.connect(lambda: signals.append('hide'))
        for _ in range(15):
            self.menu.popup(self.anchor)
            self.menu._reveal.setCurrentTime(60)
            self.menu.dismiss(immediate=True)
        self.assertEqual(signals, ['show', 'hide'] * 15)
        self.open()
        self.parent.deleteLater()
        self.parent = None
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        for mode in ('light', 'dark'):
            theme.set_mode(mode)
            self.app.processEvents()
        QTest.qWait(200)

    def test_menu_reparenting_preserves_original_owner_lifetime(self):
        section = QtWidgets.QWidget(self.parent)
        section.show()
        menu = ActionMenu(section)
        menu.add_action('动作')
        self.open(menu)
        destroyed = []
        menu.destroyed.connect(lambda: destroyed.append(True))
        section.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])


if __name__ == '__main__':
    unittest.main()
