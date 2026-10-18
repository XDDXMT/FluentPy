"""Opted-in hidden widgets coalesce theme work until their next show."""
import os
import sys
import unittest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme.manager import ThemeManager


class _Probe(QtWidgets.QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.applied = []
        self.painted = []
        self.last_mode = None
        self.resize(140, 70)

    def apply_theme(self):
        self.last_mode = self.manager.mode.value
        self.applied.append((self.last_mode, self.manager.tokens.custom_accent))

    def paintEvent(self, event):
        self.painted.append(self.last_mode)
        super().paintEvent(event)


class ThemeSubscriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: self.errors.append(str(value))
        self.manager = ThemeManager()
        self.root = QtWidgets.QWidget()
        self.root.resize(350, 180)
        self.owner = _Probe(self.manager, self.root)
        self.manager.subscribe(self.owner, self.owner.apply_theme)

    def flush(self):
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def tearDown(self):
        self.root.close()
        self.root.deleteLater()
        self.manager.deleteLater()
        self.flush()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_hidden_opted_in_widget_merges_changes_and_refreshes_before_first_paint(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        self.manager.set_mode('dark')
        self.manager.set_accent('#123456')
        self.manager.set_mode('light')
        self.manager.set_mode('dark')
        self.assertEqual(self.owner.applied, [])
        self.root.show()
        self.app.processEvents()
        self.assertEqual(self.owner.applied, [('dark', '#123456')])
        self.assertTrue(self.owner.painted)
        self.assertTrue(all(mode == 'dark' for mode in self.owner.painted))

    def test_default_hidden_widget_retains_immediate_semantics(self):
        self.manager.set_mode('dark')
        self.manager.set_mode('light')
        self.assertEqual(self.owner.applied, [('dark', None), ('light', None)])
        self.root.show()
        self.app.processEvents()
        self.assertEqual(len(self.owner.applied), 2)

    def test_visible_opted_in_widget_refreshes_immediately(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        self.root.show()
        self.app.processEvents()
        self.manager.set_mode('dark')
        self.assertEqual(self.owner.applied, [('dark', None)])

    def test_only_explicitly_hidden_child_is_deferred(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        other = _Probe(self.manager, self.root)
        self.manager.subscribe(other, other.apply_theme)
        other.hide()
        self.root.show()
        self.app.processEvents()
        self.manager.set_mode('dark')
        self.assertEqual(self.owner.applied, [('dark', None)])
        self.assertEqual(other.applied, [])
        other.show()
        self.assertEqual(other.applied, [('dark', None)])

    def test_nonwidget_owner_keeps_immediate_semantics(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        class Receiver(QtCore.QObject):
            def __init__(self, parent):
                super().__init__(parent)
                self.calls = []
            def apply_theme(receiver):
                receiver.calls.append(self.manager.mode.value)
        receiver = Receiver(self.root)
        self.manager.subscribe(receiver, receiver.apply_theme)
        self.manager.set_mode('dark')
        self.manager.set_mode('light')
        self.assertEqual(receiver.calls, ['dark', 'light'])

    def test_disabling_opt_in_flushes_on_next_changed_even_while_hidden(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        self.manager.set_mode('dark')
        self.root.setProperty('fluentLazyThemeRefresh', False)
        self.manager.set_accent('#123456')
        self.assertEqual(self.owner.applied, [('dark', '#123456')])
        self.root.show()
        self.app.processEvents()
        self.assertEqual(len(self.owner.applied), 1)

    def test_disabling_opt_in_also_flushes_on_show_without_another_change(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        self.manager.set_mode('dark')
        self.root.setProperty('fluentLazyThemeRefresh', False)
        self.root.show()
        self.assertEqual(self.owner.applied, [('dark', None)])

    def test_nested_show_does_not_reenter_the_pending_theme_callback(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        calls, depths = [], []
        depth = 0
        def apply():
            nonlocal depth
            depth += 1
            calls.append(self.manager.mode.value)
            depths.append(depth)
            self.owner.hide()
            self.owner.show()
            depth -= 1
        self.owner.apply_theme = apply
        self.manager.set_mode('dark')
        self.root.show()
        self.app.processEvents()
        self.assertEqual(calls, ['dark'])
        self.assertEqual(max(depths), 1)

    def test_destroying_a_dirty_owner_disconnects_safely(self):
        self.root.setProperty('fluentLazyThemeRefresh', True)
        calls = []
        self.owner.apply_theme = lambda: calls.append(True)
        self.manager.set_mode('dark')
        self.owner.deleteLater()
        self.flush()
        self.manager.set_mode('light')
        self.manager.set_mode('dark')
        self.assertEqual(calls, [])

    def test_only_boolean_true_enables_the_optional_policy(self):
        self.root.setProperty('fluentLazyThemeRefresh', 'true')
        self.manager.set_mode('dark')
        self.assertEqual(self.owner.applied, [('dark', None)])


if __name__ == '__main__':
    unittest.main()
