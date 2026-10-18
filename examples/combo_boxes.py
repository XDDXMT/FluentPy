"""One focused playground for the model/view combo family."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fluentpy import (ComboBox, EditableComboBox, ModelComboBox, EditableModelComboBox,
    MultiSelectionComboBox, TreeComboBox, MultiSelectionTreeComboBox, TransparentComboBox,
    FontComboBox, HeaderCardWidget, LineEdit, Button, CheckBox, ToggleSwitch, FluentWindow, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font

KINDS = [
    ('普通选择', ComboBox, '选项可以绑定业务数据；也可以保留未选择状态。'),
    ('可编辑选择', EditableComboBox, '选择已有选项，或输入新名称后按 Enter。支持 Qt 补全器。'),
    ('模型绑定', ModelComboBox, '绑定原生 Qt 模型。修改右侧名称，列表与已选文字会一起更新。'),
    ('可编辑模型', EditableModelComboBox, '直接编辑模型中的选项；Enter 添加的新选项也会写入同一模型。'),
    ('多选标签', MultiSelectionComboBox, '下拉后连续选择多项；点击标签上的 × 移除。更多标签折叠为数量。'),
    ('树形选择', TreeComboBox, '展开文件夹选择项目；支持搜索子项，并保留完整的父子路径。'),
    ('树形多选', MultiSelectionTreeComboBox, '跨分组选择多个子项，选择状态与源模型相互独立。'),
    ('透明样式', TransparentComboBox, '适合工具栏。保留悬停和键盘焦点，可单独设置文字颜色。'),
    ('系统字体', FontComboBox, '从系统字体中搜索，列表直接预览字形。选择后更新下面的样本文字。'),
]


def tree_model(parent):
    model = QtGui.QStandardItemModel(parent)
    for title, names in [('界面', ['主窗口', '设置页面', '组件预览']), ('资源', ['主题配色', '应用图标', '翻译文件'])]:
        group = QtGui.QStandardItem(title)
        for name in names:
            item = QtGui.QStandardItem(name)
            item.setData(title+'/'+name, QtCore.Qt.ItemDataRole.UserRole)
            group.appendRow(item)
        model.appendRow(group)
    return model


class ComboBoxExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview = None
        self.shared_model = QtGui.QStandardItemModel(self)
        for name, data in [('开发环境', 'dev'), ('测试环境', 'test'), ('生产环境', 'prod')]:
            item = QtGui.QStandardItem(name)
            item.setData(data, QtCore.Qt.ItemDataRole.UserRole)
            self.shared_model.appendRow(item)
        self.tree_model = tree_model(self)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)
        self.columns = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
        self.columns.setSpacing(18)
        root.addLayout(self.columns)
        self.canvas = QtWidgets.QFrame()
        self.canvas.setObjectName('comboDemoCanvas')
        self.canvas.setMinimumHeight(285)
        left = QtWidgets.QVBoxLayout(self.canvas)
        left.setContentsMargins(20, 18, 20, 18)
        self.class_name = QtWidgets.QLabel()
        self.class_name.setObjectName('comboDemoType')
        left.addWidget(self.class_name)
        left.addStretch()
        self.slot = QtWidgets.QVBoxLayout()
        self.slot.setContentsMargins(0, 14, 0, 14)
        left.addLayout(self.slot)
        self.result = QtWidgets.QLabel()
        self.result.setWordWrap(True)
        self.result.setMinimumHeight(44)
        left.addWidget(self.result)
        left.addStretch()
        self.hint = QtWidgets.QLabel('点击展开 · ↑ ↓ 移动 · Enter 选择 · Esc 收起')
        self.hint.setWordWrap(True)
        left.addWidget(self.hint)
        self.columns.addWidget(self.canvas, 1)
        self.controls = QtWidgets.QWidget()
        right = QtWidgets.QVBoxLayout(self.controls)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(9)
        right.addWidget(QtWidgets.QLabel('组件类型'))
        self.kind = ComboBox()
        self.kind.addItems([name for name, cls, hint in KINDS])
        right.addWidget(self.kind)
        right.addWidget(QtWidgets.QLabel('提示文字'))
        self.placeholder = LineEdit('未选择时显示')
        self.placeholder.setText('请选择一个环境')
        right.addWidget(self.placeholder)
        self.model_caption = QtWidgets.QLabel('第一个模型选项的名称')
        right.addWidget(self.model_caption)
        self.model_name = LineEdit()
        self.model_name.setText('开发环境')
        right.addWidget(self.model_name)
        self.enabled = CheckBox('允许交互')
        self.enabled.setChecked(True)
        right.addWidget(self.enabled)
        self.clear_button = Button('清除选择')
        right.addWidget(self.clear_button)
        right.addStretch()
        self.columns.addWidget(self.controls)
        self.description = QtWidgets.QLabel()
        self.description.setWordWrap(True)
        root.addWidget(self.description)
        self.kind.currentIndexChanged.connect(self.change_kind)
        self.placeholder.textChanged.connect(self._placeholder)
        self.enabled.toggled.connect(lambda checked: self.preview.setEnabled(checked))
        self.model_name.textChanged.connect(self._rename)
        self.clear_button.clicked.connect(self.clear_selection)
        self.change_kind(0)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def change_kind(self, index):
        if self.preview is not None:
            self.slot.removeWidget(self.preview)
            self.preview.hide()
            self.preview.deleteLater()
        title, cls, hint = KINDS[index]
        widget = cls(self.canvas)
        self.preview = widget
        if cls in (ModelComboBox, EditableModelComboBox):
            widget.setModel(self.shared_model)
        elif cls in (TreeComboBox, MultiSelectionTreeComboBox):
            widget.setModel(self.tree_model)
        elif cls is not FontComboBox:
            for text, data in [('开发环境', 'dev'), ('测试环境', 'test'), ('生产环境', 'prod'), ('离线环境', 'offline')]:
                widget.addItem(text, data)
        if cls is MultiSelectionComboBox:
            widget.setSelectedIndexes([0, 1])
        elif cls is MultiSelectionTreeComboBox:
            widget.setSelectedIndexes([self.tree_model.index(0, 0, self.tree_model.index(0, 0))])
        elif cls is not FontComboBox:
            widget.setCurrentIndex(-1)
        if cls is TransparentComboBox:
            widget.setCurrentIndex(1)
            widget.setTextColor(theme.tokens.accent)
        widget.setPlaceholderText(self.placeholder.text())
        widget.setEnabled(self.enabled.isChecked())
        widget.currentTextChanged.connect(self._result)
        if isinstance(widget, MultiSelectionComboBox):
            widget.selectionChanged.connect(self._result)
        if isinstance(widget, TreeComboBox):
            widget.currentModelIndexChanged.connect(self._result)
        if isinstance(widget, FontComboBox):
            widget.currentFontChanged.connect(lambda font: self.result.setFont(font))
        self.slot.addWidget(widget)
        widget.show()
        self.class_name.setText(cls.__name__)
        self.description.setText(hint)
        self.model_name.setVisible(cls in (ModelComboBox, EditableModelComboBox))
        self.model_caption.setVisible(self.model_name.isVisibleTo(self.controls))
        self._result()

    def _result(self, *args):
        widget = self.preview
        self.result.setFont(ui_font(14))
        if isinstance(widget, FontComboBox):
            self.result.setFont(widget.currentFont())
            self.result.setText('FluentPy 让选择更清楚 · Aa 0123')
        elif isinstance(widget, MultiSelectionComboBox):
            self.result.setText('已选择：'+('、'.join(widget.selectedTexts()) or '无'))
        elif isinstance(widget, TreeComboBox):
            self.result.setText('路径：'+(' / '.join(widget.currentPath()) or '未选择'))
        else:
            self.result.setText('当前选择：'+(widget.currentText() or '未选择')+'\n绑定数据：'+str(widget.currentData()))

    def _rename(self, text):
        self.shared_model.setData(self.shared_model.index(0, 0), text)

    def _placeholder(self, text):
        self.preview.setPlaceholderText(text)

    def clear_selection(self):
        if isinstance(self.preview, MultiSelectionComboBox):
            self.preview.clearSelection()
        else:
            self.preview.setCurrentIndex(-1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= 620
        self.columns.setDirection(QtWidgets.QBoxLayout.Direction.LeftToRight if wide else QtWidgets.QBoxLayout.Direction.TopToBottom)
        self.controls.setMinimumWidth(240 if wide else 0)
        self.controls.setMaximumWidth(240 if wide else 16777215)

    def _apply_theme(self):
        dark = theme.mode.value == 'dark'
        self.setStyleSheet(f'QFrame#comboDemoCanvas {{background:{"#242e39" if dark else "#edf7f8"};border:1px solid {theme.tokens.border};border-radius:8px;}} QLabel#comboDemoType {{color:{theme.tokens.accent};font-weight:600;}}')
        for label in (self.result, self.hint, self.description):
            label.setStyleSheet(f'color:{theme.tokens.text_muted};background:transparent;')
        if isinstance(self.preview, TransparentComboBox):
            self.preview.setTextColor(theme.tokens.accent)


class ComboBoxDemo(FluentWindow):
    def __init__(self, dark=False):
        theme.set_mode('dark' if dark else 'light')
        super().__init__('FluentPy · 下拉选择')
        self.resize(880, 560)
        self.setMinimumSize(560, 520)
        self.content_layout.setContentsMargins(28, 24, 28, 24)
        heading = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel('下拉选择')
        title.setStyleSheet('font-size:24px;font-weight:600;')
        heading.addWidget(title)
        heading.addStretch()
        toggle = ToggleSwitch()
        toggle.setChecked(dark)
        toggle.toggled.connect(lambda checked: theme.set_mode('dark' if checked else 'light'))
        heading.addWidget(QtWidgets.QLabel('深色'))
        heading.addWidget(toggle)
        self.content_layout.addLayout(heading)
        card = HeaderCardWidget('选择一个组件，直接体验')
        self.examples = ComboBoxExamples()
        card.body_layout.addWidget(self.examples)
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    window = ComboBoxDemo(args.dark)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
