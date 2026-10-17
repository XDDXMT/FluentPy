"""Build documentation content and signatures from the adjacent FluentPy source."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import re
import shutil

SITE = Path(__file__).resolve().parent
from source_project import source_root, source_version
ROOT = source_root()
VERSION = source_version()
SRC = ROOT / "src" / "fluentpy"

DESCRIPTIONS = {
    "Button": "普通按钮，提供悬浮、按下和禁用反馈。",
    "AccentButton": "跟随主题强调色的主要操作按钮。",
    "FilledButton": "填充按钮，沿用强调按钮的实现。",
    "TextButton": "弱化背景的文字按钮。",
    "OutlinedButton": "描边按钮。",
    "RoundButton": "胶囊形圆角按钮。",
    "RoundAccentButton": "胶囊形强调按钮。",
    "HyperlinkButton": "打开指定 URL 的链接按钮。",
    "IconButton": "使用 QIcon 的图标按钮。",
    "ToggleButton": "保留 Qt 选中状态与 toggled 信号，底色以180ms过渡。",
    "ToggleIconButton": "32px 图标状态按钮，支持 FluentIcon 和 QIcon。",
    "PillToggleButton": "胶囊形状态按钮，可用 QButtonGroup 组合互斥筛选。",
    "AccentIconButton": "32px 强调色图标按钮。",
    "TransparentIconButton": "32px 透明图标按钮。",
    "DropDownButton": "点击或按方向下键展开页内菜单，箭头随展开状态旋转。",
    "AccentDropDownButton": "强调色下拉操作按钮。",
    "SplitButton": "左侧触发默认动作，右侧独立展开菜单。",
    "AccentSplitButton": "强调色拆分按钮。",
    "LoadingButton": "旋转加载图标与重复点击保护，完成后恢复文本和可用状态。",
    "ActionMenu": "QAction 驱动的窗口内菜单，支持键盘、勾选、禁用、滚动与淡入位移动画。",
    "LineEdit": "带焦点底线动画和可选清除按钮的单行输入框。",
    "PasswordLineEdit": "带显示／隐藏密码操作的输入框。",
    "SearchLineEdit": "带搜索图标的单行输入框，沿用 QLineEdit 的输入信号。",
    "TextEdit": "跟随主题的多行文本编辑框。",
    "RichTextEdit": "TextEdit 的导出别名。",
    "CheckBox": "双态或三态复选框，支持标题下方的可选小号说明。",
    "RadioButton": "自绘单选按钮，可与 QButtonGroup 组合。",
    "ToggleSwitch": "带状态过渡动画的开关按钮。",
    "ComboBox": "不可编辑的下拉选择框。",
    "EditableComboBox": "允许输入自定义文本的下拉框。",
    "SpinBox": "带焦点动画与自绘箭头的整数输入框。",
    "DoubleSpinBox": "浮点数输入框，支持 Qt 精度和范围设置。",
    "Slider": "提供悬浮与按下反馈的数值滑动条。",
    "ProgressBar": "使用主题强调色的进度条。",
    "NavigationView": "组合侧栏与动画页面栈的导航容器。",
    "NavigationSidebar": "支持展开、收起、底部入口和选中指示条的侧栏。",
    "NavigationItem": "侧栏入口，负责图标、文字和交互状态。",
    "AnimatedStackedWidget": "带淡入和横向移动过渡的页面栈。",
    "BreadcrumbBar": "按路由标识管理的面包屑导航。",
    "Pivot": "以文字入口切换内容的导航条。",
    "SegmentedWidget": "分段式文字导航。",
    "SegmentedToolWidget": "以图标作为入口的分段导航。",
    "TabBar": "按路由标识管理的标签栏。",
    "FluentWindow": "提供内容布局、明暗主题和 Windows 背景效果尝试的主窗口。",
    "FramelessDialog": "独立无边框模态对话框，不提供拖动行为。",
    "MaskedDialog": "覆盖在父窗口内部的遮罩对话框。",
    "MaskDialog": "MaskedDialog 的导出别名。",
    "MessageBox": "MaskedDialog 的导出别名。",
    "Card": "跟随主题和窗口激活状态的卡片容器。",
    "CardWidget": "可组合任意 Qt 布局的卡片容器，本体不响应点击。",
    "SimpleCardWidget": "背景保持稳定的简洁卡片容器。",
    "ElevatedCardWidget": "悬浮时以轻阴影表达抬升的卡片，不改变布局分配的位置。",
    "HeaderCardWidget": "带标题条、分隔线和内容布局的静态卡片。",
    "GroupHeaderCardWidget": "按图标、标题、说明与操作控件组织设置项的分组卡片。",
    "ExamplePanel": "包含预览区与源码区的示例面板。",
    "Toast": "带状态图标、关闭按钮与指向箭头的消息卡片，支持目标锚定、淡入淡出和自动关闭。",
    "ProgressToast": "四角任务提示，支持平滑进度、循环条、完成／失败状态、尺寸过渡和悬停暂停自动关闭。",
    "ShortcutPicker": "用键帽显示快捷键，点击铅笔在页内录制，保存后回填，支持重置、清空和冲突提示。",
    "ShortcutDialog": "单组合快捷键录制浮层，保存／取消分离，校验与冲突检查优先C、不可用时回退Python。",
    "FluentScrollBar": "悬浮时展开的自绘滚动条。",
    "CodeEdit": "JSON／纯文本编辑框，支持同步行号、缩进辅助线、当前行背景与焦点底线。",
    "DatePicker": "年、月、日三列滚轮日期选择器，支持确认、取消、范围限制和 C 日历运算。",
    "TimePicker": "24／12小时制时间滚轮，支持AM／PM、确认／取消、页内动画、C优先与Python回退。",
    "CalendarPicker": "日历日期选择器，支持月／年视图、跨月选择、禁用日期、键盘操作与页内动画。",
    "DateRangePicker": "两次点击选择日期区间，支持悬停预览、反向选择和禁用起止日期。",
    "DateTimePicker": "日历与时／分／秒滚轮组合，保留草稿，确认才提交，支持本地日期时间边界。",
    "DropArea": "Qt本地路径选择区域，选择策略优先C并支持Python回退，提供异步校验和结果信号。",
    "FileDropWidget": "带浏览文件／文件夹入口的多文件拖放组件，默认接受 JPG、PNG、GIF。",
    "FolderDropWidget": "仅接受文件夹的拖放组件，默认接收一个文件夹。",
    "NoteEvent": "不可变音符数据：起始秒数、持续秒数、MIDI 音高与轨道编号。",
    "NoteTimeline": "只读音符概览，提供多轨配色、音域与进度游标。",
    "ThemeManager": "全局主题管理器，可切换模式、强调色和窗口激活状态。",
    "ThemeMode": "light／dark 主题模式枚举。",
    "ThemeTokens": "不可变主题参数与派生颜色。",
    "FluentIcon": "106 个 Microsoft Fluent System Icons 的枚举入口。",
    "fluent_icon": "将 FluentIcon 或资源名转换为 Qt 图标。",
    "fluent_icon_name": "读取图标的资源名。",
    "QT_API": "当前选用的 Qt 后端：优先 PySide6，缺失时尝试 PyQt6。",
    "theme": "全局 ThemeManager 实例。",
}

METHODS = {
    "set_date_bounds": "设置包含端点的最早和最晚日期。日历／区间的现有选择不合法时清空；日期时间夹到新边界。",
    "set_disabled_weekdays": "设置禁用的星期编号：0为星期一，6为星期日；区间只限制起止日期。",
    "set_disabled_dates": "设置禁止选择的QDate列表，替换此前配置。",
    "set_first_weekday": "设置一周从哪天开始：0为星期一，6为星期日。",
    "set_locale": "设置QLocale或语言标识，更新月份标题与星期标签。",
    "set_placeholder_text": "设置未选择时的占位文字。",
    "start_date": "读取已提交区间的起点QDate副本，空值返回无效QDate。",
    "end_date": "读取已提交区间的终点QDate副本，空值返回无效QDate。",
    "set_range": "设置起止QDate并自动交换反向端点；禁用端点报错，两个无效QDate清空区间。",
    "date_time": "返回本地QDateTime副本，精确到秒，空值返回无效QDateTime。",
    "dateTime": "date_time的Qt风格入口。",
    "set_date_time": "将QDateTime转换为本地时间、截去毫秒并夹到边界；禁用日期报错，无效值清空。",
    "setDateTime": "set_date_time的Qt风格入口。",
    "set_date_time_bounds": "设置包含端点的本地日期时间边界；现有值超出时夹紧。",
    "description": "返回复选框的第二行说明。",
    "set_description": "设置第二行说明；空字符串恢复单行，自动调整推荐尺寸和辅助功能说明。",
    "setDescription": "set_description 的 Qt 风格入口。",
    "set_loading": "切换加载状态；text为加载文字，完成后恢复普通文字和原有可用状态。",
    "is_loading": "是否处于任务加载状态。",
    "set_menu": "设置 ActionMenu 或 None。",
    "setMenu": "set_menu 的 Qt 风格入口。",
    "menu": "读取关联的 ActionMenu。",
    "show_menu": "在所属窗口中展开或收起菜单。",
    "showMenu": "show_menu 的 Qt 风格入口。",
    "add_action": "添加 QAction，可设置图标、回调、勾选、可用状态与快捷键提示。",
    "addAction": "添加现有 QAction 或文本。",
    "add_separator": "添加菜单分隔线。",
    "addSeparator": "添加菜单分隔线的 Qt 风格入口。",
    "remove_action": "移除一个 QAction。",
    "removeAction": "移除一个 QAction 的 Qt 风格入口。",
    "popup": "相对 anchor 控件展开，菜单约束在所属窗口内；无菜单项时返回 False。",
    "dismiss": "关闭菜单；immediate=True立即关闭。",
    "anchor_widget": "读取当前锚定控件。",
    "key_sequence": "返回当前QKeySequence副本。",
    "set_key_sequence": "设置PortableText或QKeySequence，非法组合或占用冲突报错。",
    "set_reserved_sequences": "设置应用提供的已占用组合列表，交给当前后端检查冲突。",
    "reserved_sequences": "返回已占用组合的QKeySequence列表副本。",
    "open_editor": "打开页内快捷键录制浮层，保存才提交。",
    "start": "创建并显示任务进度提示；placement支持四角，indeterminate开启未知进度。关闭后自动释放。",
    "set_progress": "更新0–100目标进度并平滑过渡，自动切回确定进度；终态后的迟到更新忽略。",
    "set_indeterminate": "切换任务的确定／不确定进度显示。",
    "is_indeterminate": "是否显示未知进度循环条。",
    "finish": "切换为成功、补齐进度，默认停留1800ms；悬停时暂停倒计时。",
    "fail": "切换为失败并停止循环，默认保留到手动关闭。",
    "selected_paths": "返回最近一次有效选择的规范路径副本。",
    "accept_paths": "同步校验并提交本地路径；拒绝的项目不覆盖原有选择。",
    "submit_paths": "在后台校验本地路径，结果和信号回到界面线程；旧请求不会覆盖新请求。",
    "set_file_extensions": "设置允许的后缀，支持 png、.png、*.png；空列表接受所有文件类型。",
    "file_extensions": "返回当前后端规范化后的文件后缀元组。",
    "set_multiple": "设置下次选择是否接收多个有效路径。",
    "is_multiple": "是否允许多选。",
    "is_busy": "是否正在后台校验所选路径。",
    "browse_files": "打开 Qt 原生文件选择框；取消时保留已有选择。",
    "browse_folder": "打开 Qt 原生文件夹选择框，文件夹路径原样交给应用，不递归扫描。",
    "__init__": "创建组件。parent 为可选的 Qt 父控件。",
    "set_clear_button_enabled": "设置是否显示清除按钮；可编辑下拉框默认不显示清除按钮。",
    "set_trailing_inset": "设置右侧附加控件预留宽度。",
    "set_leading_inset": "设置左侧内容预留宽度。",
    "set_code": "替换文本内容，使用普通文本保存。",
    "code": "返回当前完整文本。",
    "set_font_size": "设置代码和行号字号，单位为逻辑像素；切换主题时保留该值。",
    "font_size": "返回当前代码字号。",
    "set_indent_size": "设置 Tab、Shift+Tab、Enter 和缩进辅助线的空格宽度，默认 4；不重排已有内容。",
    "indent_size": "返回当前缩进宽度，单位为空格。",
    "acceleration_backend": "返回该组件实际选择的native或python；auto优先C、不可用时自动回退，python强制兼容实现。",
    "date": "读取已提交的 QDate；未选择时返回无效 QDate。",
    "set_date": "设置日期，超出范围夹到边界；无效 QDate 表示清空。",
    "setDate": "set_date 的 Qt 风格入口。",
    "time": "读取已提交QTime副本；未选择时返回无效QTime。",
    "set_time": "设置QTime，精确到分钟；无效QTime清空，不修改显示时制。",
    "setTime": "set_time 的 Qt 风格入口。",
    "is_12_hour_clock": "是否以12小时制显示；返回值仍然是24小时制QTime。",
    "set_12_hour_clock": "设置12／24小时显示，保留已提交时间并取消当前草稿。",
    "set12HourClock": "set_12_hour_clock 的 Qt 风格入口。",
    "is12HourClock": "is_12_hour_clock 的 Qt 风格入口。",
    "set_date_range": "设置有效的最小与最大 QDate；当前值超界时夹紧。",
    "minimum_date": "读取最早可选日期，默认 1900-01-01。",
    "maximum_date": "读取最晚可选日期，默认 2100-12-31。",
    "setMinimumDate": "设置最早可选日期。",
    "setMaximumDate": "设置最晚可选日期。",
    "show_popup": "展开选择浮层；已打开时关闭。",
    "set_language": "切换 json 或 plain；不会重置内容、光标或撤销历史。",
    "language": "返回当前高亮模式。",
    "setReadOnly": "设置是否只读。",
    "isReadOnly": "返回只读状态。",
    "setPlainText": "设置普通文本，与 set_code 等价。",
    "toPlainText": "读取普通文本，与 code 等价。",
    "set_route_visible": "控制路由入口显隐，保留页面对象和顺序；隐藏当前页时选择可见回退页。",
    "is_route_visible": "查询路由是否可用，与整个窗口的可见性独立。",
    "set_current_route": "切换到可见路由，可选择关闭过渡动画。",
    "current_route": "读取当前路由标识；没有可用页面时返回空字符串。",
    "add_sub_interface": "注册页面、图标、文字和可选路由标识。position 可为 top 或 bottom。",
    "set_expanded_width": "设置侧栏展开宽度，保留收起行为。",
    "set_expanded": "展开或收起侧栏。",
    "set_notes": "复制音符数据并重置游标；总时长至少覆盖最后一个音符，可保留曲尾休止。",
    "notes": "返回音符数据的不可变元组。",
    "set_position": "按秒设置进度；有效值限制在 0 到总时长之间。",
    "position": "返回游标位置，单位为秒。",
    "duration": "返回总时长，单位为秒。",
    "set_pitch_range": "设置固定 MIDI 音域；省略两个参数时恢复自动音域。",
    "pitch_range": "返回当前有效音域。",
    "set_track_colors": "设置非空轨道调色板，按轨道编号循环使用。",
    "set_empty_text": "设置没有音符时的提示文字。",
    "empty_text": "返回空状态文字。",
    "clear": "清空当前内容，保留控件配置。",
    "open": "非阻塞打开对话框。",
    "exec": "运行模态事件循环并返回对话框结果。",
    "accept": "以确认结果完成对话框。",
    "reject": "以取消结果完成对话框。",
    "result": "读取对话框结果。",
    "done": "使用指定结果完成对话框。",
    "setClosableOnMaskClicked": "设置点击遮罩是否关闭对话框，默认不关闭。",
    "add_content_widget": "向对话框的自定义内容区域添加控件。",
    "setContentWidget": "向自定义内容区域添加控件。",
    "setYesButtonText": "设置确认按钮文字。",
    "setCancelButtonText": "设置取消按钮文字。",
    "success": "创建提示，显示到指定位置，超时后关闭并释放。",
    "show_at": "将提示放到父窗口或屏幕的指定角落。",
    "set_mode": "切换 light／dark，更新后发送 changed 信号。",
    "set_accent": "设置自定义强调色。",
    "toggle": "切换明暗模式或展开状态。",
    "subscribe": "订阅主题变化，接收者随控件销毁自动断开。",
    "add_item": "添加一个条目。",
    "set_current_item": "按路由标识选择条目。",
    "current_item": "返回当前选中的条目。",
    "add_tab": "添加包含路由标识、文字和可选图标的标签。",
    "set_current_tab": "按路由标识切换标签。",
    "addItems": "按顺序添加多个下拉选项。",
    "addItem": "添加一个选项或导航条目。",
    "setCurrentIndex": "按索引切换当前项。",
    "currentText": "读取当前文字。",
    "currentIndex": "读取当前项索引。",
    "lineEdit": "返回下拉框内的输入控件。",
    "setChecked": "设置选中状态。",
    "isChecked": "查询选中状态。",
    "setTristate": "启用或关闭三态复选行为。",
    "setCheckState": "设置未选、部分选中或选中状态。",
    "checkState": "返回 Qt.CheckState。",
    "set_dark": "切换窗口使用的全局明暗主题。",
    "set_border_radius": "设置卡片圆角，单位为逻辑像素，默认 8。",
    "border_radius": "读取卡片圆角。",
    "setBorderRadius": "设置卡片圆角的 Qt 风格入口。",
    "borderRadius": "读取卡片圆角的 Qt 风格入口。",
    "set_title": "设置标题文字。",
    "setTitle": "设置标题条文字的 Qt 风格入口。",
    "title": "读取标题条文字。",
    "set_header_visible": "显示或隐藏标题条和它下方的分隔线，保留内容。",
    "is_header_visible": "读取标题条的显隐配置，不依赖整个窗口是否显示。",
    "add_group": "添加并返回一个分组行，控制区在窄布局中移动到文字下方。",
    "addGroup": "add_group 的 Qt 风格入口。",
    "groups": "按当前顺序读取分组行的不可变元组。",
    "remove_group": "移除分组并释放该行及其控件；不属于当前卡片时返回 False。",
    "set_group_control": "替换一行的操作控件，原控件会隐藏并延迟释放。",
    "set_group_text": "更新一行的标题与可选说明。",
}


def signature(node, name=None):
    arguments = copy.deepcopy(node.args)
    if arguments.args and arguments.args[0].arg in ("self", "cls"):
        arguments.args = arguments.args[1:]
    result = f"{name or node.name}({ast.unparse(arguments)})"
    if node.returns:
        result += " → " + ast.unparse(node.returns)
    return result


def collect_api():
    api, aliases = {}, {}
    excluded = {"event", "eventFilter", "nativeEvent", "sizeHint", "minimumSizeHint", "paint_line_numbers", "update_gutter_width", "gutter_width", "highlight_current_line"}
    for path in sorted(SRC.rglob("*.py")):
        if "assets" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                item = {"name": node.name, "description": DESCRIPTIONS.get(node.name, ""), "base": ", ".join(ast.unparse(x) for x in node.bases), "file": path.relative_to(ROOT).as_posix(), "line": node.lineno, "methods": [], "signals": []}
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and (method.name == "__init__" or (not method.name.startswith("_") and not method.name.endswith("Event") and method.name not in excluded)):
                        sig = signature(method, node.name if method.name == "__init__" else None)
                        is_property = any(isinstance(d, ast.Name) and d.id == "property" for d in method.decorator_list)
                        if is_property:
                            sig = method.name + (": " + ast.unparse(method.returns) if method.returns else "") + " [property]"
                        description = METHODS.get(method.name, ast.get_docstring(method) or "")
                        if node.name == "CalendarPicker" and method.name == "set_date":
                            description = "设置可选的QDate；禁用或超界日期报错，无效QDate清空。"
                        if node.name in ("CalendarPicker", "DateRangePicker", "DateTimePicker") and method.name == "show_popup":
                            description = "展开页内选择器；重复调用取消旧草稿并从已提交值重新开始。"
                        item["methods"].append({"name": method.name, "signature": sig, "description": description, "line": method.lineno})
                    if isinstance(method, ast.Assign) and isinstance(method.value, ast.Call) and ast.unparse(method.value.func).endswith("Signal"):
                        item["signals"].append({"name": ast.unparse(method.targets[0]), "signature": ast.unparse(method.value)})
                if node.name == "NoteEvent":
                    item["methods"] = [{"name": "__init__", "signature": "NoteEvent(start: float, duration: float, pitch: int, track: int = 0)", "description": "时间必须有限且非负；音高为 0..127 的整数，轨道为非负整数。", "line": node.lineno}]
                api[node.name] = item
            elif isinstance(node, ast.FunctionDef) and node.name in DESCRIPTIONS:
                api[node.name] = {"name": node.name, "description": DESCRIPTIONS[node.name], "base": "function", "file": path.relative_to(ROOT).as_posix(), "line": node.lineno, "methods": [{"name": node.name, "signature": signature(node), "description": DESCRIPTIONS[node.name], "line": node.lineno}], "signals": []}
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = node.value.id
    # Include custom Python base interfaces (including implementation mixins).
    # Qt's large inherited API is still left to the Qt documentation.
    def inherited(name, visiting=None):
        visiting = set(visiting or ())
        if name not in api or name in visiting:
            return [], []
        visiting.add(name)
        item = api[name]
        methods, signals = list(item["methods"]), list(item["signals"])
        for base in item["base"].split(", "):
            if base not in api:
                continue
            base_methods, base_signals = inherited(base, visiting)
            for method in base_methods:
                if method["name"] not in {m["name"] for m in methods}:
                    value = {**method, "inheritedFrom": method.get("inheritedFrom", base),
                             "file": method.get("file", api[base]["file"])}
                    if value["name"] == "__init__":
                        value["signature"] = name + value["signature"][value["signature"].index("("):]
                    methods.append(value)
            for signal in base_signals:
                if signal["name"] not in {s["name"] for s in signals}:
                    signals.append({**signal, "inheritedFrom": signal.get("inheritedFrom", base)})
        return methods, signals
    resolved = {name: inherited(name) for name in api}
    for name, (methods, signals) in resolved.items():
        api[name]["methods"], api[name]["signals"] = methods, signals
    for alias, target in aliases.items():
        if alias in DESCRIPTIONS and target in api:
            api[alias] = {**api[target], "name": alias, "description": DESCRIPTIONS[alias], "alias": target, "methods": []}
    api["theme"] = {**api["ThemeManager"], "name": "theme", "description": DESCRIPTIONS["theme"], "base": "ThemeManager"}
    exports = ast.parse((SRC / "__init__.py").read_text(encoding="utf-8-sig"))
    public = next(ast.literal_eval(n.value) for n in exports.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets))
    api["QT_API"] = {"name": "QT_API", "description": DESCRIPTIONS["QT_API"], "base": "str", "methods": [], "signals": []}
    return {key: api[key] for key in public if key in api}


def section(id, title, text, code="", preview=None, note=None, **content):
    return {"id": id, "title": title, "text": text, "code": code.strip(), "preview": preview, "note": note, **content}


def page(id, title, english, group, intro, classes, sections, **content):
    return {"id": id, "title": title, "english": english, "group": group, "intro": intro, "classes": classes, "sections": sections, **content}


NATIVE_LAYERS = [
    {"name": "Python", "role": "组件接口", "text": "沿用熟悉的类名、方法和信号，衔接界面与计算。"},
    {"name": "C", "role": "运算后端", "text": "承接 JSON 扫描、文本位置映射、日期与时间计算、拖放与快捷键策略。"},
    {"name": "Qt", "role": "界面呈现", "text": "管理文档、布局、绘制与输入交互。"},
]
NATIVE_METRICS = [
    {"value": "13.21×", "label": "JSON 扫描提速", "detail": "25.28 → 1.91 ms"},
    {"value": "1.52×", "label": "完整载入与首帧提速", "detail": "64.93 → 42.73 ms"},
]

ANIMATED_PREVIEWS = {
    "calendar-motion": {
        "image": "calendar-motion-light.gif", "poster": "calendar-motion-light.png",
        "width": 420, "height": 520,
        "alt": "实际Qt日历在窗口内展开，切换月份、预览日期区间，并在完成选择后淡出回填。",
    },
    "time-picker-motion": {
        "image": "time-picker-motion-light.gif", "poster": "time-picker-motion-light.png",
        "width": 420, "height": 520,
        "alt": "12小时制时间选择器在窗口内淡入，滚动分钟、小时与AM／PM，确认后淡出并回填。",
    },
    "button-states": {
        "image": "button-states-light.gif", "poster": "button-states-light.png",
        "width": 620, "height": 220,
        "alt": "点击收藏和胶囊筛选，选中底色平滑过渡；加载按钮旋转并阻止重复点击，完成后恢复。",
    },
    "button-menus": {
        "image": "button-menus-light.gif", "poster": "button-menus-light.png",
        "width": 620, "height": 300,
        "alt": "下拉菜单在窗口内淡入并轻移，箭头旋转；拆分按钮左侧执行保存，右侧独立展开更多动作。",
    },
    "shortcut-recording": {
        "image": "shortcut-recording-light.gif", "poster": "shortcut-recording-light.png",
        "width": 720, "height": 480,
        "alt": "点击铅笔打开页内浮层，录制Ctrl+Shift+Return和Alt+L，重置后再次录制并保存回填。",
    },
    "progress-toast": {
        "image": "progress-toast-light.gif", "poster": "progress-toast-light.png",
        "width": 520, "height": 190,
        "alt": "右下角任务提示平滑入场，进度增长后切换为下载完成，卡片缩短并淡出。",
    },
    "progress-toast-indeterminate": {
        "image": "progress-toast-indeterminate-light.gif", "poster": "progress-toast-indeterminate-light.png",
        "width": 520, "height": 190,
        "alt": "左上角未知进度提示显示一段实心线在轨道内平滑往返，随后切换为成功提示并淡出。",
    },
    "drop-file-active": {
        "image": "drop-file-active-light.gif", "poster": "drop-file-light.png",
        "width": 340, "height": 184,
        "alt": "文件拖入时虚线边框和浅色背景渐变为主题强调色，离开后恢复。",
    },
    "cards-elevated": {
        "image": "cards-elevated-light.gif", "poster": "cards-elevated-light.png",
        "width": 440, "height": 168,
        "alt": "三张 Unicode 表情卡片，悬浮时阴影渐变表达抬升，移出后恢复。",
    },
    "toast-compact": {
        "image": "toast-compact-light.gif", "poster": "toast-compact-light.png",
        "width": 460, "height": 180,
        "alt": "紧凑单行提示侧滑淡入，显示代码已复制，随后淡出关闭。",
    },
    "toast-anchored": {
        "image": "toast-anchored-light.gif", "poster": "toast-anchored-light.png",
        "width": 760, "height": 250,
        "alt": "带成功图标、标题、正文和关闭按钮的消息卡片，箭头指向按钮，淡入轻移后淡出。",
    },
}


pages = [
    page("introduction", "简介", "Introduction", "快速入门", "FluentPy 是一个独立实现的 Python 桌面组件库，为 Qt 应用带来简洁、一致的 Fluent 风格。", [], [
        section("about", "从一个组件，到自己的桌面应用", "FluentPy 基于 Qt for Python，将常见控件、页面导航和主题管理组合在一起。你可以先放下一个按钮，再逐步搭出项目工作台、编辑工具或设置页面。", paragraphs=[
            "项目以 PySide6 为主要后端，组件实现独立编写。我们希望让桌面界面的搭建更直观，同时提供开放的源码和清晰的 MIT 授权。运行示例工作台，可以直接体验侧栏、卡片、输入与标签等真实组件。",
        ], links=[{"label": "查看工作台与运行方式 →", "page": "getting-started"}]),
        section("c-backend", "Python 接口，C 优先加速", "保持Python的使用方式，以C作为首选加速后端，并维护Python兼容实现。缺少加速扩展时自动回退，前端继续使用Qt/Python。", nativeFlow=True, paragraphs=[
            "C加速已接入文本扫描、日期、时间、拖放和快捷键策略；每组均提供Python兼容实现。默认auto优先C，缺失或不兼容时自动回退，界面仍可正常使用。下面演示C可用时的数据流程，实测倍率仅适用于标注的计算路径。",
        ], links=[{"label": "查看 C 加速说明与实测 →", "page": "performance"}], note="以上为本机 10,000 行完整 JSON、五轮独立进程的中位数，相对原始版本。扫描与整段载入的收益分别计算；滚动和单次编辑基本不变。"),
        section("features", "先看看组件长什么样", "从日常操作到内容编辑，选择需要的组件，再把它们放进 Qt 布局。以下均为实际控件的亮色截图，点击卡片可查看用法与接口。", gallery=[
            {"title": "按钮与操作", "text": "普通、强调、文字和图标按钮，让主要操作与次要操作各有位置。", "image": "buttons", "page": "buttons", "tag": "Button · AccentButton"},
            {"title": "文字与输入", "text": "单行、多行、搜索与密码输入，提供清晰的焦点和输入反馈。", "image": "line", "page": "inputs", "tag": "LineEdit · TextEdit"},
            {"title": "三列日期选择", "text": "点击展开年、月、日滚轮，确认才回填，日历运算交给 C。", "image": "date-picker", "page": "date-picker", "tag": "DatePicker · C backend"},
            {"title": "两种时制的时间选择", "text": "小时与分钟独立滚动，12小时制增加AM／PM，页内展开并确认回填。", "image": "time-picker-12", "page": "time-picker", "tag": "TimePicker · 24H / 12H"},
            {"title": "日历与日程", "text": "从单个日期到连续区间，再到精确至秒的日程；圆弧区间底色和平滑预览。", "image": "date-range-picker", "page": "calendar-picker", "tag": "Calendar · Range · DateTime"},
            {"title": "页面与导航", "text": "用侧栏组织页面，也可以组合面包屑、分段导航和标签栏。", "image": "navigation", "page": "navigation", "tag": "NavigationView · Pivot"},
            {"title": "对话框与反馈", "text": "通过确认面板、遮罩对话框和短暂提示，传达当前操作的结果。", "image": "dialog", "page": "dialogs", "tag": "FramelessDialog · MaskedDialog"},
            {"title": "轻量代码编辑", "text": "行号、JSON 着色和缩进辅助线，适合编辑配置与查看响应数据。", "image": "code-summary", "page": "code-editor", "tag": "CodeEdit"},
            {"title": "音符时间轴", "text": "按音高与时间展示音符，提供多轨配色和播放位置游标。", "image": "timeline", "page": "note-timeline", "tag": "NoteTimeline · NoteEvent"},
        ]),
        section("familiar-api", "用熟悉的 Qt API 开始", "以输入框为例：LineEdit 继承 QLineEdit。替换导入与类名后，可以继续使用 setText()、setPlaceholderText() 和 textChanged，同时获得圆角外观、清除入口和焦点强调线。", '''from fluentpy import LineEdit

edit = LineEdit()
edit.setText("把灵感写下来")
edit.setPlaceholderText("写点什么…")
edit.textChanged.connect(lambda text: print(text))''', migration={"before": "QLineEdit", "after": "LineEdit", "beforeImage": "migration-input-qt-light.png", "afterImage": "migration-input-fluent-light.png", "focusImage": "migration-input-focus-light.png"}, note="迁移时请按具体组件核对构造参数：QLineEdit 的首个字符串参数是初始文本，LineEdit 的首个字符串参数是占位提示。上例通过共同的 setText() 设置内容。组合型组件则通过自己的接口使用，例如 CodeEdit.text_edit。"),
        section("more", "配色与细节，集中管理", "控件共享主题管理器，支持浅色、深色与自定义强调色。输入焦点、选中状态和常用字体由组件统一处理，减少逐个控件配置样式的重复工作。", links=[
            {"label": "了解主题与强调色 →", "page": "themes"},
            {"label": "浏览 106 个 Fluent 图标 →", "page": "icons"},
        ]),
        section("next", "把第一个窗口运行起来", "从源码安装，组合组件，再按需查阅接口。本站展示真实控件截图，实际交互可以运行项目中的 Python 示例查看。", steps=[
            {"title": "准备环境", "text": "安装项目与 Qt 后端，运行第一个窗口。", "page": "getting-started", "label": "开始使用"},
            {"title": "组合页面", "text": "把组件放进布局，用导航连接不同页面。", "page": "navigation", "label": "查看页面导航"},
            {"title": "接上逻辑", "text": "连接信号，按组件接口实现自己的功能。", "page": "api-index", "label": "查阅公开接口"},
        ], note="FluentPy 目前处于早期开发阶段。当前本机验证使用 PySide6，PyQt6 回退路径尚未作同等验证。网站外观默认跟随系统，组件配图统一使用亮色。"),
        section("license", "许可证", "本 Python 组件库的许可证为 MIT。", paragraphs=[
            "本组件库可免费用于个人和商业项目，无需另行购买本库商业授权。",
        ], links=[{"label": "查看 MIT 许可证全文 ↗", "href": "assets/FluentPy-LICENSE.txt"}], callout={
            "title": "MIT",
            "text": "MIT 是一种宽松的开源许可证，允许自由使用、修改、分发和商业化代码。使用时需保留原始版权声明和许可证文本，软件按原样提供，不承担任何担保责任。",
        }),
    ], cover={"image": "showcase-home", "width": 1122, "height": 812, "alt": "FluentPy示例工作台的导航与反馈页面，包含侧栏、面包屑、页内切换和代码文档标签", "caption": "新版示例工作台：侧栏导航、页内切换与可编辑的文档标签。运行示例，可直接体验库内控件的交互。", "tags": ["Python + Qt", "C 优先 · Python 兼容", "原生桌面组件", "MIT 开源许可"]}),
    page("getting-started", "开始使用", "Getting started", "快速入门", "用 Python 构建有 Fluent 质感的桌面界面。从一个窗口、一个按钮开始。", [], [
        section("about", "关于 FluentPy", "FluentPy 是独立实现的 Qt for Python 组件库，源码采用 MIT 许可。默认使用 PySide6，接口层保留 PyQt6 回退路径。当前为早期版本，API 仍可能调整。"),
        section("install", "从源码安装", "建议在独立虚拟环境中安装。以下为 Windows PowerShell 命令；从本仓库安装，避免误装 PyPI 上的同名项目。", '''git clone https://github.com/XDDXMT/FluentPy.git
cd FluentPy
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -e .'''),
        section("first-window", "第一个窗口", "创建 QApplication 后，将组件添加到 FluentWindow 的内容布局中。", '''import sys
from fluentpy import AccentButton, FluentWindow, Toast
from fluentpy.qt import QtWidgets

app = QtWidgets.QApplication(sys.argv)
window = FluentWindow("你好，FluentPy")
button = AccentButton("保存灵感")
button.clicked.connect(lambda: Toast.success("已保存", parent=window))
window.content_layout.addWidget(button)
window.show()
sys.exit(app.exec())'''),
        section("gallery", "新的示例工作台", "工作台包含概览、输入与日期、日历与日程、按钮与菜单、拖放文件、卡片与设置、导航与反馈、代码与性能、音符视图九个可操作页面。侧栏支持展开收起，页面与文档标签内容使用库内切换动画。下图展示使用统一主图标与紧凑尺寸的新版工作台。Windows可双击examples/run_showcase.bat，添加--page calendar直达新增日历页。", "python examples/showcase.py", preview="showcase", links=[{"label": "日历与日程 →", "page": "calendar-picker"}, {"label": "在简介了解C加速 →", "page": "introduction"}], note="C扩展为可选加速；缺失、不兼容或旧版本缺少接口时，对应组件自动回退Python。本站记录当前开发接口，不代表已发布新的库版本。"),
    ]),
    page("faq", "常见问题", "Frequently asked questions", "快速入门", "关于商用、MIT许可、闭源发布、安装、C扩展和示例体验，你可能想先了解这些。", [], [
        section("commercial", "我想用这个 Python 组件库做商用软件，可以吗？", "完全可以。FluentPy采用MIT许可证，允许用于商业项目，也允许修改和分发，无需为本库另行购买商业授权。", paragraphs=[
            "分发本库或包含本库实质性代码的软件时，请保留原始版权声明和完整MIT许可证文本。可以随应用附带第三方许可文件，并在“关于”页面提供入口；仅标注作者姓名并不能代替保留许可证。",
        ], links=[{"label":"查看FluentPy的MIT许可证 ↗", "href":"assets/FluentPy-LICENSE.txt"}, {"label":"MIT许可原文（Open Source Initiative）↗", "href":"https://opensource.org/license/mit"}]),
        section("closed-source", "使用 FluentPy 后，必须把我的软件开源吗？", "MIT许可证本身不要求你公开应用源码，可以开发和分发闭源软件；仍需保留本库的版权声明与许可证文本。", paragraphs=[
            "FluentPy的MIT授权只适用于本库。Qt、PySide6／PyQt6及其他第三方依赖有各自的许可，发布应用时也需要分别遵守。",
        ], links=[{"label":"Qt的许可说明 ↗", "href":"https://www.qt.io/licensing/"}]),
        section("requirements", "开始使用需要什么环境？", "需要Python 3.10或更高版本，以及Qt for Python绑定。FluentPy默认使用PySide6，保留PyQt6适配入口。当前实际验证环境为Windows x64、CPython 3.13和PySide6／Qt 6.11.1；其他环境需要对应验证。", paragraphs=[
            f"建议先从本仓库安装并运行示例，避免误装PyPI上同名的其他项目。项目目前为{VERSION}早期版本，文档记录当前开发接口。",
        ], links=[{"label":"安装与第一个窗口 →", "page":"getting-started"}]),
        section("native-required", "一定要编译 C 扩展，才能使用组件吗？", "不需要。C扩展是可选加速。默认auto模式优先使用C；缺少扩展、二进制无法加载或旧扩展缺少对应接口时，CodeEdit、日期／时间选择器、拖放和快捷键选择器都会自动使用Python兼容实现，组件仍可正常操作。", paragraphs=[
            "如需C加速，可再构建匹配当前Python小版本、系统和架构的扩展，然后重启应用。FLUENTPY_BACKEND=python可以强制验证兼容路径；只有显式选择native时，缺少C接口才会报错。",
        ], links=[{"label":"C扩展的构建与排查 →", "page":"performance"}]),
        section("native-scope", "所有组件都已经用 C 加速了吗？", "目前C扩展负责已接入的后端运算：JSON词元扫描与UTF-16位置映射、日期运算、时间换算与滚轮候选、拖放筛选策略，以及快捷键合法性和占用冲突检查。Python保留公开接口与绑定，Qt继续负责控件、布局、绘制和动画。", paragraphs=[
            "某一段运算的加速倍数不代表整个应用都会等比例变快。例如大段JSON应使用多行CodeEdit，C扫描可以减轻高亮开销，但文本排版和绘制仍有各自的成本。",
        ], links=[{"label":"查看接入范围与实测结果 →", "page":"performance"}, {"label":"代码编辑器 →", "page":"code-editor"}]),
        section("previews", "网页里的控件可以直接操作吗？", "文档里的组件预览是FluentPy实际Qt控件的截图或GIF，浏览器中不会运行桌面Qt控件。动图可以暂停和播放；要实际点击、输入或录制快捷键，请运行独立Demo或示例工作台。", "python examples/showcase.py", paragraphs=[
            "Windows也可以双击examples/run_showcase.bat。带说明的复选框示例入口是examples/run_checkbox.bat，工作台的“输入与日期”页也包含同一组件。",
        ], links=[{"label":"示例工作台与启动方式 →", "page":"getting-started"}, {"label":"复选框与选择控件 →", "page":"selection"}]),
        section("file-types", "拖放组件只能接收 JPG、PNG、GIF 吗？", "不是。这只是FileDropWidget的默认后缀列表，可以通过set_file_extensions()改为PDF、JSON等其他类型；传入空列表表示不限制文件后缀。FolderDropWidget用于接收文件夹。", links=[{"label":"自定义文件类型与多选 →", "page":"drag-drop"}]),
        section("preview-theme", "为什么网页是深色，控件预览却是亮色？", "网页默认跟随系统主题，也可以通过右上角按钮切换。组件截图和GIF统一展示亮色，方便比较控件的尺寸、字体与布局；实际桌面组件支持明暗两种主题，可以在Demo中切换。", links=[{"label":"主题设置 →", "page":"themes"}]),
        section("feedback", "发现问题或想增加组件，在哪里反馈？", "可以到GitHub的Issues反馈。建议写明Python版本、Qt绑定及版本、操作系统、相关组件、复现步骤，以及预期和实际表现；涉及视觉问题时附上截图或短录屏，会更容易定位。", links=[{"label":"打开FluentPy Issues ↗", "href":"https://github.com/XDDXMT/FluentPy/issues"}]),
    ]),
    page("themes", "主题", "Theming", "快速入门", "统一管理浅色、深色与强调色，让控件自然地保持一致。", ["theme", "ThemeMode", "ThemeTokens"], [
        section("theme-mode", "明暗模式", "全局主题变更后，已订阅的组件会更新。点击右上角的主题按钮也可以体验本站的两种配色。", '''from fluentpy import theme

theme.set_mode("light")
theme.set_mode("dark")
theme.toggle()''', "theme"),
        section("accent", "强调色", "默认浅色强调色为 #009FAA，深色为 #29F1FF。自定义强调色会在切换明暗模式后保留。", '''theme.set_accent("#00A8B5")
print(theme.tokens.accent)'''),
        section("backend", "Qt 后端", "优先选择 PySide6，导入失败时尝试 PyQt6。当前本机验证使用 PySide6，PyQt6 路径未作同等验证。", "from fluentpy import QT_API\nprint(QT_API)\n\nfrom fluentpy.qt import QtCore, QtGui, QtWidgets, Signal"),
    ]),
    page("performance", "性能与 C 后端", "Native acceleration", "快速入门", "C 加速后端运算，Python 保留组件接口，Qt 负责界面交互。了解当前接入范围、启用方式与完整数据实测。", [], [
        section("architecture", "C优先，Python兼容", "FluentPy以C作为后端运算的首选加速实现，同时维护Python兼容路径。扩展不可用时自动回退，组件保持可用；Qt负责界面与动画。", architecture=NATIVE_LAYERS, items=[
            {"title": "已接入", "text": "CodeEdit的JSON扫描与UTF-16映射、DatePicker日期运算、TimePicker时制换算与滚轮、三种日历组件的网格／区间／禁用策略／日期时间／秒滚轮、拖放筛选／去重／数量限制、快捷键合法性与冲突检查，均可由fluentpy._native扩展执行。"},
            {"title": "后续开发", "text": "其他后端计算按开发进度逐步接入，当前没有将全部组件改写为 C。"},
            {"title": "兼容路径", "text": "文本、日期、时间、拖放和快捷键均提供Python兼容实现；默认auto优先C，扩展缺失、不兼容或接口不完整时按组件回退，功能继续可用。"},
        ]),
        section("backend", "前端照常使用，后端自动选择", "默认auto模式按组件选择可用的C接口，不可用时自动回退Python。无需更换组件类名；两种实现保持日期边界、文件筛选、快捷键规则和文本高亮的行为兼容。", '''from fluentpy import CodeEdit
from fluentpy.backends.text import native_available

editor = CodeEdit()
editor.set_code('{"name": "FluentPy", "enabled": true}')
print(native_available())             # 当前解释器能否加载 C 扩展
print(editor.acceleration_backend())  # native：C 后端；python：兼容实现'''),
        section("build", "编译 C 扩展", "在项目根目录执行。已有兼容当前 Python 的系统 C 编译器时，可直接使用以下命令；完成后重启 Python 程序，再检查实际后端。", "python -B scripts/build_native.py", paragraphs=[
            "当前已实际验证 Windows x64、CPython 3.13.1、PySide6 / Qt 6.11.1。二进制需要匹配 Python 小版本、操作系统和架构，其他环境需要对应的构建产物。",
        ]),
        section("windows-build", "Windows 独立工具链", "没有配置系统 C 编译器时，可以使用仓库提供的 Zig 入口。首次下载固定版本并校验 SHA-256，工具链只保存在项目目录；已有工具链时仅执行第二行。", '''python -B scripts/fetch_zig.py
python -B scripts/build_native.py --zig .toolchains/zig-x86_64-windows-0.14.1/zig.exe'''),
        section("selection", "选择后端与排查回退", "默认 auto：扩展可用时使用 C。可在启动程序前用 FLUENTPY_BACKEND 明确选择；要求 C 时，以下配置会在扩展不可用时明确报错。", '''$env:FLUENTPY_BACKEND = 'native'
python examples/text_performance.py''', language="PowerShell", items=[
            {"title": "auto", "text": "默认配置，C 扩展可用时启用，否则回退 Python。"},
            {"title": "native", "text": "必须使用 C；二进制缺失或不兼容时明确报错。"},
            {"title": "python", "text": "使用兼容实现，便于性能对照与问题定位。"},
        ], note="三种模式统一作用于文本、日期、时间、拖放和快捷键。通常不必设置环境变量；auto即可自动适配。设置应在启动前完成，已打开的旧进程需重启。"),
        section("component-backends", "查看每个组件实际使用的后端", "各组件的acceleration_backend()返回native或python。旧扩展缺少某组接口时只让该组回退，其他可用的C能力继续使用；工作台显示C后端就绪、Python兼容模式或混合后端。", '''from fluentpy import DatePicker, TimePicker, CalendarPicker, FileDropWidget, ShortcutPicker

for component in (DatePicker(window), TimePicker(window), CalendarPicker(window), FileDropWidget(window), ShortcutPicker(parent=window)):
    print(type(component).__name__, component.acceleration_backend())'''),
        section("diagnostics", "为什么显示 python？", "可能是未编译扩展、二进制与当前解释器不匹配，或显式选择了 python 模式。先检查启动配置和导入原因，需要编译时使用运行应用的同一个 Python。", '''import os
from fluentpy.backends.text import native_available, native_error

print(os.environ.get("FLUENTPY_BACKEND", "auto"))
print(native_available())
print(native_error())  # 成功加载时为 None，否则为扩展导入失败原因'''),
        section("measurement", "一万行 JSON，完整内容对照", "2026-10-16 本机实测：AMD Ryzen 9 9950X3D，Windows x64、CPython 3.13.1、Qt 6.11.1，取五轮独立进程中位数。同一份输入包含 10,000 行、266,481 个 UTF-16 单元与 14,997 个高亮片段。", metrics=NATIVE_METRICS, table={
            "caption": "10,000 行 JSON · 耗时越低越好",
            "headers": ["项目", "原始版本", "Python 后端", "C 后端"],
            "rows": [
                ["JSON 扫描", "25.28 ms", "24.87 ms", "1.91 ms"],
                ["完整载入与首帧", "64.93 ms", "66.54 ms", "42.73 ms"],
                ["完整重新高亮", "98.31 ms", "98.18 ms", "73.69 ms"],
                ["单次编辑", "3.22 ms", "3.27 ms", "3.41 ms"],
                ["30 次滚动绘制", "100.43 ms", "98.53 ms", "100.59 ms"],
            ],
        }, preview="performance", links=[{"label": "查看性能 Demo 原图 ↗", "href": "assets/previews/performance-light.png"}], note="滚动与单次编辑基本不变。JSON 扫描的 13.21 倍只对应该计算路径，不能代表整库提速。"),
        section("large-document", "五万行，继续使用完整数据", "同一台机器、三轮独立进程中位数：JSON 扫描从 127.21 ms 降至 10.73 ms，完整载入与首帧从 292.60 ms 降至 180.12 ms，分别约快 11.85 倍与 1.62 倍。", paragraphs=[
            "每轮使用新进程，轮换后端执行顺序，全部后端处理相同输入。载入计时包含完整高亮、事件处理与首帧，完成后另行校验文本、行数和高亮片段数。没有通过丢弃内容、隐藏行或减少高亮来获得提速。",
            "原始报告保存在 benchmarks/text-performance-10000.json 与 benchmarks/text-performance-50000.json，包含环境、每轮耗时、源码指纹及完整性检查。",
        ]),
        section("demo", "运行性能 Demo", "可选择 1,000、10,000、50,000 行 JSON。测试在独立进程运行，窗口和下方预览仍可编辑；报告会保留每轮耗时、环境、源码指纹及完整性检查。", "python examples/text_performance.py", note="Windows 也可双击 examples/run_text_performance.bat。当前二进制实际验证范围为 Windows x64 / CPython 3.13；其他 Python 版本需重新编译。"),
        section("scope", "LineEdit 与多行 JSON", "LineEdit 继承 Qt 单行输入框，默认最多 32,767 个 UTF-16 单元。本次万行数据在默认配置下会被截断，这种结果没有计作性能提升。多行 JSON 请使用 CodeEdit，普通多行内容可使用 TextEdit。", links=[{"label": "CodeEdit 用法 →", "page": "code-editor"}, {"label": "Qt 单行输入框说明 ↗", "href": "https://doc.qt.io/qt-6/qlineedit.html#maxLength-prop"}]),
    ]),
    page("date-picker", "日期选择器", "DatePicker", "日期时间", "点击年、月、日，展开三列滚轮；确认后才保存。Python 接口与 Qt 绘制，日期运算由 C 完成。", ["DatePicker"], [
        section("picker", "三列滚轮，确认后回填", "初始显示年／月／日占位。点击任意一列打开浮层，滚轮、拖动或点击相邻行切换，中间整行高亮；✓ 或 Enter 确认，×、Esc 或点击外部取消。", '''from fluentpy import DatePicker
from fluentpy.qt import QtCore

picker = DatePicker()
picker.set_date(QtCore.QDate(2024, 2, 26))
picker.dateChanged.connect(lambda date: print(date.toString("yyyy-MM-dd")))
picker.dateAccepted.connect(lambda date: print("确认", date.toString("yyyy-MM-dd")))''', preview="date-picker", note="dateChanged 仅在已提交日期实际改变时触发。dateAccepted 在确认时触发，包括确认原值。未确认的滚动和取消都不改变已提交值。"),
        section("range", "有效日期与范围", "默认 1900-01-01 至 2100-12-31，可在公历 1 至 9999 年内自定义。超界日期夹到边界；年月改变后自动处理大小月和闰年，例如 2 月 29 日切到非闰年会调整为 28 日。", '''picker.set_date_range(QtCore.QDate(2024, 2, 1), QtCore.QDate(2024, 2, 29))
picker.setDate(QtCore.QDate(2024, 2, 26))
print(picker.minimum_date().toString("yyyy-MM-dd"))
print(picker.maximum_date().toString("yyyy-MM-dd"))'''),
        section("empty", "空值与尺寸", "默认推荐 300×38，最小推荐 240×34，可随布局横向伸缩。clear() 恢复占位，date() 返回无效 QDate；初始为空时打开浮层，临时定位到范围内的今天。", '''picker.clear()
print(picker.date().isValid())  # False
picker.setFixedWidth(300)'''),
        section("keyboard", "键盘与主题", "左右方向键切换列，上下逐项选择，PageUp／PageDown 跳五项，Enter 确认、Esc 取消。月份和日期在当前允许区间循环，年份在边界停止。浮层按当前屏幕定位，颜色跟随明暗主题与强调色。"),
        section("native", "C优先与Python兼容", "闰年、每月天数、范围夹紧、步进和候选行优先在C中计算。缺失、不兼容或旧版扩展没有日期接口时，默认自动使用Python；选择器仍能展开、滚动、确认和限制范围。", '''print(picker.acceleration_backend())  # native 或 python''', links=[{"label": "查看可选加速的构建方式 →", "page": "performance"}], note="无需编译也可使用。只有显式FLUENTPY_BACKEND=native模式要求可用的C接口。JSON扫描的倍率不代表日期组件的提速。"),
        section("demo", "单独 Demo 与示例工作台", "单独 Demo 包含空值、示例日期、清空、限定月份和亮暗切换。Windows 可双击 examples/run_date_picker.bat；完整工作台入口为 examples/run_showcase.bat。", "python examples/date_picker.py", links=[{"label": "查看新工作台 →", "page": "getting-started"}]),
    ]),
    page("calendar-picker", "日历与日程", "Calendar pickers", "日期时间", "选择单日、一段区间，或精确到秒的日程。统一的月／年视图、轻量弹层与键盘操作，使用实际Qt控件呈现。", ["CalendarPicker", "DateRangePicker", "DateTimePicker"], [
        section("single", "日历日期选择", "点击字段展开日历，点击可用日期即提交；相邻月份的日期也可直接选择。今天使用实心强调色，选中日期使用描边圆环。月份标题可进入月份、年份视图，快速跳转。", '''from fluentpy import CalendarPicker, DateRangePicker, DateTimePicker
from fluentpy.qt import QtCore

calendar = CalendarPicker(window)
calendar.set_date(QtCore.QDate(2024, 2, 26))
calendar.dateChanged.connect(lambda value: print(value.toString("yyyy-MM-dd")))
calendar.dateAccepted.connect(lambda value: print("选择完成", value))''', preview="calendar-picker", note="原有DatePicker继续提供年／月／日滚轮；CalendarPicker是独立的日历网格组件，不改变旧接口。初始为空，clear()或无效QDate清空。"),
        section("range", "两次点击，选出一个区间", "第一次点击设置起点，移动鼠标预览范围，第二次点击完成。起止先后可以反转，也可选择同一天。完成前保留旧值，Esc或点击外部取消草稿。", '''interval = DateRangePicker(window)
interval.set_range(QtCore.QDate(2024, 3, 13), QtCore.QDate(2024, 3, 21))
interval.set_disabled_weekdays((5, 6))  # 周六、周日不能作为端点
interval.rangeChanged.connect(lambda start, end: print(start, end))
print(interval.start_date(), interval.end_date())''', preview="date-range-picker", note="区间为连续、包含端点的自然日期范围。禁用日期限制起止点，允许跨越区间内部的周末和禁用日；不会把它们排除在区间外。"),
        section("date-time", "日期与时、分、秒一起选择", "左边选择日期，右边独立滚动小时、分钟与秒。选择过程只修改草稿，✓或时间滚轮上的Enter确认；×、Esc或点击外部取消。", '''scheduled = DateTimePicker(window)
scheduled.setDateTime(QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(20, 0, 0)))
scheduled.dateTimeChanged.connect(lambda value: print(value.toString("yyyy-MM-dd HH:mm:ss")))
scheduled.dateTimeAccepted.connect(lambda value: print("已确认", value))''', preview="date-time-picker", note="返回本地QDateTime，精确到秒，设置时截去毫秒。各列独立循环：秒59→00不会进位。传入其他时区的QDateTime会先转成本地时间。"),
        section("rules", "日期限制、禁用项与语言", "默认支持公历1至9999年，星期一为一周起点。限制配置先校验再生效；日历与区间的已有值因此不可选时清空，日期时间超界时夹紧。", '''calendar.set_date_bounds(QtCore.QDate(2024, 1, 1), QtCore.QDate(2026, 12, 31))
calendar.set_disabled_dates([QtCore.QDate(2024, 5, 1)])
calendar.set_disabled_weekdays((5, 6))
calendar.set_locale("en_US")
calendar.set_first_weekday(6)  # Sunday
calendar.set_placeholder_text("Pick a date")

scheduled.set_date_time_bounds(
    QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(9, 30, 15)),
    QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(20, 0, 0)))''', note="程序设置禁用日期或区间端点时会明确报错；不会默默换成另一天。日期时间的上下界包含时、分、秒，边界当天的草稿时间会自动夹紧。"),
        section("motion", "切月、选区间和收起", "实际Qt录制展示页内展开、月份缓动切换、区间预览和完成后的回填。底色延伸至端点圆环外缘，按圆弧裁切；预览190ms平滑伸缩、悬停140ms过渡、圆环200ms过渡，切月180ms、入场220ms、退场140ms。", preview="calendar-motion", paragraphs=["方向键移动日期，PageUp／PageDown切换月份，Ctrl加翻页键切换年份；Home回到本周起点，Ctrl+Home跳到今天。Tab／Shift+Tab在网格、标题、翻页和确认控件间移动。", "弹层在窗口边缘避让，窄窗口下日期时间改为上下排列；窗口过小无法容纳时不展开。隐藏、禁用、切页或销毁时取消草稿。"]),
        section("backend", "公历与区间计算优先C", "42格月份数据、闰年、日期平移、起止规范化、禁用策略、日期时间边界、时分秒步进与候选行由calendar C后端优先处理。缺失、不兼容或旧扩展缺少接口时，auto自动回退Python，三种控件继续可用。", '''print(calendar.acceleration_backend())
print(interval.acceleration_backend())
print(scheduled.acceleration_backend())  # native 或 python''', note="Qt继续负责绘制、布局和动画；没有为这些小规模日期计算标注固定提速倍数。"),
        section("demo", "独立Demo与示例工作台", "Windows可双击examples/run_calendar_picker.bat。独立Demo展示三种选择器、清空、禁用周末和明暗主题；示例工作台新增“日历与日程”页。", "python examples/calendar_picker.py", links=[{"label":"开始使用 →", "page":"getting-started"}]),
    ]),
    page("time-picker", "时间选择器", "TimePicker", "日期时间", "小时与分钟的独立滚轮，支持24小时制和带AM／PM的12小时制。页内浮层轻柔展开，确认后才回填。", ["TimePicker"], [
        section("24-hour", "24小时制：小时与分钟", "点击任意一列展开滚轮，中间整行高亮。滚动、拖动、点击相邻行都可选择；✓或Enter确认，×、Esc或点击外部取消。下图为实际Qt控件亮色截图。", '''from fluentpy import TimePicker
from fluentpy.qt import QtCore

picker = TimePicker()
picker.setTime(QtCore.QTime(14, 0))
picker.timeChanged.connect(lambda value: print(value.toString("HH:mm")))
picker.timeAccepted.connect(lambda value: print("确认", value.toString("HH:mm")))''', preview="time-picker-24", note="timeChanged只在已提交值改变时发出；timeAccepted在每次确认时发出。滚动和取消不修改已提交时间。"),
        section("12-hour", "12小时制：增加AM／PM", "同一组件设置use_12_hour=True即可增加周期列。14:00显示为2／00／PM；午夜为12:00 AM，正午为12:00 PM。返回的QTime始终使用24小时制，无需在业务代码里再换算。", '''ampm = TimePicker(use_12_hour=True)
ampm.setTime(QtCore.QTime(14, 0))
print(ampm.time().toString("HH:mm"))  # 14:00
picker.set_12_hour_clock(True)  # 保留原来的时间，只改变显示''', preview="time-picker-12", note="各列独立选择：分钟59→00不进位；12小时模式的小时11→12不改变AM／PM。第三列只显示两个有效选项，空白行不可选。"),
        section("empty", "空值、精度与共同接口", "初始为空，time()返回无效QTime。clear()恢复占位；传入无效QTime也会清空。时间精确到分钟，设置时截去秒与毫秒，不四舍五入。默认推荐300×38逻辑像素。", '''picker.clear()
print(picker.time().isValid())  # False
picker.set_time(QtCore.QTime(23, 59, 45))
print(picker.time().toString("HH:mm:ss"))  # 23:59:00
print(picker.is_12_hour_clock())'''),
        section("motion", "页内弹层与流畅动画", "选择器在当前窗口内部展开，避免额外系统弹窗。入场220ms淡入轻移、退场140ms，滚轮130ms缓动；阴影保持轻量。左右切换列，上下选择，PageUp／PageDown跳五项；Tab／Shift+Tab在滚轮、确认和取消之间移动。", preview="time-picker-motion", paragraphs=["窗口缩小时自动减少可见候选行并在边缘避让。隐藏、禁用、切页或销毁时会收起浮层，取消未提交修改；明暗主题和强调色沿用组件库统一设置。"]),
        section("backend", "C优先加速，Python兼容回退", "时间校验、12／24小时转换、步进与候选行由C后端优先处理。缺失、不兼容或旧版扩展没有时间接口时，默认auto模式自动使用Python，选择器仍可使用。", '''print(picker.acceleration_backend())  # native 或 python''', note="显式FLUENTPY_BACKEND=native要求可用的时间C接口；扩展更新后重启旧进程。此处未给时间组件标注固定加速倍数。"),
        section("demo", "独立Demo与示例工作台", "Demo同时展示24小时制、12小时制、清空、当前时间和亮暗切换。Windows可双击examples/run_time_picker.bat；完整工作台的“输入与日期”页也包含相同组件。", "python examples/time_picker.py", links=[{"label":"查看示例工作台 →", "page":"getting-started"}]),
    ]),
    page("buttons", "按钮", "Buttons", "基本输入", "为主要操作、次要操作和轻量链接选择合适的按钮。支持键盘操作、选择状态、任务加载和页内菜单。", ["Button", "AccentButton", "TextButton", "OutlinedButton", "RoundButton", "RoundAccentButton", "FilledButton", "HyperlinkButton", "IconButton", "ToggleButton", "ToggleIconButton", "PillToggleButton", "AccentIconButton", "TransparentIconButton", "DropDownButton", "AccentDropDownButton", "SplitButton", "AccentSplitButton", "LoadingButton", "ActionMenu"], [
        section("button", "普通与强调按钮", "Button 用于普通操作，AccentButton 用于主要操作。继承 Qt 按钮常用接口，支持 clicked、setEnabled() 和 setText()。", '''from fluentpy import Button, AccentButton

cancel = Button("稍后再说")
save = AccentButton("保存草稿")
save.clicked.connect(lambda: print("已保存"))''', "buttons"),
        section("variants", "更多按钮样式", "文字、描边和胶囊形按钮共享常用交互行为。", '''from fluentpy import TextButton, OutlinedButton, RoundButton

learn = TextButton("了解更多")
outline = OutlinedButton("查看详情")
round_button = RoundButton("继续")''', "button-variants"),
        section("icon-button", "链接与图标", "使用 Microsoft Fluent System Icons 作为图标，图标按钮可以设置提示文字。", '''from fluentpy import HyperlinkButton, IconButton, FluentIcon, fluent_icon

link = HyperlinkButton("项目主页", url="https://github.com/XDDXMT/FluentPy")
save_icon = IconButton(fluent_icon(FluentIcon.DOCUMENT_SAVE), tooltip="保存")'''),
        section("toggle", "带动画的状态按钮", "ToggleButton、ToggleIconButton 和 PillToggleButton 沿用 Qt 的 checked / toggled 接口，底色与文字平滑过渡。多个胶囊按钮可交给 QButtonGroup 管理互斥关系。", '''from fluentpy import ToggleButton, PillToggleButton, LoadingButton

favorite = ToggleButton("收藏")
favorite.toggled.connect(lambda checked: print("收藏：", checked))
filters = QtWidgets.QButtonGroup(window)
for text in ("全部", "文档", "图像"):
    choice = PillToggleButton(text, window)
    filters.addButton(choice)
filters.buttons()[0].setChecked(True)''', "button-states"),
        section("menu", "下拉菜单与拆分按钮", "菜单由 QAction 驱动，在所属窗口内淡入并轻移，箭头同步旋转。拆分按钮左侧执行默认动作，右侧展开其他操作。支持勾选、禁用、分隔线、长菜单滚动和键盘导航。", '''from fluentpy import ActionMenu, DropDownButton, AccentDropDownButton, SplitButton, AccentSplitButton, FluentIcon

menu = ActionMenu(window)
menu.add_action("另存为…", icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: print("另存为"))
menu.add_separator()
menu.add_action("包含说明", checkable=True, checked=True)
menu.add_action("发布到云端", enabled=False)
export = DropDownButton("导出为", window, menu=menu)
split = AccentSplitButton("保存", window, menu=menu)
split.clicked.connect(lambda: print("执行默认保存"))''', "button-menus", note="ActionMenu 是单层页内菜单，不越出窗口边界，不创建额外原生弹出窗口。shortcut参数显示快捷键提示；实际快捷键行为交给应用的QAction或QShortcut。"),
        section("loading", "加载与重复点击保护", "LoadingButton 处于加载状态时保持强调色并显示旋转指示，同时使用 Qt 禁用机制阻止鼠标、键盘和程序化 click 再次触发。应用负责真实任务与完成通知；隐藏或父容器禁用时暂停动画。", '''task = LoadingButton("保存更改", window)
task.set_loading(True, text="正在保存…")
# 在任务完成后，于Qt界面线程恢复：
task.set_loading(False)''', note="按钮和菜单属于前端交互，使用Qt绘制与动画。快捷键校验优先C，不可用时回退Python。"),
        section("keyboard", "键盘与独立 Demo", "Tab / Shift+Tab 移动焦点；Enter / Space 操作；方向下键展开菜单；菜单内上下键、Home / End 选择，Esc / Tab 关闭。Windows可双击examples/run_buttons.bat；工作台新增“按钮与菜单”页。", "python examples/buttons.py"),
    ]),
    page("inputs", "输入框", "Text inputs", "基本输入", "从一行想法到一段文字。清晰的输入状态，轻柔的焦点反馈。", ["LineEdit", "SearchLineEdit", "PasswordLineEdit", "TextEdit", "RichTextEdit"], [
        section("lineedit", "LineEdit", "用于编辑单行文本。支持占位文字、清除按钮和原生 QLineEdit 的文本操作。焦点底线收在圆角内。", '''from fluentpy import LineEdit

line_edit = LineEdit("给这个想法起个名字")
line_edit.setText("周末的桌面小工具")
line_edit.set_clear_button_enabled(True)
line_edit.textChanged.connect(lambda text: print(text))''', "line"),
        section("searchlineedit", "SearchLineEdit", "带搜索图标的输入框。搜索图标用于提示用途，按 Enter 的行为可通过 QLineEdit 的 returnPressed 信号连接。", '''from fluentpy import SearchLineEdit

search = SearchLineEdit("搜索你的灵感")
search.returnPressed.connect(lambda: print("搜索：", search.text()))''', "search"),
        section("passwordlineedit", "PasswordLineEdit", "默认隐藏密码文字，可通过右侧按钮切换显示状态。", '''from fluentpy import PasswordLineEdit

password = PasswordLineEdit("输入密码")
password.setText("fluent-morning")
print(password.text())''', "password"),
        section("textedit", "TextEdit", "编辑多行文本，支持 Qt 文本编辑与滚动行为。RichTextEdit 是同一实现的导出别名。", '''from fluentpy import TextEdit

notes = TextEdit()
notes.setPlaceholderText("写下今天的灵感…")
notes.setPlainText("先做一个按钮，\\n再把想法变成一个窗口。")''', "textarea", "需要行号和 JSON 高亮时，使用扩展组件中的 CodeEdit。"),
    ]),
    page("selection", "选择与数值", "Selection & values", "基本输入", "用复选、单选、下拉与数值控件，让每一次选择都清楚可见。", ["CheckBox", "RadioButton", "ToggleSwitch", "ComboBox", "EditableComboBox", "SpinBox", "DoubleSpinBox", "Slider"], [
        section("description-check", "带说明的复选框", "标题下方可显示文件大小或任意说明文字。点击方框、标题或说明均可选择；Tab移动焦点，空格切换。说明为空时保留原有单行布局，支持明暗主题、禁用和三态。", '''from fluentpy import CheckBox

other_files = CheckBox("Other files", description="760.0 KB")
other_files.toggled.connect(lambda checked: print(checked))
other_files.set_description("760.0 KB")''', "checkbox-description", note="Windows可双击examples/run_checkbox.bat；工作台“输入与日期”页的“选择与数值”区域也有同一组件。说明只负责显示文字，不自动扫描文件或计算容量。"),
        section("description-check-selected", "选中状态与说明更新", "使用原生Qt按钮接口读取或设置选中状态。说明可随业务更新，设为空字符串后恢复单行；更新说明不会改变选中状态。", '''other_files.setChecked(True)
print(other_files.isChecked())
other_files.setDescription("760.0 KB")
# other_files.set_description("")  # 恢复单行''', "checkbox-description-checked"),
        section("checks", "复选与单选", "CheckBox 支持双态和三态；互斥单选可交由 Qt 的 QButtonGroup 管理。", '''from fluentpy import CheckBox, RadioButton
from fluentpy.qt import QtCore, QtWidgets

check = CheckBox("保留上次的选择")
check.setTristate(True)
check.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)

group = QtWidgets.QButtonGroup()
group.addButton(RadioButton("轻量模式"))
group.addButton(RadioButton("完整模式"))''', "checks"),
        section("toggle", "开关", "用于直接开启或关闭某项设置。", '''from fluentpy import ToggleSwitch

switch = ToggleSwitch()
switch.toggled.connect(lambda enabled: print(enabled))''', "switch"),
        section("combo", "下拉选择", "普通下拉框用于固定选项；可编辑下拉框允许输入额外内容，内置输入框不显示清除按钮。", '''from fluentpy import ComboBox, EditableComboBox

choice = ComboBox()
choice.addItems(["轻量模式", "专注模式", "自由模式"])
choice.currentTextChanged.connect(print)

editable = EditableComboBox()
editable.addItems(["本地草稿", "新的灵感"])
editable.lineEdit().setPlaceholderText("选择或输入")''', "combo"),
        section("numbers", "数字与滑动条", "整数、小数和连续范围输入沿用 Qt 的范围与精度接口。", '''from fluentpy import SpinBox, DoubleSpinBox, Slider
from fluentpy.qt import QtCore

count = SpinBox()
count.setRange(1, 100)
count.setValue(12)

amount = DoubleSpinBox()
amount.setDecimals(2)
amount.setRange(0.0, 1.0)

slider = Slider(QtCore.Qt.Orientation.Horizontal)
slider.setRange(0, 100)
slider.setValue(42)''', "numbers"),
    ]),
    page("navigation", "侧栏与页面", "Navigation view", "导航", "把多个界面组织成有秩序的桌面应用，带页面过渡和选中指示。", ["NavigationView", "NavigationSidebar", "NavigationItem", "AnimatedStackedWidget"], [
        section("routes", "注册页面", "每个页面有独立路由标识。初始化时可关闭过渡动画，用户切换时保留动画。", '''from fluentpy import NavigationView, FluentIcon, fluent_icon
from fluentpy.qt import QtWidgets

navigation = NavigationView()
navigation.add_sub_interface(
    QtWidgets.QLabel("首页内容"),
    fluent_icon(FluentIcon.HOME), "首页", "home"
)
navigation.add_sub_interface(
    QtWidgets.QLabel("设置内容"),
    fluent_icon(FluentIcon.SETTINGS), "设置", "settings", "bottom"
)
navigation.set_current_route("home", animated=False)''', "navigation"),
        section("visibility", "控制入口显隐", "隐藏入口会保留页面对象和原有顺序。隐藏当前入口时自动转到可见页面，全部隐藏时收起内容区。", '''navigation.set_route_visible("settings", False)
print(navigation.is_route_visible("settings"))

# 重新显示时，原页面对象仍然保留。
navigation.set_route_visible("settings", True)'''),
        section("collapse", "展开与收起", "展开宽度可以自定义，收起后保留紧凑侧栏。", '''navigation.sidebar.set_expanded_width(260)
navigation.sidebar.set_expanded(True)
navigation.currentChanged.connect(lambda route: print(route))'''),
    ]),
    page("navigation-controls", "导航控件", "Navigation controls", "导航", "面包屑、顶部导航、分段控件与标签栏，共享清晰的路由标识。", ["BreadcrumbBar", "Pivot", "SegmentedWidget", "SegmentedToolWidget", "TabBar"], [
        section("pivot", "Pivot 与分段导航", "给每个条目分配稳定的路由标识，使用 currentChanged 响应选择。", '''from fluentpy import Pivot, SegmentedWidget

pivot = Pivot()
pivot.add_item("overview", "概览")
pivot.add_item("details", "详情")
pivot.set_current_item("overview", animated=False)
pivot.currentChanged.connect(print)

segmented = SegmentedWidget()
segmented.add_item("day", "日间")
segmented.add_item("night", "夜间")''', "tabs"),
        section("breadcrumb", "面包屑", "用独立标识组织层级入口。", '''from fluentpy import BreadcrumbBar

breadcrumb = BreadcrumbBar()
breadcrumb.add_item("home", "工作台")
breadcrumb.add_item("drafts", "草稿")
breadcrumb.add_item("today", "今天")
breadcrumb.set_current_item("today")'''),
        section("tabbar", "标签栏", "标签按路由标识添加和切换，可选择设置图标。", '''from fluentpy import TabBar

tabs = TabBar()
tabs.add_tab("notes", "笔记")
tabs.add_tab("files", "文件")
tabs.set_current_tab("notes")
tabs.currentChanged.connect(print)'''),
    ]),
    page("dialogs", "窗口与对话框", "Windows & dialogs", "容器与反馈", "主窗口、独立弹窗与窗口内遮罩，为不同层级的操作提供容器。", ["FluentWindow", "FramelessDialog", "MaskedDialog", "MaskDialog", "MessageBox"], [
        section("window", "FluentWindow", "通过 content_layout 放置控件。Windows 上尝试使用系统 Mica，不可用时回退；其他平台保留 Qt 界面。", '''from fluentpy import FluentWindow, Button

window = FluentWindow("新的工作台")
window.content_layout.addWidget(Button("开始"))
window.show()'''),
        section("frameless", "独立无边框对话框", "FramelessDialog 是独立模态窗口，不提供拖动行为。建议保留实例引用并复用。", '''from fluentpy import FramelessDialog

dialog = FramelessDialog("保存草稿", "把这次灵感留到明天。", parent=window)
dialog.setYesButtonText("保存")
dialog.accepted.connect(lambda: print("已确认"))
dialog.open()''', "dialog"),
        section("masked", "遮罩对话框", "MaskedDialog 在父窗口内部绘制遮罩，面板保持正常 QWidget 绘制。MessageBox 和 MaskDialog 是它的别名。", '''from fluentpy import MaskedDialog

message = MaskedDialog("继续编辑？", "还可以再写一点。", parent=window)
message.setClosableOnMaskClicked(True)
message.finished.connect(lambda result: print(result))
message.open()''', "masked"),
    ]),
    page("cards", "卡片组件", "Cards", "容器与反馈", "从应用条目到分组设置，用五种可组合的卡片组织内容。卡片本体只负责容纳内容，操作由内部按钮和输入控件完成。", ["CardWidget", "SimpleCardWidget", "ElevatedCardWidget", "HeaderCardWidget", "GroupHeaderCardWidget"], [
        section("cardwidget", "CardWidget · 应用卡片", "普通卡片接受任意 Qt 布局。本体不响应点击、按压或键盘激活；内部按钮、输入框保留自己的交互。", '''from fluentpy import Button, CardWidget
from fluentpy.qt import QtWidgets

card = CardWidget()
row = QtWidgets.QHBoxLayout(card)
row.setContentsMargins(22, 16, 22, 16)
labels = QtWidgets.QVBoxLayout()
labels.setSpacing(3)
labels.addWidget(QtWidgets.QLabel("PluentPy", card))
labels.addWidget(QtWidgets.QLabel("MIT License", card))
row.addLayout(labels, 1)
open_button = Button("打开", card)
row.addWidget(open_button)
open_button.clicked.connect(lambda: print("打开应用"))''', "cards-apps", note="上方应用列表来自独立 Demo：第一条使用网站主图标与 PluentPy / MIT License，第二条使用 BUILDING_BANK 与“文本” / “我是文本”。应用行高 72 个逻辑像素，标题 14px、说明 12px、图标 40，打开按钮使用库默认的 80×32。尺寸由 Qt 跟随系统 DPI 缩放，参考图只用于风格和布局，不将截图像素当成控件尺寸。"),
        section("simple", "SimpleCardWidget · 简洁卡片", "悬浮与按下时保持同一背景色，适合作为安静的内容容器。本体不进入键盘焦点顺序，也没有点击反馈。", '''from fluentpy import SimpleCardWidget

simple = SimpleCardWidget()
layout = QtWidgets.QVBoxLayout(simple)
layout.addWidget(QtWidgets.QLabel("这是一张静态背景卡片", simple))
simple.set_border_radius(8)''', "cards-simple"),
        section("elevated", "ElevatedCardWidget · 悬浮卡片", "悬浮时通过轻阴影渐变表达抬升；本体不响应点击，也不会挪动布局中的控件。下方 GIF 来自真实 Qt 控件，演示移入和移出的变化。", '''from fluentpy import ElevatedCardWidget

tile = ElevatedCardWidget()
tile.setFixedSize(128, 128)
layout = QtWidgets.QVBoxLayout(tile)
layout.addStretch()
caption = QtWidgets.QLabel("轻轻悬浮", tile)
caption.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
layout.addWidget(caption)''', "cards-elevated"),
        section("header", "HeaderCardWidget · 标题卡片", "标题条与内容区之间有细分隔线。向 body_layout 添加控件或子布局；viewLayout 是同一布局的别名。标题支持换行，内容区可独立组合。", '''from fluentpy import HeaderCardWidget

requirements = HeaderCardWidget("系统要求")
message = QtWidgets.QLabel("这台设备已满足示例的界面运行要求。", requirements.view)
message.setWordWrap(True)
requirements.body_layout.addWidget(message)
details = Button("详细信息", requirements.view)
requirements.body_layout.addWidget(details)
requirements.setTitle("运行环境")''', "cards-header"),
        section("group", "GroupHeaderCardWidget · 分组设置", "每行组合图标、标题、说明和操作控件。说明为空时自动使用单行；窗口变窄时，右侧控件换到文字下方。行与行之间自动加入细分隔线。", '''from fluentpy import GroupHeaderCardWidget, LineEdit

settings = GroupHeaderCardWidget("基本设置")
choose = Button("选择")
folder_row = settings.add_group("📁", "构建目录", "选择输出位置", choose)
terminal = QtWidgets.QComboBox()
terminal.addItems(["显示终端", "隐藏终端"])
settings.add_group("▣", "运行终端", "选择预览方式", terminal)
script = LineEdit("输入入口脚本的路径")
settings.addGroup("⌘", "入口脚本", "", script)''', "cards-group", note="行与控件由卡片管理。remove_group() 会释放该行；set_group_control() 替换控件时会释放旧控件。body_layout、viewLayout 和 vBoxLayout 指向同一布局。"),
        section("demo", "运行卡片 Demo", "独立示例包含应用条目、Unicode 表情卡片、系统要求与设置分组，提供亮暗切换、实时操作反馈和圆角调整。Windows 可双击 examples/run_cards.bat。", '''python examples/cards.py''', links=[{"label": "回到开始使用 →", "page": "getting-started"}], note="上述五类由 FluentPy 独立实现，默认圆角 8；已有 Card 与 ExamplePanel 继续可用。表情使用系统 Emoji 字体，音符等图标来自微软官方 Fluent SVG。"),
    ]),
    page("feedback", "卡片与提示", "Surfaces & feedback", "容器与反馈", "用轻量容器分隔内容，用短暂反馈回应操作。", ["Card", "ExamplePanel", "Toast", "ProgressToast", "ProgressBar", "FluentScrollBar"], [
        section("cards", "卡片", "Card 提供主题感知的表面；内部内容使用普通 Qt 布局组织。", '''from fluentpy import Card
from fluentpy.qt import QtWidgets

card = Card()
layout = QtWidgets.QVBoxLayout(card)
layout.addWidget(QtWidgets.QLabel("今天的灵感"))''', "card"),
        section("toast", "单行轻提示", "只传入标题时，自动使用紧凑样式。默认可见卡片约 187×47，字体 14px，图标与关闭按钮 20px；从对应角落侧滑淡入，关闭时淡出，阴影保持轻淡。", '''from fluentpy import Toast

Toast.success(
    "代码已复制", parent=window,
    placement="top-right", timeout_ms=2400,
)''', "toast-compact"),
        section("toast-anchored", "带箭头的消息卡片", "传入 detail 可显示正文；指定 target 后，卡片靠近按钮出现并用箭头指向它，上方空间不足时移到下方。点击 × 或等待超时关闭；timeout_ms=0 时保留到手动关闭。", '''from fluentpy import Button, Toast

button = Button("保存")
window.content_layout.addWidget(button)

Toast.success(
    "已保存", detail="灵感已经收好。",
    target=button, timeout_ms=4000,
    parent=window,
)''', "toast-anchored", note="消息使用280ms淡入与轻移、180ms淡出。有父窗口时在窗口内部绘制；省略target可使用top-right、top-left、bottom-right、bottom-left四角定位。"),
        section("progress-toast", "带进度的任务提示", "在同一张小卡片中显示任务进度和最终结果。进度平滑更新，完成后图标、颜色和宽度一起过渡；可以显示在窗口四角，鼠标悬停时暂停自动关闭。", '''from fluentpy import ProgressToast

notice = ProgressToast.start(
    "正在下载文件，请稍候…",
    parent=window, placement="bottom-right",
)
notice.set_progress(35)
# 任务实际完成时调用；演示代码不执行下载。
notice.finish("下载完成", timeout_ms=1800)''', "progress-toast", note="支持top-left、top-right、bottom-left、bottom-right。340ms入场、220ms退场；进度220ms、宽度240ms、图标200ms过渡。任务未完成时一直显示，timeout_ms=0可手动关闭。"),
        section("progress-toast-indeterminate", "未知进度与失败", "暂时不知道任务总量时，轨道内只显示一段实心线，长度为轨道宽度的30%，在两端平滑往返；不会同时出现首尾两段。随后可直接切换为确定进度，失败默认保留到手动关闭。", '''notice = ProgressToast.start(
    "正在准备文件…", parent=window,
    placement="top-left", indeterminate=True,
)
notice.set_progress(60)  # 已知总量后转为确定进度
notice.fail("连接中断，请重试", timeout_ms=0)''', "progress-toast-indeterminate", note="任务动画属于Qt界面呈现，下载和后端计算交给应用处理。工作线程通过Qt信号连接set_progress，避免直接操作控件。"),
        section("progress-toast-demo", "运行任务提示 Demo", "四个角都可独立触发，支持未知进度、模拟失败、关闭全部和明暗主题；同一位置再次触发时，旧提示退场后显示新任务。Windows可双击examples/run_progress_toast.bat。", '''python examples/progress_toast.py'''),
        section("toast-demo", "运行消息浮层 Demo", "双行卡片与亮暗主题可在独立 Demo 中查看。单行复制反馈在示例工作台的“代码与性能”页体验。Windows 可双击 examples/run_toast.bat。", '''python examples/toast.py''', links=[{"label": "查看示例工作台 →", "page": "getting-started"}]),
        section("progress", "进度条", "用 Qt 的数值接口更新进度，样式跟随主题强调色。", '''from fluentpy import ProgressBar

progress = ProgressBar()
progress.setRange(0, 100)
progress.setValue(64)''', "progress"),
    ]),
    page("code-editor", "代码编辑器", "CodeEdit", "扩展组件", "带行号、缩进辅助线、当前行提示和 JSON 高亮的轻量编辑区域。", ["CodeEdit"], [
        section("codeedit", "CodeEdit", "支持 json 与 plain 两种模式。下图为实际 Qt 控件的亮色截图，以 760×540 展示嵌套 JSON；控件默认推荐尺寸保持不变。", '''from fluentpy import CodeEdit

editor = CodeEdit(language="json")
editor.set_indent_size(2)
editor.set_code('{"name": "FluentPy", "enabled": true}')
editor.textChanged.connect(lambda: print(editor.code()))''', "code-editor", "CodeEdit 提供代码编辑与语法着色，不负责校验或执行代码，也不包含补全和折叠。"),
        section("size", "尺寸与字号", "不固定宽高，放进父布局后随布局伸缩。本机 Qt 推荐编辑区域为 258×202，最小 160×80；默认代码字号为创建时的主题字号，目前是 14px。", '''# 无父布局时可直接调整尺寸。
editor.resize(480, 300)
editor.set_font_size(16)

# 有父布局时，由布局分配实际宽高。
window.content_layout.addWidget(editor)'''),
        section("editing", "编辑与模式", "默认缩进宽度为四空格，可用 set_indent_size(2) 改为两空格。Tab、Shift+Tab、Enter 与辅助线共享此设置；支持复制、粘贴、撤销和重做。高亮按 UTF-16 位置处理 emoji。", '''editor.set_language("plain")
editor.setReadOnly(True)

# 底层 Qt 编辑器可用于设置光标、选择区等。
cursor = editor.text_edit.textCursor()
print(cursor.blockNumber() + 1)'''),
        section("c-backend", "C 加速后端", "JSON 扫描和 UTF-16 位置映射已接入 C 扩展。已编译匹配的扩展时自动使用，无需更换 CodeEdit 的用法；缺少扩展时保留 Python 兼容回退。", '''print(editor.acceleration_backend())  # native 或 python''', links=[{"label": "查看编译方法、后端配置与实测 →", "page": "performance"}]),
        section("demo", "独立 Demo", "在当前本地开发源码目录中运行，可切换明暗模式并编辑内容。Windows 也可以双击 examples/run_code_editor.bat；默认按控件推荐尺寸启动，添加 --large 可展开预览，添加 --dark 可从深色启动。", "python examples/code_editor.py"),
    ]),
    page("note-timeline", "音符时间轴", "NoteTimeline", "扩展组件", "把时间、音高和时值，压缩成一眼可读的音符概览。", ["NoteTimeline", "NoteEvent"], [
        section("timeline", "音符与游标", "横轴为时间，纵轴为音高，音符宽度表示持续时间，不同轨道可以使用不同颜色。时间统一以秒为单位。", '''from fluentpy import NoteEvent, NoteTimeline

timeline = NoteTimeline()
timeline.set_notes([
    NoteEvent(start=0.0, duration=0.4, pitch=60),
    NoteEvent(start=0.5, duration=0.4, pitch=64),
    NoteEvent(start=1.0, duration=0.8, pitch=67),
    NoteEvent(start=0.0, duration=1.5, pitch=48, track=1),
], duration=2.0)
timeline.set_position(0.5)''', "timeline", "控件只负责显示，不解析音乐文件、不播放声音，也不通过点击跳转进度。截图中的竖线表示进度游标。"),
        section("pitch-colors", "音域与配色", "省略音域参数时自动适配数据。固定音域外的音符保留在数据中，但不绘制。颜色按轨道编号循环使用。", '''timeline.set_pitch_range(48, 85)
timeline.set_track_colors(["#4b7da0", "#66a58e", "#b28bbc"])
timeline.set_empty_text("载入歌曲后显示音符")

timeline.set_pitch_range()  # 恢复自动音域'''),
        section("position", "跟随播放进度", "把应用的播放时钟传给 set_position()。静态音符层会缓存，移动游标时不需要重绘整段音符。GUI 更新应在 Qt 界面线程进行。", '''timeline.set_position(1.25)
timeline.positionChanged.connect(lambda seconds: print(seconds))

# 清空后保留显示偏好。
timeline.clear()'''),
    ]),
    page("icons", "图标", "Fluent System Icons", "扩展组件", "106 个可缩放的官方 Fluent SVG 图标，保留完整 MIT 许可与来源。", ["FluentIcon", "fluent_icon", "fluent_icon_name"], [
        section("usage", "在组件中使用", "通过 FluentIcon 枚举取得资源，再由 fluent_icon() 转为 QIcon。点击下方图标可复制枚举名称。", '''from fluentpy import Button, FluentIcon, fluent_icon

button = Button("保存草稿")
button.setIcon(fluent_icon(FluentIcon.DOCUMENT_SAVE))'''),
        section("icon-library", "图标库", "搜索名称以过滤图标。图标资源来自 Microsoft Fluent UI System Icons。", preview="icons"),
        section("license", "来源与许可", "图标随项目保留 Microsoft 的完整版权及 MIT 许可。FluentPy 的许可不能替代 Qt 及各项依赖自身的许可。"),
    ]),
    page("drag-drop", "拖放文件", "Drag and drop", "基本输入", "拖入本地文件或文件夹，也可以点击浏览按钮选择路径。", ["FileDropWidget", "FolderDropWidget", "DropArea"], [
        section("files", "拖放文件组件", "默认接受 JPG、PNG、GIF，可拖入多个文件，或点击浏览文件／浏览文件夹。文件夹直接返回路径，由应用决定后续处理。", '''from fluentpy import FileDropWidget

files = FileDropWidget()
files.pathsSelected.connect(lambda paths: print("选择：", paths))
files.pathsRejected.connect(lambda items: print("未接收：", items))
window.content_layout.addWidget(files)''', "drop-file", "默认推荐尺寸300×144逻辑像素；由Qt布局和系统DPI分配实际显示尺寸。组件只选择路径，不移动、上传或读取文件内容。"),
        section("folders", "拖放文件夹组件", "只接受文件夹，默认接收一个有效路径。浏览取消、无效路径和类型不符都不会覆盖已有选择。", '''from fluentpy import FolderDropWidget

folders = FolderDropWidget()
folders.folderSelected.connect(lambda path: print("文件夹：", path))
window.content_layout.addWidget(folders)''', "drop-folder"),
        section("configuration", "类型、选择结果与信号", "后缀大小写不敏感，重复路径只接收一次。多选关闭时接收首个有效路径，其余项目通过pathsRejected给出原因。", '''files.set_file_extensions([".png", ".jpg", ".gif"])
files.set_multiple(True)
files.set_text("把图片拖到这里")
print(files.selected_paths())
files.filesSelected.connect(lambda paths: print("文件：", paths))
files.folderSelected.connect(lambda path: print("目录：", path))
files.selectionChanged.connect(lambda paths: print("选择改变：", paths))
files.clear()''', note="pathsRejected中的原因：extension类型后缀、type文件／目录类型、missing不存在、duplicate重复、multiple超出单选、invalid无效路径。存在的有效项目仍正常提交。"),
        section("motion", "拖入反馈", "拖入本地路径时，以轻量边框和背景动画提示可放下的位置。浏览和拖放都在后台检查路径，界面保持可操作；取消、清空或关闭后，旧结果不会回显。", preview="drop-file-active"),
        section("native", "后台校验与独立示例", "后缀规则、类型过滤、去重和单多选策略优先使用C，扩展不可用时自动回退Python。Qt提供原生文件信息，两种后端均保留后台校验和相同的结果信号。files.acceleration_backend()可查看实际选择。", "python examples/drop.py", links=[{"label": "可选C加速与回退 →", "page": "performance"}], note="Windows可双击examples/run_drop.bat。无需编译也能使用，工作台“拖放文件”页复用同一组件。"),
    ]),
    page("shortcut-picker", "快捷键选择器", "Shortcut picker", "基本输入", "用键帽展示快捷键，在页内录制和确认一个组合。", ["ShortcutPicker", "ShortcutDialog"], [
        section("picker", "显示与设置", "点击铅笔打开录制浮层；保存回填，取消保留原值。默认空值，以下示例设置Ctrl+Shift+A。键帽使用正常桌面逻辑尺寸。", '''from fluentpy import ShortcutPicker

picker = ShortcutPicker("Ctrl+Shift+A")
picker.sequenceChanged.connect(print)
window.content_layout.addWidget(picker)''', "shortcut-picker"),
        section("recording", "录制、重置与保存", "按键实时预览，重置恢复打开时的组合，清除后可保存为空。普通Tab／Shift+Tab切换按钮，Esc取消；在录制区可录入Enter和Ctrl+Tab，在按钮上按Enter执行操作。", preview="shortcut-recording", note="只录制一个组合，不支持Ctrl+K, Ctrl+C这种多步序列。录制时抑制所属窗口的Qt快捷键，关闭后恢复；不拦截其他窗口。"),
        section("configuration", "占用冲突与程序设置", "占用列表由应用提供，当前后端检查冲突，发生冲突时禁止保存。默认优先C，不可用时自动使用Python；Qt仍负责平台按键和QKeySequence转换。", '''picker.set_reserved_sequences(["Ctrl+S", "Ctrl+O"])
picker.set_key_sequence("Alt+L")
print(picker.key_sequence())
picker.keySequenceChanged.connect(lambda sequence: print(sequence.toString()))
print(picker.acceleration_backend())  # native 或 python''', note="无需编译也可录制、校验和保存。构建新的C扩展后重启应用，可恢复C加速。"),
        section("actions", "连接窗口内动作", "选择器提供组合键；应用用QShortcut或QAction连接操作。它不会自动注册系统全局热键。", '''from fluentpy.qt import QtGui

action = QtGui.QShortcut(picker.key_sequence(), window)
action.activated.connect(lambda: print("快捷键已触发"))
picker.keySequenceChanged.connect(action.setKey)'''),
        section("demo", "独立 Demo", "演示支持明暗主题、录制、冲突提示与保存后的实际触发。Windows可双击examples/run_shortcut_picker.bat；工作台“快捷键”页复用相同组件。", "python examples/shortcut_picker.py", links=[{"label":"C后端构建说明 →", "page":"performance"}]),
    ]),
    page("api-index", "接口索引", "API reference", "快速入门", "按名称查找当前源码中导出的组件、工具函数与主题接口。", [], [
        section("all-interfaces", "公开接口", "接口签名来自本地 Python 源码。继承自 Qt 的通用方法未逐项展开。", preview="api-index"),
    ]),
]

# A short overview, a dedicated component catalog, and topic-specific guides.
intro = next(item for item in pages if item["id"] == "introduction")
familiar = next(item for item in intro["sections"] if item["id"] == "familiar-api")
familiar["title"] = "与 Qt 接口的衔接"
familiar["text"] = "以 LineEdit 为例，左侧代码与右侧输入框同步过渡，直观看到常用 Qt 接口与 FluentPy 外观的衔接。可暂停或重播。"
familiar["code"] = familiar["code"].replace("把灵感写下来", "示例文本").replace("写点什么…", "请输入文本")
intro["intro"] = "用于 Qt for Python 的 Fluent 风格桌面组件库。"
intro["sections"] = [
    familiar,
    section("about", "项目说明", f"FluentPy 提供常用输入、日期、导航、卡片与反馈组件，可逐步接入现有 Qt 应用。默认使用 PySide6；当前为 {VERSION} 开发版本。", links=[{"label":"安装与第一个窗口", "page":"getting-started"}, {"label":"组件目录", "page":"components"}, {"label":"后端与性能", "page":"performance"}]),
    section("c-backend", "可选 C 加速的工作流程", "跟随数据从 Python 调用进入 C 后端，再交由 Qt 呈现。可切换 JSON 与日期示例；扩展不可用时，相同组件自动使用 Python 兼容实现。", nativeFlow=True),
    section("license", "许可证", "源码采用 MIT 许可证。发行时保留版权声明与许可证文本；第三方依赖遵循各自许可。", links=[{"label":"查看 MIT 许可证", "href":"assets/FluentPy-LICENSE.txt"}, {"label":"常见问题", "page":"faq"}]),
]
intro["cover"] = {"image":"showcase-home", "width":1120, "height":780, "alt":"FluentPy 组件示例程序，按分类展示原生控件", "caption":"组件示例程序：按分类查看控件，通过实际操作检查交互。", "tags":[]}
pages.insert(1, page("components", "组件目录", "Components", "开始使用", "按用途查找组件，进入对应页面查看示例、使用方法与 API。", [], [], catalog=True))
short_descriptions = {
    "buttons":"普通、强调、状态按钮与操作菜单。", "inputs":"单行、多行、搜索、密码与数值输入。",
    "selection":"复选、单选、下拉选择与滑动控件。", "date-picker":"年、月、日三列日期滚轮。",
    "time-picker":"24／12 小时制时间滚轮。", "calendar-picker":"单日、日期区间和日期时间选择。",
    "drag-drop":"文件与文件夹选择、筛选和校验。", "shortcut-picker":"组合键录制与占用冲突检查。",
    "navigation":"侧栏与带动画的页面栈。", "navigation-controls":"面包屑、页内导航与文档标签。",
    "cards":"基础、悬浮、标题与分组卡片。", "dialogs":"遮罩与无边框确认对话框。",
    "feedback":"消息提示、任务进度与状态反馈。", "code-editor":"行号、JSON 高亮和缩进参考线。",
    "note-timeline":"按音高和时间展示多轨音符。", "icons":"Microsoft Fluent System Icons 图标。",
}
for item in pages:
    if item["id"] in short_descriptions:item["catalogDescription"] = short_descriptions[item["id"]]
    if item["id"] == "date-picker":item["title"] = "日期滚轮"
    if item["id"] == "time-picker":item["title"] = "时间滚轮"
    if item["id"] == "calendar-picker":item["title"] = "日历选择"
    if item["id"] == "feedback":item["title"] = "消息与进度"
    if item["id"] == "getting-started":
        item["intro"] = "准备 Python 环境，安装项目并运行第一个窗口。"
        for example in item["sections"]:
            example["code"] = example["code"].replace("你好，FluentPy", "FluentPy 示例").replace("保存灵感", "保存")
            if example["id"] == "gallery":
                example["title"] = "运行组件示例"
                example["text"] = "示例程序按按钮、文本、日期时间、文件、卡片、导航与反馈等 12 个页面组织。每个页面提供对应组件的实际操作，不包含虚构业务流程。Windows 可双击 examples/run_showcase.bat。"
    for example in item["sections"]:
        for field in ("text", "note"):
            if isinstance(example[field], str):
                input_page = "文本与选择" if item["id"] in ("inputs", "selection") else "日期与时间滚轮"
                example[field] = example[field].replace("“输入与日期”", f"“{input_page}”").replace("“日历与日程”", "“日历选择”")
performance = next(item for item in pages if item["id"] == "performance")
performance["sections"].insert(1, section("data-flow", "数据处理流程", "Python 调用已接入的 C 后端，Qt 负责控件、布局与绘制。扩展不可用时按组件回退到 Python。", nativeFlow=True))

groups = [
    {"name": "开始使用", "pages": ["introduction", "getting-started", "components", "faq"]},
    {"name": "基础控件", "pages": ["buttons", "inputs", "selection", "shortcut-picker"]},
    {"name": "日期与时间", "pages": ["date-picker", "time-picker", "calendar-picker"]},
    {"name": "导航与容器", "pages": ["navigation", "navigation-controls", "cards"]},
    {"name": "消息与反馈", "pages": ["dialogs", "feedback"]},
    {"name": "数据与文件", "pages": ["drag-drop", "code-editor", "note-timeline"]},
    {"name": "指南与资源", "pages": ["themes", "icons", "performance", "api-index"]},
]


for group in groups:
    for identifier in group["pages"]:
        next(item for item in pages if item["id"] == identifier)["group"] = group["name"]

api = collect_api()
icons = []
tree = ast.parse((SRC / "icons.py").read_text(encoding="utf-8-sig"))
for cls in tree.body:
    if isinstance(cls, ast.ClassDef) and cls.name == "FluentIcon":
        for node in cls.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                name = node.targets[0].id
                filename = node.value.value
                if (SRC / "assets" / "icons" / filename).exists():
                    icons.append({"name": name, "file": "assets/icons/" + filename})

preview_assets = sorted(p for p in (SITE / "dist" / "assets" / "previews").iterdir() if p.suffix.lower() in (".png", ".gif") and p.name != "showcase-light.gif")
preview_version = hashlib.sha256(b"".join(p.name.encode("utf-8") + b"\0" + p.read_bytes() for p in preview_assets)).hexdigest()[:10]
data = {"pages": pages, "groups": groups, "api": api, "icons": icons, "sourceDate": "2026-10-17", "version": VERSION, "previewVersion": preview_version, "animatedPreviews": ANIMATED_PREVIEWS}
(SITE / "dist" / "data.js").write_text("window.DOCS_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8", newline="\n")
index_path = SITE / "dist" / "index.html"
index = index_path.read_text(encoding="utf-8")
index = re.sub(r'(<span class="version">)[^<]+', lambda match: match[1] + VERSION, index)
site_assets = ("data.js", "native-flow.js", "migration.js", "app.js", "styles.css", "native-flow.css", "migration.css")
asset_version = hashlib.sha256(b"".join((SITE / "dist" / name).read_bytes() for name in site_assets)).hexdigest()[:10]
index = re.sub(r'src="(data|native-flow|migration|app)\.js(?:\?v=[a-z0-9]+)?"', lambda m: f'src="{m.group(1)}.js?v={asset_version}"', index)
index = re.sub(r'href="(styles|native-flow|migration)\.css(?:\?v=[a-z0-9]+)?"', lambda m: f'href="{m.group(1)}.css?v={asset_version}"', index)
index_path.write_text(index, encoding="utf-8", newline="\n")
destination = SITE / "dist" / "assets" / "icons"
destination.mkdir(exist_ok=True, parents=True)
for path in (SRC / "assets" / "icons").glob("*.svg"):
    shutil.copy2(path, destination / path.name)
shutil.copy2(ROOT / "licenses" / "Microsoft-Fluent-System-Icons-LICENSE.txt", SITE / "dist" / "assets" / "icons-LICENSE.txt")
shutil.copy2(ROOT / "LICENSE", SITE / "dist" / "assets" / "FluentPy-LICENSE.txt")
shutil.copy2(SRC / "assets" / "brand" / "fluentpy.svg", SITE / "dist" / "assets" / "mark.svg")
print(f"Built {len(pages)} pages, {len(api)} public API entries and {len(icons)} icons from FluentPy source.")
