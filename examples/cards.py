"""Five card containers with Unicode emoji and Fluent vector icons. Run: python examples/cards.py.

Hidden captures: --screenshot ABSOLUTE_PATH --quit-after-screenshot [--dark].
The embeddable create_cards_content() factory never changes the global theme.
"""
from __future__ import annotations

import argparse
from importlib import resources
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import (
    AccentButton, Button, CardWidget, ComboBox, ElevatedCardWidget,
    GroupHeaderCardWidget, HeaderCardWidget, LineEdit, SimpleCardWidget,
    SpinBox, TextButton, ToggleSwitch, FluentIcon, fluent_icon, theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font

BRAND_ICON = resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")
TILES_PREVIEW_SIZE = (440, 168)


class FluentPicture(QtWidgets.QWidget):
    """A bundled SVG, either theme-tinted or displayed in its original colors."""
    def __init__(self, icon: FluentIcon | QtGui.QIcon, size: int = 64, *, success=False,
                 preserve_colors=False, parent=None):
        super().__init__(parent)
        self.icon = fluent_icon(icon) if isinstance(icon, FluentIcon) else QtGui.QIcon(icon)
        self.success = success
        self.preserve_colors = preserve_colors
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName(icon.name if isinstance(icon, FluentIcon) else "FluentPy 主图标")
        theme.subscribe(self, self.update)

    def paintEvent(self, event):
        if self.preserve_colors:
            painter = QtGui.QPainter(self)
            self.icon.paint(painter, self.rect().adjusted(4, 4, -4, -4))
            return
        pixmap = self.icon.pixmap(self.size())
        painter = QtGui.QPainter(pixmap)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
        color = ("#0f7b0f" if theme.mode.value == "light" else "#6ccb5f") if self.success else theme.tokens.text
        painter.fillRect(pixmap.rect(), QtGui.QColor(color))
        painter.end()
        painter = QtGui.QPainter(self)
        painter.drawPixmap(self.rect(), pixmap)


def emoji_label(text: str, parent=None) -> QtWidgets.QLabel:
    widget = QtWidgets.QLabel(text, parent)
    widget.setFixedSize(56, 52)
    widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    widget.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    font = QtGui.QFont("Segoe UI Emoji")
    font.setPixelSize(40)
    widget.setFont(font)
    widget.setStyleSheet('font-family: "Segoe UI Emoji"; font-size: 40px; background: transparent; border: none;')
    widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    return widget


def label(text: str, role: str = "", parent=None) -> QtWidgets.QLabel:
    widget = QtWidgets.QLabel(text, parent)
    widget.setObjectName(role)
    widget.setWordWrap(True)
    widget.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    widget.setMinimumWidth(0)
    return widget


class AppMoreButton(TextButton):
    _h_padding = 4


class CardsContent(QtWidgets.QWidget):
    """Embeddable content: no window, scroll container or theme mutation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardsContent")
        self.cards = []
        self.action_counts: dict[str, int] = {}
        self.application_cards = []
        self.open_buttons = []
        self.more_buttons = []
        self.tiles = []
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(10)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(label("应用卡片", "sectionTitle"))
        controls.addStretch()
        controls.addWidget(label("圆角", "muted"))
        self.radius = SpinBox(self)
        self.radius.setRange(0, 24)
        self.radius.setValue(8)
        self.radius.setFixedWidth(90)
        controls.addWidget(self.radius)
        root.addLayout(controls)
        self.apps_preview = QtWidgets.QWidget(self)
        apps = QtWidgets.QVBoxLayout(self.apps_preview)
        apps.setContentsMargins(0, 0, 0, 0)
        apps.setSpacing(8)
        for cls, name, detail, art in (
            (CardWidget, "PluentPy", "MIT License", QtGui.QIcon(str(BRAND_ICON))),
            (SimpleCardWidget, "文本", "我是文本", FluentIcon.BUILDING_BANK),
        ):
            card = cls(self.apps_preview)
            card.setFixedHeight(72)
            row = QtWidgets.QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            row.setSpacing(16)
            row.addWidget(FluentPicture(art, 40, preserve_colors=isinstance(art, QtGui.QIcon), parent=card))
            text_widget = QtWidgets.QWidget(card)
            text_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            text = QtWidgets.QVBoxLayout(text_widget)
            text.setContentsMargins(0, 0, 0, 0)
            text.setSpacing(2)
            for value, role in ((name, "appTitle"), (detail, "appDescription")):
                caption = label(value, role, text_widget)
                caption.setWordWrap(False)
                caption.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
                text.addWidget(caption)
            row.addWidget(text_widget, 1, QtCore.Qt.AlignmentFlag.AlignVCenter)
            actions = QtWidgets.QHBoxLayout()
            actions.setSpacing(8)
            open_button = Button("打开", card)
            open_button.setFixedSize(80, 32)
            open_button.clicked.connect(lambda checked=False, n=name: self.report("打开", f"触发了「{n}」的打开操作。"))
            actions.addWidget(open_button, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
            more = AppMoreButton("•••", card)
            more.setAccessibleName(name + "的更多选项")
            more.setFixedSize(32, 32)
            more.clicked.connect(lambda checked=False, n=name: self.report("更多", f"触发了「{n}」的更多操作。"))
            actions.addWidget(more, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
            row.addLayout(actions)
            apps.addWidget(card)
            self.cards.append(card)
            self.application_cards.append(card)
            self.open_buttons.append(open_button)
            self.more_buttons.append(more)
        root.addWidget(self.apps_preview)

        root.addWidget(label("悬停，感受一点轻盈。", "sectionTitle"))
        tile_row = QtWidgets.QHBoxLayout()
        tile_row.setSpacing(16)
        self.tiles_preview = QtWidgets.QWidget(self)
        self.tiles_preview.setObjectName("tilesPreview")
        self.tiles_preview.setFixedSize(*TILES_PREVIEW_SIZE)
        tiles_layout = QtWidgets.QHBoxLayout(self.tiles_preview)
        tiles_layout.setContentsMargins(16, 20, 16, 20)
        tiles_layout.setSpacing(12)
        for title, kind in (
            ("笑出汗", "😅"),
            ("热晕了", "🥵"),
            ("派对时刻", "🥳"),
        ):
            tile = ElevatedCardWidget(self.tiles_preview)
            tile.setFixedSize(128, 128)
            box = QtWidgets.QVBoxLayout(tile)
            box.setContentsMargins(12, 12, 12, 12)
            box.setSpacing(0)
            box.addStretch()
            box.addWidget(emoji_label(kind, tile), 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
            box.addSpacing(6)
            title_label = label(title, "tileTitle", tile)
            title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            title_label.setFixedHeight(20)
            box.addWidget(title_label)
            box.addStretch()
            tiles_layout.addWidget(tile)
            self.tiles.append(tile)
            self.cards.append(tile)
        tile_row.addWidget(self.tiles_preview)
        tile_note = label("移入卡片查看悬浮阴影", "muted", self)
        tile_row.addWidget(tile_note, 1)
        root.addLayout(tile_row)

        lower = QtWidgets.QHBoxLayout()
        lower.setSpacing(18)
        self.requirements = HeaderCardWidget("系统要求", self)
        self.requirements.header_widget.setFixedHeight(52)
        check_row = QtWidgets.QHBoxLayout()
        check_row.setSpacing(12)
        check_row.addWidget(FluentPicture(FluentIcon.CHECKMARK_CIRCLE, 26, success=True, parent=self.requirements))
        check_row.addWidget(label("当前环境已就绪", "bodyStrong", self.requirements), 1)
        self.requirements.body_layout.addLayout(check_row)
        self.requirements.body_layout.addWidget(label("Windows 10 及以上\nPython 3.10+ · Qt 6", "muted", self.requirements))
        self.requirements_detail = label("卡片和交互由 Qt 绘制。\n本页演示不运行外部构建或上传。", "muted", self.requirements)
        self.requirements_detail.hide()
        self.requirements.body_layout.addWidget(self.requirements_detail)
        self.details_button = TextButton("查看详情", self.requirements)
        self.details_button.clicked.connect(self._toggle_details)
        self.requirements.body_layout.addWidget(self.details_button, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        left = QtWidgets.QVBoxLayout()
        left.addWidget(self.requirements)
        left.addStretch()
        lower.addLayout(left, 2)
        self.settings = GroupHeaderCardWidget("构建与运行", self)
        self.settings.header_widget.setFixedHeight(52)
        self.directory = LineEdit(parent=self.settings)
        self.directory.setText("build/cards-demo")
        self.directory.setFixedWidth(174)
        self.directory.editingFinished.connect(lambda: self.report("目录", f"构建目录已改为 {self.directory.text()}"))
        self.terminal = ComboBox(self.settings)
        self.terminal.addItems(["集成终端", "独立终端"])
        self.terminal.setFixedWidth(174)
        self.terminal.currentTextChanged.connect(lambda value: self.report("终端", f"已选择{value}。"))
        self.entry = ComboBox(self.settings)
        self.entry.addItems(["examples/cards.py", "examples/main.py", "app.py"])
        self.entry.setFixedWidth(174)
        self.entry.currentTextChanged.connect(lambda value: self.report("入口", f"入口脚本：{value}"))
        self.groups = [
            self.settings.add_group(FluentIcon.FOLDER, "构建目录", "保存本地演示内容", self.directory),
            self.settings.add_group(FluentIcon.CODE, "终端模式", "选择运行时的终端", self.terminal),
            self.settings.add_group(FluentIcon.DOCUMENT, "入口脚本", "启动时使用的 Python 文件", self.entry),
        ]
        footer = QtWidgets.QWidget(self.settings)
        footer_row = QtWidgets.QHBoxLayout(footer)
        footer_row.setContentsMargins(22, 12, 22, 16)
        footer_row.setSpacing(8)
        footer_row.addWidget(label("准备就绪", "muted", footer))
        footer_row.addStretch()
        self.reset_button = Button("重置", footer)
        self.reset_button.clicked.connect(self._reset)
        self.build_button = AccentButton("构建预览", footer)
        self.build_button.clicked.connect(self._build)
        footer_row.addWidget(self.reset_button)
        footer_row.addWidget(self.build_button)
        self.settings.body_layout.addWidget(footer)
        self.settings_footer = footer
        lower.addWidget(self.settings, 3, QtCore.Qt.AlignmentFlag.AlignTop)
        root.addLayout(lower)
        self.cards.extend((self.requirements, self.settings))

        self.result = label("操作卡片内的按钮或设置，结果会显示在这里。", "result", self)
        self.result.setMinimumHeight(40)
        root.addWidget(self.result)
        self.radius.valueChanged.connect(self._set_radius)
        self._set_radius(8)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _set_radius(self, radius):
        for card in self.cards:
            card.set_border_radius(radius)

    def report(self, action: str, message: str):
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        self.result.setText(message)

    def _toggle_details(self):
        expanded = self.requirements_detail.isHidden()
        self.requirements_detail.setVisible(expanded)
        self.details_button.setText("收起详情" if expanded else "查看详情")
        self.report("详情", "已展开系统要求详情。" if expanded else "已收起系统要求详情。")

    def _reset(self):
        self.directory.setText("build/cards-demo")
        self.terminal.setCurrentIndex(0)
        self.entry.setCurrentIndex(0)
        self.radius.setValue(8)
        self.report("重置", "已恢复默认设置。")

    def _build(self):
        self.report("构建", f"预览已就绪 · {self.entry.currentText()} · {self.terminal.currentText()} · {self.directory.text()}")

    def _apply_theme(self):
        tokens = theme.tokens
        self.setFont(ui_font(14, self.font()))
        self.setStyleSheet(f'''
QWidget#cardsContent {{ background: transparent; }}
QWidget#tilesPreview {{ background: {tokens.background}; }}
QLabel {{ color: {tokens.text}; background: transparent; border: none;
 font-family: "Segoe UI Variable Text", "Microsoft YaHei UI"; font-size: 14px; }}
QLabel#sectionTitle {{ font-size: 16px; font-weight: 600; }}
QLabel#appTitle {{ font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 14px; font-weight: 400; }}
QLabel#appDescription {{ font-family: "Segoe UI", "Microsoft YaHei UI"; color: {tokens.text_muted}; font-size: 12px; font-weight: 400; }}
QLabel#tileTitle, QLabel#bodyStrong {{ font-size: 14px; font-weight: 600; }}
QLabel#muted {{ color: {tokens.text_muted}; font-size: 12px; }}
QLabel#tileCaption {{ color: {tokens.text_muted}; font-size: 11px; }}
QLabel#result {{ color: {tokens.accent}; font-size: 12px; padding: 8px 12px;
 background: {tokens.surface}; border: 1px solid {tokens.border}; border-radius: 6px; }}
''')


def create_cards_content(parent=None) -> QtWidgets.QWidget:
    return CardsContent(parent)


class CardsDemo(QtWidgets.QWidget):
    def __init__(self, *, dark: bool = False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("cardsDemo")
        self.setWindowTitle("FluentPy · 卡片")
        self.setWindowIcon(QtGui.QIcon(str(BRAND_ICON)))
        self.resize(960, 760)
        self.setMinimumSize(800, 640)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        heading = QtWidgets.QHBoxLayout()
        title = label("让内容，自然成组。", "demoTitle", self)
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(label("深色", "muted", self))
        self.dark_toggle = ToggleSwitch(self)
        self.dark_toggle.setChecked(dark)
        self.dark_toggle.toggled.connect(lambda value: theme.set_mode("dark" if value else "light"))
        heading.addWidget(self.dark_toggle)
        root.addLayout(heading)
        root.addWidget(label("五种卡片，一起体验内容布局、悬停反馈与设置分组。", "muted", self))
        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.content = create_cards_content()
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)
        self._apply_theme()
        theme.subscribe(self, self._apply_theme)

    def _apply_theme(self):
        tokens = theme.tokens
        self.setFont(ui_font(14, self.font()))
        self.setStyleSheet(f'''
QWidget#cardsDemo, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {tokens.background}; }}
QLabel {{ color: {tokens.text}; background: transparent; font-family: "Segoe UI Variable Text", "Microsoft YaHei UI"; font-size: 14px; }}
QLabel#demoTitle {{ font-size: 26px; font-weight: 600; }}
QLabel#muted {{ color: {tokens.text_muted}; font-size: 12px; }}
''')

    def fit_preview(self):
        app = QtWidgets.QApplication.instance()
        app.processEvents()
        wanted = self.content.sizeHint().height() + 132
        self.resize(960, max(760, wanted))
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        app.processEvents()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot")
    if args.screenshot:
        os.environ["QT_SCALE_FACTOR"] = "1"
        if sys.platform == "win32":
            os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = CardsDemo(dark=args.dark)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    failures = []
    if args.screenshot:
        def save():
            try:
                window.fit_preview()
                target = args.screenshot.resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(target)):
                    raise RuntimeError(f"Unable to save {target}")
                print(target)
            except Exception as error:
                failures.append(str(error))
                print(str(error), file=sys.stderr)
            finally:
                if args.quit_after_screenshot or failures:
                    app.quit()
        QtCore.QTimer.singleShot(200, save)
    result = app.exec()
    return 1 if failures else result


if __name__ == "__main__":
    raise SystemExit(main())
