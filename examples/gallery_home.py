"""An original gallery landing page built with the existing FluentPy API.

Run with --light for the light palette. No downloaded artwork is required.
ResourceCard and GalleryHero are example-local compositions, not new library API.
"""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fluentpy import (
    Button,
    FluentIcon,
    FluentScrollBar,
    FluentWindow,
    ToggleSwitch,
    fluent_icon,
    theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets, Signal
from fluentpy.theme.fonts import ui_font

LINKS = (
    (
        "开始使用",
        "安装组件库，创建你的第一个\nFluentPy 桌面窗口。",
        None,
        "https://fluentpy.mcxmcl.cn/#/getting-started",
    ),
    (
        "项目源码",
        "了解实现，参与改进。\n每一处细节都可以由你掌握。",
        FluentIcon.CODE,
        "https://github.com/XDDXMT/FluentPy",
    ),
    (
        "组件示例",
        "从按钮到表格，探索布局、\n交互与明暗主题。",
        FluentIcon.GRID,
        "https://fluentpy.mcxmcl.cn/#/cards",
    ),
    (
        "交流反馈",
        "分享想法，报告问题，\n让下一次使用更顺手。",
        FluentIcon.CHAT,
        "https://github.com/XDDXMT/FluentPy/issues",
    ),
)


def caption(text, size, *, bold=False, parent=None):
    label = QtWidgets.QLabel(text, parent)
    font = ui_font(size)
    if bold:
        font.setWeight(QtGui.QFont.Weight.DemiBold)
    label.setFont(font)
    label.setProperty("captionSize", size)
    label.setProperty("captionBold", bold)
    label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    text_color(label, theme.tokens.text)
    return label


def text_color(label, color):
    # Local rules retain typography and muted ink when FluentWindow updates
    # its shared child palette and base font during show/activation/theme changes.
    label.setStyleSheet(
        f"font-size: {label.property('captionSize')}px; "
        f"font-weight: {600 if label.property('captionBold') else 400}; "
        f"color: {QtGui.QColor(color).name()}; background: transparent; border: none;"
    )
    palette = label.palette()
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(color))
    label.setPalette(palette)


class Picture(QtWidgets.QWidget):
    def __init__(self, icon, size, parent=None, *, original=False):
        super().__init__(parent)
        self.art = icon
        self.original = original
        self.setFixedSize(size, size)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._cache = None
        theme.subscribe(self, self.refresh)

    def refresh(self):
        self._cache = None
        self.update()

    def paintEvent(self, event):
        ratio = self.devicePixelRatioF()
        key = (ratio, theme.mode)
        if self._cache is None or self._cache[0] != key:
            pixmap = self.art.pixmap(self.size() * ratio)
            pixmap.setDevicePixelRatio(ratio)
            if not self.original:
                ink = QtGui.QPainter(pixmap)
                ink.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
                ink.fillRect(pixmap.rect(), QtGui.QColor(theme.tokens.text))
                ink.end()
            self._cache = key, pixmap
        painter = QtGui.QPainter(self)
        painter.drawPixmap(self.rect(), self._cache[1])


class GlassButton(Button):
    """Existing Button interactions with a translucent, rounded surface."""

    def _radius(self, rect):
        return 12

    def _surface_color(self):
        return (
            QtGui.QColor(30, 38, 50, 195)
            if theme.mode.value == "dark"
            else QtGui.QColor(255, 255, 255, 192)
        )

    def _surface_hover_color(self):
        return (
            QtGui.QColor(48, 59, 75, 225)
            if theme.mode.value == "dark"
            else QtGui.QColor(255, 255, 255, 232)
        )

    def _surface_pressed_color(self):
        return (
            QtGui.QColor(25, 32, 43, 235)
            if theme.mode.value == "dark"
            else QtGui.QColor(235, 241, 248, 230)
        )

    def _draw_content(self, painter, rect, color):
        # The ordinary Qt child layout draws the icon and text.
        pass

    def _draw_button_border(self, painter, rect, radius):
        dark = theme.mode.value == "dark"
        border = QtGui.QColor(255, 255, 255, 30) if dark else QtGui.QColor(63, 88, 109, 30)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(QtGui.QPen(border, 1))
        painter.drawRoundedRect(rect, radius, radius)


class ResourceCard(GlassButton):
    """A normal keyboard-accessible Button with a translucent custom surface.

    The inherited hover/press animations and click semantics remain intact.
    Labels pass mouse events through, so the whole surface is one click target.
    """

    def __init__(self, title, description, icon, url, parent=None):
        super().__init__(title, parent)
        self.url = QtCore.QUrl(url)
        self.setAccessibleName(title)
        self.setAccessibleDescription(description.replace("\n", " "))
        self.setToolTip(url)
        self.setFixedHeight(232)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        body = QtWidgets.QVBoxLayout(self)
        body.setContentsMargins(24, 24, 24, 20)
        body.setSpacing(0)
        brand = icon is None
        art = (
            QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
            if brand
            else fluent_icon(icon)
        )
        self.picture = Picture(art, 46, self, original=brand)
        body.addWidget(self.picture)
        body.addSpacing(20)
        self.heading = caption(title, 18, parent=self)
        body.addWidget(self.heading)
        body.addSpacing(9)
        self.description = caption(description, 12, parent=self)
        self.description.setWordWrap(True)
        body.addWidget(self.description)
        body.addStretch(1)
        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch(1)
        self.arrow = Picture(fluent_icon(FluentIcon.OPEN), 17, self)
        bottom.addWidget(self.arrow)
        body.addLayout(bottom)
        self.refresh_labels()
        theme.subscribe(self, self.refresh_labels)

    def sizeHint(self):
        return QtCore.QSize(230, 232)

    def minimumSizeHint(self):
        return QtCore.QSize(180, 232)

    def refresh_labels(self):
        text_color(self.heading, theme.tokens.text)
        text_color(self.description, theme.tokens.text_muted)
        self.update()


class AuroraSurface(QtWidgets.QWidget):
    """Cached original background shared by the landing-page examples."""

    def __init__(self, parent=None, *, art_scale=1.0, corner_radius=0):
        super().__init__(parent)
        self.art_scale = art_scale
        self.corner_radius = corner_radius
        self._background = None
        theme.subscribe(self, self.refresh_background)

    def refresh_background(self):
        self._background = None
        self.update()

    def resizeEvent(self, event):
        self.refresh_background()
        super().resizeEvent(event)

    def _make_background(self):
        """Cache original vector artwork at the current size and display DPI."""
        ratio = self.devicePixelRatioF()
        pixmap = QtGui.QPixmap(self.size() * ratio)
        pixmap.setDevicePixelRatio(ratio)
        dark = theme.mode.value == "dark"
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        base = QtGui.QLinearGradient(0, 0, self.width(), self.height())
        base.setColorAt(0, QtGui.QColor("#0b111e" if dark else "#eff6fb"))
        base.setColorAt(1, QtGui.QColor("#202d42" if dark else "#dce9f3"))
        painter.fillRect(self.rect(), base)
        # A separate curved aurora composition, authored here rather than
        # importing the reference gallery's wallpaper, geometry or assets.
        painter.save()
        painter.scale(self.width() / 1060, self.art_scale)
        glow = QtGui.QRadialGradient(730, 138, 420)
        glow.setColorAt(0, QtGui.QColor(85, 104, 216, 100 if dark else 42))
        glow.setColorAt(1, QtGui.QColor(85, 104, 216, 0))
        painter.fillRect(QtCore.QRectF(0, 0, 1060, 550), glow)
        for offset, alpha in ((70, 55), (24, 100), (0, 210)):
            ribbon = QtGui.QPainterPath()
            ribbon.moveTo(-90, 330 + offset)
            ribbon.cubicTo(140, 100 + offset, 282, 450 + offset, 550, 182 + offset)
            ribbon.cubicTo(755, -24 + offset, 900, 105 + offset, 1160, 192 + offset)
            ribbon.lineTo(1160, 245 + offset)
            ribbon.cubicTo(875, 163 + offset, 758, 56 + offset, 570, 244 + offset)
            ribbon.cubicTo(320, 495 + offset, 103, 215 + offset, -90, 402 + offset)
            ribbon.closeSubpath()
            gradient = QtGui.QLinearGradient(70, 390, 1030, 80)
            gradient.setColorAt(
                0, QtGui.QColor(20, 195, 203, alpha if dark else round(alpha * 0.65))
            )
            gradient.setColorAt(0.45, QtGui.QColor(44, 123, 225, alpha))
            gradient.setColorAt(1, QtGui.QColor(153, 111, 230, alpha))
            painter.fillPath(ribbon, gradient)
        edge = QtGui.QPainterPath()
        edge.moveTo(-90, 330)
        edge.cubicTo(140, 100, 282, 450, 550, 182)
        edge.cubicTo(755, -24, 900, 105, 1160, 192)
        painter.setPen(QtGui.QPen(QtGui.QColor(172, 226, 255, 170 if dark else 210), 1.4))
        painter.drawPath(edge)
        painter.restore()
        # Fade into the page so narrow, scrolling layouts keep a quiet base.
        fade = QtGui.QLinearGradient(0, 340, 0, 620)
        bottom = QtGui.QColor("#202d42" if dark else "#dce9f3")
        transparent = QtGui.QColor(bottom)
        transparent.setAlpha(0)
        fade.setColorAt(0, transparent)
        fade.setColorAt(1, bottom)
        painter.fillRect(self.rect(), fade)
        painter.end()
        self._background = pixmap

    def paintEvent(self, event):
        if (
            self._background is None
            or self._background.devicePixelRatioF() != self.devicePixelRatioF()
        ):
            self._make_background()
        painter = QtGui.QPainter(self)
        if self.corner_radius:
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(QtCore.QRectF(self.rect()), self.corner_radius, self.corner_radius)
            painter.setClipPath(clip)
        painter.drawPixmap(0, 0, self._background)


class GalleryHero(AuroraSurface):
    activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._background = None
        self.columns = 0
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetNoConstraint)
        self.body.setContentsMargins(36, 30, 36, 28)
        self.body.setSpacing(0)
        top = QtWidgets.QHBoxLayout()
        self.eyebrow = caption("CREATE SOMETHING FLUENT", 11, bold=True)
        top.addWidget(self.eyebrow)
        top.addStretch(1)
        self.mode_label = caption("深色", 12)
        top.addWidget(self.mode_label)
        self.dark_toggle = ToggleSwitch(self)
        self.dark_toggle.setAccessibleName("深色模式")
        self.dark_toggle.setChecked(theme.mode.value == "dark")
        self.dark_toggle.toggled.connect(lambda dark: theme.set_mode("dark" if dark else "light"))
        top.addWidget(self.dark_toggle)
        self.body.addLayout(top)
        self.body.addSpacing(23)
        self.title = caption("FluentPy Gallery", 42, bold=True)
        self.body.addWidget(self.title)
        self.body.addSpacing(12)
        self.subtitle = caption("从一个想法，到一个好用的桌面应用。", 14)
        self.body.addWidget(self.subtitle)
        self.body.addSpacing(54)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(16)
        self.cards = []
        for title, detail, icon, url in LINKS:
            card = ResourceCard(title, detail, icon, url, self)
            card.clicked.connect(
                lambda checked=False, destination=url: self.activated.emit(destination)
            )
            self.cards.append(card)
        self.body.addLayout(self.grid)
        self.body.addSpacing(26)
        footer = QtWidgets.QHBoxLayout()
        self.tagline = caption("把灵感，变成下一个界面。", 12)
        self.license = caption("FluentPy  /  MIT", 11)
        footer.addWidget(self.tagline, 1)
        footer.addWidget(self.license)
        self.body.addLayout(footer)
        self.body.addStretch(1)
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
        for column in range(4):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)
        self.body.invalidate()
        self.setMinimumHeight(self.body.minimumSize().height())

    def resizeEvent(self, event):
        title_size = 42 if self.width() >= 520 else 32
        if self.title.property("captionSize") != title_size:
            self.title.setProperty("captionSize", title_size)
            text_color(self.title, theme.tokens.text)
        self.reflow(4 if self.width() >= 920 else 2 if self.width() >= 520 else 1)
        self._background = None
        super().resizeEvent(event)

    def refresh_theme(self):
        dark = theme.mode.value == "dark"
        self.dark_toggle.blockSignals(True)
        self.dark_toggle.setChecked(dark)
        self.dark_toggle.blockSignals(False)
        for label in (self.title, self.mode_label):
            text_color(label, theme.tokens.text)
        for label in (self.subtitle, self.tagline, self.license):
            text_color(label, theme.tokens.text_muted)
        text_color(self.eyebrow, "#80d7e0" if dark else "#116a79")
        self._background = None
        self.update()


class GalleryHomeDemo(FluentWindow):
    def __init__(self, *, dark=True):
        theme.set_mode("dark" if dark else "light")
        super().__init__("FluentPy · 欢迎页")
        self.setWindowIcon(
            QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg")))
        )
        self.resize(1060, 610)
        self.setMinimumSize(380, 420)
        self.set_title_bar_enabled(True)
        self.title_bar().set_bar_height(48)
        self.set_theme_transition_enabled(True)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBar(FluentScrollBar(parent=self.scroll))
        self.hero = GalleryHero()
        self.scroll.setWidget(self.hero)
        self.content_layout.addWidget(self.scroll)
        self.hero.activated.connect(self.open_resource)

    def _apply_theme(self):
        super()._apply_theme()
        # FluentWindow also refreshes child palettes when it is first shown.
        # Restore this page's deliberate title/muted/eyebrow ink afterwards.
        hero = getattr(self, "hero", None)
        if hero is not None:
            hero.refresh_theme()
            for card in hero.cards:
                card.refresh_labels()

    def open_resource(self, url):
        # A failed browser hand-off leaves a useful, selectable address.
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)):
            QtWidgets.QMessageBox.information(self, "打开链接", f"请在浏览器中打开：\n{url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--quit-after-screenshot", action="store_true")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot")
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = GalleryHomeDemo(dark=not args.light)
    if args.screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    failures = []
    if args.screenshot:

        def capture():
            try:
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

        QtCore.QTimer.singleShot(260, capture)
    result = app.exec()
    return 1 if failures else result


if __name__ == "__main__":
    raise SystemExit(main())
