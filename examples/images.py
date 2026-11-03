"""Image/GIF, avatar, crop and product-detail magnifier examples."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fluentpy import (
    AvatarPicker,
    AvatarWidget,
    Button,
    CheckBox,
    ComboBox,
    HeaderCardWidget,
    ImageCropDialog,
    ImageCropper,
    ImageMagnifier,
    ImageView,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets


def sample_image():
    """Original vector-like landscape rendered by Qt, requiring no downloads."""
    image = QtGui.QImage(960, 600, QtGui.QImage.Format.Format_RGB32)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    sky = QtGui.QLinearGradient(0, 0, 960, 600)
    sky.setColorAt(0, QtGui.QColor("#153f78"))
    sky.setColorAt(0.6, QtGui.QColor("#5ac8cd"))
    sky.setColorAt(1, QtGui.QColor("#e0f3ed"))
    painter.fillRect(image.rect(), sky)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QColor("#f5dc96"))
    painter.drawEllipse(QtCore.QPointF(720, 155), 66, 66)
    for color, points in (
        (
            "#31677a",
            [(0, 460), (270, 180), (570, 480), (810, 270), (960, 420), (960, 600), (0, 600)],
        ),
        ("#174e60", [(0, 530), (350, 350), (650, 530), (960, 380), (960, 600), (0, 600)]),
        ("#103a49", [(0, 600), (0, 540), (400, 480), (700, 570), (960, 500), (960, 600)]),
    ):
        painter.setBrush(QtGui.QColor(color))
        painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in points]))
    painter.setPen(QtGui.QColor("#e1f6f1"))
    font = painter.font()
    font.setPixelSize(38)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(48, 76, "FLUENTPY / LANDSCAPE")
    font.setPixelSize(17)
    font.setBold(False)
    painter.setFont(font)
    painter.drawText(50, 108, "Explore the details. Make it yours.")
    painter.end()
    return image


class ImageExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = sample_image()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        toolbar = QtWidgets.QHBoxLayout()
        choose = Button("打开图片 / GIF")
        self.fit = ComboBox()
        self.fit.addItems(["完整显示", "填满区域", "拉伸"])
        toolbar.addWidget(choose)
        toolbar.addWidget(self.fit)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.status = QtWidgets.QLabel("使用本地文件；原图不会被修改。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        display = HeaderCardWidget("图片与头像")
        self.image = ImageView(self._source)
        self.image.setFixedHeight(230)
        display.body_layout.addWidget(self.image)
        row = QtWidgets.QHBoxLayout()
        self.avatar = AvatarWidget(self._source, size=60)
        self.picker = AvatarPicker(self._source, size=60)
        self.picker.avatarChanged.connect(
            lambda _image: self.status.setText(
                "头像已裁剪，可通过 avatarChanged 保存到自己的位置。"
            )
        )
        self.picker.selectionFailed.connect(self.status.setText)
        row.addWidget(self.avatar)
        row.addWidget(self.picker)
        row.addWidget(QtWidgets.QLabel("点击第二个头像，选择并裁剪本地图片。"), 1)
        display.body_layout.addLayout(row)
        layout.addWidget(display)
        detail = HeaderCardWidget("局部放大 · 悬停 / 聚焦 / 方向键")
        self.magnifier = ImageMagnifier(self._source)
        self.magnifier.setFixedHeight(240)
        self.magnifier.set_preview_rect(None)
        self.preview = ImageView()
        self.preview.setFixedSize(180, 140)
        self.preview.set_background("#163d4e")
        self.magnifier.magnifiedImageChanged.connect(self.preview.set_image)
        self.magnifier.set_anchor(QtCore.QPointF(700, 170))
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.magnifier, 1)
        row.addWidget(self.preview)
        detail.body_layout.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        enabled = CheckBox("启用放大镜")
        enabled.setChecked(True)
        enabled.toggled.connect(self.magnifier.set_magnifier_enabled)
        shape = ComboBox()
        shape.addItems(["独立预览", "圆形镜片", "圆角镜片", "矩形镜片"])
        shape.currentIndexChanged.connect(self._shape_changed)
        row.addWidget(enabled)
        row.addWidget(shape)
        row.addStretch()
        detail.body_layout.addLayout(row)
        layout.addWidget(detail)
        crop = HeaderCardWidget("裁剪 · 拖动四角或移动选区")
        self.cropper = ImageCropper(self._source)
        self.cropper.setFixedHeight(280)
        crop.body_layout.addWidget(self.cropper)
        row = QtWidgets.QHBoxLayout()
        rotate, flip, apply = (Button("旋转"), Button("镜像"), Button("打开裁剪对话框"))
        rotate.clicked.connect(lambda: self.cropper.rotate())
        flip.clicked.connect(lambda: self.cropper.flip())
        apply.clicked.connect(self._crop_dialog)
        for button in (rotate, flip, apply):
            row.addWidget(button)
        row.addStretch()
        crop.body_layout.addLayout(row)
        layout.addWidget(crop)
        choose.clicked.connect(self._choose)
        self.fit.currentIndexChanged.connect(
            lambda index: self.image.set_fit_mode(("contain", "cover", "stretch")[index])
        )

    def _shape_changed(self, index):
        self.magnifier.set_preview_rect(None if index == 0 else QtCore.QRect(12, 12, 180, 140))
        if index:
            self.magnifier.set_lens_shape(("circle", "rounded", "rectangle")[index - 1])

    def _choose(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择本地图片", "", "图片 (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;所有文件 (*)"
        )
        if not path:
            return
        try:
            self.image.set_source(path)
            self._source = self.image.image()
            self.magnifier.set_image(self._source)
            self.cropper.set_image(self._source)
            self.avatar.set_image(self._source)
            self.status.setText(Path(path).name)
        except ValueError as exc:
            self.status.setText(str(exc))

    def _crop_dialog(self):
        dialog = ImageCropDialog(self._source, self.window())
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.image.set_image(dialog.result_image())
            self.status.setText("已显示裁剪结果；源文件保持原样。")
        dialog.deleteLater()


if __name__ == "__main__":
    from fluentpy import FluentWindow

    app = QtWidgets.QApplication(sys.argv)
    window = FluentWindow("FluentPy · 图像")
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(ImageExamples())
    window.content_layout.addWidget(scroll)
    window.resize(1000, 800)
    window.show()
    sys.exit(app.exec())
