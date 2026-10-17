"""Capture and audit the reference app using its own hidden Qt widgets."""
import json
import os
from pathlib import Path
import shutil
import sys

SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root()
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples')]
os.environ['QT_QPA_PLATFORM']='windows' if sys.platform=='win32' else 'offscreen'
os.environ['QT_SCALE_FACTOR']='1'
from showcase import Showcase,PAGES
from fluentpy.qt import QtCore,QtWidgets,QT_API
from fluentpy.theme.fonts import ui_font
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(ui_font(14))
errors=[]
sys.excepthook=lambda kind,error,tb:errors.append(str(error))
output=ROOT/'build/workbench-redesign';output.mkdir(parents=True,exist_ok=True)
results=[]
for dark in (False,True):
    window=Showcase(dark=dark)
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show();QTest.qWait(350)
    for key,_,_ in PAGES:
        window.set_page(key,animated=False);app.processEvents();QTest.qWait(15)
        if app.focusWidget():app.focusWidget().clearFocus()
        path=output/f'{key}-{"dark" if dark else "light"}.png'
        assert window.grab().save(str(path))
        content=window.stack.currentWidget()
        overflow=content.widget().width()>content.viewport().width()
        results.append({'page':key,'dark':dark,'overflow':overflow})
    window.resize(900,650);app.processEvents()
    for key,_,_ in PAGES:
        window.set_page(key,animated=False);app.processEvents()
        content=window.stack.currentWidget()
        results.append({'page':key,'dark':dark,'width':900,'overflow':content.widget().width()>content.viewport().width()})
    window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
assert not errors,errors
overflows=[item for item in results if item['overflow']]
(output/'validation.json').write_text(json.dumps({'checks':results,'errors':errors,'overflows':overflows},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(output/'overview-light.png',SITE/'dist/assets/previews/showcase-home-light.png')
shutil.copy2(output/'navigation-light.png',SITE/'dist/assets/previews/showcase-light.png')
shutil.copy2(output/'overview-light.png',ROOT/'docs/assets/gallery-preview-light.png')
shutil.copy2(output/'overview-dark.png',ROOT/'docs/assets/gallery-preview.png')
shutil.copy2(output/'navigation-light.png',ROOT/'docs/assets/showcase-light.png')
shutil.copy2(output/'navigation-dark.png',ROOT/'docs/assets/showcase-dark.png')
print(json.dumps({'pages':len(PAGES),'captures':len(PAGES)*2,'errors':errors,'overflows':overflows},ensure_ascii=False,indent=2))
