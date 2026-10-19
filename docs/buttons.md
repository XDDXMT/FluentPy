# 按钮与页内菜单

Windows 双击 `examples/run_buttons.bat`，或在项目根目录运行 `python examples/buttons.py`。工作台的“按钮与菜单”页使用相同的实际组件。

## 状态与动画

`ToggleButton`、`ToggleIconButton` 和 `PillToggleButton` 继承 Qt 按钮的 `setChecked()`、`isChecked()`、`toggled(bool)`；选中底色和文字以 180ms 过渡。多个胶囊按钮可加入 `QButtonGroup`，沿用 Qt 的互斥选择机制。

`AccentIconButton`、`TransparentIconButton`、`ToggleIconButton` 默认 32×32 逻辑像素，接受 `FluentIcon` 或 `QIcon`。图标来源为随库提供的 Microsoft Fluent System Icons。

所有普通按钮支持鼠标悬浮／按压和键盘按压反馈。Tab / Shift+Tab 移动焦点，Enter / Space 激活；键盘导航显示焦点轮廓。

## 下拉与拆分

```python
from fluentpy import ActionMenu, DropDownButton, AccentSplitButton, FluentIcon

menu = ActionMenu(window)
menu.add_action("另存为…", icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: print("另存为"))
menu.add_separator()
menu.add_action("包含说明", checkable=True, checked=True)
menu.add_action("发布到云端", enabled=False)

export = DropDownButton("导出为", window, menu=menu)
save = AccentSplitButton("保存", window, menu=menu)
save.clicked.connect(lambda: print("执行默认保存"))
```

`DropDownButton` / `AccentDropDownButton` 点击展开菜单。`SplitButton` / `AccentSplitButton` 左侧触发 `clicked()`，右侧独立开关菜单；主按钮按方向下键也可展开。

## 带版本或说明的分体按钮

现有拆分按钮也可显示两行内容：主文字表示动作，`description` 显示当前版本、导出格式或其他自定义说明。普通样式与强调色样式均支持；省略说明时保持原有的单行尺寸。

此双行功能从 0.7.2 起提供，可通过 `python -m pip install -U fluentpy-qt` 升级后使用。

```python
from fluentpy import ActionMenu, AccentSplitButton

launch = AccentSplitButton("启动游戏", window, description="1.0 · 正式版")
versions = ActionMenu(window)
for version in ("1.0 · 正式版", "1.1 · 预览版", "本地开发版"):
    versions.add_action(
        version, callback=lambda checked=False, value=version: launch.set_description(value)
    )
launch.set_menu(versions)
launch.clicked.connect(lambda: print("启动所选版本：", launch.description()))
```

`set_description(text)` / `setDescription(text)` 更新第二行，空字符串恢复单行；`setText()` 更新动作文字。选择菜单项和执行主操作相互独立，组件不会替应用启动游戏或运行后台任务。

按钮沿用库内圆角、强调色和主题；左右区域分别有悬浮、按压和键盘焦点反馈，箭头随菜单展开旋转。两行内容自动增高，箭头区域保持同高；窄尺寸下文字省略，完整说明仍可通过 `description()` 和无障碍描述读取。

工作台“按钮与菜单”中的双行示例可直接选择版本和导出格式，再点击主按钮测试反馈。

`ActionMenu` 直接使用 `QAction`，也可用 `addAction(existing_action)` 添加现有动作。支持图标、勾选、禁用、显隐、分隔线和长菜单滚动；修改／删除动作时同步界面。`shortcut` 参数显示提示，应用自行用 `QAction` 或 `QShortcut` 绑定实际按键行为。

菜单在所属窗口内部以180ms淡入并轻移，120ms退场，按钮箭头同步旋转。菜单靠近下边缘时向上展开，大小与位置限制在窗口内。一个窗口同时打开一条菜单链；原控件隐藏、禁用、销毁或窗口关闭时立即收起。ActionMenu支持多级子菜单与QWidgetAction控件混排，详见[菜单说明](menus.md)。系统托盘使用独立的原生SystemTrayMenu。

菜单内支持上下键、Home / End、Enter / Space。禁用项、隐藏项与分隔线不参与键盘选择。Esc / Tab 或点击外部区域关闭，恢复按钮焦点。

## 任务加载

```python
from fluentpy import LoadingButton

button = LoadingButton("保存更改", window)
button.set_loading(True, text="正在保存…")
# 实际任务完成后，在 Qt 界面线程调用：
button.set_loading(False)
```

加载时保持强调色并显示旋转指示，Qt 禁用机制阻止重复鼠标、键盘、`click()` 和 `animateClick()`。完成后恢复文本与外部设置的可用状态。隐藏或父容器禁用时暂停动画，重新显示／启用后恢复。

按钮不执行实际任务，也不创建后台线程。业务任务自行连接完成信号。按钮、菜单和动画都属于 Qt 前端；此次 C 扩展新增的是快捷键合法性、修饰键顺序和占用冲突检查，见 [快捷键选择器](shortcut-picker.md)。
