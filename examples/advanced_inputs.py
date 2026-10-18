"""Affix fields and segmented passwords. Run python examples/advanced_inputs.py."""
import argparse
from importlib import resources
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fluentpy import AffixLineEdit,Button,HeaderCardWidget,PinCodeEdit,ToggleSwitch,theme
from fluentpy.qt import QtCore,QtGui,QtWidgets
from fluentpy.theme.fonts import ui_font


class AdvancedInputExamples(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('advancedInputExamples')
        root=QtWidgets.QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(16)
        affixes=HeaderCardWidget('前缀与后缀')
        self.url=AffixLineEdit('example.hostname',prefix='https://',suffix='.com')
        self.url.setAccessibleName('网站域名');self.url.setMaximumWidth(440)
        self.amount=AffixLineEdit('输入金额',prefix='¥',suffix='元')
        self.amount.setAccessibleName('金额');self.amount.setMaximumWidth(440)
        affixes.body_layout.addWidget(self.url);affixes.body_layout.addWidget(self.amount)
        note=QtWidgets.QLabel('前后缀固定显示；清除、复制与 text() 只操作中间输入值。')
        note.setWordWrap(True);affixes.body_layout.addWidget(note)
        root.addWidget(affixes)
        password=HeaderCardWidget('分格密码')
        self.pin=PinCodeEdit(4,masked=True)
        password.body_layout.addWidget(self.pin)
        row=QtWidgets.QHBoxLayout();row.addWidget(QtWidgets.QLabel('显示密码'))
        self.reveal=ToggleSwitch();self.reveal.toggled.connect(lambda checked:self.pin.set_masked(not checked))
        row.addWidget(self.reveal);row.addStretch()
        clear=Button('清空');clear.clicked.connect(self.pin.clear);row.addWidget(clear)
        password.body_layout.addLayout(row)
        self.result=QtWidgets.QLabel('支持整段粘贴、自动前进、方向键和退格回删。')
        self.result.setWordWrap(True);password.body_layout.addWidget(self.result)
        self.pin.textChanged.connect(lambda text:self.result.setText(f'已填写 {len(text)} / 4 位'))
        self.pin.completed.connect(lambda text:self.result.setText('4位密码已填写完整。'))
        self.pin.inputRejected.connect(self.result.setText)
        root.addWidget(password)
        code=HeaderCardWidget('六位验证码')
        self.otp=PinCodeEdit(6,masked=False);self.otp.setAccessibleName('六位验证码')
        code.body_layout.addWidget(self.otp)
        label=QtWidgets.QLabel('使用同一个 PinCodeEdit，设置 masked=False 显示字符。');label.setWordWrap(True)
        code.body_layout.addWidget(label);root.addWidget(code)
        theme.subscribe(self,self._refresh);self._refresh()

    def _refresh(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(f'QWidget#advancedInputExamples {{ background:transparent; }} QWidget#advancedInputExamples QLabel {{color:{theme.tokens.text};background:transparent;}}')


class AdvancedInputDemo(QtWidgets.QWidget):
    def __init__(self,dark=False):
        super().__init__();theme.set_mode('dark' if dark else 'light')
        self.setWindowTitle('FluentPy · 前后缀与分格输入');self.setObjectName('advancedInputDemo')
        self.setWindowIcon(QtGui.QIcon(str(resources.files('fluentpy.assets').joinpath('brand/fluentpy.svg'))))
        self.resize(620,650);root=QtWidgets.QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QtWidgets.QLabel('前后缀与分格输入');title.setObjectName('inputTitle');root.addWidget(title)
        self.examples=AdvancedInputExamples();root.addWidget(self.examples);root.addStretch()
        theme.subscribe(self,self._refresh);self._refresh()

    def _refresh(self):
        self.setFont(ui_font(14));self.setStyleSheet(f'QWidget#advancedInputDemo {{background:{theme.tokens.background};}} QLabel {{color:{theme.tokens.text};background:transparent;}} QLabel#inputTitle {{font-size:24px;font-weight:600;}}')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dark',action='store_true')
    parser.add_argument('--screenshot',type=Path);parser.add_argument('--quit-after-screenshot',action='store_true');args=parser.parse_args()
    app=QtWidgets.QApplication(sys.argv[:1]);app.setFont(ui_font(14));window=AdvancedInputDemo(args.dark)
    if args.screenshot:window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(args.screenshot))
            if args.quit_after_screenshot:app.quit()
        QtCore.QTimer.singleShot(250,capture)
    return app.exec()
if __name__=='__main__':raise SystemExit(main())
