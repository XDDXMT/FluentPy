"""Capture the library's own Qt widgets for static documentation previews."""
import os
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
from code_editor import SAMPLE
from date_picker import DatePickerDemo
from capture_showcase import create_settled_showcase
from capture_introduction import create_overview, create_code_summary
from fluentpy import *
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font
if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
app.setFont(ui_font(14))
output = SITE / "dist" / "assets" / "previews"
output.mkdir(parents=True, exist_ok=True)
retained = []
errors = []
sys.excepthook = lambda kind, error, traceback: errors.append(str(error))


def host(*widgets, width=420, height=138, vertical=False):
    root = QtWidgets.QWidget()
    root.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    root.setObjectName("previewRoot")
    background = "#fafbfc" if theme.mode.value == "light" else "#1b1b1b"
    root.setStyleSheet(f'QWidget#previewRoot {{ background: {background}; }} QLabel {{color: {theme.tokens.text}; background: transparent; font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 14px;}}')
    layout = (QtWidgets.QVBoxLayout if vertical else QtWidgets.QHBoxLayout)(root)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(16)
    layout.addStretch()
    for widget in widgets:
        layout.addWidget(widget, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
    layout.addStretch()
    root.resize(width, height)
    root.show()
    retained.append(root)
    return root


def save(name, widget):
    app.processEvents()
    if not widget.grab().save(str(output / f"{name}-{theme.mode.value}.png")):
        raise RuntimeError(f"Unable to save {name}")


for mode in ("light",):
    theme.set_mode(mode)
    theme.set_active(True)
    edit = LineEdit("给这个想法起个名字")
    edit.setText("周末的桌面小工具")
    edit.setFixedWidth(280)
    root = host(edit)
    edit.setFocus()
    edit._focus_animation.setStartValue(0.0)
    edit._focus_animation.setEndValue(1.0)
    edit._focus_animation.setCurrentTime(edit._focus_animation.duration())
    QTest.qWait(180)
    save("line", root)

    edit = SearchLineEdit("搜索你的灵感")
    edit.setFixedWidth(280)
    save("search", host(edit))
    edit = PasswordLineEdit("输入密码")
    edit.setText("fluent-morning")
    edit.setFixedWidth(280)
    save("password", host(edit))
    edit = TextEdit()
    edit.setPlainText("先做一个按钮，\n再把想法变成一个窗口。")
    edit.setFixedSize(320, 94)
    save("textarea", host(edit, height=140))

    save("buttons", host(Button("稍后再说"), AccentButton("保存草稿")))
    save("button-variants", host(TextButton("了解更多"), OutlinedButton("查看详情"), RoundButton("继续"), width=460))
    save("theme", host(AccentButton("保存草稿"), TextButton("了解更多")))
    check = CheckBox("保留上次的选择")
    check.setChecked(True)
    radio = RadioButton("轻量模式")
    radio.setChecked(True)
    save("checks", host(check, radio, width=440))
    switch = ToggleSwitch()
    switch.setChecked(True)
    switch._animation.setEndValue(1.0)
    switch._animation.setCurrentTime(switch._animation.duration())
    save("switch", host(switch, QtWidgets.QLabel("自动保存已开启")))
    choice = ComboBox()
    choice.addItems(["轻量模式", "专注模式", "自由模式"])
    editable = EditableComboBox()
    editable.addItems(["本地草稿", "新的灵感"])
    save("combo", host(choice, editable, width=460))
    count = SpinBox()
    count.setValue(12)
    count.setFixedWidth(110)
    slider = Slider(QtCore.Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(42)
    slider.setFixedWidth(220)
    save("numbers", host(count, slider))

    navigation = NavigationView()
    for key, text, icon in [("home", "首页", FluentIcon.HOME), ("notes", "灵感", FluentIcon.DOCUMENT_SAVE), ("settings", "设置", FluentIcon.SETTINGS)]:
        navigation.add_sub_interface(QtWidgets.QLabel(text + "内容"), fluent_icon(icon), text, key)
    navigation.set_current_route("home", animated=False)
    navigation.sidebar.set_expanded_width(156)
    navigation.sidebar.set_expanded(True)
    navigation.sidebar._width_animation.setCurrentTime(navigation.sidebar._width_animation.duration())
    navigation.setFixedSize(430, 166)
    save("navigation", host(navigation, width=470, height=202))
    pivot = Pivot()
    pivot.add_item("overview", "概览")
    pivot.add_item("details", "详情")
    pivot.add_item("preferences", "偏好")
    pivot.set_current_item("overview", animated=False)
    save("tabs", host(pivot))

    parent = host(QtWidgets.QLabel("正在编辑草稿"), width=700, height=310)
    dialog = FramelessDialog("保存草稿", "把这次灵感留到明天。", parent=parent)
    dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    dialog.setYesButtonText("保存")
    dialog.open()
    QTest.qWait(90)
    save("dialog", dialog)
    dialog.hide()
    masked = MaskedDialog("继续编辑？", "还可以再写一点。", parent=parent)
    masked.open()
    QTest.qWait(190)
    save("masked", parent)
    masked.hide()

    card = Card()
    layout = QtWidgets.QVBoxLayout(card)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.addWidget(QtWidgets.QLabel("今天的灵感"))
    layout.addWidget(QtWidgets.QLabel("留一点空白，给下一次好想法。"))
    save("card", host(card))
    trigger = Button("Top")
    trigger.setFixedSize(186, 40)
    toast_root = host(trigger, width=760, height=220)
    toast_root.layout().setContentsMargins(20, 140, 20, 18)
    app.processEvents()
    toast = Toast("已保存", "灵感已经收好，可以开始下一段创作。", toast_root, target=trigger)
    toast.show_at()
    QTest.qWait(Toast.SHOW_DURATION + 20)
    retained.append(toast)
    save("toast", toast_root)
    toast.hide()
    progress = ProgressBar()
    progress.setRange(0, 100)
    progress.setValue(64)
    progress.setFixedWidth(240)
    save("progress", host(progress, QtWidgets.QLabel("64%")))

    editor = CodeEdit()
    editor.set_indent_size(2)
    editor.set_code(SAMPLE)
    editor.setFixedSize(760, 540)
    root = host(editor, width=800, height=576)
    editor.clearFocus()
    save("code-editor", editor)
    timeline = NoteTimeline()
    timeline.set_notes([NoteEvent(i * .33, .25, 60 + (i % 7)) for i in range(24)] + [NoteEvent(i, .75, 48 + i % 4, 1) for i in range(8)], duration=8)
    timeline.set_position(2.75)
    timeline.setFixedSize(440, 100)
    save("timeline", host(timeline, width=480, height=136))
    for name, factory in (("overview", create_overview), ("code-summary", create_code_summary)):
        widget = factory()
        retained.append(widget)
        widget.show()
        app.processEvents()
        focused = app.focusWidget()
        if focused:
            focused.clearFocus()
        save(name, widget)
    date_demo = DatePickerDemo()
    date_demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    date_demo.show()
    app.processEvents()
    date_demo.save_preview(output / "date-picker-light.png", popup=True)
    date_demo.picker._popup.close()
    retained.append(date_demo)
    showcase = create_settled_showcase(app)
    retained.append(showcase)
    save("showcase", showcase)
    for widget in retained:
        widget.hide()

print(f"Saved {len(list(output.glob('*.png')))} Qt screenshots; callback errors: {len(errors)}")
if errors:
    print(errors)
    raise SystemExit(1)
