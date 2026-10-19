"""Shared native Qt layout for focused component examples."""

from fluentpy import FluentWindow, HeaderCardWidget, ToggleSwitch, theme
from fluentpy.qt import QtWidgets


class Playground(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(14)
        self.columns = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
        self.columns.setSpacing(18)
        self.body.addLayout(self.columns)
        self.canvas = QtWidgets.QFrame()
        self.canvas.setObjectName("componentPlaygroundCanvas")
        self.canvas.setMinimumHeight(320)
        self.preview_layout = QtWidgets.QVBoxLayout(self.canvas)
        self.preview_layout.setContentsMargins(24, 20, 24, 20)
        self.preview_layout.setSpacing(18)
        self.columns.addWidget(self.canvas, 1)
        self.controls = QtWidgets.QWidget()
        self.form = QtWidgets.QVBoxLayout(self.controls)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setSpacing(9)
        self.columns.addWidget(self.controls)
        self.result = QtWidgets.QLabel()
        self.result.setWordWrap(True)
        self.body.addWidget(self.result)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def field(self, text, widget):
        caption = QtWidgets.QLabel(text)
        self.form.addWidget(caption)
        self.form.addWidget(widget)
        return caption

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= 620
        self.columns.setDirection(
            QtWidgets.QBoxLayout.Direction.LeftToRight
            if wide
            else QtWidgets.QBoxLayout.Direction.TopToBottom
        )
        self.controls.setMinimumWidth(240 if wide else 0)
        self.controls.setMaximumWidth(240 if wide else 16777215)

    def _apply_theme(self):
        dark = theme.mode.value == "dark"
        self.setStyleSheet(
            f"QFrame#componentPlaygroundCanvas {{background:{'#242e39' if dark else '#edf7f8'};border:1px solid {theme.tokens.border};border-radius:8px;}}"
        )
        self.result.setStyleSheet(f"color:{theme.tokens.text_muted};background:transparent;")


class PlaygroundWindow(FluentWindow):
    def __init__(self, title, example_type, *, dark=False):
        theme.set_mode("dark" if dark else "light")
        super().__init__("FluentPy · " + title)
        self.resize(900, 660)
        self.setMinimumSize(560, 580)
        self.content_layout.setContentsMargins(28, 24, 28, 24)
        row = QtWidgets.QHBoxLayout()
        heading = QtWidgets.QLabel(title)
        heading.setStyleSheet("font-size:24px;font-weight:600;")
        row.addWidget(heading)
        row.addStretch()
        row.addWidget(QtWidgets.QLabel("深色"))
        toggle = ToggleSwitch()
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        row.addWidget(toggle)
        self.content_layout.addLayout(row)
        card = HeaderCardWidget("修改参数，直接体验")
        self.examples = example_type()
        card.body_layout.addWidget(self.examples)
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
