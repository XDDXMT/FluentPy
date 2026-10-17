"""Build and capture a small workspace using real FluentPy components."""
from pathlib import Path
import sys

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import (
    AccentButton, Button, Card, CodeEdit, ComboBox, FluentIcon, NavigationView,
    ProgressBar, LineEdit, ToggleSwitch, fluent_icon, theme,
)
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme.fonts import ui_font


def label(text, size=14, *, bold=False, muted=False):
    widget = QtWidgets.QLabel(text)
    font = ui_font(size)
    font.setBold(bold)
    widget.setFont(font)
    widget.setStyleSheet(f"color: {'#717884' if muted else '#242833'}; background: transparent;")
    return widget


def create_overview():
    root = QtWidgets.QWidget()
    root.setObjectName("overviewRoot")
    root.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    root.setStyleSheet("QWidget#overviewRoot {background: #f7f9fc;}")
    outer = QtWidgets.QVBoxLayout(root)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    titlebar = QtWidgets.QWidget()
    titlebar.setStyleSheet("background: #ffffff;")
    title_layout = QtWidgets.QHBoxLayout(titlebar)
    title_layout.setContentsMargins(22, 12, 22, 12)
    title_layout.addWidget(label("FluentPy", 15, bold=True))
    title_layout.addWidget(label(" /  灵感工作区", 12, muted=True))
    title_layout.addStretch()
    title_layout.addWidget(label("桌面应用示例", 11, muted=True))
    outer.addWidget(titlebar)
    navigation = NavigationView()
    outer.addWidget(navigation, 1)
    page = QtWidgets.QWidget()
    content = QtWidgets.QVBoxLayout(page)
    content.setContentsMargins(28, 20, 28, 24)
    content.setSpacing(12)
    content.addWidget(label("把想法变成一个窗口", 24, bold=True))
    content.addWidget(label("用熟悉的 Python 和 Qt，组合出自己的桌面界面。", 13, muted=True))
    content.addSpacing(4)
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(14)
    project = Card()
    form = QtWidgets.QVBoxLayout(project)
    form.setContentsMargins(20, 17, 20, 18)
    form.setSpacing(10)
    form.addWidget(label("创建一个新项目", 15, bold=True))
    form.addWidget(label("项目名称", 12, muted=True))
    name = LineEdit("给这个想法起个名字")
    name.setText("我的第一个桌面应用")
    form.addWidget(name)
    form.addWidget(label("从组件开始，再把它们组合成页面。", 12, muted=True))
    form.addStretch()
    actions = QtWidgets.QHBoxLayout()
    actions.setSpacing(9)
    actions.addWidget(AccentButton("创建项目"))
    actions.addWidget(Button("浏览示例"))
    actions.addStretch()
    form.addLayout(actions)
    row.addWidget(project, 3)
    preferences = Card()
    settings = QtWidgets.QVBoxLayout(preferences)
    settings.setContentsMargins(18, 17, 18, 18)
    settings.setSpacing(10)
    settings.addWidget(label("工作区偏好", 15, bold=True))
    choice = ComboBox()
    choice.addItems(["轻量模式", "专注模式"])
    settings.addWidget(choice)
    switch_row = QtWidgets.QHBoxLayout()
    switch_row.addWidget(label("自动保存", 12))
    switch_row.addStretch()
    switch = ToggleSwitch()
    switch.setChecked(True)
    switch._animation.setCurrentTime(switch._animation.duration())
    switch_row.addWidget(switch)
    settings.addLayout(switch_row)
    settings.addStretch()
    settings.addWidget(label("准备进度 · 64%", 12, muted=True))
    progress = ProgressBar()
    progress.setValue(64)
    settings.addWidget(progress)
    row.addWidget(preferences, 2)
    content.addLayout(row, 1)
    content.addWidget(label("导航  /  卡片  /  输入  /  按钮  /  状态反馈", 11, muted=True))
    navigation.add_sub_interface(page, fluent_icon(FluentIcon.HOME), "工作台", "workspace")
    navigation.add_sub_interface(QtWidgets.QLabel("项目"), fluent_icon(FluentIcon.DOCUMENT_SAVE), "我的项目", "projects")
    navigation.add_sub_interface(QtWidgets.QLabel("设置"), fluent_icon(FluentIcon.SETTINGS), "设置", "settings", "bottom")
    navigation.sidebar.set_expanded_width(170)
    navigation.sidebar.set_expanded(True)
    navigation.sidebar._width_animation.setCurrentTime(navigation.sidebar._width_animation.duration())
    navigation.set_current_route("workspace", animated=False)
    root.resize(920, 400)
    return root


def create_code_summary():
    editor = CodeEdit()
    editor.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    editor.set_indent_size(2)
    editor.set_code('{\n  "project": {\n    "name": "FluentPy",\n    "enabled": true,\n    "indentSize": 2\n  }\n}')
    editor.resize(420, 170)
    return editor


def main():
    app = QtWidgets.QApplication([])
    app.setFont(ui_font(14))
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("light")
    theme.set_active(True)
    output = SITE / "dist" / "assets" / "previews"
    retained = []
    errors = []
    sys.excepthook = lambda kind, error, traceback: errors.append(str(error))
    for name, factory in (("overview", create_overview), ("code-summary", create_code_summary)):
        widget = factory()
        retained.append(widget)
        widget.show()
        app.processEvents()
        focused = app.focusWidget()
        if focused:
            focused.clearFocus()
        app.processEvents()
        assert widget.grab().save(str(output / f"{name}-light.png"))
        widget.hide()
    assert not errors, errors
    print("Captured the FluentPy workspace and the introductory code preview in light mode.")


if __name__ == "__main__":
    main()
