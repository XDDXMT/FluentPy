"""Hierarchical Qt views with configurable cells and native model ownership."""

from __future__ import annotations

import csv
import io
from contextlib import contextmanager

from ..qt import QtCore, QtGui, QtWidgets, Signal
from ..theme import theme
from ..theme.fonts import ui_font
from .action_menu import ActionMenu
from .scroll_bar import FluentScrollBar
from .tree_table_delegate import TreeHeaderView, TreeItemDelegate, row_background
from .tree_table_style import tree_colors
from .tree_table_types import TreeColumn, TreeRole, column_definitions


class TreeFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Recursive literal search and per-column raw sorting, performed by Qt.

    Matches retain their ancestors. Matching a parent includes its children.
    Subclass filterAcceptsRow/lessThan for domain-specific policies. Neither
    the source hierarchy nor the source's ownership is changed by this proxy.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns = ()
        self.setRecursiveFilteringEnabled(True)
        self.setAutoAcceptChildRows(True)
        self.setFilterKeyColumn(-1)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    def set_columns(self, columns) -> None:
        self._columns = column_definitions(columns)
        self.sort(self.sortColumn(), self.sortOrder())

    def set_filter_text(self, text: str) -> None:
        """Literal text, including punctuation; use Qt regex methods when needed."""
        self.setFilterFixedString(text)

    def filterAcceptsRow(self, source_row, source_parent):
        if super().filterAcceptsRow(source_row, source_parent):
            return True
        model = self.sourceModel()
        if model is None:
            return False
        expression = self.filterRegularExpression()
        key_column = self.filterKeyColumn()
        columns = range(model.columnCount(source_parent)) if key_column < 0 else (key_column,)
        return any(
            expression.match(
                str(model.index(source_row, column, source_parent).data(TreeRole.Subtitle) or "")
            ).hasMatch()
            for column in columns
        )

    def sort(self, column, order=QtCore.Qt.SortOrder.AscendingOrder):
        if 0 <= column < len(self._columns):
            self.setSortRole(self._columns[column].sort_role)
        super().sort(column, order)


class TreeTableView(QtWidgets.QTreeView):
    """Connect any QAbstractItemModel; setModel keeps ordinary Qt semantics.

    Columns configure presentation, not business data. The caller owns external
    models, their lazy loading, drag/drop policy and update notifications.
    QModelIndex signals always refer to the model currently displayed by Qt.
    """

    cellActionTriggered = Signal(QtCore.QModelIndex)
    contextMenuAboutToShow = Signal(object, QtCore.QModelIndex)

    def __init__(self, columns=(), parent=None):
        if isinstance(columns, QtWidgets.QWidget):
            parent, columns = columns, ()
        super().__init__(parent)
        self._columns = column_definitions(columns)
        self._summaries = {}
        self._row_height = 34
        self._row_style = "standard"
        self._visual_style = "fluent"
        self._colors = tree_colors(self._visual_style)
        self._separators = False
        self._empty_text = "暂无数据"
        self._connections = []
        self._context_menu = self._context_native = self._column_menu = None
        self._right_click_selects = True
        self._hover_index = QtCore.QPersistentModelIndex()
        self._previous_hover = QtCore.QPersistentModelIndex()
        self._pressed_action = QtCore.QPersistentModelIndex()
        self._hover_progress = self._selection_progress = 1.0
        self._batch_depth = 0
        self._hover_animation = self._animation(self._set_hover_progress)
        self._selection_animation = self._animation(self._set_selection_progress)
        self._branch_animation = self._animation(self._set_branch_progress)
        self._branch_animation.finished.connect(self._finish_branch_motion)
        self._branch_index = QtCore.QPersistentModelIndex()
        self._branch_progress = 0.0
        self._branch_pressed = False
        self.setHeader(TreeHeaderView(self))
        self.header().sectionResized.connect(self._constrain_column_width)
        self.header().setSortIndicator(-1, QtCore.Qt.SortOrder.AscendingOrder)
        self.setSortingEnabled(True)
        self.setItemDelegate(TreeItemDelegate(self))
        self.setFont(ui_font(theme.tokens.font_size, self.font()))
        self.setIconSize(QtCore.QSize(18, 18))
        self.setIndentation(22)
        # Keep model expansion synchronous. Qt's whole-subtree snapshot
        # animation is unnecessary for our Python-painted rows and branches.
        self.setAnimated(False)
        self.expanded.connect(lambda index: self._branch_changed(index, True))
        self.collapsed.connect(lambda index: self._branch_changed(index, False))
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)
        self.setEditTriggers(self.EditTrigger.DoubleClicked | self.EditTrigger.EditKeyPressed)
        self.setVerticalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollBar(FluentScrollBar(parent=self))
        self.setHorizontalScrollBar(FluentScrollBar(QtCore.Qt.Orientation.Horizontal, self))
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _animation(self, callback):
        animation = QtCore.QVariantAnimation(self)
        animation.setDuration(120)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(callback)
        return animation

    def _set_hover_progress(self, value):
        self._hover_progress = float(value)
        self.viewport().update()

    def _set_selection_progress(self, value):
        self._selection_progress = float(value)
        self.viewport().update()

    def _set_branch_progress(self, value):
        self._branch_progress = float(value)
        self.viewport().update()

    def _finish_branch_motion(self):
        self._branch_index = QtCore.QPersistentModelIndex()
        self.viewport().update()

    def _branch_changed(self, index, expanded):
        if (
            index == self._branch_index
            and self._branch_animation.state() == QtCore.QAbstractAnimation.State.Running
        ):
            # A reversal is an input command, not another queued transition.
            self._branch_animation.stop()
            self._branch_index = QtCore.QPersistentModelIndex()
            self._branch_progress = float(expanded)
            self.viewport().update()
            return
        start = self._branch_progress if index == self._branch_index else float(not expanded)
        self._branch_animation.stop()
        self._branch_index = QtCore.QPersistentModelIndex(index)
        self._branch_progress = start
        self._branch_animation.setStartValue(start)
        self._branch_animation.setEndValue(float(expanded))
        if self.isVisible():
            self._branch_animation.start()
        else:
            self._branch_progress = float(expanded)

    def _hover_amount(self, index):
        row = index.siblingAtColumn(0)
        if row == self._hover_index:
            return self._hover_progress
        if row == self._previous_hover:
            return 1.0 - self._hover_progress
        return 0.0

    def columns(self) -> tuple[TreeColumn, ...]:
        return self._columns

    def column_spec(self, column: int) -> TreeColumn | None:
        return self._columns[column] if 0 <= column < len(self._columns) else None

    def set_columns(self, columns) -> None:
        """Replace presentation; data and model objects remain untouched."""
        self._columns = column_definitions(columns)
        if isinstance(self.model(), TreeFilterProxyModel):
            self.model().set_columns(self._columns)
        self._configure_columns()

    def column_number(self, column: int | str) -> int:
        if isinstance(column, str):
            for number, spec in enumerate(self._columns):
                if spec.key == column:
                    return number
            raise KeyError(column)
        if not isinstance(column, int) or not 0 <= column < self.header().count():
            raise IndexError(column)
        return column

    def setModel(self, model):
        for connection in self._connections:
            QtCore.QObject.disconnect(connection)
        self._connections.clear()
        super().setModel(model)
        if model is not None:
            for signal in (model.modelReset, model.columnsInserted, model.columnsRemoved):
                self._connections.append(signal.connect(self._configure_columns))
            self._connections.append(model.headerDataChanged.connect(self._update_header_size))
            if isinstance(model, TreeFilterProxyModel):
                model.set_columns(self._columns)
        self._reset_visual_state()
        self._configure_columns()

    def _configure_columns(self, *args):
        for number, spec in enumerate(self._columns[: self.header().count()]):
            self.header().setSectionResizeMode(
                number,
                QtWidgets.QHeaderView.ResizeMode.Stretch
                if spec.stretch
                else QtWidgets.QHeaderView.ResizeMode.Interactive,
            )
            self.setColumnWidth(number, spec.width)
        self._update_header_size()
        self.doItemsLayout()
        self.viewport().update()

    def _constrain_column_width(self, column, previous, width):
        spec = self.column_spec(column)
        if spec and width < spec.minimum_width and not self.isColumnHidden(column):
            self.header().resizeSection(column, spec.minimum_width)

    def set_header_summary(self, column: int | str, text: str | None) -> None:
        """Set an explicit summary; None resumes the model's Summary header role."""
        number = self.column_number(column)
        if text is None:
            self._summaries.pop(number, None)
        else:
            self._summaries[number] = str(text)
        self._update_header_size()

    def header_summary(self, column: int) -> str:
        if column in self._summaries:
            return self._summaries[column]
        model = self.model()
        value = (
            model.headerData(column, QtCore.Qt.Orientation.Horizontal, TreeRole.Summary)
            if model
            else None
        )
        return str(value) if value is not None else ""

    def _update_header_size(self, *args):
        self.header().setFixedHeight(
            (54 if self._visual_style == "windows" else 58)
            if any(self.header_summary(column) for column in range(self.header().count()))
            else 40
        )
        self.header().viewport().update()

    def row_height(self) -> int:
        return self._row_height

    def set_row_height(self, height: int) -> None:
        if not isinstance(height, int) or height < 24:
            raise ValueError("row height must be an integer >= 24")
        self._row_height = height
        self.doItemsLayout()
        self.viewport().update()

    def row_style(self) -> str:
        return self._row_style

    def set_row_style(self, style: str) -> None:
        if style not in {"standard", "rounded", "line"}:
            raise ValueError("row style must be standard, rounded or line")
        self._row_style = style
        self.viewport().update()

    def visual_style(self) -> str:
        return self._visual_style

    def set_visual_style(self, style: str) -> None:
        """Choose fluent or windows table surfaces without changing the app theme."""
        if style not in {"fluent", "windows"}:
            raise ValueError("visual style must be fluent or windows")
        self._visual_style = style
        self._apply_theme()
        self._update_header_size()

    def column_separators(self) -> bool:
        return self._separators

    def set_column_separators(self, visible: bool) -> None:
        self._separators = bool(visible)
        self.viewport().update()
        self.header().viewport().update()

    def set_empty_text(self, text: str) -> None:
        self._empty_text = str(text)
        self.viewport().update()

    def set_select_right_clicked_row(self, enabled: bool) -> None:
        self._right_click_selects = bool(enabled)

    def cell_kind(self, index) -> str:
        spec = self.column_spec(index.column())
        return index.data(TreeRole.CellKind) or (spec.kind if spec else "text")

    @contextmanager
    def batch_update(self):
        """Coalesce painting and proxy sorting, retaining persistent Qt indexes.

        Source notifications are never blocked. Inserts/edits preserve selection
        and expansion; a model reset still follows Qt's normal reset contract.
        Nested batches and exceptions restore the original update settings.
        """
        outer = self._batch_depth == 0
        model = self.model()
        proxy = model if isinstance(model, QtCore.QSortFilterProxyModel) else None
        if outer:
            updates = self.updatesEnabled()
            dynamic = proxy.dynamicSortFilter() if proxy else False
            scroll = self.verticalScrollBar().value()
            self.setUpdatesEnabled(False)
            if proxy:
                proxy.setDynamicSortFilter(False)
        self._batch_depth += 1
        try:
            yield self
        finally:
            self._batch_depth -= 1
            if outer:
                if proxy and self.model() is proxy:
                    proxy.setDynamicSortFilter(dynamic)
                    if dynamic:
                        proxy.invalidate()
                self.verticalScrollBar().setValue(scroll)
                self.setUpdatesEnabled(updates)
                self.viewport().update()

    def selection_text(self, *, include_headers: bool = False) -> str:
        """Visible selected rows in screen order; hidden/collapsed rows are omitted."""
        selection, model = self.selectionModel(), self.model()
        if selection is None or model is None or not selection.hasSelection():
            return ""
        selected = set(selection.selectedIndexes())
        columns = [
            self.header().logicalIndex(i)
            for i in range(self.header().count())
            if not self.isColumnHidden(self.header().logicalIndex(i))
        ]
        rows = []
        index = model.index(0, 0, self.rootIndex())
        while index.isValid():
            indexes = [index.siblingAtColumn(column) for column in columns]
            if any(cell in selected for cell in indexes):
                rows.append(
                    [self._display_text(cell) if cell in selected else "" for cell in indexes]
                )
            index = self.indexBelow(index)
        if not rows:
            return ""
        if include_headers:
            rows.insert(
                0,
                [
                    self.column_spec(c).title
                    if self.column_spec(c)
                    else str(model.headerData(c, QtCore.Qt.Orientation.Horizontal) or "")
                    for c in columns
                ],
            )
        stream = io.StringIO(newline="")
        csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(rows)
        return stream.getvalue().removesuffix("\n")

    def _display_text(self, index):
        value = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        spec = self.column_spec(index.column())
        if value is None:
            return ""
        return str(spec.formatter(value) if spec and spec.formatter else value)

    def copy_selection(self, *, include_headers: bool = False) -> bool:
        text = self.selection_text(include_headers=include_headers)
        if not text:
            return False
        QtWidgets.QApplication.clipboard().setText(text)
        return True

    def createStandardContextMenu(self, position=None):
        """An action container for ActionMenu and existing workbench adapters."""
        menu = QtWidgets.QMenu(self)
        index = self.indexAt(position) if position is not None else self.currentIndex()
        for text, callback in (
            ("复制选中内容", lambda: self.copy_selection()),
            ("连同表头复制", lambda: self.copy_selection(include_headers=True)),
        ):
            action = menu.addAction(text)
            action.setEnabled(bool(self.selectionModel() and self.selectionModel().hasSelection()))
            action.triggered.connect(callback)
        menu.addSeparator()
        for text, callback in (
            ("展开全部", self.expandAll),
            ("折叠全部", self.collapseAll),
            ("全选", self.selectAll),
        ):
            menu.addAction(text).triggered.connect(callback)
        self.contextMenuAboutToShow.emit(menu, index)
        return menu

    def contextMenuEvent(self, event):
        if self._context_menu is None:
            self._context_menu = ActionMenu(self)
        self._context_menu.dismiss(immediate=True)
        self._context_menu.clear()
        if self._context_native is not None:
            self._context_native.deleteLater()
        self._context_native = self.createStandardContextMenu()
        self._context_menu.addActions(self._context_native.actions())
        if event.reason() == QtGui.QContextMenuEvent.Reason.Keyboard:
            point = self.viewport().mapTo(self, self.visualRect(self.currentIndex()).bottomLeft())
        else:
            point = self.mapFromGlobal(event.globalPos())
        self._context_menu.popup_at(self, point)
        event.accept()

    def _show_column_menu(self, position):
        if self._column_menu is None:
            self._column_menu = ActionMenu(self)
        self._column_menu.dismiss(immediate=True)
        self._column_menu.clear()
        for column in range(self.header().count()):
            spec = self.column_spec(column)
            title = (
                spec.title
                if spec
                else self.model().headerData(column, QtCore.Qt.Orientation.Horizontal)
            )
            action = self._column_menu.add_action(
                str(title), checkable=True, checked=not self.isColumnHidden(column)
            )
            action.setEnabled(column != self.treePosition())
            action.toggled.connect(lambda checked, c=column: self.setColumnHidden(c, not checked))
        self._column_menu.popup_at(self.header(), position)

    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        self._pressed_action = QtCore.QPersistentModelIndex()
        self._branch_pressed = False
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._on_branch(
            index, event.position().toPoint()
        ):
            self._branch_pressed = True
            self.setExpanded(index, not self.isExpanded(index))
            event.accept()
            return
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            selection = self.selectionModel()
            if (
                self._right_click_selects
                and selection
                and index.isValid()
                and self.selectionMode() != self.SelectionMode.NoSelection
                and index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
                and index.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable
            ):
                flags = QtCore.QItemSelectionModel.SelectionFlag.NoUpdate
                if not selection.isSelected(index):
                    flags = QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
                    if self.selectionBehavior() == self.SelectionBehavior.SelectRows:
                        flags |= QtCore.QItemSelectionModel.SelectionFlag.Rows
                selection.setCurrentIndex(index, flags)
            event.accept()
            return
        super().mousePressEvent(event)
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and index.isValid()
            and self.cell_kind(index) == "action"
            and index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
        ):
            self._pressed_action = QtCore.QPersistentModelIndex(index)

    def mouseReleaseEvent(self, event):
        if self._branch_pressed and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._branch_pressed = False
            event.accept()
            return
        pressed = self._pressed_action
        self._pressed_action = QtCore.QPersistentModelIndex()
        super().mouseReleaseEvent(event)
        index = self.indexAt(event.position().toPoint())
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and pressed.isValid()
            and index == pressed
            and index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
        ):
            self.cellActionTriggered.emit(index)

    def _on_branch(self, index, point):
        if (
            not index.isValid()
            or not self.itemsExpandable()
            or not index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
            or not self.model().hasChildren(index)
            or (index.parent() == self.rootIndex() and not self.rootIsDecorated())
        ):
            return False
        column = self.treePosition()
        if column < 0:
            column = self.header().logicalIndex(0)
        rect = self.visualRect(index.siblingAtColumn(column))
        if self.layoutDirection() == QtCore.Qt.LayoutDirection.RightToLeft:
            branch = QtCore.QRect(rect.right() + 1, rect.top(), self.indentation(), rect.height())
        else:
            branch = QtCore.QRect(
                rect.left() - self.indentation(), rect.top(), self.indentation(), rect.height()
            )
        return branch.contains(point)

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if self._on_branch(index, event.position().toPoint()):
            # A physical second click arrives as MouseButtonDblClick, not
            # another mousePressEvent. It must reverse the pending arrow too.
            self._branch_pressed = True
            self.setExpanded(index, not self.isExpanded(index))
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        row = index.siblingAtColumn(0) if index.isValid() else QtCore.QModelIndex()
        if row != self._hover_index:
            self._previous_hover, self._hover_index = (
                self._hover_index,
                QtCore.QPersistentModelIndex(row),
            )
            self._hover_animation.stop()
            self._hover_animation.start()
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        index = self.currentIndex()
        if (
            event.key()
            in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space)
            and index.isValid()
            and self.cell_kind(index) == "action"
            and index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
        ):
            self.cellActionTriggered.emit(index)
            event.accept()
        elif event.matches(QtGui.QKeySequence.StandardKey.Copy):
            self.copy_selection()
            event.accept()
        else:
            super().keyPressEvent(event)

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        if hasattr(self, "_selection_animation"):
            self._selection_animation.stop()
            if self.isVisible() and not selected.isEmpty():
                self._selection_animation.start()
            else:
                self._selection_progress = 1.0

    def leaveEvent(self, event):
        self._previous_hover = self._hover_index
        self._hover_index = QtCore.QPersistentModelIndex()
        self._hover_animation.stop()
        if self.isVisible():
            self._hover_animation.start()
        super().leaveEvent(event)

    def _reset_visual_state(self, *, clear_branch_press=True):
        for animation in (self._hover_animation, self._selection_animation, self._branch_animation):
            animation.stop()
        self._hover_index = self._previous_hover = QtCore.QPersistentModelIndex()
        self._pressed_action = QtCore.QPersistentModelIndex()
        if clear_branch_press:
            self._branch_pressed = False
        self._branch_index = QtCore.QPersistentModelIndex()
        self._hover_progress = self._selection_progress = 1.0

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if hasattr(self, "_hover_animation"):
            self._reset_visual_state(clear_branch_press=False)

    def hideEvent(self, event):
        self._reset_visual_state()
        for menu in (self._context_menu, self._column_menu):
            if menu is not None:
                menu.dismiss(immediate=True)
        super().hideEvent(event)

    def drawBranches(self, painter, rect, index):
        painter.save()
        painter.setClipRect(rect)
        row_background(self, painter, QtCore.QRectF(rect), index)
        if self.model().hasChildren(index):
            rtl = self.layoutDirection() == QtCore.Qt.LayoutDirection.RightToLeft
            x = (
                rect.left() + self.indentation() / 2
                if rtl
                else rect.right() - self.indentation() / 2
            )
            y = rect.center().y()
            painter.setPen(QtGui.QPen(QtGui.QColor(self._colors.text_muted), 1.4))
            progress = (
                self._branch_progress
                if index == self._branch_index
                else float(self.isExpanded(index))
            )
            painter.translate(x, y)
            if rtl:
                painter.scale(-1, 1)
            painter.rotate(90 * progress)
            painter.drawPolyline(
                QtGui.QPolygonF(
                    [QtCore.QPointF(-1, -3), QtCore.QPointF(2, 0), QtCore.QPointF(-1, 3)]
                )
            )
        painter.restore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.model() is None or self.model().rowCount(self.rootIndex()) == 0:
            painter = QtGui.QPainter(self.viewport())
            painter.setPen(QtGui.QColor(self._colors.text_muted))
            painter.drawText(
                self.viewport().rect().adjusted(16, 16, -16, -16),
                QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap,
                self._empty_text,
            )

    def _apply_theme(self):
        self._colors = tree_colors(self._visual_style)
        colors = self._colors
        palette = self.palette()
        for role, value in (
            (QtGui.QPalette.ColorRole.Base, colors.surface),
            (QtGui.QPalette.ColorRole.Text, colors.text),
            (QtGui.QPalette.ColorRole.WindowText, colors.text),
            (QtGui.QPalette.ColorRole.HighlightedText, colors.text),
            (QtGui.QPalette.ColorRole.Highlight, colors.accent),
        ):
            palette.setColor(role, QtGui.QColor(value))
        palette.setColor(
            QtGui.QPalette.ColorGroup.Disabled,
            QtGui.QPalette.ColorRole.Text,
            QtGui.QColor(colors.disabled),
        )
        for widget in (self, self.viewport(), self.header()):
            widget.setPalette(palette)
        self.setStyleSheet(
            f"QTreeView {{background:{colors.surface};color:{colors.text};"
            f"border:1px solid {colors.border};border-radius:{0 if self._visual_style == 'windows' else 6}px;outline:0;}}"
            f"QHeaderView {{background:{colors.surface};border:none;}}"
        )
        self.viewport().update()
        self.header().viewport().update()
