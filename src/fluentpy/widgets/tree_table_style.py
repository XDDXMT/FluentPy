"""Per-view Windows table surfaces; application theme remains unchanged."""

from types import SimpleNamespace

from ..theme import theme


def tree_colors(style: str):
    if style == "fluent":
        return theme.tokens
    if theme.mode.value == "dark":
        return SimpleNamespace(
            surface="#191919",
            surface_high="#191919",
            text="#ffffff",
            text_muted="#eeeeee",
            border="#303030",
            border_strong="#777777",
            accent="#0078d4",
            disabled="#777777",
            selection="#323232",
            heat_low="#0b2d53",
            heat_high="#005fb8",
            header_name="#252525",
        )
    return SimpleNamespace(
        surface="#ffffff",
        surface_high="#f5f5f5",
        text="#101010",
        text_muted="#303030",
        border="#e1e1e1",
        border_strong="#999999",
        accent="#0067c0",
        disabled="#999999",
        selection="#e5e5e5",
        heat_low="#fff8dc",
        heat_high="#f5c542",
        header_name="#f3f3f3",
    )
