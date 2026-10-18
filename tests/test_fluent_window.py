"""Window composition, route history and native-window delegation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
import unittest
from unittest.mock import Mock, patch

from fluentpy import FluentWindow, FluentTitleBar, LineEdit, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class FluentWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.window = FluentWindow('Documents')
        self.mode = theme.mode

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def pages(self):
        pages = [LineEdit() for _ in range(3)]
        for page, key in zip(pages, ('overview', 'editor', 'settings')):
            self.window.add_page(page, key, route=key,
                                 position='bottom' if key == 'settings' else 'scroll')
        self.window.navigation_view().stack.setAnimationDuration(0)
        return pages

    def test_simple_window_keeps_original_layout_and_native_chrome(self):
        layout = self.window.content_layout
        child = LineEdit()
        layout.addWidget(child)
        self.assertIs(self.window.content_layout, layout)
        self.assertIsNone(self.window._navigation_view)
        self.assertIsNone(self.window.title_bar())
        self.assertFalse(self.window.windowFlags() & QtCore.Qt.WindowType.FramelessWindowHint)
        self.assertEqual(layout.contentsMargins().left(), 24)
        self.assertEqual(self.window.current_route(), '')
        self.assertFalse(self.window.go_back())

    def test_lazy_navigation_preserves_content_and_first_route(self):
        child = QtWidgets.QLabel('Existing content')
        layout = self.window.content_layout
        layout.addWidget(child)
        pages = self.pages()
        self.assertIs(self.window.content_layout, layout)
        self.assertIs(layout.itemAt(0).widget(), child)
        self.assertIs(self.window.current_page(), pages[0])
        self.assertEqual(self.window.current_route(), 'overview')
        self.assertFalse(self.window.can_go_back())
        self.assertEqual(self.window.navigation_view().sidebar._items[-1].text(), 'settings')

    def test_sidebar_widget_and_route_switches_share_history(self):
        pages = self.pages()
        pages[1].setText('Retained editor text')
        self.assertTrue(self.window.switch_to(pages[1], animated=False))
        self.window.navigation_view().sidebar.set_current_index(2, animated=False)
        self.assertEqual(self.window.current_route(), 'settings')
        self.assertTrue(self.window.go_back())
        self.assertIs(self.window.current_page(), pages[1])
        self.assertTrue(self.window.go_back())
        self.assertEqual(self.window.current_route(), 'overview')
        self.assertFalse(self.window.go_back())
        self.assertTrue(self.window.go_forward())
        self.assertEqual(pages[1].text(), 'Retained editor text')

    def test_duplicate_and_branch_navigation_do_not_add_stale_forward_entries(self):
        self.pages()
        self.window.switch_to('editor', False)
        self.window.switch_to('editor', False)
        self.window.switch_to('settings', False)
        self.window.go_back()
        self.window.switch_to('overview', False)
        self.assertFalse(self.window.can_go_forward())
        self.assertTrue(self.window.go_back())
        self.assertEqual(self.window.current_route(), 'editor')
        self.assertTrue(self.window.go_back())
        self.assertFalse(self.window.go_back())

    def test_hiding_routes_prunes_history_and_all_hidden_is_safe(self):
        self.pages()
        self.window.switch_to('editor', False)
        self.window.switch_to('settings', False)
        nav = self.window.navigation_view()
        nav.set_route_visible('editor', False)
        self.assertTrue(self.window.go_back())
        self.assertEqual(self.window.current_route(), 'overview')
        self.assertFalse(self.window.switch_to('editor'))
        for route in ('overview', 'settings'):
            nav.set_route_visible(route, False)
        self.assertEqual(self.window.current_route(), '')
        self.assertIsNone(self.window.current_page())
        self.assertFalse(self.window.can_go_back())
        nav.set_route_visible('editor', True)
        self.assertEqual(self.window.current_route(), 'editor')

    def test_deleted_page_cannot_be_revisited_or_retained_by_history(self):
        pages = self.pages()
        self.window.switch_to('editor', False)
        pages[1].deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertNotEqual(self.window.current_route(), 'editor')
        self.assertFalse(self.window.switch_to('editor'))
        self.assertNotIn('editor', self.window._route_history)
        removed = self.window.remove_page('settings')
        self.assertIs(removed, pages[2])
        removed.deleteLater()
        self.assertIsNone(self.window.remove_page('missing'))

    def test_top_layout_stays_in_sync_and_many_routes_scroll(self):
        pages = self.pages()
        self.window.set_navigation_mode('top')
        self.window.resize(450, 430)
        for index in range(8):
            self.window.add_page(QtWidgets.QLabel(str(index)), 'Additional page ' + str(index), route='extra' + str(index))
        self.window.show()
        self.app.processEvents()
        self.assertTrue(self.window.navigation_view().sidebar.isHidden())
        self.assertFalse(self.window._top_scroll.isHidden())
        self.assertGreater(self.window._top_scroll.horizontalScrollBar().maximum(), 0)
        self.window._top_navigation.set_current_item('settings', False)
        self.assertIs(self.window.current_page(), pages[2])
        self.window.navigation_view().set_route_visible('editor', False)
        self.assertNotIn('editor', [item.route_key for item in self.window._top_navigation._items])

    def test_auto_expanded_and_compact_modes_preserve_page_identity(self):
        pages = self.pages()
        self.window.resize(980, 600)
        self.window.show()
        self.app.processEvents()
        nav = self.window.navigation_view()
        self.assertTrue(nav.sidebar.expanded)
        self.window.resize(650, 600)
        self.app.processEvents()
        self.assertFalse(nav.sidebar.expanded)
        self.window.set_navigation_mode('expanded')
        self.assertTrue(nav.sidebar.expanded)
        self.window.set_navigation_mode('compact')
        self.assertFalse(nav.sidebar.expanded)
        self.assertIs(self.window.current_page(), pages[0])
        with self.assertRaises(ValueError):
            self.window.set_navigation_mode('unknown')

    def test_top_entries_follow_native_navigation_enabled_state_and_text(self):
        self.pages()
        page = self.window.navigation_view().pages()[1]
        page.item.setEnabled(False)
        self.window.set_navigation_mode('top')
        self.window.show()
        self.app.processEvents()
        def top_button():
            return next(item.widget for item in self.window._top_navigation._items if item.route_key == 'editor')
        self.assertFalse(top_button().isEnabled())
        QTest.mouseClick(top_button(), QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.current_route(), 'overview')
        page.item.setEnabled(True)
        self.app.processEvents()
        self.assertTrue(top_button().isEnabled())
        page.item.setText('Updated document')
        self.app.processEvents()
        self.assertEqual(top_button().text(), 'Updated document')
        QTest.mouseClick(top_button(), QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.current_route(), 'editor')

    def test_title_bar_toggle_preserves_layout_page_and_visible_state(self):
        pages = self.pages()
        self.window.switch_to('editor', False)
        self.window.show()
        self.app.processEvents()
        layout = self.window.content_layout
        self.window.set_title_bar_enabled(True)
        title = self.window.title_bar()
        self.assertIsInstance(title, FluentTitleBar)
        self.assertTrue(title.back_button.isEnabled())
        self.assertTrue(self.window.isVisible())
        self.assertTrue(self.window.windowFlags() & QtCore.Qt.WindowType.FramelessWindowHint)
        self.window.set_title_bar_enabled(False)
        self.assertTrue(title.isHidden())
        self.assertTrue(self.window.isVisible())
        self.assertIs(self.window.content_layout, layout)
        self.assertIs(self.window.current_page(), pages[1])
        self.window.set_title_bar_enabled(True)
        self.assertIs(self.window.title_bar(), title)

    def test_custom_title_bar_accepts_real_widgets_without_touching_content(self):
        custom = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(custom)
        search = LineEdit()
        layout.addWidget(search)
        self.window.set_title_bar(custom)
        self.assertIs(self.window.menuWidget(), custom)
        self.assertTrue(self.window.is_title_bar_enabled())
        with self.assertRaises(ValueError):
            self.window.set_title_bar(self.window)

    def test_system_resize_delegation_and_fixed_dimension_edges(self):
        self.window.set_title_bar_enabled(True)
        self.window.show()
        self.app.processEvents()
        handle = Mock()
        handle.startSystemResize.return_value = True
        with patch.object(self.window, 'windowHandle', return_value=handle):
            QTest.mousePress(self.window, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(1, 200))
        handle.startSystemResize.assert_called_once_with(QtCore.Qt.Edge.LeftEdge)
        self.window.setFixedWidth(self.window.width())
        self.assertFalse(self.window._resize_edges(QtCore.QPoint(1, 200)))
        self.window.showMaximized()
        self.assertFalse(self.window._resize_edges(QtCore.QPoint(1, 1)))

    def test_replacing_or_deleting_title_bar_clears_only_the_current_owner(self):
        self.window.set_title_bar_enabled(True)
        old = self.window.title_bar()
        custom = QtWidgets.QWidget()
        self.window.set_title_bar(custom)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertIs(self.window.title_bar(), custom)
        custom.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertIsNone(self.window.title_bar())
        self.window.set_title_bar_enabled(True)
        self.assertIsInstance(self.window.title_bar(), FluentTitleBar)
        self.assertIsNot(self.window.title_bar(), old)

    def test_background_pair_validation_theme_and_reset(self):
        self.window.set_background_colors('#eef4fa', '#162231')
        theme.set_mode('light')
        self.assertEqual(self.window.palette().color(QtGui.QPalette.ColorRole.Window).name(), '#eef4fa')
        theme.set_mode('dark')
        self.assertEqual(self.window.palette().color(QtGui.QPalette.ColorRole.Window).name(), '#162231')
        for invalid in ('invalid', '#80ffffff'):
            with self.assertRaises(ValueError):
                self.window.set_background_colors('#ffffff', invalid)
            self.assertEqual(self.window.palette().color(QtGui.QPalette.ColorRole.Window).name(), '#162231')
        self.window.clear_background_colors()
        self.assertNotEqual(self.window.palette().color(QtGui.QPalette.ColorRole.Window).name(), '#162231')

    def test_backdrop_request_reports_native_rejection_and_keeps_solid_client(self):
        self.window.show()
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=False) as apply:
            self.window.set_backdrop_enabled(True)
            self.assertTrue(self.window.is_backdrop_enabled())
            self.assertFalse(self.window.backdrop_applied())
            self.assertTrue(apply.call_args.args[-1])
            self.assertFalse(self.window.testAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground))
            painted = self.window.centralWidget().grab().toImage().pixelColor(10, 10)
            self.assertEqual(painted.alpha(), 255)
            self.assertEqual(painted.name(), self.window.palette().color(QtGui.QPalette.ColorRole.Window).name())
        with patch.object(self.window, '_native_windows_platform', return_value=True), \
             patch.object(self.window, '_forward_nonclient_activation', return_value=1), \
             patch('fluentpy.widgets.window.apply_system_backdrop', return_value=True):
            self.window.set_backdrop_enabled(True)
            self.assertTrue(self.window.backdrop_applied())


if __name__ == '__main__':
    unittest.main()
