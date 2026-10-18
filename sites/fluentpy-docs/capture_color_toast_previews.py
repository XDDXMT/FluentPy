"""Record real in-window ColorToast controls using hidden native Qt surfaces."""
import json
from pathlib import Path
import sys
SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root();sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples'),str(SITE)]
from capture_input_stack_previews import host,record,save_gif
from capture_animations import _capture_font,_image,_font_families
from color_toast import ColorToastDemo
from fluentpy import Button,ColorToast,LineEdit,ProgressToast,theme
from fluentpy.qt import QtCore,QtWidgets,QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def capture(app,mode,output):
    theme.set_mode(mode)
    demo=ColorToastDemo(dark=mode=='dark');demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    demo.show();QTest.qWait(160);demo.grab().save(str(output/f'color-toast-demo-{mode}.png'))
    demo.close();demo.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    widget=host((620,520));widget.show();QTest.qWait(100)
    first=ColorToast.info('操作提示',detail='可以自定义顶部颜色，并在通知中提供操作按钮。',parent=widget,
        placement='top-center',action_text='立即重试',card_width=340,timeout_ms=0)
    second=ColorToast.error('连接失败',detail='暂时无法连接服务器，请稍后重试。',parent=widget,
        placement='bottom-center',card_width=400,timeout_ms=0)
    for toast in (first,second):toast._reveal.setCurrentTime(toast.SHOW_DURATION);toast._stack_motion.setCurrentTime(240)
    app.processEvents();_font_families(first._title,'通知标题')
    widget.grab().save(str(output/f'color-toast-{mode}.png'))
    for toast in (first,second):toast._allow_close=True;toast.close()
    app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    custom=ColorToast('保存备注','内容和按钮均由应用编排。',widget,color='#858585',card_width=340)
    editor=LineEdit('输入备注',custom.content_widget);editor.setText('检查通知中的原生控件')
    custom.content_layout.addWidget(editor)
    actions=QtWidgets.QHBoxLayout()
    for caption in ('保存','取消'):actions.addWidget(Button(caption,custom.content_widget))
    actions.addStretch();custom.content_layout.addLayout(actions)
    custom.show_at('top-center');custom._reveal.setCurrentTime(custom.SHOW_DURATION);app.processEvents()
    for control in custom.content_widget.findChildren(QtWidgets.QWidget):
        if control.isVisible() and not control.children():
            bounds=QtCore.QRectF(control.mapTo(custom,QtCore.QPoint()),control.size())
            assert custom._card_rect().contains(bounds),(control,bounds)
    widget.grab().save(str(output/f'color-toast-content-{mode}.png'))
    custom._allow_close=True;custom.close()
    poster=_image(widget);poster.save(output/f'color-toast-motion-{mode}.png')
    messages={};performed=set()
    def once(key,at,action,now):
        if now>=at and key not in performed:performed.add(key);action()
    def top_first():messages['first']=ColorToast.success('保存完成',detail='修改已保存，可以继续下一步。',parent=widget,placement='top-center',timeout_ms=0)
    def top_next():messages['second']=ColorToast.warning('需要确认',detail='继续操作前，请检查当前设置。',parent=widget,placement='top-center',timeout_ms=0)
    def close_all():
        for toast in list(messages.values()):
            try:toast.close()
            except RuntimeError:pass
    def action():messages['action']=ColorToast.info('导出完成',detail='报告已生成，可点击按钮查看。',parent=widget,placement='top-right',action_text='查看详情',timeout_ms=0)
    def bottom():messages['bottom']=ColorToast.notify('自定义颜色',detail='顶部色条可使用任意有效颜色。',color='#9163cb',parent=widget,placement='bottom-center',timeout_ms=0)
    def progress():messages['progress']=ProgressToast.start('Custom toast view',parent=widget,placement='bottom-center',severity='warning',indeterminate=True)
    def tick(now):
        once('first',250,top_first,now);once('second',850,top_next,now);once('clear-top',1800,close_all,now)
        once('action',2200,action,now)
        once('recolor',2900,lambda:messages['action'].set_color('#009faa'),now)
        once('click',3500,lambda:messages['action'].action_button.click(),now)
        once('bottom',4000,bottom,now);once('progress',4650,progress,now);once('clear-bottom',5600,close_all,now)
    frames,times=record(app,widget,6400,tick);frames[0]=poster
    report=save_gif(frames,times,output/f'color-toast-motion-{mode}.gif',6400)
    widget.close();widget.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return report


def main():
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(_capture_font())
    errors=[]
    def report_error(kind,error,tb):errors.append(str(error));sys.__excepthook__(kind,error,tb)
    sys.excepthook=report_error
    output=SITE/'dist/assets/previews';results=[capture(app,mode,output) for mode in ('light','dark')]
    assert not errors,errors
    print(json.dumps({'captures':results,'errors':errors},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
