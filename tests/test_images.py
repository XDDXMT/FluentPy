"""Source coordinates, real GIF frames and editable image interaction."""

import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fluentpy import (
    AvatarPicker,
    AvatarWidget,
    ImageCropDialog,
    ImageCropper,
    ImageMagnifier,
    ImageView,
)
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

GIF = "R0lGODlhBAAEAIEAAP8AAAAAAAAAAAAAACH/C05FVFNDQVBFMi4wAwEAAAAh+QQACAAAACwAAAAABAAEAAAICQABCBxIsCCAgAAh+QQBCAABACwAAAAABAAEAIEAAP8AAAAAAAAAAAAICQABCBxIsCCAgAA7"


class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.image = QtGui.QImage(400, 200, QtGui.QImage.Format.Format_RGB32)
        self.image.fill(QtGui.QColor("red"))
        painter = QtGui.QPainter(self.image)
        painter.fillRect(200, 0, 200, 200, QtGui.QColor("blue"))
        painter.end()
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.temp.cleanup()

    def show(self, widget):
        self.widgets.append(widget)
        widget.resize(400, 300)
        widget.show()
        self.app.processEvents()
        return widget

    def test_fit_mapping_and_image_copy_ownership(self):
        view = self.show(ImageView(self.image))
        self.assertEqual(view.image_rect(), QtCore.QRectF(0, 50, 400, 200))
        self.assertEqual(view.widget_to_image(QtCore.QPointF(200, 150)), QtCore.QPointF(200, 100))
        view.set_fit_mode("cover")
        self.assertEqual(view.image_rect(), QtCore.QRectF(-100, 0, 600, 300))
        self.assertEqual(view.widget_to_image(QtCore.QPointF(0, 150)), QtCore.QPointF(400 / 6, 100))
        view.set_fit_mode("stretch")
        self.assertEqual(view.image_to_widget(QtCore.QPointF(400, 200)), QtCore.QPointF(400, 300))
        copy = view.image()
        copy.fill(QtGui.QColor("green"))
        self.assertEqual(view.image().pixelColor(0, 0).name(), "#ff0000")
        with self.assertRaises(ValueError):
            view.set_source(Path(self.temp.name) / "missing.png")
        self.assertFalse(view.image().isNull())

    def test_real_gif_changes_frames_and_hidden_pause_respects_explicit_stop(self):
        path = Path(self.temp.name) / "two.gif"
        path.write_bytes(base64.b64decode(GIF))
        view = self.show(ImageView(path))
        colors = []
        view.frameChanged.connect(lambda image: colors.append(image.pixelColor(0, 0).name()))
        QTest.qWait(290)
        self.assertIn("#0000ff", colors)
        self.assertIn("#ff0000", colors)
        view.hide()
        self.assertEqual(view.movie().state(), QtGui.QMovie.MovieState.Paused)
        view.set_playing(False)
        view.show()
        self.assertNotEqual(view.movie().state(), QtGui.QMovie.MovieState.Running)
        view.set_playing(True)
        self.assertEqual(view.movie().state(), QtGui.QMovie.MovieState.Running)
        view.set_image(self.image)
        self.assertIsNone(view.movie())

    def test_crop_rect_dimensions_pixels_rotation_and_keyboard(self):
        crop = self.show(ImageCropper(self.image))
        crop.set_crop_rect(QtCore.QRect(200, 0, 200, 200))
        output = crop.cropped_image(QtCore.QSize(64, 64))
        self.assertEqual(output.size(), QtCore.QSize(64, 64))
        self.assertEqual(output.pixelColor(20, 20).name(), "#0000ff")
        crop.rotate(90)
        self.assertEqual(crop.image().size(), QtCore.QSize(200, 400))
        crop.set_aspect_ratio(1)
        self.assertEqual(crop.crop_rect().width(), crop.crop_rect().height())
        crop.set_crop_rect(QtCore.QRect(20, 20, 100, 100))
        QTest.keyClick(crop, QtCore.Qt.Key.Key_Right)
        self.assertEqual(crop.crop_rect().x(), 21)
        crop.flip()
        self.assertFalse(crop.cropped_image().isNull())
        with self.assertRaises(ValueError):
            crop.set_crop_rect(QtCore.QRect(-20, -20, 1, 1))
        with self.assertRaises(ValueError):
            crop.set_aspect_ratio(0)

    def test_crop_drag_moves_and_resizes_in_source_pixels(self):
        crop = self.show(ImageCropper(self.image))
        crop.set_crop_rect(QtCore.QRect(50, 30, 200, 100))
        center = crop.image_to_widget(QtCore.QPointF(150, 80)).toPoint()
        QTest.mousePress(crop, QtCore.Qt.MouseButton.LeftButton, pos=center)
        QTest.mouseMove(crop, center + QtCore.QPoint(20, 10))
        QTest.mouseRelease(
            crop, QtCore.Qt.MouseButton.LeftButton, pos=center + QtCore.QPoint(20, 10)
        )
        self.assertEqual(crop.crop_rect(), QtCore.QRect(70, 40, 200, 100))
        corner = crop.image_to_widget(QtCore.QPointF(270, 140)).toPoint()
        QTest.mousePress(crop, QtCore.Qt.MouseButton.LeftButton, pos=corner)
        QTest.mouseMove(crop, corner + QtCore.QPoint(30, 20))
        QTest.mouseRelease(
            crop, QtCore.Qt.MouseButton.LeftButton, pos=corner + QtCore.QPoint(30, 20)
        )
        self.assertEqual(crop.crop_rect(), QtCore.QRect(70, 40, 230, 120))

    def test_dialog_commits_copy_only_on_accept_and_avatar_cancel_is_unchanged(self):
        dialog = self.show(ImageCropDialog(self.image, aspect_ratio=1))
        self.assertTrue(dialog.result_image().isNull())
        dialog.accept()
        self.assertFalse(dialog.result_image().isNull())
        self.assertEqual(dialog.result_image().width(), dialog.result_image().height())
        path = Path(self.temp.name) / "avatar.png"
        self.image.save(str(path))
        original = path.read_bytes()
        picker = self.show(AvatarPicker(self.image))
        with patch.object(
            ImageCropDialog, "exec", return_value=QtWidgets.QDialog.DialogCode.Rejected
        ):
            self.assertFalse(picker.select_file(path))
        self.assertEqual(picker.image().size(), self.image.size())
        self.assertEqual(path.read_bytes(), original)
        avatar = self.show(AvatarWidget(self.image))
        rendered = avatar.grab().toImage()
        self.assertEqual(rendered.pixelColor(0, 0).alpha(), 0)

    def test_magnifier_has_live_export_clamped_edges_and_signal_enable(self):
        view = self.show(ImageMagnifier(self.image))
        view.set_lens_size(QtCore.QSize(120, 90))
        view.set_zoom(3)
        exported = []
        view.regionChanged.connect(lambda image, rect: exported.append((image, rect)))
        view.set_anchor(QtCore.QPointF(399, 199))
        self.assertEqual(view.source_region(), QtCore.QRect(360, 170, 40, 30))
        self.assertEqual(view.region_image().size(), QtCore.QSize(40, 30))
        self.assertEqual(view.magnified_image().size(), QtCore.QSize(120, 90))
        self.assertEqual(view.region_image().pixelColor(0, 0).name(), "#0000ff")
        enabled = QtWidgets.QCheckBox()
        enabled.setChecked(True)
        enabled.toggled.connect(view.set_magnifier_enabled)
        enabled.setChecked(False)
        count = len(exported)
        view.set_anchor(QtCore.QPointF(20, 20))
        self.assertEqual(count, len(exported))
        enabled.setChecked(True)
        self.assertGreater(len(exported), count)
        for shape in ("circle", "rounded", "rectangle"):
            view.set_lens_shape(shape)
            self.assertFalse(view.grab().isNull())
        view.set_preview_rect(None)
        self.assertFalse(view.magnified_image().isNull())
        view.resize(600, 400)
        self.assertEqual(view.source_region(), QtCore.QRect(0, 5, 40, 30))
        view.clear()
        self.assertTrue(view.region_image().isNull())


if __name__ == "__main__":
    unittest.main()
