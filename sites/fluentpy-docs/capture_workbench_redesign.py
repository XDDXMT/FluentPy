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
from advanced_inputs import AdvancedInputDemo
from fluentpy.qt import QtCore,QtWidgets,QT_API
from fluentpy.theme.fonts import ui_font
from fluentpy.window_effects import capture_window_frame
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(ui_font(14))
errors=[]
sys.excepthook=lambda kind,error,tb:errors.append(str(error))
output=ROOT/'build/workbench-redesign';output.mkdir(parents=True,exist_ok=True)
results=[]
pin_comparisons=[]
layer_checks=[]


def audit_layers(window, picture, key, dark):
    assert not window.backdrop_applied(), 'Hidden widget captures must use the ordinary Qt fallback.'
    shell=window._resolved_shell_color().name();body=window._resolved_background_color().name()
    area=window.stack.currentWidget()
    points={
        'title':QtCore.QPoint(window.width()//2,3),
        'sidebar':window.sidebar.mapTo(window,QtCore.QPoint(window.sidebar.width()-4,4)),
        'page':area.viewport().mapTo(window,QtCore.QPoint(area.viewport().width()-24,10)),
        'footer':QtCore.QPoint(window.width()-8,window.height()-16),
    }
    samples={name:picture.pixelColor(point).name() for name,point in points.items()}
    assert samples['title']==samples['sidebar']==samples['footer']==shell,(key,dark,samples,shell)
    assert samples['page']==body and body!=shell,(key,dark,samples,body,shell)
    layer_checks.append({'page':key,'dark':dark,'pixels':samples})

def audit_pin_background(window,dark):
    scroll=window.stack.currentWidget();saved=scroll.verticalScrollBar().value()
    demo=AdvancedInputDemo(dark=dark);demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen);demo.show()
    scroll.ensureWidgetVisible(window.advanced_inputs.pin,0,80);app.processEvents()
    samples=[]
    for owner,pin in ((window,window.advanced_inputs.pin),(demo,demo.examples.pin)):
        picture=owner.grab().toImage();cell=pin.cells()[0];origin=cell.mapTo(owner,QtCore.QPoint())
        samples.append({'cell':picture.pixelColor(origin+QtCore.QPoint(10,10)).name(),
            'gap':picture.pixelColor(origin+QtCore.QPoint(cell.width()+4,10)).name(),
            'size':list(cell.size().toTuple())})
    assert samples[0]==samples[1],(dark,samples)
    demo.close();demo.deleteLater();scroll.verticalScrollBar().setValue(saved)
    return {'dark':dark,'workbench':samples[0],'standalone':samples[1]}

for dark in (False,True):
    window=Showcase(dark=dark,restore_preferences=False,startup=False)
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show();QTest.qWait(350)
    for key,_,_ in PAGES:
        window.set_page(key,animated=False);app.processEvents();QTest.qWait(15)
        if app.focusWidget():app.focusWidget().clearFocus()
        path=output/f'{key}-{"dark" if dark else "light"}.png'
        picture = (window.grab().toImage() if window.is_title_bar_enabled() and not window.uses_native_caption_buttons()
                   else capture_window_frame(window))
        assert picture.save(str(path))
        audit_layers(window,picture,key,dark)
        content=window.stack.currentWidget()
        overflow=content.widget().width()>content.viewport().width()
        results.append({'page':key,'dark':dark,'overflow':overflow})
        if key=='inputs':pin_comparisons.append(audit_pin_background(window,dark))
    window.resize(900,650);app.processEvents()
    for sidebar_width in (216, 280):
        window.settings_content.width_slider.setValue(sidebar_width)
        app.processEvents()
        for key,_,_ in PAGES:
            window.set_page(key,animated=False);app.processEvents()
            content=window.stack.currentWidget()
            results.append({'page':key,'dark':dark,'width':900,'sidebar_width':sidebar_width,
                            'overflow':content.widget().width()>content.viewport().width()})
    window.close();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
assert not errors,errors
overflows=[item for item in results if item['overflow']]
(output/'validation.json').write_text(json.dumps({'checks':results,'layer_checks':layer_checks,'pin_comparisons':pin_comparisons,'errors':errors,'overflows':overflows},ensure_ascii=False,indent=2),encoding='utf-8')
assert not overflows,overflows
shutil.copy2(output/'overview-light.png',SITE/'dist/assets/previews/showcase-home-light.png')
shutil.copy2(output/'overview-dark.png',SITE/'dist/assets/previews/showcase-home-dark.png')
shutil.copy2(output/'navigation-light.png',SITE/'dist/assets/previews/showcase-light.png')
shutil.copy2(output/'overview-light.png',ROOT/'docs/assets/gallery-preview-light.png')
shutil.copy2(output/'overview-dark.png',ROOT/'docs/assets/gallery-preview.png')
shutil.copy2(output/'navigation-light.png',ROOT/'docs/assets/showcase-light.png')
shutil.copy2(output/'navigation-dark.png',ROOT/'docs/assets/showcase-dark.png')
for mode in ('light','dark'):
    shutil.copy2(output/f'settings-{mode}.png',SITE/f'dist/assets/previews/showcase-settings-{mode}.png')
print(json.dumps({'pages':len(PAGES),'captures':len(PAGES)*2,'bounds_checked':len(results),'layer_checks':len(layer_checks),'pin_comparisons':pin_comparisons,'errors':errors,'overflows':overflows},ensure_ascii=False,indent=2))
