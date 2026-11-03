"""Image and animation surfaces rendered by Qt, with source-coordinate mapping."""

from __future__ import annotations

from os import PathLike

from ..qt import QtCore, QtGui, QtWidgets, Signal
from ..theme import theme


def read_image(source) -> QtGui.QImage:
    """Read a local image, honoring EXIF orientation; never modify its file."""
    if isinstance(source, QtGui.QImage):
        image = QtGui.QImage(source)
    elif isinstance(source, QtGui.QPixmap):
        image = source.toImage()
    elif isinstance(source, (str, PathLike)):
        reader = QtGui.QImageReader(str(source))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Cannot read image: {reader.errorString()}")
    else:
        raise TypeError("expected a QImage, QPixmap, or local image path")
    if image.isNull():
        raise ValueError("image is empty")
    image.setDevicePixelRatio(1.0)
    return image


class ImageView(QtWidgets.QWidget):
    """Display an image or animated GIF without a widget for each frame.

    ``image()`` returns the current frame. Hidden animations pause and resume
    when shown, while an explicit ``set_playing(False)`` persists across hides.
    """

    imageChanged = Signal(QtGui.QImage)
    frameChanged = Signal(QtGui.QImage)

    def __init__(self, source=None, parent=None):
        super().__init__(parent)
        self._image = QtGui.QImage()
        self._movie = None
        self._playing = True
        self._fit_mode = "contain"
        self._radius = 8.0
        self._background = None
        self.setMinimumSize(24, 24)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )
        theme.changed.connect(self.update)
        if source is not None:
            self.set_source(source)

    def set_source(self, source):
        image = read_image(source)
        movie = None
        if isinstance(source, (str, PathLike)):
            reader = QtGui.QImageReader(str(source))
            if reader.supportsAnimation():
                movie = QtGui.QMovie(str(source), parent=self)
                if not movie.isValid():
                    movie.deleteLater()
                    raise ValueError("invalid animated image")
        self._release_movie()
        self._movie = movie
        if movie is not None:
            movie.frameChanged.connect(self._movie_frame)
            movie.jumpToFrame(0)
            if self.isVisible() and self._playing:
                movie.start()
        self._set_frame(image)
        self.imageChanged.emit(self.image())

    def set_image(self, source):
        self.set_source(source)

    def clear(self):
        self._release_movie()
        self._set_frame(QtGui.QImage())
        self.imageChanged.emit(self.image())

    def _release_movie(self):
        if self._movie is not None:
            self._movie.stop()
            self._movie.frameChanged.disconnect(self._movie_frame)
            self._movie.deleteLater()
            self._movie = None

    def _movie_frame(self, _number):
        if self._movie is not None:
            self._set_frame(self._movie.currentImage())

    def _set_frame(self, image):
        self._image = QtGui.QImage(image)
        self._image.setDevicePixelRatio(1.0)
        self.updateGeometry()
        self.update()
        self.frameChanged.emit(self.image())

    def image(self):
        return QtGui.QImage(self._image)

    def movie(self):
        return self._movie

    def set_playing(self, playing: bool):
        self._playing = bool(playing)
        if self._movie is not None:
            if self.isVisible() and self._playing:
                self._movie.start()
                self._movie.setPaused(False)
            else:
                self._movie.setPaused(True)

    def is_playing(self):
        return self._playing

    def set_fit_mode(self, mode: str):
        if mode not in {"contain", "cover", "stretch"}:
            raise ValueError("fit mode must be contain, cover, or stretch")
        self._fit_mode = mode
        self.update()

    def fit_mode(self):
        return self._fit_mode

    def set_corner_radius(self, radius: float):
        if not 0 <= radius <= 10000:
            raise ValueError("radius must be between 0 and 10000")
        self._radius = float(radius)
        self.update()

    def set_background(self, color=None):
        value = QtGui.QColor(color) if color is not None else None
        if value is not None and not value.isValid():
            raise ValueError("invalid background color")
        self._background = value
        self.update()

    def image_rect(self):
        """Full source frame's destination rectangle, including cover overflow."""
        area = QtCore.QRectF(self.contentsRect())
        if self._image.isNull() or self._fit_mode == "stretch":
            return area
        size = QtCore.QSizeF(self._image.size())
        aspect = (
            QtCore.Qt.AspectRatioMode.KeepAspectRatio
            if self._fit_mode == "contain"
            else QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding
        )
        size.scale(area.size(), aspect)
        result = QtCore.QRectF(QtCore.QPointF(), size)
        result.moveCenter(area.center())
        return result

    def image_to_widget(self, point):
        area = self.image_rect()
        if self._image.isNull():
            return QtCore.QPointF()
        return QtCore.QPointF(
            area.left() + point.x() * area.width() / self._image.width(),
            area.top() + point.y() * area.height() / self._image.height(),
        )

    def widget_to_image(self, point, *, clamp=True):
        area = self.image_rect()
        if self._image.isNull() or area.isEmpty():
            return QtCore.QPointF()
        x = (point.x() - area.left()) * self._image.width() / area.width()
        y = (point.y() - area.top()) * self._image.height() / area.height()
        if clamp:
            x = max(0, min(self._image.width(), x))
            y = max(0, min(self._image.height(), y))
        return QtCore.QPointF(x, y)

    def _clip_path(self):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.contentsRect()), self._radius, self._radius)
        return path

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.SmoothPixmapTransform
        )
        painter.setClipPath(self._clip_path())
        if self._background is not None:
            painter.fillRect(self.rect(), self._background)
        if not self._image.isNull():
            painter.drawImage(self.image_rect(), self._image)

    def sizeHint(self):
        if self._image.isNull():
            return QtCore.QSize(320, 180)
        return self._image.size().scaled(640, 360, QtCore.Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        self.set_playing(self._playing)

    def hideEvent(self, event):
        if self._movie is not None:
            self._movie.setPaused(True)
        super().hideEvent(event)
