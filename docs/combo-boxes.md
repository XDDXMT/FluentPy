# 下拉选择

运行 `python examples/combo_boxes.py`，Windows 可双击 `examples/run_combo_boxes.bat`。
工作台入口：**文本与选择 → 下拉选择**。一个预览区切换九种组件，右侧修改参数。

## 普通、可编辑与业务数据

原有 `ComboBox`／`EditableComboBox` 继续兼容 `addItems`、`currentIndexChanged`、`currentTextChanged`、`lineEdit()`。
普通下拉框支持提示文字、空选择、业务数据、增删改与禁用选项；可编辑下拉框 Enter 选择已有值或追加新值。

```python
from fluentpy import ComboBox, EditableComboBox

choice = ComboBox()
choice.addItem("开发环境", userData={"id": "dev"})
choice.addItem("生产环境", userData={"id": "prod"})
choice.setPlaceholderText("请选择环境")
choice.setCurrentIndex(-1)
choice.currentIndexChanged.connect(lambda row: print(choice.currentData()))
choice.setItemEnabled(1, False)
choice.setMaxVisibleItems(6)

editable = EditableComboBox()
editable.addItems(["main", "develop"])
editable.setCurrentIndex(-1)
editable.setPlaceholderText("选择或输入分支名")
```

`setEditText` 可以设置不在列表中的草稿。空文本保持为空，不回退到上次选择。`setCompleter(QCompleter)` 接入原生补全；`setCompleter(None)` 关闭补全。
程序和模型修改触发 currentIndexChanged/currentTextChanged；activated/textActivated 表示用户确认。

## Qt 模型

`ModelComboBox` 和 `EditableModelComboBox` 直接使用 `setModel(QAbstractItemModel)`，不复制数据、不接管外部模型。
`ComboBox` 及其他变体同样支持模型接口。源模型的插入、移除、排序、重置与重命名会更新界面；持久索引让选择跟随同一项目。

```python
from fluentpy import ModelComboBox, EditableModelComboBox
from fluentpy.qt import QtGui

model = QtGui.QStandardItemModel(parent)
model.appendRow(QtGui.QStandardItem("开发环境"))
view = ModelComboBox(parent)
view.setModel(model)
model.setData(model.index(0, 0), "本地开发")
```

`addItem`、`insertItem`、`removeItem`、`clear` 修改绑定的模型；只清除普通选择使用 `setCurrentIndex(-1)`。
可编辑组件添加新值时，模型需要支持 `insertRows` 和 `setData`。通用禁用由模型的 `flags()` 决定，`setItemEnabled` 便利方法用于 QStandardItemModel。

## 多选与树形

`MultiSelectionComboBox` 使用原生 QListView，菜单持续展开以连续选择。标签可单独移除，过多标签显示 +N。
搜索使用 Qt 过滤代理，不改变源模型。`selectionChanged(list[QModelIndex])`、`selectedIndexes()`、`selectedTexts()`、`selectedData()` 返回实际选择。
`setSelectedIndexes([0, 1])` 设置平面行；`clearSelection()` 保留数据、仅取消选择。

`TreeComboBox`／`MultiSelectionTreeComboBox` 使用原生 QTreeView 与父子模型。父项展开，叶子选择；搜索命中子项时保留父分组。
树形单选使用 `setCurrentModelIndex`、`currentModelIndex`、`currentModelIndexChanged` 与 `currentPath()`。
树形多选的 `setSelectedIndexes` 接受同一个源模型的叶子 QModelIndex；不要只传局部行号来区分不同父分组。

选择状态属于各组件，不会修改共享模型的 CheckStateRole。批量设置有无效索引时整次拒绝并保留原选择；模型删除已选行后会自动移除失效标签。

## 透明样式与字体

`TransparentComboBox` 适合工具栏；`setTextColor(QColor | str | None)` 自定义或恢复主题文字色。
`FontComboBox` 列出 Qt 检测到的系统字体，支持搜索并用各自字形显示选项。`setCurrentFont(QFont)`、`currentFont()`、`currentFontChanged(QFont)` 可以直接与编辑器配合。字体取决于当前机器。

## 共用交互

弹层复用已有 ActionMenu，包含淡入位移、窗口边缘避让、外部点击、Esc、禁用／隐藏清理；不创建额外弹窗。长列表由原生视图滚动。
闭合时 ↑／↓、Home／End 切换单项，Space、Enter、F4 或 Alt+↓ 展开。树视图展开后沿用 Qt 的左右键导航，多选 Space 切换当前项。

参考了 [QFluentWidgets 下拉框说明](https://qfluentwidgets.com/zh/pages/components/combobox/) 的公开交互分类；未复制其源代码、图片、样式表或示例文案。实现建立在本项目既有组件与 Qt 模型／视图之上。
