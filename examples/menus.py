"""Native actions, cascades, inline Qt controls, context and tray menus."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from fluentpy import (ActionMenu, SystemTrayMenu, ComboBox, CheckBox, LineEdit, ToolTipSlider,
    Button, FluentIcon, fluent_icon, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from component_playground import Playground, PlaygroundWindow


class _ContextTarget(QtWidgets.QFrame):
    """An ordinary Qt frame handling native and keyboard context requests."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('右键菜单测试区域')
        self.setToolTip('点击鼠标右键，或使用 Shift+F10 / 菜单键')
        self._pending_point = None
        self._context_clock = QtCore.QElapsedTimer()
        self._context_clock.start()
        self._last_context_time = -1000
        self._last_context_point = None

    def contextMenuEvent(self, event):
        self._pending_point = None
        point = self.rect().center() if event.reason() == QtGui.QContextMenuEvent.Reason.Keyboard else event.pos()
        now = self._context_clock.elapsed()
        if (event.reason() == QtGui.QContextMenuEvent.Reason.Keyboard or
                point != self._last_context_point or now - self._last_context_time > 80):
            self._last_context_time = now
            self._last_context_point = QtCore.QPoint(point)
            self.customContextMenuRequested.emit(point)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Native platforms normally deliver ContextMenu after release.
            # Qt test/input backends that only send mouse events use the same
            # context event on the next turn; a native event cancels this path.
            self._pending_point = event.position().toPoint()
            QtCore.QTimer.singleShot(0, self._complete_context_request)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # A new click is always a new request, even at the same point.
            # Only the native event/fallback pair of that click is deduplicated.
            self._last_context_point = None
        super().mousePressEvent(event)

    def _complete_context_request(self):
        point = self._pending_point
        if point is not None:
            self._pending_point = None
            QtWidgets.QApplication.sendEvent(self, QtGui.QContextMenuEvent(
                QtGui.QContextMenuEvent.Reason.Mouse, point, self.mapToGlobal(point)))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Menu or (
                event.key() == QtCore.Qt.Key.Key_F10 and event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier):
            point = self.rect().center()
            QtWidgets.QApplication.sendEvent(self, QtGui.QContextMenuEvent(
                QtGui.QContextMenuEvent.Reason.Keyboard, point, self.mapToGlobal(point)))
            event.accept()
            return
        super().keyPressEvent(event)


class MenuExamples(Playground):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.menu = None
        self.tray_icon = None
        self.dynamic_action = None
        self.class_label = QtWidgets.QLabel('ActionMenu')
        self.preview_layout.addWidget(self.class_label)
        self.preview_layout.addStretch()
        self.context_target = _ContextTarget()
        self.context_target.setObjectName('contextMenuTarget')
        self.context_target.setMinimumHeight(160)
        context_layout = QtWidgets.QVBoxLayout(self.context_target)
        self.context_label = QtWidgets.QLabel('在此区域点击鼠标右键\nShift+F10 / 菜单键也可打开')
        self.context_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.context_label.setWordWrap(True)
        self.context_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        context_layout.addWidget(self.context_label)
        self.preview_layout.addWidget(self.context_target)
        self.open_button = Button('打开菜单（备用）')
        self.open_button.setToolTip('鼠标右键之外的备用打开方式')
        self.preview_layout.addWidget(self.open_button, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.preview_layout.addStretch()
        self.hint = QtWidgets.QLabel()
        self.hint.setWordWrap(True)
        self.preview_layout.addWidget(self.hint)
        self.kind = ComboBox()
        self.kind.addItems(['多级右键菜单', '勾选与互斥', '原生控件混排', '常用操作', '系统托盘菜单'])
        self.field('菜单类型', self.kind)
        self.command = LineEdit()
        self.command.setText('打开文档')
        self.field('主要动作文字', self.command)
        self.icons = CheckBox('显示图标')
        self.icons.setChecked(True)
        self.form.addWidget(self.icons)
        self.disabled = CheckBox('展示禁用项')
        self.disabled.setChecked(True)
        self.form.addWidget(self.disabled)
        self.tray_button = Button('显示系统托盘图标')
        self.form.addWidget(self.tray_button)
        self.form.addStretch()
        self.kind.currentIndexChanged.connect(self.rebuild)
        self.icons.toggled.connect(self.rebuild)
        self.disabled.toggled.connect(self.rebuild)
        self.command.textChanged.connect(self._rename)
        self.open_button.clicked.connect(self._open_special)
        self.context_target.customContextMenuRequested.connect(self._context_menu)
        self.tray_button.clicked.connect(self.toggle_tray)
        theme.subscribe(self, self._apply_context_theme)
        self._apply_context_theme()
        self.rebuild()

    def _add(self, menu, title, icon=None, **options):
        action = menu.add_action(title, icon=icon if self.icons.isChecked() else None, **options)
        action.triggered.connect(lambda checked=False, item=action: self.result.setText('已执行：'+item.text()))
        return action

    def rebuild(self, *args):
        if self.tray_icon is not None:
            self.tray_icon.hide()
            self.tray_icon.setContextMenu(None)
        if self.menu is not None:
            self.menu.hide()
            self.menu.deleteLater()
        index = self.kind.currentIndex()
        self.class_label.setText('SystemTrayMenu' if index == 4 else 'ActionMenu')
        menu = SystemTrayMenu(self) if index == 4 else ActionMenu(self)
        self.menu = menu
        self.dynamic_action = self._add(menu, self.command.text(), FluentIcon.DOCUMENT_SAVE)
        if index == 0:
            sub = menu.add_menu('导出', icon=FluentIcon.ARROW_EXPORT if self.icons.isChecked() else None)
            self._add(sub, 'JSON 配置', FluentIcon.CODE)
            images = sub.add_menu('图像格式')
            self._add(images, 'PNG 图像')
            self._add(images, 'SVG 图像')
            menu.add_separator()
            self._add(menu, '复制路径', FluentIcon.COPY)
            hint = '悬停或点击带箭头的条目；→ 展开子菜单，← 返回，Esc 逐级关闭。'
        elif index == 1:
            menu.add_separator()
            self._add(menu, '显示扩展名', checkable=True, checked=True)
            group = QtGui.QActionGroup(menu)
            group.setExclusive(True)
            for number, title in enumerate(('按名称排序', '按修改日期排序')):
                group.addAction(self._add(menu, title, checkable=True, checked=number == 0))
            hint = '普通勾选可独立开关；排序动作交给原生 QActionGroup 管理互斥，选中项显示圆点。'
        elif index == 2:
            panel = QtWidgets.QWidget()
            panel.setMinimumWidth(240)
            layout = QtWidgets.QVBoxLayout(panel)
            layout.setContentsMargins(7, 8, 7, 8)
            layout.addWidget(QtWidgets.QLabel('筛选与数值'))
            self.widget_input = LineEdit('筛选名称')
            layout.addWidget(self.widget_input)
            self.widget_slider = ToolTipSlider()
            self.widget_slider.setRange(50, 150)
            self.widget_slider.setValue(100)
            self.widget_slider.setValueFormat('{value}')
            layout.addWidget(self.widget_slider)
            self.widget_slider.valueChanged.connect(lambda value: self.result.setText(f'当前值：{value}'))
            menu.add_widget(panel)
            menu.add_separator()
            self._add(menu, '应用设置', FluentIcon.CHECKMARK)
            hint = '同一个菜单混排原生输入框、滑块与动作。操作控件保持菜单展开，点击动作后关闭。'
        elif index == 3:
            self._add(menu, '复制', FluentIcon.COPY, shortcut='Ctrl+C')
            menu.add_separator()
            self._add(menu, '查看属性', FluentIcon.SETTINGS)
            hint = '菜单定位到右键点击处，靠近窗口边缘时自动避让；只在本示例区域内响应。'
        else:
            menu.addSeparator()
            self._add(menu, '保持后台运行', checkable=True, checked=True)
            menu.add_action('隐藏托盘图标', callback=self.hide_tray)
            hint = '这里使用真正的 QMenu，可交给 QSystemTrayIcon。只有点击右侧按钮才显示托盘图标。'
        if self.disabled.isChecked():
            self._add(menu, '发布到云端（未连接）', enabled=False)
        self.context_label.setText('在此区域点击鼠标右键\nShift+F10 / 菜单键也可打开' if index < 4 else
                                   '右键此区域预览托盘菜单\n也可在系统托盘中打开')
        self.tray_button.setVisible(index == 4)
        self.tray_button.setText('显示系统托盘图标')
        self.hint.setText(hint)
        self.result.setText('在左侧测试区域点击鼠标右键；右侧设置会立即应用到菜单。')

    def _apply_context_theme(self):
        self.context_target.setStyleSheet(f'QFrame#contextMenuTarget {{background:{theme.tokens.surface};border:1px solid {theme.tokens.border};border-radius:6px;}}')
        self.context_label.setStyleSheet(f'color:{theme.tokens.text_muted};background:transparent;border:none;')

    def _rename(self, text):
        if self.dynamic_action is not None:
            self.dynamic_action.setText(text)

    def _context_menu(self, point):
        if isinstance(self.menu, ActionMenu):
            return self.menu.popup_at(self.context_target, point)
        self.menu.popup(self.context_target.mapToGlobal(point))
        return True

    def _open_special(self):
        return self._context_menu(self.context_target.rect().center())

    def toggle_tray(self):
        if self.tray_icon is not None and self.tray_icon.isVisible():
            self.hide_tray()
            return
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            self.result.setText('当前桌面未提供系统托盘，可使用上方按钮预览菜单。')
            return
        if self.tray_icon is None:
            self.tray_icon = QtWidgets.QSystemTrayIcon(fluent_icon(FluentIcon.SETTINGS), self)
            self.tray_icon.setToolTip('FluentPy 菜单演示')
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        self.tray_button.setText('隐藏系统托盘图标')
        self.result.setText('托盘图标已显示；右键打开菜单。')

    def hide_tray(self):
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self.tray_button.setText('显示系统托盘图标')

    def hideEvent(self, event):
        self.hide_tray()
        if self.menu is not None:
            self.menu.dismiss(immediate=True) if isinstance(self.menu, ActionMenu) else self.menu.hide()
        super().hideEvent(event)


class MenuDemo(PlaygroundWindow):
    def __init__(self, dark=False):
        super().__init__('右键菜单', MenuExamples, dark=dark)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    demo = MenuDemo(args.dark)
    demo.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
