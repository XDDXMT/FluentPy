"""Workbench preferences composed exclusively from existing library controls."""
from __future__ import annotations

from pathlib import Path
import sys

from fluentpy import (
    Button, ComboBox, ExpandableCardWidget, FluentIcon, GroupHeaderCardWidget,
    HyperlinkButton, Slider, TextEdit, ToggleSwitch, __version__, theme,
)
from fluentpy.qt import QtCore, QtWidgets, QT_API, Signal


DEFAULT_PREFERENCES = {
    "theme": "light", "accent": "default", "sidebar_width": 216,
    "sidebar_expanded": True, "page_animation": True, "show_backend": True,
    "mica_enabled": True,
}
ACCENTS = {
    "default": ("默认青色", None, None),
    "blue": ("蓝色", "#0078d4", "#60cdff"),
    "purple": ("紫色", "#744da9", "#c6a7f2"),
    "green": ("绿色", "#107c10", "#6ccb5f"),
}
AUTHOR_NAME = "性邓的小馒头"
AUTHOR_PROFILE = "https://github.com/XDDXMT"
DOCUMENTATION_URL = "https://fluentpy.mcxmcl.cn/"
REPOSITORY_URL = "https://github.com/XDDXMT/FluentPy"
ISSUES_URL = REPOSITORY_URL + "/issues"


def _local_declarations() -> str:
    """Read repository notices as text, without opening an external program."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    documents = []
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        path = root / name
        try:
            content = path.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            content = "本地声明文件暂不可用，请在项目仓库查看此文件。"
        documents.append(name + "\n" + "─" * 24 + "\n" + content)
    return "\n\n".join(documents)


def load_preferences(store: QtCore.QSettings | None) -> dict:
    result = dict(DEFAULT_PREFERENCES)
    if store is None:
        return result
    for key, default in result.items():
        value = store.value("workbench/" + key, default)
        if isinstance(default, bool):
            if isinstance(value, bool):
                result[key] = value
            elif isinstance(value, str) and value.lower() in ("true", "false"):
                result[key] = value.lower() == "true"
        elif key == "sidebar_width":
            try:
                width = int(value)
                if not isinstance(value, bool) and 180 <= width <= 280:
                    result[key] = width
            except (ValueError, TypeError, OverflowError):
                pass
        elif key == "theme" and value in ("light", "dark"):
            result[key] = value
        elif key == "accent" and isinstance(value, str) and value in ACCENTS:
            result[key] = value
    return result


def accent_color(preferences: dict):
    return ACCENTS[preferences["accent"]][2 if preferences["theme"] == "dark" else 1]


class WorkbenchSettings(QtWidgets.QWidget):
    """A form of public FluentPy controls; the owning workbench applies changes."""
    preferenceChanged = Signal(str, object)
    resetRequested = Signal()

    def __init__(self, preferences: dict, parent=None):
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        appearance = GroupHeaderCardWidget("外观", self)
        self.theme_choice = ComboBox()
        self.theme_choice.addItems(["浅色", "深色"])
        self.theme_choice.setFixedWidth(160)
        self.theme_choice.setAccessibleName("工作台主题")
        self.accent_choice = ComboBox()
        self.accent_choice.addItems([item[0] for item in ACCENTS.values()])
        self.accent_choice.setFixedWidth(160)
        self.accent_choice.setAccessibleName("工作台强调色")
        appearance.add_group(FluentIcon.DESKTOP, "主题", "与窗口右上方的主题开关保持同步", self.theme_choice)
        appearance.add_group(FluentIcon.COLOR, "强调色", "用于按钮、选中标记与滑块", self.accent_choice)
        self.mica_toggle = ToggleSwitch()
        self.mica_toggle.setAccessibleName("云母效果（Windows 11）")
        appearance.add_group(FluentIcon.DESKTOP, "云母效果（Windows 11）",
                             "让标题栏与导航使用系统材质；不支持时使用普通背景", self.mica_toggle)
        root.addWidget(appearance)

        navigation = GroupHeaderCardWidget("导航", self)
        self.expanded_toggle = ToggleSwitch()
        self.expanded_toggle.setAccessibleName("展开导航栏")
        navigation.add_group(FluentIcon.NAVIGATION, "展开导航栏", "关闭后只显示图标，底部设置入口仍可使用", self.expanded_toggle)
        width_control = QtWidgets.QWidget()
        width_control.setFixedWidth(210)
        width_layout = QtWidgets.QHBoxLayout(width_control)
        width_layout.setContentsMargins(0, 0, 0, 0)
        width_layout.setSpacing(8)
        self.width_slider = Slider()
        self.width_slider.setRange(180, 280)
        self.width_slider.setAccessibleName("导航栏展开宽度")
        self.width_value = QtWidgets.QLabel()
        self.width_value.setFixedWidth(30)
        width_layout.addWidget(self.width_slider, 1)
        width_layout.addWidget(self.width_value)
        navigation.add_group(FluentIcon.LAYOUT_ROW_THREE, "展开宽度", "调整导航栏展开后的宽度", width_control)
        root.addWidget(navigation)

        behavior = GroupHeaderCardWidget("交互与状态", self)
        self.animation_toggle = ToggleSwitch()
        self.animation_toggle.setAccessibleName("页面切换动画")
        self.backend_toggle = ToggleSwitch()
        self.backend_toggle.setAccessibleName("显示后端状态")
        behavior.add_group(FluentIcon.ARROW_SWAP, "页面切换动画", "在组件页面之间使用淡入与位移动画", self.animation_toggle)
        behavior.add_group(FluentIcon.INFO, "显示后端状态", "在窗口底栏显示当前使用的 C 或 Python 后端", self.backend_toggle)
        root.addWidget(behavior)

        footer = QtWidgets.QHBoxLayout()
        self.reset_button = Button("恢复默认设置")
        self.reset_button.clicked.connect(lambda _checked=False: self.resetRequested.emit())
        self.result = QtWidgets.QLabel("修改立即生效，并自动保存在本机。")
        self.result.setWordWrap(True)
        footer.addWidget(self.reset_button)
        footer.addWidget(self.result, 1)
        root.addLayout(footer)

        self.about_card = GroupHeaderCardWidget("关于 FluentPy", self)
        self.documentation_link = HyperlinkButton("官网与文档", url=DOCUMENTATION_URL)
        self.version_row = self.about_card.add_group(
            FluentIcon.INFO, "FluentPy " + __version__,
            f"{QT_API} · Qt {QtCore.qVersion()}", self.documentation_link)
        self.author_link = HyperlinkButton("GitHub 主页", url=AUTHOR_PROFILE)
        self.author_row = self.about_card.add_group(
            FluentIcon.CONTACT_CARD, AUTHOR_NAME, "项目作者 · GitHub：XDDXMT", self.author_link)
        project_links = QtWidgets.QWidget()
        links_layout = QtWidgets.QHBoxLayout(project_links)
        links_layout.setContentsMargins(0, 0, 0, 0)
        links_layout.setSpacing(8)
        self.repository_link = HyperlinkButton("项目仓库", url=REPOSITORY_URL)
        self.issues_link = HyperlinkButton("问题反馈", url=ISSUES_URL)
        links_layout.addWidget(self.repository_link)
        links_layout.addWidget(self.issues_link)
        self.project_row = self.about_card.add_group(
            FluentIcon.CODE, "源码与反馈", "代码与文档公开，问题可通过项目仓库反馈。", project_links)
        root.addWidget(self.about_card)

        self.declarations_card = ExpandableCardWidget("许可与第三方声明", self)
        self.declaration_summary = QtWidgets.QLabel(
            "FluentPy 使用 MIT 许可证。发行时须保留版权声明与许可证文本。"
            "组件独立实现；Qt、图标等第三方依赖和资源遵循各自许可证。")
        self.declaration_summary.setWordWrap(True)
        self.declaration_summary.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.declaration_summary.setMinimumWidth(0)
        self.declarations_card.body_layout.addWidget(self.declaration_summary)
        self.declarations_view = TextEdit()
        self.declarations_view.setAccessibleName("本地 MIT 许可证与第三方声明")
        self.declarations_view.setReadOnly(True)
        self.declarations_view.setAcceptRichText(False)
        self.declarations_view.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
        self.declarations_view.setMinimumWidth(0)
        self.declarations_view.setFixedHeight(240)
        self.declarations_view.setPlainText(_local_declarations())
        self.declarations_card.body_layout.addWidget(self.declarations_view)
        root.addWidget(self.declarations_card)

        self.set_preferences(preferences)
        self.theme_choice.currentIndexChanged.connect(lambda index: self.preferenceChanged.emit("theme", "dark" if index else "light"))
        self.accent_choice.currentIndexChanged.connect(lambda index: self.preferenceChanged.emit("accent", tuple(ACCENTS)[index]))
        self.width_slider.valueChanged.connect(lambda width: self.preferenceChanged.emit("sidebar_width", width))
        for key, control in (("sidebar_expanded", self.expanded_toggle), ("page_animation", self.animation_toggle),
                             ("show_backend", self.backend_toggle), ("mica_enabled", self.mica_toggle)):
            control.toggled.connect(lambda checked, name=key: self.preferenceChanged.emit(name, checked))
        theme.subscribe(self, self._refresh_theme)
        self._refresh_theme()

    def set_preferences(self, preferences: dict):
        for control, value, setter in (
            (self.theme_choice, int(preferences["theme"] == "dark"), "setCurrentIndex"),
            (self.accent_choice, tuple(ACCENTS).index(preferences["accent"]), "setCurrentIndex"),
            (self.width_slider, preferences["sidebar_width"], "setValue"),
            (self.expanded_toggle, preferences["sidebar_expanded"], "setChecked"),
            (self.animation_toggle, preferences["page_animation"], "setChecked"),
            (self.backend_toggle, preferences["show_backend"], "setChecked"),
            (self.mica_toggle, preferences["mica_enabled"], "setChecked"),
        ):
            with QtCore.QSignalBlocker(control):
                getattr(control, setter)(value)
        self.width_value.setText(str(preferences["sidebar_width"]))

    def _refresh_theme(self):
        self.width_value.setStyleSheet(f"color: {theme.tokens.text_muted}; background: transparent;")
        self.result.setStyleSheet(f"color: {theme.tokens.text_muted}; background: transparent;")
        # The shared link control's compact size hint leaves too little room
        # for its icon and text. Reserve the actual rendered font width here
        # without changing the library control or padding the visible label.
        for link in (self.documentation_link, self.author_link, self.repository_link, self.issues_link):
            icon, gap, side_padding, allowance = 14, 8, 20, 6
            link.setFixedWidth(link.fontMetrics().horizontalAdvance(link.text())
                               + icon + gap + side_padding + allowance)
