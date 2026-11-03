"""An image magnifier with public source regions and an optional output surface."""

from __future__ import annotations

import math

from ..qt import QtCore, QtGui, Signal, Slot
from ..theme import theme
from .image_view import ImageView


class ImageMagnifier(ImageView):
    """Hover/focus to inspect a source region, or drive the anchor from code.

    The unscaled source crop and enlarged output are both available as QImages.
    Connect ``magnifiedImageChanged`` to any ImageView's ``set_image`` for an
    external product-detail preview. ``set_preview_rect(None)`` hides only the
    built-in preview, retaining the signal/output API.
    """

    magnifierEnabledChanged = Signal(bool)
    regionChanged = Signal(QtGui.QImage, QtCore.QRect)
    magnifiedImageChanged = Signal(QtGui.QImage)

    def __init__(self, source=None, parent=None):
        self._magnifier_enabled = True
        self._active = False
        self._anchor = None
        self._lens_size = QtCore.QSize(180, 140)
        self._zoom = 3.0
        self._shape = "rounded"
        self._preview_rect = QtCore.QRect(12, 12, 180, 140)
        self._region = QtCore.QRect()
        self._region_image = QtGui.QImage()
        self._magnified = QtGui.QImage()
        super().__init__(source, parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.frameChanged.connect(self._refresh_region)
        self.setAccessibleName("图片放大镜，方向键移动观察位置")

    @Slot(bool)
    def set_magnifier_enabled(self, enabled):
        enabled = bool(enabled)
        if enabled != self._magnifier_enabled:
            self._magnifier_enabled = enabled
            self.magnifierEnabledChanged.emit(enabled)
            if enabled:
                self._refresh_region()
            self.update()

    def is_magnifier_enabled(self):
        return self._magnifier_enabled

    def set_zoom(self, zoom):
        if not math.isfinite(zoom) or not 1 <= zoom <= 64:
            raise ValueError("zoom must be between 1 and 64")
        self._zoom = float(zoom)
        self._refresh_region()

    def zoom(self):
        return self._zoom

    def set_lens_size(self, size):
        size = QtCore.QSize(size)
        if not 16 <= size.width() <= 2048 or not 16 <= size.height() <= 2048:
            raise ValueError("lens dimensions must be between 16 and 2048")
        self._lens_size = size
        if self._preview_rect is not None:
            self._preview_rect.setSize(size)
        self._refresh_region()

    def lens_size(self):
        return QtCore.QSize(self._lens_size)

    def set_lens_shape(self, shape):
        if shape not in {"rectangle", "rounded", "circle"}:
            raise ValueError("shape must be rectangle, rounded, or circle")
        self._shape = shape
        self.update()

    def lens_shape(self):
        return self._shape

    def set_preview_rect(self, rect):
        value = None if rect is None else QtCore.QRect(rect)
        if value is not None and value.isEmpty():
            raise ValueError("preview rectangle must have positive size")
        self._preview_rect = value
        self.update()

    def preview_rect(self):
        return None if self._preview_rect is None else QtCore.QRect(self._preview_rect)

    @Slot(QtCore.QPointF)
    def set_anchor(self, point):
        """Set a source-pixel anchor, independently of the mouse position."""
        if not math.isfinite(point.x()) or not math.isfinite(point.y()):
            raise ValueError("anchor coordinates must be finite")
        self._anchor = QtCore.QPointF(point)
        self._active = True
        self._refresh_region()

    def source_region(self):
        return QtCore.QRect(self._region)

    def region_image(self):
        return QtGui.QImage(self._region_image)

    def magnified_image(self):
        return QtGui.QImage(self._magnified)

    def _refresh_region(self, _image=None):
        if not self._magnifier_enabled:
            return
        if self._image.isNull():
            self._region = QtCore.QRect()
            self._region_image = self._magnified = QtGui.QImage()
        else:
            anchor = self._anchor or QtCore.QRectF(self._image.rect()).center()
            # Zoom is defined in source pixels; resizing the widget never changes
            # the extracted area or the output image requested by the developer.
            width = min(self._image.width(), max(1, round(self._lens_size.width() / self._zoom)))
            height = min(self._image.height(), max(1, round(self._lens_size.height() / self._zoom)))
            x = max(0, min(self._image.width() - width, round(anchor.x() - width / 2)))
            y = max(0, min(self._image.height() - height, round(anchor.y() - height / 2)))
            self._region = QtCore.QRect(x, y, width, height)
            self._region_image = self._image.copy(self._region)
            self._magnified = self._region_image.scaled(
                self._lens_size,
                QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        self.regionChanged.emit(self.region_image(), self.source_region())
        self.magnifiedImageChanged.emit(self.magnified_image())
        self.update()

    def mouseMoveEvent(self, event):
        if self.image_rect().intersected(QtCore.QRectF(self.rect())).contains(event.position()):
            self.set_anchor(self.widget_to_image(event.position()))
        else:
            self._active = self.hasFocus()
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._active = self.hasFocus()
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self._active = True
        self._refresh_region()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._active = self.underMouse()
        self.update()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        moves = {
            QtCore.Qt.Key.Key_Left: (-1, 0),
            QtCore.Qt.Key.Key_Right: (1, 0),
            QtCore.Qt.Key.Key_Up: (0, -1),
            QtCore.Qt.Key.Key_Down: (0, 1),
        }
        if event.key() in moves and not self._image.isNull():
            dx, dy = moves[event.key()]
            step = 10 if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier else 1
            point = self._anchor or QtCore.QRectF(self._image.rect()).center()
            self.set_anchor(
                QtCore.QPointF(
                    max(0, min(self._image.width(), point.x() + dx * step)),
                    max(0, min(self._image.height(), point.y() + dy * step)),
                )
            )
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not (self._active and self._magnifier_enabled) or self._magnified.isNull():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = QtCore.QRectF(
            self.image_to_widget(QtCore.QPointF(self._region.topLeft())),
            self.image_to_widget(QtCore.QPointF(self._region.bottomRight() + QtCore.QPoint(1, 1))),
        )
        painter.setPen(QtGui.QPen(QtGui.QColor(theme.tokens.accent), 2))
        painter.setBrush(QtGui.QColor(0, 159, 170, 35))
        painter.drawRect(rect)
        if self._preview_rect is None:
            return
        rect = QtCore.QRectF(self._preview_rect)
        path = QtGui.QPainterPath()
        if self._shape == "circle":
            side = min(rect.width(), rect.height())
            square = QtCore.QRectF(0, 0, side, side)
            square.moveCenter(rect.center())
            rect = square
            path.addEllipse(rect)
        elif self._shape == "rounded":
            path.addRoundedRect(rect, 10, 10)
        else:
            path.addRect(rect)
        painter.save()
        painter.setClipPath(path)
        painter.drawImage(rect, self._magnified)
        painter.restore()
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
