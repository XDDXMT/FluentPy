"""Convenience items backed by ordinary QStandardItemModel notifications."""

from __future__ import annotations

from collections.abc import Hashable, Mapping

from ..icons import FluentIcon, fluent_icon
from ..qt import QtCore, QtGui, Signal
from .tree_flatten_proxy import TreeFlattenProxyModel
from .tree_table import TreeFilterProxyModel, TreeTableView
from .tree_table_types import TreeCell, TreeRole, column_definitions


class TreeTableWidget(TreeTableView):
    """Direct item API with stable keys, an exposed source model and a proxy.

    Keys are optional, unique and hashable; incremental updates retain the same
    QStandardItem objects. All mutation belongs on the GUI thread. Use
    TreeTableView when providing your own model, including lazy-loading models.
    """

    sortModeChanged = Signal(str)

    def __init__(self, columns, parent=None):
        super().__init__(columns, parent)
        self._key_indexes = {}
        self._filter_snapshot = None
        self._sort_mode = "hierarchical"
        self._flat_sorting = False
        self._switching_sort_mode = False
        self._hierarchy_expansion = []
        self.flatten_model = None
        self.source_model = QtGui.QStandardItemModel(0, len(self.columns()), self)
        self.source_model.setHorizontalHeaderLabels([column.title for column in self.columns()])
        self.proxy_model = TreeFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.setModel(self.proxy_model)
        self.header().sortIndicatorChanged.connect(self._sort_indicator_changed)

    def sort_mode(self) -> str:
        return self._sort_mode

    def set_flat_sorting_enabled(self, enabled: bool) -> None:
        """Opt in to a globally sorted flat view when a column header is used."""
        self._flat_sorting = bool(enabled)

    def _sort_indicator_changed(self, column, order):
        if self._flat_sorting and column >= 0 and not self._switching_sort_mode:
            self.set_sort_mode("flat")

    def set_sort_mode(self, mode: str) -> None:
        """Switch hierarchical/flat display without copying source cells.

        Flat mode includes all loaded descendants, including collapsed items,
        and omits group captions. Returning to hierarchy clears the global sort
        and restores the expansion present before the switch.
        """
        if mode not in {"hierarchical", "flat"}:
            raise ValueError("sort mode must be hierarchical or flat")
        if mode == self._sort_mode:
            return
        selected = [
            QtCore.QPersistentModelIndex(self.source_index(index))
            for index in self.selectionModel().selectedIndexes()
        ]
        current = QtCore.QPersistentModelIndex(self.source_index(self.currentIndex()))
        header = self.header().saveState()
        if mode == "flat":
            self._hierarchy_expansion = self._expanded_source_indexes()
            self._hierarchy_root_decorated = self.rootIsDecorated()
        self._switching_sort_mode = True
        try:
            self._sort_mode = mode
            if mode == "flat":
                if self.flatten_model is None:
                    self.flatten_model = TreeFlattenProxyModel(self)
                self.flatten_model.setSourceModel(self.source_model)
                self.proxy_model.setSourceModel(self.flatten_model)
                self.setRootIsDecorated(False)
            else:
                self.proxy_model.setSourceModel(self.source_model)
                self.flatten_model.setSourceModel(None)
                self.setRootIsDecorated(self._hierarchy_root_decorated)
            self.header().restoreState(header)
            if mode == "hierarchical":
                self.sortByColumn(-1, QtCore.Qt.SortOrder.AscendingOrder)
                self.collapseAll()
                for index in self._hierarchy_expansion:
                    mapped = self._from_source(QtCore.QModelIndex(index))
                    if mapped.isValid():
                        self.setExpanded(mapped, True)
            selection = QtCore.QItemSelection()
            for index in selected:
                mapped = self._from_source(QtCore.QModelIndex(index))
                if mapped.isValid():
                    selection.select(mapped, mapped)
            self.selectionModel().select(
                selection, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
            self.selectionModel().setCurrentIndex(
                self._from_source(QtCore.QModelIndex(current)),
                QtCore.QItemSelectionModel.SelectionFlag.NoUpdate,
            )
        finally:
            self._switching_sort_mode = False
        self.sortModeChanged.emit(mode)

    def source_index(self, index) -> QtCore.QModelIndex:
        """Map a displayed cell to source_model in either sorting mode."""
        mapped = self.proxy_model.mapToSource(index)
        return self.flatten_model.mapToSource(mapped) if self._sort_mode == "flat" else mapped

    def _from_source(self, index):
        mapped = self.flatten_model.mapFromSource(index) if self._sort_mode == "flat" else index
        return self.proxy_model.mapFromSource(mapped)

    def setModel(self, model):
        owned = self.__dict__.get("proxy_model")
        if owned is not None and model is not owned:
            raise TypeError("TreeTableWidget owns its model; use TreeTableView for external models")
        super().setModel(model)

    def set_columns(self, columns) -> None:
        """Update presentation; populated schemas keep their existing key order."""
        columns = column_definitions(columns)
        if self.source_model.rowCount() and tuple(c.key for c in columns) != tuple(
            c.key for c in self.columns()
        ):
            raise ValueError("populated item schemas must retain their column keys and order")
        self.source_model.setColumnCount(len(columns))
        self.source_model.setHorizontalHeaderLabels([c.title for c in columns])
        super().set_columns(columns)

    def _values(self, values):
        if isinstance(values, Mapping):
            keys = {column.key for column in self.columns()}
            if values.keys() - keys:
                raise KeyError(next(iter(values.keys() - keys)))
            return [
                (number, values[column.key])
                for number, column in enumerate(self.columns())
                if column.key in values
            ]
        if isinstance(values, (str, bytes)):
            raise TypeError("values must be a mapping or a sequence of cells")
        values = tuple(values)
        if len(values) > len(self.columns()):
            raise ValueError("more cells than columns")
        return list(enumerate(values))

    def item(self, key: Hashable) -> QtGui.QStandardItem | None:
        """Find a keyed source item, including items currently filtered out."""
        index = self._key_indexes.get(key)
        if index is None:
            return None
        if not index.isValid():
            self._key_indexes.pop(key, None)
            return None
        return self.source_model.itemFromIndex(QtCore.QModelIndex(index))

    def _resolve_item(self, item):
        if not isinstance(item, QtGui.QStandardItem):
            item = self.item(item)
        if item is None or item.model() is not self.source_model:
            raise KeyError("item is missing or belongs to another model")
        return self.source_model.itemFromIndex(item.index().siblingAtColumn(0))

    def _write_cell(self, item, value, column):
        if not isinstance(value, TreeCell):
            item.setData(value, QtCore.Qt.ItemDataRole.DisplayRole)
            return
        item.setData(value.value, QtCore.Qt.ItemDataRole.DisplayRole)
        item.setData(value.subtitle or None, TreeRole.Subtitle)
        item.setData(value.kind, TreeRole.CellKind)
        item.setData(value.color, TreeRole.Color)
        item.setData(value.subtitle or None, QtCore.Qt.ItemDataRole.AccessibleDescriptionRole)
        item.setToolTip(value.tooltip)
        icon = value.icon
        item.setData(isinstance(icon, FluentIcon), TreeRole.IconTint)
        if isinstance(icon, FluentIcon):
            icon = fluent_icon(icon)
        elif isinstance(icon, QtGui.QPixmap):
            icon = QtGui.QIcon(icon)
        else:
            icon = QtGui.QIcon(icon) if icon is not None else QtGui.QIcon()
        item.setIcon(icon)
        item.setEditable(column.editable if value.editable is None else value.editable)
        item.setCheckable(value.check_state is not None)
        if value.check_state is not None:
            item.setCheckState(value.check_state)
        else:
            item.setData(None, QtCore.Qt.ItemDataRole.CheckStateRole)

    def append_item(
        self, values, *, parent=None, key: Hashable | None = None, group: bool = False
    ) -> QtGui.QStandardItem:
        """Append raw values or TreeCell metadata under a key or source item.

        Missing mapping keys create empty cells. Group rows use a stronger
        surface; their other columns may still contain caller-provided values.
        No process monitoring, aggregation or business actions are implicit.
        """
        if not self.columns():
            raise ValueError("add at least one column before adding items")
        pairs = self._values(values)
        if key is not None and self.item(key) is not None:
            raise ValueError(f"duplicate item key: {key!r}")
        parent_item = (
            self.source_model.invisibleRootItem() if parent is None else self._resolve_item(parent)
        )
        items = [QtGui.QStandardItem() for _ in self.columns()]
        for item, column in zip(items, self.columns()):
            item.setEditable(column.editable)
        for number, value in pairs:
            self._write_cell(items[number], value, self.columns()[number])
        items[0].setData(key, TreeRole.Key)
        items[0].setData(bool(group), TreeRole.Group)
        parent_item.appendRow(items)
        if key is not None:
            self._key_indexes[key] = QtCore.QPersistentModelIndex(items[0].index())
        return items[0]

    def update_item(self, item, values) -> None:
        """Patch cells without recreating rows, children, keys or selection."""
        pairs = self._values(values)
        first = self._resolve_item(item)
        parent = first.parent() or self.source_model.invisibleRootItem()
        for number, value in pairs:
            cell = parent.child(first.row(), number)
            self._write_cell(cell, value, self.columns()[number])

    def remove_item(self, item) -> None:
        first = self._resolve_item(item)
        parent = first.parent() or self.source_model.invisibleRootItem()
        parent.removeRow(first.row())
        self._key_indexes = {
            key: index for key, index in self._key_indexes.items() if index.isValid()
        }

    def clear_items(self) -> None:
        """Remove items, preserving the schema and header configuration."""
        self.source_model.removeRows(0, self.source_model.rowCount())
        self._key_indexes.clear()
        self._filter_snapshot = None

    def view_index(self, item, column: int | str = 0) -> QtCore.QModelIndex:
        """Map a source item or key to the current view; filtered items are invalid."""
        first = self._resolve_item(item)
        return self._from_source(first.index().siblingAtColumn(self.column_number(column)))

    def _expanded_source_indexes(self):
        if self._sort_mode == "flat":
            return self._hierarchy_expansion
        result, pending = [], [QtCore.QModelIndex()]
        while pending:
            parent = pending.pop()
            for row in range(self.source_model.rowCount(parent)):
                index = self.source_model.index(row, 0, parent)
                if self.isExpanded(self._from_source(index)):
                    result.append(QtCore.QPersistentModelIndex(index))
                if self.source_model.hasChildren(index):
                    pending.append(index)
        return result

    def set_filter_text(self, text: str) -> None:
        """Search all columns and subtitles, retaining matching parent paths.

        Search expands its visible results. Clearing it restores the expansion
        and selection present before search; source items added during search
        remain in the model and retain their data.
        """
        text = str(text)
        if text and self._filter_snapshot is None:
            self._filter_snapshot = (
                self._expanded_source_indexes(),
                [
                    QtCore.QPersistentModelIndex(self.source_index(index))
                    for index in self.selectionModel().selectedIndexes()
                ],
                QtCore.QPersistentModelIndex(self.source_index(self.currentIndex())),
                self.verticalScrollBar().value(),
            )
        self.proxy_model.set_filter_text(text)
        if text:
            self.expandAll()
        elif self._filter_snapshot is not None:
            expanded, selected, current, scroll = self._filter_snapshot
            self._filter_snapshot = None
            self.collapseAll()
            for index in expanded:
                mapped = self._from_source(QtCore.QModelIndex(index))
                if mapped.isValid():
                    self.setExpanded(mapped, True)
            selection = QtCore.QItemSelection()
            for index in selected:
                mapped = self._from_source(QtCore.QModelIndex(index))
                if mapped.isValid():
                    selection.select(mapped, mapped)
            self.selectionModel().select(
                selection, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
            self.selectionModel().setCurrentIndex(
                self._from_source(QtCore.QModelIndex(current)),
                QtCore.QItemSelectionModel.SelectionFlag.NoUpdate,
            )
            self.verticalScrollBar().setValue(scroll)
