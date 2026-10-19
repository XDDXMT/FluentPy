"""Small animated button variants built from the library's existing controls."""

from __future__ import annotations

from ..icons import FluentIcon, fluent_icon
from ..qt import QtCore, QtGui, QtWidgets, Signal, Slot
from ..theme import theme
from .action_menu import ActionMenu
from .button import AccentButton, Button, TextButton, _mix_color, _readable_on


class ToggleButton(Button):
    """A Qt checkable button with an animated persistent selected surface."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._selection = 0.0
        self._selection_animation = self._make_state_animation("_selection")
        self.setCheckable(True)
        self.toggled.connect(self._selection_changed)

    def _selection_changed(self, checked):
        if self.isVisible():
            self._animate_state(self._selection_animation, self._selection, 1.0 if checked else 0.0, 180)
        else:
            self._selection_animation.stop()
            self._selection = float(checked)
            self.update()

    def _surface_color(self):
        return _mix_color(super()._surface_color(), QtGui.QColor(theme.tokens.accent), self._selection)

    def _surface_hover_color(self):
        return _mix_color(super()._surface_hover_color(), QtGui.QColor(theme.tokens.accent).lighter(104), self._selection)

    def _surface_pressed_color(self):
        return _mix_color(super()._surface_pressed_color(), QtGui.QColor(theme.tokens.accent).darker(110), self._selection)

    def _draw_content(self, painter, rect, color):
        if self.isEnabled():
            color = _mix_color(color, _readable_on(QtGui.QColor(theme.tokens.accent)), self._selection)
        super()._draw_content(painter, rect, color)

    def hideEvent(self, event):
        self._selection_animation.stop()
        self._selection = float(self.isChecked())
        super().hideEvent(event)


class PillToggleButton(ToggleButton):
    _pill = True


class ToggleIconButton(ToggleButton):
    def __init__(self, icon, parent=None):
        super().__init__("", parent)
        self.setIcon(fluent_icon(icon) if isinstance(icon, FluentIcon) else icon)
        self.setFixedSize(32, 32)


class AccentIconButton(AccentButton):
    def __init__(self, icon, parent=None):
        super().__init__("", parent)
        self.setIcon(fluent_icon(icon) if isinstance(icon, FluentIcon) else icon)
        self.setFixedSize(32, 32)


class TransparentIconButton(TextButton):
    def __init__(self, icon, parent=None):
        super().__init__("", parent)
        self.setIcon(fluent_icon(icon) if isinstance(icon, FluentIcon) else icon)
        self.setFixedSize(32, 32)


class _MenuButtonMixin:
    _menu_only = False

    def __init__(self, text="", parent=None, *, menu=None):
        super().__init__(text, parent)
        self._menu = None
        self._menu_anchor = None
        self._arrow_progress = 0.0
        self._arrow_animation = self._make_state_animation("_arrow_progress")
        self._chevron = fluent_icon(FluentIcon.CHEVRON_DOWN)
        self.clicked.connect(self.show_menu)
        self.set_menu(menu)

    def set_menu(self, menu):
        if menu is not None and not isinstance(menu, ActionMenu):
            raise TypeError("menu must be an ActionMenu or None")
        if self._menu is menu:
            return
        if self._menu is not None:
            if self._menu.anchor_widget() is (self._menu_anchor or self):
                self._menu.dismiss(immediate=True)
            self._menu.aboutToShow.disconnect(self._menu_opening)
            self._menu.aboutToHide.disconnect(self._menu_closing)
            self._menu.destroyed.disconnect(self._menu_destroyed)
        self._menu = menu
        if menu is not None:
            menu.aboutToShow.connect(self._menu_opening)
            menu.aboutToHide.connect(self._menu_closing)
            menu.destroyed.connect(self._menu_destroyed)
        self._menu_closing()

    def setMenu(self, menu):  # noqa: N802
        self.set_menu(menu)

    def menu(self):
        return self._menu

    def show_menu(self):
        if self.isEnabled() and self._menu is not None:
            anchor = self._menu_anchor or self
            if self._menu.isVisible() and self._menu.anchor_widget() is anchor:
                self._menu.dismiss()
            else:
                self._menu.popup(anchor)

    def showMenu(self):  # noqa: N802
        self.show_menu()

    def _menu_opening(self):
        end = float(self._menu is not None and self._menu.anchor_widget() is (self._menu_anchor or self))
        self._animate_state(self._arrow_animation, self._arrow_progress, end, 160)

    def _menu_closing(self):
        self._animate_state(self._arrow_animation, self._arrow_progress, 0.0, 160)

    def _menu_destroyed(self):
        self._menu = None
        self._arrow_animation.stop()
        self._arrow_progress = 0.0
        self.update()

    def sizeHint(self):
        if self._menu_only:
            return QtCore.QSize(32, 32)
        size = super().sizeHint()
        size.setWidth(size.width()+24)
        return size

    def _draw_content(self, painter, rect, color):
        if not self._menu_only:
            super()._draw_content(painter, rect.adjusted(0, 0, -24, 0), color)
        center = QtCore.QPointF(self.rect().center()) if self._menu_only else QtCore.QPointF(rect.right()-15, rect.center().y())
        painter.save()
        painter.translate(center)
        painter.rotate(180 * self._arrow_progress)
        self._draw_tinted_icon(painter, QtCore.QRect(-6, -6, 12, 12), color, self._chevron)
        painter.restore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Down:
            self.show_menu()
            event.accept()
        else:
            super().keyPressEvent(event)

    def hideEvent(self, event):
        if self._menu is not None and self._menu.anchor_widget() is (self._menu_anchor or self):
            self._menu.dismiss(immediate=True)
        self._arrow_animation.stop()
        self._arrow_progress = 0.0
        super().hideEvent(event)


class DropDownButton(_MenuButtonMixin, Button):
    pass


class AccentDropDownButton(_MenuButtonMixin, AccentButton):
    pass


class _SplitPartMixin:
    _side = "left"

    def _paint_rect(self):
        rect = super()._paint_rect()
        return rect.adjusted(0, 0, 7, 0) if self._side == "left" else rect.adjusted(-7, 0, 0, 0)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._side == "right":
            painter = QtGui.QPainter(self)
            color = QtGui.QColor("#ffffff" if self._kind == "accent" and theme.mode.value == "light" else theme.tokens.text)
            color.setAlpha(60 if self._kind == "accent" else 28)
            if not self.isEnabled():
                color.setAlpha(18)
            painter.setPen(QtGui.QPen(color, 1))
            painter.drawLine(QtCore.QLineF(0.5, 8, 0.5, self.height()-8))

    def keyPressEvent(self, event):
        if self._side == "left" and event.key() == QtCore.Qt.Key.Key_Down:
            self.parentWidget().show_menu()
            event.accept()
        else:
            super().keyPressEvent(event)


class _SplitContentMixin:
    """Optional secondary text shares the main button's native hit target."""

    def __init__(self, text="", parent=None, *, description=""):
        super().__init__(text, parent)
        self._description = ""
        self.set_description(description)

    def description(self):
        return self._description

    def set_description(self, text):
        self._description = str(text)
        self.setAccessibleDescription(self._description)
        self._update_content_size()

    def _description_font(self):
        font = QtGui.QFont(self.font())
        font.setPixelSize(max(10, self.font().pixelSize()-2))
        return font

    def _title_font(self):
        font = QtGui.QFont(self.font())
        font.setWeight(QtGui.QFont.Weight.DemiBold)
        return font

    def _content_height(self):
        if not self._description:
            return 32
        return max(52, QtGui.QFontMetrics(self._title_font()).height()
                   + QtGui.QFontMetrics(self._description_font()).height()+18)

    def _update_content_size(self):
        self.setMinimumHeight(self._content_height())
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        if not getattr(self, "_description", ""):
            return super().sizeHint()
        title = QtGui.QFontMetrics(self._title_font()).horizontalAdvance(self.text())
        description = QtGui.QFontMetrics(self._description_font()).horizontalAdvance(self._description)
        icon = self.iconSize().width()+10 if not self.icon().isNull() else 0
        return QtCore.QSize(max(96, max(title, description)+icon+32), self._content_height())

    def minimumSizeHint(self):
        if not getattr(self, "_description", ""):
            return super().minimumSizeHint()
        icon = self.iconSize().width()+10 if not self.icon().isNull() else 0
        return QtCore.QSize(80+icon, self._content_height())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.Type.FontChange and hasattr(self, "_description"):
            self._update_content_size()

    def _draw_content(self, painter, rect, color):
        # The surface extends across the seam to remove the inner corners;
        # the text remains centered inside the actual main hit target.
        rect = rect.adjusted(0, 0, -7, 0)
        if not self._description:
            super()._draw_content(painter, rect, color)
            return
        title_font, description_font = self._title_font(), self._description_font()
        title_metrics, description_metrics = QtGui.QFontMetrics(title_font), QtGui.QFontMetrics(description_font)
        content = rect.adjusted(16, 0, -16, 0)
        icon_width = self.iconSize().width()+10 if not self.icon().isNull() else 0
        width = max(0, min(content.width()-icon_width,
                           max(title_metrics.horizontalAdvance(self.text()),
                               description_metrics.horizontalAdvance(self._description))))
        left = content.center().x()-(width+icon_width)/2
        if icon_width:
            icon_rect = QtCore.QRect(round(left), round(rect.center().y()-self.iconSize().height()/2),
                                     self.iconSize().width(), self.iconSize().height())
            self._draw_tinted_icon(painter, icon_rect, color)
            left += icon_width
        top = rect.center().y()-(title_metrics.height()+description_metrics.height()+2)/2
        alignment = QtCore.Qt.AlignmentFlag.AlignCenter
        painter.setFont(title_font)
        painter.setPen(color)
        painter.drawText(QtCore.QRectF(left, top, width, title_metrics.height()), alignment,
                         title_metrics.elidedText(self.text(), QtCore.Qt.TextElideMode.ElideRight, round(width)))
        secondary = QtGui.QColor(color if self._kind == "accent" else
                                theme.tokens.text_muted if self.isEnabled() else theme.tokens.disabled)
        secondary.setAlphaF(color.alphaF() * (0.82 if self._kind == "accent" else 1.0))
        painter.setFont(description_font)
        painter.setPen(secondary)
        painter.drawText(QtCore.QRectF(left, top+title_metrics.height()+2, width, description_metrics.height()),
                         alignment, description_metrics.elidedText(self._description,
                         QtCore.Qt.TextElideMode.ElideRight, round(width)))


class _SplitMain(_SplitContentMixin, _SplitPartMixin, Button):
    pass


class _AccentSplitMain(_SplitContentMixin, _SplitPartMixin, AccentButton):
    pass


class _SplitArrow(_SplitPartMixin, _MenuButtonMixin, Button):
    _side = "right"
    _menu_only = True


class _AccentSplitArrow(_SplitPartMixin, _MenuButtonMixin, AccentButton):
    _side = "right"
    _menu_only = True


class SplitButton(QtWidgets.QWidget):
    """Primary action on the left, independent menu affordance on the right."""

    clicked = Signal()
    _accent = False

    def __init__(self, text="", parent=None, *, menu=None, description=""):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.main_button = (_AccentSplitMain if self._accent else _SplitMain)(text, self, description=description)
        self.menu_button = (_AccentSplitArrow if self._accent else _SplitArrow)(parent=self, menu=menu)
        self.main_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.menu_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)
        self.menu_button._menu_anchor = self
        self.menu_button.setAccessibleName("更多操作")
        self.main_button.clicked.connect(self._clicked)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.main_button, 1)
        row.addWidget(self.menu_button)
        self.setFocusProxy(self.main_button)
        self.setAccessibleName(text)
        self.setAccessibleDescription(str(description))
        self._sync_parts()
        theme.subscribe(self, self._sync_parts)

    @Slot()
    def _clicked(self):
        self.clicked.emit()

    def setText(self, text):  # noqa: N802
        self.main_button.setText(text)
        self.setAccessibleName(text)
        self.updateGeometry()

    def text(self):
        return self.main_button.text()

    def setIcon(self, icon):  # noqa: N802
        self.main_button.setIcon(icon)
        self.updateGeometry()

    def icon(self):
        return self.main_button.icon()

    def setIconSize(self, size):  # noqa: N802
        self.main_button.setIconSize(size)
        self.updateGeometry()

    def iconSize(self):  # noqa: N802
        return self.main_button.iconSize()

    def description(self):
        """Return the optional secondary line, e.g. the selected version."""
        return self.main_button.description()

    def set_description(self, text):
        """Change the secondary line without activating either button region."""
        self.main_button.set_description(text)
        self.setAccessibleDescription(self.main_button.description())
        self._sync_parts()

    def setDescription(self, text):  # noqa: N802
        self.set_description(text)

    def _sync_parts(self):
        self.menu_button.setFixedWidth(40 if self.description() else 32)
        self.updateGeometry()
        self.update()

    def set_menu(self, menu):
        self.menu_button.set_menu(menu)

    def setMenu(self, menu):  # noqa: N802
        self.set_menu(menu)

    def menu(self):
        return self.menu_button.menu()

    def show_menu(self):
        self.menu_button.show_menu()

    def sizeHint(self):
        return self.main_button.sizeHint()+QtCore.QSize(self.menu_button.width(), 0)

    def minimumSizeHint(self):
        return self.main_button.minimumSizeHint()+QtCore.QSize(self.menu_button.width(), 0)


class AccentSplitButton(SplitButton):
    _accent = True


class LoadingButton(AccentButton):
    """Keep task feedback visible while native Qt disabling blocks activation."""

    loadingChanged = Signal(bool)

    def __init__(self, text="", parent=None):
        self._loading = False
        self._desired_enabled = True
        self._idle_text = str(text)
        self._spin = 0.0
        super().__init__(text, parent)
        self._spinner = QtCore.QVariantAnimation(self)
        self._spinner.setStartValue(0.0)
        self._spinner.setEndValue(1.0)
        self._spinner.setDuration(1100)
        self._spinner.setLoopCount(-1)
        self._spinner.valueChanged.connect(self._spin_changed)
        self._loading_ancestors = []
        self._watch_loading_ancestors()

    def _watch_loading_ancestors(self):
        for ancestor in self._loading_ancestors:
            try:
                ancestor.removeEventFilter(self)
            except RuntimeError:
                pass
        self._loading_ancestors = []
        ancestor = self.parentWidget()
        while ancestor is not None:
            ancestor.installEventFilter(self)
            self._loading_ancestors.append(ancestor)
            ancestor = ancestor.parentWidget()

    def _sync_spinner(self):
        if self._loading and self.isVisible() and self._visual_enabled():
            if self._spinner.state() != QtCore.QAbstractAnimation.State.Running:
                self._spinner.start()
        else:
            self._spinner.stop()

    def eventFilter(self, watched, event):
        # Qt does not send EnabledChange to an already disabled child. Busy
        # buttons are deliberately disabled, so observe their ancestors too.
        if event.type() in (QtCore.QEvent.Type.EnabledChange, QtCore.QEvent.Type.Show,
                            QtCore.QEvent.Type.Hide):
            self._sync_spinner()
        return super().eventFilter(watched, event)

    def event(self, event):
        result = super().event(event)
        if event.type() == QtCore.QEvent.Type.ParentChange and hasattr(self, "_loading_ancestors"):
            self._watch_loading_ancestors()
            self._sync_spinner()
        return result

    def is_loading(self):
        return self._loading

    def set_loading(self, loading, *, text="处理中…"):
        loading = bool(loading)
        if loading == self._loading:
            if loading:
                QtWidgets.QPushButton.setText(self, text)
            return
        if loading:
            self._idle_text = self.text()
        self._loading = loading
        QtWidgets.QPushButton.setText(self, text if loading else self._idle_text)
        QtWidgets.QWidget.setEnabled(self, self._desired_enabled and not loading)
        if loading and self.isVisible() and self._visual_enabled():
            self._spinner.start()
        else:
            self._spinner.stop()
        self.updateGeometry()
        self.update()
        self.loadingChanged.emit(loading)

    def setEnabled(self, enabled):  # noqa: N802
        self._desired_enabled = bool(enabled)
        super().setEnabled(self._desired_enabled and not self._loading)
        if hasattr(self, "_spinner") and self._loading:
            if self.isVisible() and self._visual_enabled():
                if self._spinner.state() != QtCore.QAbstractAnimation.State.Running:
                    self._spinner.start()
            else:
                self._spinner.stop()

    def setDisabled(self, disabled):  # noqa: N802
        self.setEnabled(not disabled)

    def setText(self, text):  # noqa: N802
        if self._loading:
            self._idle_text = str(text)
        else:
            super().setText(text)

    def _visual_enabled(self):
        parent = self.parentWidget()
        return self.isEnabled() or (self._loading and self._desired_enabled and (parent is None or parent.isEnabled()))

    def _spin_changed(self, value):
        self._spin = float(value)
        self.update()

    def sizeHint(self):
        size = super().sizeHint()
        if self._loading:
            size.setWidth(size.width()+22)
        return size

    def _draw_content(self, painter, rect, color):
        if not self._loading:
            super()._draw_content(painter, rect, color)
            return
        width = self.fontMetrics().horizontalAdvance(self.text())
        x = rect.center().x()-(width+24)/2
        painter.setPen(QtGui.QPen(color, 1.8, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawArc(QtCore.QRectF(x, rect.center().y()-7, 14, 14), round((90-self._spin*360)*16), -105*16)
        painter.setPen(color)
        painter.drawText(QtCore.QRectF(x+24, rect.top(), width, rect.height()), QtCore.Qt.AlignmentFlag.AlignVCenter, self.text())

    def showEvent(self, event):
        super().showEvent(event)
        if self._loading and self._visual_enabled():
            self._spinner.start()

    def hideEvent(self, event):
        self._spinner.stop()
        super().hideEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.Type.EnabledChange and hasattr(self, "_spinner") and self._loading:
            if self.isVisible() and self._visual_enabled():
                if self._spinner.state() != QtCore.QAbstractAnimation.State.Running:
                    self._spinner.start()
            else:
                self._spinner.stop()
