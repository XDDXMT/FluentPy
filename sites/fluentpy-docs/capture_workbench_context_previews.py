"""Render the workbench's real, shared Qt-action context menus."""
import json
import os
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
os.environ['QT_QPA_PLATFORM'] = 'windows' if sys.platform == 'win32' else 'offscreen'
os.environ['QT_SCALE_FACTOR'] = '1'

from showcase import Showcase
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from fluentpy.theme.fonts import ui_font
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def open_context(app, window, target, point=None):
    point = point or target.rect().center()
    app.sendEvent(target, QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse,
                  point, target.mapToGlobal(point)))
    app.processEvents()
    menu = window.context_menus.menu
    assert menu is not None and menu._opened
    menu._reveal.setCurrentTime(menu.SHOW_DURATION)
    app.processEvents()
    assert window.rect().contains(menu._surface.geometry())
    return menu


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setFont(ui_font(14))
    errors, captures = [], []
    sys.excepthook = lambda kind, error, tb: errors.append(str(error))
    output = SITE / 'dist/assets/previews'
    for mode in ('light', 'dark'):
        window = Showcase(dark=mode == 'dark', restore_preferences=False, startup=False)
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.show()
        assert not window.backdrop_applied(), 'Hidden previews must retain the ordinary Qt fallback.'
        window.set_page('code', animated=False)
        app.processEvents()
        editor = window.code_editor.text_edit
        editor.selectAll()
        menu = open_context(app, window, editor.viewport(), QtCore.QPoint(120, 70))
        assert any(action.isEnabled() and action.objectName() == 'edit-copy' for action in menu.actions())
        assert window.grab().save(str(output / f'workbench-context-{mode}.png'))
        captures.append({'mode': mode, 'source': 'code editor', 'actions': len(menu.actions())})
        menu.dismiss(immediate=True)
        window.set_page('navigation', animated=False)
        app.processEvents()
        tab = window.document_tabs._items[0].widget
        area = window.stack.currentWidget()
        area.ensureWidgetVisible(tab)
        app.processEvents()
        menu = open_context(app, window, tab)
        assert any(action.text() == '关闭此文档' for action in menu.actions())
        assert window.grab().save(str(output / f'workbench-tab-context-{mode}.png'))
        captures.append({'mode': mode, 'source': 'document tab', 'actions': len(menu.actions())})
        menu.dismiss(immediate=True)
        window.set_page('settings', animated=False)
        app.processEvents()
        settings = window.settings_content
        area = window.stack.currentWidget()
        QTest.qWait(200)
        area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
        QTest.qWait(200)
        assert window.grab().save(str(output / f'workbench-about-{mode}.png'))
        captures.append({'mode': mode, 'source': 'about and author'})
        settings.declarations_card.set_expanded(True, animated=False)
        QTest.qWait(200)
        area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
        QTest.qWait(200)
        assert window.grab().save(str(output / f'workbench-declarations-{mode}.png'))
        captures.append({'mode': mode, 'source': 'local license and third-party notices'})
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    assert not errors, errors
    print(json.dumps({'captures': captures, 'errors': errors}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
