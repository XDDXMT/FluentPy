"""Animated button interactions. Run: python examples/buttons.py."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from fluentpy import (ActionMenu, Button, AccentButton, AccentIconButton, TransparentIconButton,
    ToggleButton, ToggleIconButton, PillToggleButton, DropDownButton, AccentDropDownButton,
    SplitButton, AccentSplitButton, LoadingButton, FluentIcon, ToggleSwitch, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


class ButtonExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(18)
        self.result = QtWidgets.QLabel('点击按钮，查看操作反馈。', self)
        self.result.setWordWrap(True)
        ordinary = self._row('普通操作与图标')
        self.standard = Button('普通按钮', self)
        accent = AccentButton('主要操作', self)
        primary_icon = AccentIconButton(FluentIcon.ADD, self)
        primary_icon.setAccessibleName('新建')
        transparent = TransparentIconButton(FluentIcon.SETTINGS, self)
        transparent.setAccessibleName('设置')
        for widget in (self.standard, accent, primary_icon, transparent):
            ordinary.addWidget(widget)
            widget.clicked.connect(lambda _checked=False, button=widget: self.result.setText('已点击：'+(button.text() or button.accessibleName())))
        ordinary.addStretch()

        toggles = self._row('选择状态与胶囊筛选')
        self.toggle = ToggleButton('收藏', self)
        self.toggle.toggled.connect(lambda checked: self.result.setText('收藏已开启' if checked else '收藏已关闭'))
        self.heart = ToggleIconButton(FluentIcon.HEART, self)
        self.heart.setAccessibleName('喜欢')
        toggles.addWidget(self.toggle)
        toggles.addWidget(self.heart)
        self.filters = QtWidgets.QButtonGroup(self)
        self.filters.setExclusive(True)
        for label in ('全部', '文档', '图像'):
            pill = PillToggleButton(label, self)
            self.filters.addButton(pill)
            toggles.addWidget(pill)
            pill.toggled.connect(lambda checked, text=label: self.result.setText('筛选：'+text) if checked else None)
        self.filters.buttons()[0].setChecked(True)
        toggles.addStretch()

        menus = self._row('下拉菜单与拆分操作')
        self.dropdown = DropDownButton('导出为', self, menu=self._export_menu())
        self.primary_dropdown = AccentDropDownButton('新建', self, menu=self._new_menu())
        self.split = SplitButton('保存', self, menu=self._save_menu())
        self.primary_split = AccentSplitButton('发送', self, menu=self._save_menu())
        self.split.clicked.connect(lambda: self.result.setText('主操作：保存'))
        self.primary_split.clicked.connect(lambda: self.result.setText('主操作：发送'))
        for widget in (self.dropdown, self.primary_dropdown, self.split, self.primary_split):
            menus.addWidget(widget)
        menus.addStretch()

        compound = self._row('双行分体按钮：主操作 + 选项')
        self.launch_split = AccentSplitButton('启动游戏', self, description='1.0 · 正式版', menu=self._version_menu())
        self.launch_split.setMinimumWidth(216)
        self.launch_split.clicked.connect(lambda: self.result.setText('主操作：启动游戏（'+self.launch_split.description()+'）'))
        self.format_split = SplitButton('导出文档', self, description='PDF · 当前页面', menu=self._format_menu())
        self.format_split.setMinimumWidth(216)
        self.format_split.clicked.connect(lambda: self.result.setText('主操作：导出文档（'+self.format_split.description()+'）'))
        compound.addWidget(self.launch_split)
        compound.addWidget(self.format_split)
        compound.addStretch()

        busy = self._row('任务加载与重复点击保护')
        self.loading = LoadingButton('保存更改', self)
        self.loading.clicked.connect(self.start_loading)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.finish_loading)
        busy.addWidget(self.loading)
        disabled = Button('不可用', self)
        disabled.setEnabled(False)
        busy.addWidget(disabled)
        busy.addStretch()
        self.body.addWidget(self.result)
        hint = QtWidgets.QLabel('Tab / Shift+Tab 移动焦点，Enter / Space 操作，↓ 展开菜单，Esc 关闭。', self)
        hint.setWordWrap(True)
        self.body.addWidget(hint)

    def _row(self, title):
        label = QtWidgets.QLabel(title, self)
        label.setObjectName('buttonSectionTitle')
        self.body.addWidget(label)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(10)
        self.body.addLayout(row)
        return row

    def _export_menu(self):
        menu = ActionMenu(self)
        menu.add_action('JSON 配置', icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: self.result.setText('导出动作：JSON 配置'))
        menu.add_action('纯文本', icon=FluentIcon.ARROW_EXPORT, callback=lambda: self.result.setText('导出动作：纯文本'))
        menu.add_separator()
        menu.add_action('包含说明', checkable=True, checked=True)
        menu.add_action('发布到云端（未连接）', enabled=False)
        return menu

    def _new_menu(self):
        menu = ActionMenu(self)
        menu.add_action('新建文档', icon=FluentIcon.ADD, callback=lambda: self.result.setText('新建动作：文档'))
        menu.add_action('从模板创建', icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: self.result.setText('新建动作：模板'))
        return menu

    def _save_menu(self):
        menu = ActionMenu(self)
        menu.add_action('另存为…', icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: self.result.setText('更多操作：另存为'))
        menu.add_action('保存副本', icon=FluentIcon.COPY, callback=lambda: self.result.setText('更多操作：保存副本'))
        return menu

    def _version_menu(self):
        menu = ActionMenu(self)
        choices = QtGui.QActionGroup(menu)
        choices.setExclusive(True)
        for version in ('1.0 · 正式版', '1.1 · 预览版', '本地开发版'):
            action = menu.add_action(version, checkable=True, checked=version.startswith('1.0'),
                                     callback=lambda _checked=False, value=version: self._select_version(value))
            choices.addAction(action)
        return menu

    def _select_version(self, version):
        self.launch_split.set_description(version)
        self.result.setText('已选择：'+version+'。点击主按钮才会执行启动操作。')

    def _format_menu(self):
        menu = ActionMenu(self)
        choices = QtGui.QActionGroup(menu)
        choices.setExclusive(True)
        for format_name in ('PDF · 当前页面', 'PNG · 当前页面', 'HTML · 完整文档'):
            action = menu.add_action(format_name, checkable=True, checked=format_name.startswith('PDF'),
                callback=lambda _checked=False, value=format_name: self._select_format(value))
            choices.addAction(action)
        return menu

    def _select_format(self, format_name):
        self.format_split.set_description(format_name)
        self.result.setText('已选择：'+format_name+'。点击主按钮才会执行导出操作。')

    def start_loading(self):
        self.loading.set_loading(True, text='正在保存…')
        self.result.setText('正在演示任务状态；按钮会在完成前阻止再次触发。')
        self._timer.start(1800)

    def finish_loading(self):
        self.loading.set_loading(False)
        self.result.setText('演示完成，可以再次点击。')

    def hideEvent(self, event):
        self._timer.stop()
        self.loading.set_loading(False)
        super().hideEvent(event)


class ButtonDemo(QtWidgets.QWidget):
    def __init__(self, *, dark=False):
        super().__init__()
        theme.set_mode('dark' if dark else 'light')
        self.setObjectName('buttonDemo')
        self.setWindowTitle('FluentPy · 按钮与菜单')
        self.resize(900, 650)
        self.setMinimumSize(620, 560)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 28)
        row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel('按钮与菜单', self)
        title.setObjectName('buttonDemoTitle')
        row.addWidget(title)
        row.addStretch()
        row.addWidget(QtWidgets.QLabel('深色', self))
        toggle = ToggleSwitch(self)
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode('dark' if checked else 'light'))
        row.addWidget(toggle)
        root.addLayout(row)
        root.addStretch()
        self.examples = ButtonExamples(self)
        root.addWidget(self.examples)
        root.addStretch()
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _apply_theme(self):
        self.setFont(ui_font(14))
        self.setStyleSheet(
            f'QWidget#buttonDemo {{ background: {theme.tokens.background}; }}'
            f'QLabel {{ color: {theme.tokens.text}; background: transparent; font-size: 14px; }}'
            'QLabel#buttonDemoTitle { font-size: 22px; font-weight: 600; }'
            'QLabel#buttonSectionTitle { font-weight: 600; }'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dark', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    parser.add_argument('--menu', action='store_true')
    parser.add_argument('--quit-after-screenshot', action='store_true')
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error('--quit-after-screenshot requires --screenshot')
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = ButtonDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()

    def ready():
        if args.menu:
            window.examples.dropdown.show_menu()
        if args.screenshot:
            QtCore.QTimer.singleShot(250, capture)

    def capture():
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(args.screenshot.resolve())):
            raise RuntimeError('Could not save button demo')
        if args.quit_after_screenshot:
            window.close()
            app.quit()

    QtCore.QTimer.singleShot(100, ready)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
