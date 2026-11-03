"""Real local-media playback. No automatic playback or remote downloads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fluentpy import AudioPlayer, Button, CompactAudioPlayer, HeaderCardWidget, VideoPlayer
from fluentpy.qt import QtWidgets


class MediaExamples(QtWidgets.QWidget):
    """Initialize multimedia only when this page is actually shown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(16)
        self._built = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._built:
            try:
                self._build()
            except ImportError as error:
                self.status.setText(f"当前 Qt 绑定未提供多媒体模块：{error}")

    def _build(self):
        self._built = True
        self.status = QtWidgets.QLabel(
            "打开本地文件后点击播放；切换工作台页面会暂停。点击扬声器可打开音量选择器。"
        )
        self.status.setWordWrap(True)
        self.body.addWidget(self.status)
        self.players = []
        for title, cls in (
            ("紧凑音频", CompactAudioPlayer),
            ("完整音频 · 左 / 中 / 右布局", AudioPlayer),
            ("视频", VideoPlayer),
        ):
            panel = HeaderCardWidget(title)
            player = cls()
            player.set_pause_on_hide(True)
            if isinstance(player, VideoPlayer):
                player.setFixedHeight(360)
            choose = Button("打开视频" if cls == VideoPlayer else "打开音频")
            choose.clicked.connect(lambda _checked=False, target=player: self._choose(target))
            row = QtWidgets.QHBoxLayout()
            row.addWidget(choose)
            row.addStretch()
            panel.body_layout.addLayout(row)
            panel.body_layout.addWidget(player)
            player.controller.errorOccurred.connect(self.status.setText)
            self.body.addWidget(panel)
            self.players.append(player)

    def _choose(self, player):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择本地媒体",
            "",
            "媒体 (*.mp3 *.wav *.flac *.ogg *.m4a *.mp4 *.mkv *.avi *.webm);;所有文件 (*)",
        )
        if not path:
            return
        try:
            player.set_source(path)
            self.status.setText(
                f"已选择 {Path(path).name}，点击播放。格式支持取决于当前 Qt 多媒体后端。"
            )
        except (ValueError, ImportError) as exc:
            self.status.setText(str(exc))

    def hideEvent(self, event):
        for player in getattr(self, "players", ()):
            player.controller.pause()
        super().hideEvent(event)


if __name__ == "__main__":
    from fluentpy import FluentWindow

    app = QtWidgets.QApplication(sys.argv)
    window = FluentWindow("FluentPy · 音视频")
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(MediaExamples())
    window.content_layout.addWidget(scroll)
    window.resize(1000, 850)
    window.show()
    sys.exit(app.exec())
