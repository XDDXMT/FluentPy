"""Record only hidden native Qt surfaces. Eyedropper uses a synthetic screen."""
from __future__ import annotations
import json
from pathlib import Path
import sys
SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root()
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples'),str(SITE)]
from capture_animations import _capture_font, _image, _font_families
from PIL import Image, ImageChops
from colors import ColorDemo
from fluentpy import ColorDialog, ColorPaletteButton, ColorPickerButton, ColorSwatchGroup, ScreenColorPicker, theme
from fluentpy.widgets.eyedropper import _ScreenOverlay
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def capture(app,mode,output):
    theme.set_mode(mode)
    demo=ColorDemo(dark=mode=='dark');demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    demo.setFont(_capture_font());demo.show();QTest.qWait(200)
    assert _font_families(demo.content.panel.hex_input,'#ffe4579b')
    for entry in demo.content.panel.channel_inputs:
        # SpinBox reserves space for its two existing arrow buttons.
        assert entry.width() >= 90
    demo.grab().save(str(output/f'colors-{mode}.png'))
    demo.close();demo.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    host=QtWidgets.QWidget();host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    host.setObjectName('colorCapture');host.setFont(_capture_font());host.setFixedSize(620,650)
    host.setStyleSheet(f'QWidget#colorCapture {{background:{theme.tokens.background};}} QLabel {{color:{theme.tokens.text};background:transparent;}}')
    title=QtWidgets.QLabel('颜色与取色',host);title.setGeometry(30,16,200,26)
    title.setStyleSheet('font-size:18px;font-weight:600;')
    picker=ColorPickerButton('#0078d4',host);picker.move(30,55)
    palette=ColorPaletteButton('#0078d4',host);palette.move(360,55)
    for text,x in [('完整编辑器',110),('主题色板',440)]:
        label=QtWidgets.QLabel(text,host);label.setGeometry(x,60,140,26)
    host.show();QTest.qWait(120)
    palette.show_popup();palette._popup._reveal.setCurrentTime(palette._popup.SHOW_DURATION)
    app.processEvents();host.setFocus();QTest.qWait(140)
    host.grab().save(str(output/f'color-palette-{mode}.png'));palette._popup.dismiss(immediate=True)
    dialog=ColorDialog('#e4579b','选择背景颜色',host,enable_alpha=True)
    dialog.open();dialog._fade.setCurrentTime(180);host.setFocus();QTest.qWait(160)
    host.grab().save(str(output/f'color-dialog-{mode}.png'));dialog.reject();dialog._fade.setCurrentTime(100)
    picker.show_popup();picker._popup._reveal.setCurrentTime(picker._popup.SHOW_DURATION)
    app.processEvents();host.setFocus();QTest.qWait(180)
    poster=_image(host);poster.save(output/f'color-motion-{mode}.png')
    initial=picker.color();frames=[];elapsed=[];performed=set();clock=QtCore.QElapsedTimer()
    loop=QtCore.QEventLoop();timer=QtCore.QTimer();timer.setInterval(40)
    def once(key,at,action,now):
        if now>=at and key not in performed:performed.add(key);action()
    def reset():
        picker.set_color(initial);palette.set_color(initial)
        picker.show_popup();picker._popup._reveal.setCurrentTime(picker._popup.SHOW_DURATION)
        host.setFocus()
    def tick():
        now=clock.elapsed()
        if now>=5900:timer.stop();loop.quit();return
        if 450<=now<1900:
            picker.editor.spectrum.selected.emit(200+125*(now-450)/1450,.8)
        if 1950<=now<2650:
            picker.editor.channel_sliders[3].setValue(round(255-130*(now-1950)/700))
        once('confirm',2750,picker.confirm_button.click,now)
        once('palette',3300,palette.show_popup,now)
        once('select',4100,lambda:palette.palette._buttons[5].click(),now)
        once('reset',4850,reset,now)
        app.processEvents();frames.append(_image(host));elapsed.append(now)
    timer.timeout.connect(tick);clock.start();timer.start();loop.exec()
    frames[0]=poster;frames[-1]=poster.copy()
    palette_image=poster.quantize(colors=256)
    indexed=[frame.quantize(palette=palette_image,dither=Image.Dither.NONE) for frame in frames]
    boundaries=[round(value/10)*10 for value in elapsed]+[5900]
    durations=[max(10,b-a) for a,b in zip(boundaries,boundaries[1:])]
    gif_path=output/f'color-motion-{mode}.gif'
    indexed[0].save(gif_path,save_all=True,append_images=indexed[1:],duration=durations,loop=0,disposal=2,optimize=True)
    with Image.open(gif_path) as gif:
        first=gif.convert('RGB');changed=False;count=gif.n_frames
        corners=[(0,0),(619,0),(0,649),(619,649)]
        background=[first.getpixel(point) for point in corners]
        for index in range(count):
            gif.seek(index);frame=gif.convert('RGB')
            assert [frame.getpixel(point) for point in corners]==background
            assert min(frame.getextrema()[channel][1] for channel in range(3))>100
            changed|=ImageChops.difference(first,frame).getbbox() is not None
        assert changed and ImageChops.difference(first,gif.convert('RGB')).getbbox() is None
    host.close();host.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    # Render a frozen test canvas with the actual overlay painter, without reading the desktop.
    snapshot=QtGui.QImage(620,200,QtGui.QImage.Format.Format_RGB32)
    painter=QtGui.QPainter(snapshot);gradient=QtGui.QLinearGradient(0,0,620,0)
    gradient.setColorAt(0,QtGui.QColor('#c7a2ec'));gradient.setColorAt(.5,QtGui.QColor('#4ba6ed'));gradient.setColorAt(1,QtGui.QColor('#009faa'))
    painter.fillRect(snapshot.rect(),gradient);painter.end()
    sampler=ScreenColorPicker();sampler._frames=[(QtCore.QRect(0,0,620,200),snapshot)]
    sampler._point=QtCore.QPoint(240,80)
    overlay=_ScreenOverlay(sampler,QtCore.QRect(0,0,620,200),snapshot)
    overlay.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen);overlay.setFont(_capture_font())
    overlay.show();app.processEvents();overlay.grab().save(str(output/f'color-eyedropper-{mode}.png'))
    overlay.close();overlay.deleteLater();sampler.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return {'mode':mode,'frames':count,'bytes':gif_path.stat().st_size,'synthetic_screen_only':True,'no_black_frames':True,'loop_returns_to_initial_canvas':True}


def main():
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(_capture_font())
    errors=[];sys.excepthook=lambda kind,error,tb:errors.append(str(error))
    output=SITE/'dist/assets/previews';output.mkdir(parents=True,exist_ok=True)
    results=[capture(app,mode,output) for mode in ('light','dark')]
    assert not errors,errors
    print(json.dumps({'captures':results,'errors':errors},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
