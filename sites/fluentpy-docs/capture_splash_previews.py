"""Record our startup surface on hidden native Qt windows, never the desktop."""
from __future__ import annotations

import json
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples'), str(SITE)]
from capture_animations import _capture_font, _image
from capture_input_stack_previews import record, save_gif
from splash_screen import SplashDemo, brand_icon
from fluentpy import Button, FluentWindow, LineEdit, SplashScreen, theme
from fluentpy.qt import QtCore, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def dispose(app, widget):
    widget.close()
    widget.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()


def capture(app, mode, output):
    theme.set_mode(mode)
    host = FluentWindow('FluentPy · 启动页面')
    host.set_title_bar_enabled(True)
    host.setWindowIcon(brand_icon())
    host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    host.resize(720, 480)
    title = QtWidgets.QLabel('界面已就绪')
    title.setStyleSheet('font-size:22px;font-weight:600;')
    host.content_layout.addWidget(title)
    field = LineEdit()
    field.setText('启动前的输入会保留')
    host.content_layout.addWidget(field)
    host.content_layout.addWidget(Button('继续工作'))
    host.content_layout.addStretch()
    top_levels_before = set(app.topLevelWidgets())
    splash = SplashScreen(brand_icon(), host)
    splash.set_icon_size(102)
    host.show()
    splash.show()
    QTest.qWait(180)
    poster = _image(host)
    poster.save(output / f'splash-screen-{mode}.png')
    assert splash.y() == host.title_bar().height() == 48
    assert all(control.isHidden() for control in (host.title_bar().back_button,
               host.title_bar().forward_button, host.title_bar().icon_label,
               host.title_bar().title_label, host.title_bar()._content, host.title_bar()._actions))
    assert all(control.isVisible() for control in (host.title_bar().minimize_button,
               host.title_bar().maximize_button, host.title_bar().close_button))
    assert not splash.isWindow() and not splash.testAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow)
    logo, _, _ = splash._content_rects()
    assert logo.center() == QtCore.QRectF(splash.rect()).center()
    splash.set_loading(True)
    splash.set_text('正在准备界面…')
    QTest.qWait(80)
    _image(host).save(output / f'splash-loading-{mode}.png')
    splash.set_loading(False)
    splash.set_text('')
    performed, middle, complete = set(), [], []
    def once(key, at, action, now):
        if now >= at and key not in performed:
            performed.add(key)
            action()
    def loading():
        splash.set_text('正在准备界面…')
        splash.set_loading(True)
    def ready():
        assert splash.isHidden()
        assert not splash._input_filter_installed
        assert splash._spinner.state() == QtCore.QAbstractAnimation.State.Stopped
        assert field.text() == '启动前的输入会保留'
        assert host.title_bar().title_label.isVisible()
        assert host.title_bar().icon_label.isVisible()
        field.setFocus()
        QTest.keyClicks(field, ' OK')
        assert field.text().endswith(' OK')
        complete.append(True)
    def reset():
        field.setText('启动前的输入会保留')
        splash.set_loading(False)
        splash.set_text('')
        splash.show()
    def tick(now):
        once('loading', 350, loading, now)
        once('status', 1100, lambda: splash.set_text('界面准备完成，即将打开…'), now)
        once('finish', 1800, splash.finish, now)
        once('ready', 2300, ready, now)
        once('reset', 3200, reset, now)
    def sample(widget):
        image = _image(widget)
        if splash._finishing and 0 < splash._opacity < 1:
            assert image.getbbox() is not None
            middle.append(splash._opacity)
        return image
    frames, times = record(app, host, 4000, tick, capture=sample)
    assert len(performed) == 5 and complete and middle, (performed, complete, middle)
    frames.insert(0, poster)
    times.insert(0, 0)
    report = save_gif(frames, times, output / f'splash-motion-{mode}.gif', 4000, stable_corner=False)
    poster.save(output / f'splash-motion-{mode}.png')
    bounds = 0
    for width, height in ((480, 320), (720, 480), (900, 650)):
        host.resize(width, height)
        for size in (32, 96, 160):
            for loading_enabled in (False, True):
                splash.set_icon_size(size)
                splash.set_loading(loading_enabled)
                splash.set_text('自定义加载提示' if loading_enabled else '')
                app.processEvents()
                for rect in splash._content_rects():
                    assert rect.isEmpty() or QtCore.QRectF(splash.rect()).contains(rect), rect
                bounds += 1
    extra_windows = set(app.topLevelWidgets()) - top_levels_before
    assert not extra_windows, extra_windows
    dispose(app, host)
    demo = SplashDemo(dark=mode == 'dark')
    demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    demo.show()
    QTest.qWait(180)
    _image(demo).save(output / f'splash-demo-{mode}.png')
    dispose(app, demo)
    return {**report, 'mode': mode, 'bounds': bounds, 'natural_fade_frames': len(middle),
            'input_retained': True, 'extra_windows': len(extra_windows)}


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    errors = []
    def report_error(kind, error, tb):
        errors.append(str(error))
        sys.__excepthook__(kind, error, tb)
    sys.excepthook = report_error
    output = SITE / 'dist/assets/previews'
    output.mkdir(parents=True, exist_ok=True)
    results = [capture(app, mode, output) for mode in ('light', 'dark')]
    assert not errors, errors
    print(json.dumps({'captures': results, 'errors': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
