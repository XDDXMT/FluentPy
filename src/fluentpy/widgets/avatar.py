"""Circular image surfaces and a local, opt-in avatar selection workflow."""

from ..qt import QtCore, QtGui, QtWidgets, Signal, Slot
from ..theme import theme
from .image_cropper import ImageCropDialog
from .image_view import ImageView


class AvatarWidget(ImageView):
    def __init__(self, source=None, parent=None, *, size=64, initials=""):
        super().__init__(source, parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self._initials = initials
        self.set_fit_mode("cover")
        self.set_avatar_size(size)
        self.setAccessibleName("头像")

    def set_avatar_size(self, size):
        if not 16 <= size <= 2048:
            raise ValueError("avatar size must be between 16 and 2048")
        self.setFixedSize(int(size), int(size))

    def set_initials(self, text):
        self._initials = str(text)
        self.update()

    def _clip_path(self):
        path = QtGui.QPainterPath()
        path.addEllipse(QtCore.QRectF(self.contentsRect()))
        return path

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._image.isNull():
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setClipPath(self._clip_path())
            painter.fillRect(self.rect(), QtGui.QColor(theme.tokens.surface_high))
            painter.setPen(QtGui.QColor(theme.tokens.text))
            font = self.font()
            font.setPixelSize(max(12, self.width() // 3))
            painter.setFont(font)
            painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self._initials[:2])
        if self.hasFocus():
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setPen(QtGui.QPen(QtGui.QColor(theme.tokens.accent), 2))
            painter.drawEllipse(QtCore.QRectF(self.rect()).adjusted(2, 2, -2, -2))


class AvatarPicker(AvatarWidget):
    """Click/Enter to select, crop and accept a copy of a local image.

    Canceling either dialog leaves the current avatar unchanged. The source
    file is never written; applications decide whether/where to save the image.
    """

    clicked = Signal()
    avatarChanged = Signal(QtGui.QImage)
    fileSelected = Signal(str)
    selectionFailed = Signal(str)

    def __init__(self, source=None, parent=None, *, size=64, initials=""):
        super().__init__(source, parent, size=size, initials=initials)
        self._pressed = False
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setToolTip("选择并裁剪头像")
        self.setAccessibleName("选择并裁剪头像")
        self.clicked.connect(self.choose_image)

    @Slot()
    def choose_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择头像", "", "图片 (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;所有文件 (*)"
        )
        if path:
            try:
                self.select_file(path)
            except (ValueError, OSError) as exc:
                self.selectionFailed.emit(str(exc))

    def select_file(self, path):
        """Open the crop dialog for a chosen path; returns whether accepted."""
        dialog = ImageCropDialog(path, self.window(), aspect_ratio=1)
        try:
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return False
            image = dialog.result_image()
            self.set_image(image)
            self.fileSelected.emit(str(path))
            self.avatarChanged.emit(self.image())
            return True
        finally:
            dialog.deleteLater()

    def mousePressEvent(self, event):
        self._pressed = event.button() == QtCore.Qt.MouseButton.LeftButton and self.isEnabled()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        pressed = self._pressed
        self._pressed = False
        if (
            pressed
            and event.button() == QtCore.Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
            and self.isEnabled()
        ):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def hideEvent(self, event):
        self._pressed = False
        super().hideEvent(event)

    def keyPressEvent(self, event):
        if (
            event.key()
            in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Space)
            and self.isEnabled()
        ):
            if not event.isAutoRepeat():
                self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)
