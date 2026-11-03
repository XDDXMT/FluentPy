"""Column presentation and optional item roles for hierarchical data views."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from ..qt import QtCore, QtGui


class TreeRole(IntEnum):
    """Optional roles; ordinary Qt models work without providing these values."""

    Key = int(QtCore.Qt.ItemDataRole.UserRole) + 901
    Subtitle = Key + 1
    Group = Key + 2
    CellKind = Key + 3
    Color = Key + 4
    Summary = Key + 5
    IconTint = Key + 6


@dataclass(frozen=True)
class TreeColumn:
    """Presentation only: formatting never replaces the model's raw values.

    ``kind`` accepts text, badge, progress or action. ``heat`` adds a numerical
    tint independently of kind. A column delegate can replace all painting
    and editing through Qt's setItemDelegateForColumn(). ``editable`` is the
    default for convenience items; external models retain their own flags.
    """

    key: str
    title: str
    width: int = 150
    minimum_width: int = 48
    stretch: bool = False
    alignment: QtCore.Qt.AlignmentFlag = (
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    kind: str = "text"
    formatter: Callable[[Any], str] | None = None
    heat: bool = False
    minimum: float = 0.0
    maximum: float = 100.0
    color: str | None = None
    editable: bool = False
    sort_role: int = int(QtCore.Qt.ItemDataRole.DisplayRole)

    def __post_init__(self):
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("column key must be a non-empty string")
        if self.kind not in {"text", "badge", "progress", "action"}:
            raise ValueError("kind must be text, badge, progress or action")
        if self.minimum_width < 24 or self.width < self.minimum_width:
            raise ValueError("width must be at least minimum_width, which must be >= 24")
        if not all(math.isfinite(v) for v in (self.minimum, self.maximum)):
            raise ValueError("presentation range must be finite")
        if self.maximum <= self.minimum:
            raise ValueError("maximum must be greater than minimum")
        if self.color is not None and not QtGui.QColor(self.color).isValid():
            raise ValueError("invalid column color")


@dataclass(frozen=True)
class TreeCell:
    """Optional metadata for one convenience cell; a plain value also works.

    Passing TreeCell to update_item replaces its metadata. Passing a plain
    value updates only DisplayRole and keeps the existing icon and flags.
    Icons accept QIcon, QPixmap, FluentIcon or an image path.
    """

    value: Any = None
    icon: Any = None
    subtitle: str = ""
    tooltip: str = ""
    kind: str | None = None
    color: str | None = None
    check_state: QtCore.Qt.CheckState | None = None
    editable: bool | None = None

    def __post_init__(self):
        if self.kind is not None and self.kind not in {"text", "badge", "progress", "action"}:
            raise ValueError("kind must be text, badge, progress or action")
        if self.color is not None and not QtGui.QColor(self.color).isValid():
            raise ValueError("invalid cell color")


def column_definitions(columns) -> tuple[TreeColumn, ...]:
    """Validate a schema before changing either a view or its source model."""
    result = tuple(columns)
    if any(not isinstance(column, TreeColumn) for column in result):
        raise TypeError("columns must contain TreeColumn instances")
    if len({column.key for column in result}) != len(result):
        raise ValueError("column keys must be unique")
    return result
