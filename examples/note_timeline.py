"""NoteTimeline demo: a silent cursor driven by a Qt timer."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fluentpy import (  # noqa: E402
    AccentButton,
    Button,
    Card,
    ComboBox,
    FluentWindow,
    NoteEvent,
    NoteTimeline,
    ToggleSwitch,
    theme,
)
from fluentpy.qt import QtCore, QtWidgets  # noqa: E402


def make_notes(multiple_tracks: bool = False) -> list[NoteEvent]:
    """A short original phrase; no music file or audio dependency is needed."""
    pitches = (60, 64, 67, 65, 62, 64, 69, 67, 64, 62, 60, 64, 62, 60)
    notes = [NoteEvent(index * 0.5, 0.35, pitch) for index, pitch in enumerate(pitches)]
    if multiple_tracks:
        notes.extend(
            NoteEvent(index * 1.0, 0.75, pitch, track=1)
            for index, pitch in enumerate((48, 55, 50, 57, 52, 55, 48))
        )
    return notes


class NoteTimelineDemo(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        description = QtWidgets.QLabel("横向查看音符、时值和多轨分布。演示只移动游标，不播放声音。")
        description.setWordWrap(True)
        description.setObjectName("muted")
        layout.addWidget(description)

        self.source = ComboBox()
        self.source.addItems(["单轨短句", "双轨短句", "空状态"])
        self.source.setMinimumWidth(150)
        self.start_button = AccentButton("演示进度")
        self.reset_button = Button("回到开头")
        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(self.source)
        controls.addWidget(self.start_button)
        controls.addWidget(self.reset_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        card = Card()
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        self.timeline = NoteTimeline()
        self.timeline.setMinimumHeight(100)
        self.timeline.set_empty_text("选择单轨或双轨短句以显示音符")
        card_layout.addWidget(self.timeline)
        layout.addWidget(card)

        self.position_label = QtWidgets.QLabel()
        self.position_label.setObjectName("muted")
        layout.addWidget(self.position_label)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(30)
        self._elapsed = QtCore.QElapsedTimer()
        self._start_position = 0.0
        self._timer.timeout.connect(self._advance)
        self.timeline.positionChanged.connect(self._update_position)
        self.source.currentIndexChanged.connect(self._load_notes)
        self.start_button.clicked.connect(self._toggle_progress)
        self.reset_button.clicked.connect(self._reset)
        self._load_notes(0)

    def _load_notes(self, index: int) -> None:
        self._stop()
        if index == 2:
            self.timeline.clear()
        else:
            self.timeline.set_notes(make_notes(multiple_tracks=index == 1), duration=7.5)
        self.start_button.setEnabled(bool(self.timeline.notes()))
        self._update_position()

    def _toggle_progress(self) -> None:
        if self._timer.isActive():
            self._stop()
            return
        if self.timeline.position() >= self.timeline.duration():
            self.timeline.set_position(0.0)
        self._start_position = self.timeline.position()
        self._elapsed.start()
        self._timer.start()
        self.start_button.setText("暂停演示")

    def _advance(self) -> None:
        self.timeline.set_position(self._start_position + self._elapsed.elapsed() / 1000)
        if self.timeline.position() >= self.timeline.duration():
            self._stop()

    def _stop(self) -> None:
        self._timer.stop()
        self.start_button.setText("演示进度")

    def _reset(self) -> None:
        self._stop()
        self.timeline.set_position(0.0)

    def _update_position(self, _position: float = 0.0) -> None:
        self.position_label.setText(
            f"{len(self.timeline.notes())} 个音符 · "
            f"{self.timeline.position():.1f} / {self.timeline.duration():.1f} 秒"
        )


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    theme.set_mode("light")
    window = FluentWindow("NoteTimeline · 音符时间轴")
    window.resize(900, 430)
    window.content_layout.setContentsMargins(28, 20, 28, 24)

    dark_mode = ToggleSwitch()
    dark_mode.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
    header = QtWidgets.QHBoxLayout()
    header.addWidget(QtWidgets.QLabel("NoteTimeline"))
    header.addStretch(1)
    header.addWidget(QtWidgets.QLabel("深色模式"))
    header.addWidget(dark_mode)
    window.content_layout.addLayout(header)
    window.content_layout.addWidget(NoteTimelineDemo())
    window.content_layout.addStretch(1)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
