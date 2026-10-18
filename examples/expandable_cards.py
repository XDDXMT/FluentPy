"""Animated expandable settings. Run: python examples/expandable_cards.py.

Capture the complete native demo with --screenshot PATH --quit-after-screenshot.
ExpandableSettings is embeddable and never changes the application's theme.
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
    AccentButton, AccordionWidget, Button, ComboBox, ExpandableCardWidget, FluentScrollBar,
    Slider, ToggleSwitch, theme,
)
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font


def _label(text: str, role: str = "", parent=None) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text, parent)
    label.setObjectName(role)
    label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


class ExpandableSettings(QtWidgets.QWidget):
    """Three compact settings groups with independently retained values."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("expandableSettings")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.accordion = AccordionWidget(self)
        self.accordion.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                     QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(self.accordion)

        self.blend_card = ExpandableCardWidget("混合", expanded=True)
        body = self.blend_card.body_layout
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(10)
        body.addWidget(_label("混合模式"))
        self.mode = ComboBox()
        self.mode.setMinimumWidth(150)
        self.mode.setFixedWidth(150)
        self.mode.setAccessibleName("混合模式")
        self.mode.addItems(["正常", "正片叠底", "滤色", "柔光"])
        body.addWidget(self.mode)
        body.addSpacing(4)
        body.addWidget(_label("不透明度"))
        self.opacity = Slider()
        self.opacity.setRange(0, 100)
        self.opacity.setValue(40)
        self.opacity.setAccessibleName("不透明度百分比")
        self.opacity.setToolTip("40%")
        self.opacity.valueChanged.connect(lambda value: self.opacity.setToolTip(f"{value}%"))
        body.addWidget(self.opacity)
        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(12)
        self.apply_button = AccentButton("应用")
        self.reset_button = Button("重置")
        self.apply_button.clicked.connect(self._apply)
        self.reset_button.clicked.connect(self._reset_blend)
        actions.addWidget(self.apply_button, 1)
        actions.addWidget(self.reset_button, 1)
        body.addLayout(actions)
        self.accordion.add_card(self.blend_card)

        self.hue_card = ExpandableCardWidget("色度")
        self.hue_card.body_layout.setContentsMargins(12, 12, 12, 12)
        self.hue_card.body_layout.setSpacing(10)
        self.hue_value = _label("色相 · 0°")
        self.hue = Slider()
        self.hue.setRange(-180, 180)
        self.hue.setValue(0)
        self.hue.setAccessibleName("色相角度")
        self.hue.valueChanged.connect(lambda value: self.hue_value.setText(f"色相 · {value}°"))
        self.hue_card.body_layout.addWidget(self.hue_value)
        self.hue_card.body_layout.addWidget(self.hue)
        self.hue_reset = Button("重置色相")
        self.hue_reset.clicked.connect(lambda: self.hue.setValue(0))
        self.hue_card.body_layout.addWidget(self.hue_reset, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.accordion.add_card(self.hue_card)

        self.sharp_card = ExpandableCardWidget("锐化")
        self.sharp_card.body_layout.setContentsMargins(12, 12, 12, 12)
        self.sharp_card.body_layout.setSpacing(10)
        sharp_row = QtWidgets.QHBoxLayout()
        sharp_row.addWidget(_label("启用锐化"), 1)
        self.sharp_enabled = ToggleSwitch()
        self.sharp_enabled.setAccessibleName("启用锐化")
        sharp_row.addWidget(self.sharp_enabled)
        self.sharp_card.body_layout.addLayout(sharp_row)
        self.sharp_value = _label("强度 · 25%")
        self.sharpness = Slider()
        self.sharpness.setRange(0, 100)
        self.sharpness.setValue(25)
        self.sharpness.setAccessibleName("锐化强度百分比")
        self.sharpness.setEnabled(False)
        self.sharp_enabled.toggled.connect(self.sharpness.setEnabled)
        self.sharpness.valueChanged.connect(lambda value: self.sharp_value.setText(f"强度 · {value}%"))
        self.sharp_card.body_layout.addWidget(self.sharp_value)
        self.sharp_card.body_layout.addWidget(self.sharpness)
        self.accordion.add_card(self.sharp_card)

        self.result = _label("尚未应用设置", "result")
        self.result.setAccessibleName("设置操作结果")
        layout.addWidget(self.result)
        theme.subscribe(self, self._apply_theme)
        self._apply_theme()

    def _apply(self):
        sharpening = f"锐化 {self.sharpness.value()}%" if self.sharp_enabled.isChecked() else "锐化关闭"
        self.result.setText(
            f"已应用：{self.mode.currentText()} · {self.opacity.value()}% 不透明度\n"
            f"色相 {self.hue.value()}° · {sharpening}"
        )

    def _reset_blend(self):
        self.mode.setCurrentIndex(0)
        self.opacity.setValue(40)
        self.result.setText("混合设置已重置：正常 · 40% 不透明度")

    def _apply_theme(self):
        self.setFont(ui_font(14, self.font()))
        self.setStyleSheet(
            f"QWidget#expandableSettings {{ background: transparent; }}"
            f"QWidget#expandableSettings QLabel {{ color: {theme.tokens.text}; background: transparent;"
            f" border: none; font-size: 14px; font-weight: 400; }}"
            f"QWidget#expandableSettings QLabel#result {{ color: {theme.tokens.text_muted};"
            f" font-size: 12px; }}"
        )


def create_expandable_content(parent=None) -> ExpandableSettings:
    return ExpandableSettings(parent)


class ExpandableCardsDemo(QtWidgets.QWidget):
    def __init__(self, *, dark: bool = False):
        super().__init__()
        theme.set_mode("dark" if dark else "light")
        self.setObjectName("expandableCardsDemo")
        self.setWindowTitle("FluentPy · 折叠设置卡片")
        self.setWindowIcon(QtGui.QIcon(str(resources.files("fluentpy.assets").joinpath("brand/fluentpy.svg"))))
        self.resize(422, 570)
        self.setMinimumWidth(350)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        heading = QtWidgets.QHBoxLayout()
        heading.addWidget(_label("折叠设置", "title"), 1)
        heading.addWidget(_label("深色", "muted"))
        self.dark_toggle = ToggleSwitch()
        self.dark_toggle.setChecked(dark)
        self.dark_toggle.toggled.connect(lambda checked: theme.set_mode("dark" if checked else "light"))
        heading.addWidget(self.dark_toggle)
        layout.addLayout(heading)
        layout.addWidget(_label("点击标题展开设置，收起后保留各项数值。", "muted"))
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBar(FluentScrollBar(parent=self.scroll))
        self.scroll.setHorizontalScrollBar(FluentScrollBar(QtCore.Qt.Orientation.Horizontal, self.scroll))
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QtWidgets.QWidget()
        inner_layout = QtWidgets.QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(16)
        self.content = create_expandable_content()
        inner_layout.addWidget(self.content)
        inner_layout.addStretch()
        self.scroll.setWidget(inner)
        layout.addWidget(self.scroll, 1)
        behavior = QtWidgets.QHBoxLayout()
        behavior.addWidget(_label("同时只展开一项"), 1)
        self.exclusive_toggle = ToggleSwitch()
        self.exclusive_toggle.setAccessibleName("同时只展开一项")
        self.exclusive_toggle.toggled.connect(self.content.accordion.set_exclusive)
        behavior.addWidget(self.exclusive_toggle)
        layout.addLayout(behavior)
        theme.subscribe(self, self._apply_theme)
        self._apply_theme()

    def _apply_theme(self):
        self.setFont(ui_font(14, self.font()))
        self.setStyleSheet(
            f"QWidget#expandableCardsDemo, QScrollArea, QScrollArea > QWidget > QWidget"
            f" {{ background: {theme.tokens.background}; }}"
            f"QWidget#expandableCardsDemo QLabel {{ color: {theme.tokens.text}; background: transparent; }}"
            f"QWidget#expandableCardsDemo QLabel#title {{ font-size: 22px; font-weight: 600; }}"
            f"QWidget#expandableCardsDemo QLabel#muted {{ color: {theme.tokens.text_muted}; font-size: 12px; }}"
        )


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
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    demo = ExpandableCardsDemo(dark=args.dark)
    if args.screenshot:
        demo.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    demo.show()
    failures = []
    if args.screenshot:
        def save():
            try:
                target = args.screenshot.resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                if not demo.grab().save(str(target)):
                    raise RuntimeError(f"Unable to save {target}")
                print(target)
            except Exception as error:
                failures.append(str(error))
                print(error, file=sys.stderr)
            finally:
                if args.quit_after_screenshot or failures:
                    app.quit()
        QtCore.QTimer.singleShot(300, save)
    result = app.exec()
    return 1 if failures else result


if __name__ == "__main__":
    raise SystemExit(main())
