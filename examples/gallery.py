from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fluentpy import (  # noqa: E402
    AccentButton,
    Button,
    BreadcrumbBar,
    Card,
    CheckBox,
    ComboBox,
    DoubleSpinBox,
    EditableComboBox,
    ExamplePanel,
    FramelessDialog,
    FluentIcon,
    FluentScrollBar,
    FluentWindow,
    HyperlinkButton,
    IconButton,
    LineEdit,
    MaskedDialog,
    NavigationView,
    NoteEvent,
    NoteTimeline,
    OutlinedButton,
    PasswordLineEdit,
    Pivot,
    ProgressBar,
    RadioButton,
    RoundAccentButton,
    RoundButton,
    SegmentedToolWidget,
    SegmentedWidget,
    SearchLineEdit,
    Slider,
    SpinBox,
    TabBar,
    TextButton,
    TextEdit,
    Toast,
    ToggleSwitch,
    fluent_icon,
    fluent_icon_name,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets  # noqa: E402


class HeroBanner(Card):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(180)
        self.setMaximumHeight(210)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 26, 32, 26)
        layout.setSpacing(8)

        layout.addStretch(1)
        layout.addStretch(1)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self._apply_card_theme()
        self.setStyleSheet(
            """
QFrame#fluentCard {
    background: transparent;
    border: none;
    border-radius: 5px;
}
"""
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)

        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QtGui.QColor(20, 26, 41))
        gradient.setColorAt(0.55, QtGui.QColor(35, 43, 70))
        gradient.setColorAt(1.0, QtGui.QColor(29, 36, 56))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 5, 5)

        wave = QtGui.QPainterPath()
        wave.moveTo(rect.left() + rect.width() * 0.24, rect.bottom())
        wave.cubicTo(
            rect.left() + rect.width() * 0.46,
            rect.top() + rect.height() * 0.22,
            rect.left() + rect.width() * 0.68,
            rect.top() + rect.height() * 0.18,
            rect.right(),
            rect.top() + rect.height() * 0.44,
        )
        wave.lineTo(rect.right(), rect.bottom())
        wave.closeSubpath()
        wave_gradient = QtGui.QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        wave_gradient.setColorAt(0.0, QtGui.QColor(0, 176, 213, 150))
        wave_gradient.setColorAt(0.55, QtGui.QColor(126, 58, 242, 180))
        wave_gradient.setColorAt(1.0, QtGui.QColor(255, 82, 218, 120))
        painter.setBrush(wave_gradient)
        painter.drawPath(wave)

        glow = QtGui.QColor(255, 255, 255, 26)
        painter.setPen(QtGui.QPen(glow, 2))
        painter.drawPath(wave)

        title_font = QtGui.QFont("Segoe UI Variable Display")
        title_font.setPointSize(28)
        title_font.setBold(True)
        subtitle_font = QtGui.QFont("Microsoft YaHei UI")
        subtitle_font.setPointSize(10)

        text_left = rect.left() + 32
        title_rect = QtCore.QRectF(text_left, rect.top() + 58, rect.width() * 0.58, 48)
        subtitle_rect = QtCore.QRectF(text_left, title_rect.bottom() + 8, rect.width() * 0.66, 24)
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.setFont(title_font)
        painter.drawText(title_rect, QtCore.Qt.AlignmentFlag.AlignVCenter, "FluentPy")
        painter.setPen(QtGui.QColor(255, 255, 255, 216))
        painter.setFont(subtitle_font)
        painter.drawText(
            subtitle_rect,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
            "面向 Qt for Python 的 Fluent 风格组件库",
        )


class FlatSurface(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("flatSurface")
        theme.changed.connect(lambda _tokens: self._apply_theme())
        self._apply_theme()

    def _apply_theme(self) -> None:
        if theme.tokens.mode.value == "light":
            bg = "#ffffff"
            border = "#e5e5e5"
        else:
            bg = "#2b2b2b"
            border = "#1d1d1d"
        self.setStyleSheet(
            f"""
QFrame#flatSurface {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 8px;
}}
"""
        )


class HomeHero(FlatSurface):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(188)
        self.setMaximumHeight(220)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("FluentPy 组件库")
        title_font = QtGui.QFont("Microsoft YaHei UI")
        title_font.setPointSize(31)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setObjectName("homeHeroTitle")

        subtitle = QtWidgets.QLabel("把 Fluent 风格控件带到 Qt for Python，保留迁移友好的 API，也保留一点手感。")
        subtitle.setObjectName("homeHeroSubtitle")
        subtitle.setWordWrap(True)

        actions = QtWidgets.QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 0)
        actions.setSpacing(10)
        start = AccentButton("查看基础输入")
        start.setObjectName("homeStartButton")
        start.setIcon(fluent_icon(FluentIcon.CHECKBOX_CHECKED))
        docs = Button("浏览导航控件")
        docs.setObjectName("homeNavButton")
        docs.setIcon(fluent_icon(FluentIcon.NAVIGATION))
        actions.addWidget(start)
        actions.addWidget(docs)
        actions.addStretch(1)
        self.start_button = start
        self.navigation_button = docs

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addStretch(1)
        self._apply_theme()

    def _apply_theme(self) -> None:
        title_color = theme.tokens.text
        subtitle_color = theme.tokens.text_muted
        bg = "#ffffff" if theme.tokens.mode.value == "light" else "#2b2b2b"
        border = "#e5e5e5" if theme.tokens.mode.value == "light" else "#1d1d1d"
        self.setStyleSheet(
            f"""
QFrame#flatSurface {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 8px;
}}
QLabel#homeHeroTitle {{
    color: {title_color};
    font-size: 34px;
    font-weight: 700;
}}
QLabel#homeHeroSubtitle {{
    color: {subtitle_color};
    font-size: 14px;
}}
"""
        )

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)


class HomeCard(FlatSurface):
    def __init__(
        self,
        icon: QtGui.QIcon,
        title: str,
        description: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._icon = icon
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(8)

        icon_label = QtWidgets.QLabel()
        icon_label.setFixedSize(44, 44)
        icon_label.setPixmap(self._tinted_icon(36))

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("homeCardTitle")
        title_label.setStyleSheet("QLabel#homeCardTitle { font-size: 18px; }")
        title_font = QtGui.QFont("Microsoft YaHei UI")
        title_font.setPointSize(14)
        title_font.setBold(False)
        title_label.setFont(title_font)

        desc_label = QtWidgets.QLabel(description)
        desc_label.setObjectName("muted")
        desc_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addStretch(1)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        self._icon_label = icon_label
        theme.changed.connect(lambda _tokens: self._update_icon())

    def _update_icon(self) -> None:
        self._icon_label.setPixmap(self._tinted_icon(36))

    def _tinted_icon(self, size: int) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        self._icon.paint(painter, pixmap.rect())
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QtGui.QColor(theme.tokens.text))
        painter.end()
        return pixmap


class ComponentRow(FlatSurface):
    def __init__(
        self,
        icon: QtGui.QIcon,
        title: str,
        description: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(88)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        icon_button = IconButton(icon)
        icon_button.setFixedSize(46, 46)
        icon_button.setIconSize(QtCore.QSize(26, 26))
        icon_button.setEnabled(False)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("componentRowTitle")
        title_label.setStyleSheet("QLabel#componentRowTitle { font-size: 15px; font-weight: 700; }")
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        desc_label = QtWidgets.QLabel(description)
        desc_label.setObjectName("muted")
        desc_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)

        layout.addWidget(icon_button)
        layout.addLayout(text_layout, 1)


class IconViewSurface(FlatSurface):
    def _apply_theme(self) -> None:
        if theme.tokens.mode.value == "light":
            bg = "#ffffff"
            border = "#e5e5e5"
        else:
            bg = "#202020"
            border = "#242424"
        self.setStyleSheet(
            f"""
QFrame#flatSurface {{
    background: {bg};
    border: 1px solid {border};
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
}}
"""
        )


class IconTile(QtWidgets.QAbstractButton):
    def __init__(self, icon: FluentIcon, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_key = icon
        self.display_name = fluent_icon_name(icon)
        self.setFixedSize(96, 96)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self._hover = False
        self._icon = fluent_icon(icon)
        theme.changed.connect(lambda _tokens: self.update())

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.TextAntialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = theme.tokens.radius

        if self.isChecked():
            bg = QtGui.QColor(theme.tokens.accent)
            border = QtGui.QColor(theme.tokens.accent)
            text = QtGui.QColor("#ffffff" if theme.tokens.mode.value == "light" else "#111111")
        else:
            bg = QtGui.QColor("#fbfbfb" if theme.tokens.mode.value == "light" else "#2b2b2b")
            if self._hover:
                bg = QtGui.QColor("#f4f4f4" if theme.tokens.mode.value == "light" else "#323232")
            border = QtGui.QColor("#e5e5e5" if theme.tokens.mode.value == "light" else "#1d1d1d")
            text = QtGui.QColor(theme.tokens.text)

        painter.setPen(QtGui.QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)

        icon_color = text
        icon_rect = QtCore.QRect(30, 18, 36, 36)
        pixmap = self._tinted_pixmap(QtCore.QSize(36, 36), icon_color)
        painter.drawPixmap(icon_rect, pixmap)

        name_font = QtGui.QFont("Microsoft YaHei UI")
        name_font.setPointSize(9)
        painter.setFont(name_font)
        painter.setPen(text)
        text_rect = QtCore.QRectF(7, 62, self.width() - 14, 24)
        label = QtGui.QFontMetrics(name_font).elidedText(
            self.display_name,
            QtCore.Qt.TextElideMode.ElideRight,
            round(text_rect.width()),
        )
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter, label)

    def _tinted_pixmap(self, size: QtCore.QSize, color: QtGui.QColor) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        self._icon.paint(painter, QtCore.QRect(QtCore.QPoint(0, 0), size))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return pixmap


class IconDetailPanel(FlatSurface):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(216)
        self._icon = FluentIcon.ADD
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(14)

        self.title_label = QtWidgets.QLabel()
        title_font = QtGui.QFont("Microsoft YaHei UI")
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        self.preview = QtWidgets.QLabel()
        self.preview.setFixedSize(84, 72)
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.name_caption = QtWidgets.QLabel("图标名字")
        self.name_caption.setObjectName("muted")
        self.name_value = QtWidgets.QLabel()
        self.member_caption = QtWidgets.QLabel("枚举成员")
        self.member_caption.setObjectName("muted")
        self.member_value = QtWidgets.QLabel()
        self.member_value.setWordWrap(True)
        self.file_caption = QtWidgets.QLabel("资源文件")
        self.file_caption.setObjectName("muted")
        self.file_value = QtWidgets.QLabel()
        self.file_value.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.preview)
        layout.addSpacing(8)
        layout.addWidget(self.name_caption)
        layout.addWidget(self.name_value)
        layout.addSpacing(8)
        layout.addWidget(self.member_caption)
        layout.addWidget(self.member_value)
        layout.addSpacing(8)
        layout.addWidget(self.file_caption)
        layout.addWidget(self.file_value)
        layout.addStretch(1)
        theme.changed.connect(lambda _tokens: self.set_icon(self._icon))
        self.set_icon(self._icon)

    def _apply_theme(self) -> None:
        if theme.tokens.mode.value == "light":
            bg = "#ffffff"
            border = "#e5e5e5"
        else:
            bg = "#2b2b2b"
            border = "#1d1d1d"
        self.setStyleSheet(
            f"""
QFrame#flatSurface {{
    background: {bg};
    border-left: 1px solid {border};
    border-top: 1px solid {border};
    border-right: 1px solid {border};
    border-bottom: 1px solid {border};
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}}
"""
        )

    def set_icon(self, icon: FluentIcon) -> None:
        self._icon = icon
        name = fluent_icon_name(icon)
        self.title_label.setText(name)
        self.name_value.setText(name)
        self.member_value.setText(f"FluentIcon.{icon.name}")
        self.file_value.setText(icon.value)
        self.preview.setPixmap(self._tinted_pixmap(QtCore.QSize(64, 64), QtGui.QColor(theme.tokens.text)))

    def _tinted_pixmap(self, size: QtCore.QSize, color: QtGui.QColor) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        fluent_icon(self._icon).paint(painter, QtCore.QRect(QtCore.QPoint(0, 0), size))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return pixmap


class _ResizeRelayoutFilter(QtCore.QObject):
    def __init__(self, callback, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._callback = callback

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Resize:
            self._callback()
        return super().eventFilter(watched, event)


def make_section_label(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    font = label.font()
    font.setPointSize(13)
    font.setBold(True)
    label.setFont(font)
    return label


def make_example_block(title: str, panel: ExamplePanel) -> QtWidgets.QWidget:
    block = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(make_section_label(title))
    layout.addWidget(panel)
    return block


def make_placeholder_page(title: str, subtitle: str = "此页面已接入导航，内容会逐步迁移。") -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    page.setObjectName("galleryPage")
    layout = QtWidgets.QVBoxLayout(page)
    layout.setContentsMargins(36, 32, 24, 24)
    layout.setSpacing(10)

    heading = QtWidgets.QLabel(title)
    font = QtGui.QFont("Microsoft YaHei UI")
    font.setPointSize(26)
    font.setBold(True)
    heading.setFont(font)

    body = QtWidgets.QLabel(subtitle)
    body.setObjectName("muted")
    body.setWordWrap(True)

    layout.addStretch(1)
    layout.addWidget(heading)
    layout.addWidget(body)
    layout.addStretch(2)
    return page


def make_home_page(navigation: NavigationView) -> QtWidgets.QScrollArea:
    page = QtWidgets.QScrollArea()
    setup_gallery_scroll_area(page)

    content = QtWidgets.QWidget()
    content.setObjectName("galleryPage")
    content.setProperty("plainGalleryPage", True)
    content.setStyleSheet(
        """
QLabel#homeCardTitle {
    font-size: 18px;
}
QLabel#componentRowTitle {
    font-size: 15px;
    font-weight: 700;
}
"""
    )
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(36, 24, 24, 24)
    layout.setSpacing(22)

    hero = HomeHero()
    hero.start_button.clicked.connect(lambda: navigation.set_current_route("basic_input"))
    hero.navigation_button.clicked.connect(lambda: navigation.set_current_route("navigation"))

    resource_grid = QtWidgets.QGridLayout()
    resource_grid.setHorizontalSpacing(14)
    resource_grid.setVerticalSpacing(14)
    resources = [
        (
            fluent_icon(FluentIcon.HOME),
            "快速开始",
            "从几个常用控件开始，先把窗口跑起来，再慢慢替换旧接口。",
        ),
        (
            fluent_icon(FluentIcon.ICONS),
            "图标系统",
            "统一使用 Fluent System Icons，按钮、导航、状态位都能共用。",
        ),
        (
            fluent_icon(FluentIcon.NAVIGATION),
            "页面导航",
            "侧边栏、顶部导航、分段导航和标签页都会按迁移友好方式整理。",
        ),
        (
            fluent_icon(FluentIcon.TOOLBOX),
            "组件路线",
            "基础输入先打磨手感，之后继续补日期、弹窗、菜单、视图。",
        ),
    ]
    for index, (icon, title, desc) in enumerate(resources):
        resource_grid.addWidget(HomeCard(icon, title, desc), index // 4, index % 4)

    input_label = make_section_label("基础输入样例")
    input_grid = QtWidgets.QGridLayout()
    input_grid.setHorizontalSpacing(14)
    input_grid.setVerticalSpacing(14)
    samples = [
        (
            fluent_icon(FluentIcon.CHECKBOX_CHECKED),
            "Button",
            "轻量、描边、强调和胶囊按钮，按下时只改变颜色反馈。",
        ),
        (
            fluent_icon(FluentIcon.CHECKMARK),
            "CheckBox / RadioButton",
            "复选、三态复选和单选控件，选择圆点带轻微动画。",
        ),
        (
            fluent_icon(FluentIcon.APPS_LIST),
            "ComboBox",
            "下拉浮层、可编辑输入和选择高亮都走同一套主题色。",
        ),
        (
            fluent_icon(FluentIcon.TEXT_FONT),
            "LineEdit",
            "普通、搜索、密码输入框，清空按钮和焦点底线独立绘制。",
        ),
        (
            fluent_icon(FluentIcon.ARROW_SORT),
            "Slider / SpinBox",
            "滑动条、整数调节、小数调节都带细腻状态反馈。",
        ),
        (
            fluent_icon(FluentIcon.INFO),
            "Toast / Progress",
            "状态提示和进度信息会继续向真实应用场景补齐。",
        ),
    ]
    for index, (icon, title, desc) in enumerate(samples):
        input_grid.addWidget(ComponentRow(icon, title, desc), index // 2, index % 2)

    layout.addWidget(hero)
    layout.addLayout(resource_grid)
    layout.addWidget(input_label)
    layout.addLayout(input_grid)
    layout.addStretch(1)
    page.setWidget(content)
    return page


def make_icons_page() -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    page.setObjectName("galleryPage")
    page.setProperty("plainIconPage", True)
    root = QtWidgets.QVBoxLayout(page)
    root.setContentsMargins(12, 12, 12, 12)
    root.setSpacing(12)

    title = make_section_label("流畅图标库")
    search = SearchLineEdit("搜索图标")
    search.setObjectName("iconSearchEdit")
    search.setMinimumWidth(300)
    search.setMaximumWidth(340)

    body = QtWidgets.QHBoxLayout()
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(0)

    grid_host = IconViewSurface()
    grid_host.setMinimumHeight(390)
    grid_host_layout = QtWidgets.QVBoxLayout(grid_host)
    grid_host_layout.setContentsMargins(8, 3, 8, 8)
    grid_scroll = QtWidgets.QScrollArea()
    grid_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    grid_scroll.setWidgetResizable(True)
    grid_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    grid_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    grid_scroll.setVerticalScrollBar(FluentScrollBar(QtCore.Qt.Orientation.Vertical, grid_scroll))
    grid_widget = QtWidgets.QWidget()
    grid_widget.setStyleSheet("QWidget { background: transparent; }")
    grid_layout = QtWidgets.QGridLayout(grid_widget)
    grid_layout.setContentsMargins(0, 0, 0, 0)
    grid_layout.setHorizontalSpacing(8)
    grid_layout.setVerticalSpacing(8)
    grid_scroll.setWidget(grid_widget)
    grid_host_layout.addWidget(grid_scroll)

    detail = IconDetailPanel()
    tiles: list[IconTile] = []
    button_group = QtWidgets.QButtonGroup(page)
    button_group.setExclusive(True)

    grouped_names = [
        "ARROW_UP",
        "ARROW_DOWN",
        "ARROW_LEFT",
        "ARROW_RIGHT",
        "ARROW_UP_RIGHT",
        "ARROW_DOWN_LEFT",
        "ARROW_DOWNLOAD",
        "ARROW_UPLOAD",
        "ARROW_EXPORT",
        "ARROW_IMPORT",
        "ARROW_MAXIMIZE",
        "ARROW_MINIMIZE",
        "ARROW_CLOCKWISE",
        "ARROW_ROTATE_CLOCKWISE",
        "ARROW_ROTATE_COUNTERCLOCKWISE",
        "ARROW_REPEAT_ALL",
        "ARROW_RESET",
        "ARROW_SORT",
        "ARROW_SYNC",
        "ARROW_SWAP",
        "CHEVRON_UP",
        "CHEVRON_DOWN",
        "CHEVRON_LEFT",
        "CHEVRON_RIGHT",
        "ADD",
        "ADD_CIRCLE",
        "ADD_SQUARE",
        "DISMISS",
        "DISMISS_CIRCLE",
        "CHECKMARK",
        "CHECKMARK_CIRCLE",
        "CHECKMARK_SQUARE",
        "CHECKBOX_CHECKED",
        "CHECKBOX_UNCHECKED",
        "EYE",
        "EYE_OFF",
        "KEY",
        "FINGERPRINT",
        "FILTER",
        "FILTER_DISMISS",
        "SETTINGS",
        "TOOLBOX",
        "APPS",
        "APPS_LIST",
        "GRID",
        "TABLE",
        "LAYOUT_ROW_THREE",
        "NAVIGATION",
        "HOME",
        "OPEN",
        "FOLDER",
        "FOLDER_OPEN",
        "DOCUMENT",
        "DOCUMENT_ADD",
        "DOCUMENT_COPY",
        "DOCUMENT_EDIT",
        "DOCUMENT_SAVE",
        "DOCUMENT_SEARCH",
        "DOCUMENT_TEXT",
        "CLIPBOARD",
        "CLIPBOARD_TEXT_LTR",
        "COPY",
        "CUT",
        "DELETE",
        "ARCHIVE",
        "BOOK",
        "BOOKMARK",
        "TAG",
        "PIN",
        "STAR",
        "HEART",
        "MAIL",
        "SEND",
        "CHAT",
        "CHAT_MULTIPLE",
        "CALL",
        "PERSON",
        "PEOPLE",
        "CONTACT_CARD",
        "BOT",
        "COMMENT",
        "COMMENT_MULTIPLE",
        "CALENDAR_LTR",
        "CLOCK",
        "HISTORY",
        "ALERT",
        "WARNING",
        "INFO",
        "QUESTION_CIRCLE",
        "CAMERA",
        "IMAGE",
        "PLAY",
        "PAUSE",
        "STOP",
        "MIC",
        "MIC_OFF",
        "SPEAKER_2",
        "SPEAKER_MUTE",
        "AIRPLANE",
        "CAR",
        "CART",
        "BUILDING",
        "GLOBE",
        "CLOUD",
        "DESKTOP",
        "LAPTOP",
        "CODE",
        "BUG",
        "COLOR",
        "TEXT_FONT",
        "ACCESSIBILITY",
        "BACKPACK",
        "BRIEFCASE",
        "MONEY",
    ]
    preferred_order = [getattr(FluentIcon, name) for name in grouped_names if hasattr(FluentIcon, name)]
    seen: set[FluentIcon] = set()
    icons = []
    for icon in preferred_order + list(FluentIcon):
        if icon not in seen:
            icons.append(icon)
            seen.add(icon)

    for icon in icons:
        tile = IconTile(icon)
        tile.clicked.connect(lambda _checked=False, selected=icon: detail.set_icon(selected))
        tiles.append(tile)
        button_group.addButton(tile)

    current_filter = {"text": ""}

    def relayout(filter_text: str = "") -> None:
        current_filter["text"] = filter_text
        while grid_layout.count():
            item = grid_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        query = filter_text.strip().lower()
        def search_score(tile: IconTile) -> tuple[int, str]:
            if not query:
                return (0, tile.display_name)
            display = tile.display_name.lower()
            enum_name = tile.icon_key.name.lower()
            words = display.replace("/", " ").replace("_", " ").split()
            if display == query or enum_name == query:
                return (0, tile.display_name)
            if display.startswith(query) or enum_name.startswith(query):
                return (1, tile.display_name)
            if any(word.startswith(query) for word in words):
                return (2, tile.display_name)
            if query in display or query in enum_name:
                return (3, tile.display_name)
            if query in tile.icon_key.value.lower():
                return (4, tile.display_name)
            return (99, tile.display_name)

        visible = [tile for tile in tiles if search_score(tile)[0] < 99]
        visible.sort(key=search_score)
        spacing = grid_layout.horizontalSpacing()
        tile_width = 96
        available_width = max(tile_width, grid_scroll.viewport().width() - 2)
        columns = max(1, (available_width + spacing) // (tile_width + spacing))
        for index, tile in enumerate(visible):
            grid_layout.addWidget(tile, index // columns, index % columns)
            tile.show()
        rows = max(1, (len(visible) + columns - 1) // columns)
        for column in range(columns + 1):
            grid_layout.setColumnStretch(column, 0)
        for row in range(rows + 1):
            grid_layout.setRowStretch(row, 0)
        grid_layout.setColumnStretch(columns, 1)
        grid_layout.setRowStretch(rows, 1)
        grid_widget.adjustSize()
        if visible and button_group.checkedButton() not in visible:
            visible[0].setChecked(True)
            detail.set_icon(visible[0].icon_key)

    search.textChanged.connect(relayout)
    relayout_filter = _ResizeRelayoutFilter(lambda: relayout(current_filter["text"]), grid_scroll.viewport())
    grid_scroll.viewport().installEventFilter(relayout_filter)
    grid_scroll._fluent_relayout_filter = relayout_filter
    relayout()
    if tiles:
        tiles[0].setChecked(True)
        detail.set_icon(tiles[0].icon_key)

    body.addWidget(grid_host, 1)
    body.addWidget(detail)

    root.addWidget(title)
    root.addWidget(search, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    root.addLayout(body, 1)
    return page


def make_gallery_header(
    title: str,
    subtitle: str,
    *,
    docs_url: str | None = None,
    source_url: str | None = None,
) -> QtWidgets.QWidget:
    header = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(header)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    title_label = QtWidgets.QLabel(title)
    font = QtGui.QFont("Microsoft YaHei UI")
    font.setPointSize(23)
    font.setBold(False)
    title_label.setFont(font)

    subtitle_label = QtWidgets.QLabel(subtitle)
    subtitle_label.setObjectName("muted")

    action_row = QtWidgets.QHBoxLayout()
    action_row.setContentsMargins(0, 0, 0, 0)
    action_row.setSpacing(8)
    docs = Button("在线文档")
    docs.setIcon(fluent_icon(FluentIcon.DOCUMENT_SAVE))
    source = Button("源代码")
    source.setIcon(fluent_icon(FluentIcon.ICONS))
    if docs_url is not None:
        docs.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(docs_url)))
    if source_url is not None:
        source.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(source_url)))
    action_row.addWidget(docs)
    action_row.addWidget(source)
    action_row.addStretch(1)

    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    layout.addLayout(action_row)
    return header


def make_labeled_panel(
    title: str,
    widget: QtWidgets.QWidget,
    stretch: int = 1,
    *,
    source_url: str | None = None,
) -> QtWidgets.QWidget:
    panel = ExamplePanel(title, "源码")
    panel.preview_layout.addWidget(widget, stretch)
    if source_url is not None:
        source_button = panel.source.findChild(QtWidgets.QAbstractButton)
        source_button.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(source_url)))
    return make_example_block(title, panel)


def gallery_scroll_stylesheet() -> str:
    return """
QScrollArea#galleryScroll {
    background: transparent;
    border: none;
}
QScrollArea#galleryScroll > QWidget > QWidget {
    background: transparent;
}
"""


def setup_gallery_scroll_area(scroll: QtWidgets.QScrollArea) -> None:
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setObjectName("galleryScroll")
    scroll.setStyleSheet(gallery_scroll_stylesheet())
    scroll.setVerticalScrollBar(FluentScrollBar(QtCore.Qt.Orientation.Vertical, scroll))


class PivotDemo(QtWidgets.QWidget):
    def __init__(self, nav: type[Pivot] = Pivot, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.nav = nav()
        self.stack = QtWidgets.QStackedWidget()
        self._pages: dict[str, QtWidgets.QLabel] = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.nav, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.stack, 1)
        for key, text, label in (
            ("start", "开工", "今天先把最顺手的那一步做掉"),
            ("pause", "歇会", "咖啡还热，脑子也还在线"),
            ("review", "复盘", "把刚才的想法收进抽屉"),
        ):
            self.add_page(key, text, label)
        self.nav.currentChanged.connect(self.set_current_page)
        self.set_current_page("start")

    def add_page(self, key: str, text: str, label: str) -> None:
        page = QtWidgets.QLabel(label)
        page.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        page.setObjectName("navigationDemoLabel")
        self._pages[key] = page
        self.stack.addWidget(page)
        self.nav.add_item(key, text)

    def set_current_page(self, key: str) -> None:
        page = self._pages.get(key)
        if not page:
            return
        self.stack.setCurrentWidget(page)
        self.nav.set_current_item(key)


class ToolSegmentDemo(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(92)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        tool = SegmentedToolWidget()
        tool.add_item("wander", fluent_icon(FluentIcon.ARROW_SORT))
        tool.add_item("lock", fluent_icon(FluentIcon.CHECKMARK))
        tool.add_item("glow", fluent_icon(FluentIcon.COLOR))
        layout.addWidget(tool, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        label = QtWidgets.QLabel("当前：灵感捕捉模式")
        label.setObjectName("navigationDemoLabel")
        layout.addWidget(label)
        layout.addStretch(1)


class TabDemo(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(220)
        self._count = 1
        self.tab_bar = TabBar()
        self.stack = QtWidgets.QStackedWidget()
        self.control_panel = QtWidgets.QFrame()
        self.control_panel.setObjectName("navigationControlPanel")
        self._pages: dict[str, QtWidgets.QLabel] = {}

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.tab_bar)
        left_layout.addWidget(self.stack, 1)
        root.addWidget(left, 1)
        root.addWidget(self.control_panel)

        panel = QtWidgets.QVBoxLayout(self.control_panel)
        panel.setContentsMargins(14, 16, 14, 14)
        panel.setSpacing(8)
        for text, checked in (("启用标签拖拽", False), ("启用标签滚动", False), ("启用标签阴影", True)):
            box = CheckBox(text)
            box.setChecked(checked)
            panel.addWidget(box)
        panel.addWidget(QtWidgets.QLabel("标签最大宽度"))
        width_box = QtWidgets.QSpinBox()
        width_box.setRange(60, 400)
        width_box.setValue(200)
        panel.addWidget(width_box)
        panel.addWidget(QtWidgets.QLabel("关闭按钮显示模式"))
        mode = QtWidgets.QComboBox()
        mode.addItems(["始终显示", "悬浮显示", "从不显示"])
        panel.addWidget(mode)
        panel.addStretch(1)

        self.tab_bar.currentChanged.connect(self.set_current_page)
        self.tab_bar.tabAddRequested.connect(self.add_extra_tab)
        self.add_page("desk", "桌面", fluent_icon(FluentIcon.NAVIGATION), "这里放今天要盯住的事")
        self.add_page("stash", "灵感箱", fluent_icon(FluentIcon.COLOR), "突然冒出来的点子先放这里")
        self.add_page("notes", "碎碎念", fluent_icon(FluentIcon.CHAT), "不必正式，但最好别丢")
        self.set_current_page("desk")
        theme.changed.connect(lambda _tokens: self._apply_theme())
        self._apply_theme()

    def add_page(self, key: str, text: str, icon: QtGui.QIcon, label: str) -> None:
        page = QtWidgets.QLabel(label)
        page.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        page.setObjectName("navigationDemoLabel")
        page.setContentsMargins(10, 10, 10, 10)
        self._pages[key] = page
        self.stack.addWidget(page)
        self.tab_bar.add_tab(key, text, icon)

    def add_extra_tab(self) -> None:
        self._count += 1
        key = f"extra_{self._count}"
        self.add_page(key, f"新标签 {self._count}", fluent_icon(FluentIcon.ICONS), f"新标签 {self._count}")
        self.set_current_page(key)

    def set_current_page(self, key: str) -> None:
        page = self._pages.get(key)
        if not page:
            return
        self.stack.setCurrentWidget(page)
        self.tab_bar.set_current_tab(key)

    def _apply_theme(self) -> None:
        tokens = theme.tokens
        self.control_panel.setStyleSheet(
            f"""
QFrame#navigationControlPanel {{
    background: {tokens.surface_low_rgba};
    border-left: 1px solid {tokens.border};
    border-top-right-radius: {tokens.radius}px;
}}
QFrame#navigationControlPanel QLabel,
QFrame#navigationControlPanel QCheckBox {{
    color: {tokens.text};
    background: transparent;
}}
QSpinBox,
QComboBox {{
    color: {tokens.text};
    background: {tokens.surface_high_rgba};
    border: 1px solid {tokens.border};
    border-radius: {tokens.radius}px;
    padding: 5px 8px;
}}
"""
        )


def make_navigation_page() -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    page.setObjectName("galleryPage")
    outer = QtWidgets.QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    scroll = QtWidgets.QScrollArea()
    setup_gallery_scroll_area(scroll)
    content = QtWidgets.QWidget()
    content.setObjectName("galleryPage")
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(36, 28, 36, 28)
    layout.setSpacing(22)

    breadcrumb = BreadcrumbBar()
    for item in ["主页", "MEMZ", "LLL"]:
        breadcrumb.add_item(item, item)

    layout.addWidget(make_gallery_header("导航", "fluentpy.components.navigation"))
    layout.addWidget(make_labeled_panel("面包屑导航栏", breadcrumb, 1))
    layout.addWidget(make_labeled_panel("顶部导航栏", PivotDemo(Pivot), 1))
    layout.addWidget(make_labeled_panel("分段导航栏", PivotDemo(SegmentedWidget), 1))
    layout.addWidget(make_labeled_panel("另一种分段导航栏", ToolSegmentDemo(), 1))
    layout.addWidget(make_labeled_panel("标签栏", TabDemo(), 1))
    layout.addStretch(1)

    scroll.setWidget(content)
    outer.addWidget(scroll)
    return page


def make_dialogs_page(parent_window: QtWidgets.QWidget) -> QtWidgets.QWidget:
    page = QtWidgets.QWidget()
    page.setObjectName("galleryPage")
    outer = QtWidgets.QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    scroll = QtWidgets.QScrollArea()
    setup_gallery_scroll_area(scroll)
    content = QtWidgets.QWidget()
    content.setObjectName("galleryPage")
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(36, 28, 36, 28)
    layout.setSpacing(22)
    frameless_dialog = FramelessDialog(
        "这是一个无边框对话框",
        "它没有系统标题栏，也不会跟随鼠标拖动。先把壳子和按钮手感搭好。",
        parent_window,
    )
    page._frameless_dialog = frameless_dialog

    def show_frameless_dialog() -> None:
        page._frameless_dialog.open()

    masked_dialog = MaskedDialog(
        "这是一个带遮罩的对话框",
        "背景会被压暗，操作焦点留给当前决定。点击按钮关闭，遮罩本身先不抢戏。",
        parent_window,
    )
    page._masked_dialog = masked_dialog

    show_button = Button("显示对话框")
    show_button.clicked.connect(show_frameless_dialog)
    button_box = QtWidgets.QWidget()
    button_layout = QtWidgets.QHBoxLayout(button_box)
    button_layout.setContentsMargins(0, 0, 0, 0)
    button_layout.setSpacing(0)
    button_layout.addWidget(show_button)
    button_layout.addStretch(1)

    def show_masked_dialog() -> None:
        page._masked_dialog.open()

    mask_button = Button("显示遮罩对话框")
    mask_button.clicked.connect(show_masked_dialog)
    mask_box = QtWidgets.QWidget()
    mask_layout = QtWidgets.QHBoxLayout(mask_box)
    mask_layout.setContentsMargins(0, 0, 0, 0)
    mask_layout.setSpacing(0)
    mask_layout.addWidget(mask_button)
    mask_layout.addStretch(1)

    layout.addWidget(make_gallery_header("对话框和弹出窗口", "fluentpy.components.dialog_box"))
    layout.addWidget(make_labeled_panel("无边框对话框", button_box, 0))
    layout.addWidget(make_labeled_panel("遮罩对话框", mask_box, 0))
    layout.addWidget(make_labeled_panel("颜色对话框", QtWidgets.QLabel("先留占位，避免一次做散。"), 0))
    layout.addStretch(1)

    scroll.setWidget(content)
    outer.addWidget(scroll)
    return page


def make_views_page() -> QtWidgets.QWidget:
    page = QtWidgets.QScrollArea()
    setup_gallery_scroll_area(page)
    content = QtWidgets.QWidget()
    content.setObjectName("galleryPage")
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(36, 28, 36, 28)
    layout.setSpacing(22)
    layout.addWidget(make_gallery_header(
        "视图",
        "fluentpy.NoteTimeline",
        docs_url="https://github.com/XDDXMT/FluentPy/blob/main/docs/note-timeline.md",
        source_url="https://github.com/XDDXMT/FluentPy/blob/main/src/fluentpy/widgets/note_timeline.py",
    ))

    description = QtWidgets.QLabel("以时间和音高显示音符分布。下方的进度演示只移动游标，不播放声音。")
    description.setObjectName("muted")
    description.setWordWrap(True)
    layout.addWidget(description)

    preview = QtWidgets.QWidget()
    preview_layout = QtWidgets.QVBoxLayout(preview)
    preview_layout.setContentsMargins(0, 0, 0, 0)
    preview_layout.setSpacing(14)
    timeline = NoteTimeline()
    timeline.setMinimumHeight(100)
    timeline.set_empty_text("选择单轨或双轨短句以显示音符")
    preview_layout.addWidget(timeline)

    source = ComboBox()
    source.addItems(["单轨短句", "双轨短句", "空状态"])
    start = AccentButton("演示进度")
    reset = Button("回到开头")
    controls = QtWidgets.QHBoxLayout()
    controls.setSpacing(10)
    controls.addWidget(source)
    controls.addWidget(start)
    controls.addWidget(reset)
    controls.addStretch(1)
    preview_layout.addLayout(controls)
    progress = QtWidgets.QLabel()
    progress.setObjectName("muted")
    preview_layout.addWidget(progress)

    timer = QtCore.QTimer(page)
    timer.setInterval(30)
    elapsed = QtCore.QElapsedTimer()
    start_position = 0.0

    def update_progress(_seconds: float = 0.0) -> None:
        progress.setText(f"{timeline.position():.1f} / {timeline.duration():.1f} 秒")

    def stop() -> None:
        timer.stop()
        start.setText("演示进度")

    def load_notes(index: int) -> None:
        stop()
        if index == 2:
            timeline.clear()
        else:
            pitches = (60, 64, 67, 65, 62, 64, 69, 67, 64, 62, 60, 64, 62, 60)
            notes = [NoteEvent(i * 0.5, 0.35, pitch) for i, pitch in enumerate(pitches)]
            if index == 1:
                notes.extend(
                    NoteEvent(i * 1.0, 0.75, pitch, track=1)
                    for i, pitch in enumerate((48, 55, 50, 57, 52, 55, 48))
                )
            timeline.set_notes(notes, duration=7.5)
        start.setEnabled(bool(timeline.notes()))
        update_progress()

    def toggle_progress() -> None:
        nonlocal start_position
        if timer.isActive():
            stop()
            return
        if timeline.position() >= timeline.duration():
            timeline.set_position(0.0)
        start_position = timeline.position()
        elapsed.start()
        timer.start()
        start.setText("暂停演示")

    def advance() -> None:
        timeline.set_position(start_position + elapsed.elapsed() / 1000)
        if timeline.position() >= timeline.duration():
            stop()

    def reset_position() -> None:
        stop()
        timeline.set_position(0.0)

    timer.timeout.connect(advance)
    source.currentIndexChanged.connect(load_notes)
    timeline.positionChanged.connect(update_progress)
    start.clicked.connect(toggle_progress)
    reset.clicked.connect(reset_position)
    load_notes(0)
    layout.addWidget(make_labeled_panel(
        "音符时间轴",
        preview,
        source_url="https://github.com/XDDXMT/FluentPy/blob/main/examples/note_timeline.py",
    ))
    layout.addStretch(1)
    page.setWidget(content)
    return page


def create_gallery_window(mode: str = "dark") -> FluentWindow:
    theme.set_mode(mode)
    window = FluentWindow("FluentPy 组件库")
    window.content_layout.setContentsMargins(0, 0, 0, 0)
    window.content_layout.setSpacing(0)

    dark_toggle = ToggleSwitch()
    dark_toggle.setChecked(mode == "dark")

    header = QtWidgets.QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(8)
    header.addStretch(1)
    header.addWidget(QtWidgets.QLabel("深色模式"))
    header.addWidget(dark_toggle)

    hero = HeroBanner()

    controls_title = make_section_label("输入控件")

    link_panel = ExamplePanel("打开外部目标", "源码")
    link_panel.add_centered_row(HyperlinkButton("项目主页", url="https://github.com/XDDXMT/FluentPy"))

    radio_panel = ExamplePanel("选择一个选项", "源码")
    radio_group = QtWidgets.QButtonGroup(window)
    radio_layout = QtWidgets.QVBoxLayout()
    radio_layout.setContentsMargins(0, 0, 0, 0)
    radio_layout.setSpacing(8)
    for index, text in enumerate(["晨风", "极光", "港湾"]):
        radio = RadioButton(text)
        radio.setChecked(index == 1)
        radio_group.addButton(radio)
        radio_layout.addWidget(radio)
    radio_panel.add_centered_layout(radio_layout)

    slider_panel = ExamplePanel("水平数值控件", "源码")
    slider = Slider(QtCore.Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(30)
    slider.setMinimumWidth(220)
    slider_panel.add_centered_row(slider)

    switch_panel = ExamplePanel("切换设置", "源码")
    switch = ToggleSwitch()
    switch_label = QtWidgets.QLabel("关")
    switch.toggled.connect(lambda enabled: switch_label.setText("开" if enabled else "关"))
    switch_panel.add_centered_row(switch, switch_label)

    icon_panel = ExamplePanel("仅图标操作", "源码")
    large_icon = IconButton(fluent_icon(FluentIcon.DOCUMENT_SAVE), tooltip="保存草稿")
    large_icon.setFixedSize(58, 54)
    large_icon.setIconSize(QtCore.QSize(28, 28))
    icon_panel.add_centered_row(large_icon)

    button_panel = ExamplePanel("按钮家族", "源码")
    primary = AccentButton("保存草稿")
    primary.setIcon(fluent_icon(FluentIcon.DOCUMENT_SAVE))
    secondary = Button("确认")
    secondary.setIcon(fluent_icon(FluentIcon.CHECKMARK))
    disabled = Button("等待中")
    disabled.setEnabled(False)
    button_panel.add_centered_row(primary, secondary, disabled)
    button_panel.add_centered_row(TextButton("轻量"), OutlinedButton("描边"), RoundButton("胶囊"), RoundAccentButton("主题胶囊"))

    checked_panel = ExamplePanel("双态复选框", "源码")
    checked_box = CheckBox("把今天的灵感收进袋子")
    checked_box.setChecked(True)
    checked_panel.add_centered_row(checked_box)

    tristate_panel = ExamplePanel("三态复选框", "源码")
    tri_box = CheckBox("今晚先保留一点悬念")
    tri_box.setTristate(True)
    tri_box.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
    tristate_panel.add_centered_row(tri_box)

    combo_panel = ExamplePanel("下拉框", "源码")
    combo = ComboBox()
    combo.addItems(["薄荷热可可", "凌晨便利店", "云端停车位", "第七只纸船"])
    combo_panel.add_centered_row(combo)

    editable_combo_panel = ExamplePanel("可编辑的下拉框", "源码")
    editable_combo = EditableComboBox()
    editable_combo.addItems(["白昼档案", "微风信箱", "蓝莓宇航员", "备用月光"])
    editable_combo_panel.add_centered_row(editable_combo)

    line_panel = ExamplePanel("带清空按钮的输入框", "源码")
    line_edit = LineEdit("写点轻巧的东西")
    line_edit.setText("今天也要优雅地过关")
    line_edit.setMinimumWidth(240)
    line_panel.add_centered_row(line_edit)

    search_panel = ExamplePanel("搜索输入框", "源码")
    search_edit = SearchLineEdit("搜一下口袋里的想法")
    search_edit.setText("海风备忘录")
    search_edit.setMinimumWidth(240)
    search_panel.add_centered_row(search_edit)

    password_panel = ExamplePanel("密码输入框", "源码")
    password_edit = PasswordLineEdit("输入小秘密")
    password_edit.setText("quiet-rain-27")
    password_edit.setMinimumWidth(240)
    password_panel.add_centered_row(password_edit)

    spin_panel = ExamplePanel("数字调节框", "源码")
    spin_box = SpinBox()
    spin_box.setRange(0, 120)
    spin_box.setValue(42)
    spin_box.setMinimumWidth(160)
    spin_panel.add_centered_row(spin_box)

    double_spin_panel = ExamplePanel("小数调节框", "源码")
    double_spin_box = DoubleSpinBox()
    double_spin_box.setRange(0, 24)
    double_spin_box.setSingleStep(0.5)
    double_spin_box.setValue(7.5)
    double_spin_box.setMinimumWidth(160)
    double_spin_panel.add_centered_row(double_spin_box)

    text_panel = ExamplePanel("富文本框", "源码")
    rich_text = TextEdit()
    rich_text.setMinimumSize(320, 150)
    rich_text.setHtml(
        """
<h2>Morning Build</h2>
<ul>
  <li>先把按钮打磨到顺眼</li>
  <li>再把交互调到不闹心</li>
</ul>
"""
    )
    text_panel.preview_layout.addWidget(rich_text)

    primary.clicked.connect(
        lambda: Toast.success(
            "已保存",
            detail="示例使用 FluentPy 原生控件。",
            placement="top-right",
            timeout_ms=2200,
            parent=window,
        )
    )
    dark_toggle.toggled.connect(lambda enabled: theme.set_mode("dark" if enabled else "light"))

    grid = QtWidgets.QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(16)
    grid.addWidget(make_example_block("超链接按钮", link_panel), 0, 0)
    grid.addWidget(make_example_block("单选按钮", radio_panel), 0, 1)
    grid.addWidget(make_example_block("水平滑动条", slider_panel), 1, 0)
    grid.addWidget(make_example_block("开关按钮", switch_panel), 1, 1)
    grid.addWidget(make_example_block("图标按钮", icon_panel), 2, 0)
    grid.addWidget(make_example_block("按钮家族", button_panel), 2, 1)
    grid.addWidget(make_example_block("双态复选框", checked_panel), 3, 0)
    grid.addWidget(make_example_block("三态复选框", tristate_panel), 3, 1)
    grid.addWidget(make_example_block("下拉框", combo_panel), 4, 0)
    grid.addWidget(make_example_block("可编辑的下拉框", editable_combo_panel), 4, 1)
    grid.addWidget(make_example_block("带清空按钮的输入框", line_panel), 5, 0)
    grid.addWidget(make_example_block("搜索输入框", search_panel), 5, 1)
    grid.addWidget(make_example_block("密码输入框", password_panel), 6, 0)
    grid.addWidget(make_example_block("数字调节框", spin_panel), 6, 1)
    grid.addWidget(make_example_block("小数调节框", double_spin_panel), 7, 0)
    grid.addWidget(make_example_block("富文本框", text_panel), 8, 0, 1, 2)

    page = QtWidgets.QScrollArea()
    setup_gallery_scroll_area(page)
    content = QtWidgets.QWidget()
    content.setObjectName("galleryPage")
    page_layout = QtWidgets.QVBoxLayout(content)
    page_layout.setContentsMargins(36, 24, 24, 24)
    page_layout.setSpacing(16)
    page_layout.addLayout(header)
    page_layout.addWidget(hero)
    page_layout.addWidget(controls_title)
    page_layout.addLayout(grid)
    page_layout.addStretch(1)
    page.setWidget(content)

    navigation = NavigationView()
    navigation.add_sub_interface(make_home_page(navigation), fluent_icon(FluentIcon.HOME), "主页", "home")
    navigation.add_sub_interface(make_icons_page(), fluent_icon(FluentIcon.ICONS), "图标", "icons")
    navigation.add_separator()
    navigation.add_sub_interface(page, fluent_icon(FluentIcon.CHECKBOX_CHECKED), "基本输入", "basic_input")
    navigation.add_sub_interface(
        make_placeholder_page("日期和时间", "fluentpy.components.date_time"),
        fluent_icon(FluentIcon.CALENDAR_LTR),
        "日期和时间",
        "date_time",
    )
    navigation.add_sub_interface(
        make_dialogs_page(window),
        fluent_icon(FluentIcon.CHAT),
        "对话框和弹出窗口",
        "dialogs",
    )
    navigation.add_sub_interface(
        make_placeholder_page("布局", "fluentpy.components.layout"),
        fluent_icon(FluentIcon.LAYOUT_ROW_THREE),
        "布局",
        "layout",
    )
    navigation.add_sub_interface(
        make_placeholder_page("材料", "fluentpy.components.material"),
        fluent_icon(FluentIcon.COLOR),
        "材料",
        "material",
    )
    navigation.add_sub_interface(
        make_placeholder_page("菜单和工具栏", "fluentpy.components.menus"),
        fluent_icon(FluentIcon.TOOLBOX),
        "菜单和工具栏",
        "menus",
    )
    navigation.add_sub_interface(make_navigation_page(), fluent_icon(FluentIcon.NAVIGATION), "导航", "navigation")
    navigation.add_sub_interface(
        make_placeholder_page("滚动", "fluentpy.components.scroll"),
        fluent_icon(FluentIcon.ARROW_SORT),
        "滚动",
        "scroll",
    )
    navigation.add_sub_interface(
        make_placeholder_page("状态和信息", "fluentpy.components.status_info"),
        fluent_icon(FluentIcon.INFO),
        "状态和信息",
        "status_info",
    )
    navigation.add_sub_interface(
        make_placeholder_page("文本", "fluentpy.components.text"),
        fluent_icon(FluentIcon.TEXT_FONT),
        "文本",
        "text",
    )
    navigation.add_sub_interface(
        make_views_page(),
        fluent_icon(FluentIcon.TABLE),
        "视图",
        "view",
    )
    navigation.add_sub_interface(
        make_placeholder_page("设置", "fluentpy.components.settings"),
        fluent_icon(FluentIcon.SETTINGS),
        "设置",
        "settings",
        "bottom",
    )
    navigation.set_current_route("home", animated=False)
    window.content_layout.addWidget(navigation)

    def apply_page_theme() -> None:
        tokens = theme.tokens
        background = tokens.background if theme.active else tokens.background_inactive
        for gallery_page in navigation.findChildren(QtWidgets.QWidget, "galleryPage"):
            if gallery_page.property("plainIconPage") or gallery_page.property("plainGalleryPage"):
                icon_bg = "#f7f7f7" if tokens.mode.value == "light" else "#1f2633"
                gallery_page.setStyleSheet(f"QWidget#galleryPage {{ background: {icon_bg}; }}")
            else:
                gallery_page.setStyleSheet(f"QWidget#galleryPage {{ background: {background}; }}")

    theme.changed.connect(lambda _tokens: apply_page_theme())
    apply_page_theme()
    return window


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Segoe UI Variable Text", 10))
    window = create_gallery_window()

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
