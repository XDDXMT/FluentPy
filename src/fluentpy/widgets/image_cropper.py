"""Reusable image crop canvas and an optional dialog composition."""

from __future__ import annotations

from ..qt import QtCore, QtGui, QtWidgets, Signal
from ..theme import theme
from .button import AccentButton, Button
from .image_view import ImageView


class ImageCropper(ImageView):
    """Move/resize a crop in source pixels; all image operations use Qt."""

    cropChanged = Signal(QtCore.QRect)

    def __init__(self, source=None, parent=None):
        self._crop = QtCore.QRectF()
        self._ratio = None
        self._drag = None
        super().__init__(parent=parent)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(160, 120)
        self.set_background("#303030")
        if source is not None:
            self.set_source(source)

    def set_source(self, source):
        super().set_source(source)
        self._drag = None
        self.set_playing(False)
        self.reset_crop()

    def set_fit_mode(self, mode):
        if mode != "contain":
            raise ValueError("crop canvas uses contain to keep every crop handle accessible")
        super().set_fit_mode(mode)

    def clear(self):
        self._drag = None
        super().clear()
        self._crop = QtCore.QRectF()
        self.cropChanged.emit(QtCore.QRect())

    def set_aspect_ratio(self, ratio: float | None):
        if ratio is not None and not 0.01 <= ratio <= 100:
            raise ValueError("aspect ratio must be None or between 0.01 and 100")
        self._ratio = ratio
        self.reset_crop()

    def aspect_ratio(self):
        return self._ratio

    def reset_crop(self):
        if self._image.isNull():
            return
        area = QtCore.QRectF(self._image.rect())
        area.adjust(
            area.width() * 0.1, area.height() * 0.1, -area.width() * 0.1, -area.height() * 0.1
        )
        self.set_crop_rect(area)

    def set_crop_rect(self, rect):
        area = QtCore.QRectF(self._image.rect())
        rect = QtCore.QRectF(rect).normalized().intersected(area)
        if rect.isEmpty():
            raise ValueError("crop must intersect a non-empty image")
        if self._ratio is not None:
            width = min(rect.width(), rect.height() * self._ratio)
            size = QtCore.QSizeF(width, width / self._ratio)
            center = rect.center()
            rect = QtCore.QRectF(QtCore.QPointF(), size)
            rect.moveCenter(center)
        self._crop = rect
        self.update()
        self.cropChanged.emit(self.crop_rect())

    def crop_rect(self):
        return self._crop.toAlignedRect().intersected(self._image.rect())

    def cropped_image(self, size=None):
        image = self._image.copy(self.crop_rect()) if not self._crop.isEmpty() else QtGui.QImage()
        if size is not None and not image.isNull():
            size = QtCore.QSize(size)
            if size.isEmpty():
                raise ValueError("output size must be positive")
            image = image.scaled(
                size,
                QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        return image

    def rotate(self, degrees=90):
        if degrees not in {-270, -180, -90, 0, 90, 180, 270}:
            raise ValueError("rotation must be a multiple of 90 degrees")
        if not self._image.isNull():
            self.set_image(self._image.transformed(QtGui.QTransform().rotate(degrees)))

    def flip(self, horizontal=True):
        if not self._image.isNull():
            transform = QtGui.QTransform().scale(-1 if horizontal else 1, 1 if horizontal else -1)
            self.set_image(self._image.transformed(transform))

    def _selection_rect(self):
        return QtCore.QRectF(
            self.image_to_widget(self._crop.topLeft()),
            self.image_to_widget(self._crop.bottomRight()),
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._crop.isEmpty():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self._selection_rect()
        mask = QtGui.QPainterPath()
        mask.addRect(QtCore.QRectF(self.rect()))
        mask.addRect(rect)
        painter.fillPath(mask, QtGui.QColor(0, 0, 0, 130))
        painter.setPen(QtGui.QPen(QtGui.QColor("white"), 1))
        painter.drawRect(rect)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 80), 1))
        for fraction in (1 / 3, 2 / 3):
            x, y = rect.left() + rect.width() * fraction, rect.top() + rect.height() * fraction
            painter.drawLine(QtCore.QPointF(x, rect.top()), QtCore.QPointF(x, rect.bottom()))
            painter.drawLine(QtCore.QPointF(rect.left(), y), QtCore.QPointF(rect.right(), y))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor("white"))
        for point in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            painter.drawEllipse(point, 6, 6)

    def _hit(self, point):
        rect = self._selection_rect()
        for corner in ("topLeft", "topRight", "bottomLeft", "bottomRight"):
            if QtCore.QLineF(point, getattr(rect, corner)()).length() <= 12:
                return corner
        return "move" if rect.contains(point) else "new"

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and not self._image.isNull():
            if not self.image_rect().contains(event.position()):
                return
            self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
            self._drag = (
                self._hit(event.position()),
                self.widget_to_image(event.position()),
                QtCore.QRectF(self._crop),
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is None:
            hit = self._hit(event.position())
            cursors = {
                "topLeft": QtCore.Qt.CursorShape.SizeFDiagCursor,
                "bottomRight": QtCore.Qt.CursorShape.SizeFDiagCursor,
                "topRight": QtCore.Qt.CursorShape.SizeBDiagCursor,
                "bottomLeft": QtCore.Qt.CursorShape.SizeBDiagCursor,
                "move": QtCore.Qt.CursorShape.SizeAllCursor,
                "new": QtCore.Qt.CursorShape.CrossCursor,
            }
            self.setCursor(cursors[hit])
            return
        hit, start, original = self._drag
        point = self.widget_to_image(event.position())
        if hit == "move":
            rect = original.translated(point - start)
            rect.moveLeft(max(0, min(self._image.width() - rect.width(), rect.left())))
            rect.moveTop(max(0, min(self._image.height() - rect.height(), rect.top())))
        else:
            opposite = {
                "topLeft": "bottomRight",
                "topRight": "bottomLeft",
                "bottomLeft": "topRight",
                "bottomRight": "topLeft",
            }
            anchor = start if hit == "new" else getattr(original, opposite[hit])()
            if self._ratio is not None:
                dx, dy = point.x() - anchor.x(), point.y() - anchor.y()
                width = min(abs(dx), abs(dy) * self._ratio)
                point = anchor + QtCore.QPointF(
                    width if dx >= 0 else -width,
                    width / self._ratio if dy >= 0 else -width / self._ratio,
                )
            rect = QtCore.QRectF(anchor, point).normalized()
        if rect.width() >= 1 and rect.height() >= 1:
            self.set_crop_rect(rect)

    def mouseReleaseEvent(self, event):
        self._drag = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        moves = {
            QtCore.Qt.Key.Key_Left: (-1, 0),
            QtCore.Qt.Key.Key_Right: (1, 0),
            QtCore.Qt.Key.Key_Up: (0, -1),
            QtCore.Qt.Key.Key_Down: (0, 1),
        }
        if event.key() in moves and not self._crop.isEmpty():
            dx, dy = moves[event.key()]
            step = 10 if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier else 1
            rect = self._crop.translated(dx * step, dy * step)
            rect.moveLeft(max(0, min(self._image.width() - rect.width(), rect.left())))
            rect.moveTop(max(0, min(self._image.height() - rect.height(), rect.top())))
            self.set_crop_rect(rect)
            event.accept()
            return
        super().keyPressEvent(event)


class ImageCropDialog(QtWidgets.QDialog):
    """Optional composition; use ``cropper`` or ``toolbar_layout`` independently."""

    imageCropped = Signal(QtGui.QImage)

    def __init__(self, source, parent=None, *, aspect_ratio=None):
        super().__init__(parent)
        self.setWindowTitle("裁剪图片")
        self.resize(780, 580)
        self.cropper = ImageCropper(source)
        self.cropper.set_aspect_ratio(aspect_ratio)
        self._result_image = QtGui.QImage()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self.cropper, 1)
        self.toolbar_layout = QtWidgets.QHBoxLayout()
        cancel, rotate, flip, reset, apply = (
            Button("取消"),
            Button("旋转 90°"),
            Button("镜像"),
            Button("重置选区"),
            AccentButton("使用图片"),
        )
        for button in (cancel, rotate, flip, reset):
            self.toolbar_layout.addWidget(button)
        self.toolbar_layout.addStretch(1)
        self.toolbar_layout.addWidget(apply)
        layout.addLayout(self.toolbar_layout)
        cancel.clicked.connect(self.reject)
        rotate.clicked.connect(lambda: self.cropper.rotate())
        flip.clicked.connect(lambda: self.cropper.flip())
        reset.clicked.connect(self.cropper.reset_crop)
        apply.clicked.connect(self.accept)
        theme.changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self):
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(theme.tokens.background))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def accept(self):
        self._result_image = self.cropper.cropped_image()
        if self._result_image.isNull():
            return
        self.imageCropped.emit(self.result_image())
        super().accept()

    def result_image(self):
        return QtGui.QImage(self._result_image)
