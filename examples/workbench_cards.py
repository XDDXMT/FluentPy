"""Neutral, functional card samples used by the component reference application."""

from importlib import resources

from cards import FluentPicture
from expandable_cards import ExpandableSettings

from fluentpy import (
    Button,
    CardWidget,
    ComboBox,
    ElevatedCardWidget,
    FluentIcon,
    GroupHeaderCardWidget,
    HeaderCardWidget,
    LineEdit,
    SimpleCardWidget,
    ToggleSwitch,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets


class WorkbenchCards(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workbenchCards")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        basic = HeaderCardWidget("基础卡片")
        basic.body_layout.addWidget(QtWidgets.QLabel("CardWidget / SimpleCardWidget"))
        self.result = QtWidgets.QLabel("未执行操作")
        brand = QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
        for cls, title, description, icon in (
            (CardWidget, "FluentPy", "MIT License", brand),
            (SimpleCardWidget, "示例项目", "标准内容容器", FluentIcon.BUILDING_BANK),
        ):
            card = cls()
            card.setFixedHeight(72)
            row = QtWidgets.QHBoxLayout(card)
            row.setContentsMargins(16, 10, 16, 10)
            row.setSpacing(16)
            picture = FluentPicture(
                icon, 36, preserve_colors=isinstance(icon, QtGui.QIcon), parent=card
            )
            row.addWidget(picture)
            text = QtWidgets.QVBoxLayout()
            text.setSpacing(3)
            name = QtWidgets.QLabel(title)
            name.setObjectName("smallTitle")
            text.addWidget(name)
            detail = QtWidgets.QLabel(description)
            detail.setObjectName("muted")
            text.addWidget(detail)
            row.addLayout(text, 1)
            button = Button("查看")
            button.setFixedWidth(80)
            button.clicked.connect(
                lambda _checked=False, value=title: self.result.setText("已点击：" + value)
            )
            row.addWidget(button)
            basic.body_layout.addWidget(card)
        basic.body_layout.addWidget(self.result)
        root.addWidget(basic)
        raised = HeaderCardWidget("悬浮卡片")
        raised.body_layout.addWidget(QtWidgets.QLabel("ElevatedCardWidget · 悬停时显示轻阴影"))
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        for title, icon in (
            ("文档", FluentIcon.DOCUMENT),
            ("文件夹", FluentIcon.FOLDER),
            ("代码", FluentIcon.CODE),
        ):
            tile = ElevatedCardWidget()
            tile.setFixedSize(152, 112)
            box = QtWidgets.QVBoxLayout(tile)
            box.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            box.setSpacing(12)
            image = FluentPicture(icon, 30, parent=tile)
            name = QtWidgets.QLabel(title)
            name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            box.addWidget(image, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
            box.addWidget(name)
            row.addWidget(tile)
        row.addStretch()
        raised.body_layout.addLayout(row)
        root.addWidget(raised)
        self.settings = GroupHeaderCardWidget("分组设置")
        self.notifications = ToggleSwitch()
        self.notifications.setChecked(True)
        self.appearance = ComboBox()
        self.appearance.addItems(["跟随系统", "浅色", "深色"])
        self.appearance.setFixedWidth(180)
        self.directory = LineEdit("输入目录")
        self.directory.setText("./cache")
        self.directory.setFixedWidth(180)
        self.settings.add_group(
            FluentIcon.ALERT, "通知开关", "切换当前示例的状态", self.notifications
        )
        self.settings.add_group(FluentIcon.SETTINGS, "显示模式", "下拉选择示例", self.appearance)
        self.settings.add_group(FluentIcon.FOLDER, "缓存目录", "文本输入示例", self.directory)
        root.addWidget(self.settings)
        expandable = HeaderCardWidget("折叠设置")
        hint = QtWidgets.QLabel("点击标题展开或收起；卡片内的设置会保留。")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        expandable.body_layout.addWidget(hint)
        self.expandable_settings = ExpandableSettings()
        self.expandable_settings.setMaximumWidth(350)
        expandable.body_layout.addWidget(self.expandable_settings)
        root.addWidget(expandable)
        theme.subscribe(self, self._apply_theme)
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(
            f"QWidget#workbenchCards QLabel {{color:{theme.tokens.text};background:transparent;}}"
            f"QWidget#workbenchCards QLabel#smallTitle {{font-size:14px;font-weight:600;}}"
            f"QWidget#workbenchCards QLabel#muted {{font-size:12px;color:{theme.tokens.text_muted};}}"
        )
