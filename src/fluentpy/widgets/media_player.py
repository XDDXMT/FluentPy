"""Fluent control layouts around a real Qt Multimedia player."""

from __future__ import annotations

from ..icons import FluentIcon, fluent_icon
from ..qt import QtCore, QtGui, QtWidgets
from ..theme import theme
from .button import Button, TransparentIconButton
from .media_controller import MediaController, multimedia_modules
from .slider import Slider
from .volume_control import VolumeFlyout, _speaker_icon


def _time_text(milliseconds):
    seconds = max(0, milliseconds // 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


class _MediaButton(TransparentIconButton):
    """Transport control using the bundled original Microsoft SVG assets."""

    ICONS = {
        "play": FluentIcon.PLAY,
        "pause": FluentIcon.PAUSE,
        "back": FluentIcon.SKIP_BACK_10,
        "forward": FluentIcon.SKIP_FORWARD_30,
    }

    def __init__(self, kind, text, parent=None):
        super().__init__(fluent_icon(self.ICONS[kind]), parent)
        self._symbol = kind
        self.setFixedSize(38, 38)
        self.setIconSize(QtCore.QSize(20, 20))
        self.setToolTip(text)
        self.setAccessibleName(text)

    @property
    def kind(self):
        return self._symbol

    @kind.setter
    def kind(self, kind):
        self._symbol = kind
        self.setIcon(fluent_icon(self.ICONS[kind]))

    def set_seek_step(self, seconds):
        backwards = self.kind == "back"
        prefix = "SKIP_BACK" if backwards else "SKIP_FORWARD"
        fallback = (
            FluentIcon.ARROW_ROTATE_COUNTERCLOCKWISE
            if backwards
            else FluentIcon.ARROW_ROTATE_CLOCKWISE
        )
        icon = getattr(FluentIcon, f"{prefix}_{seconds:g}", fallback)
        self.setIcon(fluent_icon(icon))
        self.setProperty("fluentIcon", icon.name)


class AudioPlayer(QtWidgets.QWidget):
    """Timeline, time labels and extensible leading/transport/trailing layouts.

    Pass the same MediaController to multiple surfaces when synchronized views
    are desired. A shared controller remains owned by its original parent.
    """

    def __init__(self, source=None, parent=None, *, controller=None, compact=False):
        super().__init__(parent)
        self.controller = controller if controller is not None else MediaController(self)
        self._compact = bool(compact)
        self._back_ms, self._forward_ms = 10000, 30000
        self._duration = self.controller.duration()
        self._updating_position = False
        self._pause_on_hide = False
        self.setMinimumWidth(220)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.timeline = Slider()
        self.timeline.setRange(0, 10000)
        self.timeline.setAccessibleName("播放位置")
        self.timeline.setEnabled(self.controller.is_seekable())
        self.play_button = _MediaButton("play", "播放")
        self.back_button = _MediaButton("back", "后退 10 秒")
        self.forward_button = _MediaButton("forward", "前进 30 秒")
        self.volume_button = TransparentIconButton(fluent_icon(_speaker_icon(self.controller)))
        self.volume_button.setFixedSize(38, 38)
        self.volume_button.setIconSize(QtCore.QSize(20, 20))
        self.volume_button.setToolTip("调整音量")
        self.volume_button.setAccessibleName("打开音量选择器")
        self.volume_flyout = VolumeFlyout(self, controller=self.controller)
        self.volume_slider = self.volume_flyout.control.slider
        self.position_label = QtWidgets.QLabel(_time_text(self.controller.position()), self)
        self.duration_label = QtWidgets.QLabel(_time_text(self._duration), self)
        self.leading_layout = QtWidgets.QHBoxLayout()
        self.transport_layout = QtWidgets.QHBoxLayout()
        self.trailing_layout = QtWidgets.QHBoxLayout()
        for row in (self.leading_layout, self.transport_layout, self.trailing_layout):
            row.setSpacing(4)
            row.setContentsMargins(0, 0, 0, 0)
        self.leading_layout.addWidget(self.volume_button)
        self.transport_layout.addWidget(self.back_button)
        self.transport_layout.addWidget(self.play_button)
        self.transport_layout.addWidget(self.forward_button)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(0)
        if compact:
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(12)
            row.addLayout(self.transport_layout)
            row.addWidget(self.timeline, 1)
            row.addLayout(self.leading_layout)
            row.addLayout(self.trailing_layout)
            layout.addLayout(row)
            self.back_button.hide()
            self.forward_button.hide()
            self.position_label.hide()
            self.duration_label.hide()
        else:
            layout.addWidget(self.timeline)
            times = QtWidgets.QHBoxLayout()
            times.addWidget(self.position_label)
            times.addStretch(1)
            times.addWidget(self.duration_label)
            layout.addLayout(times)
            controls = QtWidgets.QGridLayout()
            controls.setColumnStretch(0, 1)
            controls.setColumnStretch(2, 1)
            controls.addLayout(self.leading_layout, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
            controls.addLayout(self.transport_layout, 0, 1)
            controls.addLayout(self.trailing_layout, 0, 2, QtCore.Qt.AlignmentFlag.AlignRight)
            layout.addLayout(controls)
        self.play_button.clicked.connect(self.controller.toggle_playback)
        self.back_button.clicked.connect(lambda: self.controller.seek_by(-self._back_ms))
        self.forward_button.clicked.connect(lambda: self.controller.seek_by(self._forward_ms))
        self.volume_button.clicked.connect(self.show_volume_flyout)
        self.timeline.sliderReleased.connect(self._seek_from_slider)
        self.timeline.valueChanged.connect(self._seek_if_not_dragging)
        self.controller.positionChanged.connect(self._position_changed)
        self.controller.durationChanged.connect(self._duration_changed)
        self.controller.playingChanged.connect(self._playing_changed)
        self.controller.seekableChanged.connect(self.timeline.setEnabled)
        self.controller.volumeChanged.connect(self._sync_volume_icon)
        self.controller.mutedChanged.connect(self._sync_volume_icon)
        theme.changed.connect(self._theme_changed)
        self._theme_changed()
        self._playing_changed(self.controller.is_playing())
        self._sync_volume_icon()
        self._position_changed(self.controller.position())
        if source is not None:
            self.set_source(source)

    def set_source(self, source):
        self.controller.set_source(source)

    def set_seek_steps(self, backward=10, forward=30):
        if not 1 <= backward <= 3600 or not 1 <= forward <= 3600:
            raise ValueError("seek steps must be between 1 and 3600 seconds")
        self._back_ms, self._forward_ms = round(backward * 1000), round(forward * 1000)
        for button, value, direction in (
            (self.back_button, backward, "后退"),
            (self.forward_button, forward, "前进"),
        ):
            button.set_seek_step(value)
            button.setToolTip(f"{direction} {value} 秒")
            button.setAccessibleName(button.toolTip())

    def set_volume_control_visible(self, visible):
        """Open/close the floating selector without changing the control layout."""
        if visible:
            self.volume_flyout.popup(self.volume_button)
        else:
            self.volume_flyout.dismiss()

    def show_volume_flyout(self):
        self.set_volume_control_visible(not self.volume_flyout.isVisible())

    def set_pause_on_hide(self, enabled):
        """Opt in; ordinary audio playback may legitimately continue hidden."""
        self._pause_on_hide = bool(enabled)

    def _seek_from_slider(self):
        self.controller.seek(round(self.timeline.value() * self._duration / 10000))

    def _seek_if_not_dragging(self, _value):
        if not self._updating_position and not self.timeline.isSliderDown():
            self._seek_from_slider()

    def _position_changed(self, position):
        self.position_label.setText(_time_text(position))
        if not self.timeline.isSliderDown():
            self._updating_position = True
            try:
                self.timeline.setValue(
                    round(position * 10000 / self._duration) if self._duration else 0
                )
            finally:
                self._updating_position = False

    def _duration_changed(self, duration):
        self._duration = duration
        self.duration_label.setText(_time_text(duration))
        self._position_changed(self.controller.position())

    def _sync_volume_icon(self, _value=None):
        icon = _speaker_icon(self.controller)
        self.volume_button.setIcon(fluent_icon(icon))
        self.volume_button.setProperty("fluentIcon", icon.name)

    def _playing_changed(self, playing):
        self.play_button.kind = "pause" if playing else "play"
        self.play_button.setAccessibleName("暂停" if playing else "播放")
        self.play_button.setToolTip(self.play_button.accessibleName())
        self.play_button.update()

    def _theme_changed(self):
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(theme.tokens.text))
        self.setPalette(palette)
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor(theme.tokens.border), 1))
        painter.setBrush(QtGui.QColor(theme.tokens.surface_low))
        painter.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

    def hideEvent(self, event):
        self.volume_flyout.dismiss()
        if self._pause_on_hide:
            self.controller.pause()
        super().hideEvent(event)


class CompactAudioPlayer(AudioPlayer):
    def __init__(self, source=None, parent=None, *, controller=None):
        super().__init__(source, parent, controller=controller, compact=True)


class VideoPlayer(QtWidgets.QWidget):
    """Native QVideoWidget output with a reusable AudioPlayer transport bar."""

    def __init__(self, source=None, parent=None, *, controller=None):
        super().__init__(parent)
        self.controller = controller if controller is not None else MediaController(self)
        _, widgets = multimedia_modules()
        self.video_widget = widgets.QVideoWidget(self)
        self.video_widget.installEventFilter(self)
        self.video_widget.setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.video_widget.setMinimumSize(160, 90)
        self.controller.player().setVideoOutput(self.video_widget)
        self.controls = AudioPlayer(controller=self.controller)
        self.full_screen_button = Button("全屏")
        self.full_screen_button.setMinimumWidth(48)
        self.controls.trailing_layout.addWidget(self.full_screen_button)
        self.full_screen_button.clicked.connect(
            lambda: self.set_full_screen(not self.video_widget.isFullScreen())
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video_widget, 1)
        layout.addWidget(self.controls)
        self.setMinimumSize(260, 240)
        self._pause_on_hide = False
        if source is not None:
            self.set_source(source)

    def set_source(self, source):
        self.controller.set_source(source)

    def set_full_screen(self, enabled):
        """Qt's native video fullscreen; Escape returns to the embedded output."""
        self.video_widget.setFullScreen(bool(enabled))

    def set_pause_on_hide(self, enabled):
        self._pause_on_hide = bool(enabled)

    def eventFilter(self, watched, event):
        if watched is self.video_widget:
            if (
                event.type() == QtCore.QEvent.Type.KeyPress
                and event.key() == QtCore.Qt.Key.Key_Escape
            ):
                if self.video_widget.isFullScreen():
                    self.set_full_screen(False)
                    return True
            if event.type() == QtCore.QEvent.Type.MouseButtonDblClick:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    self.set_full_screen(not self.video_widget.isFullScreen())
                    return True
        return super().eventFilter(watched, event)

    def hideEvent(self, event):
        if self._pause_on_hide and not self.video_widget.isFullScreen():
            self.controller.pause()
        super().hideEvent(event)
