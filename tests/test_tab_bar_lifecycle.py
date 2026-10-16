from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from fluentpy import AnimatedStackedWidget, TabBar
from fluentpy.qt import QtCore, QtWidgets

try:
    from PySide6.QtTest import QTest
except ImportError:
    from PyQt6.QtTest import QTest


class TabBarLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.host = QtWidgets.QWidget()
        self.host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.layout = QtWidgets.QVBoxLayout(self.host)
        self.tabs = TabBar(self.host)
        self.layout.addWidget(self.tabs)
        self.host.resize(720, 220)
        self.host.show()
        self.events = []
        self.tabs.currentChanged.connect(lambda key: self.events.append(("current", key)))
        self.tabs.tabCloseRequested.connect(lambda index: self.events.append(("close", index)))
        self.app.processEvents()

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def add(self, *keys):
        for key in keys:
            self.tabs.add_tab(key, key + ".md")
        self.app.processEvents()

    def click_close(self, key):
        button = next(item.widget for item in self.tabs._items if item.route_key == key)
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton,
                         pos=QtCore.QPoint(button.width() - 18, 18))

    def test_duplicate_add_is_ignored_without_signal_or_extra_widget(self):
        self.add("first", "second")
        first_button = self.tabs._items[0].widget
        self.events.clear()
        self.tabs.add_tab("first", "Replacement")
        self.tabs.addTab("second", "Another replacement")
        self.assertEqual([item.route_key for item in self.tabs._items], ["first", "second"])
        self.assertIs(self.tabs._items[0].widget, first_button)
        self.assertEqual(first_button.text(), "first.md")
        self.assertEqual(self.events, [])

    def test_unknown_selection_is_ignored_and_existing_tab_remains_selected(self):
        self.add("first", "second")
        self.events.clear()
        self.tabs.set_current_tab("missing")
        self.tabs.setCurrentTab("")
        self.assertEqual(self.tabs._current, "first")
        self.assertEqual([bool(item.widget.property("selected")) for item in self.tabs._items], [True, False])
        self.assertEqual(self.events, [])

    def test_closing_selected_tab_keeps_close_before_replacement_signal(self):
        self.add("first", "second", "third")
        self.tabs.set_current_tab("second")
        self.events.clear()
        self.click_close("second")
        self.assertEqual(self.events, [("close", 1), ("current", "first")])
        self.assertEqual(self.tabs._current, "first")
        self.assertEqual([item.route_key for item in self.tabs._items], ["first", "third"])

    def test_closing_inactive_or_unknown_tab_does_not_change_selection(self):
        self.add("first", "second", "third")
        self.tabs.set_current_tab("third")
        self.events.clear()
        self.click_close("first")
        self.tabs._close_tab("missing")
        self.assertEqual(self.events, [("close", 0)])
        self.assertEqual(self.tabs._current, "third")

    def test_last_close_emits_empty_then_reusing_same_key_selects_new_tab(self):
        self.add("document")
        self.events.clear()
        self.click_close("document")
        self.assertEqual(self.tabs._items, [])
        self.assertEqual(self.tabs._current, "")
        self.assertEqual(self.events, [("close", 0), ("current", "")])
        self.tabs.add_tab("document", "Reopened.md")
        self.assertEqual(self.tabs._current, "document")
        self.assertEqual(self.events[-1], ("current", "document"))
        self.assertTrue(self.tabs._items[0].widget.property("selected"))

    def test_closed_button_cannot_restore_removed_route_before_deferred_deletion(self):
        self.add("first", "second")
        old_button = self.tabs._items[0].widget
        self.tabs._close_tab("first")
        self.events.clear()
        old_button.click()
        self.assertEqual(self.tabs._current, "second")
        self.assertEqual(self.events, [])

    def test_close_callback_can_remove_another_tab_without_invalid_fallback_index(self):
        self.add("first", "second", "third")
        self.tabs.set_current_tab("third")
        def remove_second(index):
            if index == 2:
                self.tabs._close_tab("second")
        self.tabs.tabCloseRequested.connect(remove_second)
        self.events.clear()
        self.click_close("third")
        self.assertEqual(self.tabs._current, "first")
        self.assertEqual(self.events, [("close", 2), ("close", 1), ("current", "first")])

    def test_repeated_add_close_all_and_new_document_syncs_animated_stack(self):
        stack = AnimatedStackedWidget(self.host)
        self.layout.addWidget(stack)
        empty = QtWidgets.QLabel("No documents", stack)
        stack.addWidget(empty)
        keys, pages = [], {}
        counter = [0]
        def select(key):
            stack.setCurrentWidget(pages.get(key, empty))
        def add_document():
            key = f"document-{counter[0]}"
            counter[0] += 1
            page = QtWidgets.QLineEdit(key, stack)
            pages[key] = page
            keys.append(key)
            stack.addWidget(page)
            self.tabs.add_tab(key, key)
            self.tabs.set_current_tab(key)
        def remove_document(index):
            key = keys.pop(index)
            page = pages.pop(key)
            stack.removeWidget(page)
            page.deleteLater()
        self.tabs.currentChanged.connect(select)
        self.tabs.tabAddRequested.connect(add_document)
        self.tabs.tabCloseRequested.connect(remove_document)
        for _ in range(2):
            for _ in range(2):
                QTest.mouseClick(self.tabs._add, QtCore.Qt.MouseButton.LeftButton)
                QTest.qWait(210)
                self.assertIs(stack.currentWidget(), pages[self.tabs._current])
                self.assertIsInstance(stack.currentWidget(), QtWidgets.QLineEdit)
            self.click_close(keys[0])
            self.click_close(keys[0])
            self.assertEqual(self.tabs._current, "")
            self.assertEqual(keys, [])
            self.assertEqual(pages, {})
            self.assertIs(stack.currentWidget(), empty)
        QTest.mouseClick(self.tabs._add, QtCore.Qt.MouseButton.LeftButton)
        QTest.qWait(210)
        self.assertEqual(len(self.tabs._items), 1)
        self.assertIs(stack.currentWidget(), pages[self.tabs._current])


if __name__ == "__main__":
    unittest.main()
