"""Capture our hidden native controls only; no desktop or clipboard recording."""
import json
from pathlib import Path
import sys
SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root();sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples'),str(SITE)]
from capture_animations import _capture_font,_image,_font_families
from advanced_inputs import AdvancedInputDemo
from fluentpy import AffixLineEdit,PinCodeEdit,ProgressToast,Toast,Button,theme
from fluentpy.qt import QtCore,QtWidgets,QT_API
from PIL import Image,ImageChops
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def host(size):
    widget=QtWidgets.QWidget();widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    widget.setObjectName('captureInputStack');widget.setFont(_capture_font());widget.setFixedSize(*size)
    widget.setStyleSheet(f'QWidget#captureInputStack {{background:{theme.tokens.background};}} QLabel {{color:{theme.tokens.text};background:transparent;}}')
    return widget


def save_gif(frames,times,path,duration,*,stable_corner=True):
    frames[-1]=frames[0].copy()
    # Include all phases in the shared palette, including warning and success colors.
    contact=Image.new('RGB',(frames[0].width*4,frames[0].height))
    for index in range(4):contact.paste(frames[index*(len(frames)-1)//3],(index*frames[0].width,0))
    palette=contact.quantize(colors=256)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    bounds=[round(time/10)*10 for time in times]+[duration]
    durations=[max(10,b-a) for a,b in zip(bounds,bounds[1:])]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=durations,loop=0,disposal=2,optimize=True)
    with Image.open(path) as gif:
        first=gif.convert('RGB');changed=False
        for index in range(gif.n_frames):
            gif.seek(index);image=gif.convert('RGB');changed|=ImageChops.difference(first,image).getbbox() is not None
            if stable_corner:
                assert image.getpixel((0,0))==first.getpixel((0,0))
            assert image.getbbox() is not None, 'Unexpected all-black frame'
        assert changed and ImageChops.difference(first,gif.convert('RGB')).getbbox() is None
        return {'path':str(path),'frames':gif.n_frames,'bytes':path.stat().st_size}


def record(app,widget,duration,tick_action,*,capture=None):
    frames=[];times=[];clock=QtCore.QElapsedTimer();loop=QtCore.QEventLoop();timer=QtCore.QTimer();timer.setInterval(40)
    def tick():
        now=clock.elapsed()
        if now>=duration:timer.stop();loop.quit();return
        tick_action(now);app.processEvents();frames.append((capture or _image)(widget));times.append(now)
    timer.timeout.connect(tick);clock.start();timer.start();loop.exec()
    return frames,times


def inputs(app,mode,output):
    demo=AdvancedInputDemo(mode=='dark');demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    demo.show();QTest.qWait(180);demo.grab().save(str(output/f'advanced-inputs-{mode}.png'))
    demo.close();demo.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    widget=host((620,340));layout=QtWidgets.QVBoxLayout(widget);layout.setContentsMargins(28,24,28,24);layout.setSpacing(14)
    layout.addWidget(QtWidgets.QLabel('带前后缀的输入框'))
    url=AffixLineEdit('example.hostname',prefix='https://',suffix='.com');layout.addWidget(url)
    layout.addWidget(QtWidgets.QLabel('四位分格密码'))
    pin=PinCodeEdit(4);layout.addWidget(pin)
    result=QtWidgets.QLabel('Tab 切换焦点 · 支持整段粘贴与退格回删');layout.addWidget(result);layout.addStretch()
    pin.completed.connect(lambda _text:result.setText('四位密码已填写完整'))
    widget.show();QTest.qWait(150);widget.setFocus();_font_families(url,'https://')
    poster=_image(widget);poster.save(output/f'input-motion-{mode}.png')
    performed=set()
    def once(key,at,action,now):
        if now>=at and key not in performed:performed.add(key);action()
    def tick(now):
        for index,char in enumerate('fluentpy'):
            once('url'+str(index),350+index*110,lambda value=char:QTest.keyClicks(url,value),now)
        for index,char in enumerate('1234'):
            once('pin'+str(index),1600+index*180,lambda i=index,value=char:QTest.keyClicks(pin.cells()[i],value),now)
        once('backspace',2650,lambda:QTest.keyClick(pin.cells()[-1],QtCore.Qt.Key.Key_Backspace),now)
        once('replace',3100,lambda:QTest.keyClicks(pin.cells()[-1],'8'),now)
        def clear():
            pin.clear();url.clear();widget.setFocus();result.setText('Tab 切换焦点 · 支持整段粘贴与退格回删')
        once('clear',3750,clear,now)
    frames,times=record(app,widget,4500,tick);frames[0]=poster
    report=save_gif(frames,times,output/f'input-motion-{mode}.gif',4500)
    widget.close();widget.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return report


def stacks(app,mode,output):
    widget=host((620,600))
    title=QtWidgets.QLabel('吐司堆叠',widget);title.setGeometry(26,20,230,30);title.setStyleSheet('font-size:22px;font-weight:600;')
    note=QtWidgets.QLabel('底部向上排列\n顶部向下排列\n\n关闭后平滑补位',widget);note.setGeometry(26,100,190,150)
    widget.show();QTest.qWait(120)
    def create(placement,index):
        toast=ProgressToast.start('正在下载文件中，请稍候…',parent=widget,placement=placement,indeterminate=True,severity='warning')
        toast._phase=index*.13;toast._set_phase(toast._phase);return toast
    static=[create('bottom-right',index) for index in range(6)]
    static.append(Toast.success('下载成功',parent=widget,placement='bottom-right',timeout_ms=0))
    for toast in static:
        toast._reveal.setCurrentTime(toast.SHOW_DURATION);toast._stack_motion.setCurrentTime(240)
    app.processEvents();widget.grab().save(str(output/f'toast-stack-{mode}.png'))
    for toast in static:toast._allow_close=True;toast.close()
    app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    poster=_image(widget);poster.save(output/f'toast-stack-motion-{mode}.png')
    active=[];performed=set()
    def once(key,at,action,now):
        if now>=at and key not in performed:performed.add(key);action()
    def add(placement,index):active.append(create(placement,index))
    def close_all():
        for toast in active:
            try:toast.close()
            except RuntimeError:pass  # Factory toasts delete themselves after closing.
    def tick(now):
        for index in range(4):once('bottom'+str(index),300+index*260,lambda i=index:add('bottom-right',i),now)
        once('close-middle',1900,lambda:active[1].close(),now)
        once('clear-bottom',2700,close_all,now)
        for index in range(4):once('top'+str(index),3200+index*260,lambda i=index:add('top-right',i),now)
        once('clear-top',4900,close_all,now)
    frames,times=record(app,widget,5600,tick);frames[0]=poster
    report=save_gif(frames,times,output/f'toast-stack-motion-{mode}.gif',5600)
    widget.close();widget.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return report


def main():
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(_capture_font())
    errors=[]
    def report_error(kind,error,tb):
        errors.append(str(error));sys.__excepthook__(kind,error,tb)
    sys.excepthook=report_error
    output=SITE/'dist/assets/previews';results=[]
    for mode in ('light','dark'):
        theme.set_mode(mode);results.extend([inputs(app,mode,output),stacks(app,mode,output)])
    assert not errors,errors
    print(json.dumps({'captures':results,'errors':errors},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
