"""Page removal must keep live Qt pages, route keys and sidebar rows aligned."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest

from fluentpy import NavigationView, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets


class NavigationLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(str(error))
        self.view = NavigationView()
        self.view.stack.setAnimationDuration(0)

    def tearDown(self):
        self.view.close()
        self.view.deleteLater()
        self.flush()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def flush(self):
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def add(self, key, position="scroll"):
        widget = QtWidgets.QLineEdit(key)
        self.view.add_sub_interface(widget, QtGui.QIcon(), key, key, position)
        return widget

    def populate(self):
        return [
            self.add("overview", "header"),
            self.add("editor"),
            self.add("other"),
            self.add("settings", "bottom"),
        ]

    def assert_aligned(self, keys):
        pages = self.view.pages()
        self.assertIsInstance(pages, tuple)
        self.assertEqual([page.route_key for page in pages], keys)
        self.assertEqual(self.view.stack.count(), len(keys))
        self.assertEqual(len(self.view.sidebar._items), len(keys))
        for index, page in enumerate(pages):
            self.assertIs(self.view.stack.widget(index), page.widget)
            self.assertIs(self.view.sidebar._items[index], page.item)
            self.assertIs(self.view.widget_for_route(page.route_key), page.widget)
            self.assertEqual(self.view.route_for_widget(page.widget), page.route_key)

    def test_notifications_publish_complete_first_page_and_visibility_snapshots(self):
        snapshots, current = [], []
        self.view.routesChanged.connect(
            lambda: snapshots.append(
                (
                    tuple(page.route_key for page in self.view.pages()),
                    self.view.stack.count(),
                    self.view.current_route(),
                )
            )
        )
        self.view.currentChanged.connect(current.append)
        self.add("first")
        self.add("second")
        self.assertEqual(current, ["first"])
        self.assertEqual(snapshots, [(("first",), 1, "first"), (("first", "second"), 2, "first")])
        self.view.set_route_visible("second", False)
        self.view.set_route_visible("second", False)
        self.view.set_route_visible("missing", False)
        self.assertEqual(len(snapshots), 3)
        self.assertEqual(current, ["first"])

    def test_removing_earlier_row_preserves_selection_and_click_indexes(self):
        widgets = self.populate()
        self.view.set_current_route("other", False)
        seen = []
        self.view.currentChanged.connect(seen.append)
        old_item = self.view.pages()[0].item
        removed = self.view.remove_page("overview")
        self.assertIs(removed, widgets[0])
        self.assertIsNone(removed.parentWidget())
        self.assertEqual(self.view.current_route(), "other")
        self.assertEqual(seen, [])
        self.assert_aligned(["editor", "other", "settings"])
        self.view.pages()[2].item.clicked.emit(True)
        self.assertEqual(self.view.current_route(), "settings")
        # A detached old row cannot navigate using its obsolete numeric index.
        old_item.clicked.emit(True)
        self.assertEqual(self.view.current_route(), "settings")
        removed.deleteLater()

    def test_current_removal_selects_visible_fallback_and_all_removed_is_safe(self):
        self.populate()
        self.view.set_route_visible("overview", False)
        self.view.set_current_route("other", False)
        seen = []
        self.view.currentChanged.connect(seen.append)
        removed = self.view.remove_page("other", delete=True)
        self.assertIsNotNone(removed)
        self.assertEqual(self.view.current_route(), "editor")
        self.assertEqual(seen, ["editor"])
        self.assert_aligned(["overview", "editor", "settings"])
        self.view.remove_page("editor", delete=True)
        self.view.remove_page("settings", delete=True)
        self.assertEqual(self.view.current_route(), "")
        self.assertTrue(self.view.stack.isHidden())
        self.view.remove_page("overview", delete=True)
        self.assert_aligned([])
        self.assertIsNone(self.view.remove_page("missing"))
        self.add("new")
        self.assertEqual(self.view.current_route(), "new")

    def test_direct_deletion_removes_route_before_public_notifications(self):
        widgets = self.populate()
        self.view.set_current_route("editor", False)
        coherent = []
        self.view.routesChanged.connect(
            lambda: coherent.append(
                (tuple(page.route_key for page in self.view.pages()), self.view.stack.count())
            )
        )
        widgets[1].deleteLater()
        self.flush()
        self.assert_aligned(["overview", "other", "settings"])
        self.assertEqual(coherent, [(("overview", "other", "settings"), 3)])
        self.assertEqual(self.view.current_route(), "overview")
        self.assertIsNone(self.view.widget_for_route("editor"))
        self.assertIsNone(self.view.route_for_widget(widgets[1]))
        self.view.pages()[-1].item.clicked.emit(True)
        self.assertEqual(self.view.current_route(), "settings")
        widgets[0].deleteLater()
        self.flush()
        self.assert_aligned(["other", "settings"])
        self.assertEqual(self.view.current_route(), "settings")

    def test_delete_during_animation_and_owner_deletion_leave_no_qt_errors(self):
        widgets = self.populate()
        self.view.resize(600, 420)
        self.view.show()
        self.app.processEvents()
        self.view.stack.setAnimationDuration(180)
        self.view.set_current_route("editor")
        widgets[1].deleteLater()
        self.flush()
        self.assert_aligned(["overview", "other", "settings"])
        self.assertIsNone(self.view.stack._transition_widget)
        mode = theme.mode
        self.view.deleteLater()
        self.flush()
        for next_mode in ("dark", "light"):
            theme.set_mode(next_mode)
            self.app.processEvents()
        theme.set_mode(mode)
        self.view = NavigationView()

    def test_detached_page_can_be_registered_again_without_stale_link(self):
        widget = self.add("first")
        self.add("second")
        self.assertIs(self.view.remove_sub_interface("first"), widget)
        self.view.add_sub_interface(widget, QtGui.QIcon(), "returned", "first", "bottom")
        self.assert_aligned(["second", "first"])
        widget.deleteLater()
        self.flush()
        self.assert_aligned(["second"])

    def test_external_stack_removal_also_unregisters_page(self):
        widgets = self.populate()
        self.view.stack.removeWidget(widgets[1])
        self.assert_aligned(["overview", "other", "settings"])
        widgets[1].deleteLater()
        self.flush()
        self.assert_aligned(["overview", "other", "settings"])

    def test_direct_stack_selection_remains_visible_to_current_route_queries(self):
        widgets = self.populate()
        self.view.stack.setCurrentWidget(widgets[2])
        self.assertEqual(self.view.current_route(), "other")
        QtWidgets.QStackedWidget.setCurrentWidget(self.view.stack, widgets[3])
        self.assertEqual(self.view.current_route(), "settings")
        self.assertIs(self.view.widget_for_route(self.view.current_route()), widgets[3])

    def test_duplicate_widget_or_structural_widget_rejected_without_side_effects(self):
        widget = self.add("first")
        for invalid in (widget, self.view, self.view.stack, self.view.sidebar):
            with self.assertRaises(ValueError):
                self.view.add_sub_interface(invalid, QtGui.QIcon(), "other", "other")
        self.assert_aligned(["first"])

    def test_item_metadata_changes_publish_routes_without_changing_selection(self):
        self.populate()
        snapshots, current = [], []
        self.view.routesChanged.connect(
            lambda: snapshots.append(
                [(page.item.text(), page.item.isEnabled()) for page in self.view.pages()]
            )
        )
        self.view.currentChanged.connect(current.append)
        item = self.view.pages()[1].item
        item.setText("Renamed editor")
        item.setText("Renamed editor")
        item.setEnabled(False)
        item.setEnabled(False)
        pixmap = QtGui.QPixmap(8, 8)
        pixmap.fill(QtCore.Qt.GlobalColor.red)
        item.setIcon(QtGui.QIcon(pixmap))
        self.assertEqual(len(snapshots), 3)
        self.assertEqual(snapshots[-1][1], ("Renamed editor", False))
        self.assertEqual(current, [])
        self.assertTrue(self.view.is_route_visible("editor"))


if __name__ == "__main__":
    unittest.main()
