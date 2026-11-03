"""Reusable volume selector and a native Qt popup anchored to any widget."""

from ..icons import FluentIcon, fluent_icon
from ..qt import QtCore, QtGui, QtWidgets, Signal
from ..theme import theme
from .button import TransparentIconButton
from .media_controller import MediaController
from .slider import Slider


def _speaker_icon(controller):
    if controller.is_muted() or controller.volume() <= 0:
        return FluentIcon.SPEAKER_MUTE
    return FluentIcon.SPEAKER_1 if controller.volume() < 0.5 else FluentIcon.SPEAKER_2


class VolumeControl(QtWidgets.QWidget):
    """Speaker/mute, a 0..100 slider and its numeric value in one row."""

    def __init__(self, parent=None, *, controller=None):
        super().__init__(parent)
        self.controller = controller if controller is not None else MediaController(self)
        self._syncing = False
        self.mute_button = TransparentIconButton(fluent_icon(_speaker_icon(self.controller)))
        self.mute_button.setAccessibleName("静音或恢复声音")
        self.mute_button.setToolTip("静音 / 恢复声音")
        self.slider = Slider()
        self.slider.setRange(0, 100)
        self.slider.setMinimumWidth(120)
        self.slider.setAccessibleName("音量")
        self.value_label = QtWidgets.QLabel()
        self.value_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.value_label.setMinimumWidth(28)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 12, 6)
        layout.setSpacing(10)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._from_slider)
        self.mute_button.clicked.connect(
            lambda: self.controller.set_muted(not self.controller.is_muted())
        )
        self.controller.volumeChanged.connect(self._sync_volume)
        self.controller.mutedChanged.connect(self._sync_icon)
        theme.changed.connect(self._apply_theme)
        self._sync_volume(self.controller.volume())
        self._apply_theme()

    def sizeHint(self):
        return QtCore.QSize(280, 48)

    def _from_slider(self, value):
        if not self._syncing:
            self.controller.set_volume(value / 100)
            if value > 0:
                self.controller.set_muted(False)

    def _sync_volume(self, volume):
        self._syncing = True
        try:
            value = round(volume * 100)
            self.slider.setValue(value)
            self.value_label.setText(str(value))
            self.slider.setAccessibleDescription(f"当前音量 {value}")
        finally:
            self._syncing = False
        self._sync_icon()

    def _sync_icon(self, _muted=None):
        icon = _speaker_icon(self.controller)
        self.mute_button.setIcon(fluent_icon(icon))
        self.mute_button.setProperty("fluentIcon", icon.name)

    def _apply_theme(self):
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(theme.tokens.text))
        self.setPalette(palette)
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor(theme.tokens.border), 1))
        painter.setBrush(QtGui.QColor(theme.tokens.surface))
        painter.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)


class VolumeFlyout(QtWidgets.QWidget):
    """A rounded Qt.Popup; outside click/Escape close it without consuming a row.

    Unlike an in-window overlay, it also fits a compact player used as a small
    standalone window. ``control`` exposes the same embeddable VolumeControl.
    """

    aboutToShow = Signal()
    aboutToHide = Signal()

    def __init__(self, parent=None, *, controller=None):
        super().__init__(
            parent, QtCore.Qt.WindowType.Popup | QtCore.Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoMouseReplay)
        self.setAccessibleName("音量选择器")
        self._anchor = None
        self._filter_installed = False
        self.control = VolumeControl(controller=controller)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.addWidget(self.control)
        shadow = QtWidgets.QGraphicsDropShadowEffect(self.control)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 3)
        shadow.setColor(QtGui.QColor(0, 0, 0, 65))
        self.control.setGraphicsEffect(shadow)
        self._fade = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(120)
        self._fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    def popup(self, anchor):
        if not isinstance(anchor, QtWidgets.QWidget):
            raise TypeError("anchor must be a QWidget")
        if not anchor.isVisible() or not anchor.isEnabled():
            return False
        self._anchor = anchor
        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen,
            anchor.window().testAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen),
        )
        self.adjustSize()
        self._place()
        self.aboutToShow.emit()
        self._fade.stop()
        self.setWindowOpacity(0)
        self.show()
        self.raise_()
        reason = (
            QtCore.Qt.FocusReason.PopupFocusReason
            if getattr(anchor, "_keyboard_focus", False)
            else QtCore.Qt.FocusReason.MouseFocusReason
        )
        self.control.slider.setFocus(reason)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        return True

    def _place(self):
        area = self._anchor.screen().availableGeometry()
        point = self._anchor.mapToGlobal(QtCore.QPoint())
        x = max(
            area.left(),
            min(point.x() + self._anchor.width() - self.width(), area.right() - self.width() + 1),
        )
        y = point.y() - self.height() - 4
        if y < area.top():
            y = point.y() + self._anchor.height() + 4
        y = max(area.top(), min(y, area.bottom() - self.height() + 1))
        self.move(x, y)

    def dismiss(self):
        # A dismissed native popup must release input immediately.
        self.hide()

    def showEvent(self, event):
        if not self._filter_installed:
            QtWidgets.QApplication.instance().installEventFilter(self)
            self._filter_installed = True
        super().showEvent(event)

    def eventFilter(self, watched, event):
        if self.isVisible() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if (
                isinstance(watched, QtWidgets.QWidget)
                and watched is not self
                and not self.isAncestorOf(watched)
            ):
                anchor_click = watched is self._anchor
                self.dismiss()
                return anchor_click
        if self._anchor is not None and watched is self._anchor.window():
            if event.type() in (QtCore.QEvent.Type.Move, QtCore.QEvent.Type.Resize):
                self._place()
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event):
        if self._filter_installed:
            QtWidgets.QApplication.instance().removeEventFilter(self)
            self._filter_installed = False
        self._fade.stop()
        self.setWindowOpacity(1)
        self._anchor = None
        self.aboutToHide.emit()
        super().hideEvent(event)
