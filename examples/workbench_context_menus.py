"""Present existing Qt editing actions through the workbench's ActionMenu.

The application filter is scoped to one root and its Qt descendants. It finds
editors at request time, including editors created inside spin boxes, editable
combos and dialogs. Editing remains in Qt and the component's existing APIs.
"""

from __future__ import annotations

import weakref

from fluentpy import ActionMenu
from fluentpy.qt import QtCore, QtGui, QtWidgets, Slot

_EDIT_LABELS = {
    "edit-undo": "撤销",
    "edit-redo": "重做",
    "edit-cut": "剪切",
    "edit-copy": "复制",
    "edit-paste": "粘贴",
    "edit-delete": "删除",
    "select-all": "全选",
}
_EDITORS = (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)
_EDIT_KEYS = {
    "edit-undo": QtGui.QKeySequence.StandardKey.Undo,
    "edit-redo": QtGui.QKeySequence.StandardKey.Redo,
    "edit-cut": QtGui.QKeySequence.StandardKey.Cut,
    "edit-copy": QtGui.QKeySequence.StandardKey.Copy,
    "edit-paste": QtGui.QKeySequence.StandardKey.Paste,
    "edit-delete": QtGui.QKeySequence.StandardKey.Delete,
    "select-all": QtGui.QKeySequence.StandardKey.SelectAll,
}


class _LifetimeLink(QtCore.QObject):
    """A Qt-owned receiver must not inspect a dying QWidget sender."""

    def __init__(self, owner, watched, attribute, generation):
        super().__init__(owner)
        self._owner_ref = weakref.ref(owner)
        self.attribute = attribute
        self.generation = generation
        owner.destroyed.connect(self._owner_destroyed)
        watched.destroyed.connect(self._watched_destroyed)

    @Slot()
    def _owner_destroyed(self):
        self._owner_ref = lambda: None

    @Slot()
    def _watched_destroyed(self):
        owner = self._owner_ref()
        if (
            owner is not None
            and getattr(owner, "_" + self.attribute + "_generation") == self.generation
        ):
            setattr(owner, self.attribute, None)
            if self.attribute == "menu":
                owner._source = None
                QtCore.QTimer.singleShot(0, owner._release_if_idle)
        self.deleteLater()


class _Registration(QtCore.QObject):
    def __init__(self, owner, widget, builder):
        super().__init__(owner)
        self._owner_ref = weakref.ref(owner)
        self.target = widget
        self.builder = builder
        self.key = id(widget)
        owner.destroyed.connect(self._owner_destroyed)
        widget.destroyed.connect(self._target_destroyed)

    @Slot()
    def _owner_destroyed(self):
        self._owner_ref = lambda: None

    @Slot()
    def _target_destroyed(self):
        owner = self._owner_ref()
        if owner is not None and owner._registrations.get(self.key) is self:
            owner._registrations.pop(self.key, None)
        self.target = None
        self.builder = None
        self.deleteLater()


class WorkbenchContextMenus(QtCore.QObject):
    """One reusable advanced context menu for a workbench root.

    ``register(widget, builder)`` adds a business menu for that widget and its
    descendants; ``builder(menu, point)`` receives registered-widget coordinates.
    Native text editing takes priority over a registered ancestor. Menus that
    are already ActionMenu/QMenu are left to their own interaction lifecycle.
    Call ``close()`` to uninstall this manager; closing it is idempotent.
    """

    def __init__(self, root):
        if not isinstance(root, QtWidgets.QWidget):
            raise TypeError("root must be a QWidget")
        app = QtWidgets.QApplication.instance()
        if app is None:
            raise RuntimeError("a QApplication is required")
        super().__init__(root)
        self._root = root
        self._closed = False
        self._building = False
        self._registrations = {}
        self._source = None
        self._menu_generation = 0
        self._native_menu_generation = 0
        self.menu = None
        self.native_menu = None
        self._ensure_menu()
        root.destroyed.connect(self._root_destroyed)
        app.installEventFilter(self)

    def register(self, widget, builder):
        if self._closed:
            raise RuntimeError("context menu manager is closed")
        if not isinstance(widget, QtWidgets.QWidget) or not self._in_scope(widget):
            raise ValueError("registered widget must belong to this workbench")
        if not callable(builder):
            raise TypeError("builder must be callable")
        self.unregister(widget)
        entry = _Registration(self, widget, builder)
        self._registrations[id(widget)] = entry

    def unregister(self, widget):
        entry = self._registrations.pop(id(widget), None)
        if entry is not None:
            if entry.target is not None:
                try:
                    entry.target.destroyed.disconnect(entry._target_destroyed)
                except (RuntimeError, TypeError):
                    pass
            entry.target = None
            entry.builder = None
            entry.deleteLater()

    @property
    def current_source(self):
        return self._source

    def _ensure_menu(self):
        if self.menu is None and not self._closed:
            self._menu_generation += 1
            self.menu = ActionMenu(self._root)
            self.menu.triggered.connect(self._action_triggered)
            _LifetimeLink(self, self.menu, "menu", self._menu_generation)
        return self.menu

    @Slot(QtGui.QAction)
    def _action_triggered(self, _action):
        # Also close actions invoked by their native keyboard shortcuts.
        if self.menu is not None:
            self.menu.dismiss()

    def _in_scope(self, widget):
        if self._closed or self._root is None or not isinstance(widget, QtWidgets.QWidget):
            return False
        try:
            while widget is not None:
                if widget is self._root:
                    return True
                widget = widget.parentWidget()
            return False
        except RuntimeError:
            return False

    def _ancestors(self, widget):
        while widget is not None:
            if isinstance(widget, (ActionMenu, QtWidgets.QMenu)):
                return
            yield widget
            if widget is self._root:
                return
            widget = widget.parentWidget()

    def _target(self, widget):
        ancestors = tuple(self._ancestors(widget))
        # A popup's editor is intentionally owned by that popup's existing
        # interaction model, including custom QWidgetAction controls.
        if not ancestors or ancestors[-1] is not self._root:
            return None
        for ancestor in ancestors:
            if isinstance(ancestor, _EDITORS):
                return ancestor, None
            if isinstance(ancestor, QtWidgets.QScrollBar):
                if ancestor.contextMenuPolicy() in (
                    QtCore.Qt.ContextMenuPolicy.NoContextMenu,
                    QtCore.Qt.ContextMenuPolicy.PreventContextMenu,
                ):
                    return None
                return ancestor, self._scroll_actions
            if isinstance(ancestor, QtWidgets.QAbstractSpinBox):
                return ancestor, self._spin_actions
        for ancestor in ancestors:
            entry = self._registrations.get(id(ancestor))
            if entry is not None:
                return ancestor, entry.builder
        for ancestor in ancestors:
            if (
                ancestor.contextMenuPolicy() == QtCore.Qt.ContextMenuPolicy.ActionsContextMenu
                and ancestor.actions()
            ):
                return ancestor, self._existing_actions
            if isinstance(ancestor, QtWidgets.QAbstractItemView):
                if callable(getattr(ancestor, "createStandardContextMenu", None)):
                    return ancestor, None
                return ancestor, self._view_actions
        return None

    def _existing_actions(self, menu, _point):
        menu.addActions(self._source.actions())

    def _spin_actions(self, menu, point):
        spin = self._source
        field = spin.lineEdit()
        self._add_standard_actions(menu, field, field.mapFrom(spin, point))
        menu.add_separator()
        enabled = spin.stepEnabled()
        for text, name, flag, callback in (
            (
                "增加",
                "spin-step-up",
                QtWidgets.QAbstractSpinBox.StepEnabledFlag.StepUpEnabled,
                spin.stepUp,
            ),
            (
                "减少",
                "spin-step-down",
                QtWidgets.QAbstractSpinBox.StepEnabledFlag.StepDownEnabled,
                spin.stepDown,
            ),
        ):
            action = menu.add_action(
                text, callback=callback, enabled=not spin.isReadOnly() and bool(enabled & flag)
            )
            action.setObjectName(name)

    def _scroll_actions(self, menu, point):
        scroll = self._source
        vertical = scroll.orientation() == QtCore.Qt.Orientation.Vertical
        here = menu.add_action("滚动到此处", callback=lambda: self._scroll_here(scroll, point))
        here.setObjectName("scroll-here")
        menu.add_separator()
        names = (
            ("顶部", "底部", "向上翻页", "向下翻页", "向上滚动", "向下滚动")
            if vertical
            else ("最左端", "最右端", "向左翻页", "向右翻页", "向左滚动", "向右滚动")
        )
        actions = QtWidgets.QAbstractSlider.SliderAction
        for text, name, slider_action in zip(
            names,
            (
                "scroll-minimum",
                "scroll-maximum",
                "scroll-page-sub",
                "scroll-page-add",
                "scroll-step-sub",
                "scroll-step-add",
            ),
            (
                actions.SliderToMinimum,
                actions.SliderToMaximum,
                actions.SliderPageStepSub,
                actions.SliderPageStepAdd,
                actions.SliderSingleStepSub,
                actions.SliderSingleStepAdd,
            ),
        ):
            action = menu.add_action(
                text,
                callback=lambda checked=False, value=slider_action: scroll.triggerAction(value),
            )
            action.setObjectName(name)

    @staticmethod
    def _scroll_here(scroll, point):
        option = QtWidgets.QStyleOptionSlider()
        scroll.initStyleOption(option)
        style = scroll.style()
        complex_control = QtWidgets.QStyle.ComplexControl.CC_ScrollBar
        groove = style.subControlRect(
            complex_control, option, QtWidgets.QStyle.SubControl.SC_ScrollBarGroove, scroll
        )
        handle = style.subControlRect(
            complex_control, option, QtWidgets.QStyle.SubControl.SC_ScrollBarSlider, scroll
        )
        vertical = scroll.orientation() == QtCore.Qt.Orientation.Vertical
        length = handle.height() if vertical else handle.width()
        start = groove.top() if vertical else groove.left()
        span = (groove.height() if vertical else groove.width()) - length
        position = (point.y() if vertical else point.x()) - start - length // 2
        value = QtWidgets.QStyle.sliderValueFromPosition(
            scroll.minimum(),
            scroll.maximum(),
            max(0, min(position, max(0, span))),
            max(0, span),
            option.upsideDown,
        )
        scroll.setSliderPosition(value)
        scroll.triggerAction(QtWidgets.QAbstractSlider.SliderAction.SliderMove)

    def _view_actions(self, menu, _point):
        view = self._source
        selection = view.selectionModel()
        action = menu.add_action(
            "复制选中内容",
            enabled=bool(selection and selection.selectedIndexes()),
            callback=lambda: self._copy_view_selection(view),
        )
        action.setObjectName("view-copy")

    @staticmethod
    def _copy_view_selection(view):
        selection = view.selectionModel()
        if selection is None:
            return
        indexes = selection.selectedIndexes()
        indexes.sort(
            key=lambda index: (view.visualRect(index).top(), view.visualRect(index).left())
        )
        rows = {}
        for index in indexes:
            key = (index.parent(), index.row())
            value = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            rows.setdefault(key, []).append("" if value is None else str(value))
        if rows:
            QtWidgets.QApplication.clipboard().setText(
                "\n".join("\t".join(values) for values in rows.values())
            )

    @staticmethod
    def _caret_point(widget):
        if isinstance(widget, _EDITORS):
            point = widget.cursorRect().bottomLeft()
            if isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
                point = widget.viewport().mapTo(widget, point)
            return QtCore.QPoint(
                max(0, min(point.x(), widget.width() - 1)),
                max(0, min(point.y(), widget.height() - 1)),
            )
        return widget.rect().center()

    def _clear_current(self):
        if self.menu is not None:
            self.menu.dismiss(immediate=True)
            self.menu.clear()
        native = self.native_menu
        self.native_menu = None
        if native is not None:
            native.deleteLater()
        self._source = None

    @Slot()
    def _release_if_idle(self):
        if self.menu is None or not self.menu._opened:
            self._clear_current()

    def _standard_menu(self, source, point):
        if isinstance(source, QtWidgets.QLineEdit):
            return source.createStandardContextMenu()
        if isinstance(source, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            viewport_point = source.viewport().mapFrom(source, point)
            document_point = viewport_point + QtCore.QPoint(
                source.horizontalScrollBar().value(), source.verticalScrollBar().value()
            )
            return source.createStandardContextMenu(document_point)
        # Custom item views can expose their ordinary native menu factory.
        return source.createStandardContextMenu(point)

    @staticmethod
    def _prepare_native_action(action, source):
        name = action.objectName()
        text, separator, shortcut = action.text().partition("\t")
        if name in _EDIT_LABELS:
            action.setText(_EDIT_LABELS[name])
            if separator and shortcut and action.shortcut().isEmpty():
                action.setShortcut(
                    QtGui.QKeySequence.fromString(
                        shortcut, QtGui.QKeySequence.SequenceFormat.NativeText
                    )
                )
            action.setShortcutContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        # Qt's stock Paste QAction calls the C++ QLineEdit slot. Respect a
        # component's existing Python paste override (notably whole PIN paste).
        if (
            name == "edit-paste"
            and isinstance(source, QtWidgets.QLineEdit)
            and getattr(type(source), "paste") is not QtWidgets.QLineEdit.paste
        ):
            action.triggered.disconnect()
            action.triggered.connect(source.paste)

    def _add_standard_actions(self, menu, source, point):
        native = self._standard_menu(source, point)
        if not isinstance(native, QtWidgets.QMenu):
            raise TypeError("createStandardContextMenu must return a QMenu")
        native.setParent(self._root, native.windowFlags())
        self.native_menu = native
        self._native_menu_generation += 1
        _LifetimeLink(self, native, "native_menu", self._native_menu_generation)
        for action in native.actions():
            self._prepare_native_action(action, source)
            menu.addAction(action)

    def _open(self, watched, global_point=None, *, keyboard=False):
        target = self._target(watched)
        if target is None or self._building:
            return False
        source, builder = target
        if not source.isVisible() or not source.isEnabled():
            return False
        point = self._caret_point(source) if keyboard else source.mapFromGlobal(global_point)
        self._building = True
        try:
            self._clear_current()
            menu = self._ensure_menu()
            self._source = source
            if builder is None:
                self._add_standard_actions(menu, source, point)
            else:
                builder(menu, point)
            if not menu.actions():
                self._clear_current()
                return False
            source.setFocus(QtCore.Qt.FocusReason.PopupFocusReason)
            if not menu.popup_at(source, point):
                self._clear_current()
                return False
            # ActionMenu handles navigation keys at application level. Place
            # the adapter first so stock Qt editing shortcuts remain available
            # while the advanced editing menu has focus.
            app = QtWidgets.QApplication.instance()
            app.removeEventFilter(self)
            app.installEventFilter(self)
            return True
        except Exception:
            self._clear_current()
            raise
        finally:
            self._building = False

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.menu and kind == QtCore.QEvent.Type.Hide:
            # Keep native QActions alive throughout the exit animation. A
            # zero-delay cleanup also lets the triggering Qt slot finish first.
            QtCore.QTimer.singleShot(0, self._release_if_idle)
        if not self._in_scope(watched):
            return False
        menu = self.menu
        if (
            menu is not None
            and menu._opened
            and not menu._closing
            and (watched is menu or menu.isAncestorOf(watched))
            and kind in (QtCore.QEvent.Type.ShortcutOverride, QtCore.QEvent.Type.KeyPress)
        ):
            for action in menu.actions():
                standard = _EDIT_KEYS.get(action.objectName())
                if standard is not None and event.matches(standard):
                    if kind == QtCore.QEvent.Type.KeyPress and action.isEnabled():
                        menu._activate(action)
                    event.accept()
                    return True
        if kind == QtCore.QEvent.Type.ContextMenu:
            keyboard = event.reason() == QtGui.QContextMenuEvent.Reason.Keyboard
            if self._open(watched, event.globalPos(), keyboard=keyboard):
                event.accept()
                return True
        elif kind == QtCore.QEvent.Type.KeyPress and (
            event.key() == QtCore.Qt.Key.Key_Menu
            or (
                event.key() == QtCore.Qt.Key.Key_F10
                and event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
            )
        ):
            if self._open(watched, keyboard=True):
                event.accept()
                return True
        return False

    def close(self):
        if self._closed:
            return
        self._closed = True
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._clear_current()
        if self.menu is not None:
            self.menu.deleteLater()
            self.menu = None
        for entry in tuple(self._registrations.values()):
            if entry.target is not None:
                self.unregister(entry.target)

    @Slot()
    def _root_destroyed(self):
        # QObject can be partway through tearing down its child widgets here.
        # Clear Python state, but leave native child destruction to Qt.
        self._closed = True
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._root = None
        self._source = None
        self.menu = None
        self.native_menu = None
        self._registrations.clear()
