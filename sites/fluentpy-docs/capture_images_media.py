"""Capture the real image, media and multilingual Qt controls off the desktop."""

import sys
import tempfile
import time
import wave
from pathlib import Path

from capture_animations import ROOT, SITE, QtCore, QTest, QtWidgets, _capture_font, _image

sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "tests"))

from images import sample_image
from media_fixtures import video_fixture

from fluentpy import (
    AudioPlayer,
    AvatarPicker,
    AvatarWidget,
    CodeEdit,
    CompactAudioPlayer,
    ImageCropDialog,
    ImageMagnifier,
    ImageView,
    MediaController,
    VideoPlayer,
    theme,
)


def canvas(title, width=960, height=560):
    root = QtWidgets.QWidget()
    root.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    root.setObjectName("captureCanvas")
    root.setStyleSheet(
        f"QWidget#captureCanvas {{background:{theme.tokens.background};}}"
        f"QLabel {{color:{theme.tokens.text};background:transparent;}}"
    )
    root.setFont(_capture_font())
    root.setFixedSize(width, height)
    body = QtWidgets.QVBoxLayout(root)
    body.setContentsMargins(24, 20, 24, 24)
    body.setSpacing(16)
    label = QtWidgets.QLabel(title)
    font = label.font()
    font.setPixelSize(20)
    font.setBold(True)
    label.setFont(font)
    body.addWidget(label)
    return root, body


def save(root, name, mode):
    root.show()
    QTest.qWait(160)
    path = SITE / "dist/assets/previews" / f"{name}-{mode}.png"
    _image(root).save(str(path))
    if not path.is_file():
        raise RuntimeError(f"failed to save {path}")
    root.close()
    root.deleteLater()
    QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def wait_for(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(25)
    if not predicate():
        raise RuntimeError("Qt multimedia did not load the generated capture fixture")


def main():
    app = QtWidgets.QApplication([])
    app.setFont(_capture_font())
    source = sample_image()
    with tempfile.TemporaryDirectory() as temporary:
        audio = Path(temporary) / "silence.wav"
        with wave.open(str(audio), "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            output.writeframes(b"\0\0" * 16000 * 4)
        video = video_fixture(Path(temporary) / "original.avi", source=source)
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            root, body = canvas("图像与头像 · 本地图片与 GIF", 960, 480)
            display = ImageView(source)
            body.addWidget(display, 1)
            row = QtWidgets.QHBoxLayout()
            for widget in (
                AvatarWidget(source, size=64),
                AvatarWidget(size=64, initials="FP"),
                AvatarPicker(source, size=64),
            ):
                row.addWidget(widget)
            row.addWidget(QtWidgets.QLabel("圆形头像 / 文字占位 / 点击选择并裁剪"), 1)
            body.addLayout(row)
            save(root, "images-display", mode)

            dialog = ImageCropDialog(source)
            dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
            dialog.setFixedSize(960, 620)
            dialog.show()
            QTest.qWait(120)
            _image(dialog).save(str(SITE / "dist/assets/previews" / f"images-crop-{mode}.png"))
            dialog.close()
            dialog.deleteLater()

            root, body = canvas("局部放大 · 源区域与独立输出", 960, 470)
            row = QtWidgets.QHBoxLayout()
            magnifier = ImageMagnifier(source)
            magnifier.set_preview_rect(None)
            output = ImageView()
            output.setFixedSize(260, 200)
            magnifier.set_lens_size(QtCore.QSize(260, 200))
            magnifier.magnifiedImageChanged.connect(output.set_image)
            magnifier.set_anchor(QtCore.QPointF(270, 180))
            row.addWidget(magnifier, 1)
            row.addWidget(output)
            body.addLayout(row, 1)
            body.addWidget(QtWidgets.QLabel("镜片、倍率、区域位置和外部预览均可由公开接口控制。"))
            save(root, "images-magnifier", mode)

            root, body = canvas("音频 · 紧凑条 / 完整条", 960, 340)
            media = MediaController(root)
            media.set_muted(False)
            compact = CompactAudioPlayer(controller=media)
            full = AudioPlayer(controller=media)
            full.trailing_layout.addWidget(QtWidgets.QLabel("自定义区域"))
            body.addWidget(compact)
            body.addWidget(full)
            body.addStretch()
            media.set_source(audio)
            wait_for(lambda: media.duration() > 0)
            media.seek(2000)
            root.show()
            QTest.qWait(160)
            full.volume_button.click()
            QTest.qWait(180)
            full.volume_flyout.grab().save(
                str(SITE / "dist/assets/previews" / f"media-volume-{mode}.png")
            )
            full.volume_flyout.dismiss()
            save(root, "media-audio", mode)

            root, body = canvas("视频 · Qt 原生输出与播放控制", 960, 620)
            player = VideoPlayer(parent=root)
            player.controller.set_muted(False)
            # QVideoWidget uses a separate native rendering surface that cannot
            # be grabbed from a hidden QWidget. Render its actual decoded frames
            # through the public videoSink signal and retain its real controls.
            decoded = ImageView()
            decoded.set_background("#000000")
            decoded.set_corner_radius(8)
            player.video_widget.videoSink().videoFrameChanged.connect(
                lambda frame, target=decoded: (
                    target.set_image(frame.toImage()) if frame.isValid() else None
                )
            )
            body.addWidget(decoded, 1)
            body.addWidget(player.controls)
            body.addWidget(
                QtWidgets.QLabel(
                    "公开 videoSink() 导出的真实解码帧与原播放条；原生视频表面单独渲染。"
                )
            )
            player.hide()
            player.set_source(video)
            wait_for(lambda: player.controller.duration() > 0)
            player.controller.play()
            wait_for(lambda: player.controller.position() > 300)
            player.controller.pause()
            save(root, "media-video", mode)

            root, body = canvas("代码编辑器 · 可选择语言与自定义分词器", 960, 460)
            editor = CodeEdit(language="python")
            editor.set_code("""from fluentpy import ImageMagnifier, ImageView
from fluentpy.qt import QtCore

# 同一份文档，可以切换语言，也可以接入自己的高亮器。
product = ImageMagnifier("product.png")
product.set_zoom(3)
product.set_lens_size(QtCore.QSize(240, 180))
preview = ImageView()
product.magnifiedImageChanged.connect(preview.set_image)
""")
            body.addWidget(editor, 1)
            save(root, "code-editor-languages", mode)
    print("Captured image, crop, magnifier, real media and multi-language Qt controls.")


if __name__ == "__main__":
    main()
