"""Compact, actionable overview composed from existing FluentPy controls."""
from importlib import resources

from fluentpy import Button, FluentIcon, __version__, fluent_icon, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, Signal
from gallery_home import AuroraSurface, GlassButton, LINKS, Picture, caption, text_color


DESCRIPTIONS = {
    "buttons": "触发动作，展开菜单与右键操作。",
    "inputs": "输入文字，选择、组合与验证内容。",
    "tables": "展示数据，体验排序、编辑与多选。",
    "sliders": "拖动调节数值，选择连续区间。",
    "wheels": "滚动选择日期、小时与分钟。",
    "calendar": "挑选日期，设定范围与时间。",
    "drop": "拖入文件或文件夹，查看处理结果。",
    "colors": "搭配颜色，从屏幕拾取灵感。",
    "shortcut": "录入组合键，处理快捷键冲突。",
    "cards": "组织内容，展开和收起设置。",
    "navigation": "切换页面，体验窗口与启动页。",
    "feedback": "显示通知、任务进度和对话框。",
    "code": "编写文本，体验代码高亮与编辑。",
    "notes": "编辑音符，播放与定位时间轴。",
}


class QuickLink(GlassButton):
    def __init__(self, title, detail, icon, target, parent=None):
        super().__init__(title, parent)
        self.target = target
        self.setAccessibleDescription(detail)
        self.setToolTip("浏览下方的组件分类" if target == "catalog" else target)
        self.setFixedHeight(112)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(16, 14, 16, 14)
        body.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        brand = icon is None
        art = (QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
               if brand else fluent_icon(icon))
        top.addWidget(Picture(art, 25, self, original=brand))
        top.addStretch()
        top.addWidget(Picture(fluent_icon(FluentIcon.CHEVRON_DOWN if target == "catalog" else FluentIcon.OPEN), 13, self))
        body.addLayout(top)
        self.heading = caption(title, 15, bold=True)
        self.detail = caption(detail, 11)
        self.detail.setWordWrap(True)
        body.addWidget(self.heading)
        body.addWidget(self.detail)
        self.refresh_theme()
        theme.subscribe(self, self.refresh_theme)

    def sizeHint(self):
        return QtCore.QSize(180, 112)

    def minimumSizeHint(self):
        return QtCore.QSize(138, 112)

    def refresh_theme(self):
        text_color(self.heading, theme.tokens.text)
        text_color(self.detail, theme.tokens.text_muted)
        self.update()


class HomeBanner(AuroraSurface):
    activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, art_scale=.58, corner_radius=14)
        self.columns = 0
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetNoConstraint)
        self.body.setContentsMargins(24, 23, 24, 24)
        self.body.setSpacing(0)
        heading = QtWidgets.QHBoxLayout()
        self.title = caption("FluentPy 工作台", 30, bold=True)
        self.version = caption(f"{__version__}  /  MIT", 11)
        heading.addWidget(self.title, 1)
        heading.addWidget(self.version)
        self.body.addLayout(heading)
        self.body.addSpacing(9)
        self.subtitle = caption("挑选一个组件，立即试试它的外观与交互。", 13)
        self.subtitle.setWordWrap(True)
        self.body.addWidget(self.subtitle)
        self.body.addSpacing(24)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setSpacing(12)
        self.links = []
        details = ("安装与第一个窗口", "实现细节与开源协作", "浏览全部组件分类", "分享想法与报告问题")
        for index, (title, _detail, icon, url) in enumerate(LINKS):
            target = "catalog" if index == 2 else url
            link = QuickLink(title, details[index], icon, target, self)
            link.clicked.connect(lambda checked=False, destination=target: self.activated.emit(destination))
            self.links.append(link)
        self.body.addLayout(self.grid)
        self.reflow(4)
        self.refresh_theme()
        theme.subscribe(self, self.refresh_theme)

    def minimumSizeHint(self):
        return QtCore.QSize(0, self.minimumHeight())

    def reflow(self, columns):
        if self.columns == columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for col in range(4):
            self.grid.setColumnStretch(col, 1 if col < columns else 0)
        for index, link in enumerate(self.links):
            self.grid.addWidget(link, index // columns, index % columns)
        self.body.invalidate()
        self.setMinimumHeight(self.body.minimumSize().height())

    def resizeEvent(self, event):
        self.reflow(4 if self.width() >= 740 else 2)
        super().resizeEvent(event)

    def refresh_theme(self):
        text_color(self.title, theme.tokens.text)
        for label in (self.version, self.subtitle):
            text_color(label, theme.tokens.text_muted)
        for link in self.links:
            link.refresh_theme()
        self.refresh_background()


class IconBadge(QtWidgets.QWidget):
    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        picture = Picture(fluent_icon(icon), 22, self)
        picture.move(8, 8)
        theme.subscribe(self, self.update)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        fill = QtGui.QColor(theme.tokens.accent)
        fill.setAlpha(22 if theme.mode.value == "dark" else 16)
        painter.setBrush(fill)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QtCore.QRectF(self.rect()), 9, 9)


class ComponentCard(Button):
    """One focusable click target per category; original context actions remain."""
    def __init__(self, route, title, icon, parent=None):
        super().__init__(title, parent)
        self.setProperty("componentRoute", route)
        self.setProperty("componentTitle", title)
        self.setAccessibleDescription(DESCRIPTIONS[route])
        self.setFixedHeight(108)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        body = QtWidgets.QHBoxLayout(self)
        body.setContentsMargins(14, 14, 14, 14)
        body.setSpacing(12)
        body.addWidget(IconBadge(icon, self))
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(7)
        self.heading = caption(title, 15, bold=True)
        self.heading.setMinimumWidth(0)
        self.heading.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        self.detail = caption(DESCRIPTIONS[route], 12)
        self.detail.setWordWrap(True)
        self.detail.setMinimumWidth(0)
        text.addWidget(self.heading)
        text.addWidget(self.detail)
        body.addLayout(text, 1)
        body.addWidget(Picture(fluent_icon(FluentIcon.CHEVRON_RIGHT), 14, self))
        self.refresh_theme()
        theme.subscribe(self, self.refresh_theme)

    def sizeHint(self):
        return QtCore.QSize(248, 108)

    def minimumSizeHint(self):
        return QtCore.QSize(220, 108)

    def refresh_theme(self):
        text_color(self.heading, theme.tokens.text)
        text_color(self.detail, theme.tokens.text_muted)
        self.update()

    def _radius(self, rect):
        return 10

    def _surface_color(self):
        return QtGui.QColor(theme.tokens.surface)

    def _surface_hover_color(self):
        return QtGui.QColor(theme.tokens.surface_hover)

    def _surface_pressed_color(self):
        return QtGui.QColor(theme.tokens.surface_pressed)

    def _draw_content(self, painter, rect, color):
        pass

    def _draw_button_border(self, painter, rect, radius):
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(QtGui.QPen(QtGui.QColor(theme.tokens.border), 1))
        painter.drawRoundedRect(rect, radius, radius)


class CatalogArea(QtWidgets.QWidget):
    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetNoConstraint)

    def minimumSizeHint(self):
        return QtCore.QSize(0, self.minimumHeight())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self.resized.emit()
