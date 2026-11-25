"""Shared UI typography; keep CJK fallback explicit for Qt-painted text."""

import sys

from ..qt import QtGui

UI_FONT_FAMILIES = (
    "Segoe UI Variable Text",
    "Segoe UI",
    "Microsoft YaHei UI",
    "Noto Sans CJK SC",
    "Noto Sans",
)


def font_families(*, monospace: bool = False) -> list[str]:
    """Prefer the platform's own fonts and retain explicit CJK fallbacks."""
    if monospace:
        preferred = {
            "win32": ("Consolas", "Cascadia Code"),
            "darwin": ("SF Mono", "Menlo", "Monaco"),
        }.get(sys.platform, ("DejaVu Sans Mono", "Liberation Mono"))
        role = QtGui.QFontDatabase.SystemFont.FixedFont
        fallbacks = ("Noto Sans Mono CJK SC", "Microsoft YaHei UI", "PingFang SC")
    else:
        preferred = {
            "win32": UI_FONT_FAMILIES[:3],
            "darwin": (".AppleSystemUIFont", "Helvetica Neue", "PingFang SC"),
        }.get(sys.platform, ())
        role = QtGui.QFontDatabase.SystemFont.GeneralFont
        fallbacks = ("Noto Sans CJK SC", "Noto Sans", "DejaVu Sans", "sans-serif")
    system = QtGui.QFontDatabase.systemFont(role).family()
    return list(dict.fromkeys((*preferred, system, *fallbacks)))


def font_family_css(*, monospace: bool = False) -> str:
    return ", ".join(
        '"' + name.replace('"', '\\"') + '"' for name in font_families(monospace=monospace)
    )


def code_font(pixel_size: int) -> QtGui.QFont:
    font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
    font.setFamilies(font_families(monospace=True))
    font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
    font.setPixelSize(pixel_size)
    return font


def ui_font(pixel_size: int, base: QtGui.QFont | None = None) -> QtGui.QFont:
    font = QtGui.QFont(base) if base is not None else QtGui.QFont()
    font.setFamilies(font_families())
    font.setStyleHint(QtGui.QFont.StyleHint.SansSerif)
    font.setPixelSize(pixel_size)
    return font
