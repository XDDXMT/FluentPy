"""Native table contracts, real edits, checkbox hit testing and cleanup."""

import csv
import io
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from tables import TableDemo

from fluentpy import (
    ActionMenu,
    DoubleSpinBox,
    FluentWindow,
    LineEdit,
    SpinBox,
    TableItemDelegate,
    TableView,
    TableWidget,
    theme,
)
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class TableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.old_mode = theme.mode
        theme.set_mode("light")
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.host = FluentWindow("Table test")
        self.host.resize(700, 420)
        self.view = TableView()
        self.model = QtGui.QStandardItemModel(0, 3, self.host)
        self.model.setHorizontalHeaderLabels(["Name", "Count", "Enabled"])
        for name, count in [("Alpha", 30), ("Beta", 2), ("Gamma", 10), ("Delta", 4)]:
            first, number, check = (
                QtGui.QStandardItem(name),
                QtGui.QStandardItem(),
                QtGui.QStandardItem(),
            )
            number.setData(count, QtCore.Qt.ItemDataRole.DisplayRole)
            check.setCheckable(True)
            check.setEditable(False)
            self.model.appendRow([first, number, check])
        self.view.setModel(self.model)
        self.host.content_layout.addWidget(self.view)
        self.host.show()
        self.app.processEvents()

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        theme.set_mode(self.old_mode)
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_qt_interfaces_and_both_widget_constructors(self):
        self.assertIsInstance(self.view, QtWidgets.QTableView)
        self.assertIs(self.view.model(), self.model)
        table = TableWidget(2, 3, self.host)
        table.setItem(1, 2, QtWidgets.QTableWidgetItem("retained"))
        self.assertEqual(table.item(1, 2).text(), "retained")
        table.insertRow(0)
        self.assertEqual(table.rowCount(), 3)
        self.assertEqual(table.item(2, 2).text(), "retained")
        child = TableWidget(self.host)
        self.assertIs(child.parentWidget(), self.host)
        self.assertEqual(child.rowCount(), 0)

    def test_sort_and_filter_use_the_callers_qt_proxy_and_preserve_numeric_values(self):
        proxy = QtCore.QSortFilterProxyModel(self.host)
        proxy.setSourceModel(self.model)
        proxy.setFilterKeyColumn(-1)
        self.view.setModel(proxy)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
        self.assertEqual([proxy.index(r, 1).data() for r in range(4)], [2, 4, 10, 30])
        proxy.setFilterFixedString("Beta")
        self.assertEqual(proxy.rowCount(), 1)
        self.assertTrue(proxy.setData(proxy.index(0, 1), 77))
        self.assertEqual(self.model.index(1, 1).data(), 77)
        proxy.setFilterFixedString("")
        self.assertEqual(proxy.rowCount(), 4)

    def test_text_editor_commits_and_escape_discards_its_draft(self):
        index = self.model.index(0, 0)
        self.view.edit(index)
        self.app.processEvents()
        editor = self.view.findChild(LineEdit)
        self.assertIsNotNone(editor)
        editor.setText("Committed")
        QTest.keyClick(editor, QtCore.Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertEqual(index.data(), "Committed")
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.view.edit(index)
        self.app.processEvents()
        editor = self.view.findChild(LineEdit)
        editor.setText("Discard this")
        QTest.keyClick(editor, QtCore.Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertEqual(index.data(), "Committed")

    def test_numeric_editor_preserves_integer_type(self):
        index = self.model.index(0, 1)
        self.view.edit(index)
        self.app.processEvents()
        editor = self.view.findChild(SpinBox)
        self.assertIsNotNone(editor)
        editor.setValue(1234)
        QTest.keyClick(editor, QtCore.Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertEqual(index.data(), 1234)
        self.assertIsInstance(index.data(), int)

    def test_checkbox_click_matches_painted_indicator_and_honors_disabled_flags(self):
        index = self.model.index(0, 2)
        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self.view)
        option.rect = self.view.visualRect(index).adjusted(10, 0, -8, 0)
        self.view.itemDelegate().initStyleOption(option, index)
        rect = self.view.style().subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, self.view
        )
        self.assertFalse(rect.isEmpty())
        QTest.mouseClick(self.view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center())
        self.assertEqual(
            index.data(QtCore.Qt.ItemDataRole.CheckStateRole), QtCore.Qt.CheckState.Checked.value
        )
        item = self.model.itemFromIndex(index)
        item.setEnabled(False)
        QTest.mouseClick(self.view.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center())
        self.assertEqual(item.checkState(), QtCore.Qt.CheckState.Checked)

    def test_float_editor_does_not_truncate_unchanged_magnitude_or_precision(self):
        index = self.model.index(0, 1)
        for value in (1e20, 0.12345678901234567, 1.23456789e-20):
            with self.subTest(value=value):
                self.model.setData(index, value)
                self.view.edit(index)
                self.app.processEvents()
                editor = self.view.findChild(DoubleSpinBox)
                self.assertIsNotNone(editor)
                QTest.keyClick(editor, QtCore.Qt.Key.Key_Return)
                self.app.processEvents()
                self.assertEqual(index.data(), value)
                self.assertIsInstance(index.data(), float)
                self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        for value in (float("inf"), float("nan"), 5e-324):
            self.model.setData(index, value)
            self.assertIsNone(
                self.view.itemDelegate().createEditor(
                    self.view.viewport(), QtWidgets.QStyleOptionViewItem(), index
                )
            )

    def test_style_and_density_do_not_rebuild_models_or_lose_selection(self):
        self.view.selectRow(1)
        for style in ("standard", "rounded", "line"):
            self.view.set_row_style(style)
            self.view.set_row_height(52)
            self.assertIs(self.view.model(), self.model)
            self.assertEqual(self.view.selectionModel().selectedRows()[0].row(), 1)
            self.assertEqual(self.model.index(1, 0).data(), "Beta")
        self.assertEqual(self.view.rowHeight(1), 52)

    def test_sparse_copy_preserves_gaps_and_header_visual_order(self):
        self.view.setSelectionBehavior(self.view.SelectionBehavior.SelectItems)
        selection = self.view.selectionModel()
        flags = QtCore.QItemSelectionModel.SelectionFlag.Select
        selection.select(self.model.index(0, 0), flags)
        selection.select(self.model.index(1, 1), flags)
        self.view.horizontalHeader().moveSection(1, 0)
        text = self.view.selection_text(include_headers=True)
        rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
        self.assertEqual(rows, [["Count", "Name"], ["", "Alpha"], ["2", ""]])
        self.view.setColumnHidden(0, True)
        self.assertEqual(self.view.selection_text(), "2")

    def test_copy_quotes_embedded_tabs_newlines_and_keyboard_copy(self):
        self.model.setData(self.model.index(0, 0), "one\ttwo\nthree")
        self.view.setSelectionBehavior(self.view.SelectionBehavior.SelectItems)
        self.view.setCurrentIndex(self.model.index(0, 0))
        self.view.selectionModel().select(
            self.model.index(0, 0), QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        QTest.keyClick(self.view, QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)
        text = self.app.clipboard().text()
        self.assertEqual(next(csv.reader(io.StringIO(text), delimiter="\t")), ["one\ttwo\nthree"])

    def test_copy_from_a_root_index_ignores_selections_under_other_parents(self):
        first, second = QtGui.QStandardItem("first"), QtGui.QStandardItem("second")
        first.appendRow(QtGui.QStandardItem("inside"))
        second.appendRow(QtGui.QStandardItem("outside"))
        self.model.appendRow(first)
        self.model.appendRow(second)
        self.view.setRootIndex(first.index())
        flags = QtCore.QItemSelectionModel.SelectionFlag.Select
        self.view.selectionModel().select(first.child(0).index(), flags)
        self.view.selectionModel().select(second.child(0).index(), flags)
        self.assertEqual(self.view.selection_text(), "inside")

    def test_empty_selection_preserves_clipboard_but_selected_blank_cell_can_clear_it(self):
        self.app.clipboard().setText("keep")
        self.assertFalse(self.view.copy_selection())
        self.assertEqual(self.app.clipboard().text(), "keep")
        self.model.setData(self.model.index(0, 0), "")
        self.view.setSelectionBehavior(self.view.SelectionBehavior.SelectItems)
        self.view.selectionModel().select(
            self.model.index(0, 0), QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        self.assertTrue(self.view.copy_selection())
        self.assertEqual(self.app.clipboard().text(), "")

    def test_right_click_preserves_existing_multi_selection_and_can_select_a_new_target(self):
        selection = self.view.selectionModel()
        flags = (
            QtCore.QItemSelectionModel.SelectionFlag.Select
            | QtCore.QItemSelectionModel.SelectionFlag.Rows
        )
        for row in (0, 1):
            selection.select(self.model.index(row, 0), flags)

        def click(row):
            QTest.mouseClick(
                self.view.viewport(),
                QtCore.Qt.MouseButton.RightButton,
                pos=self.view.visualRect(self.model.index(row, 0)).center(),
            )

        click(1)
        self.assertEqual([i.row() for i in selection.selectedRows()], [0, 1])
        click(2)
        self.assertEqual([i.row() for i in selection.selectedRows()], [2])
        self.view.set_select_right_clicked_row(False)
        click(3)
        self.assertEqual([i.row() for i in selection.selectedRows()], [2])
        self.view.set_select_right_clicked_row(True)
        self.view.setSelectionMode(self.view.SelectionMode.NoSelection)
        self.view.clearSelection()
        click(3)
        self.assertFalse(selection.hasSelection())

    def test_keyboard_context_menu_uses_actionmenu_and_cleans_up_on_hide(self):
        self.view.selectRow(1)
        event = QtGui.QContextMenuEvent(
            QtGui.QContextMenuEvent.Reason.Keyboard, QtCore.QPoint(), QtCore.QPoint()
        )
        self.app.sendEvent(self.view, event)
        menu = self.view._context_menu
        self.assertIsInstance(menu, ActionMenu)
        self.assertTrue(menu._opened)
        action = next(a for a in menu.actions() if a.objectName() == "table-copy-headers")
        action.trigger()
        self.assertTrue(self.app.clipboard().text().startswith("Name\tCount\tEnabled"))
        self.view.hide()
        self.assertFalse(menu._opened)
        self.assertFalse(menu._filter_installed)

    def test_context_actions_respect_model_flags_and_readonly_editor_policy(self):
        self.view.setCurrentIndex(self.model.index(0, 0))
        self.view.setEditTriggers(self.view.EditTrigger.NoEditTriggers)
        menu = self.view.createStandardContextMenu()
        self.assertFalse(
            next(a for a in menu.actions() if a.objectName() == "table-edit").isEnabled()
        )
        self.assertTrue(
            next(a for a in menu.actions() if a.objectName() == "table-select-all").isEnabled()
        )
        menu.deleteLater()

    def test_hover_is_animated_and_model_changes_and_hide_stop_timers(self):
        index = self.model.index(1, 0)
        QTest.mouseMove(self.view.viewport(), self.view.visualRect(index).center())
        QTest.qWait(35)
        self.assertGreater(self.view._hover_amount(index), 0)
        self.assertLess(self.view._hover_amount(index), 1)
        self.model.removeRow(1)
        self.assertFalse(self.view._hover_index.isValid())
        self.view.selectRow(0)
        self.view.hide()
        for animation in (self.view._hover_animation, self.view._selection_animation):
            self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Stopped)

    def test_explicit_cell_background_is_retained_and_theme_switch_preserves_data(self):
        index = self.model.index(0, 1)
        self.model.setData(index, QtGui.QColor("#a33783"), QtCore.Qt.ItemDataRole.BackgroundRole)
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
            rect = self.view.visualRect(index)
            image = self.view.viewport().grab().toImage()
            self.assertEqual(
                image.pixelColor(rect.topLeft() + QtCore.QPoint(5, 5)).name(), "#a33783"
            )
            self.assertEqual(index.data(), 30)
            self.assertEqual(
                self.view.palette().color(QtGui.QPalette.ColorRole.Text).name(), theme.tokens.text
            )

    def test_model_replacement_during_hover_does_not_keep_stale_indexes(self):
        QTest.mouseMove(self.view.viewport(), self.view.visualRect(self.model.index(1, 0)).center())
        replacement = QtGui.QStandardItemModel(0, 2, self.host)
        self.view.setModel(replacement)
        self.model.clear()
        self.assertIs(self.view.model(), replacement)
        self.assertFalse(self.view._hover_index.isValid())
        replacement.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.view.grab()

    def test_large_qt_model_paints_visible_cells_without_per_cell_widgets(self):
        class Counting(TableItemDelegate):
            calls = 0

            def paint(self, painter, option, index):
                self.calls += 1
                super().paint(painter, option, index)

        model = QtGui.QStandardItemModel(20000, 4, self.host)
        model.setData(model.index(19999, 0), "last")
        self.view.setModel(model)
        delegate = Counting(self.view)
        self.view.setItemDelegate(delegate)
        self.view.grab()
        self.assertGreater(delegate.calls, 0)
        self.assertLess(delegate.calls, 200)
        self.assertIsNone(self.view.indexWidget(model.index(0, 0)))
        self.view.scrollTo(model.index(19999, 0))
        self.app.processEvents()
        self.assertFalse(
            self.view.visualRect(model.index(19999, 0))
            .intersected(self.view.viewport().rect())
            .isEmpty()
        )

    def test_rounded_border_clips_children_without_masking_the_table_window(self):
        self.view.set_border_radius(18)
        self.view.resize(550, 300)
        self.app.processEvents()
        header = self.view.horizontalHeader()
        self.assertFalse(header.mask().contains(QtCore.QPoint(0, 0)))
        self.assertTrue(self.view.mask().isEmpty())
        self.view.set_border_visible(False)
        self.assertFalse(self.view.is_border_visible())
        self.assertEqual(self.view.border_radius(), 18)
        self.assertIs(self.view.model(), self.model)


class TableDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = TableDemo()
        self.window.show()
        self.app.processEvents()
        self.examples = self.window.examples

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_search_switch_and_edits_are_retained_by_each_interface(self):
        demo = self.examples
        demo.source.setData(demo.source.index(0, 0), "Edited model")
        demo.table_widget.item(0, 0).setText("Edited widget")
        demo.search.setText("图片")
        self.assertEqual(demo.proxy.rowCount(), 3)
        demo.kind.setCurrentIndex(1)
        self.assertEqual(sum(not demo.table_widget.isRowHidden(r) for r in range(18)), 3)
        demo.search.clear()
        self.assertEqual(demo.source.index(0, 0).data(), "Edited model")
        self.assertTrue(
            demo.table_widget.findItems("Edited widget", QtCore.Qt.MatchFlag.MatchExactly)
        )
        demo.search.setText("not found")
        self.assertTrue(demo.empty_hint.isVisible())

    def test_add_and_delete_work_through_sorted_and_filtered_qt_models(self):
        demo = self.examples
        for kind in (0, 1):
            demo.kind.setCurrentIndex(kind)
            table = demo.current_table()
            count = table.model().rowCount()
            demo.add_button.click()
            self.assertEqual(table.model().rowCount(), count + 1)
            self.assertEqual(len(table.selectionModel().selectedRows()), 1)
            demo.remove_button.click()
            self.assertEqual(table.model().rowCount(), count)

    def test_open_settings_fit_narrow_window_without_rebuilding_tables(self):
        demo = self.examples
        original = demo.table_view.model()
        self.window.resize(560, 720)
        demo.advanced.set_expanded(True)
        QTest.qWait(250)
        self.app.processEvents()
        self.assertEqual(self.window.width(), 560)
        self.assertLessEqual(demo.width(), self.window.width())
        self.assertLessEqual(demo.advanced.width(), demo.width())
        demo.style_choice.setCurrentIndex(2)
        self.assertEqual(demo.table_view.row_style(), "line")
        self.assertIs(demo.table_view.model(), original)

    def test_workbench_reuses_advanced_menu_actions_for_tables_and_inline_editors(self):
        from showcase import Showcase

        window = Showcase(page="tables", restore_preferences=False, startup=False)
        try:
            window.show()
            self.app.processEvents()
            table = window.table_examples.table_view
            table.selectRow(0)
            point = table.visualRect(table.model().index(0, 0)).center()
            self.app.sendEvent(
                table.viewport(),
                QtGui.QContextMenuEvent(
                    QtGui.QContextMenuEvent.Reason.Mouse, point, table.viewport().mapToGlobal(point)
                ),
            )
            menu = window.context_menus.menu
            self.assertTrue(menu._opened)
            self.assertTrue(
                any(action.objectName() == "table-copy-headers" for action in menu.actions())
            )
            menu.dismiss(immediate=True)
            self.assertIsNone(table._context_menu)
        finally:
            window.close()
            window.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
