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
    "TableView": "原生 QTableView 模型接口，支持三种行样式、原生排序与编辑、多选 TSV 复制和高级右键菜单。",
    "TableWidget": "原生 QTableWidget 项目接口，与 TableView 共用行样式、状态动画和现有 FluentPy 编辑控件。",
    "TableItemDelegate": "只绘制可见单元格，保留 Qt 数据角色、图标、勾选与可用状态，可继承定制列编辑器。",
    "SplashScreen": "窗口内启动遮罩，居中显示应用图标，可选加载提示，完成后渐隐并露出原有内容。",
    "InfoBar": "带状态图标和浅色背景的消息条，支持横向／纵向文字、嵌入布局、六种浮层位置和自定义原生控件。",
    "ProgressInfoBar": "基于消息条的任务状态，复用现有ProgressBar，支持未知进度、平滑百分比与完成／失败。",
    "ColorToast": "复用 Toast 的顶部色条通知，支持自定义颜色、操作按钮文字和统一内容布局content_layout，可放入自己的原生控件。",
    "AffixLineEdit": "复用 LineEdit 的前后缀输入框；装饰与中间编辑值分离。",
    "PinCodeEdit": "由原生 LineEdit 组成的多格密码／验证码输入，支持粘贴、自动前进和退格回删。",
    "ColorSwatchButton": "复用 Button 输入与状态动画的方形／圆形色块。",
    "ColorSwatchGroup": "可换行的互斥圆形色块组，提供选中圆环动画。",
    "ColorPickerPanel": "光谱、明度、RGB／HSV、Hex 和 Alpha 同步编辑；复用已有输入框、滑块及下拉框。",
    "ColorPalette": "主题色、标准色、自动颜色与更多颜色的原生 Qt 色板。",
    "ColorDialog": "复用 MaskedDialog 的窗口内颜色对话框，确认才提交，取消保留原色。",
    "ColorPickerButton": "颜色按钮与窗口内编辑弹层，沿用 ActionMenu 的动画、滚动和边界处理。",
    "ColorPaletteButton": "颜色按钮与主题色板，支持自动颜色和完整颜色对话框。",
    "ScreenColorPicker": "显式启动的屏幕取色器，冻结屏幕后采样，支持多屏与缩放坐标。",
    "EyeDropperButton": "带微软 Fluent 吸管图标的取色按钮；点击才开启屏幕采样。",
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
    "SplitButton": "左侧触发默认动作，右侧独立展开菜单；可选第二行显示版本或自定义说明。",
    "AccentSplitButton": "强调色拆分按钮，可显示动作标题与自定义说明。",
    "LoadingButton": "旋转加载图标与重复点击保护，完成后恢复文本和可用状态。",
    "ActionMenu": "QAction 驱动的窗口内菜单，支持多级子菜单、勾选与互斥、原生控件混排、右键定位和动画。",
    "SystemTrayMenu": "真正的 QMenu，可交给 QSystemTrayIcon，沿用 Qt 托盘菜单行为并跟随 FluentPy 主题。",
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
    "ModelComboBox": "直接绑定 QAbstractItemModel，选项变化与选择显示同步更新。",
    "EditableModelComboBox": "可编辑的模型下拉框，Enter 选择已有值或写入新选项。",
    "MultiSelectionComboBox": "搜索并连续选择多个选项，使用可移除标签显示；选择状态不修改源模型。",
    "TreeComboBox": "使用原生 QTreeView 搜索并选择层级模型的叶子项目。",
    "MultiSelectionTreeComboBox": "跨分组选择多个叶子项目，以可移除标签显示。",
    "TransparentComboBox": "透明背景的工具栏选择框，保留悬停、焦点与自定义文字色。",
    "FontComboBox": "搜索系统字体并预览字形，提供 QFont 值与变更信号。",
    "SpinBox": "带焦点动画与自绘箭头的整数输入框。",
    "DoubleSpinBox": "浮点数输入框，支持 Qt 精度和范围设置。",
    "Slider": "支持水平与竖向、点击定位、拖动、键盘、反转方向与渐变轨道的原生 QSlider。",
    "ToolTipSlider": "在滑块附近显示数值提示，支持格式设置、窗口内避让和隐藏清理。",
    "RangeSlider": "有序双滑块区间选择，支持水平／竖向与键盘切换端点；valuesChanged 提交区间。",
    "ProgressBar": "使用主题强调色的进度条。",
    "NavigationView": "组合侧栏与动画页面栈的导航容器。",
    "NavigationSidebar": "顶部与底部固定、中间独立滚动的侧栏，支持搜索筛选、紧凑模式和选中动画。",
    "NavigationItem": "侧栏入口，负责图标、文字和交互状态。",
    "AnimatedStackedWidget": "带淡入和横向移动过渡的页面栈。",
    "BreadcrumbBar": "按路由标识管理的面包屑导航。",
    "Pivot": "以文字入口切换内容的导航条。",
    "SegmentedWidget": "分段式文字导航。",
    "SegmentedToolWidget": "以图标作为入口的分段导航。",
    "TabBar": "按路由标识管理的标签栏。",
    "FluentWindow": "原生 Qt 主窗口，可按需接入页面导航、路由历史、响应式布局、自定义标题栏与 Windows 11 云母外壳。",
    "FluentTitleBar": "一行式 Qt 标题栏，包含历史、Windows 风格窗口操作，并为搜索、标签与自定义操作提供布局。",
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
    "ExpandableCardWidget": "通过标题条展开或收起内容的卡片，高度与箭头由 Qt 动画平滑过渡。",
    "AccordionWidget": "管理多张折叠卡片的纵向容器，可切换独立展开与互斥展开。",
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
    "FluentIcon": "107 个 Microsoft Fluent System Icons 的枚举入口。",
    "fluent_icon": "将 FluentIcon 或资源名转换为 Qt 图标。",
    "fluent_icon_name": "读取图标的资源名。",
    "QT_API": "当前选用的 Qt 后端：优先 PySide6，缺失时尝试 PyQt6。",
    "theme": "全局 ThemeManager 实例。",
}

METHODS = {
    "row_style": "读取 standard／rounded／line 行样式。",
    "set_row_style": "切换普通、圆角或细线行，不重建模型和单元格。",
    "row_height": "读取默认行高。",
    "set_row_height": "设置至少 24px 的默认行高；原生逐行尺寸接口继续可用。",
    "set_border_visible": "设置是否显示表格外框。",
    "is_border_visible": "读取外框显示配置。",
    "border_radius": "读取表格外框圆角半径。",
    "set_select_right_clicked_row": "右键点击未选条目时选择目标；已选区域保留多选。False 时不改变选择。",
    "select_right_clicked_row": "读取右键选中目标行的配置。",
    "set_empty_text": "设置无数据时的占位文字，空字符串关闭。",
    "empty_text": "读取空表格提示文字。",
    "selection_text": "按可见行列顺序返回 TSV，可包含表头，保留稀疏选区空位并引用 Tab／换行。",
    "copy_selection": "将选区 TSV 放入剪贴板；没有选择时返回 False 且不改变剪贴板。",
    "createStandardContextMenu": "生成复制、含表头复制、编辑和全选 QAction，供现有 ActionMenu 适配器复用。",
    "orientation": "读取消息条的horizontal／vertical内容方向。",
    "set_orientation": "将消息条的标题和正文切换为horizontal或vertical排列，重新测量高度。",
    "is_closable": "读取消息条是否显示原生关闭按钮。",
    "set_closable": "设置是否显示关闭按钮，仍可由应用调用close关闭。",
    "set_icon": "设置FluentIcon／QIcon图标，None恢复默认状态图标。",
    "set_background": "设置浅色与深色主题的背景颜色，省略参数恢复跟随状态的颜色。",
    "background_color": "读取当前主题下的目标背景QColor副本。",
    "notify": "创建并显示顶部色条通知，支持tone、自定义color、可选操作按钮、可见卡片宽度和关闭倒计时。",
    "tone": "读取成功／失败／警告／强调／普通信息的色调名称。",
    "set_tone": "设置success、error、warning、accent或info，并清除自定义颜色覆盖。",
    "detail": "读取通知正文文字。",
    "set_detail": "更新正文；空字符串隐藏正文行并重新排列。",
    "card_width": "读取设定的可见卡片宽度；None表示自动宽度，不包含阴影留白。",
    "set_card_width": "指定120～1200逻辑像素的可见卡片宽度，或None恢复自动；仍约束在所属窗口内。",
    "set_action": "设置原生Button的文字与回调；空文字隐藏按钮。替换时断开旧回调，close_on_action=False可保持通知。",
    "set_timeout": "设置入场完成后的关闭倒计时，悬停暂停；0表示手动关闭。",
    "prefix": "读取固定前缀文字。",
    "suffix": "读取固定后缀文字。",
    "set_prefix": "替换前缀，不修改实际输入值。",
    "set_suffix": "替换后缀，不修改实际输入值。",
    "full_text": "返回前缀、中间输入值与后缀连接后的完整文本。",
    "length": "读取分格输入的格数（1～32）。",
    "is_complete": "是否每一格均已填入字符。",
    "cells": "返回当前原生 LineEdit 单元的不可变元组。",
    "is_masked": "是否以密码掩码显示字符。",
    "set_masked": "切换密码掩码／明文显示，不修改输入内容。",
    "digits_only": "是否仅允许 ASCII 数字 0～9。",
    "set_digits_only": "切换数字限制；当前内容不合法时抛出异常，保留原配置。",
    "set_length": "改变格数，保留已有内容并按新长度截断；重新创建并接管单元控件。",
    "set_read_only": "设置各原生单元的只读状态，程序仍可调用 set_text。",
    "is_read_only": "读取分格输入的只读状态。",
    "set_color": "设置 QColor 或颜色字符串；ColorPaletteButton 另外接受 None 表示自动颜色。返回值与信号中的 QColor 为副本。",
    "color": "读取颜色副本；色板按钮处于自动模式时返回无效 QColor。",
    "colors": "返回当前色块颜色的不可变元组。",
    "set_colors": "替换色块组，接受 1～256 个有效颜色，保持现有选择值。",
    "set_previous_color": "设置预览区下半部的原始颜色，不修改当前草稿。",
    "color_format": "读取当前 rgb 或 hsv 编辑格式。",
    "set_format": "切换 rgb／hsv 编辑格式，保留同一颜色。",
    "is_valid": "当前 Hex 输入是否有效。",
    "validate": "校验当前 Hex 文本，有效时更新草稿；无效时返回 False 并保留原色。",
    "current_color": "读取对话框正在预览的草稿，确认前不修改已提交颜色。",
    "is_automatic": "色板按钮是否使用自动颜色。",
    "is_active": "是否正在屏幕取色。",
    "sample_color": "读取活动截图中指定全局逻辑坐标的颜色；越界或未启动时返回无效 QColor。",
    "cancel": "取消屏幕取色，释放覆盖层、屏幕快照与鼠标形状，不提交颜色。",
    "set_track_gradient": "为现有水平 Slider 设置至少两个 0～1 的渐变色标；可选棋盘底纹和 2～18px 厚度。",
    "clear_track_gradient": "移除渐变轨道，恢复默认 Slider 外观与交互。",
    "set_content_widget": "在现有 ActionMenu 中承载并接管自定义 QWidget，不能与 QAction 行混用。替换时释放旧内容。",
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
    "start": "创建并显示任务进度提示；placement支持六种位置，indeterminate开启未知进度。关闭后自动释放。",
    "set_progress": "更新0–100目标进度并平滑过渡，自动切回确定进度；终态后的迟到更新忽略。",
    "set_indeterminate": "切换任务的确定／不确定进度显示。",
    "is_indeterminate": "当前是否为未知进度状态。",
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
    "add_sub_interface": "注册页面、图标与路由。position='header' 固定顶部，'top'／'scroll' 放入中间列表，'bottom' 固定底部。",
    "set_expanded_width": "设置侧栏展开宽度，保留收起行为。",
    "add_header_item": "在固定顶部增加导航项，独立于中间列表滚动。",
    "set_header_widget": "设置顶部自定义控件并接管所有权，替换时释放旧控件；紧凑模式隐藏。",
    "set_footer_widget": "设置底部导航项上方的自定义控件并接管所有权；紧凑模式隐藏。",
    "set_filter_text": "只筛选中间导航项，不切换页面或禁用路由，清空恢复原有入口。",
    "filter_text": "读取当前导航筛选文字。",
    "set_expanded": "设置展开状态。",
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
    "navigation_view": "按需创建并返回页面导航容器，保留已有内容布局中的控件。",
    "add_page": "注册普通Qt页面与唯一路由；header、scroll和bottom分别放在顶部、中间滚动区和底部。",
    "remove_page": "移除指定路由；delete=True同时按Qt生命周期释放页面。",
    "current_page": "返回当前页面；无页面时返回None。",
    "switch_to": "通过路由或已注册页面切换，返回是否成功；animated=False关闭本次过渡。",
    "can_go_back": "读取路由历史是否存在可返回的有效页面。",
    "can_go_forward": "读取路由历史是否存在可前进的有效页面。",
    "go_back": "返回上一有效路由，返回是否成功。",
    "go_forward": "前进到下一有效路由，返回是否成功。",
    "set_navigation_mode": "设置auto、expanded、compact或top导航布局，复用现有页面。",
    "navigation_mode": "读取配置的导航布局模式。",
    "set_navigation_width": "设置展开侧栏宽度，至少120逻辑像素。",
    "set_navigation_breakpoint": "设置auto模式展开侧栏的窗口宽度断点，至少320逻辑像素。",
    "title_bar": "返回已创建的可扩展标题栏；尚未启用时返回None。",
    "set_title_bar": "接管一体式标题栏；Windows 保留系统边框能力，普通 Qt 控件可放入其布局。",
    "set_title_bar_enabled": "显式启用或关闭自定义标题栏，默认使用系统标题栏。",
    "is_title_bar_enabled": "读取是否使用可扩展标题栏。",
    "set_background_colors": "设置浅色与深色主题对应的不透明背景颜色，无效颜色不改变原配置。",
    "clear_background_colors": "恢复跟随默认主题的窗口背景。",
    "set_backdrop_enabled": "请求Windows 11原生云母并让窗口外壳露出材质；不支持时回退实色。",
    "is_backdrop_enabled": "读取云母请求开关，实际应用状态见backdrop_applied。",
    "backdrop_applied": "读取DWM是否接受云母且Qt外壳已露出材质；失焦或系统策略下仍可能呈中性色。",
    "sync_navigation": "根据所属窗口的历史接口刷新前进与后退按钮。",
    "set_double_click_enabled": "控制标题与空白区域双击最大化；最大化按钮隐藏或禁用时仍不可用。",
    "double_click_enabled": "读取是否允许标题栏双击最大化。",
    "set_caption_buttons_visible": "分别控制最小化、最大化与关闭按钮，保留其原有Qt行为。",
    "set_border_radius": "设置组件圆角，单位为逻辑像素，默认 8。",
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
    "setExpanded": "设置折叠卡片的展开状态；animated=False 可立即切换。",
    "is_expanded": "读取当前目标展开状态。",
    "isExpanded": "is_expanded 的 Qt 风格入口。",
    "add_card": "将折叠卡片加入当前容器并返回该卡片。",
    "addCard": "add_card 的 Qt 风格入口。",
    "cards": "按布局顺序读取容器内的折叠卡片。",
    "remove_card": "从容器移除卡片；delete=True 同时按 Qt 生命周期释放。",
    "removeCard": "remove_card 的 Qt 风格入口。",
    "set_exclusive": "设置是否最多只保留一张卡片展开，默认允许多张展开。",
    "setExclusive": "set_exclusive 的 Qt 风格入口。",
    "is_exclusive": "读取是否启用互斥展开。",
    "isExclusive": "is_exclusive 的 Qt 风格入口。",
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
    excluded = {"event", "eventFilter", "nativeEvent", "focusNextPrevChild", "sizeHint", "minimumSizeHint", "paint_line_numbers", "update_gutter_width", "gutter_width", "highlight_current_line"}
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
                        if node.name == "SplashScreen":
                            description = {
                                '__init__': '创建隐藏的启动遮罩，parent必须是QWidget；icon省略时读取所属窗口图标。',
                                'set_icon': '替换应用图标，支持QIcon、QPixmap、FluentIcon或路径。',
                                'icon': '读取当前图标副本。',
                                'set_icon_size': '设置正整数或QSize图标尺寸，窄容器内自动缩小以适应可用区域。',
                                'icon_size': '读取图标尺寸副本。',
                                'set_text': '设置可选加载提示，空文字隐藏文字区域。',
                                'text': '读取加载提示。',
                                'set_loading': '显示或隐藏加载环；仅在遮罩可见时运行动画。',
                                'is_loading': '读取加载环的显示配置。',
                                'finish': '完成启动并渐隐，animated=False立即结束；重复调用不会重启或重复发送finished。',
                            }.get(method.name, description)
                        if node.name == "CalendarPicker" and method.name == "set_date":
                            description = "设置可选的QDate；禁用或超界日期报错，无效QDate清空。"
                        if node.name in ("CalendarPicker", "DateRangePicker", "DateTimePicker") and method.name == "show_popup":
                            description = "展开页内选择器；重复调用取消旧草稿并从已提交值重新开始。"
                        if node.name == "ExpandableCardWidget" and method.name == "set_expanded":
                            description = "展开或收起内容；animated=False 立即切换。状态改变时发出 expandedChanged。"
                        if node.name == "ExpandableCardWidget" and method.name == "toggle":
                            description = "切换卡片的展开状态，保留内部控件与输入值。"
                        if node.name == "ScreenColorPicker" and method.name == "start":
                            description = "显式截图并启动屏幕取色；重复启动返回 False。采集失败发出 failed，清理后返回 False。"
                        if node.name in ("ColorPickerButton", "ColorPaletteButton") and method.name == "show_popup":
                            description = "从已提交颜色展开窗口内编辑器／色板，再次调用收起。"
                        if node.name == "PinCodeEdit" and method.name == "set_text":
                            description = "原子设置整个密码／验证码，非法字符或超长抛出异常，原值不变。"
                        if node.name == "PinCodeEdit" and method.name == "text":
                            description = "返回所有已填写字符连接后的实际值；即使掩码显示也返回明文，应由应用妥善处理。"
                        if node.name == "PinCodeEdit" and method.name == "paste":
                            description = "粘贴到当前格；整段验证码从首格回填，超长截断，非法字符拒绝整次输入。"
                        if node.name == "ColorToast" and method.name == "set_color":
                            description = "设置自定义顶部色条颜色；None恢复当前tone的主题颜色。无效颜色不改变原值。"
                        if node.name == "ColorToast" and method.name == "color":
                            description = "读取实际目标色的QColor副本，不受色条过渡动画进度影响。"
                        if node.name == "InfoBar" and method.name == "notify":
                            description = "创建并显示状态背景消息条，支持横纵方向、原生控件、六种位置和悬停暂停倒计时。"
                        if node.name == "InfoBar" and method.name == "color":
                            description = "读取状态图标颜色副本，info默认跟随强调色，可通过set_color覆盖。"
                        if node.name == "ProgressInfoBar" and method.name == "state":
                            description = "读取running／success／error任务状态。"
                        if node.name == "ProgressInfoBar" and method.name == "value":
                            description = "读取0～100目标进度；动画显示值可能暂时落后。"
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
    for name in ('TableView', 'TableWidget'):
        api[name]['base'] = 'QtWidgets.Q' + name
        api[name]['methods'] = [method for method in api[name]['methods']
                                if method['name'] not in ('selectionChanged', 'scrollContentsBy')]
        for method in api[name]['methods']:
            if method.get('inheritedFrom') == '_TableMixin':
                method.pop('inheritedFrom')
            method['description'] = {
                '__init__': ('创建项目表格，接受 TableWidget(parent) 或 TableWidget(rows, columns, parent)。'
                             if name == 'TableWidget' else '创建模型表格，随后使用 setModel 连接调用方模型。'),
                'setModel': '连接调用方的 Qt 模型，清理旧模型的悬停状态与信号连接；模型所有权不转移。',
                'border_radius': '读取表格外框圆角半径。',
                'set_empty_text': '设置空模型的提示文字；空字符串关闭提示。',
                'empty_text': '读取空表格提示文字。',
                'setBorderRadius': 'set_border_radius 的 Qt 风格入口。',
                'setBorderVisible': 'set_border_visible 的 Qt 风格入口。',
                'setSelectRightClickedRow': 'set_select_right_clicked_row 的 Qt 风格入口。',
            }.get(method['name'], method['description'])
    for method in api['TableItemDelegate']['methods']:
        method['description'] = {
            'paint': '按表格行样式绘制可见单元，保留模型文字、图标、勾选与状态角色。',
            'createEditor': '创建 FluentPy 文本或数值编辑器，可继承后按业务列设置验证与精度。',
            'updateEditorGeometry': '让编辑器在当前单元内保留少量边距。',
        }.get(method['name'], method['description'])
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
    "tables-motion": {
        "image":"tables-motion-light.gif", "poster":"tables-motion-light.png",
        "width":1000, "height":760,
        "alt":"真实 Qt 表格选择、多选、排序、切换行样式与接口，并搜索和恢复记录。",
        "caption":"表格 · 真实 Qt 选择动画与模型操作",
    },
    "splash-motion": {
        "image":"splash-motion-light.gif", "poster":"splash-motion-light.png",
        "width":720, "height":480,
        "alt":"真实 Qt 启动页面显示应用图标与加载提示，完成后渐隐，原有输入继续可用。",
        "caption":"启动页面 · 真实 Qt 控件与自然退场动画",
    },
    "theme-transition": {
        "image":"theme-transition-light.gif", "poster":"theme-transition-light.png",
        "width":1120, "height":780,
        "alt":"真实工作台的标题栏、侧栏、背景与控件同步渐变为深色，再切回浅色并演示中途反向切换。",
        "caption":"整窗主题渐变 · 真实 Qt 工作台录制",
    },
    "window-motion": {
        "image":"window-motion-light.gif", "poster":"window-motion-light.png",
        "width":1040, "height":720,
        "alt":"真实 Qt 窗口编辑文档、返回历史，并切换紧凑侧栏和顶部导航。",
        "caption":"流畅窗口 · 真实 Qt 页面与布局切换",
    },
    "slider-motion": {
        "image":"slider-motion-light.gif", "poster":"slider-motion-light.png",
        "width":900, "height":660, "alt":"真实 Qt 数值提示滑块拖动、区间变化与竖向切换。",
    },
    "menu-motion": {
        "image":"menu-motion-light.gif", "poster":"menu-motion-light.png",
        "width":900, "height":660, "alt":"真实 Qt 菜单展开子菜单、执行动作，并在同一菜单中编辑输入框和滑块。",
    },
    "combo-motion": {
        "image":"combo-motion-light.gif", "poster":"combo-motion-light.png",
        "width":880, "height":560,
        "alt":"真实 Qt 多选下拉框展开、连续选择、折叠并移除标签。",
        "caption":"多选标签 · 真实 Qt 控件录制",
    },
    "info-bar-motion": {
        "image":"info-bar-motion-light.gif", "poster":"info-bar-motion-light.png",
        "width":760, "height":440,
        "alt":"真实Qt消息条展示状态背景、横纵布局、堆叠补位、自定义图标、任务进度与完成。",
        "caption":"消息条 · 真实 Qt 控件录制",
    },
    "color-toast-motion": {
        "image": "color-toast-motion-light.gif", "poster": "color-toast-motion-light.png",
        "width": 620, "height": 520,
        "alt": "真实Qt顶部色条通知居中叠放、切换颜色、点击操作按钮，再与底部居中的小型进度提示混合排列。",
    },
    "input-motion": {
        "image": "input-motion-light.gif", "poster": "input-motion-light.png",
        "width": 620, "height": 340,
        "alt": "原生前后缀输入框输入域名，分格密码逐位自动前进、退格回删并清空。",
    },
    "toast-stack-motion": {
        "image": "toast-stack-motion-light.gif", "poster": "toast-stack-motion-light.png",
        "width": 620, "height": 600,
        "alt": "真实Qt提示在右下向上叠放，关闭中间条目平滑补位，再演示右上向下叠放。",
    },
    "color-motion": {
        "image": "color-motion-light.gif", "poster": "color-motion-light.png",
        "width": 620, "height": 650,
        "alt": "原生Qt颜色按钮展开编辑器，平滑改变色相、透明度后确认，色板展开后选择主题色。",
    },
    "sidebar-regions": {
        "image": "sidebar-regions-light.gif", "poster": "sidebar-regions-light.png",
        "width": 240, "height": 560,
        "alt": "真实Qt侧栏的顶部搜索与底部设置固定，中间列表平滑滚动、搜索筛选，并切换紧凑模式。",
    },
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
    "split-button": {
        "image": "split-button-light.gif", "poster": "split-button-light.png",
        "width": 640, "height": 300,
        "alt": "双行分体按钮：主区域执行启动，箭头展开版本菜单，选择版本后只更新第二行，再次点击主区域执行新版本。",
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
    "cards-expandable": {
        "image": "cards-expandable-light.gif", "poster": "cards-expandable-light.png",
        "width": 390, "height": 400,
        "alt": "混合、色度与锐化设置卡片通过标题条展开和收起，内容高度平滑变化，箭头同步旋转。",
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
            {"label": "浏览 107 个 Fluent 图标 →", "page": "icons"},
        ]),
        section("next", "把第一个窗口运行起来", "通过 pip 安装 fluentpy-qt，组合组件，再按需查阅接口。本站展示真实控件截图，工作台示例可从源码运行。", steps=[
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
    ], cover={"image": "showcase-home", "width": 1120, "height": 780, "alt": "FluentPy 0.7.0 工作台主页，包含欢迎横幅、半透明快捷入口、组件搜索和紧凑分类卡片", "caption": "新版工作台主页：欢迎横幅、半透明入口和可搜索的组件分类。运行示例，可直接体验库内控件的交互。", "tags": ["Python + Qt", "C 优先 · Python 兼容", "原生桌面组件", "MIT 开源许可"]}),
    page("getting-started", "开始使用", "Getting started", "快速入门", "用 Python 构建有 Fluent 质感的桌面界面。从一个窗口、一个按钮开始。", [], [
        section("about", "关于 FluentPy", "FluentPy 是独立实现的 Qt for Python 组件库，源码采用 MIT 许可。默认使用 PySide6，接口层保留 PyQt6 回退路径。当前为早期版本，API 仍可能调整。"),
        section("install", "通过 pip 安装", f"需要 Python 3.10+。{VERSION} 已在 PyPI 发布，使用 fluentpy-qt 安装；PySide6 随依赖一同安装，基本运行不需要 C 编译器。", 'python -m pip install fluentpy-qt', language='PowerShell',
                links=[{'label':'查看 PyPI 发布文件 ↗', 'href':'https://pypi.org/project/fluentpy-qt/'}],
                note='安装名是 fluentpy-qt，代码导入仍是 from fluentpy import ...。PyPI 上的 fluentpy 属于其他项目，两者不要装在同一环境。'),
        section("venv-windows", "Windows：在虚拟环境中安装", "建议为自己的应用创建独立环境。以下为 PowerShell 命令，不需要先激活环境。", '''python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install fluentpy-qt''', language='PowerShell'),
        section("venv-unix", "macOS / Linux：在虚拟环境中安装", "以下命令创建环境并安装组件库。具体桌面表现与系统 Qt 支持需在目标平台验证。", '''python3 -m venv .venv
.venv/bin/python -m pip install fluentpy-qt''', language='Shell'),
        section("first-window", "第一个窗口", "创建 QApplication 后，将组件添加到 FluentWindow 的内容布局中。", '''import sys
from fluentpy import AccentButton, FluentWindow, Toast
from fluentpy.qt import QtWidgets

app = QtWidgets.QApplication(sys.argv)
window = FluentWindow("你好，FluentPy")
window.resize(800, 560)
window.set_title_bar_enabled(True)
button = AccentButton("保存灵感")
button.clicked.connect(lambda: Toast.success("已保存", parent=window))
window.content_layout.addWidget(button)
window.show()
sys.exit(app.exec())''', note='将代码保存为 app.py，用刚才虚拟环境中的 Python 运行：Windows 为 .\\.venv\\Scripts\\python.exe app.py，macOS / Linux 为 .venv/bin/python app.py。'),
        section("wheels", "C 加速包与通用包", "pip 会根据当前解释器和平台选择兼容的 wheel。默认 auto 模式优先使用 C；扩展不可用时自动回退 Python，组件使用方式不变。", table={
            'caption':f'PyPI {VERSION} 发布包与运行路径',
            'headers':['环境', '发布文件', '默认运行路径'],
            'rows':[
                ['Windows x64 / 普通 CPython 3.13', 'cp313-cp313-win_amd64.whl', '内含 C 扩展，优先使用 C'],
                ['其他满足 Python / Qt 依赖的环境', 'py3-none-any.whl', 'Python 兼容实现，无需本机编译'],
            ],
        }, paragraphs=['当前主要验证环境为 Windows x64、CPython 3.13、PySide6 / Qt 6.11.1；从 PyPI 安装的包另已在 Qt 6.12.0 完成安装与主要控件冒烟。其他平台尚未作同等桌面验证。'],
                links=[{'label':'后端诊断与源码编译', 'page':'performance'}]),
        section("source-install", "源码安装与示例工作台", "只使用组件库时，pip 安装即可。需要运行工作台、独立示例或修改源码时，再获取仓库并在独立环境中安装。", '''git clone https://github.com/XDDXMT/FluentPy.git
cd FluentPy
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -e .
.\\.venv\\Scripts\\python.exe examples/showcase.py''', language='PowerShell',
                note='wheel 安装组件库，不包含 examples 工作台。上述命令为 Windows；macOS / Linux 使用 python3 创建环境，并将解释器路径改为 .venv/bin/python。'),
        section("gallery", "新的示例工作台", "工作台包含概览、输入与日期、日历与日程、按钮与菜单、拖放文件、卡片与设置、导航与反馈、代码与性能、音符视图九个可操作页面。侧栏支持展开收起，页面与文档标签内容使用库内切换动画。下图展示使用统一主图标与紧凑尺寸的新版工作台。Windows可双击examples/run_showcase.bat，添加--page calendar直达新增日历页。", "python examples/showcase.py", preview="showcase", links=[{"label": "日历与日程 →", "page": "calendar-picker"}, {"label": "在简介了解C加速 →", "page": "introduction"}], note=f"在源码仓库中使用对应虚拟环境运行。当前 PyPI 版本为 {VERSION}；文档随源码更新，开发中的接口可能领先于已发布版本。"),
    ]),
    page("faq", "常见问题", "Frequently asked questions", "快速入门", "关于商用、MIT许可、闭源发布、安装、C扩展和示例体验，你可能想先了解这些。", [], [
        section("commercial", "我想用这个 Python 组件库做商用软件，可以吗？", "完全可以。FluentPy采用MIT许可证，允许用于商业项目，也允许修改和分发，无需为本库另行购买商业授权。", paragraphs=[
            "分发本库或包含本库实质性代码的软件时，请保留原始版权声明和完整MIT许可证文本。可以随应用附带第三方许可文件，并在“关于”页面提供入口；仅标注作者姓名并不能代替保留许可证。",
        ], links=[{"label":"查看FluentPy的MIT许可证 ↗", "href":"assets/FluentPy-LICENSE.txt"}, {"label":"MIT许可原文（Open Source Initiative）↗", "href":"https://opensource.org/license/mit"}]),
        section("closed-source", "使用 FluentPy 后，必须把我的软件开源吗？", "MIT许可证本身不要求你公开应用源码，可以开发和分发闭源软件；仍需保留本库的版权声明与许可证文本。", paragraphs=[
            "FluentPy的MIT授权只适用于本库。Qt、PySide6／PyQt6及其他第三方依赖有各自的许可，发布应用时也需要分别遵守。",
        ], links=[{"label":"Qt的许可说明 ↗", "href":"https://www.qt.io/licensing/"}]),
        section("requirements", "开始使用需要什么环境？", "需要 Python 3.10+。使用 pip install fluentpy-qt 时会安装默认依赖 PySide6。保留 PyQt6 适配入口；当前主要验证环境为 Windows x64、CPython 3.13、PySide6／Qt 6.11.1，PyPI 包另通过 Qt 6.12.0 的安装冒烟。其他环境需对应验证。", paragraphs=[
            f"建议安装到独立虚拟环境。PyPI 当前已发布 {VERSION}，项目仍处于早期阶段，开发文档可能领先于已发布包。",
        ], links=[{"label":"安装与第一个窗口 →", "page":"getting-started"}]),
        section("package-name", "为什么安装 fluentpy-qt，代码却导入 fluentpy？", "fluentpy-qt 是 PyPI 的发行名，fluentpy 是本库的 Python 导入名；安装后原有 from fluentpy import ... 用法保持不变。", paragraphs=[
            'PyPI 上的 fluentpy 已由其他作者的项目使用，pip install fluentpy 不会安装本组件库。两个项目的导入名冲突，应使用不同的虚拟环境。',
        ], links=[{'label':'fluentpy-qt 的 PyPI 页面 ↗', 'href':'https://pypi.org/project/fluentpy-qt/'}]),
        section("native-required", "一定要编译 C 扩展，才能使用组件吗？", "不需要。C扩展是可选加速。默认auto模式优先使用C；缺少扩展、二进制无法加载或旧扩展缺少对应接口时，CodeEdit、日期／时间选择器、拖放和快捷键选择器都会自动使用Python兼容实现，组件仍可正常操作。", paragraphs=[
            "Windows x64 / 普通 CPython 3.13 安装时可直接使用内含 C 扩展的 wheel。其他环境使用通用 Python wheel；需要 C 加速时再从源码构建。FLUENTPY_BACKEND=python 强制兼容路径；只有显式选择 native 时，缺少 C 接口才会报错。",
        ], links=[{"label":"C扩展的构建与排查 →", "page":"performance"}]),
        section("native-scope", "所有组件都已经用 C 加速了吗？", "C 扩展负责已接入的文本、日期、时间、日历、拖放、快捷键、颜色和分格输入策略。Python 保留公开接口与绑定，Qt 继续负责控件、布局、绘制和动画。", paragraphs=[
            "某一段运算的加速倍数不代表整个应用都会等比例变快。例如大段JSON应使用多行CodeEdit，C扫描可以减轻高亮开销，但文本排版和绘制仍有各自的成本。",
        ], links=[{"label":"查看接入范围与实测结果 →", "page":"performance"}, {"label":"代码编辑器 →", "page":"code-editor"}]),
        section("previews", "网页里的控件可以直接操作吗？", "文档里的组件预览是FluentPy实际Qt控件的截图或GIF，浏览器中不会运行桌面Qt控件。动图可以暂停和播放；要实际点击、输入或录制快捷键，请运行独立Demo或示例工作台。", "python examples/showcase.py", paragraphs=[
            "先获取源码并安装；wheel 不包含 examples。Windows 也可以双击 examples/run_showcase.bat。带说明的复选框入口是 examples/run_checkbox.bat，工作台的“文本与选择”页也有同一组件。",
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
        section("window-transition", "整窗同步渐变", "工作台默认开启 280ms 整窗主题过渡，标题栏、侧栏、卡片、文字和按钮一起变化。使用两帧缓存合成动画，切换时只提交一次目标样式；连续反向切换从当前混合画面接续。输入或拖动会及时回到实时控件，调整窗口大小会结束过渡并释放缓存。", '''window.set_theme_transition_enabled(True)
theme.set_theme("dark", accent="#60cdff")
theme.set_theme("light", accent="#0078d4")''', "theme-transition", note="普通 FluentWindow 默认关闭此过渡，可显式开启。工作台隐藏页面合并刷新，在重新显示前同步目标主题；动画期间不逐帧重设全树样式。云母启用时，缓存过渡暂用对应主题的中性外壳色，结束后恢复系统实时合成。"),
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
        section("prebuilt", "先选择已编译的安装包", "通过 pip install fluentpy-qt 安装时，Windows x64 / 普通 CPython 3.13 会选择内含 C 扩展的 wheel，无需配置编译器。其他环境选择通用 Python wheel，默认使用兼容后端。", 'python -m pip install fluentpy-qt', language='PowerShell',
                links=[{'label':'PyPI 发布文件与平台标签 ↗', 'href':'https://pypi.org/project/fluentpy-qt/#files'}, {'label':'完整安装说明', 'page':'getting-started'}],
                note='FLUENTPY_BUILD_NATIVE 只影响源码构建，不会为已安装的通用 wheel 自动补装 C 扩展。要在其他平台使用 C，需要相应平台的原生包或从源码编译。'),
        section("build", "从源码编译 C 扩展", "先获取源码并安装构建依赖，再在项目根目录执行。已有兼容当前 Python 的系统 C 编译器时可使用以下命令；完成后重启 Python，再检查实际后端。", "python -B scripts/build_native.py", paragraphs=[
            "当前已实际验证 Windows x64、CPython 3.13.1、PySide6 / Qt 6.11.1。二进制需要匹配 Python 小版本、操作系统和架构，其他环境需要对应的构建产物。",
        ], links=[{'label':'获取源码与安装环境', 'page':'getting-started', 'anchor':'source-install'}]),
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
split.clicked.connect(lambda: print("执行默认保存"))''', "button-menus", note="ActionMenu 在窗口内部展开并支持多级子菜单。shortcut参数显示快捷键提示；实际快捷键注册由应用负责。"),
        section("split-description", "主操作与选项合体", "SplitButton 和 AccentSplitButton 支持可自定义的第二行文字，用于显示当前版本、导出格式或说明。主区域执行动作，右侧箭头展开已有的高级菜单；选择选项不会触发主动作。省略 description 保持原有单行尺寸。", '''from fluentpy import AccentSplitButton, ActionMenu

launch = AccentSplitButton("启动游戏", window, description="1.0 · 正式版")
versions = ActionMenu(window)
for version in ("1.0 · 正式版", "1.1 · 预览版", "本地开发版"):
    versions.add_action(version, callback=lambda checked=False, value=version:
                        launch.set_description(value))
launch.set_menu(versions)
launch.clicked.connect(lambda: print("启动所选版本：", launch.description()))''', "split-button", note="0.7.2 起提供，可使用 python -m pip install -U fluentpy-qt 升级。set_description / setDescription 更新第二行，空字符串恢复单行；setText 更新主文字。支持图标、亮暗主题、独立悬浮与按压反馈、箭头旋转和键盘操作。工作台“按钮与菜单”包含版本及导出格式示例。"),
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
        section("regions", "三段式侧栏", "顶部放菜单、搜索和常用入口，中间列表独立滚动，底部设置保持固定。滚动条直接使用库内 FluentScrollBar；收起时保留顶部和底部导航图标。", '''from fluentpy import NavigationView, SearchLineEdit, FluentIcon, fluent_icon
from fluentpy.qt import QtWidgets

navigation = NavigationView()
navigation.sidebar.set_expanded_width(216)
navigation.sidebar.set_expanded(True)
search = SearchLineEdit("搜索导航")
navigation.sidebar.set_header_widget(search)
search.textChanged.connect(navigation.sidebar.set_filter_text)
navigation.add_sub_interface(QtWidgets.QLabel("概览"), fluent_icon(FluentIcon.HOME), "概览", "overview", "header")
for index in range(24):
    navigation.add_sub_interface(QtWidgets.QLabel(f"内容 {index}"), fluent_icon(FluentIcon.APPS), f"项目 {index}", f"item-{index}", "scroll")
navigation.add_sub_interface(QtWidgets.QLabel("设置内容"), fluent_icon(FluentIcon.SETTINGS), "设置", "settings", "bottom")
window.content_layout.addWidget(navigation)''', "sidebar-regions", note="position='header' 固定顶部，'scroll' 放入中间滚动列表，'bottom' 固定底部；原有默认 'top' 继续作为中间列表入口。set_header_widget() / set_footer_widget() 支持自己的 Qt 内容，替换时释放旧控件，紧凑模式自动隐藏自定义内容。"),
        section("search", "筛选与路由可见性", "导航搜索仅筛选中间入口，不关闭正在编辑的页面；顶部与底部入口始终可用。清空后恢复原列表。需要真正禁用某个入口时，继续使用 set_route_visible()。", '''navigation.sidebar.set_filter_text("项目 2")
print(navigation.sidebar.filter_text())
navigation.sidebar.set_filter_text("")'''),
        section("workbench-settings", "工作台设置", "工作台左侧底部的“设置”可调整主题、强调色、云母效果、侧栏宽度与展开状态、页面切换动画和底栏后端状态。界面直接组合现有 ComboBox、Slider、ToggleSwitch、Button 与 GroupHeaderCardWidget；修改立即生效，使用 Qt 的 QSettings 自动保存在本机，恢复默认设置保留编辑内容。", '''python examples/showcase.py --page settings''', "showcase-settings", paragraphs=["标题栏与侧栏共用外壳表面，主内容保持独立的不透明背景。云母默认开启，受支持的 Windows 11 使用系统材质；关闭或系统不支持时使用同色实色表面。独立 NavigationView 保留自己的侧栏背景，放入 FluentWindow 时跟随窗口外壳。"], note="使用顶部搜索定位导航，按回车进入匹配页。重新打开示例会恢复已保存的设置；--dark 可显式以深色启动。云母在失焦或部分系统策略下可能显示中性色。"),
        section("about", "关于 FluentPy 与作者", "设置页展示运行版本、Qt 环境和项目作者“性邓的小馒头”（GitHub：XDDXMT），并提供官网、作者主页、源码仓库与问题反馈入口。链接由用户点击后打开。", preview="workbench-about"),
        section("declarations", "许可与第三方声明", "FluentPy 使用 MIT 许可证。设置页的折叠卡片可展开查看本地 LICENSE 与 THIRD_PARTY_NOTICES.md 全文，使用只读文本框显示；第三方依赖和资源遵循各自许可证。", preview="workbench-declarations"),
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
        section("window", "FluentWindow", "通过 content_layout 放置控件。普通窗口默认使用 Qt 背景，可用 set_backdrop_enabled(True) 请求 Windows 11 原生云母；不支持时回退普通背景。", '''from fluentpy import FluentWindow, Button

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
    page("cards", "卡片组件", "Cards", "容器与反馈", "从应用条目到分组设置，用卡片和折叠面板组织内容。内容区保留内部按钮与输入控件的操作；折叠卡片通过标题条展开和收起。", ["CardWidget", "SimpleCardWidget", "ElevatedCardWidget", "HeaderCardWidget", "GroupHeaderCardWidget", "ExpandableCardWidget", "AccordionWidget"], [
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
        section("expandable", "ExpandableCardWidget · 折叠设置卡片", "标题条可点击，也支持聚焦后按 Space 或 Enter 切换。内容高度和箭头同步过渡，其余卡片随布局移动；收起后保留下拉选项和滑块数值。内容区只是容器，操作内部按钮不会切换卡片。", '''from fluentpy import AccentButton, AccordionWidget, Button, ComboBox, ExpandableCardWidget, Slider
from fluentpy.qt import QtWidgets

panels = AccordionWidget()
blend = panels.add_card(ExpandableCardWidget("混合", expanded=True))
blend.body_layout.addWidget(QtWidgets.QLabel("混合模式", blend.view))
mode = ComboBox(blend.view)
mode.addItems(["正常", "正片叠底", "滤色"])
mode.setFixedWidth(150)
blend.body_layout.addWidget(mode)
blend.body_layout.addWidget(QtWidgets.QLabel("不透明度", blend.view))
opacity = Slider(parent=blend.view)
opacity.setRange(0, 100)
opacity.setValue(40)
blend.body_layout.addWidget(opacity)
actions = QtWidgets.QHBoxLayout()
apply = AccentButton("应用", blend.view)
reset = Button("重置", blend.view)
actions.addWidget(apply, 1)
actions.addWidget(reset, 1)
blend.body_layout.addLayout(actions)
apply.clicked.connect(lambda: print(mode.currentText(), opacity.value()))
reset.clicked.connect(lambda: (mode.setCurrentIndex(0), opacity.setValue(40)))
for title in ("色度", "锐化"):
    card = panels.add_card(ExpandableCardWidget(title))
    card.body_layout.addWidget(Slider(parent=card.view))
window.content_layout.addWidget(panels)
window.content_layout.addStretch()''', "cards-expandable", note="view 是内容控件，body_layout / viewLayout 是同一布局。set_expanded(False) 收起；set_expanded(True, animated=False) 立即展开。expandedChanged(bool) 用于监听目标状态。布局、绘制与动画均由 Qt / Python 实现，不依赖 C 扩展。"),
        section("accordion", "AccordionWidget · 多组展开策略", "默认各组可以独立展开。exclusive=True 时，新展开一组会收起其他组，仍可收起全部；切换策略不重建内容。可以直接向卡片的 body_layout 添加自己的表单与子布局。", '''from fluentpy import AccordionWidget, ExpandableCardWidget

accordion = AccordionWidget(exclusive=True)
first = accordion.add_card(ExpandableCardWidget("基本设置", expanded=True))
second = accordion.add_card(ExpandableCardWidget("高级设置"))
first.body_layout.addWidget(QtWidgets.QLabel("这里放置常用参数", first.view))
second.body_layout.addWidget(QtWidgets.QLabel("这里放置其他参数", second.view))
accordion.set_exclusive(False)  # 允许同时展开多组
second.set_expanded(True, animated=False)
window.content_layout.addWidget(accordion)''', note="cards() 按布局顺序读取卡片。remove_card(card) 将卡片移出容器；delete=True 同时释放卡片及内部控件。setTitle() / title() 更新或读取标题，setExpanded() / isExpanded() 提供 Qt 风格入口。"),
        section("expandable-demo", "运行折叠卡片 Demo", "查看混合模式、不透明度、应用与重置，以及色度、锐化两组参数。独立示例提供明暗主题与互斥展开切换；组件示例程序的“卡片容器”页也可直接体验。Windows 可双击 examples/run_expandable_cards.bat。", '''python examples/expandable_cards.py'''),
        section("demo", "运行基础卡片 Demo", "独立示例包含应用条目、Unicode 表情卡片、系统要求与设置分组，提供亮暗切换、实时操作反馈和圆角调整。Windows 可双击 examples/run_cards.bat。", '''python examples/cards.py''', links=[{"label": "回到开始使用 →", "page": "getting-started"}], note="卡片组件由 FluentPy 独立实现，默认圆角 8；已有 Card 与 ExamplePanel 继续可用。表情使用系统 Emoji 字体，音符等图标来自微软官方 Fluent SVG。"),
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
        section("progress-toast-demo", "运行任务提示 Demo", "重复点击同一位置可连续叠放，也可点击连发三条。支持未知进度、模拟失败、关闭全部和明暗主题；底部向上、顶部向下展开。Windows可双击examples/run_progress_toast.bat。", '''python examples/progress_toast.py'''),
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
    page("icons", "图标", "Fluent System Icons", "扩展组件", "107 个可缩放的官方 Fluent SVG 图标，保留完整 MIT 许可与来源。", ["FluentIcon", "fluent_icon", "fluent_icon_name"], [
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
pages.append(page("colors", "颜色与取色", "Color controls", "基础控件", "主题色板、精确颜色编辑、快捷色块与屏幕取色。所有表单与弹层均复用库内原生 Qt 控件。", ["ColorPickerButton", "ColorPaletteButton", "ColorDialog", "ColorPickerPanel", "ColorSwatchButton", "ColorSwatchGroup", "ColorPalette", "EyeDropperButton", "ScreenColorPicker"], [
    section("picker", "精确编辑颜色", "色谱与明度控制颜色，RGB／HSV、Hex 和透明度同步。弹层沿用 ActionMenu 的窗口内动画与边界处理；取消不提交草稿。", '''from fluentpy import ColorPickerButton

picker = ColorPickerButton("#80e4579b", window, enable_alpha=True)
window.content_layout.addWidget(picker)
picker.colorPreviewed.connect(lambda color: print("预览", color.name()))
picker.colorChanged.connect(lambda color: print("已保存", color.name()))''', preview="color-motion", note="Hex 支持 #RGB、#RRGGBB、#AARRGGBB；8 位格式的透明度在最前，与 QColor 一致。普通弹层不会创建独立窗口。"),
    section("palette", "主题色板与自动颜色", "六行主题色和标准色可直接选择，更多颜色打开完整对话框。None 表示自动颜色，由应用决定最终使用的颜色。", '''from fluentpy import ColorPaletteButton

palette = ColorPaletteButton("#0078d4", window)
window.content_layout.addWidget(palette)
palette.set_color(None)
palette.colorChanged.connect(lambda color: print(color.name() if color.isValid() else "自动"))''', preview="color-palette"),
    section("dialog", "确认与取消", "颜色对话框复用 MaskedDialog，覆盖在所属窗口内。预览色与原始色上下对照；输入无效的 Hex 时暂停确认，修正后恢复。", '''from fluentpy import Button, ColorDialog

dialog = ColorDialog("#e4579b", "选择背景颜色", window, enable_alpha=True)
open_color = Button("选择背景颜色")
open_color.clicked.connect(dialog.open)
dialog.colorSelected.connect(lambda color: print("确认颜色", color.name()))
dialog.currentColorChanged.connect(lambda color: print("预览颜色", color.name()))
window.content_layout.addWidget(open_color)''', preview="color-dialog"),
    section("panel", "嵌入编辑器与快捷色块", "ColorPickerPanel 可直接放进设置页。ColorSwatchGroup 使用 Qt 布局自动换行，并以选中圆环标记当前颜色。", '''from fluentpy import ColorPickerPanel, ColorSwatchGroup

editor = ColorPickerPanel("#e4579b", window, enable_alpha=True)
editor.set_format("hsv")
swatches = ColorSwatchGroup(["#4ba6ed", "#72d4f4", "#253e72", "#c7a2ec"], window)
swatches.colorChanged.connect(editor.set_color)
window.content_layout.addWidget(editor)
window.content_layout.addWidget(swatches)''', preview="colors"),
    section("eyedropper", "从屏幕取色", "点击吸管后冻结屏幕并显示像素预览。单击或 Enter 确认，Esc／右键取消；方向键微调。支持多显示器、负坐标和不同缩放比例。关闭窗口或删除控件会释放覆盖层和鼠标形状。", '''from fluentpy import EyeDropperButton

eyedropper = EyeDropperButton("#0078d4", window)
eyedropper.colorChanged.connect(lambda color: print(color.name()))
eyedropper.failed.connect(lambda message: print("无法读取屏幕：", message))
window.content_layout.addWidget(eyedropper)''', preview="color-eyedropper", note="仅在用户启动后读取屏幕；系统限制屏幕截图时发出 failed，不改变原色。示意图使用测试画布，文档录制不采集桌面内容。"),
    section("backend", "C 运算与 Python 回退", "Hex 解析、颜色格式化及 RGB／HSV 转换优先调用 C；扩展缺失、导入失败或旧版缺少颜色接口时自动使用行为一致的 Python 实现。控件、布局、绘制和屏幕截图由 Qt 处理。", '''from fluentpy.backends import color

print(color.backend_name())
print(color.parse_hex("#80e4579b"))  # (228, 87, 155, 128)
print(color.rgb_to_hsv(228, 87, 155))'''),
    section("demo", "运行示例", "工作台新增“颜色与取色”；Windows 可双击 examples/run_colors.bat。独立示例包含五种参考样式，并可切换明暗主题。", "python examples/colors.py"),
]))
native_inputs = next(item for item in pages if item["id"] == "inputs")
native_inputs["classes"].extend(["AffixLineEdit", "PinCodeEdit"])
native_inputs["sections"][1:1] = [
    section("affixes", "带前缀与后缀的输入框", "前后缀固定显示，输入、复制、清除和 text() 只操作中间值。可用于域名、金额及单位；full_text() 返回拼接后的完整文字。", '''from fluentpy import AffixLineEdit

address = AffixLineEdit("example.hostname", prefix="https://", suffix=".com")
address.setText("fluentpy")
window.content_layout.addWidget(address)
print(address.text())       # fluentpy
print(address.full_text())  # https://fluentpy.com
address.set_suffix(".cn")''', preview="input-motion"),
    section("pin-code", "多格密码与验证码", "每格复用同一个 LineEdit，支持自动前进、方向键、退格回删、整段粘贴和输入法提交。默认4格、仅数字且掩码显示；可切换为明文验证码。", '''from fluentpy import PinCodeEdit

pin = PinCodeEdit(4, masked=True)
pin.completed.connect(lambda _value: print("密码已填写完整"))
window.content_layout.addWidget(pin)

otp = PinCodeEdit(6, masked=False)
window.content_layout.addWidget(otp)
otp.set_text("123456")
print(otp.is_complete())''', preview="advanced-inputs", note="支持1～32格。digits_only=False 可接受可显示的Unicode字符。set_text 超长或非法时抛出异常并保留原值；用户粘贴超长时按格数截断。text() 返回明文，应用应避免把真实密码写入日志。字符校验与分格优先C，旧扩展自动回退Python。"),
    section("advanced-input-demo", "运行前后缀与分格输入 Demo", "独立示例和工作台“文本与选择”页都直接使用库内控件。Windows 可双击 examples/run_advanced_inputs.bat。", "python examples/advanced_inputs.py"),
]
feedback_page = next(item for item in pages if item["id"] == "feedback")
feedback_page["classes"].insert(3,"ColorToast")
feedback_page["sections"].insert(2, section("color-toast", "可自定义顶部颜色的通知", "顶部3px色条搭配标题、正文和可选操作按钮。使用现有Toast的窗口内表面、关闭按钮及堆叠动画；操作按钮直接使用Button。支持成功、失败、警告、注意、信息和任意自定义颜色。", '''from fluentpy import ColorToast

notice = ColorToast.notify(
    "通知标题", detail="这是一条带操作按钮的消息。",
    parent=window, placement="top-center", color="#858585",
    action_text="查看详情", action_callback=lambda: print("查看详情"),
    card_width=300, timeout_ms=4000,
)
notice.set_color("#009faa")''', preview="color-toast-motion", note="动作默认关闭当前通知；close_on_action=False保持显示。倒计时在入场完成后开始，悬停暂停。颜色可传QColor／颜色字符串；set_color(None)恢复当前tone的主题颜色。"))
feedback_page["sections"].insert(3, section("color-toast-positions", "位置与卡片宽度", "Toast、ColorToast 和 ProgressToast 均支持六种位置：top-left、top-center、top-right、bottom-left、bottom-center、bottom-right。最新消息靠近锚定边，顶部向下、底部向上扩展；相同窗口与位置可混合排列。", '''from fluentpy import ColorToast, ProgressToast

ColorToast.success("保存完成", detail="修改已保存。", parent=window, placement="top-right")
ColorToast.error("连接失败", detail="请稍后重试。", parent=window, placement="bottom-center", card_width=400)
ColorToast.warning("需要确认", detail="请检查设置。", parent=window, placement="top-left")
ColorToast.info("信息", detail="普通通知。", parent=window, action_text="Action", timeout_ms=0)
ProgressToast.start("Custom toast view", parent=window, placement="bottom-center", severity="warning", indeterminate=True)''', preview="color-toast", note="card_width是可见卡片的逻辑像素宽度，不含阴影；None自动按文字测量，超出所属窗口时自动约束并换行。图中的小型进度提示复用ProgressToast，不影响单段进度线。"))
feedback_page["sections"].insert(4, section("color-toast-content", "自己编排通知内容", "通知内部使用统一的content_widget容器和content_layout纵向布局。除了设置action_text／set_action的按钮文字，也可在现有布局中加入输入框、多个按钮或其他原生控件。Qt按实际布局测量换行与高度，内容变化后自动重新排列。", '''from fluentpy import Button, ColorToast, LineEdit
from fluentpy.qt import QtWidgets

notice = ColorToast("保存备注", "内容由应用编排。", window, card_width=340)
editor = LineEdit("输入备注", notice.content_widget)
notice.content_layout.addWidget(editor)
actions = QtWidgets.QHBoxLayout()
save = Button("保存", notice.content_widget)
cancel = Button("取消", notice.content_widget)
save.clicked.connect(lambda: print(editor.text()))
save.clicked.connect(notice.close)
cancel.clicked.connect(notice.close)
actions.addWidget(save)
actions.addWidget(cancel)
actions.addStretch()
notice.content_layout.addLayout(actions)
notice.show_at("top-right")''', preview="color-toast-content", note="content_layout中已有标题／正文／可选操作行，直接addWidget或addLayout；不要给content_widget重复设置布局。自定义按钮的文字、回调与关闭行为由应用决定。"))
feedback_page["sections"].insert(5, section("color-toast-demo", "运行顶部色条通知 Demo", "在工作台“消息与对话框”页向下找到“顶部色条通知”，或运行独立示例。可直接选择颜色、位置、宽度、自动关闭，修改标题／正文及按钮文字；“自定义内容示例”可操作输入框和两个原生按钮。Windows可双击examples/run_color_toast.bat。", "python examples/color_toast.py", preview="color-toast-demo"))
feedback_page["sections"].insert(2, section("toast-stack", "连续提示与堆叠", "同一窗口、同一角落的 Toast 和 ProgressToast 共用排列。最新提示靠近锚定角：底部向上、顶部向下排列，关闭后以240ms平滑补位。提示过多时移除最旧条目，保留新消息；不同窗口和角落独立管理。", '''from fluentpy import ProgressToast, Toast

for index in range(4):
    task = ProgressToast.start(
        "正在下载文件中，请稍候…", parent=window,
        placement="bottom-right", indeterminate=True, severity="warning",
    )
Toast.success("下载成功", parent=window, placement="bottom-right", timeout_ms=0)''', preview="toast-stack-motion", note="severity='warning' 使用图中的琥珀色状态图标与进度线，默认 info 保留原强调色。进度轨道仍只显示一段移动实心线。指定 target 的带箭头提示继续跟随目标，不进入角落堆叠。"))
feedback_page["classes"][2:2]=["InfoBar","ProgressInfoBar"]
feedback_page["sections"].insert(2, section("info-bar", "消息条", "InfoBar使用状态图标、标题、正文和状态背景，支持信息、成功、警告、失败以及自定义图标／明暗背景。标题和正文可横向或纵向排列，操作按钮继续使用已有Button。入场、退场、悬停暂停及六种位置共用已有通知逻辑。", '''from fluentpy import InfoBar

notice = InfoBar.success(
    "保存完成", detail="当前设置已经写入本地文件。", parent=window,
    placement="top-center", orientation="horizontal", timeout_ms=4000,
    action_text="打开目录", action_callback=lambda: print("打开目录"),
)
notice.set_orientation("vertical")
notice.set_closable(True)''', preview="info-bar-motion", note="独立实现，仅参考公开的消息条交互与视觉示意。复用FluentPy自身的Qt布局、按钮、堆叠和计时，不依赖qfluentwidgets，也未复制其实现或图像。已有Toast、ColorToast、ProgressToast继续使用原组件。"))
feedback_page["sections"].insert(3, section("info-bar-inline", "嵌入页面与自定义内容", "直接构造InfoBar并加入已有Qt布局，即可作为页面内的消息使用；调用show_at则作为窗口内浮层显示。content_widget／content_layout是统一内容容器，可继续放入自己的控件。按钮文字、回调和关闭行为由应用决定。", '''from fluentpy import Button, FluentIcon, InfoBar, LineEdit

bar = InfoBar("检查设置", "请确认输出目录。", window,
              orientation="vertical", tone="warning", closable=False)
editor = LineEdit("输入目录", bar.content_widget)
bar.content_layout.addWidget(editor)
confirm = Button("确认目录", bar.content_widget)
confirm.clicked.connect(bar.close)
bar.content_layout.addWidget(confirm)
window.content_layout.addWidget(bar)

bar.set_icon(FluentIcon.FOLDER)
bar.set_background("#f0f1fc", "#303048")
bar.show()''', preview="info-bar", note="内联消息的位置由所属Qt布局决定；不进入浮层排列。set_background()无参数恢复状态背景；closable=False隐藏关闭按钮，应用仍可close。自定义控件请使用可伸缩布局。"))
feedback_page["sections"].insert(4, section("progress-info-bar", "任务消息条", "ProgressInfoBar沿用消息条表面和布局，复用已有ProgressBar及任务状态图标。未知进度显示旋转状态；提交百分比后显示平滑进度，可原位切换为完成或失败。此组件只展示状态，实际任务由应用执行。", '''from fluentpy import ProgressInfoBar

task = ProgressInfoBar.start(
    "正在导出", detail="正在准备文件，请稍候…", parent=window,
    placement="bottom-center", indeterminate=True,
)
task.set_progress(65)
task.set_detail("已处理 65%，正在写入剩余文件。")
task.finish("导出完成", timeout_ms=1800)

failed = ProgressInfoBar.start("上传文件", parent=window)
failed.set_progress(36)
failed.fail("连接中断", timeout_ms=0)''', note="value()返回0～100的目标值，state()为running／success／error。完成后忽略后续进度与重复终态信号；失败保留已完成进度。任务开始时不自动关闭。已有小型ProgressToast维持原来的单段进度线。"))
feedback_page["sections"].insert(5, section("info-bar-demo", "运行消息条示例", "工作台“消息与对话框”→“自定义测试”，在组件选择中选“消息条”或“任务消息条”。独立示例仍提供逐项按钮和完整测试选项，Windows可双击examples/run_info_bar.bat。", "python examples/info_bar.py", preview="info-bar-demo"))
feedback_page["sections"].insert(5, section("workbench-inline-bars", "工作台中的嵌入示例", "工作台“消息与对话框”页顶部选择“嵌入示例”，可体验三组页面内容：可关闭的消息、带输入框与提交反馈的备注，以及从35%开始、可手动推进和完成的任务消息。它们直接占据布局空间，滚动时随页面移动，关闭后下方内容自动上移。“恢复全部示例”可反复恢复体验。", "python examples/showcase.py --page feedback", preview="info-bar-embedded", note="本组示例直接复用现有InfoBar、ProgressInfoBar、LineEdit和Button。任务只演示状态；不启动实际文件处理。"))
feedback_page["sections"].insert(2, section("feedback-playground", "选择、修改、直接测试", "工作台将五种消息组件集中到一个预览区：选择消息条、顶部色条吐司、任务消息或轻提示，修改右侧标题和正文，原生组件会实时更新。状态与位置用下拉选择，进度用滑块调整；宽度、颜色、方向等更多设置默认收起。点击“测试效果”可按当前配置体验窗口浮层，“连续三条”检查堆叠；嵌入示例和对话框位于独立页签。", "python examples/showcase.py --page feedback", preview="feedback-playground", note="界面直接复用现有组件。窄窗口自动改为上下排列；关闭页面或切换页签后清理测试消息与动画。独立组件Demo继续保留完整用例。"))
for _section in feedback_page["sections"]:
    if _section["id"]=="color-toast-demo":
        _section["text"]="工作台“消息与对话框”→“自定义测试”，组件选择“顶部色条吐司”。标题、正文、状态和位置可直接修改；顶部颜色、宽度和自动关闭在“更多设置”中。独立示例继续支持完整操作按钮和自定义内容，Windows可双击examples/run_color_toast.bat。"
    if _section["id"]=="progress-toast-demo":
        _section["text"]="工作台“消息与对话框”→“自定义测试”，组件选择“任务吐司”，用滑块和结果选择体验进度与完成／失败；未知进度在“更多设置”中。独立示例保留模拟下载与连发，Windows可双击examples/run_progress_toast.bat。"
intro = next(item for item in pages if item["id"] == "introduction")
familiar = next(item for item in intro["sections"] if item["id"] == "familiar-api")
familiar["title"] = "与 Qt 接口的衔接"
familiar["text"] = "以 LineEdit 为例，左侧代码与右侧输入框同步过渡，直观看到常用 Qt 接口与 FluentPy 外观的衔接。可暂停或重播。"
familiar["code"] = familiar["code"].replace("把灵感写下来", "示例文本").replace("写点什么…", "请输入文本")
intro["intro"] = "用于 Qt for Python 的 Fluent 风格桌面组件库。"
intro["sections"] = [
    section('install', '安装 FluentPy', '使用 fluentpy-qt 安装，Python 代码仍导入 fluentpy。建议放入独立虚拟环境；默认依赖 PySide6，无 C 扩展时自动使用 Python 兼容实现。',
            'python -m pip install fluentpy-qt', language='PowerShell',
            links=[{'label':'安装与第一个窗口', 'page':'getting-started'}, {'label':'PyPI 发布页 ↗', 'href':'https://pypi.org/project/fluentpy-qt/'}]),
    familiar,
    section("about", "项目说明", f"FluentPy 提供常用输入、日期、导航、卡片与反馈组件，可逐步接入现有 Qt 应用。默认使用 PySide6；当前 {VERSION} 为已发布的早期版本，接口仍可能调整。", links=[{"label":"组件目录", "page":"components"}, {"label":"后端与性能", "page":"performance"}]),
    section("c-backend", "可选 C 加速的工作流程", "跟随数据从 Python 调用进入 C 后端，再交由 Qt 呈现。可切换 JSON 与日期示例；扩展不可用时，相同组件自动使用 Python 兼容实现。", nativeFlow=True),
    section("license", "许可证", "源码采用 MIT 许可证。发行时保留版权声明与许可证文本；第三方依赖遵循各自许可。", links=[{"label":"查看 MIT 许可证", "href":"assets/FluentPy-LICENSE.txt"}, {"label":"常见问题", "page":"faq"}]),
]
intro["cover"] = {"image":"showcase-home", "width":1120, "height":780, "alt":"FluentPy 组件示例程序，按分类展示原生控件", "caption":"组件示例程序：按分类查看控件，通过实际操作检查交互。", "tags":[]}
pages.insert(1, page("components", "组件目录", "Components", "开始使用", "按用途查找组件，进入对应页面查看示例、使用方法与 API。", [], [], catalog=True))
short_descriptions = {
    "buttons":"普通、强调、状态按钮与操作菜单。", "inputs":"单行、多行、搜索、密码与数值输入。",
    "selection":"复选、单选、下拉选择与滑动控件。", "date-picker":"年、月、日三列日期滚轮。",
    "colors":"主题色板、RGBA／HSV、颜色对话框、快捷色块与屏幕取色。",
    "time-picker":"24／12 小时制时间滚轮。", "calendar-picker":"单日、日期区间和日期时间选择。",
    "drag-drop":"文件与文件夹选择、筛选和校验。", "shortcut-picker":"组合键录制与占用冲突检查。",
    "navigation":"侧栏与带动画的页面栈。", "navigation-controls":"面包屑、页内导航与文档标签。",
    "cards":"基础、悬浮、分组与动画折叠卡片。", "dialogs":"遮罩与无边框确认对话框。",
    "feedback":"消息条、顶部色条、自定义操作与任务进度提示。", "code-editor":"行号、JSON 高亮和缩进参考线。",
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
                example["text"] = "0.7.0 工作台主页使用欢迎横幅、半透明快捷入口和紧凑分类卡片。14 个组件分类均可整卡点击，支持按名称或 API 搜索、空结果清空和随内容宽度换列；宽屏内容居中显示。原有 FluentWindow 侧栏、返回历史、右键菜单、主题、云母与设置保存继续可用。Windows 可双击 examples/run_showcase.bat。"
    for example in item["sections"]:
        for field in ("text", "note"):
            if isinstance(example[field], str):
                input_page = "文本与选择" if item["id"] in ("inputs", "selection") else "日期与时间滚轮"
                example[field] = example[field].replace("“输入与日期”", f"“{input_page}”").replace("“日历与日程”", "“日历选择”")
performance = next(item for item in pages if item["id"] == "performance")
performance["sections"].insert(1, section("data-flow", "数据处理流程", "Python 调用已接入的 C 后端，Qt 负责控件、布局与绘制。扩展不可用时按组件回退到 Python。", nativeFlow=True))

pages.insert(next(i for i, item in enumerate(pages) if item['id'] == 'selection')+1,
    page("combo-boxes", "下拉选择", "Combo boxes", "基础控件",
         "从固定选项到可编辑、多选和树形数据，用同一套原生 Qt 模型与视图完成选择。",
         ["ComboBox", "EditableComboBox", "ModelComboBox", "EditableModelComboBox", "MultiSelectionComboBox",
          "TreeComboBox", "MultiSelectionTreeComboBox", "TransparentComboBox", "FontComboBox"], [
        section("playground", "自定义与测试", "在工作台“文本与选择 → 下拉选择”中，用一个组件类型选择器切换九种示例。左侧直接交互，右侧修改提示文字、禁用状态与模型名称。Windows 可双击 examples/run_combo_boxes.bat。",
                "python examples/combo_boxes.py", "combo-playground"),
        section("selection-motion", "连续选择与移除", "多选时菜单保持展开。点击已选项取消，收起后点击标签的 × 移除；空间不足时显示 +N，完整名称保留在提示中。", preview="combo-motion"),
        section("basic", "普通选择与业务数据", "复用现有 ComboBox，增加未选择提示、业务数据、增删改、禁用选项和键盘操作。长列表滚动显示；窗口边缘自动缩短弹层。", '''from fluentpy import ComboBox

environment = ComboBox()
environment.addItem("开发环境", userData="dev")
environment.addItem("生产环境", userData="prod")
environment.setPlaceholderText("请选择环境")
environment.setCurrentIndex(-1)
environment.currentIndexChanged.connect(lambda row: print(environment.currentData()))
environment.setMaxVisibleItems(6)''', "combo-basic",
                note="setCurrentIndex(-1) 清除选择，clear() 会删除模型中的选项。activated 只表示用户确认；currentIndexChanged/currentTextChanged 也反映程序与模型修改。"),
        section("editable", "可编辑与补全", "输入已有名称后 Enter 选择该项，输入新名称后 Enter 添加一次。内置 LineEdit 保留输入法、复制和焦点动画；也可设置自己的原生 QCompleter。", '''from fluentpy import EditableComboBox
from fluentpy.qt import QtWidgets

branch = EditableComboBox()
branch.addItems(["main", "develop", "release"])
branch.setPlaceholderText("选择或输入分支名")
branch.setCurrentIndex(-1)
completer = QtWidgets.QCompleter(["main", "develop", "release"], branch)
branch.setCompleter(completer)
branch.editTextChanged.connect(print)''', "combo-editable"),
        section("model", "绑定现有 Qt 模型", "ModelComboBox 和 EditableModelComboBox 共用同一模型协议，不复制选项。重命名、插入、移除与排序会同步显示；选择使用持久索引跟随原项目。模型由调用方管理。", '''from fluentpy import ModelComboBox, EditableModelComboBox
from fluentpy.qt import QtGui

environments = QtGui.QStandardItemModel(window)
environments.appendRow(QtGui.QStandardItem("开发环境"))
environments.appendRow(QtGui.QStandardItem("生产环境"))
model_choice = ModelComboBox()
model_choice.setModel(environments)
editable_choice = EditableModelComboBox()
editable_choice.setModel(environments)
environments.setData(environments.index(0, 0), "本地开发")''', "combo-model",
                note="自定义模型通过 flags() 控制禁用与可选状态。可编辑模型新增选项需要实现 insertRows 和 setData；setModel 不接管模型所有权。"),
        section("multiple", "可搜索的多选标签", "复用原生 QListView 和 Qt 过滤代理。多选状态属于当前组件，同一模型可以服务多个选择框，互不修改模型的 CheckStateRole。", '''from fluentpy import MultiSelectionComboBox

targets = MultiSelectionComboBox()
targets.addItem("Windows", "win")
targets.addItem("Linux", "linux")
targets.addItem("macOS", "mac")
targets.setSelectedIndexes([0, 1])
targets.selectionChanged.connect(lambda indexes: print(targets.selectedData()))
# targets.clearSelection()  # 保留全部选项''', "combo-multi"),
        section("tree", "层级项目与完整路径", "用 QStandardItemModel 的父子行构建层级，父项用于展开，叶子用于选择。搜索子项时保留祖先分组。使用 QModelIndex 表示选择，避免不同分组的相同行号产生歧义。", '''from fluentpy import TreeComboBox
from fluentpy.qt import QtGui

project_model = QtGui.QStandardItemModel(window)
folder = QtGui.QStandardItem("界面")
folder.appendRow(QtGui.QStandardItem("主窗口"))
folder.appendRow(QtGui.QStandardItem("设置页面"))
project_model.appendRow(folder)
project = TreeComboBox()
project.setModel(project_model)
project.setCurrentModelIndex(project_model.index(1, 0, project_model.index(0, 0)))
project.currentModelIndexChanged.connect(lambda index: print(project.currentPath()))''', "combo-tree"),
        section("tree-multiple", "跨分组多选", "树形多选保留标签交互，setSelectedIndexes 接受同一模型中的叶子 QModelIndex。无效、其他模型或不可选的索引被拒绝，已有选择不变。", '''from fluentpy import MultiSelectionTreeComboBox

projects = MultiSelectionTreeComboBox()
projects.setModel(project_model)
parent_index = project_model.index(0, 0)
projects.setSelectedIndexes([project_model.index(0, 0, parent_index),
                             project_model.index(1, 0, parent_index)])
projects.selectionChanged.connect(lambda indexes: print(projects.selectedTexts()))''', "combo-tree-multi"),
        section("transparent", "工具栏中的透明选择", "透明样式沿用普通下拉框的数据和键盘接口。悬停、禁用与键盘焦点仍可识别；文字颜色可单独设置，传入 None 恢复主题颜色。", '''from fluentpy import TransparentComboBox

scope = TransparentComboBox()
scope.addItems(["当前文档", "整个项目", "所有文件"])
scope.setTextColor("#008e9b")''', "combo-transparent"),
        section("fonts", "系统字体与字形预览", "字体列表来自 Qt 的系统字体数据库，支持搜索并按实际字体显示每一行。currentFontChanged 直接提供 QFont，适合连接编辑器的 setFont。", '''from fluentpy import FontComboBox
from fluentpy.qt import QtGui, QtWidgets

font_choice = FontComboBox()
font_choice.setCurrentFont(QtGui.QFont("Segoe UI"))
sample = QtWidgets.QLabel("FluentPy · 字体预览 Aa 0123")
font_choice.currentFontChanged.connect(sample.setFont)''', "combo-font",
                note="可用字体由运行机器决定。界面行为借鉴公开下拉选择模式，代码、文案与配图均为 FluentPy 自主实现。"),
    ], catalogDescription="固定选项、可编辑、模型绑定、多选标签、树形与系统字体。"))
selection_page = next(item for item in pages if item['id'] == 'selection')
next(item for item in selection_page['sections'] if item['id'] == 'combo')['links'] = [
    {'label':'完整下拉选择示例与 API', 'page':'combo-boxes'}]

pages.insert(next(i for i, item in enumerate(pages) if item['id'] == 'combo-boxes')+1,
    page('sliders', '滑块', 'Sliders', '基础控件',
         '用滑块调整一个数值，或用两个端点选定区间。水平与竖向保留一致的外观和交互。',
         ['Slider', 'ToolTipSlider', 'RangeSlider'], [
        section('playground', '自定义与测试', '直接点击工作台侧栏“滑块”，集中切换三种滑块。右侧直接调整数值与方向，更多设置默认收起；组件概览中也可搜索 Slider。独立示例可切换明暗主题。',
                'python examples/sliders.py', 'sliders-playground', note='Windows 可双击 examples/run_sliders.bat。'),
        section('motion', '拖动、提示与区间', '点击和键盘调整时手柄平滑过渡，直接拖动紧随指针；数值提示淡入淡出并跟随手柄。按压和悬停有中心圆反馈，区间端点不能越过对方，方向切换保留参数。', preview='slider-motion'),
        section('horizontal', '标准滑块', '继续使用已有 Slider。继承 QSlider 的范围、步长和信号，点击轨道会定位到该处，再拖动继续调整。绘制与输入共用同一坐标规则。', '''from fluentpy import Slider
from fluentpy.qt import QtCore

volume = Slider(QtCore.Qt.Orientation.Horizontal)
volume.setRange(0, 100)
volume.setValue(35)
volume.setSingleStep(1)
volume.setPageStep(10)
volume.valueChanged.connect(print)''', 'slider-horizontal'),
        section('vertical', '竖向与反转方向', '竖向滑块使用相同的 Fluent 外观，默认低值在下。支持 setInvertedAppearance 反转显示，RTL 布局下输入位置与轨道保持一致。', '''vertical = Slider(QtCore.Qt.Orientation.Vertical)
vertical.setRange(-50, 50)
vertical.setValue(10)
vertical.setFixedSize(38, 220)
vertical.setInvertedAppearance(False)''', 'slider-vertical'),
        section('tooltip', '跟随数值提示', 'ToolTipSlider 在悬停、聚焦和拖动时显示当前数值，例如 65；不会自动变成百分比。提示在所属窗口内部避让边缘，不接收鼠标，也不创建独立弹窗；隐藏、失焦或禁用时收起。', '''from fluentpy import ToolTipSlider

value_slider = ToolTipSlider()
value_slider.setRange(-50, 150)
value_slider.setValue(65)''', 'slider-tooltip'),
        section('range', '双滑块区间选择', 'RangeSlider 维护 lower ≤ upper。程序设置非法区间时整次拒绝，拖动时限制端点互不穿越。点击更近的端点即可调整；Space 切换当前端点，再使用原生方向键、Home／End 与翻页键。', '''from fluentpy import RangeSlider

interval = RangeSlider()
interval.setRange(0, 100)
interval.setValues(20, 80)
interval.valuesChanged.connect(lambda lower, upper: print(lower, upper))
interval.setActiveHandle("upper")
print(interval.values())''', 'slider-range', note='QSlider 的 rangeChanged 仍表示允许的最小／最大值；业务区间使用 valuesChanged。当前端点可通过 activeHandle 读取。'),
        section('range-vertical', '竖向区间', '同一个 RangeSlider 设置竖向即可使用。两端重合时仍可通过 Space 切换目标端点，键盘焦点环标示正在调整的一端。', '''vertical_interval = RangeSlider(QtCore.Qt.Orientation.Vertical)
vertical_interval.setRange(0, 100)
vertical_interval.setValues(25, 75)
vertical_interval.setFixedSize(38, 220)''', 'slider-range-vertical'),
        section('tracking', '实时更新或松开提交', 'setTracking(False) 保留拖动过程的 sliderPosition 和 sliderMoved，在松开时提交 valueChanged；区间也采用相同规则。原有渐变与棋盘轨道继续可用。', '''volume.setTracking(False)
volume.sliderMoved.connect(lambda position: print("预览", position))
volume.valueChanged.connect(lambda value: print("提交", value))
volume.set_track_gradient([(0, "#16418c"), (1, "#00bbbd")], thickness=8)'''),
    ], catalogDescription='水平、竖向、数值提示、双滑块区间与原生键盘交互。'))
pages.insert(next(i for i, item in enumerate(pages) if item['id'] == 'buttons')+1,
    page('menus', '菜单', 'Menus', '导航与容器',
         '在已有 ActionMenu 上组织动作、子菜单与原生控件，系统托盘使用真正的 Qt 菜单。',
         ['ActionMenu', 'SystemTrayMenu'], [
        section('playground', '自定义与测试', '工作台“按钮与菜单 → 右键菜单”中，直接在预览区域点击鼠标右键，再切换多级、勾选、控件混排等类型。键盘也可用菜单键或 Shift+F10；托盘图标仅在点击对应按钮后出现。',
                'python examples/menus.py', 'menus-playground', note='Windows 可双击 examples/run_menus.bat。所有动作只演示反馈，不执行真实文件操作。'),
        section('motion', '展开、执行与混排', '右键展开后，条目高亮渐变，子菜单从侧面轻移展开，关闭时淡出并立即交还鼠标与键盘。执行最终动作后收起整条菜单链；混排控件中的输入与拖动保持可用。', preview='menu-motion'),
        section('workbench-context', '工作台中的统一右键菜单', '输入框、文本区、代码编辑器与数值输入统一显示 ActionMenu。复制、粘贴、撤销及只读／密码限制由 Qt 原有动作决定，分格输入保留整段粘贴行为；动态创建的编辑器也会自动接入。', preview='workbench-context'),
        section('document-context', '导航、组件卡片与文档标签', '导航与组件卡片可右键查看示例或复制分类名称。文档标签可右键新建、切换、复制标题或关闭，右键本身不会误触关闭按钮。', preview='workbench-tab-context'),
        section('cascade', '在右键菜单中加入子菜单', 'add_menu 返回一个子 ActionMenu，继续使用现有 add_action 与 add_separator。悬停延迟展开，点击或方向右键立即展开；← 返回父级，Esc 逐级关闭。靠近右侧边缘时向左展开。', '''from fluentpy import ActionMenu, FluentIcon

actions = ActionMenu(window)
actions.add_action("打开文档", icon=FluentIcon.DOCUMENT_SAVE, callback=lambda: print("打开"))
export_menu = actions.add_menu("导出", icon=FluentIcon.ARROW_EXPORT)
export_menu.add_action("JSON 配置", callback=lambda: print("JSON"))
image_menu = export_menu.add_menu("图像格式")
image_menu.add_action("PNG 图像")
context_area = QtWidgets.QFrame(window)
context_area.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
context_area.customContextMenuRequested.connect(lambda point: actions.popup_at(context_area, point))''', 'menus-submenu', note='同一子菜单属于一个父级，不允许环形引用；QAction 可以沿用原有共享方式。'),
        section('checked', '独立勾选与互斥动作', '已有 checkable 动作继续独立开关。动作加入原生 QActionGroup 后，由 Qt 管理互斥，菜单自动使用圆点标示互斥组选中项，普通项使用勾号。', '''from fluentpy.qt import QtGui

sort_menu = ActionMenu(window)
sort_menu.add_action("显示扩展名", checkable=True, checked=True)
sort_menu.add_separator()
sort_group = QtGui.QActionGroup(sort_menu)
sort_group.setExclusive(True)
sort_group.addAction(sort_menu.add_action("按名称", checkable=True, checked=True))
sort_group.addAction(sort_menu.add_action("按修改日期", checkable=True))''', 'menus-checkable'),
        section('widgets', '动作与原生控件混排', 'add_widget 以原生 QWidgetAction 管理内容，可以放在动作与分隔线之间。输入框、滑块和按钮保留自己的交互；修改其他 QAction 时不会重建或清空控件内容。', '''from fluentpy import LineEdit, ToolTipSlider
from fluentpy.qt import QtWidgets

view_menu = ActionMenu(window)
view_settings = QtWidgets.QWidget()
view_layout = QtWidgets.QVBoxLayout(view_settings)
view_layout.addWidget(LineEdit("筛选名称"))
zoom = ToolTipSlider()
zoom.setRange(50, 150)
zoom.setValue(100)
view_layout.addWidget(zoom)
view_menu.add_widget(view_settings)
view_menu.add_separator()
view_menu.add_action("应用设置")''', 'menus-widget', note='QWidgetAction 接管传入控件。原有 set_content_widget 仍适合整个弹层只放一个内容容器；两种模式不可混用。'),
        section('context', '右键菜单与点击位置', 'popup_at 使用锚点控件内的局部坐标。应用决定哪个区域响应右键，菜单只负责定位、避让与清理。', '''context_area = QtWidgets.QFrame(window)
context_area.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
context_actions = ActionMenu(window)
context_actions.add_action("复制", shortcut="Ctrl+C")
context_actions.add_action("查看属性")
context_area.customContextMenuRequested.connect(lambda pos: context_actions.popup_at(context_area, pos))''', 'menus-context', note='快捷键文字用于展示；全局快捷键的注册与处理由应用负责。'),
        section('tray', '真正的系统托盘菜单', 'SystemTrayMenu 继承 QMenu，支持直接交给 QSystemTrayIcon。它采用系统弹出菜单行为，可在应用窗口之外显示；配色跟随 FluentPy 主题。', '''from fluentpy import SystemTrayMenu, fluent_icon

tray_actions = SystemTrayMenu(window)
tray_actions.add_action("显示窗口", callback=window.show)
tray_actions.addSeparator()
tray_actions.add_action("保持后台运行", checkable=True, checked=True)
tray = QtWidgets.QSystemTrayIcon(fluent_icon(FluentIcon.SETTINGS), window)
tray.setContextMenu(tray_actions)
# 按应用需要调用 tray.show()，此示例不自动显示托盘图标。''', 'menus-tray', note='托盘由当前桌面环境提供。关闭或切换本项目的示例页面会隐藏演示图标。'),
    ], catalogDescription='多级菜单、互斥动作、控件混排、右键与系统托盘菜单。'))
buttons_page = next(item for item in pages if item['id'] == 'buttons')
menu_section = next(item for item in buttons_page['sections'] if item['id'] == 'menu')
menu_section['note'] = 'ActionMenu 在窗口内部展开并支持多级子菜单。shortcut 参数显示快捷键提示；实际快捷键注册由应用负责。'
menu_section['links'] = [{'label':'完整菜单示例', 'page':'menus'}]
next(item for item in selection_page['sections'] if item['id'] == 'numbers')['links'] = [{'label':'完整滑块示例', 'page':'sliders'}]

pages.insert(next(i for i, item in enumerate(pages) if item['id'] == 'navigation'),
    page('fluent-window', '流畅窗口', 'Fluent window', '导航与容器',
         '从普通 Qt 主窗口逐步搭出多页工作区。按需添加导航、历史、底部设置与可扩展标题栏。',
         ['FluentWindow', 'FluentTitleBar'], [
        section('demo', '打开真实窗口，直接调整', '示例提供项目概览、可编辑说明、活动记录和底部设置，默认启用自定义标题栏和云母效果。切换侧栏、顶部导航或明暗背景时保留页面输入；标题栏搜索与窗口按钮均可直接使用。',
                'python examples/fluent_window.py', 'window-expanded',
                note='普通 FluentWindow 默认使用系统标题栏，云母默认关闭。这个示例主动开启两者，可加 --native-title-bar 恢复系统标题栏；--mode compact 或 --mode top 直接选择布局。示例设置可切换云母与配对实色背景。'),
        section('motion', '页面与布局的真实切换', '在同一个 Qt 窗口中编辑说明、切换页面、返回历史，再调整导航布局。页面沿用既有动画栈，输入内容继续保留。', preview='window-motion'),
        section('basic', '从现有内容布局开始', 'FluentWindow 继承 QMainWindow。未注册页面时保持普通窗口；第一次调用 add_page 或 navigation_view 才加入导航容器，原先放进 content_layout 的控件继续保留。', '''from fluentpy import FluentWindow, LineEdit
from fluentpy.qt import QtWidgets

window = FluentWindow("项目工作区")
window.content_layout.setContentsMargins(0, 0, 0, 0)
project_name = LineEdit("项目名称")
window.content_layout.addWidget(project_name)

overview = QtWidgets.QWidget()
QtWidgets.QVBoxLayout(overview).addWidget(QtWidgets.QLabel("项目概览"))
window.add_page(overview, "概览", route="overview", position="header")

document = QtWidgets.QWidget()
document_layout = QtWidgets.QVBoxLayout(document)
editor = QtWidgets.QPlainTextEdit()
document_layout.addWidget(editor)
window.add_page(document, "项目说明", route="documents", position="scroll")'''),
        section('layout', '同一组页面，不同导航布局', 'auto 在宽窗口展开侧栏、窄窗口收起为图标栏；expanded 与 compact 固定选择一种侧栏。页面与输入内容始终由同一批 Qt 控件承载，布局切换不会重建编辑器。', '''window.set_navigation_mode("auto")
window.set_navigation_width(224)
window.set_navigation_breakpoint(880)
# 也可改为 "expanded" 或 "compact"。
print(window.navigation_mode())''', 'window-compact',
                note='默认断点为 880 逻辑像素。侧栏宽度至少 120，自动布局断点至少 320。'),
        section('top', '页面上方的导航入口', 'top 隐藏侧栏，复用现有 Pivot 组织路由。入口多于窗口可用宽度时横向滚动；切换侧栏或顶部入口会同步同一个当前页面与历史。',
                'window.set_navigation_mode("top")', 'window-top'),
        section('settings', '把设置放在底部', '底部设置是应用自己的普通页面。可直接组合已有复选框、下拉框与按钮；窗口不替应用生成设置项，也不自动保存业务数据。顶部固定、中间滚动与底部固定区域沿用现有 NavigationSidebar。', '''from fluentpy import CheckBox, FluentIcon, fluent_icon

settings = QtWidgets.QWidget()
settings_layout = QtWidgets.QVBoxLayout(settings)
dark_mode = CheckBox("深色主题")
dark_mode.toggled.connect(window.set_dark)
settings_layout.addWidget(dark_mode)
settings_layout.addStretch()
window.add_page(settings, "设置", fluent_icon(FluentIcon.SETTINGS),
                route="settings", position="bottom")''', 'window-settings',
                note='需要持久化时由应用使用 QSettings 等存储。可继续通过 navigation_view().sidebar.set_header_widget(...)／set_footer_widget(...) 放入自己的原生 Qt 控件。'),
        section('history', '共享路由与页面历史', '侧栏、顶部入口与程序化切换共用历史。前进、后退跳过不可见或已移除页面；返回后进入新页面会清除旧的前进分支。', '''window.switch_to("documents")
window.switch_to(overview, animated=False)
if window.can_go_back():
    window.go_back()
if window.can_go_forward():
    window.go_forward()

window.currentChanged.connect(lambda route: print("当前路由", route))
window.historyChanged.connect(lambda: print("可以返回", window.can_go_back()))
print(window.current_route(), window.current_page())''',
                note='switch_to 接受路由或已注册的 QWidget，未知或不可见路由返回 False。remove_page(route, delete=False) 移除页面；delete=True 同时释放。隐藏入口使用 navigation_view().set_route_visible(route, False)。'),
        section('titlebar', '一行式标题栏', '显式启用后创建默认 48 像素高的 FluentTitleBar，返回、图标、标题与窗口操作在同一行；背景、文字与操作符号同步切换主题。标题栏与导航侧栏共用外壳表面，默认配色与主内容保持分层。窗口按钮用 Qt 绘制为 Windows 风格细线符号，关闭按钮悬停为红底白色 X，操作由实际窗口执行。搜索、标签与额外按钮仍是普通控件。', '''from fluentpy import SearchLineEdit, Button

window.set_title_bar_enabled(True)
title_bar = window.title_bar()
title_bar.set_bar_height(48)
search = SearchLineEdit("搜索项目")
search.setFixedWidth(220)
title_bar.content_layout.addWidget(search)
title_bar.button_layout.addWidget(Button("帮助"))
title_bar.set_double_click_enabled(True)
title_bar.set_caption_buttons_visible(minimize=True, maximize=True, close=True)''', 'window-titlebar',
                note='Windows 保留系统边框能力，圆角与阴影由 DWM 处理；最大化／全屏关闭外层圆角与边线，还原后恢复。最大化使用工作区，全屏才覆盖任务栏区域。导航内容保留 10px 左上圆角，只裁剪子页面容器；侧栏状态和输入保留。标题栏按钮是 Qt 绘制的 Windows 风格按钮，可通过 uses_native_caption_buttons() 区分系统绘制的按钮。搜索框保留自身输入；关闭自定义模式会恢复系统标题栏。'),
        section('background', '配对背景与原生云母', 'set_background_colors 分别指定浅色与深色的不透明背景，也用于外壳的实色回退；clear_background_colors 恢复标题栏与侧栏同色、主内容分层的默认配色。普通 FluentWindow 的云母默认关闭，可显式开启。工作台与独立窗口示例默认开启，工作台“设置 → 外观”提供持久化开关。', '''window.set_background_colors("#edf4fa", "#162231")
window.clear_background_colors()
window.set_backdrop_enabled(True)
window.show()
print(window.is_backdrop_enabled(), window.backdrop_applied())
window.backdropChanged.connect(lambda applied: print("实际材质状态", applied))''', preview='window-mica',
                paragraphs=['云母需要 Windows 11 build 22621 或更新版本，且 DWM 合成与系统透明效果可用；高对比度、平台不支持或原生调用失败时回退普通 Qt 背景。材质由系统根据壁纸与主题合成，初次开启会由系统逐渐呈现；失焦或部分系统策略下可能显示中性色，不是实时模糊后方应用。下图为独立测试窗口的真实 Windows 合成截图，色调会随壁纸和系统状态变化。',
                            '原生材质应用后，标题栏、导航侧栏等外壳表面露出云母。FluentWindow.add_page 的导航内容区默认铺设独立的不透明主题背景，普通页面无需自行填充。直接使用 content_layout 时，无背景的自定义布局仍可露出材质；需要实色内容面时，可用普通 QWidget 承载布局，调用 page.setAutoFillBackground(True)，并使用主题的 QPalette.Window 背景。自定义绘制与样式由应用负责。'],
                note='is_backdrop_enabled 读取请求偏好。backdrop_applied 表示原生调用成功且 Qt 外壳已露出材质，实际状态改变时发出 backdropChanged(bool)；它不保证每时每刻都有明显的壁纸色调。窗口显示前或回退时实际状态可为 False，请求偏好仍保留。set_dark 继续作用于 FluentPy 全局主题。'),
        section('reference', '独立实现', '仅参考公开的窗口组织与交互分类，独立复用 FluentPy 的 NavigationView、Pivot、现有按钮和原生 Qt 布局；没有引入参考项目的代码、截图、样式或示例文案。',
                links=[{'label':'公开交互参考', 'href':'https://qfluentwidgets.com/zh/pages/components/fluentwindow/'},
                       {'label':'导航容器与侧栏', 'page':'navigation'}]),
    ], catalogDescription='多页窗口、响应式导航、页面历史、底部设置与可扩展标题栏。'))

pages.insert(next(i for i, item in enumerate(pages) if item['id'] == 'fluent-window') + 1,
    page('splash-screen', '启动页面', 'Splash screen', '导航与容器',
         '用居中的应用图标覆盖尚未就绪的内容，初始化完成后平滑显示原有界面。沿用窗口标题栏，支持局部或全窗口预览。',
         ['SplashScreen'], [
        section('demo', '工作台启动与手动重播', '工作台每次启动都先显示启动页，第一帧绘制后再检查后端并逐页创建界面，全部就绪后立即渐隐，没有固定等待或虚构进度。顶部只保留三个窗口操作，关闭会取消剩余初始化，失败显示实际错误。“页面导航 → 启动页面”提供大小、可选提示与手动重播；仅手动重播和独立组件示例使用演示计时。',
                'python examples/splash_screen.py', 'splash-demo'),
        section('basic', '先显示图标，再完成初始化', 'SplashScreen 必须有 QWidget 父控件，构造时隐藏，调用 show 显示。全窗口启动时，FluentTitleBar 只保留最小化、最大化／还原和关闭按钮，标题、图标、历史及自定义操作临时隐藏；结束后恢复。局部预览不改变外层标题栏，普通 Qt 宿主的系统标题栏仍由系统管理。', '''from fluentpy import SplashScreen
from importlib import resources
from fluentpy.qt import QtGui

window.set_title_bar_enabled(True)
icon = QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
splash = SplashScreen(icon, window)
splash.set_icon_size(102)
splash.show()
window.show()''', 'splash-screen',
                note='耗时初始化交给工作线程，Qt 控件仍在 GUI 线程创建；任务的完成信号连接 splash.finish。组件不运行嵌套事件循环，也不替应用执行初始化任务。'),
        section('loading', '可选加载环与提示', '默认只有图标。可以显示加载环并填写自己的提示，文本和背景跟随明暗主题。', '''splash.set_loading(True)
splash.set_text("正在准备界面…")
print(splash.icon_size(), splash.is_loading(), splash.text())''', 'splash-loading'),
        section('finish', '完成后渐隐', 'finish 默认以 220ms 渐隐，结束时发出一次 finished。输入遮罩与加载动画随退场清理，底层控件和输入值保留；可再次 show 重播。', '''splash.finished.connect(lambda: print("启动完成"))
splash.finish()
# 也可使用 splash.finish(animated=False) 立即结束。''', 'splash-motion',
                note='重复 finish 不重启动画；父控件隐藏时停止动画和输入过滤，销毁时按 Qt 所有权释放。局部预览可用 Tab 到覆盖范围外的配置控件。'),
        section('background', '明暗背景与尺寸', '图标接受 QIcon、QPixmap、FluentIcon 或文件路径；尺寸接受正整数或 QSize，在窄容器内自动缩小。背景必须是不透明的有效颜色。', '''from fluentpy.qt import QtCore
splash.set_icon_size(QtCore.QSize(96, 96))
splash.set_background_colors("#f4f7fb", "#202530")
splash.clear_background_colors()'''),
        section('reference', '独立实现', '只参考公开启动页面的布局与使用思路，使用已有 FluentPy 图标、Qt 绘制和动画独立实现；未复制外部源码、样式、图片或示例文案。',
                links=[{'label':'公开交互参考', 'href':'https://qfluentwidgets.com/zh/pages/components/splashscreen/'},
                       {'label':'流畅窗口', 'page':'fluent-window'}]),
    ], catalogDescription='居中图标、可选加载提示与完成渐隐，保留现有标题栏。'))

pages.append(page('tables', '表格', 'Tables', '数据与文件',
    '保留 Qt 项目与模型接口，统一普通、圆角和细线三种行样式。支持排序、编辑、多选复制及现有高级右键菜单。',
    ['TableView', 'TableWidget', 'TableItemDelegate'], [
    section('demo', '边改边试', '工作台侧栏“表格”提供实时搜索、接口切换、添加、删除与复制。外观和交互设置收在一个可展开区域；切换样式不重建数据，两种接口各自保留编辑内容。',
            'python examples/tables.py', 'tables-demo'),
    section('items', '项目接口', 'TableWidget 继承 QTableWidget，适合直接管理项目的界面。数值使用整数或浮点数的 DisplayRole，Qt 才会按数值排序。', '''from fluentpy import TableWidget
from fluentpy.qt import QtCore, QtWidgets

table = TableWidget(1, 2, window)
table.setHorizontalHeaderLabels(["名称", "数量"])
table.setItem(0, 0, QtWidgets.QTableWidgetItem("图标资源"))
quantity = QtWidgets.QTableWidgetItem()
quantity.setData(QtCore.Qt.ItemDataRole.DisplayRole, 12)
table.setItem(0, 1, quantity)
table.setSortingEnabled(True)
window.content_layout.addWidget(table)''', 'tables-standard',
            note='也支持 TableWidget(parent)。模型与项目 API 沿用 Qt；默认双击或 F2 编辑，Ctrl / Shift 多选。'),
    section('model', '模型接口与搜索', 'TableView 继承 QTableView，连接已有模型，不复制一份业务数据。排序与筛选复用 Qt 的 QSortFilterProxyModel。', '''from fluentpy import TableView, SearchLineEdit
from fluentpy.qt import QtCore, QtGui

source = QtGui.QStandardItemModel(0, 2, window)
source.setHorizontalHeaderLabels(["名称", "分类"])
source.appendRow([QtGui.QStandardItem("主题色板"), QtGui.QStandardItem("界面")])
source.appendRow([QtGui.QStandardItem("使用说明"), QtGui.QStandardItem("文档")])
proxy = QtCore.QSortFilterProxyModel(window)
proxy.setSourceModel(source)
proxy.setFilterKeyColumn(-1)
proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
view = TableView(window)
view.setModel(proxy)
view.setSortingEnabled(True)
search = SearchLineEdit("搜索全部列")
search.textChanged.connect(proxy.setFilterFixedString)
window.content_layout.addWidget(search)
window.content_layout.addWidget(view)''', 'tables-motion',
            note='模型生命周期由调用方管理，建议设置 Qt 父控件。只绘制可见单元，不为每格创建 QWidget；大量数据优先使用模型接口。'),
    section('appearance', '行样式与密度', '三个样式共用一套组件配置。悬停与选择使用共用的 120ms 状态动画，隐藏或重置模型后清理状态；内部圆角裁剪不会给原生窗口设置区域。', '''table.set_row_style("rounded")  # standard / rounded / line
table.set_row_height(44)        # 至少 24
table.setAlternatingRowColors(True)
table.set_border_visible(True)
table.set_border_radius(8)
table.verticalHeader().setVisible(False)
table.set_select_right_clicked_row(True)''', 'tables-rounded',
            paragraphs=['默认按行多选，可继续使用 Qt 的 selectionMode、selectionBehavior 和表头接口。右键已选区域保留多选；未选中的可用条目按设置选中。模型的可用、可选标记继续生效。']),
    section('lines', '细线行与空状态', '细线行保留轻分隔，空模型显示可自定义的提示。工作台搜索不会删除原始数据。', '''table.set_row_style("line")
table.set_empty_text("暂无记录")''', 'tables-line'),
    section('editing', '编辑与自定义代理', '字符串、整数和浮点数复用已有 LineEdit、SpinBox、DoubleSpinBox；其余类型沿用 Qt 编辑器工厂。Enter 提交、Esc 取消。保留模型的字体、前景、背景、图标和勾选角色。', '''from fluentpy import TableItemDelegate

class ProjectDelegate(TableItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        # 按业务列设置范围、精度、验证器或自己的编辑器。
        return editor

table.setItemDelegate(ProjectDelegate(table))''', 'tables-edit',
            note='setEditTriggers(NoEditTriggers) 禁止打开编辑器；勾选项仍由 ItemIsUserCheckable 和 ItemIsEnabled 标记管理。浮点编辑器保留原值精度和数量级，非有限值或超过 Qt 323 位小数范围的值不打开默认编辑器。业务范围与校验由应用代理指定。'),
    section('copy', '多选复制与右键', 'Ctrl+C 输出 TSV，按可见行列顺序保留稀疏选区空位，引用单元中的 Tab、换行和引号，排除隐藏行列。没有选择时不改剪贴板。', '''text = table.selection_text(include_headers=True)
copied = table.copy_selection(include_headers=True)''', 'tables-context',
            paragraphs=['右键复用已有 ActionMenu，提供复制、含表头复制、编辑与全选。createStandardContextMenu() 只构造 QAction 容器，供工作台现有适配器使用，不会再弹出一套系统菜单。']),
    section('reference', '独立实现', '只参考公开表格的布局与交互分类，使用 Qt 模型视图、FluentPy 主题、编辑控件和菜单独立实现。没有引入外部源码、样式、图片或示例数据。',
            links=[{'label':'公开交互参考', 'href':'https://qfluentwidgets.com/zh/pages/components/tableview/'},
                   {'label':'高级右键菜单', 'page':'menus'}]),
], catalogDescription='原生 Qt 项目／模型接口、三种行样式、排序搜索、编辑与多选复制。'))

groups = [
    {"name": "开始使用", "pages": ["introduction", "getting-started", "components", "faq"]},
    {"name": "基础控件", "pages": ["buttons", "inputs", "selection", "combo-boxes", "sliders", "colors", "shortcut-picker"]},
    {"name": "日期与时间", "pages": ["date-picker", "time-picker", "calendar-picker"]},
    {"name": "导航与容器", "pages": ["fluent-window", "splash-screen", "menus", "navigation", "navigation-controls", "cards"]},
    {"name": "消息与反馈", "pages": ["dialogs", "feedback"]},
    {"name": "数据与文件", "pages": ["tables", "drag-drop", "code-editor", "note-timeline"]},
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
data = {"pages": pages, "groups": groups, "api": api, "icons": icons, "sourceDate": "2026-10-19", "version": VERSION, "previewVersion": preview_version, "animatedPreviews": ANIMATED_PREVIEWS}
(SITE / "dist" / "data.js").write_text("window.DOCS_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8", newline="\n")
index_path = SITE / "dist" / "index.html"
index = index_path.read_text(encoding="utf-8")
index = re.sub(r'(<span class="version">)[^<]+', lambda match: match[1] + VERSION, index)
site_assets = ("data.js", "native-flow.js", "migration.js", "app.js", "styles.css", "native-flow.css", "migration.css", "workbench-home.css")
asset_version = hashlib.sha256(b"".join((SITE / "dist" / name).read_bytes() for name in site_assets)).hexdigest()[:10]
index = re.sub(r'src="(data|native-flow|migration|app)\.js(?:\?v=[a-z0-9]+)?"', lambda m: f'src="{m.group(1)}.js?v={asset_version}"', index)
index = re.sub(r'href="(styles|native-flow|migration|workbench-home)\.css(?:\?v=[a-z0-9]+)?"', lambda m: f'href="{m.group(1)}.css?v={asset_version}"', index)
index_path.write_text(index, encoding="utf-8", newline="\n")
destination = SITE / "dist" / "assets" / "icons"
destination.mkdir(exist_ok=True, parents=True)
for path in (SRC / "assets" / "icons").glob("*.svg"):
    shutil.copy2(path, destination / path.name)
shutil.copy2(ROOT / "licenses" / "Microsoft-Fluent-System-Icons-LICENSE.txt", SITE / "dist" / "assets" / "icons-LICENSE.txt")
shutil.copy2(ROOT / "LICENSE", SITE / "dist" / "assets" / "FluentPy-LICENSE.txt")
shutil.copy2(SRC / "assets" / "brand" / "fluentpy.svg", SITE / "dist" / "assets" / "mark.svg")
print(f"Built {len(pages)} pages, {len(api)} public API entries and {len(icons)} icons from FluentPy source.")
