"""Capture FluentPy's independent message-bar implementation on hidden native Qt."""
import argparse,json
from pathlib import Path
import sys
SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root();sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples'),str(SITE)]
from capture_input_stack_previews import host,record,save_gif
from capture_animations import _capture_font,_image
from info_bar import EmbeddedInfoBarExamples,InfoBarDemo
from fluentpy import FluentIcon,InfoBar,ProgressInfoBar,theme
from fluentpy.qt import QtCore,QtWidgets,QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def settled(bar):
    bar._reveal.setCurrentTime(bar.SHOW_DURATION);bar._stack_motion.setCurrentTime(240)


def capture_embedded(app,mode,output):
    theme.set_mode(mode);owner=host((820,700));layout=QtWidgets.QVBoxLayout(owner)
    layout.setContentsMargins(20,16,20,16)
    examples=EmbeddedInfoBarExamples();layout.addWidget(examples);layout.addStretch()
    owner.show();QTest.qWait(300)
    checked=0
    for bar in (examples.notice,examples.form,examples.task):
        assert bar.isVisible() and not bar.isWindow() and bar._stack is None and bar._placement is None
        for widget in bar.findChildren(QtWidgets.QWidget):
            if widget.isVisible():
                bounds=QtCore.QRectF(widget.mapTo(bar,QtCore.QPoint()),widget.size())
                assert bar._card_rect().contains(bounds),(widget,bounds,bar._card_rect())
                if isinstance(widget,QtWidgets.QLabel):assert widget.height()>=widget.heightForWidth(widget.width())
                checked+=1
    path=output/f'info-bar-embedded-{mode}.png';assert owner.grab().save(str(path))
    previous=examples.form.y();examples.notice.close();examples.notice._reveal.setCurrentTime(examples.notice.HIDE_DURATION)
    app.processEvents();app.processEvents();assert examples.form.y()<previous
    examples.restore_examples();app.processEvents();assert examples.notice.isVisible()
    examples.notice.close();examples.restore_examples();QTest.qWait(examples.notice.HIDE_DURATION+20)
    assert examples.notice.isVisible() and not examples.notice._closing
    examples.submit_button.click();assert examples.form.tone()=='warning'
    examples.note_input.setText('嵌入布局备注');examples.submit_button.click()
    assert examples.form.tone()=='success' and examples.form.detail()=='嵌入布局备注'
    examples.advance_button.click();assert examples.task.value()==55
    examples.finish_button.click();assert examples.task.state()=='success' and examples.task.value()==100
    examples.reset_button.click();app.processEvents();assert examples.task.state()=='running' and examples.task.value()==35
    assert examples.task_layout.count()==1
    owner.close();owner.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return {'mode':mode,'path':str(path),'bounds_checked':checked,'interaction_checks':9}


def audit(app,mode):
    theme.set_mode(mode);owner=host((960,1200));owner.show()
    bar=InfoBar('操作提示','设置已经保存，可以继续编辑，也可以点击按钮撤销。',owner,action_text='撤销',close_on_action=False)
    bar.show_at();settled(bar);checks=0
    for orientation in ('horizontal','vertical'):
        bar.set_orientation(orientation)
        for width in range(200,721,4):
            bar.set_card_width(width);app.processEvents()
            for widget in (bar._title,bar._detail,bar.action_button,bar.close_button,bar._status_icon):
                bounds=QtCore.QRectF(widget.mapTo(bar,QtCore.QPoint()),widget.size())
                assert bar._card_rect().contains(bounds),(mode,orientation,width,widget,bounds,bar._card_rect())
                if isinstance(widget,QtWidgets.QLabel):assert widget.height()>=widget.heightForWidth(widget.width()),(width,widget)
                checks+=1
    owner.close();owner.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return checks


def capture(app,mode,output):
    theme.set_mode(mode)
    demo=InfoBarDemo(dark=mode=='dark');demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    demo.show();QTest.qWait(120);demo.grab().save(str(output/f'info-bar-demo-{mode}.png'))
    demo.close();demo.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    inline=host((820,620));layout=QtWidgets.QVBoxLayout(inline);layout.setContentsMargins(20,16,20,16);layout.setSpacing(0)
    bars=[InfoBar('保存完成','当前设置已经写入本地文件。',inline,tone='success'),
        InfoBar('需要确认','继续操作前，请检查当前设置和输出位置。',inline,tone='warning',orientation='vertical',action_text='检查设置'),
        InfoBar('使用自己的内容','消息条可以加入原生控件，显示你需要的操作。',inline,icon=FluentIcon.CODE,background='#f0f1fc',dark_background='#303048'),
        ProgressInfoBar('正在导出','已处理 65%，正在写入剩余文件。',inline),
        ProgressInfoBar('准备文件','正在读取数据，请稍候…',inline,indeterminate=True)]
    for bar in bars:layout.addWidget(bar)
    layout.addStretch();inline.show();bars[3].set_progress(65);bars[3]._progress_motion.setCurrentTime(220)
    app.processEvents();inline.grab().save(str(output/f'info-bar-{mode}.png'))
    inline.close();inline.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    canvas=host((760,440));canvas.show();app.processEvents()
    poster=_image(canvas);poster.save(output/f'info-bar-motion-{mode}.png');messages={};done=set()
    def once(key,at,action,now):
        if now>=at and key not in done:done.add(key);action()
    def first():messages['first']=InfoBar.success('保存完成',detail='当前设置已经保存。',parent=canvas,timeout_ms=0,card_width=620)
    def second():messages['second']=InfoBar.warning('检查输出位置',detail='这条消息使用纵向排列，并提供自己的按钮文字。',parent=canvas,orientation='vertical',action_text='稍后提醒',timeout_ms=0,card_width=420)
    def custom():messages['custom']=InfoBar.notify('自定义消息',detail='自选图标与明暗背景颜色。',parent=canvas,icon=FluentIcon.CODE,background='#f0f1fc',dark_background='#303048',placement='bottom-right',timeout_ms=0,card_width=500)
    def task():messages['task']=ProgressInfoBar.start('正在导出',detail='正在准备文件，请稍候…',parent=canvas,indeterminate=True,card_width=620)
    def progress(value):messages['task'].set_progress(value);messages['task'].set_detail(f'已处理 {value}%，正在写入文件。')
    def finish():messages['task'].set_detail('文件已保存，可以继续操作。');messages['task'].finish('导出完成',timeout_ms=0)
    def close_all():
        for bar in messages.values():
            try:bar.close()
            except RuntimeError:pass
    def tick(now):
        once('first',180,first,now);once('second',750,second,now)
        once('close-first',1550,lambda:messages['first'].close(),now)
        once('close-second',2000,lambda:messages['second'].close(),now)
        once('custom',2250,custom,now);once('task',2850,task,now)
        once('35',3550,lambda:progress(35),now);once('76',4200,lambda:progress(76),now)
        once('finish',4850,finish,now);once('close',5700,close_all,now)
    frames,times=record(app,canvas,6500,tick);frames[0]=poster
    result=save_gif(frames,times,output/f'info-bar-motion-{mode}.gif',6500)
    canvas.close();canvas.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--embedded-only',action='store_true');args=parser.parse_args()
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(_capture_font())
    errors=[];sys.excepthook=lambda kind,error,tb:errors.append(str(error))
    checks=0 if args.embedded_only else sum(audit(app,mode) for mode in ('light','dark'))
    embedded=[capture_embedded(app,mode,SITE/'dist/assets/previews') for mode in ('light','dark')]
    results=[] if args.embedded_only else [capture(app,mode,SITE/'dist/assets/previews') for mode in ('light','dark')]
    assert not errors,errors
    print(json.dumps({'native_bounds_checked':checks,'embedded':embedded,'captures':results,'errors':errors},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
