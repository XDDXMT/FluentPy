"""Flatten loaded Qt model indexes while retaining their original data source."""

from __future__ import annotations

from ..qt import QtCore
from .tree_table_types import TreeRole


class TreeFlattenProxyModel(QtCore.QAbstractProxyModel):
    """Expose all loaded descendants as rows for a global Qt sorting proxy.

    Source cells are never copied. Group captions are omitted by default.
    Structural changes follow Qt's reset contract; ordinary dataChanged updates
    forward to the corresponding flat indexes without resetting selection.
    Unloaded descendants remain the source model's responsibility.
    """

    def __init__(self, parent=None, *, include_groups: bool = False):
        super().__init__(parent)
        self._include_groups = bool(include_groups)
        self._rows = []
        self._positions = {}
        self._connections = []
        self._resetting = False

    def setSourceModel(self, source_model):
        for connection in self._connections:
            QtCore.QObject.disconnect(connection)
        self._connections.clear()
        self._begin_reset()
        super().setSourceModel(source_model)
        if source_model is not None:
            for before, after in (
                (source_model.modelAboutToBeReset, source_model.modelReset),
                (source_model.rowsAboutToBeInserted, source_model.rowsInserted),
                (source_model.rowsAboutToBeRemoved, source_model.rowsRemoved),
                (source_model.rowsAboutToBeMoved, source_model.rowsMoved),
                (source_model.columnsAboutToBeInserted, source_model.columnsInserted),
                (source_model.columnsAboutToBeRemoved, source_model.columnsRemoved),
                (source_model.columnsAboutToBeMoved, source_model.columnsMoved),
                (source_model.layoutAboutToBeChanged, source_model.layoutChanged),
            ):
                self._connections.append(before.connect(self._begin_reset))
                self._connections.append(after.connect(self._end_reset))
            self._connections.append(source_model.dataChanged.connect(self._source_data_changed))
            self._connections.append(source_model.headerDataChanged.connect(self.headerDataChanged))
        self._end_reset()

    def _begin_reset(self, *args):
        if not self._resetting:
            self._resetting = True
            self.beginResetModel()

    def _end_reset(self, *args):
        if not self._resetting:
            return
        self._rows.clear()
        self._positions.clear()
        model = self.sourceModel()
        if model is not None:
            pending = [model.index(row, 0) for row in reversed(range(model.rowCount()))]
            while pending:
                index = pending.pop()
                if not index.isValid():
                    continue
                if self._include_groups or not index.data(TreeRole.Group):
                    persistent = QtCore.QPersistentModelIndex(index)
                    self._positions[persistent] = len(self._rows)
                    self._rows.append(persistent)
                pending.extend(
                    model.index(row, 0, index) for row in reversed(range(model.rowCount(index)))
                )
        self._resetting = False
        self.endResetModel()

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if (
            parent.isValid()
            or not 0 <= row < len(self._rows)
            or not 0 <= column < self.columnCount()
        ):
            return QtCore.QModelIndex()
        return self.createIndex(row, column)

    def parent(self, index):
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        model = self.sourceModel()
        return model.columnCount() if model is not None and not parent.isValid() else 0

    def mapToSource(self, proxy_index):
        if (
            not proxy_index.isValid()
            or proxy_index.model() is not self
            or not 0 <= proxy_index.row() < len(self._rows)
        ):
            return QtCore.QModelIndex()
        return QtCore.QModelIndex(self._rows[proxy_index.row()]).siblingAtColumn(
            proxy_index.column()
        )

    def mapFromSource(self, source_index):
        if not source_index.isValid() or source_index.model() is not self.sourceModel():
            return QtCore.QModelIndex()
        row = self._positions.get(QtCore.QPersistentModelIndex(source_index.siblingAtColumn(0)))
        return self.index(row, source_index.column()) if row is not None else QtCore.QModelIndex()

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        source = self.mapToSource(index)
        return source.data(role) if source.isValid() else None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        source = self.mapToSource(index)
        return self.sourceModel().setData(source, value, role) if source.isValid() else False

    def flags(self, index):
        source = self.mapToSource(index)
        if not source.isValid():
            return QtCore.Qt.ItemFlag.NoItemFlags
        # A flat row has no unambiguous destination parent for native drops.
        return source.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        model = self.sourceModel()
        return model.headerData(section, orientation, role) if model is not None else None

    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.ItemDataRole.EditRole):
        model = self.sourceModel()
        return (
            model.setHeaderData(section, orientation, value, role) if model is not None else False
        )

    def _source_data_changed(self, top_left, bottom_right, roles=()):
        model = self.sourceModel()
        if not roles or int(TreeRole.Group) in roles:
            for row in range(top_left.row(), bottom_right.row() + 1):
                index = model.index(row, 0, top_left.parent())
                visible = self._include_groups or not index.data(TreeRole.Group)
                present = QtCore.QPersistentModelIndex(index) in self._positions
                if visible != present:
                    self._begin_reset()
                    self._end_reset()
                    return
        for row in range(top_left.row(), bottom_right.row() + 1):
            first = self.mapFromSource(model.index(row, top_left.column(), top_left.parent()))
            last = self.mapFromSource(model.index(row, bottom_right.column(), top_left.parent()))
            if first.isValid() and last.isValid():
                self.dataChanged.emit(first, last, roles)
