"""Visible-cell painting and a native, resizable two-line column header."""

from __future__ import annotations

import math

from ..qt import QtCore, QtGui, QtWidgets
from ..theme import theme
from .table_view import TableItemDelegate
from .tree_table_types import TreeRole


def row_group(index) -> bool:
    return bool(index.siblingAtColumn(0).data(TreeRole.Group))


def row_background(view, painter, rect, index):
    """Paint the same surface in cells and the tree's indentation region."""
    painter.fillRect(rect, QtGui.QColor(view._colors.surface))
    row = QtCore.QRectF(0, rect.top(), view.viewport().width(), rect.height())
    rounded = view.row_style() == "rounded"
    target = row.adjusted(3, 2, -3, -2) if rounded else row
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    if row_group(index) or (view.alternatingRowColors() and index.row() % 2):
        painter.setBrush(QtGui.QColor(view._colors.surface_high))
        painter.drawRoundedRect(target, 5 if rounded else 0, 5 if rounded else 0)
    hover = view._hover_amount(index)
    if hover:
        color = QtGui.QColor("#000000" if theme.mode.value == "light" else "#ffffff")
        color.setAlphaF(0.05 * hover)
        painter.setBrush(color)
        painter.drawRoundedRect(target, 5 if rounded else 0, 5 if rounded else 0)
    if view.selectionModel() and view.selectionModel().isSelected(index):
        color = QtGui.QColor(getattr(view._colors, "selection", view._colors.accent))
        color.setAlphaF(
            (1.0 if view.visual_style() == "windows" else 0.15) * view._selection_progress
        )
        painter.setBrush(color)
        painter.drawRoundedRect(target, 5 if rounded else 0, 5 if rounded else 0)
    if view.row_style() == "line":
        painter.setPen(QtGui.QPen(QtGui.QColor(view._colors.border), 1))
        painter.drawLine(
            QtCore.QLineF(rect.left(), rect.bottom() - 0.5, rect.right(), rect.bottom() - 0.5)
        )


class TreeHeaderView(QtWidgets.QHeaderView):
    """Qt owns moving, resizing and sorting; summaries are supplied by callers."""

    def __init__(self, parent):
        super().__init__(QtCore.Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(True)
        self.setSectionsMovable(True)
        self.setHighlightSections(False)
        self.setStretchLastSection(False)
        self.setMinimumSectionSize(24)
        self.setFixedHeight(40)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(parent._show_column_menu)

    def paintSection(self, painter, rect, logicalIndex):
        if not rect.isValid():
            return
        view = self.parent()
        model = self.model()
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(
            rect,
            QtGui.QColor(
                view._colors.header_name
                if view.visual_style() == "windows" and logicalIndex == 0
                else view._colors.surface
            ),
        )
        sorted_column = self.isSortIndicatorShown() and self.sortIndicatorSection() == logicalIndex
        if sorted_column:
            tint = QtGui.QColor(
                view._colors.text if view.visual_style() == "windows" else view._colors.accent
            )
            tint.setAlphaF(0.08)
            painter.fillRect(rect, tint)
        painter.setPen(QtGui.QPen(QtGui.QColor(view._colors.border), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        if view.column_separators():
            painter.drawLine(rect.topRight(), rect.bottomRight())
        spec = view.column_spec(logicalIndex)
        title = spec.title if spec else model.headerData(logicalIndex, self.orientation())
        summary = view.header_summary(logicalIndex)
        padding = 6 if view.visual_style() == "windows" else 10
        text_rect = rect.adjusted(padding, 4, -20 if sorted_column else -padding, -4)
        alignment = spec.alignment if spec else self.defaultAlignment()
        font = self.font()
        if summary:
            font.setPointSizeF(max(11, font.pointSizeF() + 1))
            painter.setFont(font)
            painter.setPen(QtGui.QColor(view._colors.text))
            upper = QtCore.QRect(text_rect.left(), text_rect.top(), text_rect.width(), 23)
            painter.drawText(
                upper,
                alignment,
                painter.fontMetrics().elidedText(
                    summary, QtCore.Qt.TextElideMode.ElideRight, upper.width()
                ),
            )
            text_rect.setTop(text_rect.top() + 24)
        font = self.font()
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(view._colors.text_muted))
        painter.drawText(
            text_rect,
            alignment,
            painter.fontMetrics().elidedText(
                str(title or ""), QtCore.Qt.TextElideMode.ElideRight, text_rect.width()
            ),
        )
        if sorted_column:
            x, y = rect.right() - 10, rect.center().y()
            direction = 1 if self.sortIndicatorOrder() == QtCore.Qt.SortOrder.AscendingOrder else -1
            painter.setPen(QtGui.QPen(QtGui.QColor(view._colors.text_muted), 1.2))
            painter.drawPolyline(
                QtGui.QPolygonF(
                    [
                        QtCore.QPointF(x - 3, y + direction * 2),
                        QtCore.QPointF(x, y - direction * 1),
                        QtCore.QPointF(x + 3, y + direction * 2),
                    ]
                )
            )
        painter.restore()


class TreeItemDelegate(TableItemDelegate):
    """Extend or replace per column; standard roles and Qt editing remain usable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_cache = {}

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        view = self.parent()
        spec = view.column_spec(index.column())
        value = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if spec:
            if spec.formatter and value is not None:
                option.text = str(spec.formatter(value))
            option.displayAlignment = spec.alignment
        if row_group(index):
            option.font.setBold(True)
        if index.data(TreeRole.IconTint) and not option.icon.isNull():
            color = (
                view._colors.text
                if index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
                else view._colors.disabled
            )
            size = self.parent().iconSize()
            key = (option.icon.cacheKey(), size.width(), size.height(), color)
            if key not in self._icon_cache:
                pixmap = option.icon.pixmap(size)
                painter = QtGui.QPainter(pixmap)
                painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), QtGui.QColor(color))
                painter.end()
                if len(self._icon_cache) >= 256:
                    self._icon_cache.clear()
                self._icon_cache[key] = QtGui.QIcon(pixmap)
            option.icon = self._icon_cache[key]

    def paint(self, painter, option, index):
        view = self.parent()
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)
        rect = QtCore.QRectF(option.rect)
        row_background(view, painter, rect, index)
        if opt.backgroundBrush.style() != QtCore.Qt.BrushStyle.NoBrush:
            painter.fillRect(rect, opt.backgroundBrush)
        spec = view.column_spec(index.column())
        kind = index.data(TreeRole.CellKind) or (spec.kind if spec else "text")
        color = QtGui.QColor(
            index.data(TreeRole.Color) or (spec.color if spec else None) or view._colors.accent
        )
        value = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        numeric = (
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        )
        fraction = 0.0
        if numeric and spec:
            fraction = max(0.0, min(1.0, (value - spec.minimum) / (spec.maximum - spec.minimum)))
        if spec and spec.heat and numeric and not row_group(index):
            tint = QtGui.QColor(color)
            if view.visual_style() == "windows":
                low = QtGui.QColor(view._colors.heat_low)
                high = QtGui.QColor(view._colors.heat_high)
                tint = QtGui.QColor.fromRgbF(
                    low.redF() + (high.redF() - low.redF()) * fraction,
                    low.greenF() + (high.greenF() - low.greenF()) * fraction,
                    low.blueF() + (high.blueF() - low.blueF()) * fraction,
                )
            else:
                tint.setAlphaF(
                    (0.09 + fraction * 0.30)
                    if theme.mode.value == "dark"
                    else (0.04 + fraction * 0.20)
                )
            painter.fillRect(rect.adjusted(1, 1, -1, -1), tint)
        selected = bool(opt.state & QtWidgets.QStyle.StateFlag.State_Selected)
        focused = bool(opt.state & QtWidgets.QStyle.StateFlag.State_HasFocus)
        opt.state &= ~(
            QtWidgets.QStyle.StateFlag.State_Selected
            | QtWidgets.QStyle.StateFlag.State_MouseOver
            | QtWidgets.QStyle.StateFlag.State_HasFocus
        )
        opt.backgroundBrush = QtGui.QBrush(QtCore.Qt.BrushStyle.NoBrush)
        opt.rect = self._content_rect(option.rect, index)
        if kind in {"badge", "action"} and opt.text and not row_group(index):
            text = opt.fontMetrics.elidedText(
                opt.text, QtCore.Qt.TextElideMode.ElideRight, max(0, opt.rect.width() - 16)
            )
            width = min(opt.rect.width(), opt.fontMetrics.horizontalAdvance(text) + 16)
            left = opt.rect.left()
            if opt.displayAlignment & QtCore.Qt.AlignmentFlag.AlignRight:
                left = opt.rect.right() - width + 1
            elif opt.displayAlignment & QtCore.Qt.AlignmentFlag.AlignHCenter:
                left = opt.rect.center().x() - width / 2
            pill = QtCore.QRectF(left, rect.center().y() - 11, width, 22)
            tint = QtGui.QColor(color)
            tint.setAlphaF(0.16 if kind == "badge" else 0.10 + view._hover_amount(index) * 0.08)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(tint)
            painter.drawRoundedRect(pill, 4, 4)
            painter.setFont(opt.font)
            painter.setPen(
                color if theme.mode.value == "light" else QtGui.QColor(view._colors.text)
            )
            if index.data(QtCore.Qt.ItemDataRole.ForegroundRole) is not None:
                painter.setPen(opt.palette.color(QtGui.QPalette.ColorRole.Text))
            if not index.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled:
                painter.setPen(QtGui.QColor(view._colors.disabled))
            painter.drawText(pill, QtCore.Qt.AlignmentFlag.AlignCenter, text)
        else:
            if kind == "progress" and numeric and not row_group(index):
                track = rect.adjusted(10, 8, -10, -8)
                tint = QtGui.QColor(color)
                tint.setAlphaF(0.10)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(tint)
                painter.drawRoundedRect(track, 3, 3)
                tint.setAlphaF(0.32)
                painter.setBrush(tint)
                fill = QtCore.QRectF(track)
                fill.setWidth(track.width() * fraction)
                if view.layoutDirection() == QtCore.Qt.LayoutDirection.RightToLeft:
                    fill.moveRight(track.right())
                painter.drawRoundedRect(fill, 3, 3)
            subtitle = index.data(TreeRole.Subtitle)
            view.style().drawControl(
                QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, painter, view
            )
            if opt.features & QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator:
                self._paint_check(painter, opt, view)
            if subtitle:
                sub_rect = QtCore.QRect(option.rect).adjusted(10, option.rect.height() // 2, -8, -3)
                text_rect = view.style().subElementRect(
                    QtWidgets.QStyle.SubElement.SE_ItemViewItemText, opt, view
                )
                sub_rect.setLeft(text_rect.left())
                sub_rect.setRight(text_rect.right())
                font = QtGui.QFont(opt.font)
                font.setPointSizeF(max(8, font.pointSizeF() - 1))
                painter.setFont(font)
                painter.setPen(QtGui.QColor(view._colors.text_muted))
                painter.drawText(
                    sub_rect,
                    opt.displayAlignment,
                    painter.fontMetrics().elidedText(
                        str(subtitle), QtCore.Qt.TextElideMode.ElideRight, sub_rect.width()
                    ),
                )
        if view.column_separators() and not row_group(index):
            painter.setPen(QtGui.QPen(QtGui.QColor(view._colors.border), 1))
            painter.drawLine(
                QtCore.QLineF(rect.right() - 0.5, rect.top(), rect.right() - 0.5, rect.bottom())
            )
        if focused and view.hasFocus():
            painter.setPen(
                QtGui.QPen(
                    QtGui.QColor(
                        view._colors.border_strong
                        if view.visual_style() == "windows"
                        else view._colors.accent
                    ),
                    1,
                )
            )
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            radius = 0 if view.visual_style() == "windows" else 3
            painter.drawRoundedRect(rect.adjusted(1.5, 2.5, -1.5, -2.5), radius, radius)
        if selected and index.column() == view.treePosition() and view.visual_style() != "windows":
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(view._colors.accent))
            painter.drawRoundedRect(
                QtCore.QRectF(rect.left() + 1, rect.center().y() - 8, 2, 16), 1, 1
            )
        painter.restore()

    def _paint_check(self, painter, option, view):
        # Keep Qt's hit region; give the indicator the same visible surface as
        # FluentPy's standalone CheckBox on native and stylesheet Qt styles.
        rect = view.style().subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, view
        )
        box = QtCore.QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        selected = option.checkState != QtCore.Qt.CheckState.Unchecked
        painter.save()
        if not option.state & QtWidgets.QStyle.StateFlag.State_Enabled:
            painter.setOpacity(0.45)
        painter.setBrush(QtGui.QColor(view._colors.accent if selected else view._colors.surface))
        painter.setPen(
            QtGui.QPen(
                QtGui.QColor(view._colors.accent if selected else view._colors.border_strong), 1
            )
        )
        painter.drawRoundedRect(box, 3, 3)
        if selected:
            painter.setPen(
                QtGui.QPen(
                    QtGui.QColor("#ffffff"),
                    1.6,
                    QtCore.Qt.PenStyle.SolidLine,
                    QtCore.Qt.PenCapStyle.RoundCap,
                )
            )
            if option.checkState == QtCore.Qt.CheckState.PartiallyChecked:
                painter.drawLine(
                    QtCore.QPointF(box.left() + 4, box.center().y()),
                    QtCore.QPointF(box.right() - 4, box.center().y()),
                )
            else:
                painter.drawPolyline(
                    QtGui.QPolygonF(
                        [
                            QtCore.QPointF(box.left() + 3, box.center().y()),
                            QtCore.QPointF(box.left() + 6, box.bottom() - 4),
                            QtCore.QPointF(box.right() - 3, box.top() + 4),
                        ]
                    )
                )
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        height = self.parent().row_height()
        if index.data(TreeRole.Subtitle):
            height = max(height, 52)
        return QtCore.QSize(size.width(), height)

    def editorEvent(self, event, model, option, index):
        view = self.parent()
        if view.cell_kind(index) == "action":
            return False  # The view handles pointer and keyboard activation once.
        adjusted = QtWidgets.QStyleOptionViewItem(option)
        adjusted.rect = self._content_rect(option.rect, index)
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, adjusted, index)

    def _content_rect(self, rect, index):
        content = (
            rect.adjusted(5, 0, -5, 0)
            if self.parent().visual_style() == "windows"
            else rect.adjusted(10, 0, -8, 0)
        )
        if index.data(TreeRole.Subtitle):
            content.setBottom(content.top() + max(22, rect.height() // 2))
        return content

    def updateEditorGeometry(self, editor, option, index):
        adjusted = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(adjusted, index)
        adjusted.rect = self._content_rect(option.rect, index)
        text = (
            self.parent()
            .style()
            .subElementRect(
                QtWidgets.QStyle.SubElement.SE_ItemViewItemText, adjusted, self.parent()
            )
        )
        rect = text.adjusted(-1, 1, 0, -1)
        editor.setMinimumHeight(0)
        editor.setMaximumHeight(max(1, rect.height()))
        editor.setGeometry(rect)
