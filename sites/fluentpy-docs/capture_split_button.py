"""Capture real two-line split actions, menu selection, and independent clicks."""
from __future__ import annotations

import sys
import traceback

from capture_animations import SITE, SAMPLE_MS, QTest, QtCore, QtGui, QtWidgets, _capture_font, _image, _write_gif
from fluentpy import ActionMenu, SplitButton, AccentSplitButton, theme


class Canvas(QtWidgets.QWidget):
    def __init__(self, mode):
        super().__init__()
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.setObjectName('splitButtonCapture')
        self.setFixedSize(640, 300)
        self.setStyleSheet(f'QWidget#splitButtonCapture {{ background: {theme.tokens.background}; }} '
                          f'QLabel {{ color: {theme.tokens.text_muted}; background: transparent; }}')
        self.caption = QtWidgets.QLabel('动作和选项，放在一起', self)
        self.caption.setGeometry(28, 16, 580, 28)
        self.menu = ActionMenu(self)
        self.launch = AccentSplitButton('启动游戏', self, menu=self.menu, description='1.0 · 正式版')
        self.launch.setGeometry(28, 60, 228, 52)
        choices = QtGui.QActionGroup(self.menu)
        choices.setExclusive(True)
        for version in ('1.0 · 正式版', '1.1 · 预览版', '本地开发版'):
            action = self.menu.add_action(version, checkable=True, checked=version.startswith('1.0'),
                callback=lambda _checked=False, value=version: self.select(value))
            choices.addAction(action)
        export_menu = ActionMenu(self)
        export_menu.add_action('PDF · 当前页面')
        export_menu.add_action('PNG · 当前页面')
        self.export = SplitButton('导出文档', self, menu=export_menu, description='PDF · 当前页面')
        self.export.setGeometry(278, 60, 228, 52)
        self.result = QtWidgets.QLabel('主区域执行操作，箭头选择选项。', self)
        self.result.setGeometry(28, 258, 585, 28)
        self.launch.clicked.connect(lambda: self.result.setText('执行主操作：启动 '+self.launch.description()))

    def select(self, version):
        self.launch.set_description(version)
        self.result.setText('已选择 '+version+'，点击主区域才会启动。')


def record(app, mode):
    theme.set_mode(mode)
    canvas = Canvas(mode)
    canvas.show()
    QTest.qWait(150)
    canvas.launch.main_button.clearFocus()
    frames, times, actions, errors = [], [], set(), []
    loop, timer, clock = QtCore.QEventLoop(), QtCore.QTimer(), QtCore.QElapsedTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.setInterval(SAMPLE_MS)
    previous_hook = sys.excepthook
    sys.excepthook = lambda kind, error, tb: errors.append(''.join(traceback.format_exception(kind, error, tb)))
    output = SITE / 'dist/assets/previews'
    output.mkdir(parents=True, exist_ok=True)

    def once(ms, at, name, callback):
        if ms >= at and name not in actions:
            actions.add(name)
            callback()

    def reset():
        canvas.menu.actions()[0].setChecked(True)
        canvas.launch.set_description('1.0 · 正式版')
        canvas.result.setText('主区域执行操作，箭头选择选项。')
        for button in (canvas.launch.main_button, canvas.launch.menu_button):
            button.clearFocus()
            button._reset_interaction()

    def tick():
        try:
            ms = clock.elapsed()
            if ms >= 4000:
                timer.stop()
                loop.quit()
                return
            once(ms, 400, 'press-main', lambda: QTest.mousePress(canvas.launch.main_button, QtCore.Qt.MouseButton.LeftButton))
            once(ms, 540, 'release-main', lambda: QTest.mouseRelease(canvas.launch.main_button, QtCore.Qt.MouseButton.LeftButton))
            once(ms, 1000, 'press-arrow', lambda: QTest.mousePress(canvas.launch.menu_button, QtCore.Qt.MouseButton.LeftButton))
            once(ms, 1140, 'release-arrow', lambda: QTest.mouseRelease(canvas.launch.menu_button, QtCore.Qt.MouseButton.LeftButton))
            once(ms, 1650, 'poster', lambda: _image(canvas).save(output / f'split-button-{mode}.png'))
            once(ms, 1950, 'next-version', lambda: QTest.keyClick(canvas.menu, QtCore.Qt.Key.Key_Down))
            once(ms, 2250, 'select-version', lambda: QTest.keyClick(canvas.menu, QtCore.Qt.Key.Key_Return))
            once(ms, 3000, 'press-selected', lambda: QTest.mousePress(canvas.launch.main_button, QtCore.Qt.MouseButton.LeftButton))
            once(ms, 3140, 'launch-selected', lambda: QTest.mouseRelease(canvas.launch.main_button, QtCore.Qt.MouseButton.LeftButton))
            once(ms, 3600, 'reset', reset)
            frames.append(_image(canvas))
            times.append(ms)
        except Exception:
            errors.append(traceback.format_exc())
            timer.stop()
            loop.quit()

    timer.timeout.connect(tick)
    clock.start()
    timer.start()
    loop.exec()
    sys.excepthook = previous_hook
    canvas.close()
    canvas.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    if errors:
        raise RuntimeError('\n'.join(errors))
    result = _write_gif(frames, times, output / f'split-button-{mode}.gif')
    print(f'{mode}: {len(frames)} captured frames, {result["encoded_duration_ms"]} ms')


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    for mode in ('light', 'dark'):
        record(app, mode)
