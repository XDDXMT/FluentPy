"""Documentation for independently usable image and multimedia controls."""


def build_media_image_pages(page, section):
    development = "自 FluentPy 0.8.0 起提供，可从组件库独立导入使用。"
    pages = [
        page(
            "images",
            "图像与头像",
            "Images",
            "图像与媒体",
            "显示图片 / GIF，选择头像，裁剪图像并输出放大镜的实时区域。" + development,
            [
                "ImageView",
                "AvatarWidget",
                "AvatarPicker",
                "ImageCropper",
                "ImageCropDialog",
                "ImageMagnifier",
            ],
            [
                section(
                    "display",
                    "图片、GIF 与圆形头像",
                    "图片保留长宽比，支持 contain / cover / stretch；GIF 使用 QMovie，隐藏时暂停。头像使用圆形裁切。点击 AvatarPicker 可选择本地图片并确认裁剪，取消保留原头像，不覆盖源文件。",
                    """from fluentpy import ImageView, AvatarWidget, AvatarPicker

image = ImageView("photo.jpg")
image.set_fit_mode("cover")
image.set_corner_radius(12)
animation = ImageView("animation.gif")
animation.frameChanged.connect(lambda frame: print(frame.size()))
avatar = AvatarWidget("photo.jpg", size=64)
picker = AvatarPicker(size=80, initials="FP")
picker.avatarChanged.connect(lambda image: image.save("my-avatar.png"))""",
                    "images-display",
                ),
                section(
                    "crop",
                    "独立裁剪画布与确认对话框",
                    "拖动四角调整选区，拖动内部移动。方向键移动 1 像素，Shift+方向键移动 10 像素。源像素坐标不随控件尺寸变化。旋转、镜像、比例和输出大小均可由应用控制。",
                    """from fluentpy import ImageCropper, ImageCropDialog
from fluentpy.qt import QtCore, QtWidgets

crop = ImageCropper("photo.jpg")
crop.set_aspect_ratio(16 / 9)  # None 为自由比例
crop.cropChanged.connect(lambda rect: print(rect))
result = crop.cropped_image(QtCore.QSize(320, 180))

dialog = ImageCropDialog("photo.jpg", window, aspect_ratio=1)
if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
    result = dialog.result_image()
# dialog.cropper 与 dialog.toolbar_layout 可继续扩展""",
                    "images-crop",
                ),
                section(
                    "magnifier",
                    "商品式放大镜与图像输出",
                    "鼠标悬停或键盘聚焦观察细节。公开 slot 可连接任意 bool 信号；原区域、源坐标和放大后图像均可读取或订阅。支持矩形、圆角、圆形镜片，也可将预览放在独立区域。",
                    """from fluentpy import ImageMagnifier, ImageView, CheckBox
from fluentpy.qt import QtCore

product = ImageMagnifier("product.png")
product.set_zoom(3)
product.set_lens_size(QtCore.QSize(240, 180))
product.set_lens_shape("circle")
enabled = CheckBox("启用放大镜")
enabled.setChecked(True)
enabled.toggled.connect(product.set_magnifier_enabled)

detail = ImageView()
product.set_preview_rect(None)  # 仅隐藏内置预览
product.magnifiedImageChanged.connect(detail.set_image)
product.regionChanged.connect(lambda image, rect: print(rect))
product.set_anchor(QtCore.QPointF(120, 80))
original_crop = product.region_image()
enlarged = product.magnified_image()""",
                    "images-magnifier",
                    note="zoom 为输出像素 / 源像素。镜片形状影响内置预览，导出的 QImage 保持矩形，便于保存与处理。图像操作由 Qt 完成。",
                ),
            ],
            catalogDescription="图片 / GIF、圆形头像、裁剪与可输出区域的放大镜。",
        ),
        page(
            "media",
            "音视频播放",
            "Media players",
            "图像与媒体",
            "真实 Qt 多媒体播放，紧凑与完整音频条、视频输出和可扩展控制布局。" + development,
            [
                "MediaController",
                "AudioPlayer",
                "CompactAudioPlayer",
                "VideoPlayer",
                "VolumeControl",
                "VolumeFlyout",
            ],
            [
                section(
                    "audio",
                    "两种音频播放器",
                    "紧凑条适合列表与附件；完整条提供时间、后退与前进。leading_layout、transport_layout、trailing_layout 为左、中、右三个公开布局，开发者可放置自己的操作。设置源文件不会自动播放。点击扬声器打开音量浮层，显示滑块与当前数值；浮层内的扬声器用于静音。按 Escape 或点击外部关闭，不挤动原有布局。",
                    """from fluentpy import AudioPlayer, CompactAudioPlayer, Button

mini = CompactAudioPlayer("music.wav")
player = AudioPlayer("music.wav")
player.set_seek_steps(backward=10, forward=30)
player.set_volume_control_visible(True)
extra = Button("加入播放列表")
player.trailing_layout.addWidget(extra)
player.controller.play()""",
                    "media-audio",
                ),
                section(
                    "volume",
                    "点击扬声器调整音量",
                    "独立音量浮层提供微软扬声器图标、0–100 滑块与当前数值。点击播放器的扬声器只打开选择器，浮层内的扬声器用于静音；方向键可调整音量，Escape 或点击外部关闭。",
                    """from fluentpy import VolumeControl, VolumeFlyout, MediaController

media = MediaController(window)
volume = VolumeControl(controller=media)
window.content_layout.addWidget(volume)
flyout = VolumeFlyout(window, controller=media)
my_button.clicked.connect(lambda: flyout.popup(my_button))
# 播放器内置：player.volume_flyout / player.volume_slider""",
                    "media-volume",
                ),
                section(
                    "controller",
                    "共用状态，也能直接使用 Qt",
                    "一个控制器可以连接多个播放条。导入 FluentPy 和创建空音频条不会加载多媒体模块；请求源文件或视频输出时才加载。共享控制器应比它连接的播放条存活更久。",
                    """from fluentpy import MediaController, AudioPlayer, CompactAudioPlayer

media = MediaController(window)
full = AudioPlayer(controller=media)
mini = CompactAudioPlayer(controller=media)
media.set_source("music.wav")
media.errorOccurred.connect(show_error)
media.positionChanged.connect(lambda ms: print(ms))
media.set_volume(0.5)
media.set_muted(False)
# 媒体加载且 is_seekable() 后：
media.seek(30000)
media.seek_by(-10000)
media.play()
native_player = media.player()       # QMediaPlayer
native_audio = media.audio_output()  # QAudioOutput""",
                ),
                section(
                    "video",
                    "视频与原生输出",
                    "QVideoWidget 保留视频比例，controls 复用完整音频播放条。全屏使用 Qt 视频窗口，双击切换，Escape 返回；全屏显示视频画面，嵌入状态提供完整播放条。",
                    """from fluentpy import VideoPlayer

video = VideoPlayer("movie.mp4", window)
window.content_layout.addWidget(video)
video.controls.set_seek_steps(10, 30)
video.controls.trailing_layout.addWidget(my_action)
video.controller.errorOccurred.connect(show_error)
video.controller.play()
# video.video_widget.videoSink() 提供真实解码帧
# video.set_pause_on_hide(True) 可选择隐藏时暂停""",
                    "media-video",
                    note="文件格式、硬件解码和网络媒体支持取决于实际 Qt 后端与设备。已验证真实 WAV 播放、暂停与跳转，以及生成的 Motion JPEG AVI 解码；不代表所有格式均已验证。",
                ),
            ],
            catalogDescription="紧凑 / 完整音频条、视频输出与可扩展控制布局。",
        ),
    ]
    for entry in pages:
        for item in entry["sections"]:
            item["requiresUserFiles"] = True
    return pages
