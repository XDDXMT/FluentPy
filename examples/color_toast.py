"""Custom top-strip notifications. Run python examples/color_toast.py."""
from __future__ import annotations
import argparse
from importlib import resources
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fluentpy import (AccentButton,Button,CheckBox,ColorPickerButton,ColorToast,ComboBox,
    FluentScrollBar,HeaderCardWidget,LineEdit,ProgressToast,ToggleSwitch,theme)
from fluentpy.qt import QtCore,QtGui,QtWidgets,Slot
from fluentpy.theme.fonts import ui_font


POSITIONS=(('top-left','左上角'),('top-center','顶部居中'),('top-right','右上角'),
           ('bottom-left','左下角'),('bottom-center','底部居中'),('bottom-right','右下角'))


class ColorToastExamples(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('colorToastExamples')
        self._messages={};self._serial=0;self._last_custom=None
        root=QtWidgets.QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(12)
        settings=QtWidgets.QGridLayout();settings.setHorizontalSpacing(12);settings.setVerticalSpacing(10)
        self.position=ComboBox();self.position.addItems([caption for _,caption in POSITIONS]);self.position.setCurrentIndex(2)
        self.width_combo=ComboBox();self.width_combo.addItems(['自动宽度','240','300','400','520'])
        self.color_picker=ColorPickerButton('#858585',enable_alpha=False)
        self.color_picker.colorChanged.connect(self._custom_color_changed)
        settings.addWidget(QtWidgets.QLabel('位置'),0,0);settings.addWidget(self.position,0,1)
        settings.addWidget(QtWidgets.QLabel('卡片宽度'),0,2);settings.addWidget(self.width_combo,0,3)
        settings.addWidget(QtWidgets.QLabel('自定义颜色'),1,0);settings.addWidget(self.color_picker,1,1)
        self.auto_close=CheckBox('自动关闭');self.auto_close.setChecked(True);settings.addWidget(self.auto_close,1,2,1,2)
        settings.setColumnStretch(1,1);settings.setColumnStretch(3,1);root.addLayout(settings)
        self.title_input=LineEdit('通知标题');self.title_input.setText('操作提示')
        self.detail_input=LineEdit('通知正文');self.detail_input.setText('可以自定义顶部颜色，并在通知中提供操作按钮。')
        self.title_input.setAccessibleName('通知标题');self.detail_input.setAccessibleName('通知正文')
        root.addWidget(self.title_input);root.addWidget(self.detail_input)
        action_settings=QtWidgets.QHBoxLayout();action_settings.setSpacing(12)
        self.action_check=CheckBox('显示操作按钮')
        self.action_text_input=LineEdit('按钮文字');self.action_text_input.setText('查看详情')
        self.action_text_input.setAccessibleName('按钮文字');self.action_text_input.setEnabled(False)
        self.action_check.toggled.connect(self.action_text_input.setEnabled)
        action_settings.addWidget(self.action_check);action_settings.addWidget(self.action_text_input,1)
        root.addLayout(action_settings)
        buttons=QtWidgets.QGridLayout();buttons.setSpacing(10)
        self.tone_buttons={}
        for index,(tone,text) in enumerate((('success','成功'),('error','失败'),('warning','警告'),('accent','注意'),('info','信息'),('custom','自定义'))):
            button=AccentButton(text) if tone=='custom' else Button(text)
            button.clicked.connect(lambda _checked=False,value=tone:self.show_message(value))
            self.tone_buttons[tone]=button;buttons.addWidget(button,index//3,index%3)
        root.addLayout(buttons)
        actions=QtWidgets.QHBoxLayout()
        self.progress_button=Button('显示小型进度提示');self.progress_button.clicked.connect(self.show_progress)
        self.content_button=Button('自定义内容示例');self.content_button.clicked.connect(self.show_content)
        self.clear_button=Button('关闭全部');self.clear_button.clicked.connect(self.dismiss_all)
        actions.addWidget(self.progress_button);actions.addWidget(self.content_button);actions.addWidget(self.clear_button);actions.addStretch();root.addLayout(actions)
        self.result=QtWidgets.QLabel('顶部向下叠放，底部向上叠放。悬停暂停关闭倒计时。')
        self.result.setWordWrap(True);root.addWidget(self.result)
        theme.subscribe(self,self._refresh_theme);self._refresh_theme()

    def _track(self,toast):
        self._serial+=1;toast.setProperty('colorToastDemoIdentity',self._serial)
        self._messages[self._serial]=toast;toast.destroyed.connect(self._released)
        return toast

    @Slot(QtCore.QObject)
    def _released(self,destroyed):
        self._messages.pop(destroyed.property('colorToastDemoIdentity'),None)

    def show_message(self,tone='custom'):
        width=(None,240,300,400,520)[self.width_combo.currentIndex()]
        color=self.color_picker.color() if tone=='custom' else None
        action_text=self.action_text_input.text() if self.action_check.isChecked() else ''
        toast=ColorToast.notify(self.title_input.text() or '通知',detail=self.detail_input.text(),parent=self.window(),
            placement=POSITIONS[self.position.currentIndex()][0],tone='accent' if tone=='custom' else tone,color=color,
            card_width=width,timeout_ms=4000 if self.auto_close.isChecked() else 0,
            action_text=action_text,action_callback=(lambda:self._action_clicked(action_text)) if action_text else None)
        self._track(toast)
        if tone=='custom':self._last_custom=toast
        self.result.setText('已显示通知；可连续点击检查堆叠与补位。')
        return toast

    def _custom_color_changed(self,color):
        if self._last_custom is not None:
            try:
                if self._last_custom.isVisible():self._last_custom.set_color(color)
            except RuntimeError:self._last_custom=None

    def _action_clicked(self,text):
        self.result.setText(f'已触发“{text}”操作。')

    def show_content(self):
        toast=ColorToast('自定义内容','在同一布局中放入输入框和自己的按钮。',self.window(),
            color=self.color_picker.color(),card_width=(None,240,300,400,520)[self.width_combo.currentIndex()])
        toast.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        field=LineEdit('输入备注',toast.content_widget)
        toast.content_layout.addWidget(field)
        row=QtWidgets.QHBoxLayout();row.setSpacing(8)
        apply=Button('应用',toast.content_widget);cancel=Button('取消',toast.content_widget)
        def submit():
            self.result.setText(f'已应用备注：{field.text() or "（空）"}');toast.close()
        apply.clicked.connect(submit);cancel.clicked.connect(toast.close)
        row.addWidget(apply);row.addWidget(cancel);row.addStretch()
        toast.content_layout.addLayout(row)
        self._track(toast);toast.show_at(POSITIONS[self.position.currentIndex()][0])
        self.result.setText('输入框与两个原生按钮均由示例添加，通知自动测量高度。')
        return toast

    def show_progress(self):
        return self._track(ProgressToast.start('Custom toast view',parent=self.window(),
            placement=POSITIONS[self.position.currentIndex()][0],severity='warning',indeterminate=True))

    def dismiss_all(self):
        for toast in list(self._messages.values()):toast.close()

    def hideEvent(self,event):
        self.dismiss_all();super().hideEvent(event)

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(f'QWidget#colorToastExamples {{background:transparent;}} QWidget#colorToastExamples QLabel {{color:{theme.tokens.text};background:transparent;}}')


class ColorToastDemo(QtWidgets.QWidget):
    def __init__(self,*,dark=False):
        super().__init__();theme.set_mode('dark' if dark else 'light')
        self.setObjectName('colorToastDemo');self.setWindowTitle('FluentPy · 顶部色条通知')
        self.setWindowIcon(QtGui.QIcon(str(resources.files('fluentpy.assets').joinpath('brand/fluentpy.svg'))))
        self.resize(800,720);self.setMinimumSize(560,460)
        root=QtWidgets.QVBoxLayout(self);root.setContentsMargins(24,20,24,24);root.setSpacing(16)
        heading=QtWidgets.QHBoxLayout();title=QtWidgets.QLabel('顶部色条通知');title.setObjectName('colorToastTitle')
        heading.addWidget(title,1);heading.addWidget(QtWidgets.QLabel('深色模式'))
        toggle=ToggleSwitch();toggle.setChecked(dark);toggle.toggled.connect(lambda value:theme.set_mode('dark' if value else 'light'))
        heading.addWidget(toggle);root.addLayout(heading)
        scroll=QtWidgets.QScrollArea();scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame);scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBar(FluentScrollBar(parent=scroll));scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content=QtWidgets.QWidget();body=QtWidgets.QVBoxLayout(content);body.setContentsMargins(0,0,0,0)
        card=HeaderCardWidget('通知设置');self.examples=ColorToastExamples();card.body_layout.addWidget(self.examples)
        body.addWidget(card);body.addStretch();scroll.setWidget(content);content.setAutoFillBackground(False);root.addWidget(scroll,1)
        theme.subscribe(self,self._refresh_theme);self._refresh_theme()

    def _refresh_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(f'QWidget#colorToastDemo,QScrollArea {{background:{theme.tokens.background};border:none;}} QLabel {{color:{theme.tokens.text};background:transparent;}} QLabel#colorToastTitle {{font-size:24px;font-weight:600;}}')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dark',action='store_true')
    parser.add_argument('--screenshot',type=Path);parser.add_argument('--quit-after-screenshot',action='store_true');args=parser.parse_args()
    app=QtWidgets.QApplication(sys.argv[:1]);app.setFont(ui_font(14));window=ColorToastDemo(dark=args.dark)
    if args.screenshot:window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(args.screenshot))
            if args.quit_after_screenshot:app.quit()
        QtCore.QTimer.singleShot(250,capture)
    return app.exec()
if __name__=='__main__':raise SystemExit(main())
