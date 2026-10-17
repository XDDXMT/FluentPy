"""An animated in-window action menu using real Qt actions and buttons."""

from __future__ import annotations

from ..icons import FluentIcon, fluent_icon
from ..qt import QtCore, QtGui, QtWidgets, Signal, Slot
from ..theme import theme
from ..theme.fonts import ui_font
from .button import TextButton
from .scroll_bar import FluentScrollBar


class _MenuSurface(QtWidgets.QWidget):
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(10.5, 8.5, -10.5, -11.5)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        painter.save()
        painter.translate(0, 2)
        for spread in range(10, 0, -1):
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 1 if theme.mode.value == "light" else 2), spread))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        painter.restore()
        painter.setBrush(QtGui.QColor(theme.tokens.surface))
        painter.setPen(QtGui.QPen(QtGui.QColor(theme.tokens.border), 1))
        painter.drawPath(path)


class _MenuRow(TextButton):
    entered = Signal()

    def __init__(self, action, parent):
        super().__init__(action.text(), parent)
        self.action = action
        self.active = False
        self.setFixedHeight(32)
        self.setMinimumWidth(0)
        self.setEnabled(action.isEnabled())
        self.setIcon(action.icon())
        self.setAccessibleName(action.text())

    def minimumSizeHint(self):
        return QtCore.QSize(0, 32)

    def enterEvent(self, event):
        self.entered.emit()
        super().enterEvent(event)

    def _surface_color(self):
        return self._surface_hover_color() if self.active else super()._surface_color()

    def _draw_content(self, painter, rect, color):
        painter.setPen(color)
        x = rect.left() + 10
        icon = fluent_icon(FluentIcon.CHECKMARK) if self.action.isCheckable() and self.action.isChecked() else self.action.icon()
        if not icon.isNull():
            self._draw_tinted_icon(painter, QtCore.QRect(round(x), round(rect.center().y()-8), 16, 16), color, icon)
        x += 25
        shortcut = self.action.shortcut().toString(QtGui.QKeySequence.SequenceFormat.NativeText)
        width = self.fontMetrics().horizontalAdvance(shortcut) if shortcut else 0
        text_rect = QtCore.QRectF(x, rect.top(), max(0, rect.right()-x-12-width-(18 if shortcut else 0)), rect.height())
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignVCenter,
                         self.fontMetrics().elidedText(self.action.text().replace("&&", "\0").replace("&", "").replace("\0", "&"),
                                                      QtCore.Qt.TextElideMode.ElideRight, round(text_rect.width())))
        if shortcut:
            painter.setPen(QtGui.QColor(theme.tokens.text_muted if self.isEnabled() else theme.tokens.disabled))
            painter.drawText(QtCore.QRectF(rect.right()-12-width, rect.top(), width, rect.height()),
                             QtCore.Qt.AlignmentFlag.AlignVCenter, shortcut)


class ActionMenu(QtWidgets.QWidget):
    """A small action list anchored inside its owner window, without a popup HWND.

    Qt actions retain their enabled, visible, checkable, icon and shortcut state.
    Nested submenus are deliberately not part of this single-level component.
    """

    triggered = Signal(QtGui.QAction)
    aboutToShow = Signal()
    aboutToHide = Signal()

    SHOW_DURATION = 180
    HIDE_DURATION = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        if parent is not None:
            parent.destroyed.connect(self.deleteLater)
        self._anchor = None
        self._watched = []
        self._previous_focus = None
        self._closing = False
        self._opened = False
        self._placing = False
        self._active = -1
        self._progress = 0.0
        self._rest = QtCore.QPoint()
        self._direction = -1
        self._items = []
        self._filter_installed = False
        self._batching = False
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        self._surface = _MenuSurface(self)
        self._opacity = QtWidgets.QGraphicsOpacityEffect(self._surface)
        self._surface.setGraphicsEffect(self._opacity)
        self._scroll = QtWidgets.QScrollArea(self._surface)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBar(FluentScrollBar(parent=self._scroll))
        self._scroll.setObjectName("actionMenuScroll")
        self._content = QtWidgets.QWidget(self._scroll)
        self._content.setObjectName("actionMenuContent")
        self._layout = QtWidgets.QVBoxLayout(self._content)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._scroll.setWidget(self._content)
        self._reveal = QtCore.QVariantAnimation(self)
        self._reveal.valueChanged.connect(self._set_progress)
        self._reveal.finished.connect(self._motion_finished)
        self._dirty = False
        self._rebuild_timer = QtCore.QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.timeout.connect(self._rebuild)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)
        self.hide()

    def add_action(self, text, *, icon=None, callback=None, checkable=False, checked=False, enabled=True, shortcut=""):
        action = QtGui.QAction(str(text), self)
        if icon is not None:
            action.setIcon(fluent_icon(icon) if isinstance(icon, FluentIcon) else icon)
        action.setCheckable(checkable)
        action.setChecked(checked)
        action.setEnabled(enabled)
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(shortcut))
        if callback is not None:
            action.triggered.connect(callback)
        return self.addAction(action)

    def addAction(self, action):  # noqa: N802
        if isinstance(action, str):
            return self.add_action(action)
        if not isinstance(action, QtGui.QAction):
            raise TypeError("ActionMenu expects a QAction or text")
        if action not in self.actions():
            action.changed.connect(self._schedule_rebuild)
            action.triggered.connect(self._forward_triggered)
            QtWidgets.QWidget.addAction(self, action)
        return action

    def add_separator(self):
        action = QtGui.QAction(self)
        action.setSeparator(True)
        return self.addAction(action)

    def addSeparator(self):  # noqa: N802
        return self.add_separator()

    def remove_action(self, action):
        if action in self.actions():
            action.changed.disconnect(self._schedule_rebuild)
            action.triggered.disconnect(self._forward_triggered)
            QtWidgets.QWidget.removeAction(self, action)

    def removeAction(self, action):  # noqa: N802
        self.remove_action(action)

    def clear(self):
        self._batching = True
        try:
            for action in self.actions():
                self.remove_action(action)
                if action.parent() is self and not action.associatedObjects():
                    action.deleteLater()
        finally:
            self._batching = False
        self._rebuild()

    def anchor_widget(self):
        return self._anchor

    def actionEvent(self, event):
        super().actionEvent(event)
        if hasattr(self, "_layout"):
            if event.type() == QtCore.QEvent.Type.ActionRemoved and not self._batching:
                self._rebuild()
            else:
                self._schedule_rebuild()

    def _schedule_rebuild(self):
        self._dirty = True
        if not self._rebuild_timer.isActive():
            self._rebuild_timer.start(0)

    def _rebuild(self):
        self._dirty = False
        self._rebuild_timer.stop()
        active_action = self._items[self._active].action if 0 <= self._active < len(self._items) else None
        while self._layout.count():
            widget = self._layout.takeAt(0).widget()
            widget.hide()
            widget.deleteLater()
        self._items = []
        for action in self.actions():
            if not action.isVisible():
                continue
            if action.isSeparator():
                line = QtWidgets.QFrame(self._content)
                line.setFixedHeight(7)
                line.setObjectName("actionMenuSeparator")
                self._layout.addWidget(line)
            else:
                row = _MenuRow(action, self._content)
                row.entered.connect(self._row_entered)
                row.clicked.connect(self._row_clicked)
                self._items.append(row)
                self._layout.addWidget(row)
        self._layout.activate()
        self._active = next((i for i, row in enumerate(self._items) if row.action is active_action and row.isEnabled()), -1)
        if self._opened:
            if not self._items:
                self.dismiss(immediate=True)
            else:
                self._place()
                self._select(self._active if self._active >= 0 else self._first_enabled())

    def _first_enabled(self):
        return next((i for i, row in enumerate(self._items) if row.isEnabled()), -1)

    def _select(self, index):
        self._active = index
        for i, row in enumerate(self._items):
            row.active = i == index
            row.update()
        if 0 <= index < len(self._items):
            row = self._items[index]
            row.setFocus(QtCore.Qt.FocusReason.PopupFocusReason)
            self._scroll.ensureWidgetVisible(row, 0, 2)

    @Slot()
    def _row_entered(self):
        row = self.sender()
        if row in self._items and row.isEnabled():
            self._select(self._items.index(row))

    @Slot()
    def _row_clicked(self):
        row = self.sender()
        if row in self._items:
            self._activate(row.action)

    @Slot()
    def _forward_triggered(self):
        action = self.sender()
        if action in self.actions():
            self.triggered.emit(action)

    def _activate(self, action):
        if self._closing or not action.isEnabled() or not action.isVisible():
            return
        self.dismiss()
        action.trigger()

    def popup(self, anchor):
        if not isinstance(anchor, QtWidgets.QWidget):
            raise TypeError("popup anchor must be a QWidget")
        if self._dirty:
            self._rebuild()
        if not anchor.isEnabled() or not anchor.isVisible() or not self._items:
            return False
        if self._opened:
            self.dismiss(immediate=True)
        owner = anchor.window()
        for other in owner.findChildren(ActionMenu):
            if other is not self and other._opened:
                other.dismiss(immediate=True)
        if self.parentWidget() is not owner:
            self.setParent(owner, QtCore.Qt.WindowType.Widget)
        self._anchor = anchor
        self._previous_focus = anchor
        node = anchor
        while node is not None:
            self._watched.append(node)
            node.installEventFilter(self)
            if node is owner:
                break
            node = node.parentWidget()
        anchor.destroyed.connect(self._anchor_destroyed)
        self._closing = False
        self._opened = True
        self._progress = 0.0
        self._place()
        self._set_progress(0.0)
        app = QtWidgets.QApplication.instance()
        app.installEventFilter(self)
        self._filter_installed = True
        self.aboutToShow.emit()
        self.show()
        self.raise_()
        self.setFocus(QtCore.Qt.FocusReason.PopupFocusReason)
        self._select(self._first_enabled())
        self._animate(1.0, self.SHOW_DURATION)
        return True

    def dismiss(self, *, immediate=False):
        if not self._opened:
            return
        if not self._closing:
            self._closing = True
            self.aboutToHide.emit()
        if immediate or self._progress <= .001:
            self._reveal.stop()
            self._finish_hide()
        else:
            self._animate(0.0, self.HIDE_DURATION)

    def _animate(self, end, duration):
        self._reveal.stop()
        self._reveal.setDuration(duration)
        self._reveal.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic if end else QtCore.QEasingCurve.Type.InCubic)
        self._reveal.setStartValue(self._progress)
        self._reveal.setEndValue(end)
        self._reveal.start()

    def _set_progress(self, value):
        self._progress = float(value)
        self._opacity.setOpacity(self._progress)
        self._surface.move(self._rest + QtCore.QPoint(0, round(self._direction * 8 * (1-self._progress))))

    def _motion_finished(self):
        if self._closing:
            self._finish_hide()

    def _remove_watchers(self):
        if self._filter_installed:
            QtWidgets.QApplication.instance().removeEventFilter(self)
            self._filter_installed = False
        for node in self._watched:
            try:
                node.removeEventFilter(self)
            except RuntimeError:
                pass
        self._watched.clear()
        if self._anchor is not None:
            try:
                self._anchor.destroyed.disconnect(self._anchor_destroyed)
            except (RuntimeError, TypeError):
                pass

    def _finish_hide(self):
        self._remove_watchers()
        self._opened = False
        self._closing = False
        self.hide()
        try:
            if self._previous_focus is not None and self._previous_focus.isVisible():
                self._previous_focus.setFocus(QtCore.Qt.FocusReason.PopupFocusReason)
        except RuntimeError:
            pass
        self._previous_focus = None
        self._anchor = None

    def _anchor_destroyed(self):
        self._anchor = None
        self.dismiss(immediate=True)

    def _place(self):
        if self._placing or self._anchor is None:
            return
        self._placing = True
        try:
            owner = self.parentWidget()
            self.setGeometry(owner.rect())
            anchor = QtCore.QRect(self._anchor.mapTo(owner, QtCore.QPoint()), self._anchor.size())
            metrics = QtGui.QFontMetrics(ui_font(theme.tokens.font_size))
            widths = [metrics.horizontalAdvance(row.action.text()) + metrics.horizontalAdvance(row.action.shortcut().toString()) + 90
                      for row in self._items]
            width = max(0, min(self.width()-8, 480, max([160, anchor.width()+20, *widths])))
            height = max(0, min(self.height()-8, 360, self._layout.sizeHint().height()+32))
            self._surface.resize(width, height)
            self._scroll.setGeometry(17, 15, max(0, width-34), max(0, height-30))
            x = anchor.left()-10
            below = anchor.bottom()+1-3
            above = anchor.top()-height+3
            fits_below = below+height <= self.height()-4
            y = below if fits_below or above < 4 else above
            self._direction = -1 if fits_below else 1
            x = max(4, min(x, self.width()-width-4))
            y = max(4, min(y, self.height()-height-4))
            self._rest = QtCore.QPoint(x, y)
            self._set_progress(self._progress)
        finally:
            self._placing = False

    def eventFilter(self, watched, event):
        if not self._opened:
            return False
        kind = event.type()
        if watched in self._watched:
            if kind in (QtCore.QEvent.Type.Hide, QtCore.QEvent.Type.Close, QtCore.QEvent.Type.WindowDeactivate):
                self.dismiss(immediate=True)
            elif kind == QtCore.QEvent.Type.EnabledChange and not watched.isEnabled():
                self.dismiss(immediate=True)
            elif kind in (QtCore.QEvent.Type.Resize, QtCore.QEvent.Type.Move) and not self._closing:
                self._place()
        if (self._opened and isinstance(watched, QtWidgets.QWidget) and watched.window() is self.window()):
            if kind == QtCore.QEvent.Type.ShortcutOverride:
                event.accept()
                return True
            if kind == QtCore.QEvent.Type.KeyPress:
                key = event.key()
                if key in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Tab, QtCore.Qt.Key.Key_Backtab):
                    self.dismiss()
                elif key in (QtCore.Qt.Key.Key_Down, QtCore.Qt.Key.Key_Up, QtCore.Qt.Key.Key_Home, QtCore.Qt.Key.Key_End):
                    eligible = [i for i, row in enumerate(self._items) if row.isEnabled()]
                    if eligible:
                        current = eligible.index(self._active) if self._active in eligible else -1
                        index = 0 if key == QtCore.Qt.Key.Key_Home else len(eligible)-1 if key == QtCore.Qt.Key.Key_End else (current + (1 if key == QtCore.Qt.Key.Key_Down else -1)) % len(eligible)
                        self._select(eligible[index])
                elif key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space):
                    if 0 <= self._active < len(self._items) and not event.isAutoRepeat():
                        self._activate(self._items[self._active].action)
                event.accept()
                return True
        return False

    def mousePressEvent(self, event):
        self.dismiss()
        event.accept()

    def hideEvent(self, event):
        if self._opened:
            self._reveal.stop()
            self._remove_watchers()
            self._opened = False
            self._closing = False
            self.aboutToHide.emit()
            self._anchor = None
        super().hideEvent(event)

    def _apply_theme(self):
        self.setFont(ui_font(theme.tokens.font_size, self.font()))
        self.setStyleSheet(
            "QScrollArea#actionMenuScroll, QWidget#actionMenuContent, QScrollArea#actionMenuScroll > QWidget { background: transparent; border: none; }"
            f"QFrame#actionMenuSeparator {{ background: transparent; border: none; border-bottom: 1px solid {theme.tokens.border}; margin: 3px 8px; }}"
        )
        self._surface.update()
        if self._opened:
            self._place()
