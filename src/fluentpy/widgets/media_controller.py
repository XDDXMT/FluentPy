"""Lazy Qt Multimedia adapter shared by audio and video control surfaces."""

from __future__ import annotations

import math
from pathlib import Path

from ..qt import QT_API, QtCore, Signal, Slot


def multimedia_modules():
    """Import only when a media source/output is actually requested."""
    if QT_API == "PySide6":
        from PySide6 import QtMultimedia, QtMultimediaWidgets
    else:
        from PyQt6 import QtMultimedia, QtMultimediaWidgets
    return QtMultimedia, QtMultimediaWidgets


class MediaController(QtCore.QObject):
    positionChanged = Signal(object)  # qint64 milliseconds, including long recordings
    durationChanged = Signal(object)
    playingChanged = Signal(bool)
    seekableChanged = Signal(bool)
    sourceChanged = Signal(QtCore.QUrl)
    volumeChanged = Signal(float)
    mutedChanged = Signal(bool)
    errorOccurred = Signal(str)
    mediaStatusChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = None
        self._audio = None
        self._volume = 0.7
        self._muted = False

    def _ensure_player(self):
        if self._player is not None:
            return
        multimedia, _ = multimedia_modules()
        player = multimedia.QMediaPlayer(self)
        audio = multimedia.QAudioOutput(self)
        audio.setVolume(self._volume)
        audio.setMuted(self._muted)
        player.setAudioOutput(audio)
        player.positionChanged.connect(self.positionChanged.emit)
        player.durationChanged.connect(self.durationChanged.emit)
        player.playbackStateChanged.connect(
            lambda _state: self.playingChanged.emit(self.is_playing())
        )
        player.seekableChanged.connect(self.seekableChanged.emit)
        player.sourceChanged.connect(self.sourceChanged.emit)
        player.mediaStatusChanged.connect(self.mediaStatusChanged.emit)
        player.errorOccurred.connect(lambda _error, text: self.errorOccurred.emit(text))
        audio.volumeChanged.connect(self._volume_changed)
        audio.mutedChanged.connect(self._muted_changed)
        self._player, self._audio = player, audio

    def player(self):
        self._ensure_player()
        return self._player

    def audio_output(self):
        self._ensure_player()
        return self._audio

    def set_source(self, source):
        """Local path or explicit QUrl (including network URLs); does not autoplay."""
        if isinstance(source, QtCore.QUrl):
            url = QtCore.QUrl(source)
            if not url.isValid():
                raise ValueError("invalid media URL")
        elif isinstance(source, (str, Path)):
            path = Path(source).expanduser().resolve()
            if not path.is_file():
                raise ValueError("media file does not exist")
            url = QtCore.QUrl.fromLocalFile(str(path))
        else:
            raise TypeError("source must be a local path or QUrl")
        self.player().setSource(url)

    def source(self):
        return self._player.source() if self._player else QtCore.QUrl()

    def clear(self):
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QtCore.QUrl())

    @Slot()
    def play(self):
        self.player().play()

    @Slot()
    def pause(self):
        if self._player is not None:
            self._player.pause()

    @Slot()
    def stop(self):
        if self._player is not None:
            self._player.stop()

    @Slot()
    def toggle_playback(self):
        self.pause() if self.is_playing() else self.play()

    def is_playing(self):
        return self._player is not None and self._player.isPlaying()

    def duration(self):
        return self._player.duration() if self._player else 0

    def position(self):
        return self._player.position() if self._player else 0

    def is_seekable(self):
        return self._player is not None and self._player.isSeekable()

    @Slot(object)
    def seek(self, milliseconds):
        if not isinstance(milliseconds, int) or isinstance(milliseconds, bool):
            raise TypeError("seek position must be an integer number of milliseconds")
        if self.is_seekable():
            self._player.setPosition(max(0, min(self.duration(), milliseconds)))

    def seek_by(self, milliseconds):
        self.seek(self.position() + milliseconds)

    def set_playback_rate(self, rate):
        if not math.isfinite(rate) or not 0.1 <= rate <= 8:
            raise ValueError("playback rate must be between 0.1 and 8")
        self.player().setPlaybackRate(rate)

    def volume(self):
        return self._volume

    def set_volume(self, volume):
        if not math.isfinite(volume) or not 0 <= volume <= 1:
            raise ValueError("volume must be between 0 and 1")
        if self._audio is not None:
            self._audio.setVolume(volume)
        else:
            self._volume_changed(volume)

    def _volume_changed(self, volume):
        self._volume = float(volume)
        self.volumeChanged.emit(self._volume)

    def is_muted(self):
        return self._muted

    @Slot(bool)
    def set_muted(self, muted):
        if self._audio is not None:
            self._audio.setMuted(bool(muted))
        else:
            self._muted_changed(bool(muted))

    def _muted_changed(self, muted):
        self._muted = bool(muted)
        self.mutedChanged.emit(self._muted)
