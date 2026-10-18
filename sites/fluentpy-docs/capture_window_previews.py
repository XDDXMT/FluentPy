"""Capture the real FluentWindow demo; no desktop or reference assets are used."""
import json
import io
import os
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples'), str(SITE)]
os.environ['QT_QPA_PLATFORM'] = 'windows' if sys.platform == 'win32' else 'offscreen'
os.environ['QT_SCALE_FACTOR'] = '1'

from fluent_window import WindowDemo, MODES
from showcase import Showcase
from capture_animations import _capture_font
from capture_input_stack_previews import record, save_gif
from fluentpy import Button, CheckBox, ComboBox, LineEdit, SpinBox, TextEdit, ToggleSwitch
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from fluentpy.window_effects import capture_window_frame
from PIL import Image
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def _save(widget, output, name, mode):
    picture = _window_image(widget)
    assert not widget.backdrop_applied(), 'Hidden previews must retain the ordinary Qt fallback.'
    assert picture.pixelColor(widget.width() // 2, 3) == widget._resolved_shell_color()
    area = widget.current_page()
    point = area.viewport().mapTo(widget, QtCore.QPoint(area.viewport().width() - 24, 10))
    assert picture.pixelColor(point) == widget._resolved_background_color(), (name, mode, point.toTuple())
    assert picture.save(str(output / f'{name}-{mode}.png'))


def _window_image(widget):
    # An integrated Qt title bar belongs to the backing surface. Only a real
    # non-client Windows caption requires PrintWindow to include its controls.
    if widget.is_title_bar_enabled() and not widget.uses_native_caption_buttons():
        return widget.grab().toImage()
    return capture_window_frame(widget)


def _frame_image(widget):
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    assert _window_image(widget).save(buffer, 'PNG')
    with Image.open(io.BytesIO(bytes(buffer.data()))) as image:
        return image.convert('RGB')


def _dispose(app, widget):
    widget.close()
    widget.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()


def _check_page(window, route):
    area = window.current_page()
    content = area.widget()
    assert content.width() <= area.viewport().width(), (route, content.width(), area.viewport().width())
    assert not area.horizontalScrollBar().isVisible(), route
    assert window.rect().contains(window.centralWidget().geometry()), route
    control_types = (Button, CheckBox, ComboBox, LineEdit, SpinBox, TextEdit, ToggleSwitch)
    for child in content.findChildren(QtWidgets.QWidget):
        if not isinstance(child, control_types) or not child.isVisibleTo(content):
            continue
        rect = QtCore.QRect(child.mapTo(content, QtCore.QPoint()), child.size())
        assert rect.left() >= 0 and rect.right() < content.width(), (route, type(child).__name__, rect.toTuple(), content.width())


def capture(app, mode, output):
    window = WindowDemo(dark=mode == 'dark', mode='expanded', title_bar=True)
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    QTest.qWait(220)
    window.setFocus()
    _save(window, output, 'window-expanded', mode)

    window.resize(760, 720)
    window.mode_combo.setCurrentIndex(MODES.index('compact'))
    QTest.qWait(190)
    _save(window, output, 'window-compact', mode)

    window.resize(1040, 720)
    window.mode_combo.setCurrentIndex(MODES.index('top'))
    QTest.qWait(200)
    _save(window, output, 'window-top', mode)

    window.mode_combo.setCurrentIndex(MODES.index('expanded'))
    window.switch_to('settings', animated=False)
    QTest.qWait(190)
    _save(window, output, 'window-settings', mode)
    frame = _window_image(window)
    native_top = frame.height() - window.height()
    assert frame.copy(0, 0, frame.width(), native_top + window.title_bar().height()).save(
        str(output / f'window-titlebar-{mode}.png'))

    window.switch_to('overview', animated=False)
    window.setFocus()
    QTest.qWait(180)
    poster = _frame_image(window)
    poster.save(output / f'window-motion-{mode}.png')
    performed = set()
    def once(key, at, action, now):
        if now >= at and key not in performed:
            performed.add(key)
            action()
    def prepare_document():
        window.switch_to('documents')
        window.document_editor.clear()
        window.document_editor.setFocus()
    def tick(now):
        once('document', 220, prepare_document, now)
        for index, letter in enumerate('Built with FluentPy.'):
            once('type-' + str(index), 650 + index * 42,
                 lambda char=letter: QTest.keyClicks(window.document_editor, char), now)
        once('save', 1600, lambda: window.save_button.click(), now)
        once('activity', 1920, lambda: window.switch_to('activity'), now)
        once('back', 2460, window.go_back, now)
        once('compact', 3000, lambda: window.mode_combo.setCurrentIndex(MODES.index('compact')), now)
        once('top', 3560, lambda: window.mode_combo.setCurrentIndex(MODES.index('top')), now)
        once('overview', 4150, lambda: window.switch_to('overview'), now)
        once('reset', 4570, lambda: (window.mode_combo.setCurrentIndex(MODES.index('expanded')), window.setFocus()), now)
    frames, times = record(app, window, 5100, tick, capture=_frame_image)
    frames[0] = poster
    animation = save_gif(frames, times, output / f'window-motion-{mode}.gif', 5100)

    checks = []
    for width in (720, 1040):
        window.resize(width, 560)
        for navigation_mode in MODES:
            window.mode_combo.setCurrentIndex(MODES.index(navigation_mode))
            QTest.qWait(170)
            for route in ('overview', 'documents', 'activity', 'settings'):
                window.switch_to(route, animated=False)
                app.processEvents()
                _check_page(window, route)
                checks.append({'width': width, 'height': 560, 'layout': navigation_mode, 'page': route})
    _dispose(app, window)

    workbench = Showcase(dark=mode == 'dark', restore_preferences=False, startup=False)
    workbench.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    workbench.resize(900, 650)
    workbench.show()
    workbench.set_page('navigation', animated=False)
    QTest.qWait(200)
    area = workbench.stack.currentWidget()
    assert area.widget().width() <= area.viewport().width()
    assert workbench.window_examples.demo_window is None
    checks.append({'width': 900, 'height': 650, 'layout': 'workbench', 'page': 'navigation'})
    _dispose(app, workbench)
    return {'mode': mode, 'bounds_checked': len(checks), 'checks': checks, 'animation': animation}


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    errors = []
    def error(kind, value, tb):
        errors.append(str(value))
        sys.__excepthook__(kind, value, tb)
    sys.excepthook = error
    output = SITE / 'dist/assets/previews'
    output.mkdir(parents=True, exist_ok=True)
    results = [capture(app, mode, output) for mode in ('light', 'dark')]
    assert not errors, errors
    print(json.dumps({'captures': results, 'errors': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
