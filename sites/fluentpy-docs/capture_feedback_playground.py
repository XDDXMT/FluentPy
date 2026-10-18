"""Capture and exercise the actual feedback playground, including narrow windows."""
import json
from pathlib import Path
import sys
SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root();sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples'),str(SITE)]
from capture_animations import _capture_font
from showcase import Showcase
from fluentpy import InfoBar,ColorToast,ProgressInfoBar,ProgressToast,Toast,theme
from fluentpy.qt import QtCore,QtWidgets,QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def settle(app,play):
    play.refresh_preview();app.processEvents();app.processEvents()
    message=play._preview
    if message is not None:
        message._reveal.setCurrentTime(message.SHOW_DURATION);message._stack_motion.setCurrentTime(240)
        if hasattr(message,'_progress_motion'):message._progress_motion.setCurrentTime(220)
    app.processEvents()


def capture(app,mode,output):
    owner=Showcase(dark=mode=='dark',page='feedback',restore_preferences=False,startup=False)
    owner.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen);owner.show();QTest.qWait(380)
    play=owner.feedback_playground;settle(app,play)
    path=output/f'feedback-playground-{mode}.png';assert owner.grab().save(str(path))
    checked=0;overflows=[]
    for width in (1120,900):
        owner.resize(width,780 if width==1120 else 650);app.processEvents();QTest.qWait(30)
        for index,cls in enumerate((InfoBar,ColorToast,ProgressInfoBar,ProgressToast,Toast)):
            play.component.setCurrentIndex(index);play.action_check.setChecked(index in (0,1,2))
            play.action_input.setText('查看详情');settle(app,play)
            assert type(play._preview) is cls and not play._preview.isWindow()
            for widget in play._preview.findChildren(QtWidgets.QWidget):
                if widget.isVisible():
                    bounds=QtCore.QRectF(widget.mapTo(play._preview,QtCore.QPoint()),widget.size())
                    assert play._preview._card_rect().contains(bounds),(mode,width,index,widget,bounds,play._preview._card_rect())
                    checked+=1
            scroll=owner.stack.currentWidget();assert scroll.widget().width()<=scroll.viewport().width()
            for control in (play.component,play.title_input,play.detail_input,play.tone,play.position,play.test_button):
                if control.isVisible():
                    bounds=QtCore.QRect(control.mapTo(play,QtCore.QPoint()),control.size())
                    assert play.rect().contains(bounds),(mode,width,control,bounds,play.rect())
                    checked+=1
        play.tabs.set_current_item('embedded');app.processEvents()
        assert play.embedded_examples.notice.isVisible()
        play.embedded_examples.note_input.setText('布局切换保留此内容')
        play.tabs.set_current_item('dialogs');app.processEvents()
        assert play.dialog_button.isVisible()
        play.tabs.set_current_item('embedded');assert play.embedded_examples.note_input.text()=='布局切换保留此内容'
        play.tabs.set_current_item('playground');settle(app,play)
        play.advanced.set_expanded(True,animated=False);app.processEvents()
        scroll=owner.stack.currentWidget();assert scroll.widget().width()<=scroll.viewport().width()
        play.advanced.set_expanded(False,animated=False)
    owner.resize(1120,780);app.processEvents();play.component.setCurrentIndex(2);play.reset_options()
    play.progress.setValue(65);settle(app,play);QTest.qWait(250)
    assert owner.grab().save(str(output/f'feedback-playground-task-{mode}.png'))
    play.component.setCurrentIndex(1);settle(app,play);play.test_stack();assert len(play._messages)==3
    play.tabs.set_current_item('embedded');app.processEvents()
    assert all(not message.isVisible() for message in play._messages.values())
    owner.close();owner.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    return {'mode':mode,'bounds_checked':checked,'window_widths':[1120,900],'errors':overflows,'preview':str(path)}


def main():
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);app.setFont(_capture_font())
    errors=[];sys.excepthook=lambda kind,error,tb:errors.append(str(error))
    results=[capture(app,mode,SITE/'dist/assets/previews') for mode in ('light','dark')]
    assert not errors,errors
    print(json.dumps({'captures':results,'errors':errors},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
