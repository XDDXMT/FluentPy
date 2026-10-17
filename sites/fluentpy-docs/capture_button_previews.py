"""Record actual Qt button/menu transitions, without desktop pointer capture."""
from __future__ import annotations

import json
import sys
import traceback

from capture_animations import (ROOT, SITE, SAMPLE_MS, QTest, QtCore, QtWidgets,
                               _capture_font, _image, _write_gif)
from PIL import ImageChops
from fluentpy import (ActionMenu, DropDownButton, AccentSplitButton, ToggleButton,
                      PillToggleButton, LoadingButton, FluentIcon, theme)


class Canvas(QtWidgets.QWidget):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.setObjectName('buttonCapture')
        self.setStyleSheet('QWidget#buttonCapture { background: #fafbfc; } QLabel { color: #626b77; background: transparent; }')
        self.setFixedSize(620, 220 if mode == 'states' else 300)
        self.caption = QtWidgets.QLabel('选择状态与任务反馈' if mode == 'states' else '默认动作与更多操作', self)
        self.caption.setGeometry(28, 18, 560, 28)
        if mode == 'states':
            self.toggle = ToggleButton('收藏', self)
            self.toggle.setGeometry(28, 60, 80, 32)
            self.all = PillToggleButton('全部', self)
            self.docs = PillToggleButton('文档', self)
            self.all.setGeometry(128, 60, 80, 32)
            self.docs.setGeometry(218, 60, 80, 32)
            self.group = QtWidgets.QButtonGroup(self)
            self.group.addButton(self.all); self.group.addButton(self.docs)
            self.all.setChecked(True)
            self.loading = LoadingButton('保存更改', self)
            self.loading.setGeometry(28, 124, 142, 32)
            self.tip = QtWidgets.QLabel('点击选择，平滑切换；加载时避免重复操作。', self)
            self.tip.setGeometry(28, 173, 560, 26)
        else:
            self.menu = ActionMenu(self)
            self.menu.add_action('JSON 配置', icon=FluentIcon.DOCUMENT_SAVE)
            self.menu.add_action('纯文本', icon=FluentIcon.ARROW_EXPORT)
            self.menu.add_separator()
            self.menu.add_action('包含说明', checkable=True, checked=True)
            self.menu.add_action('发布到云端（未连接）', enabled=False)
            self.drop = DropDownButton('导出为', self, menu=self.menu)
            self.drop.setGeometry(28, 60, 112, 32)
            self.split_menu = ActionMenu(self)
            self.split_menu.add_action('另存为…', icon=FluentIcon.DOCUMENT_SAVE)
            self.split_menu.add_action('保存副本', icon=FluentIcon.COPY)
            self.split = AccentSplitButton('保存', self, menu=self.split_menu)
            self.split.setGeometry(176, 60, 128, 32)
            self.tip = QtWidgets.QLabel('左侧执行保存，右侧展开更多操作。', self)
            self.tip.setGeometry(28, 260, 560, 26)


def record(app, mode):
    canvas = Canvas(mode)
    canvas.show()
    QTest.qWait(200)
    if app.focusWidget():
        app.focusWidget().clearFocus()
    frames, times, errors, actions = [], [], [], set()
    loop, timer, clock = QtCore.QEventLoop(), QtCore.QTimer(), QtCore.QElapsedTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.setInterval(SAMPLE_MS)
    old_hook = sys.excepthook
    sys.excepthook = lambda kind, error, tb: errors.append(''.join(traceback.format_exception(kind,error,tb)))
    poster = None

    def once(ms, at, name, callback):
        if ms >= at and name not in actions:
            callback(); actions.add(name)

    def click(widget):
        QTest.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton)
        widget.clearFocus()

    def tick():
        nonlocal poster
        try:
            ms = clock.elapsed()
            if ms >= 4000:
                timer.stop(); loop.quit(); return
            if mode == 'states':
                once(ms, 350, 'toggle-on', lambda: click(canvas.toggle))
                once(ms, 850, 'filter', lambda: click(canvas.docs))
                once(ms, 1350, 'loading', lambda: canvas.loading.set_loading(True, text='正在保存…'))
                once(ms, 2750, 'complete', lambda: canvas.loading.set_loading(False))
                once(ms, 3100, 'toggle-off', lambda: click(canvas.toggle))
                once(ms, 3300, 'reset', lambda: click(canvas.all))
            else:
                once(ms, 350, 'open', canvas.drop.show_menu)
                once(ms, 1100, 'select', lambda: QTest.keyClick(canvas.menu, QtCore.Qt.Key.Key_Down))
                once(ms, 1550, 'trigger', lambda: QTest.keyClick(canvas.menu, QtCore.Qt.Key.Key_Return))
                once(ms, 2000, 'default', lambda: click(canvas.split.main_button))
                once(ms, 2400, 'split-menu', canvas.split.show_menu)
                once(ms, 3100, 'dismiss', canvas.split_menu.dismiss)
                for menu in (canvas.menu, canvas.split_menu):
                    if menu.isVisible():
                        assert not menu.isWindow() and menu.windowHandle() is None
                if ms > 3400:
                    canvas.drop.clearFocus(); canvas.split.main_button.clearFocus()
                    canvas.split.menu_button.clearFocus()
            frame = _image(canvas)
            frames.append(frame); times.append(ms)
            if poster is None and ((mode == 'states' and 1900 <= ms < 2200) or (mode == 'menus' and 800 <= ms < 1000)):
                poster = frame.copy()
        except Exception:
            errors.append(traceback.format_exc()); timer.stop(); loop.quit()

    try:
        clock.start(); tick(); timer.timeout.connect(tick); timer.start(); loop.exec()
        assert not errors, errors
        assert len(actions) == 6, actions
        assert ImageChops.difference(frames[0], frames[-1]).getbbox() is None, f'{mode}: loop did not settle'
        output = SITE / 'dist/assets/previews'
        poster.save(output / f'button-{mode}-light.png', optimize=True)
        result = _write_gif(frames, times, output / f'button-{mode}-light.gif')
        result['actions'] = sorted(actions)
        return result
    finally:
        sys.excepthook = old_hook
        timer.stop(); canvas.close(); canvas.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    theme.set_mode('light')
    results = {mode: record(app, mode) for mode in ('states','menus')}
    (ROOT / 'build/button-capture-validation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:{a:b for a,b in v.items() if a != 'encoded_frame_durations_ms'} for k,v in results.items()},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
