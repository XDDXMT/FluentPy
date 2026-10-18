"""Native Qt captures and boundary checks for the slider/menu playgrounds."""
import json
import os
from pathlib import Path
import sys
SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'examples'), str(SITE)]
os.environ['QT_QPA_PLATFORM'] = 'windows' if sys.platform == 'win32' else 'offscreen'
os.environ['QT_SCALE_FACTOR'] = '1'
from sliders import SliderDemo
from menus import MenuDemo
from showcase import Showcase
from capture_animations import _capture_font, _image
from capture_input_stack_previews import record, save_gif
from fluentpy import ActionMenu, RangeSlider, ToolTipSlider, theme
from fluentpy.qt import QtCore, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def settle(menu, app):
    menu._reveal.setCurrentTime(menu.SHOW_DURATION)
    for item in menu._items:
        if hasattr(item, '_selection_animation'):
            item._selection_animation.setCurrentTime(item._selection_animation.duration())
    anchor = menu.anchor_widget()
    if hasattr(anchor, '_arrow_animation'):
        anchor._arrow_animation.setCurrentTime(anchor._arrow_animation.duration())
    app.processEvents()


def save(owner, output, name, mode):
    assert owner.grab().save(str(output/f'{name}-{mode}.png'))


def open_context(play, app):
    QTest.mouseClick(play.context_target, QtCore.Qt.MouseButton.RightButton,
                     pos=QtCore.QPoint(24, 32))
    app.processEvents()


def capture(app, mode, output):
    checked = 0
    slider = SliderDemo(mode == 'dark')
    slider.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    slider.show()
    QTest.qWait(120)
    play = slider.examples
    save(slider, output, 'sliders-playground', mode)
    for name, kind, orientation in [('slider-horizontal', 0, 0), ('slider-vertical', 0, 1),
            ('slider-tooltip', 1, 0), ('slider-range', 2, 0), ('slider-range-vertical', 2, 1)]:
        play.kind.setCurrentIndex(kind)
        play.orientation.setCurrentIndex(orientation)
        app.processEvents()
        if kind == 1:
            play.preview.show_value_tip()
        QTest.qWait(200)
        save(slider, output, name, mode)
        checked += 1
    play.kind.setCurrentIndex(1)
    play.orientation.setCurrentIndex(0)
    app.processEvents()
    play.preview.hide_value_tip()
    poster = _image(slider)
    poster.save(output/f'slider-motion-{mode}.png')
    performed = set()
    def once(key, time, action, now):
        if now >= time and key not in performed:
            performed.add(key)
            action()
    def tick(now):
        widget = play.preview
        once('press', 250, lambda: QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(widget.value()).toPoint()), now)
        if 250 <= now < 1200:
            QTest.mouseMove(widget, widget._point_for_value(35+round((now-250)/950*40)).toPoint())
        once('release', 1250, lambda: QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(75).toPoint()), now)
        once('range', 1650, lambda: play.kind.setCurrentIndex(2), now)
        if 1900 <= now < 2850:
            play.preview.setValues(20, 60+round((now-1900)/950*30))
        once('vertical', 3000, lambda: play.orientation.setCurrentIndex(1), now)
        once('reset', 3600, lambda: (play.kind.setCurrentIndex(1), play.orientation.setCurrentIndex(0), play.value_input.setValue(35), play.preview.hide_value_tip()), now)
    frames, times = record(app, slider, 4200, tick)
    frames[0] = poster
    slider_gif = save_gif(frames, times, output/f'slider-motion-{mode}.gif', 4200)
    for width in (900, 560):
        slider.resize(width, 1100)
        app.processEvents()
        for kind in range(3):
            play.kind.setCurrentIndex(kind)
            for orientation in range(2):
                play.orientation.setCurrentIndex(orientation)
                app.processEvents()
                assert play.rect().contains(QtCore.QRect(play.preview.mapTo(play, QtCore.QPoint()), play.preview.size()))
                checked += 1
    slider.close()
    slider.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    menu_window = MenuDemo(mode == 'dark')
    menu_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    menu_window.show()
    QTest.qWait(100)
    play = menu_window.examples
    save(menu_window, output, 'menus-playground', mode)
    for kind, name in enumerate(('menus-submenu', 'menus-checkable', 'menus-widget', 'menus-context', 'menus-tray')):
        play.kind.setCurrentIndex(kind)
        app.processEvents()
        if kind == 4:
            play.menu.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
            open_context(play, app)
            app.processEvents()
            save(play.menu, output, name, mode)
            play.menu.hide()
        else:
            open_context(play, app)
            settle(play.menu, app)
            if kind == 0:
                play.menu._select(1)
                play.menu._open_active_submenu()
                settle(play.menu._child_menu, app)
                settle(play.menu, app)
                assert menu_window.rect().contains(play.menu._child_menu._surface.geometry())
            assert menu_window.rect().contains(play.menu._surface.geometry())
            assert play.menu._content.width() <= play.menu._scroll.viewport().width(), (mode, kind)
            save(menu_window, output, name, mode)
            play.menu.dismiss(immediate=True)
        checked += 1
    play.kind.setCurrentIndex(0)
    app.processEvents()
    poster = _image(menu_window)
    poster.save(output/f'menu-motion-{mode}.png')
    performed = set()
    def menu_tick(now):
        once('open', 300, lambda: open_context(play, app), now)
        once('child', 900, lambda: (play.menu._select(1), play.menu._open_active_submenu()), now)
        once('select', 1500, lambda: play.menu._child_menu._activate(play.menu._child_menu.actions()[0]), now)
        once('mixed', 2050, lambda: (play.kind.setCurrentIndex(2), open_context(play, app)), now)
        once('typing', 2600, lambda: play.widget_input.setText('FluentPy'), now)
        if 2800 <= now < 3400:
            play.widget_slider.setValue(75+round((now-2800)/600*50))
        once('dismiss', 3600, lambda: play.menu.dismiss(), now)
        once('reset', 3900, lambda: play.kind.setCurrentIndex(0), now)
    frames, times = record(app, menu_window, 4400, menu_tick)
    frames[0] = poster
    menu_gif = save_gif(frames, times, output/f'menu-motion-{mode}.gif', 4400)
    menu_window.close()
    menu_window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    workbench = Showcase(dark=mode == 'dark', restore_preferences=False, startup=False)
    workbench.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    workbench.resize(900, 650)
    workbench.show()
    for route in ('buttons', 'sliders'):
        workbench.set_page(route, animated=False)
        app.processEvents()
        scroll = workbench.stack.currentWidget()
        assert scroll.widget().width() <= scroll.viewport().width()
        checked += 1
    assert workbench.menu_examples.tray_icon is None
    workbench.close()
    workbench.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    return {'mode': mode, 'bounds_checked': checked, 'animations': [slider_gif, menu_gif]}


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    errors = []
    def error(kind, value, tb):
        errors.append(str(value))
        sys.__excepthook__(kind, value, tb)
    sys.excepthook = error
    results = [capture(app, mode, SITE/'dist/assets/previews') for mode in ('light', 'dark')]
    assert not errors, errors
    print(json.dumps({'captures': results, 'errors': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
