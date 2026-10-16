"""Bindings to FluentPy's required C Gregorian date backend.

Importing this module remains possible when the binary is absent or outdated.
The first calculation then explains how to rebuild it. Date arithmetic always
uses C, including when ``FLUENTPY_BACKEND=python`` selects the text reference
backend. There is no Python calendar implementation.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "backend_name", "native_available", "native_error", "days_in_month",
    "clamp_date", "step_date", "column_values",
]

_METHODS = (
    "date_days_in_month", "date_clamp_date", "date_step_date", "date_column_values",
)

try:
    _extension = import_module(f"{__package__.rpartition('.')[0]}._native")
except (ImportError, OSError) as error:
    _extension = None
    _native_import_error = str(error)
else:
    _native_import_error = None
    if not all(callable(getattr(_extension, name, None)) for name in _METHODS):
        _native_import_error = "The installed fluentpy._native extension predates the date backend."
        _extension = None


def native_available() -> bool:
    """Whether the binary supplies every required date calculation."""
    return _extension is not None


def native_error() -> str | None:
    """Return the reason the date backend could not be loaded."""
    return _native_import_error


def _require_native():
    if _extension is None:
        raise RuntimeError(
            "DatePicker and date calculations require the compiled fluentpy._native "
            "date backend. Rebuild the native extension for this Python interpreter "
            "with `python scripts/build_native.py` (or pass --zig with the Zig "
            "executable path), then restart the application. "
            f"Import error: {_native_import_error}"
        )
    return _extension


def backend_name() -> str:
    """Date calculations always use the native backend when available."""
    _require_native()
    return "native"


def days_in_month(year: int, month: int) -> int:
    """Return the Gregorian month length, for years 1 through 9999."""
    return _require_native().date_days_in_month(year=year, month=month)


def clamp_date(
    year: int, month: int, day: int,
    minimum: tuple[int, int, int] = (1, 1, 1),
    maximum: tuple[int, int, int] = (9999, 12, 31),
) -> tuple[int, int, int]:
    """Clamp the day and complete date to a valid inclusive date range."""
    return _require_native().date_clamp_date(
        year=year, month=month, day=day, minimum=minimum, maximum=maximum,
    )


def step_date(
    year: int, month: int, day: int, column: int, steps: int,
    minimum: tuple[int, int, int] = (1, 1, 1),
    maximum: tuple[int, int, int] = (9999, 12, 31),
) -> tuple[int, int, int]:
    """Step one column: years clamp, months/days wrap without carrying."""
    return _require_native().date_step_date(
        year=year, month=month, day=day, column=column, steps=steps,
        minimum=minimum, maximum=maximum,
    )


def column_values(
    year: int, month: int, day: int, column: int, radius: int = 4,
    minimum: tuple[int, int, int] = (1, 1, 1),
    maximum: tuple[int, int, int] = (9999, 12, 31),
) -> tuple[int | None, ...]:
    """Return 2*radius+1 centered wheel rows; radius is limited to 100.

    Year boundaries and the neighbors of a single selectable value are empty.
    Other month/day intervals wrap. ``None`` represents an empty row.
    """
    return _require_native().date_column_values(
        year=year, month=month, day=day, column=column, radius=radius,
        minimum=minimum, maximum=maximum,
    )
