"""Record real whole-Showcase theme transitions, without capturing the desktop.

Run ``python sites/fluentpy-docs/capture_theme_previews.py``. Both movies use
native Qt widgets and the production asynchronous 280 ms theme coordinator.
Only four documentation assets are written; settings are never persisted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples'), str(SITE)]
os.environ['QT_QPA_PLATFORM'] = 'windows' if sys.platform == 'win32' else 'offscreen'
os.environ['QT_SCALE_FACTOR'] = '1'

from capture_animations import _capture_font, _image
from capture_input_stack_previews import record, save_gif
from fluentpy import theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from showcase import Showcase
from PIL import Image
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


SIZE = (1120, 780)
DURATION = 3400
TRANSITION_MS = 280


def _rgb(color):
    color = QtGui.QColor(color)
    return color.red(), color.green(), color.blue()


def _near(actual, expected, *, tolerance=2):
    return max(abs(a - b) for a, b in zip(actual, expected)) <= tolerance


def _state(window):
    """Check real editors and selected routes, including hidden pages."""
    documents = {}
    for key, editor in window._documents.items():
        documents[key] = editor.code() if hasattr(editor, 'code') else editor.toPlainText()
    return {
        'route': window.current_route(),
        'code': window.code_editor.code(),
        'url': window.advanced_inputs.url.text(),
        'pin': window.advanced_inputs.pin.text(),
        'document_route': window.document_stack.currentIndex(),
        'documents': documents,
    }


def _points(window):
    viewport = window.stack.currentWidget().viewport()
    card = window.catalog_cards[0][0]
    return {
        'title': (400, window.title_bar().height() // 2),
        'navigation': window.sidebar.mapTo(window, QtCore.QPoint(2, 180)).toTuple(),
        'page': viewport.mapTo(window, QtCore.QPoint(viewport.width() - 24, 10)).toTuple(),
        'card': card.mapTo(window, QtCore.QPoint(card.width() - 16, 22)).toTuple(),
    }


def _check_endpoint(window, image, points):
    assert image.size == SIZE, image.size
    expected_shell = _rgb(window._resolved_shell_color())
    for key in ('title', 'navigation'):
        pixel = image.getpixel(points[key])
        assert _near(pixel, expected_shell), (key, pixel, expected_shell)
    expected_background = _rgb(window._resolved_background_color())
    assert _near(image.getpixel(points['page']), expected_background), ('page', image.getpixel(points['page']), expected_background)
    assert expected_shell != expected_background, (expected_shell, expected_background)
    card = image.getpixel(points['card'])
    assert _near(card, _rgb(theme.tokens.surface)), ('card', card, theme.tokens.surface)
    return {key: image.getpixel(point) for key, point in points.items()}


def _check_blended_frame(window, image, points):
    coordinator = window._theme_transition
    layer = coordinator.layer
    if (not coordinator.is_running() or layer.target_frame.isNull()
            or not 0.08 < layer.opacity < 0.92):
        return None
    old, new = layer.frame.toImage(), layer.target_frame.toImage()
    opacity = layer.opacity
    samples = {}
    for key, point in points.items():
        old_rgb, new_rgb = _rgb(old.pixelColor(*point)), _rgb(new.pixelColor(*point))
        expected = tuple(round(a * opacity + b * (1 - opacity)) for a, b in zip(old_rgb, new_rgb))
        actual = image.getpixel(point)
        assert _near(actual, expected, tolerance=3), (key, actual, expected, opacity)
        assert max(actual) > 5, ('black cached surface', key, actual)
        samples[key] = actual
    # A full caption glyph also has to blend, rather than retaining the old
    # black/white foreground while only the title-bar background changes.
    button = window.title_bar().close_button
    glyph = button.mapTo(window, button.rect().center() + QtCore.QPoint(4, 4)).toTuple()
    a, b = _rgb(old.pixelColor(*glyph)), _rgb(new.pixelColor(*glyph))
    expected = tuple(round(x * opacity + y * (1 - opacity)) for x, y in zip(a, b))
    assert _near(image.getpixel(glyph), expected, tolerance=3), ('caption glyph', image.getpixel(glyph), expected)
    return {'opacity': round(opacity, 4), 'pixels': samples}


def _dispose(app, window):
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()


def capture(app, mode, output):
    window = Showcase(dark=mode == 'dark', restore_preferences=False, startup=False)
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.resize(*SIZE)
    window.show()
    QTest.qWait(260)
    window.theme_toggle.setFocus()
    app.processEvents()
    coordinator = window._theme_transition
    assert window.is_theme_transition_enabled()
    assert coordinator.duration == TRANSITION_MS
    assert window.title_bar().height() == 48
    assert not window.uses_native_caption_buttons(), 'The integrated 48px title bar must be captured.'

    original_state = _state(window)
    original_accent = theme.tokens.custom_accent
    original_preferences = dict(window._preferences)
    points = _points(window)
    poster = _image(window)
    initial_pixels = _check_endpoint(window, poster, points)
    poster.save(output / f'theme-transition-{mode}.png')

    performed = set()
    endpoints = []
    midpoints = []
    reversals = []
    def once(key, at, action, now):
        if now >= at and key not in performed:
            performed.add(key)
            action()

    def toggle(*, reverse=False):
        before = _image(window) if reverse else None
        if reverse:
            assert coordinator.is_running(), 'Reversal must interrupt an actual running transition.'
            assert 0.0 < coordinator.layer.opacity < 1.0
        QTest.mouseClick(window.theme_toggle, QtCore.Qt.MouseButton.LeftButton,
                         pos=window.theme_toggle.rect().center())
        assert coordinator.is_running(), 'A real mouse click must start the production transition.'
        if reverse:
            # The new old-frame is the currently displayed composite. This
            # guards against flashing a complete old theme on rapid reversal.
            after = _image(window)
            for key, point in points.items():
                assert _near(after.getpixel(point), before.getpixel(point), tolerance=3), (
                    'discontinuous reversal', key, before.getpixel(point), after.getpixel(point))
            reversals.append({'opacity': round(coordinator.layer.opacity, 4),
                              'pixels': {key: after.getpixel(point) for key, point in points.items()}})

    def check_endpoint():
        assert not coordinator.is_running(), 'Transition must finish at 280 ms.'
        image = _image(window)
        endpoints.append({'mode': theme.tokens.mode.value,
                          'pixels': _check_endpoint(window, image, points)})

    def tick(now):
        once('opposite', 180, toggle, now)
        once('first-end', 650, check_endpoint, now)
        once('return', 820, toggle, now)
        once('return-end', 1280, check_endpoint, now)
        once('reverse-start', 1440, toggle, now)
        once('reverse', 1580, lambda: toggle(reverse=True), now)
        once('reverse-end', 2050, check_endpoint, now)
        once('last-opposite', 2240, toggle, now)
        once('last-return', 2820, toggle, now)
        once('last-end', 3280, check_endpoint, now)

    def sample(widget):
        image = _image(widget)
        assert image.size == SIZE
        assert image.getbbox() is not None, 'Unexpected all-black frame'
        blended = _check_blended_frame(window, image, points)
        if blended is not None:
            midpoints.append(blended)
        return image

    try:
        frames, times = record(app, window, DURATION, tick, capture=sample)
        assert len(performed) == 10, performed
        assert len(midpoints) >= 6, len(midpoints)
        assert len(endpoints) == 4 and len(reversals) == 1
        assert theme.tokens.mode.value == mode
        assert theme.tokens.custom_accent == original_accent
        assert _state(window) == original_state, 'Theme changes must retain routes and editor contents.'
        assert window._preferences == original_preferences
        assert window.updatesEnabled()
        final = _image(window)
        _check_endpoint(window, final, points)
        # Use a complete real initial frame at time zero; no frame is recreated
        # or manually progressed, including the interrupted transition.
        # The shared encoder closes the loop with this same captured poster,
        # avoiding a mouse-focus or first-paint antialiasing seam.
        frames.insert(0, poster)
        times.insert(0, 0)
        path = output / f'theme-transition-{mode}.gif'
        report = save_gif(frames, times, path, DURATION, stable_corner=False)
        with Image.open(path) as gif:
            duration = 0
            for index in range(gif.n_frames):
                gif.seek(index)
                assert gif.size == SIZE
                duration += gif.info.get('duration', 0)
        report.update({'mode': mode, 'size': list(SIZE), 'duration_ms': duration,
                       'sampled_frames': len(frames), 'transition_ms': TRANSITION_MS,
                       'title_bar_height': window.title_bar().height(),
                       'initial_pixels': initial_pixels, 'endpoints': endpoints,
                       'intermediate_frames_checked': len(midpoints), 'reversals_checked': len(reversals),
                       'state_preserved': True})
        return report
    finally:
        _dispose(app, window)


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
    original_mode, original_accent = theme.tokens.mode, theme.tokens.custom_accent
    try:
        captures = [capture(app, mode, output) for mode in ('light', 'dark')]
    finally:
        theme.set_theme(original_mode, accent=original_accent)
    assert not errors, errors
    print(json.dumps({'captures': captures, 'errors': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
