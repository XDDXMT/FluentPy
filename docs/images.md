# 图像、头像与局部放大

这些接口自 0.8.0 起提供。工作台侧栏“图像与头像”和 `python examples/images.py` 可直接测试。

所有控件都是可独立加入 Qt 布局的 QWidget；图像解码、缩放、变换、裁剪与绘制由 Qt 完成。示例图片位于 `examples/assets/image-demo.png`，可替换为自己的本地图片。

## 图片与 GIF

```python
from fluentpy import ImageView, AvatarWidget, AvatarPicker

image = ImageView("photo.jpg", window)
image.set_fit_mode("contain")  # contain / cover / stretch
image.set_corner_radius(12)
window.content_layout.addWidget(image)

animation = ImageView("animation.gif", window)
animation.set_playing(True)
animation.frameChanged.connect(lambda frame: print(frame.size()))

avatar = AvatarWidget("photo.jpg", size=64)
picker = AvatarPicker(size=80, initials="FP")
picker.avatarChanged.connect(lambda cropped: cropped.save("my-avatar.png"))
```

`set_source` / `set_image` 接受本地路径、QImage 或 QPixmap。读取失败会抛出 ValueError，并保留原来的内容。`image()` 返回当前帧的 QImage 副本；`imageChanged` 通知更换图片，`frameChanged` 通知 GIF 帧变化。本地静态图片读取尊重 EXIF 方向。

GIF 在隐藏时暂停，显示后恢复；显式 `set_playing(False)` 会一直保持暂停。`movie()` 暴露底层 QMovie。图片尺寸是源像素尺寸，`image_rect()`、`image_to_widget()`、`widget_to_image()` 可用于自定义标注。

AvatarWidget 使用圆形裁切，图片为空时可显示 initials。AvatarPicker 支持点击、Enter、空格选择本地文件，随后打开正方形裁剪；取消不改变头像，也不覆盖源文件。`select_file(path)` 可由自己的文件选择流程调用，返回是否确认。`fileSelected(str)`、`avatarChanged(QImage)` 和 `selectionFailed(str)` 分别通知确认、结果和打开失败。开发者决定保存位置。

## 裁剪画布与对话框

```python
from fluentpy import ImageCropDialog, ImageCropper
from fluentpy.qt import QtCore, QtWidgets

crop = ImageCropper("photo.jpg")
crop.set_aspect_ratio(16 / 9)  # None 为自由比例
crop.set_crop_rect(QtCore.QRect(40, 30, 640, 360))
result = crop.cropped_image(QtCore.QSize(320, 180))

dialog = ImageCropDialog("photo.jpg", window, aspect_ratio=1)
if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
    result = dialog.result_image()
```

选区以源像素坐标表达，`cropChanged(QRect)` 提供实时通知。拖动选区可移动，拖动四角可调整范围，在选区外拖动可重新选择；方向键移动 1 像素，Shift+方向键移动 10 像素。选区始终限制在图片范围内。

`rotate(90)` / `rotate(-90)`、`flip(horizontal=True)`、`reset_crop()` 可接入自己的工具栏；变换后重新建立选区。画布固定使用 contain，保证四个控制点可见。`cropped_image()` 返回矩形裁剪副本，指定 QSize 时缩放到该尺寸。GIF 裁剪的是当前静态帧。

ImageCropDialog 暴露 `cropper` 和 `toolbar_layout`；只在确认时写入 `result_image()` 并发出 `imageCropped(QImage)`，取消不会提交结果。独立 ImageCropper 不依赖对话框或工作台。

## 放大镜与实时图像输出

```python
from fluentpy import ImageMagnifier, ImageView, CheckBox
from fluentpy.qt import QtCore

product = ImageMagnifier("product.png")
product.set_zoom(3)
product.set_lens_size(QtCore.QSize(240, 180))
product.set_lens_shape("circle")  # rectangle / rounded / circle
product.set_preview_rect(QtCore.QRect(16, 16, 180, 180))

toggle = CheckBox("启用放大镜")
toggle.setChecked(True)
toggle.toggled.connect(product.set_magnifier_enabled)

detail = ImageView()
product.magnifiedImageChanged.connect(detail.set_image)
product.regionChanged.connect(lambda image, rect: print("源区域", rect))
# 使用独立预览时，可关闭图片内部的预览框：
product.set_preview_rect(None)
product.set_anchor(QtCore.QPointF(120, 80))
```

鼠标悬停或键盘聚焦可显示观察区域；方向键与 Shift+方向键调整观察位置。`set_magnifier_enabled(bool)` 是公开 Qt slot，可直接连接信号。关闭后停止区域更新和放大绘制；重新启用会立即刷新。

`source_region()` 是当前源像素 QRect，`region_image()` 是未放大的裁剪图，`magnified_image()` 是缩放至 lens_size 的图；两个图像信号均输出独立 QImage 值。边缘处会平移观察区域，避免返回空白边。zoom 定义为输出像素与源像素的比例，改变控件尺寸不改变提取范围。

镜片形状作用于内置预览的绘制；输出图像保持矩形，便于保存、识别或接入自己的预览。`set_preview_rect(None)` 只隐藏内置预览，仍可获取和连接输出。使用较大的图片、镜片或高帧率 GIF 时，请结合实际设备测量开销；组件不做 Python 像素循环。
