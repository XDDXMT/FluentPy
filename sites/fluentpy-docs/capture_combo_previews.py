"""Render and audit only our hidden native Qt combo examples."""
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
from combo_boxes import ComboBoxDemo, KINDS
from showcase import Showcase
from capture_animations import _capture_font, _image
from capture_input_stack_previews import record, save_gif
from fluentpy import theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

NAMES = ['combo-basic', 'combo-editable', 'combo-model', 'combo-editable-model',
         'combo-multi', 'combo-tree', 'combo-tree-multi', 'combo-transparent', 'combo-font']


def capture(app, mode, output):
    demo = ComboBoxDemo(mode == 'dark')
    demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    demo.show()
    QTest.qWait(180)
    play = demo.examples
    assert len(QtGui.QFontDatabase.families()) > 10, 'Native font inventory is missing'
    demo.grab().save(str(output/f'combo-playground-{mode}.png'))
    bounds_checked = 0
    for number, name in enumerate(NAMES):
        play.kind.setCurrentIndex(number)
        app.processEvents()
        choice = play.preview
        if number == 6:
            parent = choice.model().index(0, 0)
            choice.setSelectedIndexes([choice.model().index(row, 0, parent) for row in range(3)])
        if choice._multiple:
            for button in choice._tag_buttons:
                assert button.fontMetrics().horizontalAdvance(button.text())+2*button._h_padding+1 <= button.width(), (mode, button.text())
        choice.show_popup()
        popup = choice._popup
        assert popup is not None and popup._opened
        popup._reveal.setCurrentTime(popup.SHOW_DURATION)
        if choice._tree:
            popup.view.expandAll()
        app.processEvents()
        assert demo.rect().contains(popup._surface.geometry())
        assert not popup.isWindow()
        demo.grab().save(str(output/f'{name}-{mode}.png'))
        choice.hide_popup()
        bounds_checked += 1
    for width in (880, 560):
        demo.resize(width, 820)
        app.processEvents()
        for number, name in enumerate(NAMES):
            play.kind.setCurrentIndex(number)
            app.processEvents()
            if play.preview._multiple:
                for button in play.preview._tag_buttons:
                    assert button.fontMetrics().horizontalAdvance(button.text())+2*button._h_padding+1 <= button.width(), (mode, width, button.text())
            assert play.rect().contains(QtCore.QRect(play.preview.mapTo(play, QtCore.QPoint()), play.preview.size())), (width, name)
            play.preview.show_popup()
            popup = play.preview._popup
            popup._reveal.setCurrentTime(popup.SHOW_DURATION)
            app.processEvents()
            assert demo.rect().contains(popup._surface.geometry())
            play.preview.hide_popup()
            bounds_checked += 2
    demo.resize(880, 560)
    play.kind.setCurrentIndex(4)
    play.preview.clearSelection()
    app.processEvents()
    poster = _image(demo)
    poster.save(output/f'combo-motion-{mode}.png')
    performed = set()
    def once(name, at, action, now):
        if now >= at and name not in performed:
            performed.add(name)
            action()
    def click(row):
        popup = play.preview._popup
        index = popup.proxy.index(row, 0)
        QTest.mouseClick(popup.view.viewport(), QtCore.Qt.MouseButton.LeftButton,
                         pos=popup.view.visualRect(index).center())
    def tick(now):
        once('open', 300, play.preview.show_popup, now)
        once('one', 800, lambda: click(0), now)
        once('two', 1250, lambda: click(1), now)
        once('three', 1700, lambda: click(2), now)
        once('close', 2200, play.preview.hide_popup, now)
        once('remove', 2700, lambda: play.preview._tag_buttons[0].click(), now)
        once('clear', 3300, play.preview.clearSelection, now)
    frames, times = record(app, demo, 4000, tick)
    frames[0] = poster
    gif = save_gif(frames, times, output/f'combo-motion-{mode}.gif', 4000)
    demo.close()
    demo.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    # Audit integration at the workbench's minimum supported width.
    workbench = Showcase(dark=mode == 'dark', page='inputs', restore_preferences=False, startup=False)
    workbench.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    workbench.resize(900, 650)
    workbench.show()
    QTest.qWait(180)
    scroll = workbench.stack.currentWidget()
    for number in range(len(KINDS)):
        workbench.combo_examples.kind.setCurrentIndex(number)
        app.processEvents()
        assert scroll.widget().width() <= scroll.viewport().width()
        bounds_checked += 1
    workbench.close()
    workbench.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    return {'mode': mode, 'bounds_checked': bounds_checked, 'animation': gif}


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    errors = []
    sys.excepthook = lambda kind, error, tb: errors.append(str(error))
    results = [capture(app, mode, SITE/'dist/assets/previews') for mode in ('light', 'dark')]
    assert not errors, errors
    print(json.dumps({'captures': results, 'errors': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
