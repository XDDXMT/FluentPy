"""Hierarchical model, incremental-update and native input contracts."""

import os
import subprocess
import sys
import textwrap
import unittest
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from fluentpy import (
    ActionMenu,
    FluentIcon,
    LineEdit,
    TreeCell,
    TreeColumn,
    TreeFlattenProxyModel,
    TreeItemDelegate,
    TreeRole,
    TreeTableView,
    TreeTableWidget,
    theme,
)
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QAbstractItemModelTester, QTest
else:
    from PyQt6.QtTest import QAbstractItemModelTester, QTest


class TreeTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.old_mode = theme.mode
        self.tree = TreeTableWidget(
            [
                TreeColumn("name", "Name", width=240, editable=True),
                TreeColumn(
                    "value", "Value", formatter=lambda v: f"{v} MB", heat=True, editable=True
                ),
                TreeColumn("state", "State", kind="badge"),
                TreeColumn("action", "Action", kind="action"),
            ]
        )
        self.tree.resize(820, 500)
        self.tree.setAnimated(False)
        self.group = self.tree.append_item({"name": "Apps"}, key="apps", group=True)
        self.alpha = self.tree.append_item(
            ["Alpha", 30, "Ready", "Open"], parent="apps", key="alpha"
        )
        self.beta = self.tree.append_item(["Beta", 2, "Ready", "Open"], parent="apps", key="beta")
        self.other = self.tree.append_item(["Other", 10, "Ready", "Open"], key="other")
        self.tree.expandAll()
        self.tree.show()
        self.app.processEvents()

    def tearDown(self):
        self.tree.close()
        self.tree.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        theme.set_mode(self.old_mode)
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_native_models_pass_qt_model_consistency_checks(self):
        testers = [
            QAbstractItemModelTester(
                model, QAbstractItemModelTester.FailureReportingMode.Fatal, self.tree
            )
            for model in (self.tree.source_model, self.tree.proxy_model)
        ]
        with self.tree.batch_update():
            self.tree.update_item("beta", {"value": 9})
            self.tree.append_item(["Third", 10], parent=self.alpha, key="third")
        self.tree.sortByColumn(1, QtCore.Qt.SortOrder.DescendingOrder)
        self.tree.set_filter_text("Third")
        self.tree.set_filter_text("")
        self.tree.remove_item("alpha")
        self.assertEqual(len(testers), 2)

    def test_presentation_format_does_not_change_raw_sorting_or_hierarchy(self):
        self.tree.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
        group = self.tree.view_index("apps")
        self.assertEqual([self.tree.model().index(r, 1, group).data() for r in range(2)], [2, 30])
        self.assertEqual(self.tree.source_model.item(0), self.group)
        self.assertIs(self.alpha.parent(), self.group)
        option = QtWidgets.QStyleOptionViewItem()
        self.tree.itemDelegate().initStyleOption(option, self.tree.view_index("alpha", "value"))
        self.assertEqual(option.text, "30 MB")
        self.assertEqual(self.tree.view_index("alpha", 1).data(), 30)

    def test_external_models_are_not_wrapped_or_reparented(self):
        model = QtGui.QStandardItemModel(self.tree)
        model.appendRow(QtGui.QStandardItem("External"))
        view = TreeTableView(self.tree.columns(), self.tree)
        view.setModel(model)
        self.assertIs(view.model(), model)
        self.assertIs(model.parent(), self.tree)
        self.assertTrue(model.index(0, 0).flags() & QtCore.Qt.ItemFlag.ItemIsEditable)
        view.setModel(None)
        self.assertIsNone(view.model())
        self.assertEqual(model.rowCount(), 1)
        with self.assertRaises(TypeError):
            self.tree.setModel(model)

    def test_column_sort_role_uses_callers_typed_values(self):
        role = int(QtCore.Qt.ItemDataRole.UserRole) + 10
        columns = list(self.tree.columns())
        columns[0] = replace(columns[0], sort_role=role)
        self.tree.set_columns(columns)
        self.alpha.setData(1, role)
        self.beta.setData(2, role)
        self.tree.sortByColumn(0, QtCore.Qt.SortOrder.DescendingOrder)
        first = self.tree.model().index(0, 0, self.tree.view_index("apps"))
        self.assertEqual(first.data(), "Beta")

    def test_recursive_literal_search_includes_ancestors_and_parent_children(self):
        nested = self.tree.append_item({"name": "Needle [x]"}, parent="alpha", key="nested")
        self.tree.set_filter_text("[x]")
        self.assertEqual(self.tree.model().rowCount(), 1)
        self.assertEqual(self.tree.model().index(0, 0).data(), "Apps")
        self.assertTrue(self.tree.view_index(nested).isValid())
        self.assertFalse(self.tree.view_index("beta").isValid())
        self.tree.set_filter_text("Apps")
        self.assertTrue(self.tree.view_index("alpha").isValid())
        self.assertTrue(self.tree.view_index("beta").isValid())

    def test_subtitle_search_respects_the_requested_filter_column(self):
        self.tree.update_item("alpha", {"name": TreeCell("Alpha", subtitle="hidden description")})
        self.tree.set_filter_text("description")
        self.assertTrue(self.tree.view_index("alpha").isValid())
        self.tree.proxy_model.setFilterKeyColumn(2)
        self.assertFalse(self.tree.view_index("alpha").isValid())

    def test_search_clear_restores_pre_search_expansion_selection_and_current(self):
        self.tree.setExpanded(self.tree.view_index("apps"), False)
        self.tree.setCurrentIndex(self.tree.view_index("other"))
        self.tree.set_filter_text("Alpha")
        self.assertTrue(self.tree.isExpanded(self.tree.view_index("apps")))
        self.tree.set_filter_text("")
        self.assertFalse(self.tree.isExpanded(self.tree.view_index("apps")))
        self.assertEqual(self.tree.currentIndex().data(), "Other")
        self.assertIn(self.tree.view_index("other"), self.tree.selectionModel().selectedIndexes())

    def test_updates_keep_persistent_indexes_selection_and_expansion_after_sort(self):
        self.tree.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
        self.tree.setCurrentIndex(self.tree.view_index("alpha"))
        selected = QtCore.QPersistentModelIndex(self.tree.view_index("alpha"))
        resets = []
        self.tree.source_model.modelReset.connect(lambda: resets.append(True))
        with self.tree.batch_update():
            self.tree.update_item("alpha", {"value": 0})
            self.tree.append_item(["Added", 100], parent="apps")
        self.assertEqual(resets, [])
        self.assertTrue(selected.isValid())
        self.assertEqual(selected.data(), "Alpha")
        self.assertEqual(selected.row(), 0)
        self.assertEqual(self.tree.currentIndex().data(), "Alpha")
        self.assertTrue(self.tree.selectionModel().isSelected(QtCore.QModelIndex(selected)))
        self.assertTrue(self.tree.isExpanded(self.tree.view_index("apps")))
        self.assertIs(self.tree.item("alpha"), self.alpha)

    def test_nested_batches_restore_updates_and_proxy_flags_on_exception(self):
        self.tree.proxy_model.setDynamicSortFilter(False)
        self.tree.setUpdatesEnabled(False)
        with self.assertRaisesRegex(RuntimeError, "test"):
            with self.tree.batch_update():
                with self.tree.batch_update():
                    self.tree.update_item("alpha", {"value": 5})
                    raise RuntimeError("test")
        self.assertFalse(self.tree.updatesEnabled())
        self.assertFalse(self.tree.proxy_model.dynamicSortFilter())
        self.tree.setUpdatesEnabled(True)
        self.tree.proxy_model.setDynamicSortFilter(True)

    def test_removed_keys_and_descendants_can_be_reused(self):
        self.tree.append_item(["Nested"], parent="alpha", key="nested")
        self.tree.remove_item("alpha")
        self.assertIsNone(self.tree.item("alpha"))
        self.assertIsNone(self.tree.item("nested"))
        new = self.tree.append_item(["Replacement"], key="alpha")
        self.assertIs(self.tree.item("alpha"), new)
        with self.assertRaises(ValueError):
            self.tree.append_item(["Duplicate"], key="alpha")
        self.tree.clear_items()
        self.assertEqual(self.tree.source_model.rowCount(), 0)
        self.assertEqual(self.tree.source_model.columnCount(), 4)

    def test_plain_patch_preserves_metadata_and_treecell_replaces_it(self):
        self.tree.update_item(
            "alpha",
            {
                "name": TreeCell(
                    "A",
                    icon=FluentIcon.DOCUMENT,
                    subtitle="Details",
                    check_state=QtCore.Qt.CheckState.Checked,
                )
            },
        )
        self.tree.update_item("alpha", {"name": "Renamed"})
        self.assertFalse(self.alpha.icon().isNull())
        self.assertEqual(self.alpha.checkState(), QtCore.Qt.CheckState.Checked)
        self.assertEqual(self.alpha.data(TreeRole.Subtitle), "Details")
        self.tree.update_item("alpha", {"name": TreeCell("Clean")})
        self.assertTrue(self.alpha.icon().isNull())
        self.assertFalse(self.alpha.isCheckable())
        self.assertIsNone(self.alpha.data(TreeRole.Subtitle))

    def test_typed_editor_commits_raw_values_and_checkbox_uses_native_hit_region(self):
        index = self.tree.view_index("alpha")
        self.tree.setCurrentIndex(index)
        self.tree.edit(index)
        self.app.processEvents()
        editor = self.tree.findChild(LineEdit)
        self.assertIsNotNone(editor)
        editor.setText("Edited")
        QTest.keyClick(editor, QtCore.Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertEqual(self.alpha.text(), "Edited")
        self.tree.update_item(
            "beta", {"name": TreeCell("Beta", check_state=QtCore.Qt.CheckState.Unchecked)}
        )
        index = self.tree.view_index("beta")
        opt = QtWidgets.QStyleOptionViewItem()
        opt.initFrom(self.tree)
        opt.rect = self.tree.visualRect(index).adjusted(10, 0, -8, 0)
        self.tree.itemDelegate().initStyleOption(opt, index)
        check = self.tree.style().subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator, opt, self.tree
        )
        QTest.mouseClick(self.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=check.center())
        self.assertEqual(self.beta.checkState(), QtCore.Qt.CheckState.Checked)

    def test_action_cells_emit_once_for_mouse_and_keyboard_and_honor_disabled_flags(self):
        calls = []
        self.tree.cellActionTriggered.connect(
            lambda index: calls.append(index.siblingAtColumn(0).data())
        )
        index = self.tree.view_index("alpha", "action")
        QTest.mouseClick(
            self.tree.viewport(),
            QtCore.Qt.MouseButton.LeftButton,
            pos=self.tree.visualRect(index).center(),
        )
        self.assertEqual(calls, ["Alpha"])
        self.tree.setCurrentIndex(index)
        QTest.keyClick(self.tree, QtCore.Qt.Key.Key_Return)
        self.assertEqual(calls, ["Alpha", "Alpha"])
        self.group.child(self.alpha.row(), 3).setEnabled(False)
        QTest.keyClick(self.tree, QtCore.Qt.Key.Key_Space)
        self.assertEqual(len(calls), 2)

    def test_subtitle_checkbox_click_matches_the_upper_line_in_both_visual_styles(self):
        for style in ("fluent", "windows"):
            self.tree.set_visual_style(style)
            self.tree.update_item(
                "beta",
                {
                    "name": TreeCell(
                        "Beta", subtitle="Details", check_state=QtCore.Qt.CheckState.Unchecked
                    )
                },
            )
            self.app.processEvents()
            index = self.tree.view_index("beta")
            option = QtWidgets.QStyleOptionViewItem()
            option.initFrom(self.tree)
            rect = self.tree.visualRect(index)
            option.rect = (
                rect.adjusted(5, 0, -5, 0) if style == "windows" else rect.adjusted(10, 0, -8, 0)
            )
            option.rect.setBottom(option.rect.top() + rect.height() // 2)
            self.tree.itemDelegate().initStyleOption(option, index)
            box = self.tree.style().subElementRect(
                QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, self.tree
            )
            QTest.mouseClick(
                self.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=box.center()
            )
            self.assertEqual(self.beta.checkState(), QtCore.Qt.CheckState.Checked, style)

    def test_copy_uses_visual_order_formats_and_skips_collapsed_hidden_items(self):
        self.tree.selectAll()
        self.tree.header().moveSection(1, 0)
        self.tree.setColumnHidden(2, True)
        self.tree.setExpanded(self.tree.view_index("apps"), False)
        self.app.processEvents()
        text = self.tree.selection_text(include_headers=True)
        self.assertTrue(text.startswith("Value\tName\tAction"), text)
        self.assertIn("10 MB\tOther\tOpen", text)
        self.assertNotIn("Alpha", text)
        self.assertNotIn("Ready", text)
        self.tree.setRowHidden(self.other.row(), QtCore.QModelIndex(), True)
        self.assertNotIn("Other", self.tree.selection_text())

    def test_copy_escapes_tabs_newlines_and_does_not_overwrite_clipboard_without_rows(self):
        self.tree.update_item("other", {"name": 'a\tb\n"c"'})
        self.tree.setCurrentIndex(self.tree.view_index("other"))
        self.assertIn('"a\tb\n""c"""', self.tree.selection_text())
        self.tree.clearSelection()
        self.app.clipboard().setText("keep")
        self.assertFalse(self.tree.copy_selection())
        self.assertEqual(self.app.clipboard().text(), "keep")

    def test_right_click_keeps_multiselection_and_menu_is_extensible(self):
        self.tree.selectAll()
        before = len(self.tree.selectionModel().selectedIndexes())
        QTest.mouseClick(
            self.tree.viewport(),
            QtCore.Qt.MouseButton.RightButton,
            pos=self.tree.visualRect(self.tree.view_index("alpha")).center(),
        )
        self.assertEqual(len(self.tree.selectionModel().selectedIndexes()), before)
        self.tree.contextMenuAboutToShow.connect(
            lambda menu, index: menu.addAction("Domain action")
        )
        menu = self.tree.createStandardContextMenu()
        self.assertIn("Domain action", [action.text() for action in menu.actions()])
        menu.deleteLater()
        event = QtGui.QContextMenuEvent(
            QtGui.QContextMenuEvent.Reason.Keyboard,
            QtCore.QPoint(),
            self.tree.mapToGlobal(QtCore.QPoint()),
        )
        self.app.sendEvent(self.tree, event)
        self.assertIsInstance(self.tree._context_menu, ActionMenu)
        self.tree.hide()
        self.assertFalse(self.tree._context_menu.isVisible())

    def test_header_summaries_and_column_actions_retain_native_resize_and_move(self):
        self.tree.source_model.setHeaderData(
            1, QtCore.Qt.Orientation.Horizontal, "Model total", TreeRole.Summary
        )
        self.assertEqual(self.tree.header_summary(1), "Model total")
        self.assertEqual(self.tree.header().height(), 58)
        self.tree.set_header_summary("value", "Explicit total")
        self.assertEqual(self.tree.header_summary(1), "Explicit total")
        self.tree.set_header_summary("value", None)
        self.assertEqual(self.tree.header_summary(1), "Model total")
        self.tree.header().resizeSection(0, 25)
        self.assertGreaterEqual(self.tree.columnWidth(0), 48)
        self.tree._show_column_menu(QtCore.QPoint(20, 20))
        actions = self.tree._column_menu.actions()
        self.assertFalse(actions[0].isEnabled())
        actions[1].setChecked(False)
        self.assertTrue(self.tree.isColumnHidden(1))

    def test_replacing_delegates_keeps_native_extension_points(self):
        class CustomDelegate(TreeItemDelegate):
            def initStyleOption(self, option, index):
                super().initStyleOption(option, index)
                option.text = "custom: " + option.text

        delegate = CustomDelegate(self.tree)
        self.tree.setItemDelegateForColumn(2, delegate)
        option = QtWidgets.QStyleOptionViewItem()
        delegate.initStyleOption(option, self.tree.view_index("alpha", 2))
        self.assertEqual(option.text, "custom: Ready")

    def test_many_items_do_not_create_a_widget_for_every_cell(self):
        before = len(self.tree.findChildren(QtWidgets.QWidget))
        with self.tree.batch_update():
            for number in range(1000):
                self.tree.append_item([f"Item {number}", number, "Ready", "Open"], parent="apps")
        self.app.processEvents()
        self.assertEqual(len(self.tree.findChildren(QtWidgets.QWidget)), before)
        self.assertEqual(self.group.rowCount(), 1002)

    def test_model_view_can_fetch_children_lazily(self):
        class LazyModel(QtGui.QStandardItemModel):
            fetched = False

            def hasChildren(self, parent=QtCore.QModelIndex()):
                return parent == self.index(0, 0) or super().hasChildren(parent)

            def canFetchMore(self, parent):
                return parent == self.index(0, 0) and not self.fetched

            def fetchMore(self, parent):
                if self.canFetchMore(parent):
                    self.fetched = True
                    self.itemFromIndex(parent).appendRow(QtGui.QStandardItem("Fetched"))

        model = LazyModel(self.tree)
        model.appendRow(QtGui.QStandardItem("Lazy parent"))
        view = TreeTableView(self.tree)
        view.setModel(model)
        view.expand(model.index(0, 0))
        self.app.processEvents()
        self.assertTrue(model.fetched)
        self.assertEqual(model.index(0, 0, model.index(0, 0)).data(), "Fetched")

    def test_validation_precedes_model_changes(self):
        for change in (
            {"kind": "unknown"},
            {"minimum": 5, "maximum": 5},
            {"color": "not a color"},
            {"width": 10},
            {"key": ""},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(TreeColumn("test", "Test"), **change)
        count = self.tree.source_model.rowCount()
        with self.assertRaises(KeyError):
            self.tree.append_item({"missing": 1})
        with self.assertRaises(ValueError):
            self.tree.set_columns([self.tree.columns()[0]])
        with self.assertRaises(ValueError):
            self.tree.set_columns([self.tree.columns()[0]] * 2)
        self.assertEqual(self.tree.source_model.rowCount(), count)
        self.assertEqual(self.tree.source_model.columnCount(), 4)

    def test_all_cell_kinds_themes_rtl_and_nonfinite_values_render_without_qt_errors(self):
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            for kind in ("text", "badge", "progress", "action"):
                columns = list(self.tree.columns())
                columns[1] = replace(columns[1], kind=kind)
                self.tree.set_columns(columns)
                for value in (float("nan"), float("inf"), -1, 0, 50, 1000):
                    self.tree.update_item("alpha", {"value": value})
                    self.app.processEvents()
                    self.assertFalse(self.tree.grab().isNull())
            self.tree.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
            self.assertFalse(self.tree.grab().isNull())

    def test_three_demo_scenes_exercise_independent_data_and_pause_hidden_timers(self):
        from tree_tables import TreeTableExamples

        demo = TreeTableExamples(self.tree)
        demo.show()
        for scene in range(3):
            demo.scene.setCurrentIndex(scene)
            demo.search.setText("none")
            self.assertEqual(demo.current_tree().model().rowCount(), 0)
            demo.search.clear()
            demo.update_batch()
        demo.live.setChecked(True)
        self.assertTrue(demo.timer.isActive())
        demo.hide()
        self.assertFalse(demo.timer.isActive())

    def test_branch_pointer_clicks_change_structure_immediately_without_selecting_hidden_children(
        self,
    ):
        self.tree.setCurrentIndex(self.tree.view_index("alpha"))
        selected = QtCore.QPersistentModelIndex(self.tree.view_index("alpha"))
        parent = self.tree.view_index("apps")
        rect = self.tree.visualRect(parent)
        point = QtCore.QPoint(rect.left() - self.tree.indentation() // 2, rect.center().y())
        self.assertFalse(self.tree.isAnimated())
        for _ in range(30):
            expanded = self.tree.isExpanded(parent)
            QTest.mouseClick(self.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
            self.assertEqual(self.tree.isExpanded(parent), not expanded)
            self.assertEqual(
                self.tree.visualRect(QtCore.QModelIndex(selected)).isValid(), not expanded
            )
            self.assertTrue(selected.isValid())
        self.assertEqual(self.tree.currentIndex().data(), "Alpha")

    def test_keyboard_expansion_and_windows_palette_do_not_change_other_views(self):
        self.tree.set_visual_style("windows")
        self.tree.set_header_summary("value", "20%")
        self.assertEqual(self.tree.header().height(), 54)
        self.tree.setCurrentIndex(self.tree.view_index("apps"))
        QTest.keyClick(self.tree, QtCore.Qt.Key.Key_Left)
        self.assertFalse(self.tree.isExpanded(self.tree.view_index("apps")))
        QTest.keyClick(self.tree, QtCore.Qt.Key.Key_Right)
        self.assertTrue(self.tree.isExpanded(self.tree.view_index("apps")))
        other = TreeTableView(self.tree)
        self.assertEqual(other.visual_style(), "fluent")
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
            self.assertFalse(self.tree.grab().isNull())
            self.assertNotEqual(self.tree._colors.border, other._colors.border)

    def test_native_workbench_selected_child_and_rapid_parent_clicks_have_a_watchdog(self):
        root = Path(__file__).resolve().parents[1]
        script = textwrap.dedent("""
            import faulthandler, sys
            faulthandler.enable()
            faulthandler.dump_traceback_later(8)
            sys.path.insert(0, 'examples')
            from showcase import Showcase
            from fluentpy.qt import QT_API, QtCore, QtWidgets
            if QT_API == 'PySide6':
                from PySide6.QtTest import QTest
            else:
                from PyQt6.QtTest import QTest
            app = QtWidgets.QApplication([])
            window = Showcase(restore_preferences=False, startup=False)
            window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
            window.resize(1110, 773)
            window.show()
            window.set_page('tree-tables', animated=False)
            QTest.qWait(150)
            tree = window.tree_table_examples.metrics
            heartbeats = []
            timer = QtCore.QTimer(window)
            timer.setInterval(1)
            timer.timeout.connect(lambda: heartbeats.append(1))
            timer.start()
            for round in range(20):
                for key in ('app-0', 'app-1', 'app-2', 'apps'):
                    tree.expandAll()
                    parent = tree.view_index(key)
                    child = tree.model().index(0, 0, parent)
                    tree.setCurrentIndex(child)
                    rect = tree.visualRect(parent)
                    point = QtCore.QPoint(rect.left() - tree.indentation() // 2, rect.center().y())
                    QTest.mouseMove(tree.viewport(), point)
                    QTest.mouseClick(tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
                    assert not tree.isExpanded(parent), key
                    assert not tree.visualRect(child).isValid(), key
                    QTest.qWait(2)
            assert heartbeats
            print('80 native parent clicks completed; event loop remained responsive')
            window.close()
            faulthandler.cancel_dump_traceback_later()
        """)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root / "src")
        env["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else "offscreen"
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-c", script],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("80 native parent clicks completed", result.stdout)

    def test_physical_double_click_during_arrow_motion_reopens_the_same_branch(self):
        parent = self.tree.view_index("apps")
        self.tree.setCurrentIndex(self.tree.view_index("alpha"))
        rect = self.tree.visualRect(parent)
        point = QtCore.QPoint(rect.left() - self.tree.indentation() // 2, rect.center().y())
        for _ in range(12):
            QTest.mouseClick(self.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
            self.assertFalse(self.tree.isExpanded(parent))
            QTest.qWait(20)
            QTest.mouseDClick(self.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
            QTest.mouseRelease(self.tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
            self.assertTrue(self.tree.isExpanded(parent))
            self.assertTrue(self.tree.visualRect(self.tree.view_index("alpha")).isValid())
        QTest.qWait(140)
        self.assertFalse(self.tree._branch_index.isValid())

    def test_inline_editor_starts_after_the_icon_and_uses_the_title_line(self):
        self.tree.update_item(
            "alpha",
            {
                "name": TreeCell(
                    "Alpha", icon=FluentIcon.FOLDER, subtitle="Description", editable=True
                )
            },
        )
        self.app.processEvents()
        index = self.tree.view_index("alpha")
        option = QtWidgets.QStyleOptionViewItem()
        option.initFrom(self.tree)
        option.rect = self.tree.visualRect(index)
        self.tree.itemDelegate().initStyleOption(option, index)
        content = QtWidgets.QStyleOptionViewItem(option)
        content.rect = option.rect.adjusted(10, 0, -8, 0)
        content.rect.setBottom(content.rect.top() + option.rect.height() // 2)
        icon_rect = self.tree.style().subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemDecoration, content, self.tree
        )
        self.tree.edit(index)
        self.app.processEvents()
        editor = self.tree.findChild(LineEdit)
        self.assertGreater(editor.geometry().left(), icon_rect.right())
        self.assertLessEqual(editor.geometry().bottom(), content.rect.bottom())
        editor.setText("Renamed")
        QTest.keyClick(editor, QtCore.Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertEqual(self.alpha.text(), "Renamed")

    def test_global_sort_flattens_all_loaded_descendants_and_round_trips_source_indexes(self):
        nested = self.tree.append_item(["Nested", 25], parent="beta", key="nested")
        self.tree.setExpanded(self.tree.view_index("apps"), False)
        self.tree.set_sort_mode("flat")
        testers = [
            QAbstractItemModelTester(
                model, QAbstractItemModelTester.FailureReportingMode.Fatal, self.tree
            )
            for model in (self.tree.flatten_model, self.tree.proxy_model)
        ]
        self.tree.sortByColumn(1, QtCore.Qt.SortOrder.DescendingOrder)
        self.assertEqual(
            [self.tree.model().index(row, 1).data() for row in range(self.tree.model().rowCount())],
            [30, 25, 10, 2],
        )
        self.assertEqual(self.tree.source_index(self.tree.view_index("nested")), nested.index())
        self.tree.proxy_model.setData(self.tree.view_index("nested", 1), 99)
        self.assertEqual(
            nested.parent().child(nested.row(), 1).data(QtCore.Qt.ItemDataRole.DisplayRole), 99
        )
        self.tree.append_item(["New", 50], parent="apps", key="new")
        self.tree.remove_item("beta")
        self.assertEqual(self.tree.model().rowCount(), 3)
        self.assertEqual(len(testers), 2)
        self.tree.set_sort_mode("hierarchical")
        self.assertIs(self.tree.proxy_model.sourceModel(), self.tree.source_model)
        self.assertFalse(self.tree.isExpanded(self.tree.view_index("apps")))

    def test_global_live_updates_keep_selection_and_search_maps_both_proxy_layers(self):
        self.tree.setCurrentIndex(self.tree.view_index("alpha"))
        self.tree.set_flat_sorting_enabled(True)
        self.tree.sortByColumn(1, QtCore.Qt.SortOrder.DescendingOrder)
        self.assertEqual(self.tree.sort_mode(), "flat")
        self.assertEqual(self.tree.currentIndex().data(), "Alpha")
        selected = QtCore.QPersistentModelIndex(self.tree.view_index("alpha"))
        resets = []
        self.tree.flatten_model.modelReset.connect(lambda: resets.append(True))
        with self.tree.batch_update():
            self.tree.update_item("alpha", {"value": 1})
        self.assertTrue(selected.isValid())
        self.assertEqual(selected.row(), 2)
        self.assertEqual(resets, [])
        self.tree.set_filter_text("Beta")
        self.assertEqual(self.tree.model().rowCount(), 1)
        self.tree.set_filter_text("")
        self.assertEqual(self.tree.currentIndex().data(), "Alpha")

    def test_flat_proxy_can_wrap_an_external_qt_model_without_a_workbench(self):
        proxy = TreeFlattenProxyModel(self.tree)
        proxy.setSourceModel(self.tree.source_model)
        self.assertEqual(proxy.rowCount(), 3)
        self.assertFalse(proxy.parent(proxy.index(0, 0)).isValid())
        self.assertEqual(
            proxy.mapToSource(proxy.mapFromSource(self.alpha.index())), self.alpha.index()
        )
        proxy.setSourceModel(None)
        self.assertEqual(proxy.rowCount(), 0)
        self.assertFalse(proxy.mapFromSource(self.alpha.index()).isValid())

    def test_all_demo_headers_sort_globally_and_can_return_to_hierarchy(self):
        from tree_tables import TreeTableExamples

        demo = TreeTableExamples(self.tree)
        demo.show()
        for scene, column in ((0, 3), (1, 3), (2, 2)):
            demo.scene.setCurrentIndex(scene)
            view = demo.current_tree()
            original_roots = view.model().rowCount()
            view.sortByColumn(column, QtCore.Qt.SortOrder.DescendingOrder)
            self.assertEqual(demo.mode.currentIndex(), 1)
            numbers = [
                view.model().index(row, column).data() for row in range(view.model().rowCount())
            ]
            numbers = [number for number in numbers if isinstance(number, (int, float))]
            self.assertEqual(numbers, sorted(numbers, reverse=True))
            demo.mode.setCurrentIndex(0)
            self.assertEqual(view.model().rowCount(), original_roots)


if __name__ == "__main__":
    unittest.main()
