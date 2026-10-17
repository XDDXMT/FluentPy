"""Calendar, date range and date/time demo: python examples/calendar_picker.py."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fluentpy import CalendarPicker, DateRangePicker, DateTimePicker, Button, CheckBox, HeaderCardWidget, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


class CalendarExamples(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("calendarExamples")
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(16)
        self.single=CalendarPicker();self.interval=DateRangePicker();self.datetime=DateTimePicker()
        self.single.set_date(QtCore.QDate.currentDate())
        today=QtCore.QDate.currentDate()
        self.interval.set_range(today,today.addDays(7))
        self.datetime.set_date_time(QtCore.QDateTime.currentDateTime())
        for picker,title,hint in (
            (self.single,"日历日期","按天选择；点击月份标题可以快速选择月份和年份。"),
            (self.interval,"日期区间","点击起点，再点击终点；悬停预览整个区间，也可以反向选择。"),
            (self.datetime,"日期与时间","日历搭配时、分、秒独立滚轮；确认后保存，取消保留原值。"),
        ):
            card=HeaderCardWidget(title)
            description=QtWidgets.QLabel(hint);description.setObjectName("muted");description.setWordWrap(True)
            card.body_layout.addWidget(description)
            row=QtWidgets.QHBoxLayout();row.setSpacing(12)
            picker.setMinimumWidth(260);picker.setMaximumWidth(340)
            row.addWidget(picker,1)
            clear=Button("清空");clear.clicked.connect(picker.clear);row.addWidget(clear)
            row.addStretch();card.body_layout.addLayout(row)
            result=QtWidgets.QLabel(picker.text());result.setObjectName("selection");result.setWordWrap(True)
            card.body_layout.addWidget(result)
            if picker is self.single:
                picker.dateChanged.connect(lambda value,label=result:label.setText(value.toString("yyyy-MM-dd") if value.isValid() else "尚未选择"))
            elif picker is self.interval:
                picker.rangeChanged.connect(lambda start,end,label=result:label.setText(f"{start.toString('yyyy-MM-dd')} → {end.toString('yyyy-MM-dd')}" if start.isValid() else "尚未选择"))
                self.weekends=CheckBox("禁用周末作为起止日期")
                self.weekends.toggled.connect(lambda enabled:self.interval.set_disabled_weekdays((5,6) if enabled else ()))
                card.body_layout.addWidget(self.weekends)
            else:
                picker.dateTimeChanged.connect(lambda value,label=result:label.setText(value.toString("yyyy-MM-dd HH:mm:ss") if value.isValid() else "尚未选择"))
            layout.addWidget(card)
        theme.subscribe(self,self._refresh_theme);self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f"QWidget#calendarExamples QLabel {{ color:{theme.tokens.text}; background:transparent; }}"
            f"QWidget#calendarExamples QLabel#muted {{ color:{theme.tokens.text_muted}; font-size:12px; }}"
            f"QWidget#calendarExamples QLabel#selection {{ color:{theme.tokens.accent}; font-size:12px; }}")


class CalendarPickerDemo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("calendarDemo")
        self.setWindowTitle("FluentPy · 日历与日程")
        self.setWindowIcon(QtGui.QIcon(str(ROOT/"src/fluentpy/assets/brand/fluentpy.svg")))
        self.resize(940,820);self.setMinimumSize(720,650)
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(32,24,32,24);layout.setSpacing(16)
        top=QtWidgets.QHBoxLayout()
        title=QtWidgets.QLabel("把日程，安排得从容一点。")
        title.setObjectName("title");top.addWidget(title);top.addStretch()
        top.addWidget(QtWidgets.QLabel("深色"));self.dark=ToggleSwitch()
        self.dark.toggled.connect(lambda checked:theme.set_mode("dark" if checked else "light"))
        self.dark.setChecked(theme.mode.value=="dark");top.addWidget(self.dark);layout.addLayout(top)
        self.examples=CalendarExamples(self);layout.addWidget(self.examples)
        hint=QtWidgets.QLabel("方向键移动 · PageUp／PageDown切月 · Ctrl加翻页键切年 · Tab切换焦点 · Esc取消")
        hint.setWordWrap(True);hint.setObjectName("muted");layout.addWidget(hint)
        backend=QtWidgets.QLabel("后端："+self.examples.single.acceleration_backend()+" · C优先，Python兼容")
        backend.setObjectName("muted");layout.addWidget(backend)
        theme.subscribe(self,self._refresh_theme);self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(f"QWidget#calendarDemo {{ background:{theme.tokens.background}; }}"
            f"QWidget#calendarDemo > QLabel {{ color:{theme.tokens.text}; }}"
            f"QLabel#title {{ font-size:24px; font-weight:600; color:{theme.tokens.text}; }}"
            f"QLabel#muted {{ color:{theme.tokens.text_muted}; font-size:12px; }}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark",action="store_true")
    parser.add_argument("--open",choices=("single","range","datetime"))
    args=parser.parse_args()
    app=QtWidgets.QApplication(sys.argv);app.setFont(ui_font(14));theme.set_mode("dark" if args.dark else "light")
    demo=CalendarPickerDemo();demo.show()
    if args.open:
        picker={"single":demo.examples.single,"range":demo.examples.interval,"datetime":demo.examples.datetime}[args.open]
        QtCore.QTimer.singleShot(120,picker.show_popup)
    return app.exec()


if __name__=="__main__": raise SystemExit(main())
