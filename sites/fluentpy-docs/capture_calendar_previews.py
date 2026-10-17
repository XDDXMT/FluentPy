"""Render actual Qt calendars, without showing any desktop window."""
import io
import os
from pathlib import Path
import sys

SITE=Path(__file__).resolve().parent
from source_project import source_root
ROOT=source_root()
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"examples")]
os.environ["QT_QPA_PLATFORM"]="windows" if sys.platform=="win32" else "offscreen"
os.environ["QT_SCALE_FACTOR"]="1"
from fluentpy import CalendarPicker,DateRangePicker,DateTimePicker,QT_API,theme
from fluentpy.qt import QtCore,QtGui,QtWidgets
from fluentpy.theme.fonts import ui_font
from calendar_picker import CalendarPickerDemo
from PIL import Image,ImageChops,ImageStat
if QT_API=="PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def canvas(width,height):
    host=QtWidgets.QWidget();host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    host.setFixedSize(width,height)
    palette=host.palette();palette.setColor(QtGui.QPalette.ColorRole.Window,QtGui.QColor(theme.tokens.background))
    host.setPalette(palette);host.setAutoFillBackground(True)
    return host


def fixture(picker):
    if isinstance(picker,CalendarPicker): picker.set_date(QtCore.QDate(2024,2,26))
    elif isinstance(picker,DateRangePicker):
        picker.set_disabled_weekdays((5,6));picker.set_range(QtCore.QDate(2024,3,13),QtCore.QDate(2024,3,21))
    else: picker.set_date_time(QtCore.QDateTime(QtCore.QDate(2026,2,10),QtCore.QTime(20,0,0)))


def motion(app,output):
    host=canvas(420,520);picker=DateRangePicker(host);picker.setGeometry(35,26,350,36);fixture(picker)
    host.show();app.processEvents();picker.clearFocus()
    def confirm(): picker._popup.calendar.choose((2024,3,25));picker.clearFocus()
    def reset(): fixture(picker);picker.clearFocus()
    def hover():
        cal=picker._popup.calendar
        cal.grid._set_hover(next(i for i,c in enumerate(cal.cells) if c and c[:3]==(2024,3,25)))
    actions=[(400,picker.show_popup),(1000,lambda:picker._popup.calendar.navigate(1)),
             (1400,lambda:picker._popup.calendar.navigate(-1)),(1850,lambda:picker._popup.calendar.choose((2024,3,13))),
             (2250,hover),(2750,confirm),(3600,reset)]
    elapsed=QtCore.QElapsedTimer();elapsed.start();frames=[]
    for target in range(0,4050,30):
        if target>elapsed.elapsed():QTest.qWait(target-elapsed.elapsed())
        while actions and actions[0][0]<=target:actions.pop(0)[1]()
        app.processEvents();buffer=QtCore.QBuffer();buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        assert host.grab().save(buffer,"PNG")
        with Image.open(io.BytesIO(bytes(buffer.data()))) as image:
            frame=image.convert("RGB");assert min(ImageStat.Stat(frame).mean)>180
            frames.append(frame.copy())
    assert ImageChops.difference(frames[0],frames[-1]).getbbox() is None
    frames[0].save(output/"calendar-motion-light.png",optimize=True)
    images=[f.quantize(colors=128) for f in frames]
    images[0].save(output/"calendar-motion-light.gif",save_all=True,append_images=images[1:],duration=30,loop=0,disposal=1,optimize=True)
    host.close();host.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    print("Captured calendar-motion-light.gif:",len(frames),"opaque frames")


def main():
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False)
    font=ui_font(14);font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias|QtGui.QFont.StyleStrategy.NoSubpixelAntialias);app.setFont(font)
    output=SITE/"dist/assets/previews"
    for mode in ("light","dark"):
        theme.set_mode(mode)
        for kind,name in ((CalendarPicker,"calendar-picker"),(DateRangePicker,"date-range-picker"),(DateTimePicker,"date-time-picker")):
            combined=kind is DateTimePicker
            host=canvas(820,600 if combined else 520)
            picker=kind(host);picker.setGeometry(140 if combined else 450,28,300 if combined else 320,36);fixture(picker)
            if not combined:
                field=kind(host);field.setGeometry(28,240,300,36)
            host.show();app.processEvents();picker.show_popup();QTest.qWait(260)
            path=output/f"{name}-light.png" if mode=="light" else ROOT/"build"/f"{name}-dark.png"
            assert host.grab().save(str(path));assert not picker._popup.isWindow();print("Captured",path)
            if mode=="light" and kind is DateRangePicker:
                app.setActiveWindow(host);picker._popup.calendar.grid.setFocus();app.processEvents()
                assert picker._popup.calendar.grid.hasFocus()
                proof=ROOT/"build"/"calendar-range-no-inner-focus.png"
                assert picker._popup.surface.grab().save(str(proof));print("Captured focused calendar proof",proof)
            host.close();host.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        demo=CalendarPickerDemo();demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen);demo.show();app.processEvents()
        path=ROOT/"build"/f"calendar-demo-{mode}.png";assert demo.grab().save(str(path));print("Captured",path)
        demo.close();demo.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        if mode=="light":motion(app,output)


if __name__=="__main__":main()
