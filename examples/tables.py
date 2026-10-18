"""One editable table workbench; both Qt data interfaces retain their state."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fluentpy import (TableView, TableWidget, Button, ComboBox, CheckBox,
                      SearchLineEdit, ExpandableCardWidget, AnimatedStackedWidget, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from component_playground import PlaygroundWindow

HEADERS = ['名称', '分类', '数量', '说明', '启用']
SEEDS = [('界面图标', '界面', '用于导航与操作'), ('欢迎插画', '图片', '启动与欢迎页面'),
         ('窗口示例', '组件', '保留系统窗口能力'), ('主题色板', '界面', '配对浅色与深色'),
         ('交互说明', '文档', '键盘与鼠标操作'), ('项目模板', '组件', '可编辑的演示条目')]


def record_values(number):
    title, category, note = SEEDS[(number - 1) % len(SEEDS)]
    return [f'{title} {number:02d}', category, number * 7 % 101, note, number % 3 != 0]


def make_item(value, column, item_type):
    item = item_type()
    if column == 4:
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable |
                      QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.CheckState.Checked if value else QtCore.Qt.CheckState.Unchecked)
    else:
        if isinstance(item, QtGui.QStandardItem):
            item.setData(value, QtCore.Qt.ItemDataRole.DisplayRole)
        else:
            item.setData(QtCore.Qt.ItemDataRole.DisplayRole, value)
        if column == 2:
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
    return item


class TableExamples(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._next_id = 19
        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        self.toolbar = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
        self.search = SearchLineEdit('搜索名称、分类、数量或说明')
        self.search.setAccessibleName('搜索表格内容')
        self.kind = ComboBox()
        self.kind.addItems(['TableView · 模型', 'TableWidget · 项目'])
        self.kind.setAccessibleName('表格数据接口')
        self.toolbar.addWidget(self.search, 1)
        self.toolbar.addWidget(self.kind)
        body.addLayout(self.toolbar)
        self.stack = AnimatedStackedWidget()
        self.stack.setMinimumHeight(310)
        self.stack.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.stack.setFixedHeight(340)
        self.table_view, self.table_widget = TableView(), TableWidget(0, len(HEADERS))
        self.source = QtGui.QStandardItemModel(0, len(HEADERS), self)
        self.source.setHorizontalHeaderLabels(HEADERS)
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.source)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setSortRole(QtCore.Qt.ItemDataRole.EditRole)
        self.table_view.setModel(self.proxy)
        self.table_view.set_empty_text('没有可显示的条目，试试清空搜索或新增。')
        self.table_widget.setHorizontalHeaderLabels(HEADERS)
        for number in range(1, 19):
            values = record_values(number)
            self.source.appendRow([make_item(v, c, QtGui.QStandardItem) for c, v in enumerate(values)])
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            for column, value in enumerate(values):
                self.table_widget.setItem(row, column, make_item(value, column, QtWidgets.QTableWidgetItem))
        for table in (self.table_view, self.table_widget):
            self.stack.addWidget(table)
            table.setMinimumWidth(160)
            for column, width in enumerate((165, 85, 70, 180, 65)):
                table.setColumnWidth(column, width)
            table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
            table.setSortingEnabled(True)
            table.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
            table.selectionModel().selectionChanged.connect(self.update_info)
        body.addWidget(self.stack)
        self.empty_hint = QtWidgets.QLabel('没有匹配的条目，试试清空搜索。', self.table_widget.viewport())
        self.empty_hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty_hint.hide()
        self.table_widget.viewport().installEventFilter(self)

        row = QtWidgets.QHBoxLayout()
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.status.setForegroundRole(QtGui.QPalette.ColorRole.PlaceholderText)
        row.addWidget(self.status, 1)
        self.add_button, self.remove_button, self.copy_button = Button('新增'), Button('删除选中'), Button('复制')
        for button in (self.add_button, self.remove_button, self.copy_button):
            row.addWidget(button)
        body.addLayout(row)
        self.advanced = ExpandableCardWidget('外观与交互')
        self.settings_grid = QtWidgets.QGridLayout()
        self.settings_grid.setHorizontalSpacing(16)
        self.advanced.body_layout.addLayout(self.settings_grid)
        self.style_choice, self.density, self.selection = ComboBox(), ComboBox(), ComboBox()
        self.style_choice.addItems(['普通行', '圆角行', '细线行'])
        self.density.addItems(['紧凑 · 36', '舒适 · 44', '宽松 · 52'])
        self.density.setCurrentIndex(1)
        self.selection.addItems(['多行选择', '单行选择', '单元格选择'])
        for column, (caption, field) in enumerate((('行样式', self.style_choice), ('行密度', self.density), ('选择方式', self.selection))):
            self.settings_grid.addWidget(QtWidgets.QLabel(caption), 0, column)
            self.settings_grid.addWidget(field, 1, column)
        self.editing, self.sorting, self.zebra = CheckBox('允许编辑单元格'), CheckBox('允许表头排序'), CheckBox('交替行底色')
        self.border, self.row_numbers, self.right_click = CheckBox('显示边框'), CheckBox('显示行号'), CheckBox('右键选中目标行')
        for index, field in enumerate((self.editing, self.sorting, self.zebra, self.border, self.row_numbers, self.right_click)):
            field.setChecked(field in (self.editing, self.sorting, self.border, self.right_click))
            self.settings_grid.addWidget(field, 2 + index // 3, index % 3)
            field.toggled.connect(self.configure)
        body.addWidget(self.advanced)
        self.hint = QtWidgets.QLabel('点击表头排序，双击或 F2 编辑；Ctrl / Shift 多选，Ctrl+C 复制，右键打开操作。两种接口各自保留编辑。')
        self.hint.setWordWrap(True)
        self.hint.setForegroundRole(QtGui.QPalette.ColorRole.PlaceholderText)
        body.addWidget(self.hint)
        self.kind.currentIndexChanged.connect(self.change_kind)
        self.search.textChanged.connect(self.apply_filter)
        for choice in (self.style_choice, self.density, self.selection):
            choice.currentIndexChanged.connect(self.configure)
        self.add_button.clicked.connect(self.add_record)
        self.remove_button.clicked.connect(self.remove_selected)
        self.copy_button.clicked.connect(self.copy_selected)
        for model in (self.source, self.table_widget.model()):
            model.dataChanged.connect(self.apply_filter)
            model.rowsInserted.connect(self.update_info)
            model.rowsRemoved.connect(self.update_info)
        self.configure()
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def current_table(self):
        return self.table_view if self.kind.currentIndex() == 0 else self.table_widget

    def change_kind(self, index):
        self.stack.setCurrentIndex(index)
        self.apply_filter()

    def configure(self, *args):
        for table in (self.table_view, self.table_widget):
            table.set_row_style(('standard', 'rounded', 'line')[self.style_choice.currentIndex()])
            table.set_row_height((36, 44, 52)[self.density.currentIndex()])
            table.setSelectionBehavior(table.SelectionBehavior.SelectItems if self.selection.currentIndex() == 2 else table.SelectionBehavior.SelectRows)
            table.setSelectionMode(table.SelectionMode.SingleSelection if self.selection.currentIndex() == 1 else table.SelectionMode.ExtendedSelection)
            table.setEditTriggers((table.EditTrigger.DoubleClicked | table.EditTrigger.EditKeyPressed)
                                  if self.editing.isChecked() else table.EditTrigger.NoEditTriggers)
            table.setSortingEnabled(self.sorting.isChecked())
            table.setAlternatingRowColors(self.zebra.isChecked())
            table.set_border_visible(self.border.isChecked())
            table.verticalHeader().setVisible(self.row_numbers.isChecked())
            table.set_select_right_clicked_row(self.right_click.isChecked())
        self.update_info()

    def apply_filter(self, *args):
        query = self.search.text().strip()
        self.proxy.setFilterFixedString(query)
        matches = ({item.row() for item in self.table_widget.findItems(query, QtCore.Qt.MatchFlag.MatchContains)}
                   if query else set(range(self.table_widget.rowCount())))
        for row in range(self.table_widget.rowCount()):
            self.table_widget.setRowHidden(row, row not in matches)
        self.empty_hint.setGeometry(self.table_widget.viewport().rect())
        self.empty_hint.setVisible(bool(query) and not matches)
        self.update_info()

    def update_info(self, *args):
        if not hasattr(self, 'status'):
            return
        table = self.current_table()
        count = (self.proxy.rowCount() if table is self.table_view else
                 sum(not table.isRowHidden(row) for row in range(table.rowCount())))
        selected = table.selectionModel().selectedRows()
        self.status.setText(f'{count} 条可见 · 已选 {len(selected)} 行')
        self.remove_button.setEnabled(bool(selected))
        self.copy_button.setEnabled(table.selectionModel().hasSelection())

    def add_record(self):
        number = self._next_id
        self._next_id += 1
        values = record_values(number)
        table = self.current_table()
        if table is self.table_view:
            row = self.source.rowCount()
            self.source.appendRow([make_item(v, c, QtGui.QStandardItem) for c, v in enumerate(values)])
            index = self.proxy.mapFromSource(self.source.index(row, 0))
        else:
            sorting = table.isSortingEnabled()
            table.setSortingEnabled(False)
            row = table.rowCount()
            table.insertRow(row)
            first = None
            for column, value in enumerate(values):
                item = make_item(value, column, QtWidgets.QTableWidgetItem)
                table.setItem(row, column, item)
                if column == 0:
                    first = item
            table.setSortingEnabled(sorting)
            index = table.indexFromItem(first)
        self.apply_filter()
        if index.isValid() and not table.isRowHidden(index.row()):
            table.selectRow(index.row())
            table.scrollTo(index)

    def remove_selected(self):
        table = self.current_table()
        for row in sorted({index.row() for index in table.selectionModel().selectedRows()}, reverse=True):
            table.model().removeRow(row)
        self.apply_filter()

    def copy_selected(self):
        self.current_table().copy_selection()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Resize and hasattr(self, 'empty_hint'):
            self.empty_hint.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toolbar.setDirection(QtWidgets.QBoxLayout.Direction.LeftToRight if self.width() >= 540
                                  else QtWidgets.QBoxLayout.Direction.TopToBottom)

    def _apply_theme(self):
        self.empty_hint.setPalette(self.table_widget.palette())
        self.empty_hint.setForegroundRole(QtGui.QPalette.ColorRole.PlaceholderText)


class TableDemo(PlaygroundWindow):
    def __init__(self, dark=False):
        super().__init__('表格', TableExamples, dark=dark)
        self.resize(1000, 760)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    window = TableDemo(args.dark)
    window.show()
    raise SystemExit(app.exec())


if __name__ == '__main__':
    main()
