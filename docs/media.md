# 音视频播放器

本页接口自 0.8.0 起提供。可运行 `python examples/media.py` 或打开工作台“音视频播放”。示例不会自动播放、下载文件或采集声音。

## 两种音频布局

```python
from fluentpy import AudioPlayer, CompactAudioPlayer, Button

compact = CompactAudioPlayer("music.wav")
full = AudioPlayer("music.wav")
full.set_seek_steps(backward=10, forward=30)
full.set_volume_control_visible(True)  # 在播放器显示后调用

download = Button("保存到播放列表")
full.trailing_layout.addWidget(download)
# 可继续添加自己的控件：
# full.leading_layout：左侧，默认音量按钮
# full.transport_layout：中间，默认后退 / 播放暂停 / 前进
# full.trailing_layout：右侧，默认留空

full.controller.play()
```

完整播放器显示进度条、当前与总时长，下方为左、中、右布局。CompactAudioPlayer 使用播放、进度、音量的一行布局，并保留右侧扩展区域。二者复用同一套 Slider 和按钮输入行为，支持键盘与焦点。公开属性包括 `timeline`、`play_button`、`volume_button`、`volume_slider`、完整布局的 `back_button`、`forward_button`、`position_label`、`duration_label`。

点击扬声器打开独立的音量浮层，显示微软扬声器图标、0–100 滑块和当前数值。打开浮层不会改变静音状态；拖动正音量会恢复声音，浮层内的扬声器按钮用于静音。按 Escape、点击外部或隐藏播放器会关闭浮层，不改变播放条布局。也可使用 `set_volume_control_visible()` 自己提供入口。进度根据真实媒体时长映射，无法跳转的媒体会禁用进度操作。

## 共享控制器与原生 Qt 接口

```python
from fluentpy import MediaController, AudioPlayer, CompactAudioPlayer
from fluentpy.qt import QtCore

media = MediaController(window)
media.set_source("music.wav")
full = AudioPlayer(controller=media)
mini = CompactAudioPlayer(controller=media)

media.positionChanged.connect(lambda milliseconds: print(milliseconds))
media.errorOccurred.connect(print)
media.set_volume(0.5)  # 0..1
media.set_muted(False)
media.set_playback_rate(1.25)
media.seek(30000)  # 毫秒，限制到有效时长
media.seek_by(-10000)
media.play()
media.pause()
media.stop()

native_player = media.player()  # QMediaPlayer
native_audio = media.audio_output()  # QAudioOutput
# 显式 QUrl 可以用于调用方自己的网络媒体：
# media.set_source(QtCore.QUrl("https://example.com/video.mp4"))
```

`source()`、`duration()`、`position()`、`is_playing()`、`is_seekable()` 提供当前状态。其他信号包括 `durationChanged`、`playingChanged`、`seekableChanged`、`sourceChanged`、`volumeChanged`、`mutedChanged`、`mediaStatusChanged`。时间值为整数毫秒；长录音不会被 Qt 的 32 位整数信号截断。`clear()` 停止并释放当前媒体源。

设置文件不会自动播放。导入 FluentPy、创建空控制器或空音频播放器不会导入 QtMultimedia；请求媒体源、原生播放器或视频输出时才加载。共享控制器由原有父对象持有，使用者应让它比连接的播放器存活更久。一个控制器只有一个活动的视频输出。

默认音频可在隐藏后继续播放；按需调用 `set_pause_on_hide(True)`。工作台为所有播放控件启用了隐藏暂停。

## 视频

```python
from fluentpy import VideoPlayer

video = VideoPlayer("movie.mp4", window)
window.content_layout.addWidget(video)
video.controls.set_seek_steps(10, 30)
video.controls.trailing_layout.addWidget(my_button)
video.controller.errorOccurred.connect(show_error)
video.controller.play()
```

`video_widget` 是 Qt 原生 QVideoWidget，保留长宽比；`controls` 是完整 AudioPlayer，`controller` 是实际播放控制器。`set_full_screen(True)` 使用 Qt 视频输出的全屏模式，双击视频切换，Escape 返回；全屏为视频画面，嵌入状态提供完整播放条。开发者可直接访问 `video_widget.videoSink()` 获取 Qt 解码帧。

实际格式、硬件解码和网络媒体支持由当前 Qt Multimedia 后端、Qt 版本及本机环境决定。PySide6 已提供多媒体模块；使用可选 PyQt6 绑定时需相应 QtMultimedia 模块。错误通过 `errorOccurred(str)` 传给应用，工作台在页面中显示。开发验证包含真实 WAV 播放/暂停/跳转、双控件状态同步，以及生成的 Motion JPEG AVI 解码帧；并不意味着所有格式和设备都已验证。

## 独立音量选择器

```python
from fluentpy import MediaController, VolumeControl, VolumeFlyout

media = MediaController(window)
inline_volume = VolumeControl(controller=media)
window.content_layout.addWidget(inline_volume)
flyout = VolumeFlyout(window, controller=media)
my_button.clicked.connect(lambda: flyout.popup(my_button))
```

`AudioPlayer.volume_flyout` 暴露此浮层，`volume_slider` 是其中的 Slider。`VolumeFlyout.control` 提供独立的 VolumeControl，内部的 `slider`、`mute_button`、`value_label` 均可访问。多个选择器连接同一个控制器时会保持数值、静音与图标同步。浮层使用 Qt.Popup，按屏幕可用范围放置，紧凑播放器作为小窗口使用时也可完整展开。

媒体按钮使用微软 Fluent UI System Icons 的原始 MIT SVG：PLAY、PAUSE、SKIP_BACK_10、SKIP_FORWARD_30、SPEAKER_1、SPEAKER_2、SPEAKER_MUTE 等。自定义跳转秒数若没有对应的数字图标，则显示通用微软旋转箭头，并在提示和无障碍名称中显示实际秒数。
