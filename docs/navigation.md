# 导航侧栏与工作台设置

`NavigationView` 组合已有的 `NavigationSidebar` 与 `AnimatedStackedWidget`。侧栏使用原生 Qt 布局，顶部与底部固定，中间用 `QScrollArea` 和库内 `FluentScrollBar` 独立滚动。

```python
from fluentpy import NavigationView, SearchLineEdit, FluentIcon, fluent_icon
from fluentpy.qt import QtWidgets

navigation = NavigationView()
navigation.sidebar.set_expanded_width(216)
navigation.sidebar.set_expanded(True)

search = SearchLineEdit("搜索导航")
navigation.sidebar.set_header_widget(search)
search.textChanged.connect(navigation.sidebar.set_filter_text)

navigation.add_sub_interface(QtWidgets.QLabel("概览"), fluent_icon(FluentIcon.HOME), "概览", "overview", "header")
navigation.add_sub_interface(QtWidgets.QLabel("项目"), fluent_icon(FluentIcon.FOLDER), "项目", "projects", "scroll")
navigation.add_sub_interface(QtWidgets.QLabel("设置"), fluent_icon(FluentIcon.SETTINGS), "设置", "settings", "bottom")
```

| 接口 | 行为 |
| --- | --- |
| `position="header"` | 固定顶部导航，位于菜单与自定义顶部内容之后 |
| `position="scroll"` | 中间滚动列表；原有默认 `"top"` 保持相同含义 |
| `position="bottom"` | 固定底部导航 |
| `sidebar.set_header_widget(widget)` | 设置顶部自定义内容，如已有的 `SearchLineEdit` |
| `sidebar.set_footer_widget(widget)` | 在固定底部导航上方设置自定义内容 |
| `sidebar.set_filter_text(text)` | 只筛选中间入口，不切换当前页面，不改变路由是否可用 |
| `sidebar.filter_text()` | 读取当前筛选文字 |
| `sidebar.expandedChanged(bool)` | 监听展开目标状态，适合同步设置开关 |

自定义内容归侧栏所有，替换或设置为 `None` 时释放原内容。紧凑模式隐藏自定义顶部／底部内容，保留固定导航图标。选中中间项目会自动滚入可见区域；手动滚动使选中项离开视野时隐藏其指示条，避免覆盖固定区域。

筛选与 `NavigationView.set_route_visible()` 分工不同：前者只改变搜索结果，保留正在编辑的页面；后者控制路由是否可用，隐藏当前路由时按既有规则切换到可用页面。

工作台：`python examples/showcase.py --page settings`，或双击 `examples/run_showcase.bat` 后点击左下角“设置”。

- 外观：浅色／深色主题、四种强调色、云母效果开关。
- 导航：展开／收起、展开宽度180～280个逻辑像素。
- 交互与状态：页面切换动画、底栏后端状态显示。
- 使用已有 `ComboBox`、`Slider`、`ToggleSwitch`、`Button` 和 `GroupHeaderCardWidget`，不在示例中重画这些控件。
- 修改即时生效，通过 `QSettings("FluentPy", "Showcase")` 保存 `workbench/` 下的设置。恢复默认设置不清空编辑器内容。

设置页下方的“关于 FluentPy”显示项目作者 **性邓的小馒头**、当前运行版本（目前为 0.6.9）及 Qt 绑定与版本，并提供四个外部入口：[官网与文档](https://fluentpy.mcxmcl.cn/)、[作者 GitHub 主页](https://github.com/XDDXMT)、[项目仓库](https://github.com/XDDXMT/FluentPy)和[问题反馈](https://github.com/XDDXMT/FluentPy/issues)。只有点击相应链接才打开浏览器。

“许可与第三方声明”默认折叠，展开后通过只读文本框查看本地 `LICENSE` 和 `THIRD_PARTY_NOTICES.md` 全文。FluentPy 使用 MIT 许可证，发行时须保留版权声明与许可证文本；Qt、图标等第三方依赖和资源遵循各自许可证。

窗口右上方主题开关与设置页同步；侧栏菜单展开／收起也会同步设置页。文档录制与自动测试禁用真实用户设置读写，避免改变用户的工作台偏好。以上均属于 Qt 界面与状态管理，不新增计算后端。

工作台的标题栏与侧栏共用外壳颜色，主内容区保留独立的不透明背景。云母效果默认开启；在受支持的 Windows 11 上，外壳显示系统云母材质，关闭或系统不支持时使用同色实色表面。失焦后云母可能按系统行为回到中性色。独立使用的 `NavigationView` 保持自己的侧栏背景；放入 `FluentWindow` 时跟随窗口外壳。云母条件与自定义页面背景见[流畅窗口](fluent-window.md#明暗背景与云母效果)。

工作台的一体式标题栏默认高 48 逻辑像素，标题、背景及窗口按钮随明暗主题同步；自定义窗口可通过 `window.title_bar().set_bar_height(...)` 调整高度。工作台默认启用 280ms 整窗主题渐变，标题栏与内容一起过渡；云母在短暂的缓存过渡后恢复实时合成。普通 `FluentWindow` 默认关闭该过渡，使用 `set_theme_transition_enabled(True)` 可启用；同时切换模式与强调色时，可用 `theme.set_theme("dark", accent="#60cdff")` 一次提交。

连续反转会接续当前混合画面；输入、点击、滚轮或拖动会返回实时控件，操作本身触发的新主题过渡除外。缩放窗口、隐藏或关闭时取消过渡并释放缓存帧。窗口用法见[流畅窗口](fluent-window.md)。
