"""Record our own Qt tables, editor and menu; never capture other windows."""
import json
import os
from pathlib import Path
import shutil
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples'), str(SITE)]
os.environ['QT_QPA_PLATFORM'] = 'windows' if sys.platform == 'win32' else 'offscreen'
os.environ['QT_SCALE_FACTOR'] = '1'
from tables import TableDemo
from showcase import Showcase
from fluentpy import LineEdit, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from capture_animations import _capture_font, _image
from capture_input_stack_previews import record, save_gif
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
    window = TableDemo(mode == 'dark')
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    QTest.qWait(140)
    play = window.examples
    view = play.table_view
    view.selectRow(1)
    QTest.qWait(150)
    # Native Windows styles can draw their own selected-row panels before the
    # delegate. Exactly one accent marker may remain at the leading edge.
    row = view.visualRect(view.model().index(1, 0))
    row_image = view.viewport().grab().toImage()
    accent = QtGui.QColor(theme.tokens.accent)
    marker_columns = []
    for column in range(view.model().columnCount()):
        rect = view.visualRect(view.model().index(1, column))
        if any(row_image.pixelColor(x, row.center().y()) == accent
               for x in range(rect.left() + 1, rect.left() + 8)):
            marker_columns.append(column)
    assert marker_columns == [0], marker_columns
    zebra_samples = []
    for style in ('standard', 'rounded', 'line'):
        view.set_row_style(style)
        view.setAlternatingRowColors(True)
        app.processEvents()
        picture = view.viewport().grab().toImage()
        x = view.viewport().width() - 100
        selected = picture.pixelColor(x, view.visualRect(view.model().index(1, 3)).center().y()).name()
        ordinary = picture.pixelColor(x, view.visualRect(view.model().index(3, 3)).center().y()).name()
        assert selected != ordinary, (mode, style, selected, ordinary)
        zebra_samples.append({'style': style, 'selected': selected, 'ordinary': ordinary})
    view.setAlternatingRowColors(False)
    view.set_row_style('standard')
    window.grab().save(str(output / f'tables-demo-{mode}.png'))
    for number, name in enumerate(('standard', 'rounded', 'line')):
        play.style_choice.setCurrentIndex(number)
        app.processEvents()
        assert view.grab().save(str(output / f'tables-{name}-{mode}.png'))
    play.style_choice.setCurrentIndex(1)
    play.search.setText('no-matching-record')
    app.processEvents()
    assert view.model().rowCount() == 0
    assert view.grab().save(str(output / f'tables-empty-{mode}.png'))
    play.search.clear()
    view.setCurrentIndex(view.model().index(1, 0))
    app.sendEvent(view, QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Keyboard,
                                               QtCore.QPoint(), QtCore.QPoint()))
    QTest.qWait(200)
    assert view._context_menu._opened
    assert window.grab().save(str(output / f'tables-context-{mode}.png'))
    view._context_menu.dismiss(immediate=True)
    view.edit(view.model().index(1, 0))
    app.processEvents()
    editor = view.findChild(LineEdit)
    assert editor is not None
    editor.selectAll()
    QTest.keyClicks(editor, 'Edited entry')
    assert window.grab().save(str(output / f'tables-edit-{mode}.png'))
    QTest.keyClick(editor, QtCore.Qt.Key.Key_Return)
    app.processEvents()
    play.style_choice.setCurrentIndex(0)
    view.clearSelection()
    window.setFocus()
    poster = _image(window)
    poster.save(output / f'tables-motion-{mode}.png')
    done = set()
    def once(key, at, action, now):
        if now >= at and key not in done:
            done.add(key)
            action()
    def click_row(row, modifier=QtCore.Qt.KeyboardModifier.NoModifier):
        index = view.model().index(row, 0)
        QTest.mouseClick(view.viewport(), QtCore.Qt.MouseButton.LeftButton, modifier,
                         view.visualRect(index).center())
    def sort_count():
        header = view.horizontalHeader()
        point = QtCore.QPoint(header.sectionViewportPosition(2) + header.sectionSize(2) // 2, 16)
        QTest.mouseClick(header.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)
    def hover_row(row):
        point = view.visualRect(view.model().index(row, 0)).center()
        # The capture root is hidden from the desktop. Deliver local pointer
        # movement without moving the user's real cursor onto another window.
        app.sendEvent(view.viewport(), QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(point), QtCore.QPointF(view.viewport().mapToGlobal(point)),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier))
    def finish_preview():
        play.style_choice.setCurrentIndex(0)
        view.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
        view.scrollToTop()
        view.clearSelection()
        window.setFocus()
    def tick(now):
        once('select', 180, lambda: click_row(1), now)
        once('multi', 480, lambda: click_row(3, QtCore.Qt.KeyboardModifier.ControlModifier), now)
        once('hover', 780, lambda: hover_row(4), now)
        once('sort', 1100, sort_count, now)
        once('rounded', 1550, lambda: play.style_choice.setCurrentIndex(1), now)
        once('widget', 2050, lambda: play.kind.setCurrentIndex(1), now)
        once('search', 2550, lambda: play.search.setText('图片'), now)
        once('clear', 3000, play.search.clear, now)
        once('model', 3350, lambda: play.kind.setCurrentIndex(0), now)
        once('line', 3700, lambda: play.style_choice.setCurrentIndex(2), now)
        once('return', 4150, finish_preview, now)
    intermediate = {'hover': 0, 'selection': 0}
    def animation_frame(widget):
        for name in intermediate:
            if 0 < getattr(view, f'_{name}_progress') < 1:
                intermediate[name] += 1
        return _image(widget)
    frames, times = record(app, window, 4600, tick, capture=animation_frame)
    assert all(intermediate.values()), intermediate
    frames[0] = poster
    animation = save_gif(frames, times, output / f'tables-motion-{mode}.gif', 4600)
    assert len(done) == 11
    bounds = []
    for width in (560, 900):
        window.resize(width, 760)
        for kind in (0, 1):
            play.kind.setCurrentIndex(kind)
            for expanded in (False, True):
                play.advanced.set_expanded(expanded, animated=False)
                app.processEvents()
                assert window.width() == width
                assert play.advanced.width() <= play.width()
                assert play.current_table().width() <= play.width()
                bounds.append({'width': width, 'kind': kind, 'settings': expanded})
    dispose(app, window)
    workbench = Showcase(dark=mode == 'dark', page='tables', restore_preferences=False, startup=False)
    workbench.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    workbench.resize(900, 650)
    workbench.show()
    QTest.qWait(180)
    for sidebar_width in (216, 280):
        workbench.settings_content.width_slider.setValue(sidebar_width)
        workbench.table_examples.advanced.set_expanded(True, animated=False)
        app.processEvents()
        area = workbench.current_page()
        assert area.widget().width() <= area.viewport().width()
        bounds.append({'width': 900, 'sidebar': sidebar_width})
    dispose(app, workbench)
    return {'mode': mode, 'bounds': bounds, 'animation': animation,
            'intermediate_frames': intermediate, 'selection_markers': marker_columns,
            'alternating_selection': zebra_samples}


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(_capture_font())
    errors = []
    def failed(kind, value, tb):
        errors.append(str(value))
        sys.__excepthook__(kind, value, tb)
    sys.excepthook = failed
    output = SITE / 'dist' / 'assets' / 'previews'
    output.mkdir(parents=True, exist_ok=True)
    reports = [capture(app, mode, output) for mode in ('light', 'dark')]
    for mode in ('light', 'dark'):
        shutil.copy2(output / f'tables-demo-{mode}.png', ROOT / f'docs/assets/tables-{mode}.png')
    report = {'captures': reports, 'errors': errors}
    (ROOT / 'build' / 'table-previews.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not errors, errors
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
