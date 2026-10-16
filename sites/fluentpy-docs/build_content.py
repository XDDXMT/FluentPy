"""Build documentation content and signatures from the adjacent FluentPy source."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import re
import shutil

SITE = Path(__file__).resolve().parent
ROOT = SITE.parents[1]
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
    "LineEdit": "带焦点底线动画和可选清除按钮的单行输入框。",
    "PasswordLineEdit": "带显示／隐藏密码操作的输入框。",
    "SearchLineEdit": "带搜索图标的单行输入框，沿用 QLineEdit 的输入信号。",
    "TextEdit": "跟随主题的多行文本编辑框。",
    "RichTextEdit": "TextEdit 的导出别名。",
    "CheckBox": "双态或三态复选框。",
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
    "FluentScrollBar": "悬浮时展开的自绘滚动条。",
    "CodeEdit": "JSON／纯文本编辑框，支持同步行号、缩进辅助线、当前行背景与焦点底线。",
    "DatePicker": "年、月、日三列滚轮日期选择器，支持确认、取消、范围限制和 C 日历运算。",
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
    "acceleration_backend": "返回当前 JSON 高亮器实际使用的 native 或 python 后端；C 扩展可用时自动启用。",
    "date": "读取已提交的 QDate；未选择时返回无效 QDate。",
    "set_date": "设置日期，超出范围夹到边界；无效 QDate 表示清空。",
    "setDate": "set_date 的 Qt 风格入口。",
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
    "set_title": "设置标题条文字。",
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
    excluded = {"eventFilter", "nativeEvent", "sizeHint", "minimumSizeHint", "paint_line_numbers", "update_gutter_width", "gutter_width", "highlight_current_line"}
    for path in sorted(SRC.rglob("*.py")):
        if "assets" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                item = {"name": node.name, "description": DESCRIPTIONS.get(node.name, ""), "base": ", ".join(ast.unparse(x) for x in node.bases), "file": path.relative_to(ROOT).as_posix(), "line": node.lineno, "methods": [], "signals": []}
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and (method.name == "__init__" or (not method.name.startswith("_") and not method.name.endswith("Event") and method.name not in excluded)):
                        sig = signature(method, node.name if method.name == "__init__" else None)
                        is_property = any(isinstance(d, ast.Name) and d.id == "property" for d in method.decorator_list)
                        if is_property:
                            sig = method.name + (": " + ast.unparse(method.returns) if method.returns else "") + " [property]"
                        item["methods"].append({"name": method.name, "signature": sig, "description": METHODS.get(method.name, ast.get_docstring(method) or ""), "line": method.lineno})
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
    {"name": "C", "role": "运算后端", "text": "承接 JSON 扫描、文本位置映射与日期计算。"},
    {"name": "Qt", "role": "界面呈现", "text": "管理文档、布局、绘制与输入交互。"},
]
NATIVE_METRICS = [
    {"value": "13.21×", "label": "JSON 扫描提速", "detail": "25.28 → 1.91 ms"},
    {"value": "1.52×", "label": "完整载入与首帧提速", "detail": "64.93 → 42.73 ms"},
]

ANIMATED_PREVIEWS = {
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
        section("c-backend", "Python 接口，C 运算后端", "保持 Python 的使用方式，把后端运算交给 C。今后新增或修改的后端计算统一使用 C 实现，前端继续使用 Qt/Python。", nativeFlow=True, paragraphs=[
            "已接入 CodeEdit 的 JSON 扫描与 UTF-16 位置映射，以及 DatePicker 的闰年、范围和日期步进计算。其他组件尚未全部迁移；已有 Python 后端回退保留用于兼容与性能对照。",
        ], links=[{"label": "查看 C 加速说明与实测 →", "page": "performance"}], note="以上为本机 10,000 行完整 JSON、五轮独立进程的中位数，相对原始版本。扫描与整段载入的收益分别计算；滚动和单次编辑基本不变。"),
        section("features", "先看看组件长什么样", "从日常操作到内容编辑，选择需要的组件，再把它们放进 Qt 布局。以下均为实际控件的亮色截图，点击卡片可查看用法与接口。", gallery=[
            {"title": "按钮与操作", "text": "普通、强调、文字和图标按钮，让主要操作与次要操作各有位置。", "image": "buttons", "page": "buttons", "tag": "Button · AccentButton"},
            {"title": "文字与输入", "text": "单行、多行、搜索与密码输入，提供清晰的焦点和输入反馈。", "image": "line", "page": "inputs", "tag": "LineEdit · TextEdit"},
            {"title": "三列日期选择", "text": "点击展开年、月、日滚轮，确认才回填，日历运算交给 C。", "image": "date-picker", "page": "date-picker", "tag": "DatePicker · C backend"},
            {"title": "页面与导航", "text": "用侧栏组织页面，也可以组合面包屑、分段导航和标签栏。", "image": "navigation", "page": "navigation", "tag": "NavigationView · Pivot"},
            {"title": "对话框与反馈", "text": "通过确认面板、遮罩对话框和短暂提示，传达当前操作的结果。", "image": "dialog", "page": "dialogs", "tag": "FramelessDialog · MaskedDialog"},
            {"title": "轻量代码编辑", "text": "行号、JSON 着色和缩进辅助线，适合编辑配置与查看响应数据。", "image": "code-summary", "page": "code-editor", "tag": "CodeEdit"},
            {"title": "音符时间轴", "text": "按音高与时间展示音符，提供多轨配色和播放位置游标。", "image": "timeline", "page": "note-timeline", "tag": "NoteTimeline · NoteEvent"},
        ]),
        section("familiar-api", "用熟悉的 Qt API 开始", "以普通按钮为例：Button 继承 QPushButton。替换导入和类名后，常用的文字设置、启用状态与 clicked 信号可以继续沿用。", '''from fluentpy import Button

button = Button("保存")
button.setText("保存草稿")
button.setEnabled(True)
button.clicked.connect(lambda: print("已保存"))''', migration={"before": "QPushButton", "after": "Button"}, note="迁移时请按具体组件核对构造参数与扩展接口。组合型组件通过自己的接口使用；例如 CodeEdit 通过 text_edit 访问底层 QPlainTextEdit。"),
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
    ], cover={"image": "showcase", "width": 1120, "height": 780, "caption": "新版示例工作台：侧栏导航、应用卡片与分组设置。运行示例，可直接体验库内控件的交互。", "tags": ["Python + Qt", "C 运算后端", "原生桌面组件", "MIT 开源许可"]}),
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
        section("gallery", "新的示例工作台", "工作台包含概览、输入与日期、卡片与设置、导航与反馈、代码与性能、音符视图六个可操作页面。侧栏支持展开收起，页面与文档标签内容使用库内切换动画。下图展示使用统一主图标与紧凑尺寸的新版工作台。Windows 可双击 examples/run_showcase.bat，添加 --dark 从深色启动。", "python examples/showcase.py", preview="showcase", links=[{"label": "在简介了解 C 加速 →", "page": "introduction"}], note="日期选择器需要包含日期运算的新 C 扩展；缺少扩展时，工作台仅在日期区显示提示，其他组件仍可使用。本站记录当前本地开发接口，不代表已发布新的库版本。"),
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
        section("architecture", "后端运算使用 C", "FluentPy 的后续开发统一用 C 实现新增或修改的后端运算，Python 负责接口、绑定与调用；前端继续使用现有 Qt/Python 方案。", architecture=NATIVE_LAYERS, items=[
            {"title": "已接入", "text": "CodeEdit 的 JSON 扫描、UTF-16 位置映射，以及 DatePicker 的公历、范围和步进运算，均由 fluentpy._native 扩展执行。"},
            {"title": "后续开发", "text": "其他后端计算按开发进度逐步接入，当前没有将全部组件改写为 C。"},
            {"title": "兼容路径", "text": "已有 Python 实现保留作兼容回退与实测对照。"},
        ]),
        section("backend", "前端照常使用，后端自动选择", "已编译 fluentpy._native 时，CodeEdit 自动使用 C 后端；缺少当前 Python 对应的二进制时，自动回退 Python。当前接入的是文本扫描，不会改变 JSON 内容、配色或编辑行为。", '''from fluentpy import CodeEdit
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
        ], note="这些模式互斥，选择一个即可。设置只对当前终端及其启动的程序生效；CodeEdit 在载入、切换语言或重新高亮时刷新后端选择。"),
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
        section("native", "日期运算使用 C", "闰年、每月天数、范围夹紧、步进和候选行生成均在 C 扩展中完成。DatePicker 需要重新编译包含日期接口的扩展，不增加 Python 日历运算回退。导入组件库本身仍可在没有扩展时完成。", "python -B scripts/build_native.py --zig .toolchains/zig-x86_64-windows-0.14.1/zig.exe", links=[{"label": "查看工具链与编译说明 →", "page": "performance"}], note="上面的命令在项目根目录执行，工具链首次使用需先运行 python -B scripts/fetch_zig.py。已有系统 C 编译器可运行 python -B scripts/build_native.py。JSON 扫描的倍率不代表日期组件的提速。"),
        section("demo", "单独 Demo 与示例工作台", "单独 Demo 包含空值、示例日期、清空、限定月份和亮暗切换。Windows 可双击 examples/run_date_picker.bat；完整工作台入口为 examples/run_showcase.bat。", "python examples/date_picker.py", links=[{"label": "查看新工作台 →", "page": "getting-started"}]),
    ]),
    page("buttons", "按钮", "Buttons", "基本输入", "为主要操作、次要操作和轻量链接选择合适的按钮。", ["Button", "AccentButton", "TextButton", "OutlinedButton", "RoundButton", "RoundAccentButton", "FilledButton", "HyperlinkButton", "IconButton"], [
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
    page("feedback", "卡片与提示", "Surfaces & feedback", "容器与反馈", "用轻量容器分隔内容，用短暂反馈回应操作。", ["Card", "ExamplePanel", "Toast", "ProgressBar", "FluentScrollBar"], [
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
)''', "toast-anchored", note="消息使用 240ms 淡入与轻移、140ms 淡出。有父窗口时在窗口内部绘制；省略 target 可使用 top-right、top-left、bottom-right、bottom-left 四角定位。"),
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
    page("api-index", "接口索引", "API reference", "快速入门", "按名称查找当前源码中导出的组件、工具函数与主题接口。", [], [
        section("all-interfaces", "公开接口", "接口签名来自本地 Python 源码。继承自 Qt 的通用方法未逐项展开。", preview="api-index"),
    ]),
]

groups = [
    {"name": "快速入门", "pages": ["introduction", "getting-started", "themes", "performance", "api-index"]},
    {"name": "基本输入", "pages": ["buttons", "inputs", "selection"]},
    {"name": "日期时间", "pages": ["date-picker"]},
    {"name": "导航", "pages": ["navigation", "navigation-controls"]},
    {"name": "容器与反馈", "pages": ["cards", "dialogs", "feedback"]},
    {"name": "扩展组件", "pages": ["code-editor", "note-timeline", "icons"]},
]

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

preview_assets = sorted(p for p in (SITE / "dist" / "assets" / "previews").iterdir() if p.suffix.lower() in (".png", ".gif"))
preview_version = hashlib.sha256(b"".join(p.name.encode("utf-8") + b"\0" + p.read_bytes() for p in preview_assets)).hexdigest()[:10]
data = {"pages": pages, "groups": groups, "api": api, "icons": icons, "sourceDate": "2026-10-17", "version": "0.1.0", "previewVersion": preview_version, "animatedPreviews": ANIMATED_PREVIEWS}
(SITE / "dist" / "data.js").write_text("window.DOCS_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
index_path = SITE / "dist" / "index.html"
index = index_path.read_text(encoding="utf-8")
site_assets = ("data.js", "native-flow.js", "app.js", "styles.css", "native-flow.css")
asset_version = hashlib.sha256(b"".join((SITE / "dist" / name).read_bytes() for name in site_assets)).hexdigest()[:10]
index = re.sub(r'src="(data|native-flow|app)\.js(?:\?v=[a-z0-9]+)?"', lambda m: f'src="{m.group(1)}.js?v={asset_version}"', index)
index = re.sub(r'href="(styles|native-flow)\.css(?:\?v=[a-z0-9]+)?"', lambda m: f'href="{m.group(1)}.css?v={asset_version}"', index)
index_path.write_text(index, encoding="utf-8")
destination = SITE / "dist" / "assets" / "icons"
destination.mkdir(exist_ok=True, parents=True)
for path in (SRC / "assets" / "icons").glob("*.svg"):
    shutil.copy2(path, destination / path.name)
shutil.copy2(ROOT / "licenses" / "Microsoft-Fluent-System-Icons-LICENSE.txt", SITE / "dist" / "assets" / "icons-LICENSE.txt")
shutil.copy2(ROOT / "LICENSE", SITE / "dist" / "assets" / "FluentPy-LICENSE.txt")
shutil.copy2(SRC / "assets" / "brand" / "fluentpy.svg", SITE / "dist" / "assets" / "mark.svg")
print(f"Built {len(pages)} pages, {len(api)} public API entries and {len(icons)} icons from FluentPy source.")
