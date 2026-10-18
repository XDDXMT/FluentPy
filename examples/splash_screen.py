"""Startup-screen controls and a nonblocking, independently runnable demo."""
from __future__ import annotations

import argparse
from importlib import resources
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from fluentpy import (AccentButton, Button, CheckBox, FluentWindow, HeaderCardWidget,
                      LineEdit, SpinBox, SplashScreen, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets


def brand_icon():
    return QtGui.QIcon(str(resources.files('fluentpy.assets').joinpath('brand/fluentpy.svg')))


class SplashExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._window_splash = None
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._finish_preview)
        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        self.preview = QtWidgets.QFrame(self)
        self.preview.setObjectName('splashPreview')
        self.preview.setMinimumHeight(230)
        preview_layout = QtWidgets.QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(28, 28, 28, 28)
        preview_layout.addStretch()
        ready = QtWidgets.QLabel('界面已就绪', self.preview)
        ready.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(ready)
        self.retained_input = LineEdit('输入会在重播后保留', self.preview)
        preview_layout.addWidget(self.retained_input)
        preview_layout.addStretch()
        body.addWidget(self.preview)
        self.preview_splash = SplashScreen(brand_icon(), self.preview)
        self.preview_splash.show()

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(QtWidgets.QLabel('图标大小'))
        self.size_spin = SpinBox()
        self.size_spin.setRange(32, 160)
        self.size_spin.setSuffix(' px')
        self.size_spin.setValue(96)
        self.size_spin.setFixedWidth(112)
        self.size_spin.valueChanged.connect(self._configure)
        row.addWidget(self.size_spin)
        self.loading_check = CheckBox('显示加载提示')
        self.loading_check.toggled.connect(self._configure)
        row.addWidget(self.loading_check)
        row.addStretch()
        body.addLayout(row)
        self.text_edit = LineEdit('输入加载提示')
        self.text_edit.setText('正在准备界面…')
        self.text_edit.textChanged.connect(self._configure)
        self.text_edit.hide()
        body.addWidget(self.text_edit)
        buttons = QtWidgets.QHBoxLayout()
        self.replay_button = AccentButton('重播预览')
        self.replay_button.clicked.connect(self.replay)
        self.window_button = Button('全窗口预览')
        self.window_button.clicked.connect(self.preview_window)
        buttons.addWidget(self.replay_button)
        buttons.addWidget(self.window_button)
        buttons.addStretch()
        body.addLayout(buttons)
        self.result = QtWidgets.QLabel('图标居中显示；点击重播，约 1.5 秒后渐隐并显示原有内容。')
        self.result.setObjectName('muted')
        self.result.setWordWrap(True)
        body.addWidget(self.result)
        self._configure()
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _configure(self, *_):
        self.text_edit.setVisible(self.loading_check.isChecked())
        for splash in (self.preview_splash, self._window_splash):
            if splash is not None:
                splash.set_icon_size(self.size_spin.value())
                splash.set_loading(self.loading_check.isChecked())
                splash.set_text(self.text_edit.text() if self.loading_check.isChecked() else '')

    def _apply_theme(self):
        self.preview.setStyleSheet(f'QFrame#splashPreview {{background:{theme.tokens.surface};'
                                  f'border:1px solid {theme.tokens.border};border-radius:6px;}}')

    def replay(self):
        self._finish_window()
        self.preview_splash.show()
        self._timer.start(1500)
        self.result.setText('正在预览启动过程…')

    def preview_window(self):
        self._finish_window()
        self._window_splash = SplashScreen(brand_icon(), self.window())
        self._configure()
        self._window_splash.finished.connect(self._window_finished)
        self._window_splash.show()
        self._timer.start(1500)
        return self._window_splash

    def _window_finished(self):
        splash = self._window_splash
        self._window_splash = None
        if splash is not None:
            splash.deleteLater()

    def _finish_window(self):
        if self._window_splash is not None:
            self._window_splash.finish(animated=False)

    def _finish_preview(self):
        self.preview_splash.finish()
        if self._window_splash is not None:
            self._window_splash.finish()
        self.result.setText('启动完成。可以编辑内容，再次重播后输入仍会保留。')

    def hideEvent(self, event):
        self._timer.stop()
        self._finish_window()
        self.preview_splash.finish(animated=False)
        super().hideEvent(event)


class SplashDemo(FluentWindow):
    def __init__(self, *, dark=False):
        theme.set_mode('dark' if dark else 'light')
        super().__init__('FluentPy · 启动页面')
        self.setWindowIcon(brand_icon())
        self.set_title_bar_enabled(True)
        self.set_backdrop_enabled(True)
        self.set_theme_transition_enabled(True)
        self.resize(800, 680)
        self.setMinimumSize(520, 580)
        theme_button = Button('切换主题')
        theme_button.clicked.connect(theme.toggle)
        self.title_bar().button_layout.addWidget(theme_button)
        card = HeaderCardWidget('启动页面')
        self.examples = SplashExamples(card)
        card.body_layout.addWidget(self.examples)
        self.content_layout.addWidget(card)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    window = SplashDemo(dark=args.dark)
    window.show()
    QtCore.QTimer.singleShot(0, window.examples.preview_window)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
